"""BOM data processor for converting Onshape API responses to domain objects."""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from ..domain.bom import (
    Bom, Part, Assembly, Material, OnshapeReference, 
    BomAnalysis, ElementType
)
from ..domain.geometry import Mass, MassUnit, Dimensions, MassProperties
from ..domain.strategies import default_classifier
from ..domain.errors import BomDataError
from .dto import OnshapeReferenceDto


logger = logging.getLogger(__name__)


class BomProcessor:
    """Processes raw BOM data from Onshape API into domain objects."""
    
    def __init__(self):
        self.classifier = default_classifier
    
    async def process_bom_data(
        self,
        bom_data: Dict[str, Any],
        onshape_ref: OnshapeReference,
        configuration_id: Optional[str] = None
    ) -> Bom:
        """Process raw BOM data from Onshape API into a Bom domain object."""
        
        logger.info("Processing BOM data", extra={
                   "document_id": onshape_ref.document_id,
                   "element_id": onshape_ref.element_id
                   })
        
        # Create BOM aggregate
        bom = Bom(
            onshape_ref=onshape_ref,
            configuration_id=configuration_id
        )
        
        # Extract BOM items from API response
        items = self._extract_bom_items(bom_data)
        
        # Process each item
        for item_data in items:
            try:
                item = await self._process_bom_item(item_data, onshape_ref)
                
                if isinstance(item, Part):
                    bom.add_part(item)
                elif isinstance(item, Assembly):
                    bom.add_assembly(item)
                    
            except Exception as e:
                logger.warning(f"Failed to process BOM item {item_data.get('id', 'unknown')}: {e}")
                continue
        
        # Build hierarchy relationships
        bom.build_hierarchy()
        
        # Calculate assembly masses
        bom.calculate_assembly_masses()
        
        # Perform analysis
        bom.analyze()
        
        logger.info("BOM processing completed", extra={
                   "parts_count": len(bom.parts),
                   "assemblies_count": len(bom.assemblies),
                   "total_weight_lb": float(bom.analysis.total_weight_lb) if bom.analysis else 0
                   })
        
        return bom
    
    def _extract_bom_items(self, bom_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract BOM items from Onshape API response."""
        
        # Handle different API response formats
        if "items" in bom_data:
            return bom_data["items"]
        elif "bomTable" in bom_data and "items" in bom_data["bomTable"]:
            return bom_data["bomTable"]["items"]
        elif isinstance(bom_data, list):
            return bom_data
        else:
            logger.warning("Unexpected BOM data format", extra={"keys": list(bom_data.keys())})
            return []
    
    async def _process_bom_item(
        self,
        item_data: Dict[str, Any],
        parent_onshape_ref: OnshapeReference
    ) -> Optional[Part | Assembly]:
        """Process a single BOM item."""
        
        # Extract basic properties
        item_id = item_data.get("id", item_data.get("itemId", "unknown"))
        name = item_data.get("name", item_data.get("partName", "Unnamed"))
        quantity = self._parse_quantity(item_data.get("quantity", "1"))
        indent_level = item_data.get("indentLevel", 0)
        
        # Determine if this is a part or assembly
        is_assembly = item_data.get("type") == "Assembly" or item_data.get("hasChildren", False)
        
        if is_assembly:
            return await self._create_assembly(item_data, item_id, name, quantity, indent_level)
        else:
            return await self._create_part(item_data, item_id, name, quantity, indent_level, parent_onshape_ref)
    
    async def _create_part(
        self,
        item_data: Dict[str, Any],
        item_id: str,
        name: str,
        quantity: Decimal,
        indent_level: int,
        parent_onshape_ref: OnshapeReference
    ) -> Part:
        """Create a Part domain object from BOM item data."""
        
        # Parse mass
        mass = None
        mass_data = item_data.get("mass", item_data.get("weight"))
        if mass_data:
            mass = self._parse_mass(mass_data)
        
        # Parse material
        material = Material.from_bom_data(item_data.get("material"))
        
        # Create Onshape reference for part
        onshape_ref = None
        if item_data.get("documentId") and item_data.get("elementId"):
            onshape_ref = OnshapeReference(
                document_id=item_data["documentId"],
                element_id=item_data["elementId"],
                wvm_type=item_data.get("wvmType", "w"),
                wvm_id=item_data.get("wvmId", "master"),
                part_id=item_data.get("partId")
            )
        
        # Determine if part is from current document
        is_current_document = (
            onshape_ref and
            onshape_ref.document_id == parent_onshape_ref.document_id
        )
        
        # Parse dimensions if available
        dimensions = None
        if item_data.get("dimensions"):
            dimensions = self._parse_dimensions(item_data["dimensions"])
        
        # Parse mass properties if available
        mass_properties = None
        if item_data.get("massProperties"):
            mass_properties = self._parse_mass_properties(item_data["massProperties"])
        
        # Create part
        part = Part(
            item_id=item_id,
            name=name,
            quantity=quantity,
            mass=mass,
            material=material,
            indent_level=indent_level,
            onshape_ref=onshape_ref,
            is_current_document=is_current_document,
            dimensions=dimensions,
            mass_properties=mass_properties,
            vendor=item_data.get("vendor"),
            part_number=item_data.get("partNumber"),
            cots_category=item_data.get("cotsCategory")
        )
        
        # Classify part
        if self.classifier:
            try:
                classification = self.classifier.classify(
                    name=name,
                    dimensions=dimensions,
                    mass_properties=mass_properties,
                    material=material.display_name
                )
                part.update_classification(classification)
            except Exception as e:
                logger.warning(f"Failed to classify part {item_id}: {e}")
        
        return part
    
    async def _create_assembly(
        self,
        item_data: Dict[str, Any],
        item_id: str,
        name: str,
        quantity: Decimal,
        indent_level: int
    ) -> Assembly:
        """Create an Assembly domain object from BOM item data."""
        
        # Create Onshape reference for assembly
        onshape_ref = None
        if item_data.get("documentId") and item_data.get("elementId"):
            onshape_ref = OnshapeReference(
                document_id=item_data["documentId"],
                element_id=item_data["elementId"],
                wvm_type=item_data.get("wvmType", "w"),
                wvm_id=item_data.get("wvmId", "master")
            )
        
        assembly = Assembly(
            item_id=item_id,
            name=name,
            quantity=quantity,
            indent_level=indent_level,
            onshape_ref=onshape_ref
        )
        
        return assembly
    
    def _parse_quantity(self, quantity_data: Any) -> Decimal:
        """Parse quantity from various formats."""
        if isinstance(quantity_data, (int, float)):
            return Decimal(str(quantity_data))
        elif isinstance(quantity_data, str):
            try:
                # Remove any non-numeric characters except decimal point
                cleaned = ''.join(c for c in quantity_data if c.isdigit() or c == '.')
                return Decimal(cleaned) if cleaned else Decimal("1")
            except Exception:
                return Decimal("1")
        else:
            return Decimal("1")
    
    def _parse_mass(self, mass_data: Any) -> Optional[Mass]:
        """Parse mass from various formats."""
        if isinstance(mass_data, str):
            return Mass.from_string(mass_data)
        elif isinstance(mass_data, dict):
            value = mass_data.get("value")
            unit = mass_data.get("unit", "lb")
            
            if value is not None:
                try:
                    mass_value = Decimal(str(value))
                    unit_enum = {
                        "lb": MassUnit.POUNDS,
                        "lbs": MassUnit.POUNDS,
                        "kg": MassUnit.KILOGRAMS,
                        "g": MassUnit.GRAMS
                    }.get(unit.lower(), MassUnit.POUNDS)
                    
                    return Mass(value=mass_value, unit=unit_enum)
                except Exception:
                    pass
        elif isinstance(mass_data, (int, float)):
            return Mass(value=Decimal(str(mass_data)), unit=MassUnit.POUNDS)
        
        return None
    
    def _parse_dimensions(self, dimensions_data: Dict[str, Any]) -> Optional[Dimensions]:
        """Parse dimensions from API data."""
        try:
            length = Decimal(str(dimensions_data.get("length", 0)))
            width = Decimal(str(dimensions_data.get("width", 0)))
            height = Decimal(str(dimensions_data.get("height", 0)))
            unit = dimensions_data.get("unit", "mm")
            
            return Dimensions(
                length=length,
                width=width,
                height=height,
                unit=unit
            )
        except Exception as e:
            logger.warning(f"Failed to parse dimensions: {e}")
            return None
    
    def _parse_mass_properties(self, mass_props_data: Dict[str, Any]) -> Optional[MassProperties]:
        """Parse mass properties from API data."""
        try:
            mass = None
            if mass_props_data.get("mass"):
                mass = self._parse_mass(mass_props_data["mass"])
            
            volume = None
            if mass_props_data.get("volume"):
                volume = Decimal(str(mass_props_data["volume"]))
            
            density = None
            if mass_props_data.get("density"):
                density = Decimal(str(mass_props_data["density"]))
            
            center_of_mass = None
            if mass_props_data.get("centerOfMass"):
                com_data = mass_props_data["centerOfMass"]
                if isinstance(com_data, list) and len(com_data) >= 3:
                    center_of_mass = (
                        Decimal(str(com_data[0])),
                        Decimal(str(com_data[1])),
                        Decimal(str(com_data[2]))
                    )
            
            return MassProperties(
                mass=mass,
                volume=volume,
                density=density,
                center_of_mass=center_of_mass
            )
        except Exception as e:
            logger.warning(f"Failed to parse mass properties: {e}")
            return None