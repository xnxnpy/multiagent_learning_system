from sqlalchemy import Column, BigInteger, String, DateTime, JSON, ForeignKey, Text, Index, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class LearningResource(Base):
    """学习资源模型 — 存储 AI 生成的文档、思维导图、代码示例"""
    __tablename__ = "learning_resources"
    __table_args__ = (
        Index("ix_lr_user_type_created", "user_id", "resource_type", "created_at"),
        Index("ix_lr_user_stage_type_created", "user_id", "stage_id", "resource_type", "created_at"),
        Index("uk_lr_res_profile_stage_type_topic", "user_id", "profile_id", "stage_id", "resource_type", "topic", unique=True),
    )

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    profile_id = Column(BigInteger, ForeignKey("student_profiles.id"), nullable=True, index=True)
    stage_id = Column(BigInteger, nullable=True, comment="所属学习阶段 ID，null 表示不限阶段")
    resource_type = Column(String(30), nullable=False)  # document / mindmap / code
    topic = Column(String(200), nullable=False)
    content = Column(JSON, nullable=False)  # 存储完整资源内容
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="learning_resources")
    profile = relationship("StudentProfile", backref="learning_resources")
