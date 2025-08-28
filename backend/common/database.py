from google.cloud import firestore
from google.cloud.firestore import CollectionReference, DocumentReference
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from backend.domain.config import get_config


class Database:
    def __init__(self, client: firestore.Client):
        self.client = client

    @property
    def sessions(self) -> CollectionReference:
        return self.client.collection("sessions")

    @property
    def documents(self) -> CollectionReference:
        return self.client.collection("documents")

    @property
    def elements(self) -> CollectionReference:
        return self.client.collection("elements")

    @property
    def configurations(self) -> CollectionReference:
        return self.client.collection("configurations")

    @property
    def bom_sessions(self) -> CollectionReference:
        return self.client.collection("bom_sessions")


    @property
    def document_order(self) -> DocumentReference:
        # Yes, there are three layers of documentOrder...
        return self.client.collection("documentOrder").document("documentOrder")

    def get_document_order(self) -> list[str]:
        result = self.document_order.get().to_dict()
        if result == None:
            return []
        # We have to nest to satisfy Google Cloud
        return result.get("documentOrder", [])

    def set_document_order(self, order: list[str]) -> None:
        self.document_order.set({"documentOrder": order})

    def delete_document(self, document_id: str):
        """Deletes a document and all elements and configurations which depend on it."""
        document = self.documents.document(document_id).get().to_dict()
        self.documents.document(document_id).delete()

        if document == None:
            return
        # Delete all children as well
        for element_id in document.get("elementIds", []):
            self.elements.document(element_id).delete()
            self.configurations.document(element_id).delete()

    def save_bom_session(
        self,
        session_id: str,
        bom_data: Dict[str, Any],
        document_id: str,
        element_id: str,
        workspace_id: str = None,
    ) -> None:
        """Save BOM data to Firestore with timestamp and metadata."""
        bom_session_data = {
            "bomData": bom_data,
            "documentId": document_id,
            "elementId": element_id,
            "lastUpdated": datetime.now(timezone.utc),
            "sessionId": session_id,
        }
        
        # Add workspace_id if provided (for assembly data lookup from part studios)
        if workspace_id:
            bom_session_data["workspaceId"] = workspace_id

        # Use a composite key for easy lookup
        doc_id = f"{session_id}_{document_id}_{element_id}"
        self.bom_sessions.document(doc_id).set(bom_session_data)

    def get_bom_session(
        self,
        session_id: str,
        document_id: str,
        element_id: str,
        max_age_hours: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get BOM data from Firestore if it's recent enough."""
        if max_age_hours is None:
            max_age_hours = get_config().bom_cache_hours
        doc_id = f"{session_id}_{document_id}_{element_id}"
        doc = self.bom_sessions.document(doc_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        if not data:
            return None

        # Check if data is still fresh (within max_age_hours)
        last_updated = data.get("lastUpdated")
        if not last_updated:
            return None

        # Convert Firestore timestamp to datetime if needed
        if hasattr(last_updated, "timestamp"):
            last_updated = datetime.fromtimestamp(
                last_updated.timestamp(), tz=timezone.utc
            )
        elif isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        elif isinstance(last_updated, datetime):
            # Ensure it's timezone-aware
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

        age_limit = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        if last_updated < age_limit:
            # Data is too old, delete it
            self.bom_sessions.document(doc_id).delete()
            return None

        return data

    def get_bom_session_by_workspace(
        self,
        session_id: str,
        document_id: str,
        workspace_id: str,
        max_age_hours: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get BOM data from Firestore by workspace ID (for part studios)."""
        if max_age_hours is None:
            max_age_hours = get_config().bom_cache_hours
        # Query for BOM sessions in the same document/workspace
        query = (
            self.bom_sessions
            .where("sessionId", "==", session_id)
            .where("documentId", "==", document_id)
            .where("workspaceId", "==", workspace_id)
            .limit(1)
        )
        
        docs = list(query.stream())
        if not docs:
            return None
            
        doc = docs[0]
        data = doc.to_dict()
        if not data:
            return None

        # Check if data is still fresh (within max_age_hours) 
        last_updated = data.get("lastUpdated")
        if not last_updated:
            return None

        # Convert Firestore timestamp to datetime if needed
        if hasattr(last_updated, "timestamp"):
            last_updated = datetime.fromtimestamp(
                last_updated.timestamp(), tz=timezone.utc
            )
        elif isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        elif isinstance(last_updated, datetime):
            # Ensure it's timezone-aware
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

        age_limit = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        if last_updated < age_limit:
            # Data is too old, delete it
            doc.reference.delete()
            return None

        return data

    def cleanup_old_bom_sessions(self, max_age_hours: Optional[int] = None) -> None:
        """Clean up old BOM sessions to prevent database bloat."""
        if max_age_hours is None:
            max_age_hours = get_config().bom_cache_hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Query for old sessions
        old_sessions = self.bom_sessions.where("lastUpdated", "<", cutoff_time).stream()

        # Delete old sessions in batches
        batch = self.client.batch()
        count = 0
        batch_size = get_config().cleanup_batch_size

        for doc in old_sessions:
            batch.delete(doc.reference)
            count += 1

            # Commit batch every batch_size operations
            if count % batch_size == 0:
                batch.commit()
                batch = self.client.batch()

        # Commit remaining operations
        if count % batch_size != 0:
            batch.commit()



def delete_collection(coll_ref: CollectionReference, batch_size=500):
    """Deletes a collection in the database."""
    if batch_size == 0:
        return

    docs = coll_ref.list_documents(page_size=batch_size)
    deleted = 0

    for doc in docs:
        doc.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)
