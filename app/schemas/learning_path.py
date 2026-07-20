from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class KnowledgePoint(BaseModel):
    """知识点模型"""
    id: str
    name: str
    description: Optional[str] = None
    prerequisites: List[str] = Field(default_factory=list)
    estimated_hours: float = 1.0


class LearningStage(BaseModel):
    """学习阶段模型"""
    stage_id: int = Field(..., description="阶段ID")
    title: str = Field(..., description="阶段标题")
    description: str = Field(..., description="阶段描述")
    knowledge_points: List[KnowledgePoint] = Field(default_factory=list)
    recommended_resource_types: List[str] = Field(
        default_factory=list,
        description="推荐资源类型: document, question, mindmap, video, code"
    )
    estimated_hours: float = Field(..., description="预估学习时间（小时）")
    difficulty: str = Field(default="medium", description="难度: easy, medium, hard")


class LearningPathBase(BaseModel):
    """学习路径基础模型"""
    title: str = Field(..., description="路径标题")
    stages: List[LearningStage] = Field(default_factory=list)


class LearningPathCreate(BaseModel):
    """学习路径创建模型"""
    title: str = Field(..., description="路径标题")
    profile_id: int = Field(..., description="关联的画像ID")


class LearningPathUpdate(BaseModel):
    """学习路径更新模型"""
    title: Optional[str] = None
    stages: Optional[List[LearningStage]] = None
    current_stage: Optional[int] = None


class LearningPathResponse(LearningPathBase):
    """学习路径响应模型"""
    id: int
    user_id: int
    current_stage: Optional[int] = None
    completed_stages: List[int] = Field(default_factory=list, description="已完成的 stage_id 列表")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LearningPathGenerateRequest(BaseModel):
    """生成学习路径请求模型"""
    topic: str = Field(..., description="学习主题")
    knowledge_level: Optional[str] = Field("beginner", description="当前知识水平")
    learning_goal: Optional[str] = Field(None, description="学习目标")


class LearningPathGenerateResponse(BaseModel):
    """生成学习路径响应模型"""
    path: LearningPathResponse
    generated_stages: List[LearningStage]


class LearningPathProgressUpdate(BaseModel):
    """学习路径进度更新模型"""
    current_stage: int = Field(..., description="当前阶段")
    completed_resources: List[str] = Field(default_factory=list, description="已完成的资源ID")


class LearningPathStats(BaseModel):
    """学习路径统计模型"""
    total_stages: int
    completed_stages: int
    total_estimated_hours: float
    completed_hours: float
    progress_percentage: float
