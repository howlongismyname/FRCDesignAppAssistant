"""Domain models for BOM data structures."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BomPart:
    """Represents a single part in a Bill of Materials."""
    
    # Core identification
    item: str
    name: str
    quantity: float
    
    # Physical properties
    mass_lb: Optional[float] = None
    material: Optional[Dict[str, Any]] = None
    
    # Hierarchy information
    indent_level: int = 0
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    is_subassembly: bool = False
    has_children: bool = False
    
    # Document context
    is_current_document: bool = False
    document_id: Optional[str] = None
    element_id: Optional[str] = None
    
    # Calculated values
    direct_mass: Optional[float] = None
    calculated_mass: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BomPart':
        """Convert raw BOM data dictionary to domain model.
        
        This handles both the new headerIdToValue format and legacy format.
        """
        return cls(
            item=str(data.get('item', '')),
            name=str(data.get('name', '')),
            quantity=float(data.get('quantity', 1.0)),
            mass_lb=data.get('mass_lb'),
            material=data.get('material'),
            indent_level=int(data.get('indentLevel', 0)),
            parent_id=data.get('parentId'),
            children=list(data.get('children', [])),
            is_subassembly=bool(data.get('isSubassembly', False)),
            has_children=bool(data.get('hasChildren', False)),
            is_current_document=bool(data.get('isCurrentDocument', False)),
            document_id=data.get('documentId'),
            element_id=data.get('elementId'),
            direct_mass=data.get('directMass'),
            calculated_mass=data.get('calculatedMass')
        )
    
    def to_dict(self) -> dict:
        """Convert domain model back to dictionary format."""
        return {
            'item': self.item,
            'name': self.name,
            'quantity': self.quantity,
            'mass_lb': self.mass_lb,
            'material': self.material,
            'indentLevel': self.indent_level,
            'parentId': self.parent_id,
            'children': self.children,
            'isSubassembly': self.is_subassembly,
            'hasChildren': self.has_children,
            'isCurrentDocument': self.is_current_document,
            'documentId': self.document_id,
            'elementId': self.element_id,
            'directMass': self.direct_mass,
            'calculatedMass': self.calculated_mass
        }
    
    def has_material_info(self) -> bool:
        """Check if this part has material information."""
        return bool(self.material and self.material != "")
    
    def get_effective_mass(self) -> Optional[float]:
        """Get the most appropriate mass value for calculations."""
        return self.calculated_mass or self.direct_mass or self.mass_lb


@dataclass
class WeightMetrics:
    """Weight calculation results for a BOM."""
    
    unit: str = "lb"
    total_weight: float = 0.0
    rows_counted: int = 0
    rows_skipped: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WeightMetrics':
        """Create from dictionary data."""
        return cls(
            unit=data.get('unit', 'lb'),
            total_weight=float(data.get('total_weight', 0.0)),
            rows_counted=int(data.get('rows_counted', 0)),
            rows_skipped=int(data.get('rows_skipped', 0))
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            'unit': self.unit,
            'total_weight': self.total_weight,
            'rows_counted': self.rows_counted,
            'rows_skipped': self.rows_skipped
        }


@dataclass
class BomAnalysis:
    """Complete BOM analysis results."""
    
    weight_metrics: WeightMetrics
    missing_material_parts: List[BomPart]
    all_parts: Optional[List[BomPart]] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BomAnalysis':
        """Create from dictionary data."""
        return cls(
            weight_metrics=WeightMetrics.from_dict(data.get('weight_metrics', {})),
            missing_material_parts=[
                BomPart.from_dict(part_data) 
                for part_data in data.get('missing_material_parts', [])
            ],
            all_parts=[
                BomPart.from_dict(part_data)
                for part_data in data.get('all_parts', [])
            ] if data.get('all_parts') else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            'weight_metrics': self.weight_metrics.to_dict(),
            'missing_material_parts': [part.to_dict() for part in self.missing_material_parts]
        }
        if self.all_parts is not None:
            result['all_parts'] = [part.to_dict() for part in self.all_parts]
        return result