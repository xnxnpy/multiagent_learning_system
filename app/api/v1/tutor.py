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
        question = message.get("question", "")              # 拼接 OCR 后的完整查询（给大模型）
        display_content = message.get("display_content", question)  # 用户原始输入（用于保存和前端显示）
        session_id = message.get("session_id")
        image_base64 = message.get("image_base64")  # 用户上传的题目图片 base64（可选）
        image_name = message.get("image_name")      # 图片文件名
        image_size = message.get("image_size")      # 图片文件大小（字节）

        if not question:
            await ws.send_json({"type": MessageType.ERROR, "message": "问题不能为空"})
            return

        # 确保 session_id 存在（过滤掉前端 new_ 前缀的临时 ID）
        if not session_id or session_id.startswith("new_"):
            session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"

        # 记录请求日志
        has_image = bool(image_base64)
        log.info(
            f"辅导查询: user_id={user_id}, session_id={session_id}, "
            f"display_len={len(display_content)}, question_len={len(question)}, "
            f"has_image={has_image}, image_name={image_name}, image_size={image_size}"
        )
        if has_image:
            log.info(f"  图片OCR文本(前200字): {question[:200]}...")

        # 1. 从 ContextManager 获取历史
        history = await tutor_context_manager.get_history_as_messages(session_id, user_id)

        await ws.send_json({"type": MessageType.STATUS, "message": "正在检索相关资料..."})

        # 2. 流式生成（TutorAgent 接收拼接 OCR 后的 question）
        full_response = ""
        try:
            await ws.send_json({"type": MessageType.STATUS, "message": "已找到相关资料，正在生成回答..."})

            async for chunk in tutor_agent.run_stream(
                user_id=user_id, question=question, history=history,
            ):
                full_response += chunk
                await ws.send_json({"type": MessageType.CHUNK, "data": chunk})

            # 3. 保存到 ContextManager（content=question 给大模型用，display_content=display_content 给用户看）
            now = datetime.now()
            await tutor_context_manager.add_message(
                session_id, user_id,
                TutorMessage(
                    role="user",
                    content=question,              # 包含 OCR 文本的完整内容（给大模型用）
                    display_content=display_content,  # 用户原始输入（给用户看）
                    timestamp=now,
                    image_base64=image_base64,
                    image_name=image_name,
                    image_size=image_size,
                )
            )
            await tutor_context_manager.add_message(
                session_id, user_id,
                TutorMessage(role="assistant", content=full_response, timestamp=now)
            )
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
