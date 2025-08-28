"""Factory for creating repository instances with proper dependency injection."""

import logging
from typing import Optional

from google.cloud import firestore
from onshape_api.api.api_base import Api

from .storage_interfaces import SessionStorageAdapter, BomStorageAdapter, CacheStorageAdapter, StorageConfig
from .firestore_session_repository import FirestoreSessionRepository
from .onshape_bom_repository import OnshapeBomRepository
from .memory_cache_repository import MemoryCacheRepository


logger = logging.getLogger(__name__)


class RepositoryFactory:
    """Factory for creating storage repository instances."""
    
    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig.from_env()
        self._session_repo: Optional[SessionStorageAdapter] = None
        self._bom_repo: Optional[BomStorageAdapter] = None
        self._cache_repo: Optional[CacheStorageAdapter] = None
    
    def get_session_repository(self, firestore_client: Optional[firestore.Client] = None) -> SessionStorageAdapter:
        """Get session repository instance (singleton)."""
        if self._session_repo is None:
            if firestore_client is None:
                firestore_client = firestore.Client()
                
            self._session_repo = FirestoreSessionRepository(firestore_client, self.config)
            logger.debug("Created Firestore session repository")
        
        return self._session_repo
    
    def get_bom_repository(self, onshape_api: Api) -> BomStorageAdapter:
        """Get BOM repository instance.
        
        Note: Creates new instance each time since API client may change.
        In the future, could implement caching based on API client identity.
        """
        bom_repo = OnshapeBomRepository(onshape_api, self.config)
        logger.debug("Created Onshape BOM repository")
        return bom_repo
    
    def get_cache_repository(self) -> CacheStorageAdapter:
        """Get cache repository instance (singleton)."""
        if self._cache_repo is None:
            self._cache_repo = MemoryCacheRepository(self.config)
            logger.debug("Created memory cache repository")
        
        return self._cache_repo
    
    def cleanup_repositories(self) -> None:
        """Clean up repository resources."""
        if self._cache_repo:
            # Clean up expired cache entries
            if hasattr(self._cache_repo, 'cleanup_expired'):
                expired_count = self._cache_repo.cleanup_expired()
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired cache entries")
    
    def get_repository_status(self) -> dict:
        """Get status of all repositories for health checks."""
        status = {
            "session_repository": "initialized" if self._session_repo else "not_initialized",
            "bom_repository": "factory_ready",  # Created on demand
            "cache_repository": "initialized" if self._cache_repo else "not_initialized",
            "config": {
                "use_json_tree_storage": self.config.use_json_tree_storage,
                "session_collection": self.config.session_collection_name,
                "cache_ttl_seconds": self.config.default_cache_ttl_seconds
            }
        }
        
        # Add cache stats if available
        if self._cache_repo and hasattr(self._cache_repo, 'get_cache_stats'):
            status["cache_stats"] = self._cache_repo.get_cache_stats()
        
        return status


# Global factory instance
_repository_factory: Optional[RepositoryFactory] = None


def get_repository_factory(config: Optional[StorageConfig] = None) -> RepositoryFactory:
    """Get global repository factory instance (singleton)."""
    global _repository_factory
    if _repository_factory is None:
        _repository_factory = RepositoryFactory(config)
        logger.info("Created repository factory")
    
    return _repository_factory


def reset_repository_factory() -> None:
    """Reset factory instance (mainly for testing)."""
    global _repository_factory
    if _repository_factory:
        _repository_factory.cleanup_repositories()
    _repository_factory = None