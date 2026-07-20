from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Text, func
from app.models.base import Base


class KnowledgeDocument(Base):
    """知识库文档模型 — 存储上传文件的元数据和处理状态"""
    __tablename__ = "knowledge_documents"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    file_type = Column(String(20), nullable=False, comment="文件类型：pdf/docx/txt/md")
    status = Column(String(20), nullable=False, default="processing", comment="processing/completed/failed")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    error_message = Column(Text, nullable=True, comment="处理失败时的错误信息")
    uploaded_by = Column(BigInteger, nullable=False, comment="上传者用户 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="处理完成时间")
