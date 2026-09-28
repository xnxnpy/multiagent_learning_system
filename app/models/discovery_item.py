from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, func
from app.models.base import Base


class DiscoveryItem(Base):
    """学习发现收藏 — 学生保存的外部资源（按 user_id 隔离）"""
    __tablename__ = "discovery_items"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    url = Column(String(1000), nullable=False)
    type = Column(String(20), nullable=False, default="article", comment="video/article/paper/repo")
    summary = Column(Text, nullable=True)
    source = Column(String(120), nullable=True, comment="来源站点")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
