"""Storage adapters for structured and blob data."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pathlib import Path
import pickle
import hashlib

from ..domain.bom import Bom, OnshapeReference
from ..application.services import StoragePort


logger = logging.getLogger(__name__)


class StructuredStorageAdapter:
    """Adapter for storing structured BOM data using Onshape structured storage."""
    
    def __init__(self, onshape_client, storage_element_id: str):
        self.onshape_client = onshape_client
        self.storage_element_id = storage_element_id
    
    async def save_bom(self, bom: Bom) -> str:
        """Save BOM data to structured storage and return cache key."""
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(bom.onshape_ref, bom.configuration_id)
            
            # Serialize BOM to structured format
            bom_data = self._serialize_bom(bom)
            
            # Store in Onshape structured storage
            await self._store_structured_data(cache_key, bom_data)
            
            logger.info(f"Saved BOM to structured storage with key: {cache_key}")
            return cache_key
            
        except Exception as e:
            logger.error(f"Failed to save BOM to structured storage: {e}")
            raise
    
    async def get_bom(self, cache_key: str) -> Optional[Bom]:
        """Retrieve BOM data from structured storage."""
        
        try:
            # Fetch from structured storage
            bom_data = await self._get_structured_data(cache_key)
            if not bom_data:
                return None
            
            # Deserialize to domain object
            bom = self._deserialize_bom(bom_data)
            
            logger.info(f"Retrieved BOM from structured storage with key: {cache_key}")
            return bom
            
        except Exception as e:
            logger.error(f"Failed to get BOM from structured storage: {e}")
            return None
    
    async def _store_structured_data(self, key: str, data: Dict[str, Any]) -> None:
        """Store data in Onshape structured storage."""
        
        # Build path for structured storage
        path = f"/api/v9/elements/d/{self.storage_element_id}/structured"
        
        payload = {
            "changeId": str(uuid.uuid4()),
            "entities": [
                {
                    "id": key,
                    "type": "bom_cache",
                    "data": data
                }
            ]
        }
        
        # Use Onshape client to make the request
        await self.onshape_client._make_request("POST", path, json=payload)
    
    async def _get_structured_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from Onshape structured storage."""
        
        path = f"/api/v9/elements/d/{self.storage_element_id}/structured/{key}"
        
        try:
            response = await self.onshape_client._make_request("GET", path)
            return response.json()
        except Exception:
            return None
    
    def _serialize_bom(self, bom: Bom) -> Dict[str, Any]:
        """Serialize BOM domain object to dictionary."""
        
        # Convert parts to serializable format
        parts_data = {}
        for part_id, part in bom.parts.items():
            parts_data[part_id] = {
                "item_id": part.item_id,
                "name": part.name,
                "quantity": str(part.quantity),
                "mass_lb": str(part.mass.to_pounds()) if part.mass else None,
                "material": {
                    "display_name": part.material.display_name,
                    "id": part.material.id,
                    "density": str(part.material.density) if part.material.density else None,
                    "type": part.material.type
                },
                "parent_id": part.parent_id,
                "indent_level": part.indent_level,
                "is_current_document": part.is_current_document,
                "vendor": part.vendor,
                "part_number": part.part_number,
                "cots_category": part.cots_category,
                "onshape_ref": {
                    "document_id": part.onshape_ref.document_id,
                    "element_id": part.onshape_ref.element_id,
                    "wvm_type": part.onshape_ref.wvm_type,
                    "wvm_id": part.onshape_ref.wvm_id,
                    "part_id": part.onshape_ref.part_id
                } if part.onshape_ref else None,
                "classification": {
                    "part_type": part.classification.part_type.name,
                    "confidence": part.classification.confidence,
                    "reasoning": part.classification.reasoning,
                    "suggested_material": part.classification.suggested_material,
                    "manufacturing_process": part.classification.manufacturing_process
                } if part.classification else None
            }
        
        # Convert assemblies to serializable format
        assemblies_data = {}
        for assembly_id, assembly in bom.assemblies.items():
            assemblies_data[assembly_id] = {
                "item_id": assembly.item_id,
                "name": assembly.name,
                "quantity": str(assembly.quantity),
                "calculated_mass_lb": str(assembly.calculated_mass.to_pounds()) if assembly.calculated_mass else None,
                "parent_id": assembly.parent_id,
                "indent_level": assembly.indent_level,
                "children": assembly.children,
                "has_children_missing_mass": assembly.has_children_missing_mass,
                "has_children_missing_material": assembly.has_children_missing_material
            }
        
        # Convert analysis to serializable format
        analysis_data = None
        if bom.analysis:
            analysis_data = {
                "total_weight_lb": str(bom.analysis.total_weight_lb),
                "parts_counted": bom.analysis.parts_counted,
                "parts_skipped": bom.analysis.parts_skipped,
                "missing_material_count": bom.analysis.missing_material_count,
                "missing_mass_count": bom.analysis.missing_mass_count,
                "subassembly_count": bom.analysis.subassembly_count,
                "current_document_parts": bom.analysis.current_document_parts,
                "imported_parts": bom.analysis.imported_parts,
                "processed_at": bom.analysis.processed_at.isoformat(),
                "processing_time_ms": bom.analysis.processing_time_ms
            }
        
        return {
            "onshape_ref": {
                "document_id": bom.onshape_ref.document_id,
                "element_id": bom.onshape_ref.element_id,
                "wvm_type": bom.onshape_ref.wvm_type,
                "wvm_id": bom.onshape_ref.wvm_id,
                "part_id": bom.onshape_ref.part_id
            },
            "configuration_id": bom.configuration_id,
            "parts": parts_data,
            "assemblies": assemblies_data,
            "analysis": analysis_data,
            "last_updated": bom.last_updated.isoformat(),
            "cache_key": bom.cache_key,
            "version": "1.0"  # Schema version for future compatibility
        }
    
    def _deserialize_bom(self, data: Dict[str, Any]) -> Bom:
        """Deserialize dictionary to BOM domain object."""
        # TODO: Implement deserialization from structured data
        # This would reverse the serialization process above
        # For now, return a minimal BOM object
        
        onshape_ref = OnshapeReference(
            document_id=data["onshape_ref"]["document_id"],
            element_id=data["onshape_ref"]["element_id"],
            wvm_type=data["onshape_ref"]["wvm_type"],
            wvm_id=data["onshape_ref"]["wvm_id"],
            part_id=data["onshape_ref"]["part_id"]
        )
        
        bom = Bom(
            onshape_ref=onshape_ref,
            configuration_id=data.get("configuration_id")
        )
        
        if data.get("last_updated"):
            bom.last_updated = datetime.fromisoformat(data["last_updated"])
        
        bom.cache_key = data.get("cache_key")
        
        return bom
    
    def _generate_cache_key(self, onshape_ref: OnshapeReference, config_id: Optional[str]) -> str:
        """Generate cache key for BOM data."""
        key_parts = [
            onshape_ref.document_id,
            onshape_ref.element_id,
            onshape_ref.wvm_type,
            onshape_ref.wvm_id
        ]
        
        if config_id:
            key_parts.append(config_id)
        
        key_string = "_".join(key_parts)
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"bom_{key_string}_{timestamp}"


class BlobStorageAdapter:
    """Adapter for storing binary data like thumbnails and exported files."""
    
    def __init__(self, onshape_client, blob_element_id: str, local_cache_dir: Optional[str] = None):
        self.onshape_client = onshape_client
        self.blob_element_id = blob_element_id
        self.local_cache_dir = Path(local_cache_dir) if local_cache_dir else None
        
        if self.local_cache_dir:
            self.local_cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_thumbnail(
        self, 
        onshape_ref: OnshapeReference,
        thumbnail_data: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """Save thumbnail to blob storage and return URL."""
        
        try:
            # Generate unique filename
            filename = self._generate_thumbnail_filename(onshape_ref, metadata)
            
            # Save to Onshape blob storage
            blob_url = await self._store_blob_data(filename, thumbnail_data, "image/png")
            
            # Cache locally if configured
            if self.local_cache_dir:
                local_path = self.local_cache_dir / filename
                with open(local_path, 'wb') as f:
                    f.write(thumbnail_data)
            
            logger.info(f"Saved thumbnail to blob storage: {filename}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to save thumbnail: {e}")
            raise
    
    async def save_fab_pack(
        self,
        onshape_ref: OnshapeReference,
        files: List[Dict[str, Any]]
    ) -> str:
        """Save fabrication package and return package ID."""
        
        try:
            # Generate package ID
            package_id = self._generate_package_id(onshape_ref)
            
            # Save each file in the package
            for file_info in files:
                filename = f"{package_id}/{file_info['filename']}"
                blob_url = await self._store_blob_data(
                    filename,
                    file_info['data'],
                    file_info.get('content_type', 'application/octet-stream')
                )
                file_info['blob_url'] = blob_url
            
            # Create package manifest
            manifest = {
                "package_id": package_id,
                "created_at": datetime.now().isoformat(),
                "onshape_ref": {
                    "document_id": onshape_ref.document_id,
                    "element_id": onshape_ref.element_id,
                    "wvm_type": onshape_ref.wvm_type,
                    "wvm_id": onshape_ref.wvm_id
                },
                "files": files
            }
            
            # Save manifest
            manifest_data = json.dumps(manifest, indent=2).encode('utf-8')
            await self._store_blob_data(
                f"{package_id}/manifest.json",
                manifest_data,
                "application/json"
            )
            
            logger.info(f"Saved fabrication package: {package_id}")
            return package_id
            
        except Exception as e:
            logger.error(f"Failed to save fabrication package: {e}")
            raise
    
    async def _store_blob_data(
        self,
        filename: str,
        data: bytes,
        content_type: str
    ) -> str:
        """Store binary data in Onshape blob storage."""
        
        # Build path for blob storage
        path = f"/api/v9/blobelements/d/{self.blob_element_id}/content/{filename}"
        
        # Use multipart upload for binary data
        files = {
            'file': (filename, data, content_type)
        }
        
        # Make request using proper authentication and circuit breaker logic
        if not self.onshape_client.circuit_breaker.call_allowed():
            raise Exception("Circuit breaker is open - too many API failures")
        
        headers = self.onshape_client._build_auth_headers("POST", path)
        
        try:
            response = await self.onshape_client.client.post(
                f"{self.onshape_client.base_url}{path}",
                files=files,
                headers=headers
            )
            
            if response.status_code not in (200, 201):
                self.onshape_client.circuit_breaker.record_failure()
                raise Exception(f"Failed to upload blob: {response.status_code}")
            
            self.onshape_client.circuit_breaker.record_success()
            
        except Exception as e:
            self.onshape_client.circuit_breaker.record_failure()
            raise Exception(f"Blob upload failed: {e}") from e
        
        # Return the blob URL
        return f"{self.onshape_client.base_url}{path}"
    
    def _generate_thumbnail_filename(
        self,
        onshape_ref: OnshapeReference,
        metadata: Dict[str, Any]
    ) -> str:
        """Generate filename for thumbnail."""
        
        # Create hash of reference for uniqueness
        ref_string = f"{onshape_ref.document_id}_{onshape_ref.element_id}_{onshape_ref.part_id}"
        ref_hash = hashlib.sha256(ref_string.encode()).hexdigest()[:8]
        
        size = metadata.get('size', '300x300')
        view_angle = metadata.get('view_angle', 'iso')
        
        return f"thumbnails/{ref_hash}_{size}_{view_angle}.png"
    
    def _generate_package_id(self, onshape_ref: OnshapeReference) -> str:
        """Generate package ID for fabrication package."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_short = onshape_ref.document_id[:8]
        element_short = onshape_ref.element_id[:8]
        
        return f"fabpack_{doc_short}_{element_short}_{timestamp}"


# File system fallback storage (for development/testing)
class FileSystemStorageAdapter:
    """File system-based storage adapter for development."""
    
    def __init__(self, storage_dir: str = "./storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.bom_dir = self.storage_dir / "boms"
        self.blob_dir = self.storage_dir / "blobs"
        
        self.bom_dir.mkdir(exist_ok=True)
        self.blob_dir.mkdir(exist_ok=True)
    
    async def save_bom(self, bom: Bom) -> str:
        """Save BOM to file system using JSON serialization."""
        
        cache_key = self._generate_cache_key(bom.onshape_ref, bom.configuration_id)
        file_path = self.bom_dir / f"{cache_key}.json"
        
        # Serialize BOM to JSON-safe format
        bom_data = self._serialize_bom(bom)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(bom_data, f, indent=2, ensure_ascii=False)
        
        return cache_key
    
    async def get_bom(self, cache_key: str) -> Optional[Bom]:
        """Get BOM from file system using JSON deserialization."""
        
        file_path = self.bom_dir / f"{cache_key}.json"
        
        # Also check for legacy pickle files and migrate them
        legacy_path = self.bom_dir / f"{cache_key}.pkl"
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    bom_data = json.load(f)
                return self._deserialize_bom(bom_data)
            except Exception as e:
                logger.error(f"Failed to load BOM from {file_path}: {e}")
                return None
        elif legacy_path.exists():
            # Legacy pickle file - load and migrate to JSON
            try:
                with open(legacy_path, 'rb') as f:
                    bom = pickle.load(f)
                
                # Save as JSON for future use
                await self.save_bom(bom)
                
                # Remove legacy pickle file
                legacy_path.unlink()
                
                logger.info(f"Migrated legacy pickle file to JSON: {cache_key}")
                return bom
            except Exception as e:
                logger.error(f"Failed to migrate legacy BOM from {legacy_path}: {e}")
                return None
        
        return None
    
    async def save_thumbnail(
        self, 
        onshape_ref: OnshapeReference,
        thumbnail_data: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """Save thumbnail to file system."""
        
        filename = self._generate_thumbnail_filename(onshape_ref, metadata)
        file_path = self.blob_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(thumbnail_data)
        
        return f"/storage/blobs/{filename}"
    
    async def save_fab_pack(
        self,
        onshape_ref: OnshapeReference,
        files: List[Dict[str, Any]]
    ) -> str:
        """Save fabrication package to file system."""
        
        package_id = self._generate_package_id(onshape_ref)
        package_dir = self.blob_dir / package_id
        package_dir.mkdir(parents=True, exist_ok=True)
        
        for file_info in files:
            file_path = package_dir / file_info['filename']
            with open(file_path, 'wb') as f:
                f.write(file_info['data'])
        
        return package_id
    
    def _serialize_bom(self, bom: Bom) -> Dict[str, Any]:
        """Serialize BOM domain object to dictionary (copied from StructuredStorageAdapter)."""
        
        # Convert parts to serializable format
        parts_data = {}
        for part_id, part in bom.parts.items():
            parts_data[part_id] = {
                "item_id": part.item_id,
                "name": part.name,
                "quantity": str(part.quantity),
                "mass_lb": str(part.mass.to_pounds()) if part.mass else None,
                "material": {
                    "display_name": part.material.display_name,
                    "id": part.material.id,
                    "density": str(part.material.density) if part.material.density else None,
                    "type": part.material.type
                },
                "parent_id": part.parent_id,
                "indent_level": part.indent_level,
                "is_current_document": part.is_current_document,
                "vendor": part.vendor,
                "part_number": part.part_number,
                "cots_category": part.cots_category,
                "onshape_ref": {
                    "document_id": part.onshape_ref.document_id,
                    "element_id": part.onshape_ref.element_id,
                    "wvm_type": part.onshape_ref.wvm_type,
                    "wvm_id": part.onshape_ref.wvm_id,
                    "part_id": part.onshape_ref.part_id
                } if part.onshape_ref else None,
                "classification": {
                    "part_type": part.classification.part_type.name,
                    "confidence": part.classification.confidence,
                    "reasoning": part.classification.reasoning,
                    "suggested_material": part.classification.suggested_material,
                    "manufacturing_process": part.classification.manufacturing_process
                } if part.classification else None
            }
        
        # Convert assemblies to serializable format
        assemblies_data = {}
        for assembly_id, assembly in bom.assemblies.items():
            assemblies_data[assembly_id] = {
                "item_id": assembly.item_id,
                "name": assembly.name,
                "quantity": str(assembly.quantity),
                "calculated_mass_lb": str(assembly.calculated_mass.to_pounds()) if assembly.calculated_mass else None,
                "parent_id": assembly.parent_id,
                "indent_level": assembly.indent_level,
                "children": assembly.children,
                "has_children_missing_mass": assembly.has_children_missing_mass,
                "has_children_missing_material": assembly.has_children_missing_material
            }
        
        # Convert analysis to serializable format
        analysis_data = None
        if bom.analysis:
            analysis_data = {
                "total_weight_lb": str(bom.analysis.total_weight_lb),
                "parts_counted": bom.analysis.parts_counted,
                "parts_skipped": bom.analysis.parts_skipped,
                "missing_material_count": bom.analysis.missing_material_count,
                "missing_mass_count": bom.analysis.missing_mass_count,
                "subassembly_count": bom.analysis.subassembly_count,
                "current_document_parts": bom.analysis.current_document_parts,
                "imported_parts": bom.analysis.imported_parts,
                "processed_at": bom.analysis.processed_at.isoformat(),
                "processing_time_ms": bom.analysis.processing_time_ms
            }
        
        return {
            "onshape_ref": {
                "document_id": bom.onshape_ref.document_id,
                "element_id": bom.onshape_ref.element_id,
                "wvm_type": bom.onshape_ref.wvm_type,
                "wvm_id": bom.onshape_ref.wvm_id,
                "part_id": bom.onshape_ref.part_id
            },
            "configuration_id": bom.configuration_id,
            "parts": parts_data,
            "assemblies": assemblies_data,
            "analysis": analysis_data,
            "last_updated": bom.last_updated.isoformat(),
            "cache_key": bom.cache_key,
            "version": "1.0"  # Schema version for future compatibility
        }
    
    def _deserialize_bom(self, data: Dict[str, Any]) -> Bom:
        """Deserialize dictionary to BOM domain object (copied from StructuredStorageAdapter)."""
        # TODO: Implement full deserialization from structured data
        # This would reverse the serialization process above
        # For now, return a minimal BOM object
        
        onshape_ref = OnshapeReference(
            document_id=data["onshape_ref"]["document_id"],
            element_id=data["onshape_ref"]["element_id"],
            wvm_type=data["onshape_ref"]["wvm_type"],
            wvm_id=data["onshape_ref"]["wvm_id"],
            part_id=data["onshape_ref"]["part_id"]
        )
        
        bom = Bom(
            onshape_ref=onshape_ref,
            configuration_id=data.get("configuration_id")
        )
        
        if data.get("last_updated"):
            bom.last_updated = datetime.fromisoformat(data["last_updated"])
        
        bom.cache_key = data.get("cache_key")
        
        return bom
    
    def _generate_cache_key(self, onshape_ref: OnshapeReference, config_id: Optional[str]) -> str:
        """Generate cache key."""
        key_parts = [
            onshape_ref.document_id,
            onshape_ref.element_id,
            onshape_ref.wvm_type,
            onshape_ref.wvm_id
        ]
        
        if config_id:
            key_parts.append(config_id)
        
        key_string = "_".join(key_parts)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"bom_{key_string}_{timestamp}"
    
    def _generate_thumbnail_filename(
        self,
        onshape_ref: OnshapeReference,
        metadata: Dict[str, Any]
    ) -> str:
        """Generate filename for thumbnail."""
        
        ref_string = f"{onshape_ref.document_id}_{onshape_ref.element_id}_{onshape_ref.part_id}"
        ref_hash = hashlib.sha256(ref_string.encode()).hexdigest()[:8]
        
        size = metadata.get('size', '300x300')
        view_angle = metadata.get('view_angle', 'iso')
        
        return f"thumbnails/{ref_hash}_{size}_{view_angle}.png"
    
    def _generate_package_id(self, onshape_ref: OnshapeReference) -> str:
        """Generate package ID."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_short = onshape_ref.document_id[:8]
        element_short = onshape_ref.element_id[:8]
        
        return f"fabpack_{doc_short}_{element_short}_{timestamp}"