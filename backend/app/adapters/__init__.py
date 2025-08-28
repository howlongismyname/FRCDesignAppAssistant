"""Adapters layer for the Design Assistant.

This layer contains concrete implementations of the ports defined in the application layer.
Adapters handle communication with external systems like Onshape API, storage systems, 
caching, and notifications.
"""

from .onshape_client import OnshapeClientAdapter
from .storage_adapter import StructuredStorageAdapter, BlobStorageAdapter
from .cache_adapter import RedisCacheAdapter, MemoryCacheAdapter
from .notification_adapter import WebhookNotificationAdapter

__all__ = [
    "OnshapeClientAdapter",
    "StructuredStorageAdapter", 
    "BlobStorageAdapter",
    "RedisCacheAdapter",
    "MemoryCacheAdapter",
    "WebhookNotificationAdapter"
]