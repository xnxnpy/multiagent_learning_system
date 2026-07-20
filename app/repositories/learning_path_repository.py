from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base_repository import BaseRepository
from app.models import LearningPath


class LearningPathRepository(BaseRepository):
    """学习路径仓库"""

    def __init__(self):
        super().__init__(LearningPath)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: int
    ) -> List[LearningPath]:
        """根据用户 ID 获取学习路径列表"""
        result = await db.execute(
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .order_by(LearningPath.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_by_user_id(
        self, db: AsyncSession, user_id: int, profile_id: int = None
    ) -> Optional[LearningPath]:
        """获取用户最新的学习路径"""
        query = select(LearningPath).where(LearningPath.user_id == user_id)
        if profile_id:
            query = query.where(LearningPath.profile_id == profile_id)
        result = await db.execute(
            query.order_by(LearningPath.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_for_user(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        stages: List[dict],
        profile_id: int = None,
    ) -> LearningPath:
        """为用户创建学习路径"""
        path_data = {
            "user_id": user_id,
            "profile_id": profile_id,
            "title": title,
            "stages": stages
        }
        return await self.create(db, obj_in=path_data)

    async def update_stages(
        self, db: AsyncSession, path_id: int, stages: List[dict]
    ) -> Optional[LearningPath]:
        """更新学习路径阶段"""
        path = await self.get(db, path_id)
        if path:
            path.stages = stages
            await db.commit()
            await db.refresh(path)
        return path

    async def update_progress(
        self, db: AsyncSession, path_id: int, current_stage: int
    ) -> Optional[LearningPath]:
        """更新学习路径进度"""
        path = await self.get(db, path_id)
        if path:
            if not hasattr(path, 'current_stage'):
                path.current_stage = current_stage
            else:
                path.current_stage = current_stage
            await db.commit()
            await db.refresh(path)
        return path

    async def delete_by_user_id(self, db: AsyncSession, user_id: int) -> bool:
        """删除用户的所有学习路径"""
        result = await db.execute(
            select(LearningPath).where(LearningPath.user_id == user_id)
        )
        paths = list(result.scalars().all())
        for path in paths:
            await db.delete(path)
        await db.commit()
        return True
