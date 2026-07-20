from sqlalchemy import Column, BigInteger, String, DateTime, JSON, ForeignKey, Float, Index, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class EvaluationReport(Base):
    """学习评估报告模型"""
    __tablename__ = "evaluation_reports"
    __table_args__ = (
        Index("ix_er_user_created", "user_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    overall_grade = Column(String(10), nullable=True)
    total_score = Column(Float, nullable=True)
    accuracy_rate = Column(Float, nullable=True)
    mastery_level = Column(Float, nullable=True)
    report_data = Column(JSON, nullable=False)  # 完整评估报告 JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="evaluation_reports")
