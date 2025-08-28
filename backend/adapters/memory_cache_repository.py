"""Simple in-memory cache implementation of cache storage adapter."""

import logging
import time
import threading
from typing import Optional, Dict, Any
import fnmatch

from .storage_interfaces import CacheStorageAdapter, StorageConfig


logger = logging.getLogger(__name__)


class MemoryCacheRepository(CacheStorageAdapter):
    """Simple in-memory cache implementation.
    
    Note: This is not persistent across server restarts.
    For production, consider Redis or Firestore caching.
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig.from_env()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def set_cache(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        """Store data in cache with TTL."""
        try:
            with self._lock:
                expiry_time = time.time() + ttl_seconds
                cache_key = f"{self.config.cache_key_prefix}:{key}"
                
                self._cache[cache_key] = {
                    "value": value,
                    "expires_at": expiry_time,
                    "created_at": time.time()
                }
                
                logger.debug(f"Cached data for key: {cache_key} (TTL: {ttl_seconds}s)")
                
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {str(e)}")
    
    def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache."""
        try:
            with self._lock:
                cache_key = f"{self.config.cache_key_prefix}:{key}"
                
                if cache_key not in self._cache:
                    return None
                
                cache_entry = self._cache[cache_key]
                current_time = time.time()
                
                # Check if expired
                if current_time > cache_entry["expires_at"]:
                    del self._cache[cache_key]
                    logger.debug(f"Cache expired for key: {cache_key}")
                    return None
                
                logger.debug(f"Cache hit for key: {cache_key}")
                return cache_entry["value"]
                
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {str(e)}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete data from cache."""
        try:
            with self._lock:
                cache_key = f"{self.config.cache_key_prefix}:{key}"
                
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.debug(f"Deleted cache for key: {cache_key}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {str(e)}")
            return False
    
    def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern. Returns count cleared."""
        try:
            with self._lock:
                full_pattern = f"{self.config.cache_key_prefix}:{pattern}"
                keys_to_delete = []
                
                # Find matching keys
                for cache_key in self._cache.keys():
                    if fnmatch.fnmatch(cache_key, full_pattern):
                        keys_to_delete.append(cache_key)
                
                # Delete matching keys
                for cache_key in keys_to_delete:
                    del self._cache[cache_key]
                
                logger.debug(f"Cleared {len(keys_to_delete)} cache entries matching pattern: {pattern}")
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Failed to clear cache pattern {pattern}: {str(e)}")
            return 0
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries. Returns count cleaned."""
        try:
            with self._lock:
                current_time = time.time()
                keys_to_delete = []
                
                # Find expired keys
                for cache_key, cache_entry in self._cache.items():
                    if current_time > cache_entry["expires_at"]:
                        keys_to_delete.append(cache_key)
                
                # Delete expired keys
                for cache_key in keys_to_delete:
                    del self._cache[cache_key]
                
                if keys_to_delete:
                    logger.debug(f"Cleaned up {len(keys_to_delete)} expired cache entries")
                
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            with self._lock:
                current_time = time.time()
                total_entries = len(self._cache)
                expired_entries = 0
                
                for cache_entry in self._cache.values():
                    if current_time > cache_entry["expires_at"]:
                        expired_entries += 1
                
                return {
                    "total_entries": total_entries,
                    "active_entries": total_entries - expired_entries,
                    "expired_entries": expired_entries,
                    "cache_key_prefix": self.config.cache_key_prefix
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {"error": str(e)}