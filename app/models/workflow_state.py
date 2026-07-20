from sqlalchemy import Column, BigInteger, String, DateTime, JSON, func
from app.models.base import Base


class WorkflowState(Base):
    """工作流状态持久化模型"""
    __tablename__ = "workflow_states"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    state_data = Column(JSON, nullable=False, comment="工作流状态 JSON")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
