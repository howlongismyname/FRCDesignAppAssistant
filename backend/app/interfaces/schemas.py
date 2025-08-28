"""Pydantic schemas for API requests and responses."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, validator

from ..application.dto import OnshapeReferenceDto, ExportFormat


# Request schemas
class OnshapeReference(BaseModel):
    """Onshape element reference."""
    
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


class BomRequest(BaseModel):
    """Request to refresh BOM cache."""
    
    onshape_ref: OnshapeReference
    element_type: str = Field(..., description="Element type (ASSEMBLY/PARTSTUDIO)")
    configuration_id: Optional[str] = Field(None, description="Configuration ID if applicable")
    force_refresh: bool = Field(False, description="Force refresh from Onshape API")
    
    @validator('element_type')
    def validate_element_type(cls, v):
        if v not in ('ASSEMBLY', 'PARTSTUDIO'):
            raise ValueError('element_type must be ASSEMBLY or PARTSTUDIO')
        return v


class ThumbnailRequest(BaseModel):
    """Request to generate thumbnails."""
    
    onshape_ref: OnshapeReference
    part_ids: Optional[List[str]] = Field(None, description="Specific part IDs to generate thumbnails for")
    size: str = Field("300x300", description="Thumbnail size (WxH)")
    view_angle: str = Field("iso", description="View angle (iso, front, top, etc.)")
    force_regenerate: bool = Field(False, description="Force regeneration if exists")
    batch_size: int = Field(5, description="Batch size for processing")


class MetadataUpdate(BaseModel):
    """Single metadata update."""
    
    onshape_ref: OnshapeReference
    properties: Dict[str, Any] = Field(..., description="Properties to update")


class BulkMetadataRequest(BaseModel):
    """Request for bulk metadata updates."""
    
    updates: List[MetadataUpdate] = Field(..., description="List of metadata updates")
    batch_size: int = Field(10, description="Batch size for processing")
    validate_properties: bool = Field(True, description="Validate properties before update")
    skip_on_error: bool = Field(False, description="Continue processing if individual updates fail")


class FabPackRequest(BaseModel):
    """Request to build fabrication package."""
    
    onshape_ref: OnshapeReference
    formats: List[ExportFormat] = Field(..., description="Export formats to include")
    include_drawings: bool = Field(True, description="Include technical drawings")
    include_bom_csv: bool = Field(True, description="Include BOM CSV file")
    include_cut_lists: bool = Field(True, description="Include cut lists")
    store_in_document: bool = Field(True, description="Store files in Onshape document")
    package_name: Optional[str] = Field(None, description="Custom package name")


# Response schemas
class BomResponse(BaseModel):
    """Response from BOM refresh operation."""
    
    success: bool
    message: str
    cache_key: Optional[str] = None
    parts_processed: int = 0
    assemblies_processed: int = 0
    total_weight_lb: Optional[float] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ThumbnailResponse(BaseModel):
    """Response from thumbnail generation."""
    
    success: bool
    message: str
    thumbnails_generated: int = 0
    thumbnails_failed: int = 0
    total_size_bytes: int = 0
    failed_parts: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class FailedMetadataUpdate(BaseModel):
    """Information about a failed metadata update."""
    
    document_id: str
    element_id: str
    error: str


class BulkMetadataResponse(BaseModel):
    """Response from bulk metadata update."""
    
    success: bool
    message: str
    total_updates: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    failed_items: List[FailedMetadataUpdate] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class FabPackFile(BaseModel):
    """Information about a file in fabrication package."""
    
    filename: str
    format: str
    size_bytes: int
    content_type: str
    download_url: Optional[str] = None


class FabPackResponse(BaseModel):
    """Response from fabrication package build."""
    
    success: bool
    message: str
    package_id: str = ""
    files_generated: int = 0
    total_size_bytes: int = 0
    download_url: Optional[str] = None
    file_list: List[FabPackFile] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class WeightMetricsResponse(BaseModel):
    """Response with weight/mass metrics."""
    
    total_weight_lb: float
    weight_by_material: Dict[str, float] = Field(default_factory=dict)
    weight_by_document: Dict[str, float] = Field(default_factory=dict)
    subassembly_weights: Dict[str, float] = Field(default_factory=dict)
    parts_with_mass: int
    parts_missing_mass: int
    confidence_score: float


class MissingDataItem(BaseModel):
    """Item with missing data."""
    
    item_id: str
    name: str
    quantity: str
    current_material: Optional[str] = None


class MissingDataReportResponse(BaseModel):
    """Response with missing data report."""
    
    missing_materials: List[MissingDataItem] = Field(default_factory=list)
    missing_masses: List[MissingDataItem] = Field(default_factory=list)
    suggested_materials: Dict[str, str] = Field(default_factory=dict)
    completeness_score: float
    recommendations: List[str] = Field(default_factory=list)


class PartInfo(BaseModel):
    """Basic part information."""
    
    item_id: str
    name: str
    quantity: str
    mass_lb: Optional[float] = None
    material: Optional[str] = None
    missing_material: bool
    missing_mass: bool
    parent_id: Optional[str] = None
    indent_level: int
    is_subassembly: bool
    vendor: Optional[str] = None
    part_number: Optional[str] = None


class AssemblyInfo(BaseModel):
    """Basic assembly information."""
    
    item_id: str
    name: str
    quantity: str
    calculated_mass_lb: Optional[float] = None
    parent_id: Optional[str] = None
    indent_level: int
    children_count: int


class BomAnalysisInfo(BaseModel):
    """BOM analysis summary."""
    
    total_weight_lb: float
    parts_counted: int
    parts_skipped: int
    missing_material_count: int
    missing_mass_count: int
    subassembly_count: int
    current_document_parts: int
    imported_parts: int
    processed_at: datetime
    processing_time_ms: Optional[int] = None


class BomDataResponse(BaseModel):
    """Full BOM data response."""
    
    onshape_ref: OnshapeReference
    analysis: Optional[BomAnalysisInfo] = None
    parts: List[PartInfo] = Field(default_factory=list)
    assemblies: List[AssemblyInfo] = Field(default_factory=list)
    is_cached: bool = False
    last_updated: datetime
    cache_age_hours: Optional[float] = None


class CacheInfoResponse(BaseModel):
    """Cache information response."""
    
    cache_key: str
    last_updated: datetime
    age_hours: float
    is_stale: bool
    size_bytes: int
    hit_count: int = 0


class DiagnosticsResponse(BaseModel):
    """System diagnostics response."""
    
    system_status: str
    active_sessions: int
    cache_hit_rate: float
    average_processing_time_ms: float
    error_count_last_hour: int
    memory_usage_mb: float
    disk_usage_mb: float
    api_calls_last_hour: int
    api_success_rate: float


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    status_code: int = 500
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Webhook schemas
class WebhookEvent(BaseModel):
    """Base webhook event."""
    
    event: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]


class BomUpdatedEvent(WebhookEvent):
    """BOM updated webhook event."""
    
    event: str = "bom_updated"
    
    class Data(BaseModel):
        document_id: str
        element_id: str
        wvm_type: str
        wvm_id: str
        cache_key: str
        parts_processed: int
        total_weight_lb: Optional[float] = None
    
    data: Data


class ThumbnailsReadyEvent(WebhookEvent):
    """Thumbnails ready webhook event."""
    
    event: str = "thumbnails_ready"
    
    class Data(BaseModel):
        document_id: str
        element_id: str
        wvm_type: str
        wvm_id: str
        thumbnails_generated: int
        total_size_bytes: int
    
    data: Data


class FabPackReadyEvent(WebhookEvent):
    """Fabrication package ready webhook event."""
    
    event: str = "fab_pack_ready"
    
    class Data(BaseModel):
        document_id: str
        element_id: str
        wvm_type: str
        wvm_id: str
        package_id: str
        files_generated: int
        total_size_bytes: int
        download_url: Optional[str] = None
    
    data: Data


class ProcessingErrorEvent(WebhookEvent):
    """Processing error webhook event."""
    
    event: str = "processing_error"
    
    class Data(BaseModel):
        document_id: str
        element_id: str
        wvm_type: str
        wvm_id: str
        operation: str
        error_message: str
    
    data: Data


# Validation schemas
class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""
    
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str] = Field(default_factory=dict)  # service_name -> status
    uptime_seconds: Optional[float] = None