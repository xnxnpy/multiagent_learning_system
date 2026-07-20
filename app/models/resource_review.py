from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class ResourceReview(Base):
    """资源审核模型"""
    __tablename__ = "resource_reviews"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    resource_type = Column(String(50), nullable=False)  # document, mindmap, video, code
    resource_content = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    creator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
