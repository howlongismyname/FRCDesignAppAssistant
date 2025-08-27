"""BOM domain models and aggregates."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from decimal import Decimal
from datetime import datetime
from enum import Enum

from .geometry import Mass, MassProperties, Dimensions
from .status import PartStatus, ProcessingState
from .strategies import PartType, ClassificationResult
from .errors import BomDataError, HierarchyError


class ElementType(Enum):
    """Onshape element types."""
    ASSEMBLY = "ASSEMBLY"
    PARTSTUDIO = "PARTSTUDIO"


@dataclass
class OnshapeReference:
    """Reference to an Onshape element."""
    
    document_id: str
    element_id: str
    wvm_type: str  # w=workspace, v=version, m=microversion
    wvm_id: str
    part_id: Optional[str] = None
    
    def __post_init__(self):
        if self.wvm_type not in ("w", "v", "m"):
            raise BomDataError(f"Invalid wvm_type: {self.wvm_type}")
    
    @property
    def is_workspace(self) -> bool:
        return self.wvm_type == "w"
    
    @property
    def is_version(self) -> bool:
        return self.wvm_type == "v" 
        
    @property
    def is_microversion(self) -> bool:
        return self.wvm_type == "m"


@dataclass
class Material:
    """Material information for a part."""
    
    display_name: Optional[str] = None
    id: Optional[str] = None
    density: Optional[Decimal] = None
    type: Optional[str] = None
    
    def has_material(self) -> bool:
        """Check if material is assigned."""
        return bool(self.display_name or self.id)
    
    @classmethod
    def from_bom_data(cls, material_data: Any) -> "Material":
        """Create Material from BOM data."""
        if not material_data:
            return cls()
        
        if isinstance(material_data, str):
            return cls(display_name=material_data.strip() if material_data.strip() else None)
        elif isinstance(material_data, dict):
            return cls(
                display_name=material_data.get("displayName"),
                id=material_data.get("id"),
                density=Decimal(str(material_data["density"])) if material_data.get("density") else None,
                type=material_data.get("type")
            )
        else:
            return cls()


@dataclass
class Part:
    """Individual part in a BOM."""
    
    # Identity
    item_id: str
    name: str
    onshape_ref: Optional[OnshapeReference] = None
    
    # Physical properties
    quantity: Decimal = Decimal("1")
    mass: Optional[Mass] = None
    material: Material = field(default_factory=Material)
    dimensions: Optional[Dimensions] = None
    mass_properties: Optional[MassProperties] = None
    
    # Hierarchy information
    parent_id: Optional[str] = None
    indent_level: int = 0
    item_path: List[str] = field(default_factory=list)
    
    # Classification and status
    classification: Optional[ClassificationResult] = None
    status: PartStatus = field(default_factory=PartStatus)
    
    # Metadata
    is_current_document: bool = False
    vendor: Optional[str] = None
    part_number: Optional[str] = None
    cots_category: Optional[str] = None
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise BomDataError(f"Invalid quantity for part {self.item_id}: {self.quantity}")
    
    @property
    def has_mass(self) -> bool:
        """Check if part has mass data."""
        return self.mass is not None
    
    @property
    def has_material(self) -> bool:
        """Check if part has material assigned."""
        return self.material.has_material()
    
    @property
    def is_missing_material(self) -> bool:
        """Check if part is missing material."""
        return not self.has_material
    
    @property
    def is_missing_mass(self) -> bool:
        """Check if part is missing mass data."""
        return not self.has_mass
    
    @property
    def total_mass(self) -> Optional[Mass]:
        """Get total mass including quantity."""
        if not self.mass:
            return None
        return self.mass * self.quantity
    
    def update_classification(self, classification: ClassificationResult) -> None:
        """Update part classification."""
        self.classification = classification


@dataclass
class Assembly:
    """Assembly containing parts and sub-assemblies."""
    
    # Identity
    item_id: str
    name: str
    onshape_ref: Optional[OnshapeReference] = None
    
    # Hierarchy
    parent_id: Optional[str] = None
    indent_level: int = 0
    children: List[str] = field(default_factory=list)  # item_ids of children
    
    # Properties
    quantity: Decimal = Decimal("1")
    calculated_mass: Optional[Mass] = None
    
    # Status
    status: PartStatus = field(default_factory=PartStatus)
    
    # Flags
    has_children_missing_mass: bool = False
    has_children_missing_material: bool = False
    
    @property
    def is_subassembly(self) -> bool:
        """Check if this is a subassembly."""
        return len(self.children) > 0
    
    @property
    def has_calculated_mass(self) -> bool:
        """Check if assembly has calculated mass."""
        return self.calculated_mass is not None


@dataclass
class BomAnalysis:
    """Analysis results for a BOM."""
    
    total_weight_lb: Decimal
    parts_counted: int
    parts_skipped: int
    missing_material_count: int
    missing_mass_count: int
    subassembly_count: int
    
    # Breakdown by document
    current_document_parts: int = 0
    imported_parts: int = 0
    
    # Processing metadata
    processed_at: datetime = field(default_factory=datetime.now)
    processing_time_ms: Optional[int] = None


@dataclass  
class Bom:
    """Bill of Materials aggregate root."""
    
    # Identity
    onshape_ref: OnshapeReference
    configuration_id: Optional[str] = None
    
    # Content
    parts: Dict[str, Part] = field(default_factory=dict)
    assemblies: Dict[str, Assembly] = field(default_factory=dict)
    
    # Analysis
    analysis: Optional[BomAnalysis] = None
    
    # Processing state
    processing_state: ProcessingState = field(default_factory=ProcessingState)
    
    # Cache info
    last_updated: datetime = field(default_factory=datetime.now)
    cache_key: Optional[str] = None
    
    def add_part(self, part: Part) -> None:
        """Add a part to the BOM."""
        self.parts[part.item_id] = part
    
    def add_assembly(self, assembly: Assembly) -> None:
        """Add an assembly to the BOM."""
        self.assemblies[assembly.item_id] = assembly
    
    def get_part(self, item_id: str) -> Optional[Part]:
        """Get part by item ID."""
        return self.parts.get(item_id)
    
    def get_assembly(self, item_id: str) -> Optional[Assembly]:
        """Get assembly by item ID.""" 
        return self.assemblies.get(item_id)
    
    def get_all_items(self) -> List:
        """Get all items (parts and assemblies)."""
        items = list(self.parts.values()) + list(self.assemblies.values())
        return sorted(items, key=lambda x: (x.indent_level, x.item_id))
    
    def get_root_items(self) -> List:
        """Get root-level items (indent_level = 0)."""
        return [item for item in self.get_all_items() if item.indent_level == 0]
    
    def get_children(self, parent_id: str) -> List:
        """Get children of a parent item."""
        return [item for item in self.get_all_items() if item.parent_id == parent_id]
    
    def build_hierarchy(self) -> None:
        """Build parent-child relationships."""
        all_items = self.get_all_items()
        
        # Sort by indent level for processing
        all_items.sort(key=lambda x: (x.indent_level, x.item_id))
        
        # Build relationships
        for i, item in enumerate(all_items):
            current_level = item.indent_level
            
            # Find parent (previous item with lower indent level)
            parent = None
            for j in range(i - 1, -1, -1):
                prev_item = all_items[j]
                if prev_item.indent_level < current_level:
                    parent = prev_item
                    break
            
            if parent:
                item.parent_id = parent.item_id
                
                # Add to parent's children if it's an assembly
                if parent.item_id in self.assemblies:
                    assembly = self.assemblies[parent.item_id]
                    if item.item_id not in assembly.children:
                        assembly.children.append(item.item_id)
    
    def calculate_assembly_masses(self) -> None:
        """Calculate masses for assemblies from their components."""
        # Process from deepest level up
        max_level = max((item.indent_level for item in self.get_all_items()), default=0)
        
        for level in range(max_level, -1, -1):
            for assembly in self.assemblies.values():
                if assembly.indent_level == level:
                    self._calculate_assembly_mass(assembly)
    
    def _calculate_assembly_mass(self, assembly: Assembly) -> None:
        """Calculate total mass for a single assembly."""
        total_mass_lb = Decimal("0")
        has_any_mass = False
        has_missing_mass = False
        has_missing_material = False
        
        for child_id in assembly.children:
            # Check parts first
            if child_id in self.parts:
                part = self.parts[child_id]
                if part.has_mass:
                    total_mass_lb += part.total_mass.to_pounds()
                    has_any_mass = True
                else:
                    has_missing_mass = True
                
                if part.is_missing_material:
                    has_missing_material = True
                    
            # Check sub-assemblies
            elif child_id in self.assemblies:
                sub_assembly = self.assemblies[child_id]
                if sub_assembly.calculated_mass:
                    total_mass_lb += (sub_assembly.calculated_mass * sub_assembly.quantity).to_pounds()
                    has_any_mass = True
                else:
                    has_missing_mass = True
                
                # Propagate missing flags from children
                if sub_assembly.has_children_missing_mass:
                    has_missing_mass = True
                if sub_assembly.has_children_missing_material:
                    has_missing_material = True
        
        # Set calculated mass
        if has_any_mass:
            assembly.calculated_mass = Mass(value=total_mass_lb, unit=Mass.MassUnit.POUNDS)
        
        # Update flags
        assembly.has_children_missing_mass = has_missing_mass
        assembly.has_children_missing_material = has_missing_material
    
    def analyze(self) -> BomAnalysis:
        """Perform BOM analysis and update analysis property."""
        all_items = self.get_all_items()
        root_items = self.get_root_items()
        
        # Calculate totals (only from root items to avoid double counting)
        total_weight_lb = Decimal("0")
        for item in root_items:
            if isinstance(item, Part) and item.has_mass:
                total_weight_lb += item.total_mass.to_pounds()
            elif isinstance(item, Assembly) and item.calculated_mass:
                total_weight_lb += (item.calculated_mass * item.quantity).to_pounds()
        
        # Count various statistics
        missing_material_count = sum(1 for part in self.parts.values() if part.is_missing_material)
        missing_mass_count = sum(1 for part in self.parts.values() if part.is_missing_mass)
        
        current_doc_parts = sum(1 for part in self.parts.values() if part.is_current_document)
        imported_parts = len(self.parts) - current_doc_parts
        
        self.analysis = BomAnalysis(
            total_weight_lb=total_weight_lb,
            parts_counted=len(self.parts),
            parts_skipped=0,  # Will be set by processor
            missing_material_count=missing_material_count,
            missing_mass_count=missing_mass_count,
            subassembly_count=len(self.assemblies),
            current_document_parts=current_doc_parts,
            imported_parts=imported_parts
        )
        
        return self.analysis
    
    def mark_bom_cached(self) -> None:
        """Mark BOM as cached."""
        self.processing_state.mark_bom_cached()
        self.last_updated = datetime.now()


# Type aliases for convenience
BomItem = Part | Assembly