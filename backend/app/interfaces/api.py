"""API endpoints for the Design Assistant."""

import uuid
from typing import Optional, List
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

from ..application import (
    RefreshBomCacheCommand, GenerateThumbnailsCommand, 
    BulkUpdateMetadataCommand, BuildFabPackCommand,
    BomService, ThumbnailService, MetadataService, FabPackService,
    QueryService, GetBomQuery, GetWeightMetricsQuery, 
    GetMissingDataReportQuery, GetDiagnosticsQuery,
    BomRequestDto, ThumbnailRequestDto, BulkMetadataRequestDto, 
    FabPackRequestDto, BomResponseDto, DiagnosticsDto
)
from ..infrastructure.logging import RequestContext, get_logger
from .schemas import (
    BomRequest, BomResponse, ThumbnailRequest, ThumbnailResponse,
    BulkMetadataRequest, BulkMetadataResponse, FabPackRequest, FabPackResponse,
    WeightMetricsResponse, MissingDataReportResponse, ErrorResponse
)
from .dependencies import (
    get_bom_service, get_thumbnail_service, get_metadata_service, 
    get_fab_pack_service, get_query_service, get_auth_data
)


logger = get_logger("api")


def create_design_assistant_router() -> APIRouter:
    """Create the main Design Assistant API router."""
    
    router = APIRouter(
        prefix="/api/v1/design-assistant",
        tags=["design-assistant"]
    )
    
    # BOM endpoints
    router.include_router(create_bom_router())
    
    # Thumbnail endpoints  
    router.include_router(create_thumbnail_router())
    
    # Metadata endpoints
    router.include_router(create_metadata_router())
    
    # Fabrication package endpoints
    router.include_router(create_fab_pack_router())
    
    # Report endpoints
    router.include_router(create_reports_router())
    
    # System endpoints
    router.include_router(create_system_router())
    
    return router


def create_bom_router() -> APIRouter:
    """Create BOM-related endpoints."""
    
    router = APIRouter(prefix="/bom", tags=["bom"])
    
    @router.post("/refresh", response_model=BomResponse)
    async def refresh_bom_cache(
        request: BomRequest,
        background_tasks: BackgroundTasks,
        bom_service: BomService = Depends(get_bom_service),
        auth_data = Depends(get_auth_data)
    ) -> BomResponse:
        """Refresh BOM cache from Onshape API."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            logger.info("BOM refresh requested", 
                       document_id=request.onshape_ref.document_id,
                       force_refresh=request.force_refresh)
            
            try:
                # Convert to application command
                command = RefreshBomCacheCommand.from_dto(
                    BomRequestDto(**request.dict())
                )
                
                # Execute command
                result = await bom_service.refresh_bom_cache(command)
                
                if not result.success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result.message
                    )
                
                logger.info("BOM refresh completed successfully",
                           parts_processed=result.parts_processed,
                           execution_time_ms=result.execution_time_ms)
                
                # Return response (would typically fetch the BOM data here)
                return BomResponse(
                    success=True,
                    message=result.message,
                    cache_key=result.cache_key,
                    parts_processed=result.parts_processed,
                    total_weight_lb=result.total_weight_lb
                )
                
            except Exception as e:
                logger.error("BOM refresh failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"BOM refresh failed: {str(e)}"
                )
    
    @router.get("/{document_id}/{element_id}", response_model=BomResponseDto)
    async def get_bom(
        document_id: str,
        element_id: str,
        wvm_type: str = "w",
        wvm_id: str = "master", 
        configuration_id: Optional[str] = None,
        max_age_hours: Optional[int] = None,
        query_service: QueryService = Depends(get_query_service),
        auth_data = Depends(get_auth_data)
    ) -> BomResponseDto:
        """Get BOM data from cache."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            logger.info("BOM data requested", 
                       document_id=document_id, 
                       element_id=element_id)
            
            try:
                from ..application.dto import OnshapeReferenceDto
                
                onshape_ref = OnshapeReferenceDto(
                    document_id=document_id,
                    element_id=element_id,
                    wvm_type=wvm_type,
                    wvm_id=wvm_id
                )
                
                query = GetBomQuery(
                    onshape_ref=onshape_ref,
                    configuration_id=configuration_id,
                    max_age_hours=max_age_hours
                )
                
                bom_data = await query_service.get_bom(query)
                
                if not bom_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="BOM data not found or too old. Try refreshing the cache."
                    )
                
                return bom_data
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Get BOM failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get BOM: {str(e)}"
                )
    
    return router


def create_thumbnail_router() -> APIRouter:
    """Create thumbnail-related endpoints."""
    
    router = APIRouter(prefix="/thumbnails", tags=["thumbnails"])
    
    @router.post("/generate", response_model=ThumbnailResponse)
    async def generate_thumbnails(
        request: ThumbnailRequest,
        background_tasks: BackgroundTasks,
        thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
        auth_data = Depends(get_auth_data)
    ) -> ThumbnailResponse:
        """Generate thumbnails for parts in a BOM."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            logger.info("Thumbnail generation requested",
                       document_id=request.onshape_ref.document_id)
            
            try:
                command = GenerateThumbnailsCommand.from_dto(
                    ThumbnailRequestDto(**request.dict())
                )
                
                result = await thumbnail_service.generate_thumbnails(command)
                
                if not result.success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result.message
                    )
                
                logger.info("Thumbnail generation completed",
                           thumbnails_generated=result.thumbnails_generated,
                           thumbnails_failed=result.thumbnails_failed)
                
                return ThumbnailResponse(
                    success=True,
                    message=result.message,
                    thumbnails_generated=result.thumbnails_generated,
                    thumbnails_failed=result.thumbnails_failed,
                    total_size_bytes=result.total_size_bytes,
                    failed_parts=result.failed_parts
                )
                
            except Exception as e:
                logger.error("Thumbnail generation failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Thumbnail generation failed: {str(e)}"
                )
    
    return router


def create_metadata_router() -> APIRouter:
    """Create metadata-related endpoints."""
    
    router = APIRouter(prefix="/metadata", tags=["metadata"])
    
    @router.post("/bulk-update", response_model=BulkMetadataResponse)
    async def bulk_update_metadata(
        request: BulkMetadataRequest,
        background_tasks: BackgroundTasks,
        metadata_service: MetadataService = Depends(get_metadata_service),
        auth_data = Depends(get_auth_data)
    ) -> BulkMetadataResponse:
        """Perform bulk metadata updates."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            logger.info("Bulk metadata update requested",
                       update_count=len(request.updates))
            
            try:
                command = BulkUpdateMetadataCommand.from_dto(
                    BulkMetadataRequestDto(**request.dict())
                )
                
                result = await metadata_service.bulk_update_metadata(command)
                
                logger.info("Bulk metadata update completed",
                           successful_updates=result.successful_updates,
                           failed_updates=result.failed_updates)
                
                return BulkMetadataResponse(
                    success=result.success,
                    message=result.message,
                    total_updates=result.total_updates,
                    successful_updates=result.successful_updates,
                    failed_updates=result.failed_updates,
                    failed_items=result.failed_items
                )
                
            except Exception as e:
                logger.error("Bulk metadata update failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Bulk metadata update failed: {str(e)}"
                )
    
    return router


def create_fab_pack_router() -> APIRouter:
    """Create fabrication package endpoints."""
    
    router = APIRouter(prefix="/fab-pack", tags=["fabrication"])
    
    @router.post("/build", response_model=FabPackResponse)
    async def build_fab_pack(
        request: FabPackRequest,
        background_tasks: BackgroundTasks,
        fab_pack_service: FabPackService = Depends(get_fab_pack_service),
        auth_data = Depends(get_auth_data)
    ) -> FabPackResponse:
        """Build fabrication package for an assembly."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            logger.info("Fabrication package build requested",
                       document_id=request.onshape_ref.document_id,
                       formats=request.formats)
            
            try:
                command = BuildFabPackCommand.from_dto(
                    FabPackRequestDto(**request.dict())
                )
                
                result = await fab_pack_service.build_fab_pack(command)
                
                if not result.success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result.message
                    )
                
                logger.info("Fabrication package build completed",
                           package_id=result.package_id,
                           files_generated=result.files_generated)
                
                return FabPackResponse(
                    success=True,
                    message=result.message,
                    package_id=result.package_id,
                    files_generated=result.files_generated,
                    total_size_bytes=result.total_size_bytes,
                    download_url=result.download_url,
                    file_list=result.file_list
                )
                
            except Exception as e:
                logger.error("Fabrication package build failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fabrication package build failed: {str(e)}"
                )
    
    return router


def create_reports_router() -> APIRouter:
    """Create reporting endpoints."""
    
    router = APIRouter(prefix="/reports", tags=["reports"])
    
    @router.get("/weight-metrics/{document_id}/{element_id}", response_model=WeightMetricsResponse)
    async def get_weight_metrics(
        document_id: str,
        element_id: str,
        wvm_type: str = "w",
        wvm_id: str = "master",
        configuration_id: Optional[str] = None,
        group_by_material: bool = False,
        group_by_document: bool = False,
        query_service: QueryService = Depends(get_query_service),
        auth_data = Depends(get_auth_data)
    ) -> WeightMetricsResponse:
        """Get weight/mass metrics for a BOM."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            try:
                from ..application.dto import OnshapeReferenceDto
                
                onshape_ref = OnshapeReferenceDto(
                    document_id=document_id,
                    element_id=element_id,
                    wvm_type=wvm_type,
                    wvm_id=wvm_id
                )
                
                query = GetWeightMetricsQuery(
                    onshape_ref=onshape_ref,
                    configuration_id=configuration_id,
                    group_by_material=group_by_material,
                    group_by_document=group_by_document
                )
                
                metrics = await query_service.get_weight_metrics(query)
                
                return WeightMetricsResponse(
                    total_weight_lb=float(metrics.total_weight_lb),
                    weight_by_material={k: float(v) for k, v in metrics.weight_by_material.items()},
                    weight_by_document={k: float(v) for k, v in metrics.weight_by_document.items()},
                    subassembly_weights={k: float(v) for k, v in metrics.subassembly_weights.items()},
                    parts_with_mass=metrics.parts_with_mass,
                    parts_missing_mass=metrics.parts_missing_mass,
                    confidence_score=metrics.confidence_score
                )
                
            except Exception as e:
                logger.error("Get weight metrics failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get weight metrics: {str(e)}"
                )
    
    @router.get("/missing-data/{document_id}/{element_id}", response_model=MissingDataReportResponse)
    async def get_missing_data_report(
        document_id: str,
        element_id: str,
        wvm_type: str = "w",
        wvm_id: str = "master",
        configuration_id: Optional[str] = None,
        include_suggestions: bool = True,
        query_service: QueryService = Depends(get_query_service),
        auth_data = Depends(get_auth_data)
    ) -> MissingDataReportResponse:
        """Get missing data report for a BOM."""
        
        request_id = str(uuid.uuid4())
        
        with RequestContext(request_id, auth_data.get("user_id")):
            try:
                from ..application.dto import OnshapeReferenceDto
                
                onshape_ref = OnshapeReferenceDto(
                    document_id=document_id,
                    element_id=element_id,
                    wvm_type=wvm_type,
                    wvm_id=wvm_id
                )
                
                query = GetMissingDataReportQuery(
                    onshape_ref=onshape_ref,
                    configuration_id=configuration_id,
                    include_suggestions=include_suggestions
                )
                
                report = await query_service.get_missing_data_report(query)
                
                return MissingDataReportResponse(
                    missing_materials=report.missing_materials,
                    missing_masses=report.missing_masses,
                    suggested_materials=report.suggested_materials,
                    completeness_score=report.completeness_score,
                    recommendations=report.recommendations
                )
                
            except Exception as e:
                logger.error("Get missing data report failed", error=str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get missing data report: {str(e)}"
                )
    
    return router


def create_system_router() -> APIRouter:
    """Create system/diagnostics endpoints."""
    
    router = APIRouter(prefix="/system", tags=["system"])
    
    @router.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    
    @router.get("/diagnostics", response_model=DiagnosticsDto)
    async def get_diagnostics(
        query_service: QueryService = Depends(get_query_service),
        auth_data = Depends(get_auth_data)
    ) -> DiagnosticsDto:
        """Get system diagnostics."""
        
        try:
            query = GetDiagnosticsQuery()
            diagnostics = await query_service.get_diagnostics(query)
            return diagnostics
            
        except Exception as e:
            logger.error("Get diagnostics failed", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get diagnostics: {str(e)}"
            )
    
    return router


@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with proper error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=str(exc.detail),
            status_code=exc.status_code,
            timestamp=datetime.now()
        ).dict()
    )