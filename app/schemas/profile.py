from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProfileBase(BaseModel):
    """学生画像基础模型"""
    major: Optional[str] = Field(None, description="专业")
    grade: Optional[str] = Field(None, description="年级")
    goal: Optional[str] = Field(None, description="学习目标")
    knowledge_level: Optional[Dict[str, float]] = Field(None, description="知识掌握程度")
    learning_style: Optional[str] = Field(None, description="学习风格")
    weakness: Optional[List[str]] = Field(None, description="薄弱点")
    interests: Optional[List[str]] = Field(None, description="兴趣方向")
    coding_ability: Optional[str] = Field(None, description="编程能力")


class ProfileCreate(ProfileBase):
    """学生画像创建模型"""
    user_id: int = Field(..., description="用户ID")


class ProfileUpdate(BaseModel):
    """学生画像更新模型"""
    major: Optional[str] = None
    grade: Optional[str] = None
    goal: Optional[str] = None
    knowledge_level: Optional[Dict[str, float]] = None
    learning_style: Optional[str] = None
    weakness: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    coding_ability: Optional[str] = None


class ProfileResponse(ProfileBase):
    """学生画像响应模型"""
    id: int
    user_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileBuildRequest(BaseModel):
    """构建画像请求模型"""
    user_input: str = Field(..., description="用户输入的自然语言描述")
    current_profile: Optional[Dict[str, Any]] = Field(None, description="当前画像（用于更新）")


class ProfileBuildResponse(BaseModel):
    """构建画像响应模型"""
    profile: ProfileResponse
    updated_fields: List[str] = Field(default_factory=list, description="更新的字段列表")


class ProfileStatsResponse(BaseModel):
    """画像统计响应模型"""
    total_profiles: int
    average_knowledge_level: float
    common_weakness: List[str]
    learning_style_distribution: Dict[str, int]
