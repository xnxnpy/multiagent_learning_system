"""SupervisorAgent — 学习环主控 Agent

职责：读取共享状态（画像/阶段/已生成资源/质量分/知识库命中），
思考并输出「下一步调用哪个工具」的决策 JSON。

防幻觉设计：
- 行动空间封闭：tool 只能取 TOOLS 白名单或 done
- 决策 schema 校验：字段类型/枚举由代码强制
- LLM 失败时回退确定性默认计划（default_plan），流程永不中断
"""
import json
from typing import Dict, Any, List, Optional

from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log

# 工具白名单（与 stage_workflow 分发表一一对应）
TOOLS = [
    "document", "question", "code", "mindmap",
    "reading_material", "glossary", "summary", "ppt_video", "knowledge_link",
]

# 必做工具：未达标前不允许 done
REQUIRED_TOOLS = ["document", "question"]

# 质量阈值来源（与 quality_thresholds 保持一致的默认值，运行时以配置为准）
DEFAULT_QUALITY_THRESHOLD = 70

MAX_REGEN = 2


class SupervisorAgent(BaseAgent):
    agent_name = "supervisor"

    PROMPT_PATH = "prompts/supervisor_prompt.txt"

    async def run(self, **kwargs) -> Dict[str, Any]:
        """BaseAgent 接口兼容：等价于 plan()"""
        return await self.plan(
            profile=kwargs.get("profile") or {},
            stage=kwargs.get("stage") or {},
            generated=kwargs.get("generated") or {},
            quality_scores=kwargs.get("quality_scores") or {},
            regen_counts=kwargs.get("regen_counts") or {},
            knowledge_base_hits=kwargs.get("knowledge_base_hits") or [],
            fix_hints=kwargs.get("fix_hints") or [],
            force_tools=kwargs.get("force_tools"),
            force_mode=bool(kwargs.get("force_mode")),
        )

    # ── 决策 ───────────────────────────────────────────────

    async def plan(
        self,
        profile: Dict[str, Any],
        stage: Dict[str, Any],
        generated: Dict[str, Any],
        quality_scores: Dict[str, float],
        regen_counts: Dict[str, int],
        knowledge_base_hits: List[Dict[str, str]],
        fix_hints: List[str],
        force_tools: Optional[List[str]] = None,
        force_mode: bool = False,
    ) -> Dict[str, Any]:
        """产出一个经白名单校验的决策。LLM 失败时回退 default_plan。"""
        # 上下文截断：过长 JSON 容易触发讯飞 400 RequestParamsError
        compact_profile = {
            k: profile.get(k)
            for k in ("major", "grade", "goal", "knowledge_level", "learning_style",
                      "coding_ability", "interests", "weakness")
            if profile.get(k)
        }
        compact_stage = {
            k: stage.get(k)
            for k in ("title", "stage_id", "knowledge_points", "recommended_resources")
            if stage.get(k) is not None
        }
        kb_brief = [
            {"id": h.get("evidence_id", f"E{i+1}"), "text": str(h.get("text", ""))[:180]}
            for i, h in enumerate(knowledge_base_hits[:3])
        ]
        force = list(force_tools or [])
        prompt = self._load_prompt(self.PROMPT_PATH).format(
            profile=json.dumps(compact_profile, ensure_ascii=False),
            stage=json.dumps(compact_stage, ensure_ascii=False),
            generated_summary=json.dumps(
                {
                    "generated_tools": list(generated.keys()),
                    "quality_scores": quality_scores,
                    "regen_counts": regen_counts,
                    "force_tools": force,
                    "force_mode": force_mode,
                },
                ensure_ascii=False,
            ),
            knowledge_base_hits=json.dumps(kb_brief, ensure_ascii=False),
            fix_hints=json.dumps((fix_hints or [])[:5], ensure_ascii=False),
        )
        # 再砍一刀：总长控制在 ~6k 字符内
        if len(prompt) > 6000:
            prompt = prompt[:5800] + "\n\n请只输出 JSON 决策。"

        try:
            response = await self._call_llm(prompt)
            raw = extract_json(response)
            decision = self.validate(raw)
            if decision:
                # force 约束：优先/只做 force_tools，禁止 LLM 绕开
                decision = self._apply_force(decision, force, force_mode)
                if decision:
                    log.info(f"Supervisor 决策: tool={decision['tool']}, reasoning={decision['reasoning'][:60]}")
                    return decision
            log.warning(f"Supervisor 决策校验失败，回退默认计划: {raw}")
        except Exception as e:
            log.warning(f"Supervisor LLM 决策失败，回退默认计划: {e}")

        return self.default_plan(
            profile, stage, generated, quality_scores, regen_counts, fix_hints,
            force_tools=force, force_mode=force_mode,
        )

    @staticmethod
    def _apply_force(
        decision: Dict[str, Any],
        force_tools: List[str],
        force_mode: bool,
    ) -> Optional[Dict[str, Any]]:
        """force 模式下改写/否决 LLM 决策，保证点名资源一定生成"""
        if force_mode:
            if not force_tools:
                return {
                    "reasoning": "用户点名资源已全部完成",
                    "action": "done",
                    "tool": None,
                    "params": {},
                }
            target = force_tools[0]
            if decision.get("action") == "generate" and decision.get("tool") == target:
                return decision
            return {
                "reasoning": f"用户点名补生成 {target}，优先执行",
                "action": "generate",
                "tool": target,
                "params": decision.get("params") or {"fix_hints": [], "use_grounding": True},
            }
        # 非 force：若 LLM 选了 force 列表外的工具但 force 非空，强制先做 force
        if force_tools and decision.get("action") == "generate" and decision.get("tool") not in force_tools:
            target = force_tools[0]
            return {
                "reasoning": f"用户点名 {target} 未完成，优先执行",
                "action": "generate",
                "tool": target,
                "params": decision.get("params") or {"fix_hints": [], "use_grounding": True},
            }
        return decision

    def validate(self, raw: Any) -> Optional[Dict[str, Any]]:
        """决策 schema + 白名单校验；非法返回 None"""
        if not isinstance(raw, dict):
            return None
        action = raw.get("action")
        if action == "done":
            return {
                "reasoning": str(raw.get("reasoning", ""))[:200],
                "action": "done",
                "tool": None,
                "params": {},
            }
        if action != "generate":
            return None
        tool = raw.get("tool")
        if tool not in TOOLS:
            return None
        params = raw.get("params")
        if not isinstance(params, dict):
            params = {}
        # fix_hints 只接受字符串列表
        hints = params.get("fix_hints")
        if isinstance(hints, list):
            params["fix_hints"] = [str(h) for h in hints if h][:10]
        else:
            params["fix_hints"] = []
        return {
            "reasoning": str(raw.get("reasoning", ""))[:200],
            "action": "generate",
            "tool": tool,
            "params": params,
        }

    # ── 确定性默认计划（LLM 不可用时的兜底）─────────────────

    def default_plan(
        self,
        profile: Dict[str, Any],
        stage: Dict[str, Any],
        generated: Dict[str, Any],
        quality_scores: Dict[str, float],
        regen_counts: Dict[str, int],
        fix_hints: List[str],
        force_tools: Optional[List[str]] = None,
        force_mode: bool = False,
    ) -> Dict[str, Any]:
        """按画像适配的固定优先级生成计划；全部达标则 done

        force_tools：用户点名要生成的类型（画像跳过后补生成 / 单资源重生）。
        force_mode=True 时只做 force_tools，做完立即 done。
        """
        force = list(force_tools or [])
        threshold = DEFAULT_QUALITY_THRESHOLD

        # ── force 优先：点名资源必须先做 ──
        if force:
            tool = force[0]
            return self._gen(tool, f"用户点名补生成/重生成 {tool}（覆盖画像偏好）")
        if force_mode:
            return {
                "reasoning": "用户点名资源已全部完成",
                "action": "done",
                "tool": None,
                "params": {},
            }

        def _needs(tool: str) -> bool:
            score = quality_scores.get(tool)
            if tool not in generated:
                return True
            if score is not None and score < threshold and regen_counts.get(tool, 0) < MAX_REGEN:
                return True
            return False

        # 质量不达标的优先重做
        for tool in TOOLS:
            score = quality_scores.get(tool)
            if tool in generated and score is not None and score < threshold and regen_counts.get(tool, 0) < MAX_REGEN:
                return self._gen(tool, f"{tool} 质量 {score} 分未达标，重做", fix_hints)

        # 必做资源
        for tool in REQUIRED_TOOLS:
            if _needs(tool):
                return self._gen(tool, f"本阶段必做资源 {tool} 尚未生成或未达标")

        # 画像适配的扩展资源
        style = str(profile.get("learning_style", "") or "")
        coding = str(profile.get("coding_ability", "") or "")
        recommended = stage.get("recommended_resources") or stage.get("recommended_resource_types") or []

        adaptive_order: List[str] = []
        if "视频" in style:
            adaptive_order += ["ppt_video"]
        if "实践" in style or "动手" in style or coding in ("中级", "熟练", "精通"):
            adaptive_order += ["code"]
        if "文档" in style:
            adaptive_order += ["reading_material", "glossary"]
        # 阶段推荐兜底
        for t in recommended:
            if t in TOOLS and t not in adaptive_order:
                adaptive_order.append(t)
        # 其余类型默认收尾生成
        for t in ["mindmap", "knowledge_link", "summary"]:
            if t not in adaptive_order:
                adaptive_order.append(t)

        for tool in adaptive_order:
            if _needs(tool):
                return self._gen(tool, f"按画像/阶段推荐生成 {tool}")

        # 缺口收尾：画像未点名、阶段也未推荐，但仍缺失的类型不自动铺满——
        # 留给用户 force 补生成（如「看文档」学生日后要点视频）。

        return {
            "reasoning": "本阶段资源已齐备且质量达标",
            "action": "done",
            "tool": None,
            "params": {},
        }

    def _gen(self, tool: str, reasoning: str, fix_hints: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "reasoning": reasoning,
            "action": "generate",
            "tool": tool,
            "params": {"fix_hints": fix_hints or [], "use_grounding": True},
        }

    # ── 知识库接地检索 ─────────────────────────────────────

    async def retrieve_grounding(
        self, user_id: int, query: str, top_k: int = 4
    ) -> List[Dict[str, str]]:
        """检索学生个人知识库；空库/失败时返回 []（调用方走纯 LLM 降级）"""
        try:
            from app.rag.retriever import RAGRetriever
            retriever = RAGRetriever(top_k=top_k, use_rerank=True)
            docs = await retriever.retrieve_smart(query, user_id=user_id, top_k=top_k)
            hits = []
            for i, doc in enumerate(docs):
                meta = getattr(doc, "metadata", {}) or {}
                # 只允许命中本人知识库
                if meta.get("user_id") is not None and meta.get("user_id") != user_id:
                    continue
                hits.append({
                    "evidence_id": f"E{i + 1}",
                    "text": (doc.page_content or "")[:500],
                    "source": str(meta.get("source", "knowledge_base")),
                })
            return hits
        except Exception as e:
            log.warning(f"知识库接地检索失败（降级为无接地）: {e}")
            return []
