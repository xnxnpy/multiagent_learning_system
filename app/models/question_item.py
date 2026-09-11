"""题库与错题本模型

题目从 learning_resources 的 JSON 中提升为一等公民：
- 重生成资源不再误删答题历史（修复 student.py 旧逻辑）
- 错题本 = 最近一次作答错误的题目视图，支持重练与移出
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, JSON, Float, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class QuestionItem(Base):
    """题库条目：一道题的稳定身份（跨资源重生成存活）"""
    __tablename__ = "question_items"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    profile_id = Column(BigInteger, ForeignKey("student_profiles.id"), nullable=True)
    stage_id = Column(BigInteger, nullable=True)
    # 稳定题目标识（生成时分配；同一题重练不变）
    question_uid = Column(String(64), nullable=False, unique=True, index=True)
    knowledge_point = Column(String(200), nullable=True)
    difficulty = Column(String(20), nullable=True)
    question_type = Column(String(30), nullable=True)  # choice / fill / coding / case
    question_data = Column(JSON, nullable=False)       # 完整题面（options/answer/rubric...）
    # 最近一次作答状态
    last_correct = Column(Boolean, nullable=True)
    last_score = Column(Float, nullable=True)
    attempt_count = Column(BigInteger, default=0)
    # 错题本状态：active=在错题本；mastered=重练正确后移出；removed=手动移出
    wrong_book_status = Column(String(20), default=None, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_qi_user_kp", "user_id", "knowledge_point"),
        Index("ix_qi_user_wrong", "user_id", "wrong_book_status"),
    )

    user = relationship("User")
