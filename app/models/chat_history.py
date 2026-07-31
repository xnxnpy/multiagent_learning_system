from sqlalchemy import Column, BigInteger, String, DateTime, Text, func, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMTEXT
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
    content = Column(Text, nullable=False, comment="给大模型用的完整内容（含 OCR 文本）")
    display_content = Column(Text, nullable=True, comment="给用户显示的原始输入（不含 OCR 文本）")
    image_base64 = Column(MEDIUMTEXT, nullable=True, comment="用户上传的题目图片 base64（仅 role=user 时有值）")
    image_name = Column(String(255), nullable=True, comment="图片文件名")
    image_size = Column(BigInteger, nullable=True, comment="图片文件大小（字节）")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
