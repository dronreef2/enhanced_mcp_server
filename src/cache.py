"""Sistema de cache inteligente com Redis (conexão preguiçosa)."""
import json
import time
from typing import Any, Optional, Callable, Dict
import redis
from functools import wraps
import threading
from enhanced_mcp_server.settings import settings
from enhanced_mcp_server.logging import get_logger

logger = get_logger(__name__)

class Cache:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._redis_checked = False
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_redis_client(self) -> Optional[redis.Redis]:
        with self._lock:
            if not self._redis_checked:
                self._redis_checked = True
                if settings.redis_url:
                    try:
                        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
                        client.ping()
                        self._redis_client = client
                        logger.info("Redis cache connected successfully.")
                    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                        logger.warning(f"Failed to connect to Redis, using memory cache: {e}")
                        self._redis_client = None
                else:
                    logger.info("Redis not configured, using memory cache.")
        return self._redis_client

    def get(self, key: str) -> Optional[Any]:
        redis_client = self.get_redis_client()
        if redis_client:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        else:
            with self._lock:
                entry = self._memory_cache.get(key)
                if entry and time.time() < entry["expires_at"]:
                    return entry["value"]
        return None

    def set(self, key: str, value: Any, ttl: int):
        redis_client = self.get_redis_client()
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
        else:
            with self._lock:
                self._memory_cache[key] = {"value": value, "expires_at": time.time() + ttl}

def cached(ttl: Optional[int] = None):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            final_ttl = ttl if ttl is not None else settings.cache_ttl
            cache_key = f"{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", key=cache_key)
                return cached_result

            logger.debug("Cache miss", key=cache_key)
            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, final_ttl)
            return result
        return wrapper
    return decorator

cache = Cache()