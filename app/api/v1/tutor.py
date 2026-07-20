from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from app.models import User
from app.api.v1.deps import get_current_user
from app.agents.tutor_agent import tutor_agent
from app.core.tutor_streaming import tutor_context_manager, TutorMessage
from app.core.logger import log
from app.core.websocket_manager import manager
from app.core.websocket_heartbeat import HeartbeatManager
from app.core.websocket_dispatcher import MessageType
from app.api.v1.ws_base import WebSocketEndpoint
import uuid

router = APIRouter(prefix="/tutor", tags=["智能辅导"])

_heartbeat = HeartbeatManager()


class TutorWebSocket(WebSocketEndpoint):
    """智能辅导 WebSocket 端点（上下文由 TutorContextManager 管理）"""

    def setup_handlers(self):
        self.dispatcher.register(MessageType.QUERY, self.handle_query)
        self.dispatcher.register(MessageType.STOP, self.handle_stop)

    async def handle_query(self, ws, user_id, message):
        question = message.get("question", "")
        session_id = message.get("session_id")

        if not question:
            await ws.send_json({"type": MessageType.ERROR, "message": "问题不能为空"})
            return

        # 确保 session_id 存在
        if not session_id:
            session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"

        # 1. 从 ContextManager 获取历史
        history = await tutor_context_manager.get_history_as_messages(session_id, user_id)

        await ws.send_json({"type": MessageType.STATUS, "message": "正在检索相关资料..."})

        # 2. 流式生成（TutorAgent 只负责 RAG）
        full_response = ""
        try:
            await ws.send_json({"type": MessageType.STATUS, "message": "已找到相关资料，正在生成回答..."})

            async for chunk in tutor_agent.run_stream(
                user_id=user_id, question=question, history=history,
            ):
                full_response += chunk
                await ws.send_json({"type": MessageType.CHUNK, "data": chunk})

            # 3. 保存到 ContextManager
            now = datetime.now()
            await tutor_context_manager.add_message(session_id, user_id, TutorMessage(role="user", content=question, timestamp=now))
            await tutor_context_manager.add_message(session_id, user_id, TutorMessage(role="assistant", content=full_response, timestamp=now))
            await tutor_context_manager.update_session_list(user_id, session_id)

            await ws.send_json({"type": MessageType.END, "data": full_response, "session_id": session_id})

        except Exception as e:
            log.error(f"辅导查询失败: user_id={user_id}, error={e}")
            try:
                await ws.send_json({"type": MessageType.ERROR, "message": "生成回答失败，请稍后重试"})
            except Exception:
                pass  # WebSocket 已关闭，忽略

    async def handle_stop(self, ws, user_id, message):
        try:
            await ws.send_json({"type": MessageType.STATUS, "message": "已停止生成"})
        except Exception:
            pass


# 注册端点
_tutor_ws = TutorWebSocket(path="/ws/chat", manager=manager, heartbeat=_heartbeat)
_tutor_ws.register(router)


# ── REST API ──────────────────────────────────────────

@router.get("/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    """获取用户的所有会话"""
    try:
        sessions = await tutor_context_manager.get_user_sessions(current_user.id)
        return {"sessions": sessions}
    except Exception as e:
        log.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, current_user: User = Depends(get_current_user)):
    """获取指定会话的聊天历史"""
    try:
        history = await tutor_context_manager.get_history_dict(session_id)
        return {"messages": history, "session_id": session_id}
    except Exception as e:
        log.error(f"获取辅导历史失败: {e}")
        return {"messages": [], "session_id": session_id}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str, current_user: User = Depends(get_current_user)):
    """清空指定会话"""
    try:
        await tutor_context_manager.clear_session(session_id, current_user.id)
        return {"message": "会话已清空"}
    except Exception as e:
        log.error(f"清空会话失败: {e}")
        raise HTTPException(status_code=500, detail="清空会话失败")


@router.post("/sessions")
async def create_session(current_user: User = Depends(get_current_user)):
    """创建新的辅导会话"""
    session_id = f"session_{current_user.id}_{uuid.uuid4().hex[:8]}"
    return {"session_id": session_id, "message": "会话已创建"}


@router.get("/ws/status")
async def get_websocket_status():
    """获取 WebSocket 连接状态"""
    connected = manager.is_connected(0)  # 简化
    return {"connected": connected}
