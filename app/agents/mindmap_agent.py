"""思维导图生成 Agent"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log


class MindmapAgent(BaseAgent):
    """思维导图生成 Agent"""

    agent_name = "mindmap"
    PROMPT_PATH = "prompts/mindmap_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, user_id: int = None, skip_cache: bool = False) -> Dict[str, Any]:
        log.info(f"MindmapAgent 开始为主题 '{topic}' 生成思维导图")

        if user_id and self.db and not skip_cache:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)

        result = None
        for attempt in range(2):
            response = await self._call_llm(prompt)
            result = extract_json(response)
            if result and isinstance(result, dict) and "mindmap_markdown" in result:
                break
            if attempt == 0:
                log.warning("MindmapAgent JSON 提取失败，尝试重新生成")

        if not result or not isinstance(result, dict):
            log.warning("MindmapAgent JSON 提取失败，使用 mock 数据兜底")
            result = self._get_mock(topic)

        if "mindmap_markdown" in result and result["mindmap_markdown"]:
            result["mindmap_markdown"] = self._ensure_markdown_format(result["mindmap_markdown"])
        else:
            result["mindmap_markdown"] = ""

        if result["mindmap_markdown"]:
            result["mindmap_html"] = self._markdown_to_markmap_html(result["mindmap_markdown"])
        else:
            result["mindmap_html"] = ""

        log.info("MindmapAgent 完成")
        return result

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        from app.models import LearningResource
        result = await self.db.execute(
            select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "mindmap",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        return record.content if record else None

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

**请根据学生画像调整内容**：
- 思维导图重点展示学生的薄弱点
- 使用学生专业相关的案例场景
"""
        else:
            profile_context = ""
        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    def _get_mock(self, topic: str) -> Dict[str, Any]:
        mock_md = (
            f"# {topic}\n"
            f"## 核心概念\n- 基本定义\n- 关键术语\n"
            f"## 基础语法\n- 语法要点\n- 常见用法\n"
            f"## 实践应用\n- 案例分析\n- 练习"
        )
        return {"mindmap_markdown": mock_md, "mindmap_html": self._markdown_to_markmap_html(mock_md)}

    def _ensure_markdown_format(self, md: str) -> str:
        lines = md.strip().split('\n')
        has_heading = any(line.strip().startswith('#') for line in lines if line.strip())
        if has_heading:
            return md
        non_empty = [line.strip() for line in lines if line.strip()]
        if not non_empty:
            return md
        result_lines = [f"# {non_empty[0]}"]
        for line in non_empty[1:]:
            cleaned = line.lstrip('- *•').strip()
            if cleaned:
                result_lines.append(f"## {cleaned}")
        log.info("mindmap_markdown 缺少标题格式，已自动转换")
        return '\n'.join(result_lines)

    def _markdown_to_markmap_html(self, md: str) -> str:
        escaped_md = md.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>思维导图</title>
  <style>
    html, body {{ margin: 0; padding: 0; height: 100%; }}
    .markmap {{ width: 100%; height: 100vh; }}
  </style>
</head>
<body>
  <div class="markmap">
    <script type="text/template">
{escaped_md}
    </script>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.15.4"></script>
</body>
</html>"""


mindmap_agent = MindmapAgent()
