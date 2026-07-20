"""
系统配置服务 - 读写数据库中的配置
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_config import SystemConfig
from app.core.logger import log


class ConfigService:
    """系统配置服务"""

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self._cache: Dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 先查内存缓存
        if key in self._cache:
            return self._cache[key]

        if not self.db:
            return default

        try:
            result = await self.db.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            record = result.scalar_one_or_none()
            if record:
                try:
                    value = json.loads(record.config_value)
                except:
                    value = record.config_value
                self._cache[key] = value
                return value
        except Exception as e:
            log.warning(f"读取配置 {key} 失败: {e}")

        return default

    async def set(self, key: str, value: Any, description: str = None):
        """设置配置值"""
        if not self.db:
            return

        try:
            value_str = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)

            result = await self.db.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            record = result.scalar_one_or_none()

            if record:
                record.config_value = value_str
                if description:
                    record.description = description
            else:
                record = SystemConfig(
                    config_key=key,
                    config_value=value_str,
                    description=description
                )
                self.db.add(record)

            await self.db.commit()
            self._cache[key] = value
            log.info(f"配置已保存: {key}")
        except Exception as e:
            log.error(f"保存配置 {key} 失败: {e}")
            await self.db.rollback()

    async def get_all(self, prefix: str = None) -> Dict[str, Any]:
        """获取所有配置"""
        if not self.db:
            return {}

        try:
            query = select(SystemConfig)
            if prefix:
                query = query.where(SystemConfig.config_key.like(f"{prefix}%"))

            result = await self.db.execute(query)
            records = result.scalars().all()

            configs = {}
            for record in records:
                try:
                    value = json.loads(record.config_value)
                except:
                    value = record.config_value
                configs[record.config_key] = value
                self._cache[record.config_key] = value

            return configs
        except Exception as e:
            log.error(f"读取配置失败: {e}")
            return {}

    def clear_cache(self):
        """清除内存缓存"""
        self._cache.clear()


# 默认配置键名
CONFIG_KEYS = {
    "agent_text_models": "各Agent使用的文本模型配置",
    "image_task_models": "图片任务使用的模型配置",
    "video_task_models": "视频任务使用的模型配置",
}
