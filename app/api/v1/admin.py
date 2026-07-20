from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import get_db, User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.user_service import user_service
from app.services.stats_service import stats_service
from app.core.logger import log
from app.core.config import settings
from app.api.v1.deps import get_current_user, require_roles
from app.schemas.common import PageResponse
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

router = APIRouter(prefix="/admin", tags=["管理员"])

require_admin = require_roles(["admin"])


class SystemConfig(BaseModel):
    """系统配置模型"""
    app_name: str
    debug: bool
    secret_key: str
    jwt_expire_minutes: int
    backend_host: str
    backend_port: int
    quality_thresholds: Dict[str, int] = {}
    ppt_video_max_pages: int = 10
    tts_voice: str = "x4_yezi"


class SystemConfigUpdate(BaseModel):
    """系统配置更新模型"""
    app_name: Optional[str] = None
    debug: Optional[bool] = None
    jwt_expire_minutes: Optional[int] = None
    backend_host: Optional[str] = None
    backend_port: Optional[int] = None
    quality_thresholds: Optional[Dict[str, int]] = None
    ppt_video_max_pages: Optional[int] = None
    tts_voice: Optional[str] = None


class ModelProviderResponse(BaseModel):
    """模型提供商响应"""
    id: int
    name: str
    provider_type: str
    api_url: str
    is_active: bool
    config: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ModelProviderCreate(BaseModel):
    """创建模型提供商"""
    name: str = Field(..., description="名称")
    provider_type: str = Field(..., description="类型: xunfei, openai, azure")
    api_url: str = Field(..., description="API URL")
    api_key: Optional[str] = Field(None, description="API Key")
    config: Dict[str, Any] = Field(default_factory=dict, description="其他配置")


class ModelProviderUpdate(BaseModel):
    """更新模型提供商"""
    name: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class MonitoringStats(BaseModel):
    """监控统计"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    uptime_seconds: float
    request_count: int
    error_count: int


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str
    level: str
    message: str
    module: Optional[str] = None


class BackupResponse(BaseModel):
    """备份响应"""
    success: bool
    message: str
    backup_path: Optional[str] = None
    backup_size: Optional[int] = None


class SystemStatsResponse(BaseModel):
    """系统数据统计响应"""
    users_count: int
    courses_count: int
    learning_records_count: int
    resources_count: int
    disk_usage_bytes: int
    chroma_size_bytes: int
    logs_size_bytes: int


class CacheClearRequest(BaseModel):
    """缓存清理请求"""
    target: str = Field(..., description="清理目标: redis / chroma / all")


class LogCleanRequest(BaseModel):
    """日志清理请求"""
    days: int = Field(7, ge=1, le=365, description="保留天数")


class ContentReviewResponse(BaseModel):
    """内容审核响应"""
    id: int
    content_type: str
    content: str
    status: str
    reviewer_id: Optional[int]
    review_comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ContentReviewAction(BaseModel):
    """内容审核操作"""
    action: str = Field(..., description="操作: approve/reject")
    comment: Optional[str] = Field(None, description="审核意见")


# ==================== 用户管理接口 ====================

@router.get("/users", response_model=PageResponse[UserListResponse])
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（分页、搜索）"""
    log.info(f"管理员 {current_user.username} 获取用户列表")
    skip = (page - 1) * page_size
    users, total = await user_service.get_users_paginated(
        db, skip=skip, limit=page_size, search=search
    )

    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserListResponse.model_validate(u) for u in users],
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户"""
    log.info(f"管理员 {current_user.username} 创建用户: {user_data.username}")
    user = await user_service.create_user(db, user_data)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取单个用户"""
    log.info(f"管理员 {current_user.username} 获取用户: {user_id}")
    user = await user_service.get_by_id(db, user_id)
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户"""
    log.info(f"管理员 {current_user.username} 更新用户: {user_id}")
    user = await user_service.update_user(db, user_id, user_data)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户"""
    log.info(f"管理员 {current_user.username} 删除用户: {user_id}")
    await user_service.delete_user(db, user_id)
    return None


# ==================== 系统配置接口 ====================

@router.get("/config", response_model=SystemConfig)
async def get_system_config(
    current_user: User = Depends(require_admin),
):
    """获取系统配置"""
    log.info(f"管理员 {current_user.username} 获取系统配置")

    from app.core.quality_thresholds import quality_thresholds
    from app.services.config_service import ConfigService
    from app.models import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        cs = ConfigService(db)
        ppt_max = await cs.get("ppt_video_max_pages") or 10
        tts_v = await cs.get("tts_voice") or "x4_yezi"

    return SystemConfig(
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
        secret_key="****" + settings.SECRET_KEY[-4:] if len(settings.SECRET_KEY) > 4 else "****",
        jwt_expire_minutes=settings.JWT_EXPIRE_MINUTES,
        backend_host=settings.BACKEND_HOST,
        backend_port=settings.BACKEND_PORT,
        quality_thresholds=quality_thresholds.get_all(),
        ppt_video_max_pages=int(ppt_max),
        tts_voice=str(tts_v),
    )


@router.put("/config", response_model=dict)
async def update_system_config(
    config_data: SystemConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新系统配置"""
    log.info(f"管理员 {current_user.username} 更新系统配置")

    updated_fields = []

    if config_data.app_name is not None:
        settings.APP_NAME = config_data.app_name
        updated_fields.append("app_name")
    if config_data.debug is not None:
        settings.DEBUG = config_data.debug
        updated_fields.append("debug")
    if config_data.jwt_expire_minutes is not None:
        settings.JWT_EXPIRE_MINUTES = config_data.jwt_expire_minutes
        updated_fields.append("jwt_expire_minutes")
    if config_data.backend_host is not None:
        settings.BACKEND_HOST = config_data.backend_host
        updated_fields.append("backend_host")
    if config_data.backend_port is not None:
        settings.BACKEND_PORT = config_data.backend_port
        updated_fields.append("backend_port")

    from app.services.config_service import ConfigService
    cs = ConfigService(db)

    if config_data.quality_thresholds is not None:
        from app.core.quality_thresholds import quality_thresholds
        await quality_thresholds.update(config_data.quality_thresholds, db)
        updated_fields.append("quality_thresholds")
    if config_data.ppt_video_max_pages is not None:
        await cs.set("ppt_video_max_pages", config_data.ppt_video_max_pages, "PPT视频最大页数")
        updated_fields.append("ppt_video_max_pages")
    if config_data.tts_voice is not None:
        await cs.set("tts_voice", config_data.tts_voice, "TTS默认音色")
        updated_fields.append("tts_voice")

    return {
        "message": "配置已更新",
        "updated_fields": updated_fields
    }


# ==================== 模型接口管理 ====================

MODEL_PROVIDERS = []


@router.get("/model-providers", response_model=List[dict])
async def get_model_providers(
    current_user: User = Depends(require_admin),
):
    """获取模型提供商列表"""
    log.info(f"管理员 {current_user.username} 获取模型提供商列表")
    
    providers = [
        {
            "id": 1,
            "name": "讯飞星火",
            "provider_type": "xunfei",
            "api_url": "https://xinghuo.xf-yun.com",
            "is_active": True,
            "config": {
                "models": ["lite", "pro", "pro-128k", "max", "ultra", "x1", "x2", "x2-flash"]
            },
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "name": "Qwen-Image-2512",
            "provider_type": "qwen_image",
            "api_url": settings.QWEN_IMAGE_API_URL,
            "is_active": bool(settings.QWEN_IMAGE_APP_ID),
            "config": {
                "model_id": settings.QWEN_IMAGE_MODEL_ID
            },
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 3,
            "name": "Stable Diffusion",
            "provider_type": "stable_diffusion",
            "api_url": settings.SD_API_URL,
            "is_active": bool(settings.SD_API_KEY),
            "config": {},
            "created_at": datetime.now().isoformat()
        }
    ]
    
    return providers


@router.post("/model-providers", response_model=dict, status_code=201)
async def create_model_provider(
    provider_data: ModelProviderCreate,
    current_user: User = Depends(require_admin),
):
    """创建模型提供商"""
    log.info(f"管理员 {current_user.username} 创建模型提供商: {provider_data.name}")
    
    new_provider = {
        "id": len(MODEL_PROVIDERS) + 1,
        "name": provider_data.name,
        "provider_type": provider_data.provider_type,
        "api_url": provider_data.api_url,
        "is_active": True,
        "config": provider_data.config,
        "created_at": datetime.now().isoformat()
    }
    
    MODEL_PROVIDERS.append(new_provider)
    
    return new_provider


@router.put("/model-providers/{provider_id}", response_model=dict)
async def update_model_provider(
    provider_id: int,
    provider_data: ModelProviderUpdate,
    current_user: User = Depends(require_admin),
):
    """更新模型提供商"""
    log.info(f"管理员 {current_user.username} 更新模型提供商: {provider_id}")
    
    for provider in MODEL_PROVIDERS:
        if provider["id"] == provider_id:
            if provider_data.name is not None:
                provider["name"] = provider_data.name
            if provider_data.api_url is not None:
                provider["api_url"] = provider_data.api_url
            if provider_data.is_active is not None:
                provider["is_active"] = provider_data.is_active
            if provider_data.config is not None:
                provider["config"] = provider_data.config
            
            return provider
    
    raise HTTPException(status_code=404, detail="模型提供商不存在")


@router.delete("/model-providers/{provider_id}", status_code=204)
async def delete_model_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
):
    """删除模型提供商"""
    log.info(f"管理员 {current_user.username} 删除模型提供商: {provider_id}")
    
    global MODEL_PROVIDERS
    MODEL_PROVIDERS = [p for p in MODEL_PROVIDERS if p["id"] != provider_id]
    return None


# ==================== 系统监控接口 ====================

@router.get("/monitoring", response_model=MonitoringStats)
async def get_monitoring_stats(
    current_user: User = Depends(require_admin),
):
    """获取系统监控统计"""
    log.info(f"管理员 {current_user.username} 获取系统监控统计")
    
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return MonitoringStats(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_total_mb=memory.total / (1024 * 1024),
            disk_percent=disk.percent,
            uptime_seconds=0,
            request_count=0,
            error_count=0
        )
    except ImportError:
        return MonitoringStats(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            disk_percent=0.0,
            uptime_seconds=0,
            request_count=0,
            error_count=0
        )


@router.get("/stats", response_model=dict)
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统统计信息"""
    log.info(f"管理员 {current_user.username} 获取系统统计信息")
    
    return await stats_service.get_system_stats(db)


# ==================== 日志接口 ====================

@router.get("/logs")
async def get_logs(
    level: Optional[str] = Query("INFO", description="日志级别"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    current_user: User = Depends(require_admin),
):
    """获取系统日志（分页）"""
    log.info(f"管理员 {current_user.username} 获取系统日志")

    import os
    import re

    all_entries = []
    log_dir = "logs"

    if os.path.exists(log_dir):
        for filename in sorted(os.listdir(log_dir), reverse=True):
            if filename.endswith(".log"):
                filepath = os.path.join(log_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*(\S+)\s*-\s*(.*)', line)
                            if match:
                                timestamp, log_level, module, message = match.groups()
                                log_level = log_level.strip()
                                if level and log_level >= level:
                                    all_entries.append(LogEntry(
                                        timestamp=timestamp,
                                        level=log_level,
                                        module=module,
                                        message=message.strip()
                                    ))
                except Exception as e:
                    log.error(f"读取日志文件失败: {e}")

    total = len(all_entries)
    start = (page - 1) * page_size
    items = all_entries[start:start + page_size]

    return {"total": total, "page": page, "page_size": page_size, "items": items}



# ==================== 数据备份接口 ====================

@router.post("/backup", response_model=BackupResponse)
async def create_backup(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建数据备份"""
    log.info(f"管理员 {current_user.username} 创建数据备份")
    
    import os
    import shutil
    import json
    from datetime import datetime
    
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)
    os.makedirs(backup_path, exist_ok=True)
    
    try:
        db_backup_path = os.path.join(backup_path, "database.json")
        
        from sqlalchemy import select, text
        result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema"), 
                                  {"schema": settings.MYSQL_DATABASE})
        tables = result.fetchall()
        
        backup_data = {"tables": {}}
        for table in tables:
            table_name = table[0]
            result = await db.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = result.keys()
            backup_data["tables"][table_name] = {
                "columns": list(columns),
                "rows": [dict(zip(columns, row)) for row in rows]
            }
        
        with open(db_backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
        
        chroma_backup_path = os.path.join(backup_path, "chroma")
        if os.path.exists(settings.CHROMA_PERSIST_DIRECTORY):
            shutil.copytree(settings.CHROMA_PERSIST_DIRECTORY, chroma_backup_path)
        
        backup_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(backup_path)
            for filename in filenames
        )
        
        return BackupResponse(
            success=True,
            message="备份创建成功",
            backup_path=backup_path,
            backup_size=backup_size
        )
        
    except Exception as e:
        log.error(f"备份失败: {e}")
        return BackupResponse(
            success=False,
            message=f"备份失败: {str(e)}"
        )


@router.get("/backups", response_model=List[dict])
async def list_backups(
    current_user: User = Depends(require_admin),
):
    """列出所有备份"""
    log.info(f"管理员 {current_user.username} 列出备份")
    
    import os
    import json
    
    backup_dir = "backups"
    backups = []
    
    if os.path.exists(backup_dir):
        for name in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, name)
            if os.path.isdir(backup_path):
                size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(backup_path)
                    for filename in filenames
                )
                backups.append({
                    "name": name,
                    "path": backup_path,
                    "size": size,
                    "created_at": datetime.fromtimestamp(
                        os.path.getctime(backup_path)
                    ).isoformat()
                })
    
    return sorted(backups, key=lambda x: x["created_at"], reverse=True)


@router.delete("/backups/{backup_name}")
async def delete_backup(
    backup_name: str,
    current_user: User = Depends(require_admin),
):
    """删除指定备份"""
    import os
    import shutil

    log.info(f"管理员 {current_user.username} 删除备份 {backup_name}")
    backup_path = os.path.join("backups", backup_name)
    if not os.path.isdir(backup_path):
        raise HTTPException(status_code=404, detail="备份不存在")
    shutil.rmtree(backup_path)
    return {"success": True, "message": f"备份 {backup_name} 已删除"}


class RestoreRequest(BaseModel):
    """恢复请求"""
    backup_name: str = Field(..., description="备份目录名称")


@router.post("/restore")
async def restore_backup(
    request: RestoreRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """从备份恢复数据"""
    import os
    import shutil
    import json

    backup_path = os.path.join("backups", request.backup_name)
    if not os.path.isdir(backup_path):
        raise HTTPException(status_code=404, detail="备份不存在")

    log.info(f"管理员 {current_user.username} 开始从备份 {request.backup_name} 恢复数据")

    try:
        db_backup_file = os.path.join(backup_path, "database.json")
        if os.path.exists(db_backup_file):
            with open(db_backup_file, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            for table_name, table_data in backup_data.get("tables", {}).items():
                columns = table_data["columns"]
                rows = table_data["rows"]
                if not rows:
                    continue
                await db.execute(text(f"DELETE FROM {table_name}"))
                for row in rows:
                    placeholders = ", ".join([f":{col}" for col in columns])
                    col_names = ", ".join(columns)
                    values = {col: (json.dumps(row[col]) if isinstance(row[col], (dict, list)) else row[col]) for col in columns}
                    await db.execute(text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"), values)
            await db.commit()

        chroma_backup = os.path.join(backup_path, "chroma")
        chroma_dir = settings.CHROMA_PERSIST_DIRECTORY
        if os.path.exists(chroma_backup):
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
            shutil.copytree(chroma_backup, chroma_dir)

        return {"success": True, "message": f"从备份 {request.backup_name} 恢复成功"}
    except Exception as e:
        log.error(f"恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.get("/system/stats", response_model=SystemStatsResponse)
async def get_system_data_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统数据统计（详细版）"""
    import os
    from app.models import Course, LearningRecord, LearningResource

    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    courses_count = (await db.execute(select(func.count(Course.id)))).scalar() or 0
    records_count = (await db.execute(select(func.count(LearningRecord.id)))).scalar() or 0
    resources_count = (await db.execute(select(func.count(LearningResource.id)))).scalar() or 0

    def dir_size(path: str) -> int:
        if not os.path.exists(path):
            return 0
        return sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fns in os.walk(path) for f in fns)

    return SystemStatsResponse(
        users_count=users_count,
        courses_count=courses_count,
        learning_records_count=records_count,
        resources_count=resources_count,
        disk_usage_bytes=dir_size("."),
        chroma_size_bytes=dir_size(settings.CHROMA_PERSIST_DIRECTORY),
        logs_size_bytes=dir_size("logs"),
    )


@router.post("/cache/clear")
async def clear_cache(
    request: CacheClearRequest,
    current_user: User = Depends(require_admin),
):
    """清理缓存"""
    import os
    import shutil

    log.info(f"管理员 {current_user.username} 清理缓存: {request.target}")
    results = []

    if request.target in ("redis", "all"):
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.flushdb()
            results.append("Redis 缓存已清空")
        except Exception as e:
            results.append(f"Redis 清理失败: {str(e)}")

    if request.target in ("chroma", "all"):
        try:
            chroma_dir = settings.CHROMA_PERSIST_DIRECTORY
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
                os.makedirs(chroma_dir, exist_ok=True)
            results.append("ChromaDB 数据已清空")
        except Exception as e:
            results.append(f"ChromaDB 清理失败: {str(e)}")

    return {"success": True, "results": results}


@router.delete("/logs/clean")
async def clean_logs(
    days: int = Query(7, ge=1, le=365, description="保留天数"),
    current_user: User = Depends(require_admin),
):
    """清理过期日志文件"""
    import os
    import time

    log.info(f"管理员 {current_user.username} 清理 {days} 天前的日志")
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        return {"success": True, "deleted_count": 0, "freed_bytes": 0}

    cutoff = time.time() - days * 86400
    deleted_count = 0
    freed_bytes = 0

    for name in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, name)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
            freed_bytes += os.path.getsize(file_path)
            os.remove(file_path)
            deleted_count += 1

    log.info(f"清理完成: 删除 {deleted_count} 个文件，释放 {freed_bytes} 字节")
    return {"success": True, "deleted_count": deleted_count, "freed_bytes": freed_bytes}


# ==================== 内容安全审核接口 ====================

@router.get("/content-review", response_model=PageResponse[ContentReviewResponse])
async def get_content_for_review(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取待审核内容"""
    log.info(f"管理员 {current_user.username} 获取待审核内容")
    
    from app.models import ResourceReview
    from sqlalchemy import select, func
    
    query = select(ResourceReview)
    if status:
        query = query.where(ResourceReview.status == status)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(ResourceReview.created_at.desc())
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            ContentReviewResponse(
                id=r.id,
                content_type=r.resource_type,
                content=r.resource_content[:200] + "..." if len(r.resource_content) > 200 else r.resource_content,
                status=r.status,
                reviewer_id=r.reviewer_id,
                review_comment=r.review_comment,
                created_at=r.created_at
            ) for r in items
        ]
    )


@router.put("/content-review/{content_id}/action", response_model=dict)
async def review_content(
    content_id: int,
    action_data: ContentReviewAction,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核内容"""
    log.info(f"管理员 {current_user.username} 审核内容: {content_id}, 操作: {action_data.action}")
    
    from app.models import ResourceReview
    from sqlalchemy import select
    
    result = await db.execute(
        select(ResourceReview).where(ResourceReview.id == content_id)
    )
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    review.status = "approved" if action_data.action == "approve" else "rejected"
    review.reviewer_id = current_user.id
    review.review_comment = action_data.comment
    review.reviewed_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": f"内容已{'通过' if action_data.action == 'approve' else '拒绝'}审核",
        "content_id": content_id
    }


# ==================== 内容安全（敏感词过滤） ====================

class ContentSecurityToggle(BaseModel):
    enabled: bool

class SecurityWordsRequest(BaseModel):
    category: str
    words: List[str]

class SecurityWordDelete(BaseModel):
    category: str
    word: str


@router.get("/content-security")
async def get_content_security(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取内容安全配置（开关 + 词库）"""
    from app.core.content_security import content_security
    if not content_security._loaded:
        await content_security.load_from_db(db)
    return {
        "enabled": content_security.is_enabled(),
        "words": content_security.get_all_words(),
    }


@router.put("/content-security")
async def update_content_security(
    data: ContentSecurityToggle,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新内容安全开关"""
    from app.core.content_security import content_security
    await content_security.set_enabled(data.enabled, db)
    return {"message": f"内容安全已{'开启' if data.enabled else '关闭'}", "enabled": data.enabled}


@router.post("/content-security/words")
async def add_security_words(
    data: SecurityWordsRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加敏感词"""
    from app.core.content_security import content_security
    added = await content_security.add_words(data.category, data.words, db)
    return {"message": f"添加 {len(added)} 个敏感词", "added": added, "words": content_security.get_all_words()}


@router.delete("/content-security/words")
async def delete_security_word(
    data: SecurityWordDelete,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除敏感词"""
    from app.core.content_security import content_security
    ok = await content_security.remove_word(data.category, data.word, db)
    if not ok:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    return {"message": f"已删除: {data.word}", "words": content_security.get_all_words()}


@router.get("/content-security/logs")
async def get_security_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取敏感词过滤记录"""
    from app.core.content_security import content_security
    logs, total = await content_security.get_logs(db, page, page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": logs}


# ==================== 模型管理接口 ====================

class ModelUpdateRequest(BaseModel):
    """模型切换请求"""
    model_config = {"protected_namespaces": ()}
    model_key: str = Field(..., description="模型标识")


@router.get("/models")
async def get_models(
    current_user: User = Depends(require_admin),
):
    """获取完整模型配置（文本/图片/视频/Agent映射）"""
    from app.core.model_manager import model_manager
    return model_manager.get_all_config()


@router.put("/models/agent/{agent_name}")
async def update_agent_model(
    agent_name: str,
    data: ModelUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """切换 Agent 使用的文本模型"""
    from app.core.model_manager import model_manager
    try:
        model_manager.set_agent_text_model(agent_name, data.model_key)
        await model_manager.save_to_db(db, "agent_text_models")
        return {"message": f"Agent [{agent_name}] 文本模型切换为 [{data.model_key}]"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/models/image/{task_name}")
async def update_image_model(
    task_name: str,
    data: ModelUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """切换图片任务使用的模型"""
    from app.core.model_manager import model_manager
    try:
        model_manager.set_image_task_model(task_name, data.model_key)
        await model_manager.save_to_db(db, "image_task_models")
        return {"message": f"图片任务 [{task_name}] 模型切换为 [{data.model_key}]"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/models/video/{task_name}")
async def update_video_model(
    task_name: str,
    data: ModelUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """切换视频任务使用的模型（预留）"""
    from app.core.model_manager import model_manager
    try:
        model_manager.set_video_task_model(task_name, data.model_key)
        await model_manager.save_to_db(db, "video_task_models")
        return {"message": f"视频任务 [{task_name}] 模型切换为 [{data.model_key}]"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class TtsVoiceUpdateRequest(BaseModel):
    voice: str = Field(..., description="音色 ID，如 x4_yezi, x4_xiaoyan")


@router.put("/tts/voice")
async def update_tts_voice(
    data: TtsVoiceUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """切换 TTS 音色"""
    from app.core.model_manager import TTS_VOICES
    if data.voice not in TTS_VOICES:
        raise HTTPException(status_code=400, detail=f"不支持的音色: {data.voice}，可选: {list(TTS_VOICES.keys())}")
    from app.services.config_service import ConfigService
    await ConfigService(db).set("tts_voice", data.voice, "TTS 音色配置")
    # 同步更新 ppt_video_config 常量（运行时生效）
    from app.core import ppt_video_config
    ppt_video_config.TTS_VOICE = data.voice
    return {"message": f"TTS 音色切换为 [{TTS_VOICES[data.voice]['name']}]", "voice": data.voice}


@router.get("/tts/voices")
async def get_tts_voices(
    current_user: User = Depends(require_admin),
):
    """获取可用的 TTS 音色列表"""
    from app.core.model_manager import TTS_VOICES
    from app.core import ppt_video_config
    return {
        "current_voice": ppt_video_config.TTS_VOICE,
        "voices": [{"id": k, "name": v["name"], "gender": v["gender"]} for k, v in TTS_VOICES.items()],
    }
