from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ProfileCase(BaseModel):
    """画像案例"""
    case_id: int
    title: str
    description: str
    profile_data: Dict[str, Any]
    created_at: Optional[str] = None


class ResourceCase(BaseModel):
    """资源生成案例"""
    case_id: int
    resource_type: str
    resource_type_name: str
    topic: Optional[str] = None
    stage_id: Optional[int] = None
    knowledge_point: Optional[str] = None
    content: Dict[str, Any]
    quality_score: Optional[Dict[str, Any]] = None
    student_profile: Optional[Dict[str, Any]] = None
    target_profile: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class PathCase(BaseModel):
    """路径推荐案例"""
    case_id: int
    title: str
    student_profile_summary: Optional[str] = None
    path_stages: List[Dict[str, Any]]
    recommendation_reason: str
    match_score: Optional[float] = None
    created_at: Optional[str] = None


class TutorCase(BaseModel):
    """智能辅导案例"""
    case_id: int
    title: str
    question: str
    answer: str
    question_type: str
    resource_type_used: Optional[str] = None
    created_at: Optional[str] = None


class EvaluationCase(BaseModel):
    """学习评估案例"""
    case_id: int
    title: str
    student_profile_summary: Optional[str] = None
    student_profile: Optional[Dict[str, Any]] = None
    knowledge_point: Optional[str] = None
    evaluation_result: Dict[str, Any]
    path_adjustment: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class ShowcaseResponse(BaseModel):
    """案例展示完整响应"""
    profiles: List[ProfileCase]
    resources: List[ResourceCase]
    resources_by_student: List[Dict[str, Any]] = []
    paths: List[PathCase]
    tutor_dialogues: List[TutorCase]
    evaluations: List[EvaluationCase]
    system_info: Dict[str, Any]
