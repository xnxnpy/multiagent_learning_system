import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import log
from app.core.redis_client import close_redis
from app.models import init_db
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    log.info(f"启动 {settings.APP_NAME}")
    try:
        await init_db()
        log.info("数据库初始化成功")

        # 加载模型配置到 model_manager
        from app.models import AsyncSessionLocal
        from app.core.model_manager import model_manager
        async with AsyncSessionLocal() as db:
            await model_manager.load_from_db(db)
        log.info("模型配置加载成功")

        # 启动 WebSocket 心跳 ping 循环
        from app.api.v1.tutor import _heartbeat
        _heartbeat.start_ping_loop()
        log.info("WebSocket 心跳循环已启动")

        # 预加载 BGE 嵌入模型（避免首次查询时 10 秒延迟）
        from app.embeddings.bge_embeddings import bge_embeddings
        await bge_embeddings.apreload()
        log.info("BGE 嵌入模型预加载完成")

        # 加载内容安全配置
        from app.core.content_security import content_security
        async with AsyncSessionLocal() as db:
            await content_security.load_from_db(db)
        log.info("内容安全配置加载完成")
    except Exception as e:
        log.error(f"数据库初始化失败: {e}")
    yield
    log.info("应用关闭")
    # 停止心跳循环
    try:
        from app.api.v1.tutor import _heartbeat
        _heartbeat.stop_ping_loop()
    except Exception:
        pass
    from app.core.neo4j_client import close_neo4j_driver
    await close_neo4j_driver()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="基于大模型的个性化资源生成与学习多智能体系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")

# WebSocket 路由已通过 api_router 自动注册
# 不需要单独注册 WebSocket 端点

# 调试：打印所有 WebSocket 路由
import logging
logging.getLogger("uvicorn").info("WebSocket 路由已注册")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    from app.core.websocket_manager import manager
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "websocket_connections": manager.get_connection_count()
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用基于大模型的个性化资源生成与学习多智能体系统",
        "docs": "/docs",
        "health": "/health",
        "websocket_tutor": "/api/v1/tutor/ws/chat",
        "websocket_notifications": "/api/v1/notifications/ws"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
