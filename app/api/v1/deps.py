from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.logger import log

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前认证用户"""
    if credentials is None:
        log.warning("请求缺少 Authorization 头")
        raise UnauthorizedException(detail="Missing authorization header")

    token = credentials.credentials
    if not token:
        log.warning("Authorization header 中 token 为空")
        raise UnauthorizedException(detail="Token is empty")

    payload = decode_access_token(token)

    if payload is None:
        log.warning(f"Token 解码失败，token 前20字符: {token[:20]}...")
        raise UnauthorizedException(detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        log.warning(f"Token payload 中缺少 sub 字段: {payload}")
        raise UnauthorizedException(detail="Invalid token payload")

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        log.warning(f"Token 中 sub 字段无法转换为 int: {user_id}")
        raise UnauthorizedException(detail="Invalid token payload")

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        log.warning(f"用户不存在: user_id={user_id}")
        raise UnauthorizedException(detail="User not found")

    return user


def require_roles(allowed_roles: List[str]):
    """角色权限依赖装饰器"""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    return current_user
