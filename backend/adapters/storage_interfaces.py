"""Storage adapter interfaces for the BOM processing system.

Based on research of Onshape Structured Storage APIs:
- Onshape provides application elements with JSON tree storage
- Supports incremental updates (deltas) and atomic transactions
- Data transmitted as Base-64 encoded JSON
- Two storage mechanisms: Sub Elements and JSON Tree Storage
- JSON Tree Storage recommended for Onshape-native storage with merge/diff support
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from backend.domain.models import BomAnalysis, BomPart


@dataclass
class StorageMetadata:
    """Metadata for storage operations."""
    created_at: datetime
    updated_at: datetime
    version: str
    change_id: Optional[str] = None  # Onshape changeId for state tracking
    

class SessionStorageAdapter(ABC):
    """Interface for session-related storage operations (Firestore)."""
    
    @abstractmethod
    def save_refresh_cooldown(self, session_id: str, document_id: str, 
                             element_id: str, timestamp: float) -> None:
        """Save the last refresh timestamp for rate limiting."""
        pass
    
    @abstractmethod
    def get_refresh_cooldown(self, session_id: str, document_id: str, 
                           element_id: str) -> Optional[float]:
        """Get the last refresh timestamp for rate limiting."""
        pass
    
    @abstractmethod
    def cleanup_old_sessions(self, max_age_hours: int) -> int:
        """Clean up old session data and return count of cleaned items."""
        pass


class BomStorageAdapter(ABC):
    """Interface for BOM data storage operations (Onshape Structured Storage)."""
    
    @abstractmethod
    def save_bom_analysis(self, document_id: str, element_id: str, 
                         workspace_id: str, analysis: BomAnalysis,
                         metadata: Optional[StorageMetadata] = None) -> str:
        """Save BOM analysis results to structured storage.
        
        Returns: change_id for tracking the stored state
        """
        pass
    
    @abstractmethod
    def get_bom_analysis(self, document_id: str, element_id: str,
                        workspace_id: str) -> Optional[BomAnalysis]:
        """Retrieve BOM analysis from structured storage."""
        pass
    
    @abstractmethod
    def save_part_metadata(self, document_id: str, element_id: str,
                          workspace_id: str, part_id: str, 
                          metadata: Dict[str, Any]) -> str:
        """Save individual part metadata."""
        pass
    
    @abstractmethod
    def get_part_metadata(self, document_id: str, element_id: str,
                         workspace_id: str, part_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve individual part metadata."""
        pass
    
    @abstractmethod
    def list_stored_analyses(self, document_id: str) -> List[Dict[str, str]]:
        """List all BOM analyses stored in a document.
        
        Returns: List of dicts with keys: element_id, workspace_id, updated_at
        """
        pass
    
    @abstractmethod
    def delete_bom_analysis(self, document_id: str, element_id: str,
                           workspace_id: str) -> bool:
        """Delete BOM analysis from structured storage."""
        pass


class CacheStorageAdapter(ABC):
    """Interface for temporary caching operations (could be Firestore or memory)."""
    
    @abstractmethod
    def set_cache(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        """Store data in cache with TTL."""
        pass
    
    @abstractmethod
    def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache."""
        pass
    
    @abstractmethod
    def delete_cache(self, key: str) -> bool:
        """Delete data from cache."""
        pass
    
    @abstractmethod
    def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern. Returns count cleared."""
        pass


@dataclass
class StorageConfig:
    """Configuration for storage adapters."""
    
    # Session storage config (Firestore)
    session_collection_name: str = "sessions"
    session_cleanup_batch_size: int = 500
    
    # BOM storage config (Onshape)
    onshape_application_id: Optional[str] = None
    onshape_element_name: str = "BOM_Analysis"
    use_json_tree_storage: bool = True  # vs sub-elements
    
    # Cache config
    default_cache_ttl_seconds: int = 3600  # 1 hour
    cache_key_prefix: str = "bom_cache"
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create storage config from environment variables."""
        import os
        return cls(
            session_collection_name=os.getenv('SESSION_COLLECTION_NAME', 'sessions'),
            session_cleanup_batch_size=int(os.getenv('SESSION_CLEANUP_BATCH_SIZE', 500)),
            onshape_application_id=os.getenv('ONSHAPE_APPLICATION_ID'),
            onshape_element_name=os.getenv('ONSHAPE_ELEMENT_NAME', 'BOM_Analysis'),
            use_json_tree_storage=os.getenv('USE_JSON_TREE_STORAGE', 'true').lower() == 'true',
            default_cache_ttl_seconds=int(os.getenv('CACHE_TTL_SECONDS', 3600)),
            cache_key_prefix=os.getenv('CACHE_KEY_PREFIX', 'bom_cache')
        )