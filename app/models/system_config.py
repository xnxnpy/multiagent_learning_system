from sqlalchemy import Column, BigInteger, String, Text, DateTime, func
from app.models.base import Base


class SystemConfig(Base):
    """系统配置表 - 存储模型配置等全局设置"""
    __tablename__ = "system_config"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(String(500))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
