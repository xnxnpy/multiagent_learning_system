from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from fastapi import WebSocket
from app.core.logger import log


@dataclass
class ConnectionInfo:
    """连接信息数据类"""
    websocket: WebSocket
    user_id: int
    session_id: str
    connected_at: datetime = field(default_factory=datetime.now)


class EnhancedConnectionManager:
    """增强版 WebSocket 连接管理器，支持 session 持久化"""

    def __init__(self):
        self._connections: Dict[int, List[ConnectionInfo]] = {}
        self._session_map: Dict[str, int] = {}
        self._websocket_map: Dict[WebSocket, ConnectionInfo] = {}

    async def connect(self, websocket: WebSocket, user_id: int, session_id: str):
        """连接 WebSocket 并存储 ConnectionInfo"""
        await websocket.accept()
        info = ConnectionInfo(websocket=websocket, user_id=user_id, session_id=session_id)
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(info)
        self._session_map[session_id] = user_id
        self._websocket_map[websocket] = info
        log.info(f"WebSocket 连接已建立: user_id={user_id}, session_id={session_id}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """断开 WebSocket 连接并清理所有映射"""
        info = self._websocket_map.pop(websocket, None)
        if info:
            self._session_map.pop(info.session_id, None)
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c.websocket is not websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        log.info(f"WebSocket 连接已断开: user_id={user_id}")

    def is_connected(self, user_id: int) -> bool:
        """检查用户是否有活跃连接"""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_session_id(self, websocket: WebSocket) -> Optional[str]:
        """获取 websocket 对应的 session_id"""
        info = self._websocket_map.get(websocket)
        return info.session_id if info else None

    def get_user_id_from_session(self, session_id: str) -> Optional[int]:
        """根据 session_id 获取 user_id"""
        return self._session_map.get(session_id)

    async def send_to_user(self, user_id: int, message: dict) -> int:
        """发送消息到用户的所有连接，返回成功发送的连接数"""
        count = 0
        if user_id in self._connections:
            for info in self._connections[user_id]:
                try:
                    await info.websocket.send_json(message)
                    count += 1
                except Exception as e:
                    log.error(f"发送消息失败: user_id={user_id}, error={e}")
        return count

    async def send_to_session(self, session_id: str, message: dict) -> bool:
        """发送消息到指定 session，返回是否成功"""
        user_id = self._session_map.get(session_id)
        if user_id is None:
            return False
        # 尝试找到该 session 对应的具体 websocket
        if user_id in self._connections:
            for info in self._connections[user_id]:
                if info.session_id == session_id:
                    try:
                        await info.websocket.send_json(message)
                        return True
                    except Exception as e:
                        log.error(f"发送消息失败: session_id={session_id}, error={e}")
                        return False
            # 未找到精确匹配的 ConnectionInfo（例如通过 register_session 外部注册的），
            # 回退到向该用户的所有连接发送
            sent = False
            for info in self._connections[user_id]:
                try:
                    await info.websocket.send_json(message)
                    sent = True
                except Exception as e:
                    log.error(f"发送消息失败: session_id={session_id}, error={e}")
            return sent
        return False

    async def send_to_websocket(self, websocket: WebSocket, message: dict) -> bool:
        """发送消息到指定 websocket，返回是否成功"""
        if websocket not in self._websocket_map:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            log.error(f"发送消息失败: error={e}")
            return False

    def get_all_sessions(self) -> Dict[str, int]:
        """获取所有 session_id -> user_id 映射"""
        return dict(self._session_map)

    def get_user_connections(self, user_id: int) -> List[WebSocket]:
        """获取用户的所有 websocket 列表"""
        if user_id not in self._connections:
            return []
        return [info.websocket for info in self._connections[user_id]]

    def get_connection_count(self) -> int:
        """获取所有活跃连接的总数"""
        return sum(len(conns) for conns in self._connections.values())


class ConnectionManager(EnhancedConnectionManager):
    """向后兼容的 ConnectionManager，包装 EnhancedConnectionManager 并提供旧接口"""

    @property
    def active_connections(self) -> Dict[int, List[WebSocket]]:
        """返回旧格式的 active_connections 字典"""
        result: Dict[int, List[WebSocket]] = {}
        for user_id, infos in self._connections.items():
            result[user_id] = [info.websocket for info in infos]
        return result

    @property
    def user_sessions(self) -> Dict[str, int]:
        """返回旧格式的 user_sessions 字典"""
        return dict(self._session_map)

    async def connect_legacy(self, websocket: WebSocket, user_id: int):
        """旧版连接方法（不带 session_id），自动生成 session_id"""
        import uuid
        session_id = f"auto_{user_id}_{str(uuid.uuid4())[:8]}"
        await self.connect(websocket, user_id=user_id, session_id=session_id)

    async def send_personal_message(self, message: dict, user_id: int):
        """发送个人消息（旧接口别名）"""
        await self.send_to_user(user_id, message)

    async def broadcast(self, message: dict, user_ids: List[int] = None):
        """广播消息（旧接口）"""
        if user_ids is None:
            user_ids = list(self._connections.keys())
        for user_id in user_ids:
            await self.send_to_user(user_id, message)

    def register_session(self, session_id: str, user_id: int):
        """注册会话（旧接口别名）"""
        self._session_map[session_id] = user_id

    def unregister_session(self, session_id: str):
        """取消注册会话（旧接口别名）"""
        self._session_map.pop(session_id, None)

    def get_user_connections_list(self, user_id: int) -> List[WebSocket]:
        """获取用户所有连接（旧接口别名）"""
        return self.get_user_connections(user_id)


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self.manager = ConnectionManager()
        self.notification_handlers: Dict[str, List[Callable]] = {
            "learning_progress": [],
            "evaluation_result": [],
            "resource_status": [],
            "system_alert": [],
            "chat_message": []
        }

    def register_handler(self, notification_type: str, handler: Callable):
        """注册通知处理器"""
        if notification_type in self.notification_handlers:
            self.notification_handlers[notification_type].append(handler)

    async def send_notification(
        self,
        user_id: int,
        notification_type: str,
        data: dict,
        title: str = None,
        content: str = None
    ):
        """发送通知"""
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "content": content,
            "data": data,
            "timestamp": self._get_timestamp()
        }

        await self.manager.send_personal_message(notification, user_id)

        if notification_type in self.notification_handlers:
            for handler in self.notification_handlers[notification_type]:
                try:
                    await handler(user_id, data)
                except Exception as e:
                    log.error(f"处理通知失败: {e}")

    async def send_learning_progress(self, user_id: int, progress: float, current_step: str):
        """发送学习进度更新"""
        await self.send_notification(
            user_id=user_id,
            notification_type="learning_progress",
            data={"progress": progress, "current_step": current_step},
            title="学习进度更新",
            content=f"当前进度: {int(progress * 100)}%"
        )

    async def send_evaluation_result(self, user_id: int, result: dict):
        """发送评估结果"""
        summary = result.get("summary", "")
        if not summary:
            summary = result.get("report_data", {}).get("summary", "")
        if not summary:
            summary = f"您的学习评估已完成，等级: {result.get('overall_grade', 'N/A')}"

        await self.send_notification(
            user_id=user_id,
            notification_type="evaluation_result",
            data={
                "overall_grade": result.get("overall_grade"),
                "accuracy_rate": result.get("accuracy_rate"),
                "mastery_level": result.get("mastery_level"),
                "should_update_path": result.get("should_update_path", False),
                "summary": summary,
            },
            title="📊 阶段学习评估",
            content=summary,
        )

    async def send_resource_status(self, user_id: int, resource_id: int, status: str):
        """发送资源状态更新"""
        await self.send_notification(
            user_id=user_id,
            notification_type="resource_status",
            data={"resource_id": resource_id, "status": status},
            title="资源状态更新",
            content=f"资源审核状态: {status}"
        )

    async def send_system_alert(self, user_ids: List[int], message: str, level: str = "info"):
        """发送系统警报"""
        notification = {
            "type": "system_alert",
            "level": level,
            "message": message,
            "timestamp": self._get_timestamp()
        }
        await self.manager.broadcast(notification, user_ids)

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().isoformat()


class StreamManager:
    """流式输出管理器"""

    def __init__(self):
        self.active_streams: Dict[str, bool] = {}

    def start_stream(self, stream_id: str):
        """开始流"""
        self.active_streams[stream_id] = True

    def stop_stream(self, stream_id: str):
        """停止流"""
        self.active_streams[stream_id] = False

    def is_streaming(self, stream_id: str) -> bool:
        """检查是否正在流式输出"""
        return self.active_streams.get(stream_id, False)

    async def stream_text(
        self,
        websocket: WebSocket,
        text: str,
        stream_id: str = None,
        chunk_size: int = 50
    ):
        """流式发送文本"""
        for i in range(0, len(text), chunk_size):
            if stream_id and not self.is_streaming(stream_id):
                break

            chunk = text[i:i + chunk_size]
            await websocket.send_json({
                "type": "stream",
                "content": chunk,
                "stream_id": stream_id
            })

    async def stream_json(
        self,
        websocket: WebSocket,
        data: dict,
        stream_id: str = None
    ):
        """流式发送 JSON"""
        await websocket.send_json({
            "type": "json",
            "data": data,
            "stream_id": stream_id
        })


manager = ConnectionManager()
notification_manager = NotificationManager()
stream_manager = StreamManager()
