"""阶段学习工作流 — Supervisor 驱动的 LangGraph 状态图

一次调用 = 为一个学习阶段按需增量生成资源。

图结构（真 StateGraph + 条件边 + 循环）：

    START → supervisor_plan ──generate──→ act → observe → quality_gate ──不合格──→ supervisor_plan
                          └────done────→ END ←──────────合格──────────────────────────┘

与旧 graph_builder 的区别：
- 真正 compile().ainvoke()，不是 for 循环
- 条件边由确定性谓词裁决（质量分/重做次数/白名单），LLM 只在 plan 节点内活动
- 每次只针对一个 stage，由学生进入阶段时触发（增量生成）
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import log
from app.agents.supervisor_agent import SupervisorAgent, MAX_REGEN

# 单节点超时（秒），防止某个工具卡死拖垮整个循环
TOOL_TIMEOUT_SECONDS = 300
PLAN_TIMEOUT_SECONDS = 60

# 资源生成器分发表（与 student.py 的 _RESOURCE_GENERATORS 对齐，但独立维护）
# 每个生成器签名: async (db, user_id, topic, stage_id) -> content


class StageState(BaseModel):
    """阶段工作流共享状态（黑板）"""

    user_id: int
    stage_id: int
    profile_id: Optional[int] = None
    db: Optional[Any] = None  # 运行时注入，不参与图序列化

    profile: Dict[str, Any] = Field(default_factory=dict)
    stage: Dict[str, Any] = Field(default_factory=dict)
    topic: str = ""

    generated: Dict[str, Any] = Field(default_factory=dict)      # tool -> 摘要
    quality_scores: Dict[str, float] = Field(default_factory=dict)
    regen_counts: Dict[str, int] = Field(default_factory=dict)

    decision: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    fix_hints: List[str] = Field(default_factory=list)
    grounding: List[Dict[str, str]] = Field(default_factory=list)

    messages: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    status: str = "running"

    class Config:
        arbitrary_types_allowed = True


def _now() -> str:
    return datetime.now().isoformat()


def _log_msg(state: StageState, sender: str, receiver: str, mtype: str, content: Any) -> None:
    """结构化消息协议：from/to/type/content"""
    state.messages.append({
        "from": sender,
        "to": receiver,
        "type": mtype,
        "content": content if isinstance(content, (str, int, float, bool)) else str(content)[:500],
        "timestamp": _now(),
    })


# ── 节点实现 ───────────────────────────────────────────────


async def supervisor_plan_node(state: StageState) -> Dict[str, Any]:
    """思考节点：LLM 决策下一步调用哪个工具（输出经白名单校验）"""
    supervisor = SupervisorAgent(state.db)

    # 仅在本轮需要 grounding 时检索（plan 后由 act 使用）
    result: Dict[str, Any] = {}

    try:
        decision = await asyncio.wait_for(
            supervisor.plan(
                profile=state.profile,
                stage=state.stage,
                generated=state.generated,
                quality_scores=state.quality_scores,
                regen_counts=state.regen_counts,
                knowledge_base_hits=state.grounding,
                fix_hints=state.fix_hints,
            ),
            timeout=PLAN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        log.warning(f"Supervisor 规划超时，使用默认计划，用户 {state.user_id}")
        decision = supervisor.default_plan(
            state.profile, state.stage, state.generated,
            state.quality_scores, state.regen_counts, state.fix_hints,
        )
    except Exception as e:
        log.warning(f"Supervisor 规划异常，使用默认计划: {e}")
        decision = supervisor.default_plan(
            state.profile, state.stage, state.generated,
            state.quality_scores, state.regen_counts, state.fix_hints,
        )

    result["decision"] = decision
    _log_msg(state, "supervisor", "self", "decision", f"{decision.get('action')}:{decision.get('tool')} — {decision.get('reasoning')}")
    return result


async def act_node(state: StageState) -> Dict[str, Any]:
    """执行节点：按决策调用工具（资源生成 Agent），携带 grounding"""
    decision = state.decision or {}
    tool = decision.get("tool")
    if not tool:
        return {"tool_result": None}

    db = state.db
    user_id = state.user_id
    stage_id = state.stage_id
    topic = state.topic
    params = decision.get("params") or {}
    fix_hints = params.get("fix_hints") or state.fix_hints

    # 需要接地的工具：检索知识库（空库自然返回 []，纯 LLM 降级）
    grounding = state.grounding
    if params.get("use_grounding", True) and not grounding:
        supervisor = SupervisorAgent(db)
        grounding = await supervisor.retrieve_grounding(user_id, f"{topic} {tool}")

    try:
        content = await asyncio.wait_for(
            _dispatch_tool(db, user_id, topic, stage_id, tool, state.profile, grounding, fix_hints),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return {
            "tool_result": {"tool": tool, "error": f"timeout:{TOOL_TIMEOUT_SECONDS}s"},
            "error": f"工具 {tool} 执行超时",
            "fix_hints": [f"TOOL_TIMEOUT_{tool}"],
        }
    except Exception as e:
        log.error(f"工具 {tool} 执行失败: {e}", exc_info=True)
        return {
            "tool_result": {"tool": tool, "error": str(e)},
            "error": str(e),
            "fix_hints": [f"TOOL_FAILED_{tool}"],
        }

    # 统一 content 为 dict + 规范化
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            content = parsed if isinstance(parsed, (dict, list)) else {"content": content}
        except Exception:
            content = {"content": content}
    elif content is None:
        content = {}
    if isinstance(content, dict):
        from app.agents.utils import normalize_resource_content
        content = normalize_resource_content(content, tool)

    # 标记 grounding 来源（空库时显式 llm_generated，不伪装教材内容）
    if isinstance(content, dict):
        content["source"] = "grounded" if grounding else "llm_generated"
        if grounding:
            content["grounding_evidence_ids"] = [g["evidence_id"] for g in grounding]

    _log_msg(state, "supervisor", tool, "dispatch", f"生成 {tool}（grounding={len(grounding)} 条）")
    return {
        "tool_result": {"tool": tool, "content": content},
        "grounding": grounding,
    }


async def observe_node(state: StageState) -> Dict[str, Any]:
    """观察节点：产物入库（MySQL + ChromaDB 双写）并回写 State"""
    result = state.tool_result
    if not result or result.get("error"):
        return {}

    tool = result["tool"]
    content = result["content"]
    db = state.db

    # 1. MySQL 入库（唯一可信源）
    try:
        await _save_resource_mysql(
            db, state.user_id, state.profile_id, state.stage_id, tool, state.topic, content
        )
    except Exception as e:
        log.error(f"资源 {tool} MySQL 入库失败: {e}")
        return {"error": f"MySQL 入库失败: {e}"}

    # 1.5 题目同步进题库（一等公民，重生成不丢作答历史）
    if tool == "question" and isinstance(content, dict):
        try:
            from app.api.v1.question_bank import upsert_question_from_resource
            await upsert_question_from_resource(
                db, state.user_id, state.profile_id, state.stage_id,
                content.get("questions") or [],
            )
        except Exception as e:
            log.warning(f"题目同步题库失败（不影响主流程）: {e}")

    # 2. 摘要回写 State（完整内容留在 DB，State 只存摘要，避免黑板膨胀）
    summary = _summarize_content(tool, content)
    generated = dict(state.generated)
    generated[tool] = summary
    regen = dict(state.regen_counts)

    _log_msg(state, tool, "supervisor", "result", f"{tool} 已生成并入库")
    return {"generated": generated, "regen_counts": regen}


async def quality_gate_node(state: StageState) -> Dict[str, Any]:
    """质量守门员：确定性谓词——分数阈值 + 重做次数上限"""
    result = state.tool_result
    if not result or result.get("error"):
        return {"status": "failed"}

    tool = result["tool"]
    content = result["content"]
    from app.core.quality_thresholds import quality_thresholds
    threshold = quality_thresholds.get_threshold(tool)

    # 质量评估
    try:
        from app.agents.resource_quality_agent import ResourceQualityAgent
        quality_agent = ResourceQualityAgent(state.db)
        quality = await asyncio.wait_for(
            quality_agent.run(topic=state.topic, resource_type=tool, content=content, user_id=state.user_id),
            timeout=60,
        )
    except Exception as e:
        log.warning(f"资源 {tool} 质量评估失败，按通过处理: {e}")
        quality = {"overall_score": threshold, "issues": []}

    score = quality.get("overall_score") or threshold
    issues = quality.get("issues") or []

    # 把质量分写回 MySQL 资源记录
    try:
        await _update_resource_quality(state.db, state.user_id, state.stage_id, tool, quality)
    except Exception as e:
        log.warning(f"回写质量分失败: {e}")

    scores = dict(state.quality_scores)
    scores[tool] = float(score)
    regen = dict(state.regen_counts)

    messages_delta: List[Dict[str, Any]] = []

    if score < threshold and regen.get(tool, 0) < MAX_REGEN:
        # 不达标：记录重做次数 + 结构化扣分点，回环给 Supervisor
        regen[tool] = regen.get(tool, 0) + 1
        hints = [str(i) for i in issues][:10] or [f"score_below_threshold:{score}<{threshold}"]
        _log_msg(state, "quality_gate", "supervisor", "reject", f"{tool} {score}分<{threshold}，第{regen[tool]}次重做")
        return {
            "quality_scores": scores,
            "regen_counts": regen,
            "fix_hints": hints,
            "error": None,
        }

    # 达标或重做次数用尽：入库向量库（检索记忆）
    try:
        await _index_resource_chroma(state.user_id, state.stage_id, tool, state.topic, content)
    except Exception as e:
        log.warning(f"资源 {tool} ChromaDB 索引失败（不影响主流程）: {e}")

    _log_msg(state, "quality_gate", "supervisor", "accept", f"{tool} {score}分 达标")
    return {
        "quality_scores": scores,
        "regen_counts": regen,
        "fix_hints": [],
        "error": None,
    }


# ── 条件边（确定性守门员，无 LLM）─────────────────────────


def route_after_plan(state: StageState) -> str:
    decision = state.decision or {}
    if state.error and state.status == "failed":
        return "end"
    if decision.get("action") == "done":
        return "end"
    # 白名单已在 SupervisorAgent.validate 保证；act 只认 generate+tool
    if decision.get("action") == "generate" and decision.get("tool"):
        return "act"
    return "end"


def route_after_gate(state: StageState) -> str:
    if state.status == "failed":
        return "end"
    # 回到 supervisor 重新思考（可能重做同一工具或推进下一个）
    return "supervisor_plan"


# ── 工具分发 ───────────────────────────────────────────────


async def _dispatch_tool(
    db: AsyncSession,
    user_id: int,
    topic: str,
    stage_id: int,
    tool: str,
    profile: Dict[str, Any],
    grounding: List[Dict[str, str]],
    fix_hints: List[str],
) -> Any:
    """调用对应的专业工具 Agent（这些是无脑手脚，决策在 Supervisor）"""
    grounding_text = "\n".join(
        f"[{g['evidence_id']}] {g['text']}" for g in grounding
    ) if grounding else ""
    hints_text = "；".join(fix_hints) if fix_hints else ""

    if tool == "document":
        from app.agents.document_agent import DocumentAgent
        agent = DocumentAgent(db)
        extra = f"\n\n## 参考资料（以此为准，参考资料未覆盖的才允许拓展并标注「拓展」）\n{grounding_text}" if grounding_text else ""
        if hints_text:
            extra += f"\n\n## 上次生成的问题（必须修正）\n{hints_text}"
        return await agent.run(topic, user_id=user_id, force=True, extra_instructions=extra)

    if tool == "question":
        from app.agents.question_agent import QuestionAgent
        agent = QuestionAgent(db)
        extra = f"\n\n## 参考资料（题目须基于以下材料，不得超纲）\n{grounding_text}" if grounding_text else ""
        if hints_text:
            extra += f"\n\n## 上次生成的问题（必须修正）\n{hints_text}"
        return await agent.run(topic, user_id=user_id, force=True, extra_instructions=extra)

    if tool == "code":
        from app.agents.code_agent import CodeAgent
        agent = CodeAgent(db)
        task = f"编写一个与「{topic}」相关的 Python 代码示例"
        if grounding_text:
            task += f"\n参考材料：\n{grounding_text}"
        if hints_text:
            task += f"\n上次问题（必须修正）：{hints_text}"
        return await agent.run(task, user_id=user_id)

    if tool == "mindmap":
        from app.agents.mindmap_agent import MindmapAgent
        agent = MindmapAgent(db)
        return await agent.run(topic, user_id=user_id)

    if tool == "reading_material":
        from app.agents.reading_material_agent import ReadingMaterialAgent
        agent = ReadingMaterialAgent(db)
        return await agent.run(topic, user_id=user_id)

    if tool == "glossary":
        from app.agents.glossary_agent import GlossaryAgent
        agent = GlossaryAgent(db)
        return await agent.run(topic, user_id=user_id)

    if tool == "summary":
        from app.agents.summary_agent import SummaryAgent
        agent = SummaryAgent(db)
        return await agent.run(topic, user_id=user_id)

    if tool == "ppt_video":
        from app.agents.ppt_video_agent import PptVideoAgent
        agent = PptVideoAgent(db)
        return await agent.run(topic, user_id=user_id)

    if tool == "knowledge_link":
        from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
        agent = KnowledgeGraphAgent(db, scope="stage")
        return await agent.run(topic, user_id=user_id, stage_id=stage_id)

    raise ValueError(f"未知工具: {tool}")


# ── 存储辅助 ───────────────────────────────────────────────


async def _save_resource_mysql(
    db: AsyncSession,
    user_id: int,
    profile_id: Optional[int],
    stage_id: int,
    resource_type: str,
    topic: str,
    content: Dict[str, Any],
) -> None:
    from app.models import LearningResource
    from app.models.upsert import upsert as mysql_upsert
    await mysql_upsert(db, LearningResource.__table__, values={
        "user_id": user_id,
        "profile_id": profile_id,
        "stage_id": stage_id,
        "resource_type": resource_type,
        "topic": topic,
        "content": content,
    })
    await db.commit()


async def _update_resource_quality(
    db: AsyncSession, user_id: int, stage_id: int, resource_type: str, quality: Dict[str, Any]
) -> None:
    from sqlalchemy import select
    from app.models import LearningResource
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.user_id == user_id,
            LearningResource.stage_id == stage_id,
            LearningResource.resource_type == resource_type,
        ).order_by(LearningResource.created_at.desc()).limit(1)
    )
    record = result.scalar_one_or_none()
    if record and isinstance(record.content, dict):
        updated = dict(record.content)
        updated["quality_score"] = quality
        record.content = updated
        await db.commit()


async def _index_resource_chroma(
    user_id: int, stage_id: int, resource_type: str, topic: str, content: Dict[str, Any]
) -> None:
    """达标资源写入 ChromaDB（检索记忆）；重生成前按 resource 标识先删旧块"""
    from app.vectorstore.chroma_store import vector_store

    # 先删该资源旧分块（重生成场景）
    resource_key = f"user{user_id}_stage{stage_id}_{resource_type}"
    try:
        vector_store.delete_documents_by_filter({"resource_key": resource_key})
    except Exception:
        pass

    text = _extract_text_for_index(content)
    if not text or not text.strip():
        return

    # 分块（约 500 字一块）
    chunks = _split_text(text, chunk_size=500, overlap=50)
    ids = [f"{resource_key}_c{i}" for i in range(len(chunks))]
    metadatas = [{
        "user_id": user_id,
        "stage_id": stage_id,
        "resource_type": resource_type,
        "resource_key": resource_key,
        "topic": topic,
        "source": content.get("source", "llm_generated"),
    } for _ in chunks]
    vector_store.add_documents(chunks, metadatas=metadatas, ids=ids)
    log.info(f"资源 {resource_type} 已索引进 ChromaDB：{len(chunks)} 块（用户 {user_id}）")


def _extract_text_for_index(content: Dict[str, Any]) -> str:
    """从各类资源 content 中抽取可检索文本"""
    parts: List[str] = []
    for key in ("content", "mindmap_markdown", "code", "summary", "report"):
        v = content.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    for key, sub in (("questions", "question"), ("terms", "term"), ("pages", "content")):
        items = content.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    val = it.get(sub) or it.get("title") or ""
                    if val:
                        parts.append(str(val))
                elif isinstance(it, str):
                    parts.append(it)
    return "\n".join(parts)


def _split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def _summarize_content(tool: str, content: Dict[str, Any]) -> Dict[str, Any]:
    """State 里只留摘要，避免黑板无限膨胀"""
    summary: Dict[str, Any] = {"type": tool, "source": content.get("source")}
    qs = content.get("quality_score")
    if isinstance(qs, dict):
        summary["quality_score"] = qs.get("overall_score")
    for key in ("title", "summary", "topic"):
        if content.get(key):
            summary[key] = str(content[key])[:100]
    if tool == "question":
        summary["question_count"] = len(content.get("questions") or [])
    if tool == "document":
        text = content.get("content") or ""
        summary["excerpt"] = str(text)[:80]
    return summary


# ── 图构建与入口 ───────────────────────────────────────────


def build_stage_graph():
    """构建阶段学习状态图"""
    workflow = StateGraph(StageState)

    workflow.add_node("supervisor_plan", supervisor_plan_node)
    workflow.add_node("act", act_node)
    workflow.add_node("observe", observe_node)
    workflow.add_node("quality_gate", quality_gate_node)

    workflow.set_entry_point("supervisor_plan")

    # 条件边：plan 之后——generate→act / done→END
    workflow.add_conditional_edges(
        "supervisor_plan",
        route_after_plan,
        {"act": "act", "end": END},
    )
    workflow.add_edge("act", "observe")
    workflow.add_edge("observe", "quality_gate")
    # 条件边：gate 之后——回 supervisor 循环 / 失败结束
    workflow.add_conditional_edges(
        "quality_gate",
        route_after_gate,
        {"supervisor_plan": "supervisor_plan", "end": END},
    )

    return workflow.compile()


# 模块级缓存编译后的图
_compiled_graph = None


def get_stage_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_stage_graph()
        log.info("阶段学习状态图已编译")
    return _compiled_graph


async def run_stage_workflow(
    db: AsyncSession,
    user_id: int,
    stage_id: int,
    profile_id: Optional[int] = None,
    progress_cb=None,
) -> StageState:
    """为指定阶段运行 Supervisor 学习环（真 LangGraph ainvoke）

    Args:
        progress_cb: 可选回调 async (state: StageState) -> None，用于推送进度
    """
    # ── 组装初始状态 ──
    profile, stage, topic = await _load_context(db, user_id, profile_id, stage_id)

    initial = StageState(
        user_id=user_id,
        stage_id=stage_id,
        profile_id=profile_id,
        db=db,
        profile=profile,
        stage=stage,
        topic=topic,
    )
    _log_msg(initial, "system", "supervisor", "start", f"阶段 {stage_id} 学习环启动")

    graph = get_stage_graph()

    # LangGraph 配置里放 db（避免塞进可序列化 state 的深坑由 db 字段 + 模块缓存兜底）
    final_state: StageState = await graph.ainvoke(initial)

    # ainvoke 返回的可能是 dict，统一还原
    if isinstance(final_state, dict):
        final_state = StageState(**{**initial.dict(), **final_state, "db": db})
    final_state.db = db

    if final_state.status != "failed" and not final_state.error:
        final_state.status = "completed"
    log.info(
        f"阶段 {stage_id} 学习环结束：status={final_state.status}, "
        f"生成={list(final_state.generated.keys())}, 质量={final_state.quality_scores}"
    )
    if progress_cb:
        try:
            await progress_cb(final_state)
        except Exception:
            pass
    return final_state


async def _load_context(
    db: AsyncSession, user_id: int, profile_id: Optional[int], stage_id: int
) -> tuple[Dict, Dict, str]:
    """加载画像 + 阶段 + topic"""
    from sqlalchemy import select
    from app.models import StudentProfile, LearningPath

    # 画像
    if profile_id:
        prof = await db.get(StudentProfile, profile_id)
    else:
        result = await db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
                StudentProfile.is_archived == False,
            )
        )
        prof = result.scalar_one_or_none()
    profile = {}
    if prof:
        profile = {
            "major": prof.major or "",
            "grade": prof.grade or "",
            "goal": prof.goal or "",
            "knowledge_level": prof.knowledge_level or "",
            "learning_style": prof.learning_style or "",
            "interests": prof.interests or [],
            "weakness": prof.weakness or [],
            "coding_ability": prof.coding_ability or "",
        }

    # 路径阶段
    path_query = select(LearningPath).where(LearningPath.user_id == user_id)
    if prof:
        path_query = path_query.where(LearningPath.profile_id == prof.id)
    path_result = await db.execute(path_query.order_by(LearningPath.created_at.desc()).limit(1))
    path = path_result.scalar_one_or_none()
    stages = (path.stages if path else []) or []
    stage = next((s for s in stages if s.get("stage_id") == stage_id), stages[0] if stages else {})

    # topic：本阶段知识点拼接
    kps = stage.get("knowledge_points") or []
    kp_names = []
    for kp in kps:
        if isinstance(kp, dict):
            kp_names.append(kp.get("name", ""))
        else:
            kp_names.append(str(kp))
    topic = "、".join(k[:20] for k in kp_names if k)[:80] or stage.get("title", "") or "学习基础"

    return profile, stage or {}, topic
