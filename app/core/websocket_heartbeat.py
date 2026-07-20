"""WebSocket 心跳管理器 - 通过 ping/pong 协议监控连接健康状态"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.core.logger import log


@dataclass
class ConnectionHealth:
    """连接健康状态"""
    user_id: int
    session_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_pong: datetime = field(default_factory=datetime.now)
    ping_sent: bool = False
    pong_received: bool = False


class HeartbeatManager:
    """WebSocket 心跳管理器

    通过定期发送 ping 消息并等待 pong 响应来监控连接健康状态。
    如果在超时时间内未收到 pong，则判定为过期连接。
    """

    def __init__(self, ping_interval: int = 30, timeout: int = 30):
        """初始化心跳管理器

        Args:
            ping_interval: ping 间隔秒数（默认: 30s）
            timeout: 等待 pong 超时秒数（默认: 10s）
        """
        self._ping_interval = ping_interval
        self._timeout = timeout
        self._connections: Dict[int, ConnectionHealth] = {}  # id(websocket) -> ConnectionHealth
        self._websocket_map: Dict[int, WebSocket] = {}  # id(websocket) -> websocket
        self._session_map: Dict[str, int] = {}  # session_id -> user_id
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False

    def register(self, websocket: WebSocket, user_id: int, session_id: str) -> None:
        """注册连接用于心跳监控

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
            session_id: 会话 ID
        """
        ws_id = id(websocket)
        health = ConnectionHealth(user_id=user_id, session_id=session_id)
        self._connections[ws_id] = health
        self._websocket_map[ws_id] = websocket
        self._session_map[session_id] = user_id
        log.debug(f"心跳管理器已注册连接: user_id={user_id}, session_id={session_id}")

    def unregister(self, websocket: WebSocket) -> None:
        """取消注册连接

        Args:
            websocket: WebSocket 连接对象
        """
        ws_id = id(websocket)
        if ws_id in self._connections:
            health = self._connections[ws_id]
            session_id = health.session_id
            del self._connections[ws_id]
            del self._websocket_map[ws_id]
            if session_id in self._session_map:
                del self._session_map[session_id]
            log.debug(f"心跳管理器已取消注册连接: user_id={health.user_id}, session_id={session_id}")

    def is_registered(self, websocket: WebSocket) -> bool:
        """检查连接是否已注册

        Args:
            websocket: WebSocket 连接对象

        Returns:
            True 如果已注册
        """
        return id(websocket) in self._connections

    def get_user_id(self, websocket: WebSocket) -> Optional[int]:
        """获取连接对应的用户 ID

        Args:
            websocket: WebSocket 连接对象

        Returns:
            用户 ID，如果未注册返回 None
        """
        ws_id = id(websocket)
        if ws_id in self._connections:
            return self._connections[ws_id].user_id
        return None

    async def handle_pong(self, websocket: WebSocket) -> None:
        """处理 pong 响应

        Args:
            websocket: WebSocket 连接对象
        """
        ws_id = id(websocket)
        if ws_id in self._connections:
            health = self._connections[ws_id]
            health.pong_received = True
            health.last_pong = datetime.now()
            log.debug(f"收到 pong 响应: user_id={health.user_id}")

    def check_stale_connections(self) -> List[WebSocket]:
        """检查过期连接

        过期判定条件: ping_sent == True AND pong_received == False AND 时间差 > timeout

        Returns:
            过期的 WebSocket 连接列表
        """
        stale = []
        now = datetime.now()
        for ws_id, health in self._connections.items():
            if health.ping_sent and not health.pong_received:
                elapsed = (now - health.last_pong).total_seconds()
                if elapsed > self._timeout:
                    if ws_id in self._websocket_map:
                        stale.append(self._websocket_map[ws_id])
        return stale

    async def send_pings(self) -> None:
        """向所有已注册的连接发送 ping 消息"""
        now = datetime.now()
        for ws_id, health in self._connections.items():
            if ws_id in self._websocket_map:
                websocket = self._websocket_map[ws_id]
                try:
                    await websocket.send_json({"type": "ping"})
                    health.ping_sent = True
                    health.pong_received = False
                    health.last_pong = now  # 发送 ping 时重置计时器，给客户端响应时间
                    log.debug(f"已发送 ping: user_id={health.user_id}")
                except Exception as e:
                    log.error(f"发送 ping 失败: user_id={health.user_id}, error={e}")

    async def cleanup_stale(self) -> List[WebSocket]:
        """查找并清理过期连接

        Returns:
            已清理的 WebSocket 连接列表
        """
        stale = self.check_stale_connections()
        cleaned = []

        for websocket in stale:
            try:
                log.warning(f"检测到过期连接，准备关闭: user_id={self.get_user_id(websocket)}")
                await websocket.close(code=1000, reason="Connection stale - heartbeat timeout")
                self.unregister(websocket)
                cleaned.append(websocket)
            except Exception as e:
                log.error(f"关闭过期连接失败: error={e}")
                self.unregister(websocket)
                cleaned.append(websocket)

        return cleaned

    async def _ping_loop(self) -> None:
        """后台 ping 循环"""
        while self._running:
            try:
                await asyncio.sleep(self._ping_interval)
                if self._running:
                    await self.send_pings()
                    await self.cleanup_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"ping 循环异常: error={e}")

    def start_ping_loop(self) -> asyncio.Task:
        """启动后台 ping 循环

        Returns:
            ping 循环的 asyncio.Task
        """
        if self._ping_task is not None and not self._ping_task.done():
            log.debug("ping 循环已经在运行")
            return self._ping_task

        self._running = True
        self._ping_task = asyncio.create_task(self._ping_loop())
        log.debug("已启动心跳 ping 循环")
        return self._ping_task

    def stop_ping_loop(self) -> None:
        """停止后台 ping 循环"""
        self._running = False
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()
            log.debug("已停止心跳 ping 循环")
        self._ping_task = None

    def get_all_sessions(self) -> Dict[str, int]:
        """获取所有会话映射

        Returns:
            session_id -> user_id 映射
        """
        return dict(self._session_map)
