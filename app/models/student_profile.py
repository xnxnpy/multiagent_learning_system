from sqlalchemy import Column, BigInteger, String, DateTime, func, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base


class StudentProfile(Base):
    """学生画像模型"""
    __tablename__ = "student_profiles"

    id              = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id         = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    profile_name    = Column(String(100), nullable=False, default="默认画像")
    is_active       = Column(Boolean, default=True, index=True)
    is_archived     = Column(Boolean, default=False, index=True)
    archived_at     = Column(DateTime(timezone=True), nullable=True)
    major           = Column(String(100))
    grade           = Column(String(50))
    goal            = Column(String(500))
    knowledge_level = Column(String(50))
    learning_style  = Column(String(100))
    weakness        = Column(JSON)
    interests       = Column(JSON)
    coding_ability  = Column(String(50))
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    user = relationship("User", back_populates="student_profiles")
