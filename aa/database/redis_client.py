"""
database/redis_client.py
مدیریت async Redis برای کش و session
"""

import json
import redis.asyncio as aioredis
from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, CACHE_TTL_USER


class RedisClient:
    """Singleton async Redis manager"""

    _redis: aioredis.Redis | None = None

    # ── اتصال / قطع ─────────────────────────────────────────────
    @classmethod
    async def connect(cls) -> None:
        cls._redis = aioredis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
        )
        await cls._redis.ping()
        print("✅ Redis connected")

    @classmethod
    async def disconnect(cls) -> None:
        if cls._redis:
            await cls._redis.aclose()
            print("🔌 Redis disconnected")

    @classmethod
    def _r(cls) -> aioredis.Redis:
        if cls._redis is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return cls._redis

    # ════════════════════════════════════════════════════════════
    #  کش کاربر
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def cache_user(cls, user_id: int, data: dict, ttl: int = CACHE_TTL_USER) -> None:
        key = f"user:{user_id}"
        await cls._r().setex(key, ttl, json.dumps(data, default=str))

    @classmethod
    async def get_cached_user(cls, user_id: int) -> dict | None:
        key = f"user:{user_id}"
        raw = await cls._r().get(key)
        return json.loads(raw) if raw else None

    @classmethod
    async def invalidate_user(cls, user_id: int) -> None:
        await cls._r().delete(f"user:{user_id}")

    # ════════════════════════════════════════════════════════════
    #  State مکالمه (FSM ساده)
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_state(cls, user_id: int, state: str, ttl: int = 600) -> None:
        await cls._r().setex(f"state:{user_id}", ttl, state)

    @classmethod
    async def get_state(cls, user_id: int) -> str | None:
        return await cls._r().get(f"state:{user_id}")

    @classmethod
    async def clear_state(cls, user_id: int) -> None:
        await cls._r().delete(f"state:{user_id}")

    # ════════════════════════════════════════════════════════════
    #  داده موقت مکالمه
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_temp(cls, user_id: int, key: str, value: str, ttl: int = 600) -> None:
        await cls._r().setex(f"temp:{user_id}:{key}", ttl, value)

    @classmethod
    async def get_temp(cls, user_id: int, key: str) -> str | None:
        return await cls._r().get(f"temp:{user_id}:{key}")

    @classmethod
    async def clear_temp(cls, user_id: int) -> None:
        keys = await cls._r().keys(f"temp:{user_id}:*")
        if keys:
            await cls._r().delete(*keys)

    # ════════════════════════════════════════════════════════════
    #  زبان کاربر
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_lang(cls, user_id: int, lang: str) -> None:
        await cls._r().setex(f"lang:{user_id}", 86400 * 30, lang)

    @classmethod
    async def get_lang(cls, user_id: int) -> str | None:
        return await cls._r().get(f"lang:{user_id}")

    @classmethod
    async def clear_lang(cls, user_id: int) -> None:
        await cls._r().delete(f"lang:{user_id}")

    # ════════════════════════════════════════════════════════════
    #  Rate Limit
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def check_rate_limit(
        cls,
        user_id: int,
        action: str,
        max_calls: int = 5,
        window: int = 60,
    ) -> bool:
        """True = مجاز | False = بلاک شده"""
        key = f"rl:{user_id}:{action}"
        count = await cls._r().incr(key)
        if count == 1:
            await cls._r().expire(key, window)
        return count <= max_calls

    # ════════════════════════════════════════════════════════════
    #  آمار آنلاین
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_online(cls, user_id: int, ttl: int = 300) -> None:
        await cls._r().setex(f"online:{user_id}", ttl, "1")

    @classmethod
    async def count_online(cls) -> int:
        keys = await cls._r().keys("online:*")
        return len(keys)
