"""Domain-specific exceptions for the Design Assistant."""

from typing import Optional, Dict, Any


class DesignAssistantError(Exception):
    """Base exception for Design Assistant domain errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidElementTypeError(DesignAssistantError):
    """Raised when an unsupported element type is encountered."""
    pass


class BomDataError(DesignAssistantError):
    """Raised when BOM data is invalid or cannot be processed."""
    pass


class MassConversionError(DesignAssistantError):
    """Raised when mass unit conversion fails."""
    pass


class HierarchyError(DesignAssistantError):
    """Raised when BOM hierarchy cannot be built correctly."""
    pass


class OnshapeApiError(DesignAssistantError):
    """Raised when Onshape API operations fail."""
    pass


class StorageError(DesignAssistantError):
    """Raised when storage operations fail."""
    pass


class AuthenticationError(DesignAssistantError):
    """Raised when authentication fails."""
    pass


class RateLimitError(DesignAssistantError):
    """Raised when rate limits are exceeded."""
    pass


class ThumbnailGenerationError(DesignAssistantError):
    """Raised when thumbnail generation fails."""
    pass


class MetadataUpdateError(DesignAssistantError):
    """Raised when metadata updates fail."""
    pass


class ExportError(DesignAssistantError):
    """Raised when export operations fail."""
    pass