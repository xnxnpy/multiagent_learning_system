"""智能辅导 Agent - LangChain 版本

纯 RAG Agent，只负责检索 + 生成。
对话上下文管理由 TutorContextManager 统一处理。
"""
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
from operator import itemgetter

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from app.core.model_manager import ModelManagerChatModel
from app.core.logger import log
from app.rag.retriever import retriever


class TutorAgent:
    agent_name = "tutor"
    """纯 RAG Agent — 检索文档 + 构建 Prompt + 调用 LLM"""

    PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../prompts/tutor_prompt.txt")

    def __init__(self):
        self._rag_chain = None
        self._llm = ModelManagerChatModel(agent_name="tutor")

    @property
    def rag_chain(self):
        """懒加载 RAG 链（LCEL）

        链结构:
            question → retriever → format_docs  ─┐
            question ─────────────────────────────┤
            history  ─────────────────────────────┼→ prompt → llm → StrOutputParser
            profile  (内嵌于 system prompt)  ─────┘
        """
        if self._rag_chain is None:
            self._rag_chain = (
                {
                    "context": itemgetter("question") | retriever | RunnableLambda(self._format_docs),
                    "question": itemgetter("question"),
                    "history": itemgetter("history"),
                }
                | RunnableLambda(self._build_messages)
                | self._llm
                | StrOutputParser()
            )
            log.info("RAG 链（LCEL）初始化完成")
        return self._rag_chain

    # ── 公开接口 ────────────────────────────────────────────

    async def run_stream(
        self, user_id: int, question: str, history: Optional[List[BaseMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """流式执行辅导对话"""
        log.info(f"TutorAgent 流式处理用户 {user_id} 的问题: '{question[:50]}'")

        profile = await self._get_profile(user_id)

        # 快速检查知识库是否有文档，避免空库时走 RAG 浪费时间
        has_docs = await self._check_knowledge_base()
        full_answer = ""

        if has_docs:
            # 有知识库：走 RAG 链
            rag_input = {
                "question": question,
                "history": history or [],
                "profile": profile,
            }
            full_answer = ""
            async for chunk in self.rag_chain.astream(rag_input):
                text = chunk if isinstance(chunk, str) else getattr(chunk, 'text', str(chunk))
                full_answer += text
                yield text
        else:
            # 无知识库：直接用 LLM 回答
            system_prompt = self._load_system_prompt()
            profile_text = self._format_profile(profile)
            system_prompt = system_prompt.replace("{student_context}", profile_text)
            system_prompt = system_prompt.replace("{context}", "（知识库暂无相关资料，以下为通用回答）")

            messages = [
                {"role": "system", "content": system_prompt},
            ]
            # 添加历史
            for msg in (history or []):
                role = "assistant" if isinstance(msg, AIMessage) else "user"
                messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": question})

            from app.core.model_manager import model_manager
            async for chunk in model_manager.chat_stream(messages, agent_name="tutor"):
                full_answer += chunk
                yield chunk

        log.info(f"TutorAgent 流式完成，回答长度: {len(full_answer)}")

    # ── 内部方法 ────────────────────────────────────────────

    def _build_messages(self, data: Dict) -> List[BaseMessage]:
        """构建 LangChain 消息列表"""
        system_template = self._load_system_prompt()
        profile = data.get("profile", {})
        profile_text = self._format_profile(profile)

        raw_context = data.get("context", [])
        context_text = self._format_docs(raw_context)

        system_content = system_template
        system_content = system_content.replace("{student_context}", profile_text)
        system_content = system_content.replace("{context}", context_text)

        messages = [AIMessage(content=system_content)]
        messages.extend(data.get("history", []))
        messages.append(HumanMessage(content=data["question"]))
        return messages

    @staticmethod
    def _format_profile(profile: Dict) -> str:
        if not profile:
            return "暂无学生信息"
        weakness_str = ", ".join(profile.get("weakness", [])) or "无"
        interests_str = ", ".join(profile.get("interests", [])) or "无"
        return f"""
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade', '未知')}
- 知识水平：{profile.get('knowledge_level', '未知')}
- 学习风格：{profile.get('learning_style', '未知')}
- 学习目标：{profile.get('goal', '未知')}
- 薄弱点：{weakness_str}
- 兴趣方向：{interests_str}

**请根据学生画像调整回答**：根据知识水平调整解释深度，使用专业相关案例，重点讲解薄弱点。
""".strip()

    @staticmethod
    def _format_docs(docs) -> str:
        if not docs:
            return "（暂无相关参考资料）"
        doc_strings = []
        for i, doc in enumerate(docs):
            if hasattr(doc, 'page_content'):
                doc_strings.append(f"【文档 {i+1}】\n{doc.page_content}")
            elif isinstance(doc, str):
                doc_strings.append(f"【文档 {i+1}】\n{doc}")
            elif isinstance(doc, dict):
                doc_strings.append(f"【文档 {i+1}】\n{doc.get('page_content', doc.get('document', ''))}")
            else:
                doc_strings.append(f"【文档 {i+1}】\n{str(doc)}")
        return "\n\n".join(doc_strings)

    def _load_system_prompt(self) -> str:
        default_prompt = (
            "你是一位专业的学习辅导老师，擅长为学生提供深入浅出的解答。\n\n"
            "## 回答规则\n"
            "1. 使用中文回答，语言亲切友好\n"
            "2. 分步讲解复杂问题\n"
            "3. 提供代码示例（如适用）\n"
            "4. 参考提供的文档回答问题\n\n"
            "## 参考资料\n{context}\n\n"
            "## 学生信息\n{student_context}\n\n"
            "请开始回答用户的问题。"
        )
        try:
            if os.path.exists(self.PROMPT_PATH):
                with open(self.PROMPT_PATH, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                log.warning(f"Prompt 文件不存在: {self.PROMPT_PATH}，使用默认 prompt")
                return default_prompt
        except Exception as e:
            log.warning(f"加载 prompt 文件失败: {e}，使用默认 prompt")
            return default_prompt

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
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

    async def _check_knowledge_base(self) -> bool:
        """快速检查知识库是否有文档"""
        try:
            from app.vectorstore.chroma_store import vector_store
            collection = vector_store.get_collection()
            count = collection.count()
            return count > 0
        except Exception:
            return False


# 全局单例
tutor_agent = TutorAgent()
