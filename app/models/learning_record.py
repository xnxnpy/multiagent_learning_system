from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class LearningRecord(Base):
    """学习记录模型"""
    __tablename__ = "learning_records"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)  # document, question, mindmap, video, code
    resource_id = Column(BigInteger, nullable=True)
    correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    behavior_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    user = relationship("User", back_populates="learning_records")
