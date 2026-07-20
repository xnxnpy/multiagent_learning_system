"""WebSocket 统一端点框架 - 提供可复用的 WebSocket 连接、认证、消息分发和心跳管理"""
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.logger import log
from app.core.websocket_dispatcher import MessageDispatcher, MessageType
from app.core.websocket_heartbeat import HeartbeatManager
from app.core.websocket_manager import EnhancedConnectionManager


class WebSocketEndpoint:
    """WebSocket 统一端点基类

    集成了连接管理、心跳监控、消息分发等功能，子类只需重写 setup_handlers
    注册自定义消息处理器即可。

    Usage:
        class MyWebSocket(WebSocketEndpoint):
            def setup_handlers(self):
                self.dispatcher.register(MessageType.QUERY, self.handle_query)

            async def handle_query(self, ws, user_id, message):
                ...

        endpoint = MyWebSocket(path="/ws/chat", manager=mgr, heartbeat=hb)
        endpoint.register(router)
    """

    def __init__(
        self,
        path: str,
        manager: EnhancedConnectionManager,
        heartbeat: HeartbeatManager,
        auth_func: Optional[Callable[[str], Optional[int]]] = None,
    ):
        """初始化 WebSocket 端点

        Args:
            path: WebSocket 端点路径
            manager: 连接管理器
            heartbeat: 心跳管理器
            auth_func: 认证函数，接受 token 返回 user_id，为 None 时使用默认认证
        """
        self.path = path
        self.manager = manager
        self.heartbeat = heartbeat
        self.auth_func = auth_func or self._default_auth
        self.dispatcher = MessageDispatcher(heartbeat=heartbeat)

        # 注册内置的 ping 处理器
        self.dispatcher.register(MessageType.PING, self._handle_ping)

        # 允许子类注册自定义处理器
        self.setup_handlers()

    def setup_handlers(self) -> None:
        """子类重写此方法以注册自定义消息处理器，默认为空实现"""
        pass

    def _default_auth(self, token: str) -> Optional[int]:
        """默认 JWT 认证函数

        Args:
            token: JWT token 字符串

        Returns:
            user_id 如果认证成功，否则返回 None
        """
        from app.core.security import decode_token

        try:
            payload = decode_token(token)
            if payload is None:
                return None
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return int(user_id)
        except Exception:
            log.warning("默认认证失败")
            return None

    def _generate_session_id(self, websocket: WebSocket, user_id: int) -> str:
        """生成会话 ID

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID

        Returns:
            格式为 "{path}_{user_id}_{id(websocket)}" 的会话 ID
        """
        return f"{self.path}_{user_id}_{id(websocket)}"

    async def _handle_ping(self, ws: WebSocket, user_id: int, message: Dict[str, Any]) -> None:
        """处理 ping 消息并返回 pong

        Args:
            ws: WebSocket 连接对象
            user_id: 用户 ID
            message: 收到的消息
        """
        await ws.send_json({"type": MessageType.PONG})

    async def connect(self, websocket: WebSocket, token: str) -> Optional[int]:
        """认证并建立连接

        Args:
            websocket: WebSocket 连接对象
            token: 认证 token

        Returns:
            user_id 如果认证成功并连接建立，否则返回 None
        """
        log.info(f"WebSocket 尝试连接: path={self.path}, token={token[:20] if token else 'None'}...")

        if not token:
            log.warning(f"WebSocket 认证失败: 缺少 token, path={self.path}")
            await websocket.close(code=4001)
            return None

        user_id = self.auth_func(token)
        if user_id is None:
            log.warning(f"WebSocket 认证失败: token 无效, path={self.path}")
            await websocket.close(code=4001)
            return None

        log.info(f"WebSocket 认证成功: path={self.path}, user_id={user_id}")

        session_id = self._generate_session_id(websocket, user_id)

        # 连接管理器处理 accept 和连接信息存储
        await self.manager.connect(websocket, user_id, session_id)

        # 注册心跳监控
        self.heartbeat.register(websocket, user_id, session_id)

        # 发送连接成功消息
        await websocket.send_json({
            "type": MessageType.CONNECTED,
            "message": "连接成功",
            "session_id": session_id,
        })

        log.info(f"WebSocket 连接成功: path={self.path}, user_id={user_id}, session_id={session_id}")
        return user_id

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """断开连接并清理资源

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
        """
        # 发送断开连接消息（如果连接仍然存活）
        try:
            await websocket.send_json({
                "type": MessageType.DISCONNECTED,
                "message": "连接已断开",
            })
        except Exception:
            pass  # 连接可能已经关闭

        # 取消心跳注册
        if self.heartbeat.is_registered(websocket):
            self.heartbeat.unregister(websocket)

        # 断开连接管理
        self.manager.disconnect(websocket, user_id)

        log.info(f"WebSocket 断开连接: path={self.path}, user_id={user_id}")

    async def run(self, websocket: WebSocket, token: str) -> None:
        """主 WebSocket 循环

        完整流程：认证 -> 连接 -> 消息循环 -> 清理

        Args:
            websocket: WebSocket 连接对象
            token: 认证 token
        """
        user_id = await self.connect(websocket, token)
        if user_id is None:
            return

        try:
            while True:
                data = await websocket.receive_json()
                log.info(f"收到 WebSocket 消息: path={self.path}, user_id={user_id}, type={data.get('type')}")
                log.info(f"WebSocket URL: {websocket.url}")
                log.info(f"WebSocket 路径: {websocket.url.path}")
                await self.dispatcher.dispatch(data, websocket, user_id)
        except WebSocketDisconnect:
            log.info(f"WebSocket 客户端断开: path={self.path}, user_id={user_id}")
        except Exception as e:
            log.error(f"WebSocket 运行异常: path={self.path}, user_id={user_id}, error={e}")
        finally:
            await self.disconnect(websocket, user_id)

    def register(self, router: APIRouter) -> None:
        """在 FastAPI router 上注册 WebSocket 端点

        Args:
            router: FastAPI APIRouter 实例
        """
        ws_endpoint = self

        @router.websocket(self.path)
        async def websocket_endpoint(
            websocket: WebSocket,
            token: str = Query(..., description="认证 token")
        ):
            log.info(f"WebSocket 端点被调用: path={self.path}, url={websocket.url}, url_path={websocket.url.path}")
            await ws_endpoint.run(websocket, token)

        log.debug(f"WebSocket 端点已注册: path={self.path}")
