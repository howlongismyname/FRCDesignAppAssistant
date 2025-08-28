"""Application layer for the Design Assistant.

This layer contains the application services, commands, queries, and DTOs.
It orchestrates the use cases but delegates domain logic to the domain layer
and infrastructure concerns to the adapters.
"""

from .dto import (
    # Request DTOs
    OnshapeReferenceDto,
    BomRequestDto, 
    ThumbnailRequestDto,
    BulkMetadataRequestDto,
    FabPackRequestDto,
    
    # Response DTOs
    BomResponseDto,
    BomAnalysisDto,
    PartDto,
    AssemblyDto,
    ThumbnailResponseDto,
    BulkMetadataResponseDto,
    FabPackResponseDto,
    DiagnosticsDto,
    ErrorResponseDto,
    
    # Enums
    ExportFormat
)

from .commands import (
    # Commands
    RefreshBomCacheCommand,
    GenerateThumbnailsCommand,
    BulkUpdateMetadataCommand,
    BuildFabPackCommand,
    ClassifyPartsCommand,
    ValidateBomCommand,
    ExportBomCommand,
    UpdatePartStatusCommand,
    GenerateReportsCommand,
    
    # Results
    CommandResult,
    BomCacheResult,
    ThumbnailResult,
    MetadataUpdateResult,
    FabPackResult
)

from .query import (
    # Queries
    GetBomQuery,
    GetWeightMetricsQuery,
    GetMissingDataReportQuery,
    GetPartClassificationQuery,
    GetCacheInfoQuery,
    GetDiagnosticsQuery,
    
    # Query Results
    WeightMetricsResult,
    MissingDataReport,
    CacheInfo,
    
    # Query Service
    QueryService,
    
    # Builders
    BomResponseBuilder,
    WeightMetricsBuilder,
    MissingDataReportBuilder
)

from .services import (
    # Services
    BomService,
    ThumbnailService,
    MetadataService,
    FabPackService,
    
    # Ports (interfaces)
    OnshapeApiPort,
    StoragePort,
    CachePort,
    NotificationPort,
    QueryPort
)

__all__ = [
    # DTOs
    "OnshapeReferenceDto",
    "BomRequestDto",
    "ThumbnailRequestDto", 
    "BulkMetadataRequestDto",
    "FabPackRequestDto",
    "BomResponseDto",
    "BomAnalysisDto",
    "PartDto",
    "AssemblyDto",
    "ThumbnailResponseDto",
    "BulkMetadataResponseDto",
    "FabPackResponseDto",
    "DiagnosticsDto",
    "ErrorResponseDto",
    "ExportFormat",
    
    # Commands and Results
    "RefreshBomCacheCommand",
    "GenerateThumbnailsCommand", 
    "BulkUpdateMetadataCommand",
    "BuildFabPackCommand",
    "ClassifyPartsCommand",
    "ValidateBomCommand",
    "ExportBomCommand",
    "UpdatePartStatusCommand",
    "GenerateReportsCommand",
    "CommandResult",
    "BomCacheResult",
    "ThumbnailResult", 
    "MetadataUpdateResult",
    "FabPackResult",
    
    # Queries
    "GetBomQuery",
    "GetWeightMetricsQuery",
    "GetMissingDataReportQuery",
    "GetPartClassificationQuery", 
    "GetCacheInfoQuery",
    "GetDiagnosticsQuery",
    "WeightMetricsResult",
    "MissingDataReport",
    "CacheInfo",
    "QueryService",
    "BomResponseBuilder",
    "WeightMetricsBuilder",
    "MissingDataReportBuilder",
    
    # Services and Ports
    "BomService",
    "ThumbnailService",
    "MetadataService", 
    "FabPackService",
    "OnshapeApiPort",
    "StoragePort",
    "CachePort",
    "NotificationPort",
    "QueryPort"
]