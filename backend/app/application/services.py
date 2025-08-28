"""Application services for Design Assistant use cases."""

from abc import ABC, abstractmethod
from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from ..domain.bom import Bom, OnshapeReference, ElementType
from ..domain.errors import DesignAssistantError, BomDataError
from .commands import (
    RefreshBomCacheCommand, GenerateThumbnailsCommand, 
    BulkUpdateMetadataCommand, BuildFabPackCommand,
    BomCacheResult, ThumbnailResult, MetadataUpdateResult, FabPackResult
)
from .bom_processor import BomProcessor


logger = logging.getLogger(__name__)


# Port interfaces (to be implemented by adapters)
class OnshapeApiPort(Protocol):
    """Port for Onshape API operations."""
    
    async def get_bom_data(
        self, 
        onshape_ref: OnshapeReference,
        configuration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch BOM data from Onshape API."""
        ...
    
    async def get_mass_properties(
        self,
        onshape_ref: OnshapeReference
    ) -> Dict[str, Any]:
        """Get mass properties for parts."""
        ...
    
    async def generate_thumbnail(
        self,
        onshape_ref: OnshapeReference,
        size: str = "300x300",
        view_angle: str = "iso"
    ) -> Dict[str, Any]:
        """Generate thumbnail for a part."""
        ...
    
    async def update_metadata(
        self,
        onshape_ref: OnshapeReference,
        properties: Dict[str, Any]
    ) -> bool:
        """Update metadata properties for a part."""
        ...
    
    async def export_files(
        self,
        onshape_ref: OnshapeReference,
        formats: List[str]
    ) -> List[Dict[str, Any]]:
        """Export files in specified formats."""
        ...


class StoragePort(Protocol):
    """Port for data storage operations."""
    
    async def save_bom(self, bom: Bom) -> str:
        """Save BOM data and return cache key."""
        ...
    
    async def get_bom(self, cache_key: str) -> Optional[Bom]:
        """Retrieve BOM data by cache key."""
        ...
    
    async def save_thumbnail(
        self, 
        onshape_ref: OnshapeReference,
        thumbnail_data: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """Save thumbnail and return URL."""
        ...
    
    async def save_fab_pack(
        self,
        onshape_ref: OnshapeReference,
        files: List[Dict[str, Any]]
    ) -> str:
        """Save fabrication package and return package ID."""
        ...


class CachePort(Protocol):
    """Port for caching operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        ...


class NotificationPort(Protocol):
    """Port for sending notifications."""
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """Notify that BOM was updated."""
        ...
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """Notify that thumbnails are ready."""
        ...


class BomService:
    """Service for BOM-related operations."""
    
    def __init__(
        self,
        onshape_api: OnshapeApiPort,
        storage: StoragePort,
        cache: CachePort,
        notification: Optional[NotificationPort] = None
    ):
        self.onshape_api = onshape_api
        self.storage = storage
        self.cache = cache
        self.notification = notification
        self.bom_processor = BomProcessor()
    
    async def refresh_bom_cache(self, command: RefreshBomCacheCommand) -> BomCacheResult:
        """Refresh BOM cache from Onshape API."""
        start_time = datetime.now()
        
        try:
            # Convert DTO to domain object
            onshape_ref = OnshapeReference(
                document_id=command.onshape_ref.document_id,
                element_id=command.onshape_ref.element_id,
                wvm_type=command.onshape_ref.wvm_type,
                wvm_id=command.onshape_ref.wvm_id,
                part_id=command.onshape_ref.part_id
            )
            
            # Check cache first (unless force refresh)
            cache_key = self._generate_cache_key(onshape_ref, command.configuration_id)
            if not command.force_refresh:
                cached_bom = await self.cache.get(cache_key)
                if cached_bom:
                    logger.info(f"Using cached BOM for {cache_key}")
                    return BomCacheResult(
                        success=True,
                        message="BOM retrieved from cache",
                        cache_key=cache_key,
                        execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    )
            
            # Fetch fresh data from Onshape
            logger.info(f"Fetching fresh BOM data for {onshape_ref.document_id}")
            bom_data = await self.onshape_api.get_bom_data(onshape_ref, command.configuration_id)
            
            # Process BOM data into domain objects
            bom = await self._process_bom_data(bom_data, onshape_ref, command.configuration_id)
            
            # Include mass properties if requested
            if command.include_mass_properties:
                await self._enrich_with_mass_properties(bom)
            
            # Save to storage and cache
            cache_key = await self.storage.save_bom(bom)
            await self.cache.set(cache_key, bom, ttl=3600)  # Cache for 1 hour
            
            # Send notification if configured
            if self.notification:
                await self.notification.notify_bom_updated(onshape_ref)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return BomCacheResult(
                success=True,
                message="BOM cache refreshed successfully",
                parts_processed=len(bom.parts),
                assemblies_processed=len(bom.assemblies),
                total_weight_lb=float(bom.analysis.total_weight_lb) if bom.analysis else None,
                cache_key=cache_key,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Failed to refresh BOM cache: {e}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return BomCacheResult(
                success=False,
                message=f"Failed to refresh BOM cache: {str(e)}",
                errors=[str(e)],
                execution_time_ms=execution_time
            )
    
    async def _process_bom_data(
        self, 
        bom_data: Dict[str, Any], 
        onshape_ref: OnshapeReference,
        configuration_id: Optional[str]
    ) -> Bom:
        """Process raw BOM data into domain objects."""
        return await self.bom_processor.process_bom_data(
            bom_data, onshape_ref, configuration_id
        )
    
    async def _enrich_with_mass_properties(self, bom: Bom) -> None:
        """Enrich BOM parts with mass properties."""
        for part in bom.parts.values():
            if part.onshape_ref:
                try:
                    mass_props = await self.onshape_api.get_mass_properties(part.onshape_ref)
                    # TODO: Parse and set mass properties on part
                except Exception as e:
                    logger.warning(f"Failed to get mass properties for {part.item_id}: {e}")
    
    def _generate_cache_key(self, onshape_ref: OnshapeReference, config_id: Optional[str]) -> str:
        """Generate cache key for BOM data."""
        parts = [
            onshape_ref.document_id,
            onshape_ref.element_id,
            onshape_ref.wvm_type,
            onshape_ref.wvm_id
        ]
        if config_id:
            parts.append(config_id)
        return "_".join(parts)


class ThumbnailService:
    """Service for thumbnail generation operations."""
    
    def __init__(
        self,
        onshape_api: OnshapeApiPort,
        storage: StoragePort,
        notification: Optional[NotificationPort] = None
    ):
        self.onshape_api = onshape_api
        self.storage = storage
        self.notification = notification
    
    async def generate_thumbnails(self, command: GenerateThumbnailsCommand) -> ThumbnailResult:
        """Generate thumbnails for parts in a BOM."""
        start_time = datetime.now()
        
        try:
            onshape_ref = OnshapeReference(
                document_id=command.onshape_ref.document_id,
                element_id=command.onshape_ref.element_id,
                wvm_type=command.onshape_ref.wvm_type,
                wvm_id=command.onshape_ref.wvm_id
            )
            
            # TODO: Get list of parts from BOM if part_ids not specified
            part_refs = await self._get_part_references(onshape_ref, command.part_ids)
            
            thumbnails_generated = 0
            thumbnails_failed = 0
            failed_parts = []
            total_size = 0
            
            # Process in batches to respect rate limits
            for i in range(0, len(part_refs), command.batch_size):
                batch = part_refs[i:i + command.batch_size]
                batch_results = await self._process_thumbnail_batch(
                    batch, command.size, command.view_angle, command.force_regenerate
                )
                
                for result in batch_results:
                    if result["success"]:
                        thumbnails_generated += 1
                        total_size += result.get("size_bytes", 0)
                    else:
                        thumbnails_failed += 1
                        failed_parts.append(result["part_id"])
                
                # Brief pause between batches
                await asyncio.sleep(0.5)
            
            # Send notification if configured
            if self.notification and thumbnails_generated > 0:
                await self.notification.notify_thumbnails_ready(onshape_ref)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ThumbnailResult(
                success=True,
                message=f"Generated {thumbnails_generated} thumbnails, {thumbnails_failed} failed",
                thumbnails_generated=thumbnails_generated,
                thumbnails_failed=thumbnails_failed,
                total_size_bytes=total_size,
                failed_parts=failed_parts,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnails: {e}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ThumbnailResult(
                success=False,
                message=f"Failed to generate thumbnails: {str(e)}",
                errors=[str(e)],
                execution_time_ms=execution_time
            )
    
    async def _get_part_references(
        self, 
        onshape_ref: OnshapeReference, 
        part_ids: Optional[List[str]]
    ) -> List[OnshapeReference]:
        """Get list of part references to process."""
        # TODO: Implement logic to get part references from BOM
        return []
    
    async def _process_thumbnail_batch(
        self,
        part_refs: List[OnshapeReference],
        size: str,
        view_angle: str,
        force_regenerate: bool
    ) -> List[Dict[str, Any]]:
        """Process a batch of thumbnail generation requests."""
        results = []
        
        for part_ref in part_refs:
            try:
                thumbnail_data = await self.onshape_api.generate_thumbnail(
                    part_ref, size, view_angle
                )
                
                # Save thumbnail to storage
                thumbnail_url = await self.storage.save_thumbnail(
                    part_ref, thumbnail_data["data"], thumbnail_data["metadata"]
                )
                
                results.append({
                    "success": True,
                    "part_id": part_ref.part_id,
                    "thumbnail_url": thumbnail_url,
                    "size_bytes": len(thumbnail_data["data"])
                })
                
            except Exception as e:
                logger.error(f"Failed to generate thumbnail for {part_ref.part_id}: {e}")
                results.append({
                    "success": False,
                    "part_id": part_ref.part_id,
                    "error": str(e)
                })
        
        return results


class MetadataService:
    """Service for metadata operations."""
    
    def __init__(self, onshape_api: OnshapeApiPort):
        self.onshape_api = onshape_api
    
    async def bulk_update_metadata(self, command: BulkUpdateMetadataCommand) -> MetadataUpdateResult:
        """Perform bulk metadata updates."""
        start_time = datetime.now()
        
        try:
            total_updates = len(command.updates)
            successful_updates = 0
            failed_updates = 0
            failed_items = []
            
            # Process in batches
            for i in range(0, total_updates, command.batch_size):
                batch = command.updates[i:i + command.batch_size]
                batch_results = await self._process_metadata_batch(batch, command.validate_properties)
                
                for update, result in zip(batch, batch_results):
                    if result["success"]:
                        successful_updates += 1
                    else:
                        failed_updates += 1
                        failed_items.append({
                            "document_id": update["onshape_ref"].document_id,
                            "element_id": update["onshape_ref"].element_id,
                            "error": result["error"]
                        })
                        
                        if not command.skip_on_error:
                            break
                
                # Brief pause between batches
                await asyncio.sleep(0.2)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return MetadataUpdateResult(
                success=failed_updates == 0,
                message=f"Updated {successful_updates}/{total_updates} items",
                total_updates=total_updates,
                successful_updates=successful_updates,
                failed_updates=failed_updates,
                failed_items=failed_items,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Bulk metadata update failed: {e}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return MetadataUpdateResult(
                success=False,
                message=f"Bulk metadata update failed: {str(e)}",
                errors=[str(e)],
                execution_time_ms=execution_time
            )
    
    async def _process_metadata_batch(
        self, 
        batch: List[Dict[str, Any]], 
        validate: bool
    ) -> List[Dict[str, Any]]:
        """Process a batch of metadata updates."""
        results = []
        
        for update in batch:
            try:
                onshape_ref = OnshapeReference(
                    document_id=update["onshape_ref"].document_id,
                    element_id=update["onshape_ref"].element_id,
                    wvm_type=update["onshape_ref"].wvm_type,
                    wvm_id=update["onshape_ref"].wvm_id,
                    part_id=update["onshape_ref"].part_id
                )
                
                if validate:
                    self._validate_properties(update["properties"])
                
                success = await self.onshape_api.update_metadata(
                    onshape_ref, update["properties"]
                )
                
                results.append({
                    "success": success,
                    "error": None if success else "Update failed"
                })
                
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def _validate_properties(self, properties: Dict[str, Any]) -> None:
        """Validate metadata properties."""
        # TODO: Implement property validation logic
        pass


class FabPackService:
    """Service for fabrication package operations."""
    
    def __init__(
        self,
        onshape_api: OnshapeApiPort,
        storage: StoragePort
    ):
        self.onshape_api = onshape_api
        self.storage = storage
    
    async def build_fab_pack(self, command: BuildFabPackCommand) -> FabPackResult:
        """Build fabrication package."""
        start_time = datetime.now()
        
        try:
            onshape_ref = OnshapeReference(
                document_id=command.onshape_ref.document_id,
                element_id=command.onshape_ref.element_id,
                wvm_type=command.onshape_ref.wvm_type,
                wvm_id=command.onshape_ref.wvm_id
            )
            
            # Export files in requested formats
            format_strings = [f.value for f in command.formats]
            exported_files = await self.onshape_api.export_files(onshape_ref, format_strings)
            
            # TODO: Add drawings, BOM CSV, cut lists if requested
            all_files = exported_files.copy()
            
            if command.include_drawings:
                # TODO: Export technical drawings
                pass
            
            if command.include_bom_csv:
                # TODO: Generate BOM CSV
                pass
            
            if command.include_cut_lists:
                # TODO: Generate cut lists
                pass
            
            # Save fabrication package
            package_id = await self.storage.save_fab_pack(onshape_ref, all_files)
            
            total_size = sum(file.get("size_bytes", 0) for file in all_files)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return FabPackResult(
                success=True,
                message="Fabrication package built successfully",
                package_id=package_id,
                files_generated=len(all_files),
                total_size_bytes=total_size,
                file_list=all_files,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Failed to build fabrication package: {e}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return FabPackResult(
                success=False,
                message=f"Failed to build fabrication package: {str(e)}",
                errors=[str(e)],
                execution_time_ms=execution_time
            )