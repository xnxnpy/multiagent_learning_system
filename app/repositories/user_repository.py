from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base_repository import BaseRepository
from app.models import User
from app.core.security import get_password_hash


class UserRepository(BaseRepository):
    """用户仓库"""

    def __init__(self):
        super().__init__(User)

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create_with_password(
        self, db: AsyncSession, *, username: str, password: str, role: str, **kwargs
    ) -> User:
        """创建带密码哈希的用户"""
        hashed_password = get_password_hash(password)
        user_data = {
            "username": username,
            "password_hash": hashed_password,
            "role": role,
            **kwargs,
        }
        return await self.create(db, obj_in=user_data)
