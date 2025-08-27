"""FastAPI dependencies for dependency injection."""

from typing import Dict, Any, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request

from ..application import (
    BomService, ThumbnailService, MetadataService, FabPackService, QueryService
)
from ..adapters import (
    OnshapeClientAdapter, StructuredStorageAdapter, BlobStorageAdapter,
    MemoryCacheAdapter, RedisCacheAdapter, TieredCacheAdapter,
    WebhookNotificationAdapter, CompositeNotificationAdapter, NullNotificationAdapter
)
from ..infrastructure.config import DesignAssistantConfig, get_config
from ..infrastructure.auth import AuthManager
from ..infrastructure.logging import get_logger


logger = get_logger("dependencies")


# Configuration dependencies
@lru_cache()
def get_config_cached() -> DesignAssistantConfig:
    """Get cached configuration."""
    return get_config()


def get_auth_manager(config: DesignAssistantConfig = Depends(get_config_cached)) -> AuthManager:
    """Get authentication manager."""
    return AuthManager(config.security)


def get_auth_data(request: Request) -> Optional[Dict[str, Any]]:
    """Get authentication data from request state."""
    return getattr(request.state, "auth_data", None)


def require_auth(auth_data: Optional[Dict[str, Any]] = Depends(get_auth_data)) -> Dict[str, Any]:
    """Require authentication for endpoint."""
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return auth_data


def require_permission(permission: str):
    """Require specific permission for endpoint."""
    def _require_permission(
        auth_data: Dict[str, Any] = Depends(require_auth),
        auth_manager: AuthManager = Depends(get_auth_manager)
    ) -> Dict[str, Any]:
        if not auth_manager.check_permission(auth_data, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return auth_data
    
    return _require_permission


# Adapter dependencies
@lru_cache()
def get_onshape_client(config: DesignAssistantConfig = Depends(get_config_cached)) -> OnshapeClientAdapter:
    """Get Onshape client adapter."""
    return OnshapeClientAdapter(
        base_url=config.onshape.base_url,
        access_key=config.onshape.access_key,
        secret_key=config.onshape.secret_key,
        timeout=config.onshape.timeout,
        max_retries=config.onshape.max_retries,
        retry_delay=config.onshape.retry_delay
    )


@lru_cache()
def get_storage_adapter(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    config: DesignAssistantConfig = Depends(get_config_cached)
) -> StructuredStorageAdapter:
    """Get structured storage adapter."""
    return StructuredStorageAdapter(
        onshape_client=onshape_client,
        storage_element_id=config.onshape.structured_storage_element_id
    )


@lru_cache()
def get_blob_storage_adapter(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    config: DesignAssistantConfig = Depends(get_config_cached)
) -> BlobStorageAdapter:
    """Get blob storage adapter."""
    return BlobStorageAdapter(
        onshape_client=onshape_client,
        blob_element_id=config.onshape.blob_storage_element_id
    )


@lru_cache()
def get_cache_adapter(config: DesignAssistantConfig = Depends(get_config_cached)):
    """Get cache adapter based on configuration."""
    
    if config.cache.type == "memory":
        return MemoryCacheAdapter(
            max_size=config.cache.max_memory_size,
            default_ttl=config.cache.default_ttl
        )
    
    elif config.cache.type == "redis":
        try:
            return RedisCacheAdapter(
                redis_url=config.cache.redis_url,
                prefix=config.cache.redis_prefix,
                default_ttl=config.cache.default_ttl,
                max_connections=config.cache.max_redis_connections
            )
        except ImportError:
            logger.warning("Redis not available, falling back to memory cache")
            return MemoryCacheAdapter(
                max_size=config.cache.max_memory_size,
                default_ttl=config.cache.default_ttl
            )
    
    elif config.cache.type == "tiered":
        memory_cache = MemoryCacheAdapter(
            max_size=config.cache.max_memory_size,
            default_ttl=300  # 5 minutes in memory
        )
        
        try:
            redis_cache = RedisCacheAdapter(
                redis_url=config.cache.redis_url,
                prefix=config.cache.redis_prefix,
                default_ttl=config.cache.default_ttl,
                max_connections=config.cache.max_redis_connections
            )
            
            return TieredCacheAdapter(
                memory_cache=memory_cache,
                redis_cache=redis_cache
            )
        except ImportError:
            logger.warning("Redis not available, using memory cache only")
            return memory_cache
    
    else:
        logger.warning(f"Unknown cache type {config.cache.type}, using memory cache")
        return MemoryCacheAdapter(
            max_size=config.cache.max_memory_size,
            default_ttl=config.cache.default_ttl
        )


@lru_cache()
def get_notification_adapter(config: DesignAssistantConfig = Depends(get_config_cached)):
    """Get notification adapter based on configuration."""
    
    if not config.notifications.enabled:
        return NullNotificationAdapter()
    
    adapters = []
    
    # Add webhook adapter if URLs configured
    if config.notifications.webhook_urls:
        webhook_adapter = WebhookNotificationAdapter(
            webhook_urls=config.notifications.webhook_urls
        )
        adapters.append(webhook_adapter)
    
    # Add Slack adapter if configured
    if config.notifications.slack_webhook_url:
        from ..adapters.notification_adapter import SlackNotificationAdapter
        slack_adapter = SlackNotificationAdapter(
            webhook_url=config.notifications.slack_webhook_url,
            channel=config.notifications.slack_channel
        )
        adapters.append(slack_adapter)
    
    # Add email adapter if configured
    if config.notifications.email_enabled and config.notifications.smtp_server:
        from ..adapters.notification_adapter import EmailNotificationAdapter
        email_adapter = EmailNotificationAdapter(
            smtp_server=config.notifications.smtp_server,
            smtp_port=config.notifications.smtp_port,
            username=config.notifications.smtp_username,
            password=config.notifications.smtp_password,
            from_email=config.notifications.from_email,
            to_emails=config.notifications.to_emails
        )
        adapters.append(email_adapter)
    
    # Return composite adapter if multiple, single adapter if one, null if none
    if len(adapters) > 1:
        return CompositeNotificationAdapter(adapters)
    elif len(adapters) == 1:
        return adapters[0]
    else:
        return NullNotificationAdapter()


# Service dependencies
@lru_cache()
def get_bom_service(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    storage_adapter: StructuredStorageAdapter = Depends(get_storage_adapter),
    cache_adapter = Depends(get_cache_adapter),
    notification_adapter = Depends(get_notification_adapter)
) -> BomService:
    """Get BOM service with injected dependencies."""
    return BomService(
        onshape_api=onshape_client,
        storage=storage_adapter,
        cache=cache_adapter,
        notification=notification_adapter
    )


@lru_cache()
def get_thumbnail_service(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    blob_storage_adapter: BlobStorageAdapter = Depends(get_blob_storage_adapter),
    notification_adapter = Depends(get_notification_adapter)
) -> ThumbnailService:
    """Get thumbnail service with injected dependencies."""
    return ThumbnailService(
        onshape_api=onshape_client,
        storage=blob_storage_adapter,
        notification=notification_adapter
    )


@lru_cache()
def get_metadata_service(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client)
) -> MetadataService:
    """Get metadata service with injected dependencies."""
    return MetadataService(onshape_api=onshape_client)


@lru_cache()
def get_fab_pack_service(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    blob_storage_adapter: BlobStorageAdapter = Depends(get_blob_storage_adapter)
) -> FabPackService:
    """Get fabrication package service with injected dependencies."""
    return FabPackService(
        onshape_api=onshape_client,
        storage=blob_storage_adapter
    )


# Query adapter (placeholder - would need actual implementation)
class QueryAdapter:
    """Adapter for query operations."""
    
    def __init__(
        self,
        storage_adapter: StructuredStorageAdapter,
        cache_adapter
    ):
        self.storage = storage_adapter
        self.cache = cache_adapter
    
    async def get_bom(self, query):
        """Get BOM data (placeholder)."""
        # Would implement query logic here
        return None
    
    async def get_weight_metrics(self, query):
        """Get weight metrics (placeholder)."""
        # Would implement metrics calculation here
        pass
    
    async def get_missing_data_report(self, query):
        """Get missing data report (placeholder)."""
        # Would implement report generation here
        pass
    
    async def get_cache_info(self, query):
        """Get cache info (placeholder)."""
        # Would implement cache info retrieval here
        pass
    
    async def get_diagnostics(self, query):
        """Get diagnostics (placeholder)."""
        # Would implement diagnostics collection here
        pass


@lru_cache()
def get_query_adapter(
    storage_adapter: StructuredStorageAdapter = Depends(get_storage_adapter),
    cache_adapter = Depends(get_cache_adapter)
) -> QueryAdapter:
    """Get query adapter with injected dependencies."""
    return QueryAdapter(
        storage_adapter=storage_adapter,
        cache_adapter=cache_adapter
    )


@lru_cache()
def get_query_service(
    query_adapter: QueryAdapter = Depends(get_query_adapter)
) -> QueryService:
    """Get query service with injected dependencies."""
    return QueryService(query_port=query_adapter)


# Health check dependencies
def get_system_status(
    onshape_client: OnshapeClientAdapter = Depends(get_onshape_client),
    cache_adapter = Depends(get_cache_adapter),
    storage_adapter: StructuredStorageAdapter = Depends(get_storage_adapter)
) -> Dict[str, str]:
    """Get system component status for health checks."""
    
    status_map = {}
    
    # Check Onshape client
    try:
        # Would do actual health check here
        status_map["onshape"] = "healthy"
    except Exception:
        status_map["onshape"] = "unhealthy"
    
    # Check cache
    try:
        # Would do actual cache check here  
        status_map["cache"] = "healthy"
    except Exception:
        status_map["cache"] = "unhealthy"
    
    # Check storage
    try:
        # Would do actual storage check here
        status_map["storage"] = "healthy"
    except Exception:
        status_map["storage"] = "unhealthy"
    
    return status_map


# Cleanup function for graceful shutdown
async def cleanup_dependencies():
    """Clean up resources during shutdown."""
    
    # Close HTTP clients
    try:
        onshape_client = get_onshape_client()
        await onshape_client.__aexit__(None, None, None)
    except Exception as e:
        logger.error(f"Error closing Onshape client: {e}")
    
    # Close cache connections
    try:
        cache_adapter = get_cache_adapter()
        if hasattr(cache_adapter, '__aexit__'):
            await cache_adapter.__aexit__(None, None, None)
    except Exception as e:
        logger.error(f"Error closing cache adapter: {e}")
    
    # Close notification adapters
    try:
        notification_adapter = get_notification_adapter()
        if hasattr(notification_adapter, '__aexit__'):
            await notification_adapter.__aexit__(None, None, None)
    except Exception as e:
        logger.error(f"Error closing notification adapter: {e}")
    
    logger.info("Dependencies cleanup completed")