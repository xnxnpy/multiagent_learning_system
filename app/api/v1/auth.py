from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import get_db, User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.user_service import user_service
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedException, BadRequestException
from app.core.logger import log
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    log.info(f"用户注册: {user_data.username}")
    user = await user_service.create_user(db, user_data)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    log.info(f"用户登录: {login_data.username}")
    user = await user_service.authenticate(db, login_data.username, login_data.password)

    if not user:
        raise UnauthorizedException(detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    log.info(f"用户 {user.username} 登录成功，token 已创建")

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户信息"""
    log.info(f"更新用户信息: {current_user.id}")
    user = await user_service.update_user(db, current_user.id, user_data)
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    log.info(f"修改密码: {current_user.id}")
    user = await user_service.change_password(
        db,
        current_user.id,
        password_data.old_password,
        password_data.new_password,
    )
    return UserResponse.model_validate(user)
