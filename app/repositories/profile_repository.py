from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base_repository import BaseRepository
from app.models import StudentProfile


class ProfileRepository(BaseRepository):
    """学生画像仓库"""

    def __init__(self):
        super().__init__(StudentProfile)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: int
    ) -> Optional[StudentProfile]:
        """根据用户 ID 获取当前活跃画像"""
        result = await db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        db: AsyncSession,
        user_id: int,
        profile_data: dict
    ) -> StudentProfile:
        """创建或更新学生画像"""
        existing_profile = await self.get_by_user_id(db, user_id)
        
        if existing_profile:
            for key, value in profile_data.items():
                if hasattr(existing_profile, key):
                    setattr(existing_profile, key, value)
            await db.commit()
            await db.refresh(existing_profile)
            return existing_profile
        else:
            profile_data["user_id"] = user_id
            return await self.create(db, obj_in=profile_data)

    async def update_knowledge_level(
        self, db: AsyncSession, user_id: int, knowledge_level: dict
    ) -> Optional[StudentProfile]:
        """更新知识掌握程度"""
        profile = await self.get_by_user_id(db, user_id)
        if profile:
            profile.knowledge_level = knowledge_level
            await db.commit()
            await db.refresh(profile)
        return profile

    async def update_weakness(
        self, db: AsyncSession, user_id: int, weakness: List[str]
    ) -> Optional[StudentProfile]:
        """更新薄弱点"""
        profile = await self.get_by_user_id(db, user_id)
        if profile:
            profile.weakness = weakness
            await db.commit()
            await db.refresh(profile)
        return profile

    async def get_all_profiles(
        self, db: AsyncSession
    ) -> List[StudentProfile]:
        """获取所有学生画像"""
        result = await db.execute(select(StudentProfile))
        return list(result.scalars().all())
