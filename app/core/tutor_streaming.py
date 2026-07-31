"""Tutor 上下文管理器

统一管理辅导对话的 Redis 缓存 + MySQL 持久化，职责：
- 对话历史读写（Redis 优先，MySQL 兜底）
- 会话列表管理
- 会话清除
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from app.core.logger import log


MAX_CONTEXT_MESSAGES = 20
REDIS_TTL_SECONDS = 86400  # 24 小时


@dataclass
class TutorMessage:
    """对话消息数据结构"""
    role: str  # "user" or "assistant"
    content: str  # 给大模型用的完整内容（含 OCR 文本）
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    image_base64: Optional[str] = None  # 用户上传的题目图片 base64（仅 role=user 时有值）
    image_name: Optional[str] = None    # 图片文件名
    image_size: Optional[int] = None    # 图片文件大小（字节）
    display_content: Optional[str] = None  # 给用户显示的原始输入（不含 OCR 文本）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "image_base64": self.image_base64,
            "image_name": self.image_name,
            "image_size": self.image_size,
            "display_content": self.display_content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TutorMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.now()),
            metadata=data.get("metadata"),
            image_base64=data.get("image_base64"),
            image_name=data.get("image_name"),
            image_size=data.get("image_size"),
            display_content=data.get("display_content"),
        )


class TutorContextManager:
    """辅导对话上下文管理器（Redis + MySQL 双写，Redis 优先读取）"""

    def __init__(self):
        self.session_expire_time = REDIS_TTL_SECONDS

    # ── Redis key ──────────────────────────────────────────

    def _redis_key(self, session_id: str) -> str:
        return f"tutor:session:{session_id}"

    # ── 对话历史读取 ────────────────────────────────────────

    async def get_context(self, session_id: str, user_id: int) -> List[TutorMessage]:
        """获取对话上下文（Redis 优先，MySQL 兜底）"""
        from app.core.redis_client import get_redis

        # 1. 尝试 Redis
        try:
            r = await get_redis()
            if r:
                redis_data = await r.get(self._redis_key(session_id))
                if redis_data:
                    messages = self._deserialize_messages(redis_data)
                    if len(messages) > MAX_CONTEXT_MESSAGES:
                        messages = messages[-MAX_CONTEXT_MESSAGES:]
                    return messages
        except Exception as e:
            log.warning(f"Redis 读取上下文失败，降级到 MySQL: {e}")

        # 2. MySQL 兜底
        messages = await self._load_from_db(session_id, user_id)

        # 3. 回写 Redis（最佳努力）
        if messages:
            try:
                r = await get_redis()
                if r:
                    await r.set(self._redis_key(session_id), self._serialize_messages(messages), ex=self.session_expire_time)
            except Exception:
                pass

        return messages

    async def get_history_as_messages(self, session_id: str, user_id: int) -> List[BaseMessage]:
        """获取历史消息（LangChain BaseMessage 格式，供 RAG 链使用）"""
        tutor_msgs = await self.get_context(session_id, user_id)
        messages = []
        for msg in tutor_msgs:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        return messages

    async def get_history_dict(self, session_id: str) -> List[Dict[str, str]]:
        """获取历史（字典格式，供 API 返回）"""
        from app.core.redis_client import get_redis

        # 1. 尝试 Redis
        try:
            r = await get_redis()
            if r:
                history_str = await r.get(self._redis_key(session_id))
                if history_str:
                    return json.loads(history_str)
        except Exception as e:
            log.warning(f"Redis 读取历史失败，降级到 MySQL: {e}")

        # 2. MySQL 兜底
        return await self._load_history_dict_from_db(session_id)

    # ── 对话历史写入 ────────────────────────────────────────

    async def add_message(self, session_id: str, user_id: int, message: TutorMessage) -> None:
        """添加新消息（MySQL 先写，Redis 后写）"""
        from app.core.redis_client import get_redis

        # 1. 读取现有消息
        messages = None
        try:
            r = await get_redis()
            if r:
                redis_data = await r.get(self._redis_key(session_id))
                if redis_data:
                    messages = self._deserialize_messages(redis_data)
        except Exception as e:
            log.warning(f"Redis 读取消息失败，降级到 MySQL: {e}")

        if messages is None:
            messages = await self._load_from_db(session_id, user_id)

        # 2. 追加 + 裁剪
        messages.append(message)
        if len(messages) > MAX_CONTEXT_MESSAGES:
            messages = messages[-MAX_CONTEXT_MESSAGES:]

        # 3. 写 MySQL
        try:
            await self._save_to_db(session_id, user_id, message)
        except Exception as e:
            log.error(f"MySQL 写入消息失败: {e}")

        # 4. 写 Redis
        try:
            r = await get_redis()
            if r:
                await r.set(self._redis_key(session_id), self._serialize_messages(messages), ex=self.session_expire_time)
        except Exception as e:
            log.warning(f"Redis 缓存消息失败（MySQL 已保存）: {e}")

    # ── 会话列表 ────────────────────────────────────────────

    async def get_user_sessions(self, user_id: int) -> List[Dict[str, str]]:
        """获取用户的所有会话（Redis 优先，MySQL 兜底），附带首条消息预览"""
        from app.core.redis_client import get_redis

        session_ids = None
        r = None
        try:
            r = await get_redis()
            if r:
                sessions_str = await r.get(f"user_{user_id}_sessions")
                if sessions_str:
                    session_ids = json.loads(sessions_str)
        except Exception as e:
            log.warning(f"Redis 读取会话列表失败，降级到 MySQL: {e}")

        if not session_ids:
            session_ids = await self._load_session_ids_from_db(user_id)
            if session_ids and r:
                try:
                    await r.set(f"user_{user_id}_sessions", json.dumps(session_ids), ex=self.session_expire_time * 7)
                except Exception:
                    pass

        if not session_ids:
            return []

        # 获取每个会话的预览
        result = []
        for sid in session_ids:
            preview = ""
            updated_at = ""
            try:
                history = await self.get_history_dict(sid)
                for msg in history:
                    if msg.get("role") == "user":
                        preview = msg["content"][:50]
                    if msg.get("timestamp"):
                        updated_at = msg["timestamp"]
                        break
            except Exception:
                pass
            result.append({"session_id": sid, "preview": preview or "新对话", "updated_at": updated_at})
        return result

    async def update_session_list(self, user_id: int, session_id: str) -> None:
        """将会话 ID 加入用户的会话列表"""
        from app.core.redis_client import get_redis

        try:
            r = await get_redis()
            if not r:
                return
            user_key = f"user_{user_id}_sessions"
            sessions_str = await r.get(user_key)
            sessions = json.loads(sessions_str) if sessions_str else []
            if session_id not in sessions:
                sessions.append(session_id)
            await r.set(user_key, json.dumps(sessions), ex=self.session_expire_time * 7)
        except Exception as e:
            log.warning(f"Redis 更新会话列表失败: {e}")

    # ── 会话清除 ────────────────────────────────────────────

    async def clear_session(self, session_id: str, user_id: int) -> None:
        """清除指定会话（MySQL + Redis 都清理）"""
        from app.core.redis_client import get_redis

        # 1. 清 MySQL
        try:
            from app.models import TutorChatMessage, AsyncSessionLocal
            from sqlalchemy import delete as sa_delete
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(TutorChatMessage).where(TutorChatMessage.session_id == session_id)
                )
                await db.commit()
        except Exception as e:
            log.error(f"MySQL 清除会话记录失败: {e}")

        # 2. 清 Redis
        try:
            r = await get_redis()
            if not r:
                return
            await r.delete(self._redis_key(session_id))
            # 从用户会话列表中移除
            user_key = f"user_{user_id}_sessions"
            sessions_str = await r.get(user_key)
            if sessions_str:
                sessions = json.loads(sessions_str)
                if session_id in sessions:
                    sessions.remove(session_id)
                    await r.set(user_key, json.dumps(sessions), ex=self.session_expire_time * 7)
        except Exception as e:
            log.warning(f"Redis 清除会话缓存失败（MySQL 已清理）: {e}")

        log.info(f"会话 {session_id} 清理完成")

    # ── MySQL 内部方法 ──────────────────────────────────────

    async def _load_from_db(self, session_id: str, user_id: int) -> List[TutorMessage]:
        """从 MySQL 加载消息（TutorMessage 格式）"""
        try:
            from app.models import TutorChatMessage, AsyncSessionLocal
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TutorChatMessage)
                    .where(TutorChatMessage.session_id == session_id, TutorChatMessage.user_id == user_id)
                    .order_by(TutorChatMessage.id.asc())
                    .limit(MAX_CONTEXT_MESSAGES)
                )
                rows = result.scalars().all()
                return [TutorMessage(role=r.role, content=r.content, timestamp=r.created_at, image_base64=r.image_base64, image_name=getattr(r, 'image_name', None), image_size=getattr(r, 'image_size', None), display_content=getattr(r, 'display_content', None)) for r in rows]
        except Exception as e:
            log.error(f"从 MySQL 加载消息失败: {e}")
            return []

    async def _load_history_dict_from_db(self, session_id: str) -> List[Dict[str, str]]:
        """从 MySQL 加载消息（字典格式）"""
        try:
            from app.models import TutorChatMessage, AsyncSessionLocal
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TutorChatMessage)
                    .where(TutorChatMessage.session_id == session_id)
                    .order_by(TutorChatMessage.id.asc())
                    .limit(MAX_CONTEXT_MESSAGES)
                )
                rows = result.scalars().all()
                return [{"role": r.role, "content": r.content, "display_content": getattr(r, 'display_content', None), "image_base64": r.image_base64, "image_name": getattr(r, 'image_name', None), "image_size": getattr(r, 'image_size', None)} for r in rows]
        except Exception as e:
            log.error(f"从 MySQL 加载历史失败: {e}")
            return []

    async def _save_to_db(self, session_id: str, user_id: int, message: TutorMessage) -> None:
        """保存单条消息到 MySQL"""
        try:
            from app.models import TutorChatMessage, AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                db.add(TutorChatMessage(
                    user_id=user_id,
                    session_id=session_id,
                    role=message.role,
                    content=message.content,
                    display_content=message.display_content,
                    image_base64=message.image_base64,
                    image_name=message.image_name,
                    image_size=message.image_size,
                ))
                await db.commit()
        except Exception as e:
            log.error(f"MySQL 保存消息失败: {e}")

    async def _load_session_ids_from_db(self, user_id: int) -> List[str]:
        """从 MySQL 恢复用户的会话 ID 列表"""
        try:
            from app.models import TutorChatMessage, AsyncSessionLocal
            from sqlalchemy import select, func
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(TutorChatMessage.session_id)
                    .where(TutorChatMessage.user_id == user_id)
                    .group_by(TutorChatMessage.session_id)
                    .order_by(func.max(TutorChatMessage.id).desc())
                )
                return [row[0] for row in result.all()]
        except Exception as e:
            log.error(f"从 MySQL 加载会话列表失败: {e}")
            return []

    # ── 序列化 ──────────────────────────────────────────────

    @staticmethod
    def _serialize_messages(messages: List[TutorMessage]) -> str:
        return json.dumps([msg.to_dict() for msg in messages])

    @staticmethod
    def _deserialize_messages(data: str) -> List[TutorMessage]:
        items = json.loads(data)
        return [TutorMessage.from_dict(item) for item in items]


# 全局单例
tutor_context_manager = TutorContextManager()
