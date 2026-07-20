from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.repositories.user_repository import UserRepository
from app.core.exceptions import UnauthorizedException, NotFoundException


class AuthService:
    """认证服务"""

    def __init__(self):
        self.user_repo = UserRepository()

    def create_token(self, user_id: int, username: str, role: str) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire
        }
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    def decode_token(self, token: str) -> dict:
        """解码令牌"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            raise UnauthorizedException(detail="Could not validate credentials")

    async def login(
        self, db: AsyncSession, username: str, password: str
    ) -> dict:
        """用户登录"""
        user = await self.user_repo.get_by_username(db, username)
        if not user:
            raise UnauthorizedException(detail="Incorrect username or password")
        
        if not verify_password(password, user.password_hash):
            raise UnauthorizedException(detail="Incorrect username or password")
        
        access_token = self.create_token(
            user_id=user.id,
            username=user.username,
            role=user.role
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "real_name": user.real_name
            }
        }

    async def get_current_user_from_token(
        self, db: AsyncSession, token: str
    ) -> dict:
        """从令牌获取当前用户"""
        payload = self.decode_token(token)
        user_id = int(payload.get("sub"))
        
        user = await self.user_repo.get(db, user_id)
        if not user:
            raise NotFoundException(detail="User not found")
        
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "real_name": user.real_name
        }

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return verify_password(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return get_password_hash(password)


auth_service = AuthService()
