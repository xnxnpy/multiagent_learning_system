"""WebSocket 消息分发器 - 基于消息类型将 WebSocket 消息路由到注册的处理器"""
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import WebSocket

from app.core.logger import log

# 消息处理器类型: (WebSocket连接, 用户ID, 消息字典)
MessageHandler = Callable[[WebSocket, int, Dict[str, Any]], Awaitable[None]]


class MessageType:
    """WebSocket 消息类型常量"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PING = "ping"
    PONG = "pong"
    CHUNK = "chunk"
    STATUS = "status"
    END = "end"
    ERROR = "error"
    QUERY = "query"
    STOP = "stop"


class MessageDispatcher:
    """基于消息类型的 WebSocket 消息路由器"""

    def __init__(self, heartbeat=None):
        self._handlers: Dict[str, MessageHandler] = {}
        self._heartbeat = heartbeat

    def register(self, message_type: str, handler: MessageHandler) -> None:
        """注册一个处理器到指定的消息类型"""
        self._handlers[message_type] = handler
        log.debug(f"已注册消息处理器: type={message_type}, handler={handler.__name__}")

    def unregister(self, message_type: str) -> None:
        """取消注册指定消息类型的处理器"""
        if message_type in self._handlers:
            del self._handlers[message_type]
            log.debug(f"已取消注册消息处理器: type={message_type}")

    def has_handler(self, message_type: str) -> bool:
        """检查指定消息类型是否有已注册的处理器"""
        return message_type in self._handlers

    async def dispatch(
        self, message: dict, websocket: WebSocket, user_id: int
    ) -> bool:
        """将消息分发到对应的处理器

        Args:
            message: 消息字典，必须包含 'type' 字段
            websocket: WebSocket 连接对象
            user_id: 用户 ID

        Returns:
            bool: 消息是否被成功处理
        """
        message_type = message.get("type")

        if message_type is None:
            log.warning("收到缺少 type 字段的消息")
            return False

        # pong 消息直接交给心跳管理器处理，不需要注册 handler
        if message_type == "pong":
            if hasattr(self, '_heartbeat') and self._heartbeat:
                await self._heartbeat.handle_pong(websocket)
            return True

        handler = self._handlers.get(message_type)
        if handler is None:
            log.warning(f"未找到消息类型的处理器: type={message_type}")
            return False

        log.debug(f"分发消息: type={message_type}, user_id={user_id}")

        try:
            await handler(websocket, user_id, message)
            return True
        except Exception as e:
            log.error(f"处理器执行失败: type={message_type}, error={e}")
            try:
                await websocket.send_json({
                    "type": MessageType.ERROR,
                    "message": f"处理消息时发生错误: {str(e)}",
                })
            except Exception:
                log.error(f"向客户端发送错误消息失败: type={message_type}, user_id={user_id}")
            return False
