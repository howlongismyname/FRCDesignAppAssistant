"""Part classification strategies."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from typing import Protocol, Optional, List
from decimal import Decimal

from .geometry import Dimensions, MassProperties


class PartType(Enum):
    """Part classification types."""
    PLATE = auto()        # Flat plate/sheet
    SHAFT = auto()        # Cylindrical shaft/rod
    TUBE = auto()         # Hollow tube
    BRACKET = auto()      # L-bracket or similar
    FASTENER = auto()     # Bolt, screw, nut, washer
    BEARING = auto()      # Ball bearing, bushing
    GEAR = auto()         # Gears and sprockets
    ELECTRONICS = auto()  # Motors, sensors, controllers
    FRAME = auto()        # Structural frame members
    CUSTOM = auto()       # Custom fabricated parts
    UNKNOWN = auto()      # Cannot classify


@dataclass
class ClassificationResult:
    """Result of part classification."""
    
    part_type: PartType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    suggested_material: Optional[str] = None
    manufacturing_process: Optional[str] = None


class PartClassificationStrategy(Protocol):
    """Strategy interface for classifying parts."""
    
    def classify(
        self, 
        name: str,
        dimensions: Optional[Dimensions] = None,
        mass_properties: Optional[MassProperties] = None,
        material: Optional[str] = None
    ) -> ClassificationResult:
        """Classify a part based on available information."""
        ...


class NameBasedClassifier:
    """Classify parts based on name patterns."""
    
    def classify(
        self, 
        name: str,
        dimensions: Optional[Dimensions] = None,
        mass_properties: Optional[MassProperties] = None,
        material: Optional[str] = None
    ) -> ClassificationResult:
        """Classify part based on name patterns."""
        name_lower = name.lower().strip()
        
        # Plate patterns
        plate_keywords = ["plate", "sheet", "panel", "deck"]
        if any(keyword in name_lower for keyword in plate_keywords):
            return ClassificationResult(
                part_type=PartType.PLATE,
                confidence=0.8,
                reasoning=f"Name contains plate/sheet keywords: {name}",
                suggested_material="Aluminum",
                manufacturing_process="CNC/Laser Cut"
            )
        
        # Shaft patterns  
        shaft_keywords = ["shaft", "rod", "axle", "pin"]
        if any(keyword in name_lower for keyword in shaft_keywords):
            return ClassificationResult(
                part_type=PartType.SHAFT,
                confidence=0.8,
                reasoning=f"Name contains shaft/rod keywords: {name}",
                suggested_material="Steel",
                manufacturing_process="Turned"
            )
        
        # Tube patterns
        tube_keywords = ["tube", "pipe", "tubing"]
        if any(keyword in name_lower for keyword in tube_keywords):
            return ClassificationResult(
                part_type=PartType.TUBE,
                confidence=0.8,
                reasoning=f"Name contains tube keywords: {name}",
                suggested_material="Aluminum",
                manufacturing_process="Purchased/Cut to Length"
            )
        
        # Bracket patterns
        bracket_keywords = ["bracket", "mount", "support", "angle"]
        if any(keyword in name_lower for keyword in bracket_keywords):
            return ClassificationResult(
                part_type=PartType.BRACKET,
                confidence=0.7,
                reasoning=f"Name contains bracket keywords: {name}",
                suggested_material="Aluminum",
                manufacturing_process="CNC/Bent"
            )
        
        # Fastener patterns
        fastener_keywords = ["bolt", "screw", "nut", "washer", "rivet"]
        if any(keyword in name_lower for keyword in fastener_keywords):
            return ClassificationResult(
                part_type=PartType.FASTENER,
                confidence=0.9,
                reasoning=f"Name contains fastener keywords: {name}",
                suggested_material="Steel",
                manufacturing_process="Purchased"
            )
        
        # Bearing patterns
        bearing_keywords = ["bearing", "bushing", "sleeve"]
        if any(keyword in name_lower for keyword in bearing_keywords):
            return ClassificationResult(
                part_type=PartType.BEARING,
                confidence=0.8,
                reasoning=f"Name contains bearing keywords: {name}",
                suggested_material="Steel/Bronze",
                manufacturing_process="Purchased"
            )
        
        # Gear patterns
        gear_keywords = ["gear", "sprocket", "pulley", "belt"]
        if any(keyword in name_lower for keyword in gear_keywords):
            return ClassificationResult(
                part_type=PartType.GEAR,
                confidence=0.7,
                reasoning=f"Name contains gear keywords: {name}",
                suggested_material="Aluminum/Steel",
                manufacturing_process="CNC/Purchased"
            )
        
        # Electronics patterns
        electronics_keywords = ["motor", "sensor", "controller", "pcb", "wire", "cable"]
        if any(keyword in name_lower for keyword in electronics_keywords):
            return ClassificationResult(
                part_type=PartType.ELECTRONICS,
                confidence=0.9,
                reasoning=f"Name contains electronics keywords: {name}",
                manufacturing_process="Purchased"
            )
        
        # Frame patterns
        frame_keywords = ["frame", "rail", "beam", "strut", "extrusion"]
        if any(keyword in name_lower for keyword in frame_keywords):
            return ClassificationResult(
                part_type=PartType.FRAME,
                confidence=0.7,
                reasoning=f"Name contains frame keywords: {name}",
                suggested_material="Aluminum",
                manufacturing_process="Purchased/Cut to Length"
            )
        
        # Default to unknown
        return ClassificationResult(
            part_type=PartType.UNKNOWN,
            confidence=0.0,
            reasoning="No matching patterns found in name"
        )


class GeometryBasedClassifier:
    """Classify parts based on geometric properties."""
    
    def classify(
        self, 
        name: str,
        dimensions: Optional[Dimensions] = None,
        mass_properties: Optional[MassProperties] = None,
        material: Optional[str] = None
    ) -> ClassificationResult:
        """Classify part based on geometry."""
        if not dimensions:
            return ClassificationResult(
                part_type=PartType.UNKNOWN,
                confidence=0.0,
                reasoning="No dimensions available"
            )
        
        length, width, height = dimensions.length, dimensions.width, dimensions.height
        
        # Sort dimensions to identify aspect ratios
        sorted_dims = sorted([length, width, height])
        min_dim, mid_dim, max_dim = sorted_dims
        
        # Calculate ratios
        aspect_ratio = max_dim / min_dim if min_dim > 0 else 0
        thickness_ratio = min_dim / mid_dim if mid_dim > 0 else 0
        
        # Plate classification: one dimension much smaller than others
        if thickness_ratio < 0.1 and aspect_ratio > 2:
            return ClassificationResult(
                part_type=PartType.PLATE,
                confidence=0.7,
                reasoning=f"Thin geometry - thickness ratio: {thickness_ratio:.2f}"
            )
        
        # Shaft classification: two dimensions similar, one much longer
        if aspect_ratio > 5 and abs(sorted_dims[0] - sorted_dims[1]) / sorted_dims[1] < 0.2:
            return ClassificationResult(
                part_type=PartType.SHAFT,
                confidence=0.6,
                reasoning=f"Long cylindrical geometry - aspect ratio: {aspect_ratio:.2f}"
            )
        
        # Compact part (could be fastener or bearing)
        if aspect_ratio < 3 and max_dim < Decimal("50"):  # Less than 50mm
            return ClassificationResult(
                part_type=PartType.FASTENER,
                confidence=0.4,
                reasoning=f"Small compact geometry - max dimension: {max_dim}mm"
            )
        
        return ClassificationResult(
            part_type=PartType.UNKNOWN,
            confidence=0.0,
            reasoning="Geometry doesn't match known patterns"
        )


class CompositeClassifier:
    """Combines multiple classification strategies."""
    
    def __init__(self):
        self.name_classifier = NameBasedClassifier()
        self.geometry_classifier = GeometryBasedClassifier()
    
    def classify(
        self, 
        name: str,
        dimensions: Optional[Dimensions] = None,
        mass_properties: Optional[MassProperties] = None,
        material: Optional[str] = None
    ) -> ClassificationResult:
        """Classify using multiple strategies and combine results."""
        
        # Get results from each classifier
        name_result = self.name_classifier.classify(name, dimensions, mass_properties, material)
        geometry_result = self.geometry_classifier.classify(name, dimensions, mass_properties, material)
        
        # Name-based classification typically has higher confidence
        if name_result.confidence > 0.7:
            return name_result
        
        # If geometry gives better confidence, use it
        if geometry_result.confidence > name_result.confidence:
            return geometry_result
        
        # Otherwise use name result as fallback
        return name_result


# Default classifier instance
default_classifier = CompositeClassifier()