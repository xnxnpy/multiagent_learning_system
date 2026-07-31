"""Tutor Streaming WebSocket 端点（/stream 路径）

与 tutor.py 的 /ws/chat 功能相同，使用 TutorContextManager 管理上下文。
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, WebSocket

from app.agents.tutor_agent import tutor_agent
from app.api.v1.ws_base import WebSocketEndpoint
from app.core.logger import log
from app.core.websocket_dispatcher import MessageType
from app.core.websocket_heartbeat import HeartbeatManager
from app.core.websocket_manager import manager
from app.core.tutor_streaming import tutor_context_manager, TutorMessage
import uuid

router = APIRouter(prefix="/tutor/stream", tags=["辅导流式"])

_heartbeat = HeartbeatManager()


class TutorStreamWebSocket(WebSocketEndpoint):
    """辅导流式 WebSocket 端点（/stream）"""

    def setup_handlers(self):
        self.dispatcher.register(MessageType.QUERY, self.handle_query)
        self.dispatcher.register(MessageType.STOP, self.handle_stop)

    async def handle_query(self, ws: WebSocket, user_id: int, message: Dict[str, Any]):
        question = message.get("question", "")
        session_id = message.get("session_id")
        image_base64 = message.get("image_base64")  # 用户上传的题目图片 base64（可选）

        if not question:
            await ws.send_json({"type": MessageType.ERROR, "message": "问题不能为空"})
            return

        if not session_id:
            session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"

        # 1. 获取历史
        history = await tutor_context_manager.get_history_as_messages(session_id, user_id)

        await ws.send_json({"type": MessageType.STATUS, "message": "正在检索相关资料..."})

        # 2. 流式生成（Agent 只接收 OCR 文本，不接收图片）
        full_response = ""
        try:
            await ws.send_json({"type": MessageType.STATUS, "message": "已找到相关资料，正在生成回答..."})

            async for chunk in tutor_agent.run_stream(user_id=user_id, question=question, history=history):
                full_response += chunk
                await ws.send_json({"type": MessageType.CHUNK, "data": chunk})

            # 3. 保存（用户消息携带图片 base64，AI 回复不带）
            now = datetime.now()
            await tutor_context_manager.add_message(session_id, user_id, TutorMessage(role="user", content=question, timestamp=now, image_base64=image_base64))
            await tutor_context_manager.add_message(session_id, user_id, TutorMessage(role="assistant", content=full_response, timestamp=now))
            await tutor_context_manager.update_session_list(user_id, session_id)

            await ws.send_json({"type": MessageType.END, "data": full_response, "session_id": session_id})

        except Exception as e:
            log.error(f"辅导流式查询失败: user_id={user_id}, error={e}")
            await ws.send_json({"type": MessageType.ERROR, "message": "生成回答失败，请稍后重试"})

    async def handle_stop(self, ws: WebSocket, user_id: int, message: Dict[str, Any]):
        await ws.send_json({"type": MessageType.STATUS, "message": "已停止生成"})


_tutor_stream_ws = TutorStreamWebSocket(path="/stream", manager=manager, heartbeat=_heartbeat)
_tutor_stream_ws.register(router)
