from sqlalchemy import Column, BigInteger, String, DateTime, Text, func, ForeignKey
from app.models.base import Base


class ProfileChatMessage(Base):
    """个人画像聊天消息模型"""
    __tablename__ = "profile_chat_messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    profile_id = Column(BigInteger, ForeignKey("student_profiles.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TutorChatMessage(Base):
    """智能辅导聊天消息模型"""
    __tablename__ = "tutor_chat_messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
