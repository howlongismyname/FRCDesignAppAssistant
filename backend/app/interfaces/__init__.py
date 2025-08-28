"""Interfaces layer for the Design Assistant.

This layer contains the API endpoints, request/response schemas, and 
web framework integration. It acts as the entry point for external clients.
"""

from .api import create_design_assistant_router
from .schemas import (
    BomRequest,
    BomResponse,
    ThumbnailRequest,
    BulkMetadataRequest,
    FabPackRequest,
    ErrorResponse
)
from .middleware import AuthMiddleware, RequestLoggingMiddleware
from .dependencies import get_config, get_bom_service, get_thumbnail_service

__all__ = [
    "create_design_assistant_router",
    "BomRequest",
    "BomResponse", 
    "ThumbnailRequest",
    "BulkMetadataRequest",
    "FabPackRequest",
    "ErrorResponse",
    "AuthMiddleware",
    "RequestLoggingMiddleware",
    "get_config",
    "get_bom_service",
    "get_thumbnail_service"
]