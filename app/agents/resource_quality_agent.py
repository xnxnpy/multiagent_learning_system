from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log


class ResourceQualityAgent(BaseAgent):
    agent_name = "resource_quality"
    """资源质量评估 Agent - 自动评估AI生成资源的质量"""

    PROMPT_PATH = "prompts/resource_quality_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, resource_type: str, content: Any, user_id: int = None) -> Dict[str, Any]:
        log.info(f"ResourceQualityAgent 开始评估资源质量: topic='{topic}', type='{resource_type}'")

        profile_context = ""
        if user_id and self.db:
            profile = await self._get_profile(user_id)
            if profile:
                profile_context = f"- 专业：{profile.get('major', '未知')}\n- 知识水平：{profile.get('knowledge_level', '未知')}"

        content_preview = self._extract_preview(content)

        prompt = self._load_prompt(self.PROMPT_PATH)
        prompt = self._format_prompt(
            prompt,
            topic=topic,
            resource_type=resource_type,
            content_preview=content_preview,
            profile_context=profile_context or "无画像信息"
        )

        response = await self._call_llm(prompt)
        result = extract_json(response)

        if not result or not isinstance(result, dict):
            log.warning("ResourceQualityAgent JSON 提取失败，使用规则评估兜底")
            result = self._rule_based_evaluate(content_preview, resource_type)

        result = self._ensure_fields(result)
        log.info(f"ResourceQualityAgent 完成，综合评分: {result['overall_score']}，等级: {result['grade']}")
        return result

    def _extract_preview(self, content: Any, max_length: int = 1000) -> str:
        if isinstance(content, str):
            return content[:max_length]
        if isinstance(content, dict):
            text = content.get("content", "") or content.get("mindmap_markdown", "") or str(content)
            return text[:max_length]
        return str(content)[:max_length]

    def _ensure_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        defaults = {
            "relevance": 75, "completeness": 75, "personalization": 70,
            "accuracy": 80, "difficulty_fit": 75,
            "overall_score": 74, "grade": "C+", "suggestions": []
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default

        result["overall_score"] = round(
            result["relevance"] * 0.25 +
            result["completeness"] * 0.25 +
            result["personalization"] * 0.15 +
            result["accuracy"] * 0.20 +
            result["difficulty_fit"] * 0.15
        )
        result["grade"] = self._score_to_grade(result["overall_score"])
        return result

    def _score_to_grade(self, score: int) -> str:
        if score >= 95: return "A+"
        if score >= 90: return "A"
        if score >= 85: return "B+"
        if score >= 80: return "B"
        if score >= 75: return "C+"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

    def _rule_based_evaluate(self, content_preview: str, resource_type: str) -> Dict[str, Any]:
        length = len(content_preview)
        has_heading = any(line.strip().startswith("#") for line in content_preview.split("\n") if line.strip())

        relevance = 80 if length > 100 else 60
        completeness = 85 if has_heading and length > 200 else 65
        personalization = 70
        accuracy = 78
        difficulty_fit = 75

        return {
            "relevance": relevance, "completeness": completeness,
            "personalization": personalization, "accuracy": accuracy,
            "difficulty_fit": difficulty_fit,
            "suggestions": ["基于规则的自动评估，建议结合人工审核"]
        }

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        from app.models import StudentProfile
        from sqlalchemy import select
        try:
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            profile = result.scalar_one_or_none()
            if profile:
                return {"major": profile.major or "", "knowledge_level": profile.knowledge_level or ""}
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None
