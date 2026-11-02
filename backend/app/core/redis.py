import logging
from typing import AsyncGenerator
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis Connection Pool
redis_pool = aioredis.ConnectionPool.from_url(
    settings.redis_connection_url,
    max_connections=20,
    decode_responses=True,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency providing the async Redis client."""
    yield redis_client


async def set_user_revocation_epoch(user_id: str, epoch: int, ttl: int = 900) -> bool:
    """Sets the user revocation epoch in Redis with a 15-minute TTL."""
    try:
        await redis_client.set(f"user_revocation_epoch:{user_id}", str(epoch), ex=ttl)
        return True
    except Exception as e:
        logger.error("Failed to set user revocation epoch in Redis: %s", e)
        return False


async def get_user_revocation_epoch(user_id: str) -> int | None:
    """Retrieves the user revocation epoch from Redis, or None if not set or Redis is down."""
    try:
        val = await redis_client.get(f"user_revocation_epoch:{user_id}")
        return int(val) if val is not None else None
    except Exception as e:
        logger.warning("Failed to fetch user revocation epoch from Redis: %s", e)
        return None


async def set_grace_stash(family_id: str, encrypted_token: str, ttl: int = 15) -> bool:
    """Stores the AES-256-GCM encrypted refresh token in the 15-second grace stash."""
    try:
        await redis_client.set(f"rt_grace:{family_id}", encrypted_token, ex=ttl)
        return True
    except Exception as e:
        logger.error("Failed to write to Redis grace stash: %s", e)
        return False


async def get_grace_stash(family_id: str) -> str | None:
    """Fetches the encrypted refresh token from the Redis grace stash."""
    try:
        return await redis_client.get(f"rt_grace:{family_id}")
    except Exception as e:
        logger.warning("Failed to read from Redis grace stash: %s", e)
        return None


async def delete_grace_stash(family_id: str) -> bool:
    """Deletes the grace stash entry for the token family."""
    try:
        await redis_client.delete(f"rt_grace:{family_id}")
        return True
    except Exception as e:
        logger.warning("Failed to delete Redis grace stash: %s", e)
        return False


async def close_redis():
    """Gracefully closes Redis connection pool on application shutdown."""
    await redis_client.aclose()
    await redis_pool.disconnect()
