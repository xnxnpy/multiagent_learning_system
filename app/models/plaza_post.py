from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, func
from app.models.base import Base


class PlazaPost(Base):
    """学习广场帖子（社区分享）"""
    __tablename__ = "plaza_posts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(200), nullable=True)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PlazaLike(Base):
    """点赞去重：user_id + post_id 唯一语义由应用层保证"""
    __tablename__ = "plaza_likes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    post_id = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
