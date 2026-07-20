import redis.asyncio as aioredis
from typing import Optional, Any
from app.core.config import settings
from app.core.logger import log

# 全局 Redis 客户端实例
redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端实例"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await redis_client.ping()
            log.info("Redis 连接成功")
        except Exception as e:
            log.error(f"Redis 连接失败: {e}")
            raise
    return redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        log.info("Redis 连接已关闭")


async def redis_set(key: str, value: Any, expire: Optional[int] = None):
    """设置键值"""
    r = await get_redis()
    await r.set(key, value, ex=expire)


async def redis_get(key: str) -> Optional[str]:
    """获取键值"""
    r = await get_redis()
    return await r.get(key)


async def redis_delete(key: str):
    """删除键"""
    r = await get_redis()
    await r.delete(key)


async def redis_exists(key: str) -> bool:
    """检查键是否存在"""
    r = await get_redis()
    return bool(await r.exists(key))


async def redis_expire(key: str, seconds: int):
    """设置过期时间"""
    r = await get_redis()
    await r.expire(key, seconds)
