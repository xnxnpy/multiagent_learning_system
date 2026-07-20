from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.core.logger import log


class ReadingMaterialAgent(BaseAgent):
    agent_name = "reading_material"
    """拓展阅读材料 Agent - 生成Markdown格式的扩展阅读文章"""

    PROMPT_PATH = "prompts/reading_material_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, user_id: int = None) -> Dict[str, Any]:
        log.info(f"ReadingMaterialAgent 开始为主题 '{topic}' 生成拓展阅读材料")

        if user_id and self.db:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)
        content = await self._call_llm(prompt)

        if not content or len(content.strip()) < 100:
            log.warning("ReadingMaterialAgent LLM 返回内容过短，使用 mock 兜底")
            content = self._get_mock_reading_material(topic, profile)

        result = {"topic": topic, "content": content, "type": "reading_material"}
        log.info(f"ReadingMaterialAgent 完成，内容长度: {len(content)} 字符")
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
                LearningResource.resource_type == "reading_material",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            return record.content
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        template = self._load_prompt(self.PROMPT_PATH)
        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            interests_str = ", ".join(profile.get("interests", [])) or "无"
            profile_context = f"""
## 学生画像信息（用于个性化生成）
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade', '未知')}
- 知识水平：{profile.get('knowledge_level', '未知')}
- 学习风格：{profile.get('learning_style', '未知')}
- 学习目标：{profile.get('goal', '未知')}
- 薄弱点：{weakness_str}
- 兴趣方向：{interests_str}

**请根据学生画像调整内容深度和案例选择**
"""
        else:
            profile_context = ""
        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    def _get_mock_reading_material(self, topic: str, profile: Dict = None) -> str:
        major = profile.get("major", "计算机科学") if profile else "计算机科学"
        return f"""# {topic}：深入探索

## 导读
本文将帮助你从更广阔的视角理解 {topic} 的核心概念与实际应用。

## 1. 基础回顾
{topic} 是 {major} 领域的重要基础知识。在掌握了基本概念之后，让我们进一步探讨其深层原理。

## 2. 前沿进展
近年来，{topic} 在工业界和学术界都有广泛应用。例如在人工智能、大数据分析等方向。

## 3. 实际应用案例
以 {major} 为例，{topic} 可以应用于数据分析、系统设计、算法优化等场景。

## 4. 延伸阅读
- 深入学习 {topic} 的高级特性
- 了解 {topic} 在实际项目中的最佳实践
- 探索 {topic} 与其他技术的结合

## 思考题
1. 请结合你的专业方向，思考 {topic} 可以解决哪些实际问题？
2. 如果要向非技术人员解释 {topic}，你会如何描述？
"""
