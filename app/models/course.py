from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Course(Base):
    """课程模型"""
    __tablename__ = "courses"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    teacher_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    knowledge_tree = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    teacher = relationship("User", back_populates="courses")
