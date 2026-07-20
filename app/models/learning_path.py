from sqlalchemy import Column, BigInteger, String, DateTime, func, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class LearningPath(Base):
    """学习路径模型"""
    __tablename__ = "learning_paths"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_id", name="uk_lp_user_profile"),
    )

    id              = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id         = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    profile_id      = Column(BigInteger, ForeignKey("student_profiles.id"), nullable=True, index=True)
    title           = Column(String(255))
    stages          = Column(JSON)
    completed_stages = Column(JSON, default=list, comment="已完成的 stage_id 列表")
    path_version    = Column(BigInteger, default=1, comment="路径版本号，每次更新 +1")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    user = relationship("User", back_populates="learning_paths")
    profile = relationship("StudentProfile", backref="learning_paths")
