"""Cache adapters for in-memory and Redis caching."""

import asyncio
import fnmatch
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import pickle
from abc import ABC, abstractmethod

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from ..application.services import CachePort


logger = logging.getLogger(__name__)


class MemoryCacheAdapter:
    """In-memory cache adapter for development and testing."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        async with self._lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
                del self.cache[key]
                return None
            
            # Update access time for LRU
            entry["accessed_at"] = datetime.now()
            
            return entry["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        async with self._lock:
            # Evict if at max size
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            expires_at = None
            if ttl or self.default_ttl:
                expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            
            self.cache[key] = {
                "value": value,
                "created_at": datetime.now(),
                "accessed_at": datetime.now(),
                "expires_at": expires_at
            }
    
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        async with self._lock:
            self.cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self.cache.clear()
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern (glob-style matching)."""
        async with self._lock:
            if pattern == "*":
                return list(self.cache.keys())
            else:
                # Use fnmatch for proper glob pattern matching
                return list(fnmatch.filter(self.cache.keys(), pattern))
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.cache:
            return
        
        # Find LRU item
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k]["accessed_at"]
        )
        
        del self.cache[lru_key]
        logger.debug(f"Evicted LRU cache item: {lru_key}")
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            now = datetime.now()
            expired_count = sum(
                1 for entry in self.cache.values()
                if entry.get("expires_at") and now > entry["expires_at"]
            )
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "expired_count": expired_count,
                "hit_rate": 0.0,  # Would need to track hits/misses
                "memory_usage": len(pickle.dumps(self.cache))
            }


class RedisCacheAdapter:
    """Redis cache adapter for production use."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "design_assistant:",
        default_ttl: int = 3600,
        max_connections: int = 10
    ):
        if redis is None:
            raise ImportError("redis package is required for RedisCacheAdapter")
        
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def __aenter__(self):
        await self._ensure_connected()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if self._client is None:
            self._connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False  # Handle binary data
            )
            self._client = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            try:
                await self._client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
    
    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        await self._ensure_connected()
        
        try:
            data = await self._client.get(self._make_key(key))
            if data is None:
                return None
            
            # Deserialize the data
            return pickle.loads(data)
            
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        await self._ensure_connected()
        
        try:
            # Serialize the value
            data = pickle.dumps(value)
            
            # Set with TTL
            await self._client.setex(
                self._make_key(key),
                ttl or self.default_ttl,
                data
            )
            
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        await self._ensure_connected()
        
        try:
            await self._client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
    
    async def clear(self, pattern: str = "*") -> None:
        """Clear cached values matching pattern."""
        await self._ensure_connected()
        
        try:
            # Get keys matching pattern
            keys = await self._client.keys(self._make_key(pattern))
            if keys:
                await self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to clear cache pattern {pattern}: {e}")
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        await self._ensure_connected()
        
        try:
            keys = await self._client.keys(self._make_key(pattern))
            # Remove prefix from returned keys
            return [key.decode().replace(self.prefix, "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get cache keys {pattern}: {e}")
            return []
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        await self._ensure_connected()
        
        try:
            return bool(await self._client.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> None:
        """Set TTL for existing key."""
        await self._ensure_connected()
        
        try:
            await self._client.expire(self._make_key(key), ttl)
        except Exception as e:
            logger.error(f"Failed to set TTL for cache key {key}: {e}")
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key."""
        await self._ensure_connected()
        
        try:
            return await self._client.ttl(self._make_key(key))
        except Exception as e:
            logger.error(f"Failed to get TTL for cache key {key}: {e}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment integer value."""
        await self._ensure_connected()
        
        try:
            return await self._client.incrby(self._make_key(key), amount)
        except Exception as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return 0
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        await self._ensure_connected()
        
        try:
            info = await self._client.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                ),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


class TieredCacheAdapter:
    """Tiered cache using both memory and Redis."""
    
    def __init__(
        self,
        memory_cache: MemoryCacheAdapter,
        redis_cache: RedisCacheAdapter,
        memory_ttl: int = 300,  # 5 minutes in memory
        redis_ttl: int = 3600   # 1 hour in Redis
    ):
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
        self.memory_ttl = memory_ttl
        self.redis_ttl = redis_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from memory first, then Redis."""
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try Redis cache
        value = await self.redis_cache.get(key)
        if value is not None:
            # Store in memory cache for faster access
            await self.memory_cache.set(key, value, self.memory_ttl)
            return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set in both caches."""
        # Set in memory cache
        await self.memory_cache.set(key, value, self.memory_ttl)
        
        # Set in Redis cache
        await self.redis_cache.set(key, value, ttl or self.redis_ttl)
    
    async def delete(self, key: str) -> None:
        """Delete from both caches."""
        await self.memory_cache.delete(key)
        await self.redis_cache.delete(key)
    
    async def clear(self) -> None:
        """Clear both caches."""
        await self.memory_cache.clear()
        await self.redis_cache.clear()
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get unique keys from both caches matching pattern."""
        # Get keys from both caches
        memory_keys = await self.memory_cache.keys(pattern)
        redis_keys = await self.redis_cache.keys(pattern)
        
        # Convert to sets to ensure uniqueness, then union and convert back to list
        unique_keys = set(memory_keys) | set(redis_keys)
        return list(unique_keys)
    
    async def stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        memory_stats = await self.memory_cache.stats()
        redis_stats = await self.redis_cache.stats()
        
        return {
            "memory_cache": memory_stats,
            "redis_cache": redis_stats,
            "tier": "memory_redis"
        }