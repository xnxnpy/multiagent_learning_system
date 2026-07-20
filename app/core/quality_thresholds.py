"""资源质量阈值管理"""
from typing import Dict
from app.core.logger import log

# 各资源类型的默认质量阈值（低于此分数不展示给学生）
DEFAULT_THRESHOLDS: Dict[str, int] = {
    "document": 60,
    "mindmap": 60,
    "code": 70,
    "question": 70,
    "reading_material": 60,
    "glossary": 60,
    "knowledge_link": 50,
    "summary": 60,
    "ppt_video": 60,
}

CONFIG_KEY = "quality_thresholds"


class QualityThresholds:
    """资源质量阈值管理器（单例）"""

    def __init__(self):
        self._thresholds: Dict[str, int] = dict(DEFAULT_THRESHOLDS)
        self._loaded = False

    async def load_from_db(self, db=None):
        """从 SystemConfig 加载阈值"""
        if db is None:
            from app.models import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await self._load(db)
        else:
            await self._load(db)

    async def _load(self, db):
        from app.services.config_service import ConfigService
        config_service = ConfigService(db)
        saved = await config_service.get(CONFIG_KEY)
        if saved and isinstance(saved, dict):
            self._thresholds.update(saved)
        self._loaded = True
        log.info(f"质量阈值已加载: {self._thresholds}")

    async def update(self, new_thresholds: Dict[str, int], db=None):
        """更新阈值（内存 + DB）"""
        self._thresholds.update(new_thresholds)
        if db:
            from app.services.config_service import ConfigService
            config_service = ConfigService(db)
            await config_service.set(CONFIG_KEY, self._thresholds, "资源质量阈值配置")
            log.info(f"质量阈值已保存: {self._thresholds}")

    def get_threshold(self, resource_type: str) -> int:
        """获取指定资源类型的阈值"""
        return self._thresholds.get(resource_type, 60)

    def get_all(self) -> Dict[str, int]:
        """获取所有阈值"""
        return dict(self._thresholds)


# 全局实例
quality_thresholds = QualityThresholds()
