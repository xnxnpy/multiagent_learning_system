"""智能辅导 Tutor Agent — ReAct 子图

Think → Act（白名单工具）→ Observe（事实冻结）→ 循环 ≤4 轮 → Answer（引用校验）

防幻觉五层：
1. 行动空间封闭：action 只能取 TOOLS 白名单
2. 引用编号代码校验：最终回答的 [En] 必须来自本轮真实检索
3. 循环硬上限 4 轮
4. Observation 冻结：工具结果原样注入，LLM 不可改写
5. 校验失败降级：去掉非法引用 + 显式标注资料边界
"""
import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from app.core.model_manager import ModelManagerChatModel, model_manager
from app.core.logger import log
from app.rag.retriever import retriever as default_retriever

# 行动白名单
TOOLS = {
    "search_rag",
    "search_knowledge_graph",
    "get_student_record",
    "generate_question",
    "answer_directly",
}

MAX_ROUNDS = 4


class TutorAgent:
    agent_name = "tutor"

    PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../prompts/tutor_react_prompt.txt")
    LEGACY_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../prompts/tutor_prompt.txt")

    def __init__(self):
        self._llm = ModelManagerChatModel(agent_name="tutor")

    # ── 公开接口（保持原签名，API 层无感升级）──────────────

    async def run_stream(
        self, user_id: int, question: str, history: Optional[List[BaseMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """ReAct 式流式辅导：循环思考行动，最终流式输出经引用校验的回答"""
        log.info(f"TutorAgent ReAct 处理用户 {user_id}: '{question[:50]}'")

        try:
            profile = await self._get_profile(user_id)
            async for chunk in self._react_loop(user_id, question, history or [], profile):
                yield chunk
        except Exception as e:
            log.error(f"ReAct 循环异常，降级为直接回答: {e}")
            async for chunk in self._fallback_stream(question, history or []):
                yield chunk

    # ── ReAct 主循环 ──────────────────────────────────────

    async def _react_loop(
        self,
        user_id: int,
        question: str,
        history: List[BaseMessage],
        profile: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        # 证据库：本轮所有工具返回（Observation 冻结）
        evidence: List[Dict[str, str]] = []
        thought_history: List[str] = []
        last_answer = ""

        for round_idx in range(1, MAX_ROUNDS + 1):
            decision = await self._think(question, history, profile, thought_history, evidence)
            action = decision.get("action")
            action_input = decision.get("action_input") or {}
            thought = str(decision.get("thought", ""))[:200]
            thought_history.append(f"[R{round_idx}] {thought} → {action}")

            log.info(f"Tutor ReAct R{round_idx}: action={action}, thought={thought[:60]}")

            # ── 最终回答 ──
            if action == "answer_directly":
                answer = str(action_input.get("answer", "")).strip()
                if not answer:
                    answer = last_answer or "抱歉，我暂时无法回答这个问题。"
                last_answer = answer

                verified, ok = self._verify_citations(answer, evidence)
                if not ok and evidence:
                    # 重试一次：带着校验失败原因重新生成
                    answer = await self._regenerate_with_correction(
                        question, profile, evidence, answer
                    )
                    verified, ok = self._verify_citations(answer, evidence)
                if not ok:
                    verified = self._degrade_answer(answer, evidence)

                async for chunk in self._stream_final(question, profile, verified, evidence):
                    yield chunk
                return

            # ── 行动 + 观察 ──
            if action not in TOOLS:
                # 白名单外：注入纠正 Observation，让下一轮重选
                thought_history.append(f"[R{round_idx}] 非法工具 {action}，已拒绝")
                continue

            observation = await self._act(action, action_input, user_id)
            evidence.append({
                "id": f"E{len(evidence) + 1}",
                "text": observation[:800],
                "source": action,
            })

        # 4 轮未 answer_directly：强制收束
        log.info(f"Tutor ReAct 达到 {MAX_ROUNDS} 轮上限，强制生成回答")
        answer = await self._force_answer(question, profile, evidence)
        verified, ok = self._verify_citations(answer, evidence)
        if not ok:
            verified = self._degrade_answer(answer, evidence)
        async for chunk in self._stream_final(question, profile, verified, evidence):
            yield chunk

    # ── Think：LLM 决策（非流式，输出 JSON）────────────────

    async def _think(
        self,
        question: str,
        history: List[BaseMessage],
        profile: Dict,
        thought_history: List[str],
        evidence: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        prompt = self._load_react_prompt().format(
            student_context=self._format_profile(profile),
            history=self._format_history(history),
            thought_history="\n".join(thought_history) or "（尚无）",
            evidence=self._format_evidence(evidence) or "（尚无检索结果）",
            question=question,
        )
        try:
            raw = await model_manager.chat(
                [{"role": "user", "content": prompt}], agent_name="tutor"
            )
            decision = self._parse_decision(raw)
            if decision:
                return decision
            log.warning(f"ReAct 决策解析失败: {raw[:200]}")
        except Exception as e:
            log.warning(f"ReAct think 失败: {e}")

        # 决策失败兜底：有证据则直接回答，无证据先检索
        if evidence:
            return {
                "thought": "决策解析失败，基于已有证据直接回答",
                "action": "answer_directly",
                "action_input": {"answer": self._compose_from_evidence(evidence)},
            }
        return {
            "thought": "决策解析失败，先检索知识库",
            "action": "search_rag",
            "action_input": {"query": question},
        }

    def _parse_decision(self, raw: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 决策 JSON；action 必须在白名单内"""
        from app.agents.utils import extract_json
        data = extract_json(raw)
        if not isinstance(data, dict):
            return None
        action = data.get("action")
        if action not in TOOLS:
            return None
        action_input = data.get("action_input")
        if not isinstance(action_input, dict):
            action_input = {}
        return {
            "thought": str(data.get("thought", "")),
            "action": action,
            "action_input": action_input,
        }

    # ── Act：执行白名单工具 ───────────────────────────────

    async def _act(self, action: str, action_input: Dict, user_id: int) -> str:
        """执行工具并返回冻结的 Observation 文本"""
        try:
            if action == "search_rag":
                return await self._tool_search_rag(user_id, action_input.get("query") or "")
            if action == "search_knowledge_graph":
                return await self._tool_search_kg(user_id, action_input.get("knowledge_point") or "")
            if action == "get_student_record":
                return await self._tool_student_record(user_id)
            if action == "generate_question":
                return await self._tool_generate_question(user_id, action_input.get("topic") or "")
        except Exception as e:
            log.warning(f"工具 {action} 执行失败: {e}")
            return f"工具 {action} 执行失败：{e}"
        return f"未知工具 {action}"

    async def _tool_search_rag(self, user_id: int, query: str) -> str:
        if not query.strip():
            return "未提供检索词。"
        try:
            # 智能检索：查询改写 + 多路召回 + 用户隔离 + 质量过滤
            docs = await default_retriever.retrieve_smart(query, user_id=user_id, top_k=4)
        except Exception as e:
            return f"知识库检索失败：{e}"
        hits = []
        for doc in docs:
            meta = getattr(doc, "metadata", {}) or {}
            text = (getattr(doc, "page_content", "") or "")[:400]
            if text:
                hits.append(f"[E{len(hits) + 1}] {text}")
        if not hits:
            return "知识库中未找到相关内容（可能尚未上传教材，或该问题超出资料范围）。"
        return "\n\n".join(hits)

    async def _tool_search_kg(self, user_id: int, knowledge_point: str) -> str:
        try:
            from app.core.neo4j_client import KnowledgeGraphStore
            graph = await KnowledgeGraphStore.get_graph(user_id)
            nodes = graph.get("nodes") or []
            edges = graph.get("edges") or []
            if not nodes:
                return "知识图谱为空，尚未生成。"
            if not knowledge_point:
                labels = [n.get("label", "") for n in nodes[:20]]
                return "知识图谱节点（前20）：" + "、".join(labels)
            matched = [n for n in nodes if knowledge_point in str(n.get("label", ""))]
            if not matched:
                return f"知识图谱中未找到「{knowledge_point}」相关节点。"
            related = []
            mids = {m.get("id") for m in matched}
            for e in edges:
                if e.get("source") in mids or e.get("target") in mids:
                    related.append(f"{e.get('source')} -[{e.get('relationship')}]-> {e.get('target')}")
            return (
                f"匹配节点：{[m.get('label') for m in matched[:5]]}\n"
                f"关联关系（前10）：\n" + "\n".join(related[:10] or ["（无关联边）"])
            )
        except Exception as e:
            return f"知识图谱查询失败（Neo4j 可能未启动）：{e}"

    async def _tool_student_record(self, user_id: int) -> str:
        try:
            from sqlalchemy import select, func
            from app.models import AsyncSessionLocal, QuestionItem, EvaluationReport

            async with AsyncSessionLocal() as db:
                wrong = await db.execute(
                    select(func.count()).select_from(QuestionItem).where(
                        QuestionItem.user_id == user_id,
                        QuestionItem.wrong_book_status == "active",
                    )
                )
                wrong_cnt = wrong.scalar() or 0

                kp = await db.execute(
                    select(QuestionItem.knowledge_point, func.count())
                    .where(
                        QuestionItem.user_id == user_id,
                        QuestionItem.wrong_book_status == "active",
                    )
                    .group_by(QuestionItem.knowledge_point)
                )
                kp_map = {k or "通用": c for k, c in kp.all()}

                ev = await db.execute(
                    select(EvaluationReport)
                    .where(EvaluationReport.user_id == user_id)
                    .order_by(EvaluationReport.created_at.desc())
                    .limit(1)
                )
                report = ev.scalar_one_or_none()

            parts = [f"错题本待重练：{wrong_cnt} 题"]
            if kp_map:
                parts.append("薄弱知识点：" + "、".join(f"{k}({v})" for k, v in kp_map.items()))
            if report and report.report_data:
                rd = report.report_data
                parts.append(
                    f"最近评估：{rd.get('overall_grade', '未知')}，"
                    f"正确率 {rd.get('accuracy_rate', 0):.0%}，"
                    f"掌握度 {rd.get('mastery_level', 0):.0%}"
                )
                weak = (rd.get("analysis") or {}).get("weaknesses") or []
                if weak:
                    parts.append("评估指出的薄弱点：" + "、".join(weak[:5]))
            return "\n".join(parts)
        except Exception as e:
            return f"学习记录查询失败：{e}"

    async def _tool_generate_question(self, user_id: int, topic: str) -> str:
        if not topic.strip():
            return "未提供出题主题。"
        try:
            from app.agents.question_agent import QuestionAgent
            from app.models import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                agent = QuestionAgent(db)
                result = await agent.run(topic, user_id=user_id)
            questions = (result or {}).get("questions") or []
            if not questions:
                return "题目生成失败或为空。"
            q = questions[0]
            opts = q.get("options") or []
            text = f"练习题：{q.get('question', '')}\n"
            for i, o in enumerate(opts):
                text += f"{chr(65 + i)}. {o}\n"
            text += f"答案：{q.get('answer', '（见解析）')}"
            if q.get("explanation"):
                text += f"\n解析：{q['explanation']}"
            return text[:600]
        except Exception as e:
            return f"题目生成失败：{e}"

    # ── 引用校验与降级（防幻觉核心）────────────────────────

    def _verify_citations(self, answer: str, evidence: List[Dict[str, str]]) -> Tuple[str, bool]:
        """校验回答中的 [En] 引用必须真实存在；无证据时剥离所有引用"""
        refs = re.findall(r"\[(E\d+)\]", answer)
        if not evidence:
            # 无证据：剥离伪造引用
            cleaned = re.sub(r"\s*\[E\d+\]", "", answer).strip()
            return cleaned, True
        if not refs:
            return answer, False  # 有证据但未引用 → 不通过
        valid_ids = {e["id"] for e in evidence}
        invalid = [r for r in refs if r not in valid_ids]
        if invalid:
            return answer, False
        return answer, True

    def _degrade_answer(self, answer: str, evidence: List[Dict[str, str]]) -> str:
        """校验最终失败：去掉非法引用，显式标注资料边界"""
        cleaned = re.sub(r"\s*\[E\d+\]", "", answer).strip()
        if evidence:
            preview = evidence[0]["text"][:120]
            return (
                f"（以下回答基于系统检索到的有限资料，未能完成严格引用校验）\n\n"
                f"{cleaned}\n\n"
                f"——检索资料摘录：{preview}…"
            )
        return (
            "（知识库暂无相关教材，以下为通用知识回答）\n\n"
            f"{cleaned}"
        )

    async def _regenerate_with_correction(
        self, question: str, profile: Dict, evidence: List[Dict], bad_answer: str
    ) -> str:
        """引用校验失败后的一次纠正重试"""
        prompt = (
            f"你是辅导老师。请基于给定证据重新回答，回答中每个引用论断后必须标注 [E编号]，"
            f"编号只能使用给定证据中真实存在的编号。\n\n"
            f"## 学生问题\n{question}\n\n"
            f"## 证据\n{self._format_evidence(evidence)}\n\n"
            f"## 上次回答（引用编号无效，不要重复其错误）\n{bad_answer[:500]}\n\n"
            f"请输出修正后的完整回答（直接输出正文，不要 JSON）。"
        )
        try:
            return await model_manager.chat(
                [{"role": "user", "content": prompt}], agent_name="tutor"
            )
        except Exception:
            return bad_answer

    async def _force_answer(
        self, question: str, profile: Dict, evidence: List[Dict]
    ) -> str:
        """4 轮上限后的强制收束回答"""
        prompt = (
            f"你是辅导老师。请基于以下证据回答学生问题，引用处标注 [E编号]。\n\n"
            f"## 学生画像\n{self._format_profile(profile)}\n\n"
            f"## 证据\n{self._format_evidence(evidence) or '（无检索证据）'}\n\n"
            f"## 问题\n{question}\n\n直接输出回答正文。"
        )
        try:
            return await model_manager.chat(
                [{"role": "user", "content": prompt}], agent_name="tutor"
            )
        except Exception:
            return self._compose_from_evidence(evidence) or "抱歉，我暂时无法回答这个问题。"

    def _compose_from_evidence(self, evidence: List[Dict[str, str]]) -> str:
        if not evidence:
            return ""
        lines = ["根据检索到的资料："]
        for e in evidence[:3]:
            lines.append(f"- {e['text'][:200]}[{e['id']}]")
        return "\n".join(lines)

    # ── 最终回答流式输出 ───────────────────────────────────

    async def _stream_final(
        self, question: str, profile: Dict, answer: str, evidence: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """将已校验的回答流式输出（保持逐块体验）"""
        # 分块模拟流式（回答已在服务端定稿，引用已校验）
        step = 24
        for i in range(0, len(answer), step):
            yield answer[i: i + step]

    # ── 降级：ReAct 整体失败时的旧 RAG 直答 ──────────────────

    async def _fallback_stream(
        self, question: str, history: List[BaseMessage]
    ) -> AsyncGenerator[str, None]:
        system = (
            "你是一位专业的学习辅导老师。系统检索暂不可用，请基于通用知识谨慎回答，"
            "并在开头说明「以下为通用回答」。"
        )
        messages = [{"role": "system", "content": system}]
        for msg in history[-8:]:
            role = "assistant" if isinstance(msg, AIMessage) else "user"
            messages.append({"role": role, "content": msg.content})
        messages.append({"role": "user", "content": question})
        async for chunk in model_manager.chat_stream(messages, agent_name="tutor"):
            yield chunk

    # ── Prompt / 上下文格式化 ──────────────────────────────

    def _load_react_prompt(self) -> str:
        try:
            if os.path.exists(self.PROMPT_PATH):
                with open(self.PROMPT_PATH, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            log.warning(f"加载 ReAct prompt 失败: {e}")
        return (
            "你是辅导 Tutor。通过 JSON 决策下一步行动，action ∈ "
            f"{sorted(TOOLS)}。输出："
            '{{"thought":"...","action":"search_rag","action_input":{{"query":"..."}}}}\n'
            "学生问题：{question}\n证据：{evidence}"
        )

    @staticmethod
    def _format_profile(profile: Dict) -> str:
        if not profile:
            return "暂无学生信息"
        weakness_str = ", ".join(profile.get("weakness", [])) or "无"
        interests_str = ", ".join(profile.get("interests", [])) or "无"
        return (
            f"- 专业：{profile.get('major', '未知')}\n"
            f"- 年级：{profile.get('grade', '未知')}\n"
            f"- 知识水平：{profile.get('knowledge_level', '未知')}\n"
            f"- 学习风格：{profile.get('learning_style', '未知')}\n"
            f"- 学习目标：{profile.get('goal', '未知')}\n"
            f"- 薄弱点：{weakness_str}\n"
            f"- 兴趣方向：{interests_str}"
        )

    @staticmethod
    def _format_history(history: List[BaseMessage]) -> str:
        if not history:
            return "（无）"
        lines = []
        for msg in history[-6:]:
            role = "学生" if isinstance(msg, HumanMessage) else "老师"
            lines.append(f"{role}：{str(msg.content)[:120]}")
        return "\n".join(lines)

    @staticmethod
    def _format_evidence(evidence: List[Dict[str, str]]) -> str:
        if not evidence:
            return ""
        return "\n\n".join(f"{e['id']}（来源 {e['source']}）：{e['text']}" for e in evidence)

    async def _get_profile(self, user_id: Optional[int]) -> Optional[Dict[str, Any]]:
        if not user_id:
            return {}
        from app.models import StudentProfile, AsyncSessionLocal
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(StudentProfile).where(
                        StudentProfile.user_id == user_id,
                        StudentProfile.is_active == True,
                    )
                )
                profile = result.scalar_one_or_none()
                if profile:
                    return {
                        "major": profile.major or "",
                        "grade": profile.grade or "",
                        "goal": profile.goal or "",
                        "knowledge_level": profile.knowledge_level or "",
                        "learning_style": profile.learning_style or "",
                        "weakness": profile.weakness or [],
                        "interests": profile.interests or [],
                    }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return {}


# 全局单例
tutor_agent = TutorAgent()
