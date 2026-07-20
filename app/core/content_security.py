"""内容安全：敏感词过滤管理"""
from typing import Dict, List
from app.core.logger import log


class ContentSecurity:
    """敏感词过滤管理器（单例）"""

    CONFIG_ENABLED = "content_security_enabled"
    CONFIG_WORDS = "content_security_words"
    CONFIG_LOGS = "content_security_logs"

    DEFAULT_WORDS: Dict[str, List[str]] = {
        "政治": [],
        "暴力": [],
        "色情": [],
        "自定义": [],
    }

    def __init__(self):
        self._enabled = False
        self._words: Dict[str, List[str]] = dict(self.DEFAULT_WORDS)
        self._loaded = False

    async def load_from_db(self, db=None):
        if db is None:
            from app.models import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await self._load(db)
        else:
            await self._load(db)

    async def _load(self, db):
        from app.services.config_service import ConfigService
        cs = ConfigService(db)
        enabled = await cs.get(self.CONFIG_ENABLED)
        if enabled is not None:
            self._enabled = bool(enabled)
        words = await cs.get(self.CONFIG_WORDS)
        if words and isinstance(words, dict):
            self._words.update(words)
        self._loaded = True
        log.info(f"内容安全已加载: enabled={self._enabled}, 词库={sum(len(v) for v in self._words.values())}个")

    def is_enabled(self) -> bool:
        return self._enabled

    def check(self, text: str) -> List[str]:
        """检测文本中的敏感词，返回命中的词列表"""
        if not self._enabled or not text:
            return []
        text_lower = text.lower()
        hits = []
        for category, word_list in self._words.items():
            for word in word_list:
                if word.lower() in text_lower:
                    hits.append(word)
        return hits

    def get_all_words(self) -> Dict[str, List[str]]:
        return dict(self._words)

    async def set_enabled(self, enabled: bool, db):
        self._enabled = enabled
        from app.services.config_service import ConfigService
        await ConfigService(db).set(self.CONFIG_ENABLED, enabled, "内容安全开关")

    async def update_words(self, category: str, words: List[str], db):
        if category not in self._words:
            self._words[category] = []
        self._words[category] = words
        from app.services.config_service import ConfigService
        await ConfigService(db).set(self.CONFIG_WORDS, self._words, "内容安全词库")

    async def add_words(self, category: str, new_words: List[str], db):
        if category not in self._words:
            self._words[category] = []
        added = [w for w in new_words if w not in self._words[category]]
        self._words[category].extend(added)
        from app.services.config_service import ConfigService
        await ConfigService(db).set(self.CONFIG_WORDS, self._words, "内容安全词库")
        return added

    async def remove_word(self, category: str, word: str, db):
        if category in self._words and word in self._words[category]:
            self._words[category].remove(word)
            from app.services.config_service import ConfigService
            await ConfigService(db).set(self.CONFIG_WORDS, self._words, "内容安全词库")
            return True
        return False

    async def add_log(self, entry: dict, db):
        from app.services.config_service import ConfigService
        cs = ConfigService(db)
        logs = await cs.get(self.CONFIG_LOGS) or []
        if not isinstance(logs, list):
            logs = []
        logs.insert(0, entry)
        logs = logs[:500]  # 最多保留 500 条
        await cs.set(self.CONFIG_LOGS, logs, "内容安全过滤记录")

    async def get_logs(self, db, page: int = 1, size: int = 20):
        from app.services.config_service import ConfigService
        logs = await ConfigService(db).get(self.CONFIG_LOGS) or []
        if not isinstance(logs, list):
            logs = []
        total = len(logs)
        start = (page - 1) * size
        return logs[start:start + size], total


content_security = ContentSecurity()
