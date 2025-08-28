"""Query objects and handlers for Design Assistant read operations."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Protocol
from datetime import datetime
from decimal import Decimal

from ..domain.bom import Bom, OnshapeReference
from .dto import (
    OnshapeReferenceDto, BomResponseDto, BomAnalysisDto,
    PartDto, AssemblyDto, DiagnosticsDto
)


@dataclass
class GetBomQuery:
    """Query to retrieve BOM data."""
    
    onshape_ref: OnshapeReferenceDto
    configuration_id: Optional[str] = None
    include_hierarchy: bool = True
    include_analysis: bool = True
    max_age_hours: Optional[int] = None  # Maximum age of cached data


@dataclass
class GetWeightMetricsQuery:
    """Query for weight/mass metrics."""
    
    onshape_ref: OnshapeReferenceDto
    configuration_id: Optional[str] = None
    group_by_material: bool = False
    group_by_document: bool = False
    include_subassemblies: bool = True


@dataclass
class GetMissingDataReportQuery:
    """Query for missing data reports."""
    
    onshape_ref: OnshapeReferenceDto
    configuration_id: Optional[str] = None
    report_type: str = "all"  # all, missing_material, missing_mass
    include_suggestions: bool = True


@dataclass
class GetPartClassificationQuery:
    """Query for part classification data."""
    
    onshape_ref: OnshapeReferenceDto
    configuration_id: Optional[str] = None
    confidence_threshold: float = 0.0
    part_types: Optional[List[str]] = None


@dataclass
class GetCacheInfoQuery:
    """Query for cache information."""
    
    onshape_ref: OnshapeReferenceDto
    configuration_id: Optional[str] = None


@dataclass
class GetDiagnosticsQuery:
    """Query for system diagnostics."""
    
    include_cache_stats: bool = True
    include_api_stats: bool = True
    include_error_stats: bool = True


# Query result types
@dataclass
class WeightMetricsResult:
    """Result for weight metrics queries."""
    
    total_weight_lb: Decimal
    weight_by_material: Dict[str, Decimal]
    weight_by_document: Dict[str, Decimal]
    subassembly_weights: Dict[str, Decimal]
    parts_with_mass: int
    parts_missing_mass: int
    confidence_score: float


@dataclass
class MissingDataReport:
    """Report on missing data in BOM."""
    
    missing_materials: List[Dict[str, Any]]
    missing_masses: List[Dict[str, Any]]
    suggested_materials: Dict[str, str]
    completeness_score: float
    recommendations: List[str]


@dataclass
class CacheInfo:
    """Information about cached data."""
    
    cache_key: str
    last_updated: datetime
    age_hours: float
    is_stale: bool
    size_bytes: int
    hit_count: int


# Port for query operations
class QueryPort(Protocol):
    """Port for read-only query operations."""
    
    async def get_bom(self, query: GetBomQuery) -> Optional[BomResponseDto]:
        """Get BOM data."""
        ...
    
    async def get_weight_metrics(self, query: GetWeightMetricsQuery) -> WeightMetricsResult:
        """Get weight/mass metrics."""
        ...
    
    async def get_missing_data_report(self, query: GetMissingDataReportQuery) -> MissingDataReport:
        """Get missing data report."""
        ...
    
    async def get_cache_info(self, query: GetCacheInfoQuery) -> Optional[CacheInfo]:
        """Get cache information."""
        ...
    
    async def get_diagnostics(self, query: GetDiagnosticsQuery) -> DiagnosticsDto:
        """Get system diagnostics."""
        ...


class QueryService:
    """Service for handling read queries."""
    
    def __init__(self, query_port: QueryPort):
        self.query_port = query_port
    
    async def get_bom(self, query: GetBomQuery) -> Optional[BomResponseDto]:
        """Get BOM data with optional freshness check."""
        
        # Check cache info first if max_age is specified
        if query.max_age_hours:
            cache_query = GetCacheInfoQuery(
                onshape_ref=query.onshape_ref,
                configuration_id=query.configuration_id
            )
            cache_info = await self.query_port.get_cache_info(cache_query)
            
            if cache_info and cache_info.age_hours > query.max_age_hours:
                return None  # Data too old, caller should refresh
        
        return await self.query_port.get_bom(query)
    
    async def get_weight_metrics(self, query: GetWeightMetricsQuery) -> WeightMetricsResult:
        """Get comprehensive weight metrics."""
        return await self.query_port.get_weight_metrics(query)
    
    async def get_missing_data_report(self, query: GetMissingDataReportQuery) -> MissingDataReport:
        """Get report on missing materials and masses."""
        return await self.query_port.get_missing_data_report(query)
    
    async def get_cache_info(self, query: GetCacheInfoQuery) -> Optional[CacheInfo]:
        """Get information about cached data."""
        return await self.query_port.get_cache_info(query)
    
    async def get_diagnostics(self, query: GetDiagnosticsQuery) -> DiagnosticsDto:
        """Get system diagnostics information."""
        return await self.query_port.get_diagnostics(query)


# Query result builders (helpers for converting domain objects to DTOs)
class BomResponseBuilder:
    """Builder for BOM response DTOs."""
    
    @staticmethod
    def build_response(bom: Bom) -> BomResponseDto:
        """Build BOM response DTO from domain object."""
        
        # Convert domain objects to DTOs
        onshape_ref_dto = OnshapeReferenceDto(
            document_id=bom.onshape_ref.document_id,
            element_id=bom.onshape_ref.element_id,
            wvm_type=bom.onshape_ref.wvm_type,
            wvm_id=bom.onshape_ref.wvm_id,
            part_id=bom.onshape_ref.part_id
        )
        
        # Build analysis DTO
        analysis_dto = None
        if bom.analysis:
            analysis_dto = BomAnalysisDto(
                total_weight_lb=bom.analysis.total_weight_lb,
                parts_counted=bom.analysis.parts_counted,
                parts_skipped=bom.analysis.parts_skipped,
                missing_material_count=bom.analysis.missing_material_count,
                missing_mass_count=bom.analysis.missing_mass_count,
                subassembly_count=bom.analysis.subassembly_count,
                current_document_parts=bom.analysis.current_document_parts,
                imported_parts=bom.analysis.imported_parts,
                processed_at=bom.analysis.processed_at,
                processing_time_ms=bom.analysis.processing_time_ms
            )
        
        # Build part DTOs
        part_dtos = []
        for part in bom.parts.values():
            part_onshape_ref = None
            if part.onshape_ref:
                part_onshape_ref = OnshapeReferenceDto(
                    document_id=part.onshape_ref.document_id,
                    element_id=part.onshape_ref.element_id,
                    wvm_type=part.onshape_ref.wvm_type,
                    wvm_id=part.onshape_ref.wvm_id,
                    part_id=part.onshape_ref.part_id
                )
            
            part_dto = PartDto(
                item_id=part.item_id,
                name=part.name,
                quantity=part.quantity,
                mass_lb=part.mass.to_pounds() if part.mass else None,
                material=part.material.display_name if part.material else None,
                missing_material=part.is_missing_material,
                missing_mass=part.is_missing_mass,
                parent_id=part.parent_id,
                indent_level=part.indent_level,
                is_subassembly=False,
                has_children=False,
                onshape_ref=part_onshape_ref,
                is_current_document=part.is_current_document,
                vendor=part.vendor,
                part_number=part.part_number,
                cots_category=part.cots_category
            )
            part_dtos.append(part_dto)
        
        # Build assembly DTOs
        assembly_dtos = []
        for assembly in bom.assemblies.values():
            assembly_dto = AssemblyDto(
                item_id=assembly.item_id,
                name=assembly.name,
                quantity=assembly.quantity,
                calculated_mass_lb=assembly.calculated_mass.to_pounds() if assembly.calculated_mass else None,
                parent_id=assembly.parent_id,
                indent_level=assembly.indent_level,
                children=assembly.children,
                has_children_missing_mass=assembly.has_children_missing_mass,
                has_children_missing_material=assembly.has_children_missing_material
            )
            assembly_dtos.append(assembly_dto)
        
        # Calculate cache age
        cache_age_hours = None
        if bom.last_updated:
            age_delta = datetime.utcnow() - bom.last_updated
            cache_age_hours = age_delta.total_seconds() / 3600
        
        return BomResponseDto(
            onshape_ref=onshape_ref_dto,
            analysis=analysis_dto,
            parts=part_dtos,
            assemblies=assembly_dtos,
            is_cached=bom.processing_state.bom_cached,
            last_updated=bom.last_updated,
            cache_age_hours=cache_age_hours
        )


class WeightMetricsBuilder:
    """Builder for weight metrics results."""
    
    @staticmethod
    def build_metrics(bom: Bom, group_by_material: bool = False, group_by_document: bool = False) -> WeightMetricsResult:
        """Build weight metrics from BOM data."""
        
        total_weight = Decimal("0")
        weight_by_material = {}
        weight_by_document = {}
        subassembly_weights = {}
        parts_with_mass = 0
        parts_missing_mass = 0
        
        # Calculate metrics from parts
        for part in bom.parts.values():
            if part.has_mass:
                part_weight = part.total_mass.to_pounds()
                total_weight += part_weight
                parts_with_mass += 1
                
                if group_by_material and part.material and part.material.display_name:
                    material = part.material.display_name
                    weight_by_material[material] = weight_by_material.get(material, Decimal("0")) + part_weight
                
                if group_by_document:
                    doc_key = "current" if part.is_current_document else "imported"
                    weight_by_document[doc_key] = weight_by_document.get(doc_key, Decimal("0")) + part_weight
            else:
                parts_missing_mass += 1
        
        # Calculate metrics from assemblies
        for assembly in bom.assemblies.values():
            if assembly.has_calculated_mass:
                assembly_weight = (assembly.calculated_mass * assembly.quantity).to_pounds()
                subassembly_weights[assembly.name] = assembly_weight
        
        # Calculate confidence score based on completeness
        total_parts = len(bom.parts)
        confidence_score = parts_with_mass / total_parts if total_parts > 0 else 0.0
        
        return WeightMetricsResult(
            total_weight_lb=total_weight,
            weight_by_material=weight_by_material,
            weight_by_document=weight_by_document,
            subassembly_weights=subassembly_weights,
            parts_with_mass=parts_with_mass,
            parts_missing_mass=parts_missing_mass,
            confidence_score=confidence_score
        )


class MissingDataReportBuilder:
    """Builder for missing data reports."""
    
    @staticmethod
    def build_report(bom: Bom, include_suggestions: bool = True) -> MissingDataReport:
        """Build missing data report from BOM."""
        
        missing_materials = []
        missing_masses = []
        suggested_materials = {}
        recommendations = []
        
        for part in bom.parts.values():
            if part.is_missing_material:
                missing_materials.append({
                    "item_id": part.item_id,
                    "name": part.name,
                    "quantity": str(part.quantity),
                    "current_material": part.material.display_name if part.material else "None"
                })
                
                # Suggest material based on classification if available
                if include_suggestions and part.classification:
                    suggested_materials[part.item_id] = part.classification.suggested_material or "Aluminum"
            
            if part.is_missing_mass:
                missing_masses.append({
                    "item_id": part.item_id,
                    "name": part.name,
                    "quantity": str(part.quantity),
                    "material": part.material.display_name if part.material else "Unknown"
                })
        
        # Generate recommendations
        if missing_materials:
            recommendations.append(f"Assign materials to {len(missing_materials)} parts")
        if missing_masses:
            recommendations.append(f"Add mass properties to {len(missing_masses)} parts")
        
        # Calculate completeness score
        total_parts = len(bom.parts)
        complete_parts = sum(1 for part in bom.parts.values() 
                           if part.has_material and part.has_mass)
        completeness_score = complete_parts / total_parts if total_parts > 0 else 1.0
        
        return MissingDataReport(
            missing_materials=missing_materials,
            missing_masses=missing_masses,
            suggested_materials=suggested_materials,
            completeness_score=completeness_score,
            recommendations=recommendations
        )