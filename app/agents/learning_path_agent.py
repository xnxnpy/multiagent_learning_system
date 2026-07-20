import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log
from app.models import StudentProfile, LearningPath


class LearningPathAgent(BaseAgent):
    agent_name = "learning_path"
    """学习路径规划 Agent"""

    PROMPT_PATH = "prompts/learning_path_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, user_id: int, profile: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行学习路径规划任务
        
        Args:
            user_id: 用户 ID
            profile: 可选，用户画像数据，不传则从数据库读取
        
        Returns:
            学习路径数据
        """
        log.info(f"LearningPathAgent 开始为用户 {user_id} 规划学习路径")

        if not profile:
            profile = await self._get_profile_from_db(user_id)
        
        if not profile:
            raise ValueError(f"用户 {user_id} 没有画像数据，请先构建画像")

        profile_json = json.dumps(profile, ensure_ascii=False)
        prompt = self._load_and_format_prompt(profile_json)
        response = await self._call_llm(prompt)
        
        path_data = extract_json(response)

        if not path_data or not isinstance(path_data, dict):
            log.warning(f"LearningPathAgent JSON 提取失败，使用 mock 数据兜底")
            path_data = self._get_mock_path(profile)

        await self._save_path(user_id, path_data)

        log.info(f"LearningPathAgent 完成，用户 {user_id} 的学习路径已保存")
        return path_data

    async def _get_profile_from_db(self, user_id: int) -> Optional[Dict[str, Any]]:
        """从数据库获取用户画像"""
        if not self.db:
            return None
        
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
                "interests": profile.interests or [],
                "weakness": profile.weakness or [],
                "coding_ability": profile.coding_ability or ""
            }
        return None

    def _load_and_format_prompt(self, profile_json: str) -> str:
        """加载并格式化 Prompt"""
        template = self._load_prompt(self.PROMPT_PATH)
        return self._format_prompt(template, profile_json=profile_json)


    def _get_mock_path(self, profile: Dict) -> Dict[str, Any]:
        """LLM 失败时构造基础学习路径"""
        goal = profile.get("goal", "Python 编程学习") if profile else "Python 编程学习"
        return {
            "title": f"{goal}学习路径",
            "stages": [
                {
                    "stage_id": 1,
                    "title": "基础入门",
                    "description": f"学习{goal}的基本概念和语法",
                    "knowledge_points": ["基本概念", "环境搭建", "基础语法"],
                    "recommended_resources": ["document", "video_script"]
                },
                {
                    "stage_id": 2,
                    "title": "进阶提高",
                    "description": f"深入学习{goal}的核心特性",
                    "knowledge_points": ["核心特性", "面向对象", "异常处理"],
                    "recommended_resources": ["document", "code", "question"]
                },
                {
                    "stage_id": 3,
                    "title": "实战应用",
                    "description": f"通过项目巩固{goal}知识",
                    "knowledge_points": ["项目实战", "综合运用"],
                    "recommended_resources": ["code", "question"]
                }
            ]
        }

    async def _save_path(self, user_id: int, path_data: Dict[str, Any], profile_id: int = None):
        """保存学习路径到数据库（upsert）"""
        if not self.db:
            log.warning("数据库连接未设置，跳过保存")
            return

        from app.models.upsert import upsert as mysql_upsert

        # 如果没传 profile_id，查活跃画像
        if not profile_id:
            from app.models import StudentProfile
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            prof = result.scalar_one_or_none()
            profile_id = prof.id if prof else None

        stages = path_data.get("stages", [])
        title = self._generate_title(stages)

        await mysql_upsert(
            self.db, LearningPath.__table__,
            values={
                "user_id": user_id,
                "profile_id": profile_id,
                "title": title,
                "stages": stages,
                "completed_stages": [],
            },
            update_cols=["title", "stages", "completed_stages"],
        )
        await self.db.commit()
        log.info(f"学习路径已保存到数据库，用户 ID: {user_id}，profile_id: {profile_id}")

    def _generate_title(self, stages: list) -> str:
        """根据阶段生成标题"""
        if not stages:
            return "个性化学习路径"
        
        first_stage = stages[0] if stages else {}
        stage_title = first_stage.get("title", "")
        
        if "基础" in stage_title or "入门" in stage_title:
            return "从基础到进阶学习路径"
        elif "进阶" in stage_title or "高级" in stage_title:
            return "进阶提升学习路径"
        else:
            return "个性化学习路径"


# 创建全局实例
learning_path_agent = LearningPathAgent()
