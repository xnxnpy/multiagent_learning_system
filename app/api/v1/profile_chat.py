"""ProfileChat WebSocket 端点 - 流式对话构建学习画像"""
from fastapi import APIRouter, WebSocket
from app.agents.profile_agent import ProfileAgent
from app.core.logger import log
from app.core.websocket_manager import manager
from app.core.websocket_heartbeat import HeartbeatManager
from app.core.websocket_dispatcher import MessageType
from app.api.v1.ws_base import WebSocketEndpoint
from app.core.security import decode_token
from app.models import AsyncSessionLocal

router = APIRouter(prefix="/profile-chat", tags=["画像对话"])

_heartbeat = HeartbeatManager()


class ProfileChatWebSocket(WebSocketEndpoint):
    """画像对话 WebSocket 端点"""

    def setup_handlers(self):
        self.dispatcher.register(MessageType.QUERY, self.handle_query)
        self.dispatcher.register(MessageType.STOP, self.handle_stop)

    async def handle_query(self, ws, user_id, message):
        """处理画像对话查询

        流程：
        1. 发送状态 "正在思考..."
        2. 流式输出 AI 回复
        3. 回复完成后发送 profile_update 更新画像卡片
        4. 检查是否需要触发工作流
        """
        question = message.get("question", "")
        session_id = message.get("session_id", f"profile_{user_id}")
        chat_history = message.get("chat_history", [])
        frontend_profile = message.get("profile", None)
        profile_id = message.get("profile_id", None)

        log.info(f"收到画像对话: user_id={user_id}, question={question[:50]}...")

        if not question:
            await ws.send_json({
                "type": MessageType.ERROR,
                "message": "消息不能为空",
            })
            return

        await ws.send_json({
            "type": MessageType.STATUS,
            "message": "正在思考...",
        })

        full_response = ""
        try:
            async with AsyncSessionLocal() as db:
                agent = ProfileAgent(db)

                async for chunk in agent.run_stream(
                    user_id=user_id,
                    user_input=question,
                    chat_history=chat_history,
                    ws=ws,
                    frontend_profile=frontend_profile,
                    profile_id=profile_id,
                ):
                    full_response += chunk
                    await ws.send_json({
                        "type": MessageType.CHUNK,
                        "content": chunk,
                    })

            # 流式输出完成，发送 end
            await ws.send_json({
                "type": MessageType.END,
                "content": full_response,
            })

            # profile_update 和 check_workflow 已移到后台任务中，画像保存完成后才发送

        except Exception as e:
            import traceback
            log.error(f"画像对话失败: user_id={user_id}, error={e}")
            log.error(f"完整堆栈: {traceback.format_exc()}")
            await ws.send_json({
                "type": MessageType.ERROR,
                "message": "生成回答失败，请稍后重试",
            })

    async def handle_stop(self, ws, user_id, message):
        """处理停止生成"""
        await ws.send_json({
            "type": MessageType.STATUS,
            "message": "已停止生成",
        })


# 注册端点
_profile_chat_ws = ProfileChatWebSocket(
    path="/ws/chat",
    manager=manager,
    heartbeat=_heartbeat,
)
_profile_chat_ws.register(router)
