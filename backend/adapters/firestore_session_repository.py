"""Firestore implementation of session storage adapter."""

import logging
import time
from typing import Optional
from datetime import datetime, timedelta, timezone

from google.cloud import firestore
from google.cloud.firestore import Client

from .storage_interfaces import SessionStorageAdapter, StorageConfig
from backend.domain.config import get_config


logger = logging.getLogger(__name__)


class FirestoreSessionRepository(SessionStorageAdapter):
    """Firestore implementation for session-related storage operations."""
    
    def __init__(self, client: Client, config: Optional[StorageConfig] = None):
        self.client = client
        self.config = config or StorageConfig.from_env()
        
        # Collections
        self.sessions = client.collection("sessions")
        self.refresh_cooldowns = client.collection("refresh_cooldowns")
    
    def save_refresh_cooldown(self, session_id: str, document_id: str, 
                             element_id: str, timestamp: float) -> None:
        """Save the last refresh timestamp for rate limiting."""
        try:
            cooldown_key = f"{session_id}_{document_id}_{element_id}"
            doc_ref = self.refresh_cooldowns.document(cooldown_key)
            
            doc_ref.set({
                "session_id": session_id,
                "document_id": document_id,
                "element_id": element_id,
                "last_refresh_timestamp": timestamp,
                "updated_at": datetime.now(timezone.utc)
            })
            
            logger.debug(f"Saved refresh cooldown for {cooldown_key}")
            
        except Exception as e:
            logger.error(f"Failed to save refresh cooldown: {str(e)}")
            raise
    
    def get_refresh_cooldown(self, session_id: str, document_id: str, 
                           element_id: str) -> Optional[float]:
        """Get the last refresh timestamp for rate limiting."""
        try:
            cooldown_key = f"{session_id}_{document_id}_{element_id}"
            doc_ref = self.refresh_cooldowns.document(cooldown_key)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            data = doc.to_dict()
            if not data:
                return None
                
            return data.get("last_refresh_timestamp")
            
        except Exception as e:
            logger.error(f"Failed to get refresh cooldown: {str(e)}")
            return None
    
    def cleanup_old_sessions(self, max_age_hours: int) -> int:
        """Clean up old session data and return count of cleaned items."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Clean up old refresh cooldowns
            old_cooldowns = self.refresh_cooldowns.where(
                "updated_at", "<", cutoff_time
            ).stream()
            
            # Delete in batches
            batch = self.client.batch()
            count = 0
            batch_size = get_config().cleanup_batch_size
            
            for doc in old_cooldowns:
                batch.delete(doc.reference)
                count += 1
                
                if count % batch_size == 0:
                    batch.commit()
                    batch = self.client.batch()
            
            # Commit remaining operations
            if count % batch_size != 0:
                batch.commit()
            
            logger.info(f"Cleaned up {count} old session records")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {str(e)}")
            return 0
    
    # Additional session-related methods for future use
    
    def save_user_session_data(self, session_id: str, data: dict) -> None:
        """Save arbitrary user session data."""
        try:
            doc_ref = self.sessions.document(session_id)
            doc_ref.set({
                **data,
                "updated_at": datetime.now(timezone.utc)
            }, merge=True)
            
        except Exception as e:
            logger.error(f"Failed to save session data: {str(e)}")
            raise
    
    def get_user_session_data(self, session_id: str) -> Optional[dict]:
        """Get user session data."""
        try:
            doc_ref = self.sessions.document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            return doc.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get session data: {str(e)}")
            return None
    
    def is_refresh_allowed(self, session_id: str, document_id: str, 
                          element_id: str) -> tuple[bool, int]:
        """Check if refresh is allowed and return remaining cooldown seconds.
        
        Returns: (is_allowed, remaining_seconds)
        """
        try:
            last_refresh = self.get_refresh_cooldown(session_id, document_id, element_id)
            if last_refresh is None:
                return True, 0
                
            current_time = time.time()
            cooldown_seconds = get_config().refresh_cooldown_seconds
            time_since_refresh = current_time - last_refresh
            
            if time_since_refresh >= cooldown_seconds:
                return True, 0
            else:
                remaining = int(cooldown_seconds - time_since_refresh)
                return False, remaining
                
        except Exception as e:
            logger.error(f"Failed to check refresh status: {str(e)}")
            # On error, allow refresh to avoid blocking users
            return True, 0