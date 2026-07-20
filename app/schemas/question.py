from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class QuestionType(str, Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    CODING = "coding"
    CASE_ANALYSIS = "case_analysis"


class QuestionDifficulty(str, Enum):
    """题目难度枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionOption(BaseModel):
    """选择题选项模型"""
    id: str
    content: str
    is_correct: bool = False


class QuestionBase(BaseModel):
    """题目基础模型"""
    type: QuestionType = Field(..., description="题目类型")
    difficulty: QuestionDifficulty = Field(..., description="题目难度")
    content: str = Field(..., description="题目内容")
    options: Optional[List[QuestionOption]] = Field(None, description="选项（选择题）")
    correct_answer: Optional[str] = Field(None, description="正确答案")
    explanation: Optional[str] = Field(None, description="答案解析")
    test_code: Optional[str] = Field(None, description="测试代码（编程题）")
    knowledge_points: List[str] = Field(default_factory=list, description="关联知识点")


class QuestionCreate(QuestionBase):
    """题目创建模型"""
    pass


class QuestionResponse(QuestionBase):
    """题目响应模型"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionSubmitRequest(BaseModel):
    """提交答案请求模型"""
    question_id: int = Field(..., description="题目ID")
    user_answer: str = Field(..., description="用户答案")
    duration_seconds: Optional[int] = Field(None, description="答题耗时（秒）")


class QuestionSubmitResponse(BaseModel):
    """提交答案响应模型"""
    question_id: int
    is_correct: bool
    score: float
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    feedback: Optional[str] = None


class QuestionGenerateRequest(BaseModel):
    """生成题目请求模型"""
    topic: str = Field(..., description="知识点/主题")
    count: int = Field(default=5, ge=1, le=20, description="生成数量")
    question_types: List[QuestionType] = Field(
        default=[QuestionType.SINGLE_CHOICE],
        description="题目类型列表"
    )
    difficulty: QuestionDifficulty = Field(
        default=QuestionDifficulty.MEDIUM,
        description="题目难度"
    )
    knowledge_points: List[str] = Field(default_factory=list, description="具体知识点")


class QuestionGenerateResponse(BaseModel):
    """生成题目响应模型"""
    questions: List[QuestionResponse]
    total_count: int


class QuestionBatchSubmitRequest(BaseModel):
    """批量提交答案请求模型"""
    answers: List[QuestionSubmitRequest]


class QuestionBatchSubmitResponse(BaseModel):
    """批量提交答案响应模型"""
    results: List[QuestionSubmitResponse]
    total_score: float
    correct_count: int
    total_count: int


class QuestionStats(BaseModel):
    """题目统计模型"""
    total_attempts: int
    correct_count: int
    accuracy: float
    average_duration: float
    common_mistakes: List[str]
