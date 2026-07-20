"""通知系统 API 模块

提供通知的 REST 接口和 WebSocket 实时推送功能，包括：
- 通知的 CRUD 操作（获取、标记已读、删除、清空）
- 通知未读计数
- WebSocket 实时通知推送（mark_read、mark_all_read）
- 学习通知、评估通知、资源状态通知的发送
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models import User
from app.api.v1.deps import get_current_user
from app.core.logger import log
from app.core.websocket_manager import manager, notification_manager, EnhancedConnectionManager
from app.core.websocket_heartbeat import HeartbeatManager
from app.api.v1.ws_base import WebSocketEndpoint
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["通知系统"])

# 共享心跳管理器
_heartbeat = HeartbeatManager()


class Notification(BaseModel):
    """通知模型"""
    id: Optional[int] = None
    type: str
    title: str
    content: str
    data: Optional[dict] = None
    read: bool = False
    created_at: Optional[str] = None


notifications_store: List[Notification] = []


@router.get("", response_model=List[Notification])
async def get_notifications(
    current_user: User = Depends(get_current_user),
    unread_only: bool = False,
    limit: int = 50
):
    """获取当前用户的所有通知"""
    user_notifications = [
        n for n in notifications_store
        if not unread_only or not n.read
    ][:limit]

    return user_notifications


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
):
    """获取未读通知数量"""
    count = sum(1 for n in notifications_store if not n.read)
    return {"count": count}


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
):
    """标记通知为已读"""
    for notification in notifications_store:
        if notification.id == notification_id:
            notification.read = True
            return {"message": "通知已标记为已读"}

    raise HTTPException(status_code=404, detail="通知不存在")


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
):
    """标记所有通知为已读"""
    for notification in notifications_store:
        notification.read = True
    return {"message": "所有通知已标记为已读"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
):
    """删除通知"""
    global notifications_store
    notifications_store = [n for n in notifications_store if n.id != notification_id]
    return {"message": "通知已删除"}


@router.delete("/clear")
async def clear_notifications(
    current_user: User = Depends(get_current_user),
):
    """清空所有通知"""
    global notifications_store
    notifications_store = []
    return {"message": "通知已清空"}


class NotificationWebSocket(WebSocketEndpoint):
    """通知 WebSocket 端点

    使用统一 WebSocket 框架，处理通知相关的实时消息：
    - mark_read: 标记单条通知为已读
    - mark_all_read: 标记所有通知为已读
    """

    def setup_handlers(self):
        """注册通知相关的消息处理器"""
        self.dispatcher.register("mark_read", self.handle_mark_read)
        self.dispatcher.register("mark_all_read", self.handle_mark_all_read)

    async def handle_mark_read(self, ws, user_id, message):
        """处理标记单条通知为已读

        收到 mark_read 类型消息后:
        1. 从消息中获取 notification_id
        2. 遍历 notifications_store 找到并标记为已读
        3. 发送 notification_updated 响应
        """
        notification_id = message.get("notification_id")
        for notification in notifications_store:
            if notification.id == notification_id:
                notification.read = True
                break

        await ws.send_json({
            "type": "notification_updated",
            "notification_id": notification_id
        })

    async def handle_mark_all_read(self, ws, user_id, message):
        """处理标记所有通知为已读

        收到 mark_all_read 类型消息后:
        1. 将 notifications_store 中所有通知标记为已读
        2. 发送 all_notifications_updated 响应
        """
        for notification in notifications_store:
            notification.read = True

        await ws.send_json({
            "type": "all_notifications_updated"
        })


# 创建端点实例并注册到 router
_notification_ws = NotificationWebSocket(
    path="/ws",
    manager=manager,
    heartbeat=_heartbeat,
)
_notification_ws.register(router)


async def send_learning_notification(
    user_id: int,
    title: str,
    content: str,
    data: Optional[dict] = None
):
    """发送学习相关通知"""
    notification = Notification(
        id=len(notifications_store) + 1,
        type="learning",
        title=title,
        content=content,
        data=data,
        created_at=datetime.now().isoformat()
    )
    notifications_store.append(notification)

    await notification_manager.send_notification(
        user_id=user_id,
        notification_type="learning",
        data=data or {},
        title=title,
        content=content
    )

    return notification


async def send_evaluation_notification(
    user_id: int,
    result: dict
):
    """发送评估结果通知"""
    notification = Notification(
        id=len(notifications_store) + 1,
        type="evaluation",
        title="学习评估完成",
        content=f"您的学习评估已完成，等级: {result.get('overall_grade', 'N/A')}",
        data=result,
        created_at=datetime.now().isoformat()
    )
    notifications_store.append(notification)

    await notification_manager.send_evaluation_result(user_id, result)
    return notification


async def send_resource_notification(
    user_id: int,
    resource_name: str,
    status: str
):
    """发送资源状态通知"""
    notification = Notification(
        id=len(notifications_store) + 1,
        type="resource",
        title="资源状态更新",
        content=f"资源 '{resource_name}' 审核状态: {status}",
        data={"resource_name": resource_name, "status": status},
        created_at=datetime.now().isoformat()
    )
    notifications_store.append(notification)

    await notification_manager.send_resource_status(user_id, resource_name, status)
    return notification
