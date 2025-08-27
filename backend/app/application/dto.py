"""Data Transfer Objects for the Design Assistant application layer."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum

from ..domain.bom import ElementType
from ..domain.status import ManufacturingStatus, ThumbnailStatus


class OnshapeReferenceDto(BaseModel):
    """DTO for Onshape element references."""
    
    document_id: str = Field(..., description="Onshape document ID")
    element_id: str = Field(..., description="Element ID within document")
    wvm_type: str = Field(..., description="Version management type (w/v/m)")
    wvm_id: str = Field(..., description="Version management ID")
    part_id: Optional[str] = Field(None, description="Part ID for parts")
    
    @validator('wvm_type')
    def validate_wvm_type(cls, v):
        if v not in ('w', 'v', 'm'):
            raise ValueError('wvm_type must be w, v, or m')
        return v


class BomRequestDto(BaseModel):
    """DTO for BOM analysis requests."""
    
    onshape_ref: OnshapeReferenceDto
    element_type: str = Field(..., description="Element type (ASSEMBLY/PARTSTUDIO)")
    configuration_id: Optional[str] = Field(None, description="Configuration ID if applicable")
    force_refresh: bool = Field(False, description="Force refresh from Onshape API")
    
    @validator('element_type')
    def validate_element_type(cls, v):
        if v not in ('ASSEMBLY', 'PARTSTUDIO'):
            raise ValueError('element_type must be ASSEMBLY or PARTSTUDIO')
        return v


class PartDto(BaseModel):
    """DTO for part information."""
    
    item_id: str = Field(..., description="Item ID from BOM")
    name: str = Field(..., description="Part name")
    quantity: Decimal = Field(..., description="Quantity in BOM")
    mass_lb: Optional[Decimal] = Field(None, description="Mass in pounds")
    material: Optional[str] = Field(None, description="Material name")
    missing_material: bool = Field(..., description="Whether part is missing material")
    missing_mass: bool = Field(..., description="Whether part is missing mass data")
    
    # Hierarchy information
    parent_id: Optional[str] = Field(None, description="Parent item ID")
    indent_level: int = Field(0, description="Hierarchy depth")
    is_subassembly: bool = Field(False, description="Whether item is a subassembly")
    has_children: bool = Field(False, description="Whether item has child components")
    
    # Document reference
    onshape_ref: Optional[OnshapeReferenceDto] = Field(None, description="Onshape reference")
    is_current_document: bool = Field(False, description="Whether part is from current document")
    
    # Additional metadata
    vendor: Optional[str] = Field(None, description="Vendor name")
    part_number: Optional[str] = Field(None, description="Part number")
    cots_category: Optional[str] = Field(None, description="COTS category")
    
    class Config:
        use_enum_values = True


class AssemblyDto(BaseModel):
    """DTO for assembly information."""
    
    item_id: str = Field(..., description="Item ID from BOM")
    name: str = Field(..., description="Assembly name")
    quantity: Decimal = Field(..., description="Quantity in BOM")
    calculated_mass_lb: Optional[Decimal] = Field(None, description="Calculated mass in pounds")
    
    # Hierarchy
    parent_id: Optional[str] = Field(None, description="Parent item ID")
    indent_level: int = Field(0, description="Hierarchy depth")
    children: List[str] = Field(default_factory=list, description="Child item IDs")
    
    # Status flags
    has_children_missing_mass: bool = Field(False, description="Children missing mass")
    has_children_missing_material: bool = Field(False, description="Children missing material")


class BomAnalysisDto(BaseModel):
    """DTO for BOM analysis results."""
    
    total_weight_lb: Decimal = Field(..., description="Total weight in pounds")
    parts_counted: int = Field(..., description="Number of parts analyzed")
    parts_skipped: int = Field(0, description="Number of parts skipped")
    missing_material_count: int = Field(..., description="Parts missing material")
    missing_mass_count: int = Field(..., description="Parts missing mass")
    subassembly_count: int = Field(..., description="Number of subassemblies")
    
    # Document breakdown
    current_document_parts: int = Field(0, description="Parts from current document")
    imported_parts: int = Field(0, description="Parts from other documents")
    
    # Processing metadata
    processed_at: datetime = Field(..., description="When analysis was performed")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class BomResponseDto(BaseModel):
    """DTO for BOM analysis response."""
    
    onshape_ref: OnshapeReferenceDto
    analysis: BomAnalysisDto
    parts: List[PartDto] = Field(default_factory=list)
    assemblies: List[AssemblyDto] = Field(default_factory=list)
    
    # Cache information
    is_cached: bool = Field(False, description="Whether data came from cache")
    last_updated: datetime = Field(..., description="When data was last updated")
    cache_age_hours: Optional[float] = Field(None, description="Age of cached data in hours")


class ThumbnailRequestDto(BaseModel):
    """DTO for thumbnail generation requests."""
    
    onshape_ref: OnshapeReferenceDto
    size: str = Field("300x300", description="Thumbnail size (WxH)")
    view_angle: str = Field("iso", description="View angle (iso, front, top, etc.)")
    force_regenerate: bool = Field(False, description="Force regeneration if exists")


class ThumbnailResponseDto(BaseModel):
    """DTO for thumbnail response."""
    
    onshape_ref: OnshapeReferenceDto
    thumbnail_url: str = Field(..., description="URL to generated thumbnail")
    size: str = Field(..., description="Actual thumbnail size")
    generated_at: datetime = Field(..., description="When thumbnail was generated")
    file_size_bytes: int = Field(..., description="Thumbnail file size")


class MetadataUpdateDto(BaseModel):
    """DTO for metadata updates."""
    
    onshape_ref: OnshapeReferenceDto
    properties: Dict[str, Any] = Field(..., description="Properties to update")


class BulkMetadataRequestDto(BaseModel):
    """DTO for bulk metadata update requests."""
    
    updates: List[MetadataUpdateDto] = Field(..., description="List of metadata updates")
    batch_size: int = Field(10, description="Batch size for processing")


class BulkMetadataResponseDto(BaseModel):
    """DTO for bulk metadata update response."""
    
    total_updates: int = Field(..., description="Total number of updates requested")
    successful_updates: int = Field(..., description="Number of successful updates")
    failed_updates: int = Field(..., description="Number of failed updates")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    processing_time_ms: int = Field(..., description="Total processing time")


class ExportFormat(str, Enum):
    """Export format options."""
    STEP = "step"
    IGES = "iges"
    STL = "stl"
    PARASOLID = "parasolid"
    PDF = "pdf"


class FabPackRequestDto(BaseModel):
    """DTO for fabrication package requests."""
    
    onshape_ref: OnshapeReferenceDto
    formats: List[ExportFormat] = Field(..., description="Export formats to include")
    include_drawings: bool = Field(True, description="Include technical drawings")
    store_in_document: bool = Field(True, description="Store files in Onshape document")


class FabPackResponseDto(BaseModel):
    """DTO for fabrication package response."""
    
    onshape_ref: OnshapeReferenceDto
    package_id: str = Field(..., description="Package identifier")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="Generated files")
    total_size_bytes: int = Field(..., description="Total package size")
    generated_at: datetime = Field(..., description="When package was generated")


class DiagnosticsDto(BaseModel):
    """DTO for diagnostics information."""
    
    system_status: str = Field(..., description="Overall system status")
    active_sessions: int = Field(..., description="Number of active BOM sessions")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    average_processing_time_ms: float = Field(..., description="Average processing time")
    error_count_last_hour: int = Field(..., description="Errors in last hour")
    
    # Resource usage
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    disk_usage_mb: float = Field(..., description="Disk usage in MB")
    
    # Onshape API stats
    api_calls_last_hour: int = Field(..., description="API calls in last hour")
    api_success_rate: float = Field(..., description="API success rate percentage")


class ErrorResponseDto(BaseModel):
    """DTO for error responses."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for debugging")
    timestamp: datetime = Field(default_factory=datetime.now, description="When error occurred")