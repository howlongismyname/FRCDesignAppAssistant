"""Manufacturing status state machine."""

from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from .errors import DesignAssistantError


class ManufacturingStatus(Enum):
    """Manufacturing status states."""
    QUEUED = auto()      # Queued for processing
    CAM = auto()         # In CAM programming
    IN_FAB = auto()      # Being fabricated
    FABBED = auto()      # Fabrication complete
    RECEIVED = auto()    # Received by team
    
    def can_transition_to(self, target: "ManufacturingStatus") -> bool:
        """Check if transition to target status is valid."""
        transitions = {
            ManufacturingStatus.QUEUED: [ManufacturingStatus.CAM],
            ManufacturingStatus.CAM: [ManufacturingStatus.IN_FAB, ManufacturingStatus.QUEUED],
            ManufacturingStatus.IN_FAB: [ManufacturingStatus.FABBED, ManufacturingStatus.CAM],
            ManufacturingStatus.FABBED: [ManufacturingStatus.RECEIVED],
            ManufacturingStatus.RECEIVED: [],  # Terminal state
        }
        return target in transitions.get(self, [])


class ThumbnailStatus(Enum):
    """Thumbnail generation status."""
    PENDING = auto()      # Not generated yet
    GENERATING = auto()   # Currently generating
    READY = auto()        # Generated and available
    FAILED = auto()       # Generation failed


@dataclass
class PartStatus:
    """Status information for a part."""
    
    manufacturing: ManufacturingStatus = ManufacturingStatus.QUEUED
    thumbnail: ThumbnailStatus = ThumbnailStatus.PENDING
    last_updated: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def update_manufacturing_status(self, new_status: ManufacturingStatus) -> None:
        """Update manufacturing status with validation."""
        if not self.manufacturing.can_transition_to(new_status):
            raise DesignAssistantError(
                f"Cannot transition from {self.manufacturing.name} to {new_status.name}",
                details={
                    "current_status": self.manufacturing.name,
                    "requested_status": new_status.name
                }
            )
        
        self.manufacturing = new_status
        self.last_updated = datetime.now()
    
    def update_thumbnail_status(self, new_status: ThumbnailStatus) -> None:
        """Update thumbnail status."""
        self.thumbnail = new_status
        self.last_updated = datetime.now()
    
    def is_manufacturing_complete(self) -> bool:
        """Check if manufacturing is complete."""
        return self.manufacturing == ManufacturingStatus.RECEIVED
    
    def has_thumbnail(self) -> bool:
        """Check if thumbnail is available."""
        return self.thumbnail == ThumbnailStatus.READY


@dataclass  
class ProcessingState:
    """State of BOM processing operations."""
    
    bom_cached: bool = False
    thumbnails_generated: bool = False
    metadata_updated: bool = False
    fab_pack_built: bool = False
    last_processed: Optional[datetime] = None
    error_count: int = 0
    
    def mark_bom_cached(self) -> None:
        """Mark BOM as cached."""
        self.bom_cached = True
        self.last_processed = datetime.now()
    
    def mark_thumbnails_generated(self) -> None:
        """Mark thumbnails as generated."""
        self.thumbnails_generated = True
        self.last_processed = datetime.now()
    
    def mark_metadata_updated(self) -> None:
        """Mark metadata as updated.""" 
        self.metadata_updated = True
        self.last_processed = datetime.now()
    
    def mark_fab_pack_built(self) -> None:
        """Mark fab pack as built."""
        self.fab_pack_built = True
        self.last_processed = datetime.now()
    
    def increment_error(self) -> None:
        """Increment error count."""
        self.error_count += 1
        self.last_processed = datetime.now()
    
    def is_fully_processed(self) -> bool:
        """Check if all processing steps are complete."""
        return all([
            self.bom_cached,
            self.thumbnails_generated,
            self.metadata_updated,
            self.fab_pack_built
        ])
    
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        completed_steps = sum([
            self.bom_cached,
            self.thumbnails_generated, 
            self.metadata_updated,
            self.fab_pack_built
        ])
        return (completed_steps / 4) * 100