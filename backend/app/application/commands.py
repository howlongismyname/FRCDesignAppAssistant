"""Command objects for Design Assistant use cases."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from .dto import (
    OnshapeReferenceDto, 
    BomRequestDto,
    ThumbnailRequestDto,
    BulkMetadataRequestDto,
    FabPackRequestDto,
    ExportFormat
)


@dataclass
class RefreshBomCacheCommand:
    """Command to refresh BOM cache from Onshape."""
    
    onshape_ref: OnshapeReferenceDto
    element_type: str  # ASSEMBLY or PARTSTUDIO
    configuration_id: Optional[str] = None
    force_refresh: bool = False
    include_mass_properties: bool = True
    include_thumbnails: bool = False
    
    @classmethod
    def from_dto(cls, dto: BomRequestDto) -> "RefreshBomCacheCommand":
        """Create command from BOM request DTO."""
        return cls(
            onshape_ref=dto.onshape_ref,
            element_type=dto.element_type,
            configuration_id=dto.configuration_id,
            force_refresh=dto.force_refresh
        )


@dataclass
class GenerateThumbnailsCommand:
    """Command to generate thumbnails for parts in a BOM."""
    
    onshape_ref: OnshapeReferenceDto
    part_ids: Optional[List[str]] = None  # If None, generate for all parts
    size: str = "300x300"
    view_angle: str = "iso"
    force_regenerate: bool = False
    batch_size: int = 5  # Process in batches to avoid rate limits
    
    @classmethod
    def from_dto(cls, dto: ThumbnailRequestDto) -> "GenerateThumbnailsCommand":
        """Create command from thumbnail request DTO."""
        return cls(
            onshape_ref=dto.onshape_ref,
            size=dto.size,
            view_angle=dto.view_angle,
            force_regenerate=dto.force_regenerate
        )


@dataclass
class BulkUpdateMetadataCommand:
    """Command to bulk update metadata for multiple parts."""
    
    updates: List[Dict[str, Any]]  # List of {onshape_ref, properties} dicts
    batch_size: int = 10
    validate_properties: bool = True
    skip_on_error: bool = False  # Continue processing other items if one fails
    
    @classmethod
    def from_dto(cls, dto: BulkMetadataRequestDto) -> "BulkUpdateMetadataCommand":
        """Create command from bulk metadata request DTO."""
        return cls(
            updates=[
                {
                    "onshape_ref": update.onshape_ref,
                    "properties": update.properties
                }
                for update in dto.updates
            ],
            batch_size=dto.batch_size
        )


@dataclass
class BuildFabPackCommand:
    """Command to build fabrication package for an assembly."""
    
    onshape_ref: OnshapeReferenceDto
    formats: List[ExportFormat]
    include_drawings: bool = True
    include_bom_csv: bool = True
    include_cut_lists: bool = True
    store_in_document: bool = True
    package_name: Optional[str] = None
    
    @classmethod
    def from_dto(cls, dto: FabPackRequestDto) -> "BuildFabPackCommand":
        """Create command from fab pack request DTO."""
        return cls(
            onshape_ref=dto.onshape_ref,
            formats=dto.formats,
            include_drawings=dto.include_drawings,
            store_in_document=dto.store_in_document
        )


@dataclass
class ClassifyPartsCommand:
    """Command to classify parts in a BOM using ML/rules."""
    
    onshape_ref: OnshapeReferenceDto
    reclassify_existing: bool = False
    confidence_threshold: float = 0.7
    update_metadata: bool = True


@dataclass
class ValidateBomCommand:
    """Command to validate BOM data integrity."""
    
    onshape_ref: OnshapeReferenceDto
    check_missing_materials: bool = True
    check_missing_masses: bool = True
    check_duplicate_names: bool = True
    check_hierarchy_integrity: bool = True


@dataclass
class ExportBomCommand:
    """Command to export BOM in various formats."""
    
    onshape_ref: OnshapeReferenceDto
    format: str  # csv, xlsx, json, xml
    include_hierarchy: bool = True
    include_mass_rollup: bool = True
    include_classifications: bool = True
    flatten_structure: bool = False


@dataclass
class UpdatePartStatusCommand:
    """Command to update manufacturing status for parts."""
    
    part_references: List[OnshapeReferenceDto]
    new_status: str  # Manufacturing status
    notes: Optional[str] = None
    bulk_update: bool = False


@dataclass
class GenerateReportsCommand:
    """Command to generate various BOM reports."""
    
    onshape_ref: OnshapeReferenceDto
    report_types: List[str]  # weight_summary, missing_materials, cut_list, etc.
    output_format: str = "json"  # json, pdf, xlsx
    include_charts: bool = True


# Command result types for better type safety
@dataclass
class CommandResult:
    """Base result for all commands."""
    
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BomCacheResult(CommandResult):
    """Result for BOM cache refresh operations."""
    
    parts_processed: int = 0
    assemblies_processed: int = 0
    total_weight_lb: Optional[float] = None
    cache_key: Optional[str] = None


@dataclass
class ThumbnailResult(CommandResult):
    """Result for thumbnail generation operations."""
    
    thumbnails_generated: int = 0
    thumbnails_failed: int = 0
    total_size_bytes: int = 0
    failed_parts: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.failed_parts is None:
            self.failed_parts = []


@dataclass
class MetadataUpdateResult(CommandResult):
    """Result for bulk metadata update operations."""
    
    total_updates: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    failed_items: List[Dict[str, str]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.failed_items is None:
            self.failed_items = []


@dataclass
class FabPackResult(CommandResult):
    """Result for fabrication package build operations."""
    
    package_id: str = ""
    files_generated: int = 0
    total_size_bytes: int = 0
    download_url: Optional[str] = None
    file_list: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.file_list is None:
            self.file_list = []