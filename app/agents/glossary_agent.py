from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json, normalize_resource_content
from app.core.logger import log


class GlossaryAgent(BaseAgent):
    agent_name = "glossary"
    """术语词汇卡片 Agent - 生成结构化的术语列表"""

    PROMPT_PATH = "prompts/glossary_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, user_id: int = None) -> Dict[str, Any]:
        log.info(f"GlossaryAgent 开始为主题 '{topic}' 生成术语词汇卡片")

        if user_id and self.db:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)
        response = await self._call_llm(prompt)

        result = extract_json(response)
        if not result or not isinstance(result, dict) or "terms" not in result:
            log.warning("GlossaryAgent JSON 提取失败，使用 mock 兜底")
            result = self._get_mock_glossary(topic, profile)

        result = normalize_resource_content(result, "glossary")
        log.info(f"GlossaryAgent 完成，生成 {len(result.get('terms', []))} 个术语")
        return result

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        from app.models import StudentProfile
        try:
            result = await self.db.execute(
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
                    "interests": profile.interests or []
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        from app.models import LearningResource
        result = await self.db.execute(
            select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "glossary",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            content = record.content
            if isinstance(content, dict):
                content = normalize_resource_content(content, "glossary")
            return content
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        template = self._load_prompt(self.PROMPT_PATH)
        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            level = profile.get("knowledge_level", "未知")
            profile_context = f"""
## 学生画像信息（用于个性化生成）
- 知识水平：{level}
- 薄弱点：{weakness_str}

**请根据知识水平调整术语难度分布**
"""
        else:
            profile_context = ""
        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    def _get_mock_glossary(self, topic: str, profile: Dict = None) -> Dict[str, Any]:
        return {
            "topic": topic,
            "terms": [
                {"term": f"{topic}基础概念", "definition": f"{topic}的核心定义", "example": f"在{topic}中，这个概念被广泛使用", "related_terms": [], "difficulty": "基础"},
                {"term": f"{topic}核心原理", "definition": f"{topic}的基本工作原理", "example": f"理解{topic}原理有助于深入学习", "related_terms": [f"{topic}基础概念"], "difficulty": "进阶"},
                {"term": f"{topic}高级应用", "definition": f"{topic}在实际场景中的高级用法", "example": f"企业级项目中{topic}的高级应用", "related_terms": [f"{topic}核心原理"], "difficulty": "高级"}
            ]
        }
