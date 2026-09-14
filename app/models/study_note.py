"""学习笔记模型 — 知识沉淀层

学生在学习/辅导过程中可将内容沉淀为笔记；
笔记进入个人知识库（ChromaDB），后续 Tutor/资源生成可检索引用。
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class StudyNote(Base):
    __tablename__ = "study_notes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    profile_id = Column(BigInteger, ForeignKey("student_profiles.id"), nullable=True)
    stage_id = Column(BigInteger, nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    # 来源：manual=手写 / tutor=辅导沉淀 / resource=资源摘录
    source = Column(String(20), default="manual")
    tags = Column(String(500), default="")  # 逗号分隔
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_sn_user", "user_id", "updated_at"),
    )

    user = relationship("User")
