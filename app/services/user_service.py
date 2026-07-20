from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import NotFoundException, ConflictException, UnauthorizedException
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """用户服务"""

    def __init__(self):
        self.user_repo = UserRepository()

    async def get_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        user = await self.user_repo.get(db, user_id)
        if not user:
            raise NotFoundException(detail=f"User with id {user_id} not found")
        return user

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await self.user_repo.get_by_username(db, username)

    async def create_user(
        self, db: AsyncSession, user_data: UserCreate
    ) -> User:
        """创建用户"""
        existing_user = await self.user_repo.get_by_username(db, user_data.username)
        if existing_user:
            raise ConflictException(detail="Username already registered")

        user = await self.user_repo.create_with_password(
            db,
            username=user_data.username,
            password=user_data.password,
            role=user_data.role,
            email=user_data.email,
            real_name=user_data.real_name,
        )
        return user

    async def update_user(
        self, db: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User:
        """更新用户"""
        user = await self.get_by_id(db, user_id)
        update_data = user_data.model_dump(exclude_unset=True)
        return await self.user_repo.update(db, db_obj=user, obj_in=update_data)

    async def change_password(
        self, db: AsyncSession, user_id: int, old_password: str, new_password: str
    ) -> User:
        """修改密码"""
        user = await self.get_by_id(db, user_id)

        if not verify_password(old_password, user.password_hash):
            raise UnauthorizedException(detail="Incorrect old password")

        user.password_hash = get_password_hash(new_password)
        await db.commit()
        await db.refresh(user)
        return user

    async def delete_user(self, db: AsyncSession, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_by_id(db, user_id)
        await self.user_repo.remove(db, id=user_id)
        return True

    async def get_users_paginated(
        self, db: AsyncSession, skip: int = 0, limit: int = 10, search: str = None
    ) -> tuple[List[User], int]:
        """分页获取用户列表"""
        query = select(User)

        if search:
            query = query.where(
                User.username.ilike(f"%{search}%") |
                User.real_name.ilike(f"%{search}%") |
                User.email.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit).order_by(User.id.desc())
        result = await db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def authenticate(
        self, db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """用户认证"""
        user = await self.user_repo.get_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


user_service = UserService()
