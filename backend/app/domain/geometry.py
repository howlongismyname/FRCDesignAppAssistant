"""Geometry and mass properties domain models."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Union
from .errors import MassConversionError


class MassUnit(Enum):
    """Supported mass units."""
    POUNDS = "lb"
    KILOGRAMS = "kg"
    GRAMS = "g"


@dataclass(frozen=True)
class Mass:
    """Value object for mass with unit conversion."""
    
    value: Decimal
    unit: MassUnit
    
    def __post_init__(self):
        if self.value < 0:
            raise MassConversionError("Mass cannot be negative")
    
    @classmethod
    def from_string(cls, mass_str: str) -> Optional["Mass"]:
        """Parse mass from string like '1.5 lb', '2.3 kg', '500 g'."""
        if not mass_str or mass_str.strip().upper() in ("N/A", "", "NULL"):
            return None
            
        try:
            parts = mass_str.strip().split()
            if len(parts) == 0:
                return None
            
            value = Decimal(str(parts[0]))
            unit_str = parts[1].lower() if len(parts) > 1 else "lb"
            
            # Map unit string to enum
            unit_mapping = {
                "lb": MassUnit.POUNDS,
                "lbs": MassUnit.POUNDS, 
                "pound": MassUnit.POUNDS,
                "pounds": MassUnit.POUNDS,
                "kg": MassUnit.KILOGRAMS,
                "kgs": MassUnit.KILOGRAMS,
                "kilogram": MassUnit.KILOGRAMS,
                "kilograms": MassUnit.KILOGRAMS,
                "g": MassUnit.GRAMS,
                "gram": MassUnit.GRAMS,
                "grams": MassUnit.GRAMS,
            }
            
            unit = unit_mapping.get(unit_str, MassUnit.POUNDS)
            return cls(value=value, unit=unit)
            
        except (ValueError, IndexError, TypeError) as e:
            raise MassConversionError(f"Cannot parse mass string '{mass_str}': {e}")
    
    def to_pounds(self) -> Decimal:
        """Convert mass to pounds."""
        if self.unit == MassUnit.POUNDS:
            return self.value
        elif self.unit == MassUnit.KILOGRAMS:
            return self.value * Decimal("2.20462")
        elif self.unit == MassUnit.GRAMS:
            return self.value * Decimal("0.00220462")
        else:
            raise MassConversionError(f"Unknown unit: {self.unit}")
    
    def to_kilograms(self) -> Decimal:
        """Convert mass to kilograms."""
        if self.unit == MassUnit.KILOGRAMS:
            return self.value
        elif self.unit == MassUnit.POUNDS:
            return self.value / Decimal("2.20462")
        elif self.unit == MassUnit.GRAMS:
            return self.value / Decimal("1000")
        else:
            raise MassConversionError(f"Unknown unit: {self.unit}")
    
    def __add__(self, other: "Mass") -> "Mass":
        """Add two masses (converts to pounds)."""
        total_pounds = self.to_pounds() + other.to_pounds()
        return Mass(value=total_pounds, unit=MassUnit.POUNDS)
    
    def __mul__(self, scalar: Union[int, float, Decimal]) -> "Mass":
        """Multiply mass by scalar."""
        if isinstance(scalar, (int, float)):
            scalar = Decimal(str(scalar))
        return Mass(value=self.value * scalar, unit=self.unit)
    
    def __str__(self) -> str:
        return f"{self.value} {self.unit.value}"


@dataclass(frozen=True)
class Dimensions:
    """3D dimensions value object."""
    
    length: Decimal
    width: Decimal 
    height: Decimal
    unit: str = "mm"  # Default to millimeters
    
    def volume(self) -> Decimal:
        """Calculate volume."""
        return self.length * self.width * self.height


@dataclass(frozen=True)
class MassProperties:
    """Mass properties for a part or assembly."""
    
    mass: Optional[Mass]
    volume: Optional[Decimal]
    density: Optional[Decimal]
    center_of_mass: Optional[tuple[Decimal, Decimal, Decimal]] = None
    
    def has_mass(self) -> bool:
        """Check if mass properties include mass data."""
        return self.mass is not None
    
    def mass_in_pounds(self) -> Optional[Decimal]:
        """Get mass in pounds."""
        return self.mass.to_pounds() if self.mass else None


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box."""
    
    min_x: Decimal
    max_x: Decimal
    min_y: Decimal 
    max_y: Decimal
    min_z: Decimal
    max_z: Decimal
    
    def dimensions(self) -> Dimensions:
        """Get dimensions from bounding box."""
        return Dimensions(
            length=self.max_x - self.min_x,
            width=self.max_y - self.min_y,
            height=self.max_z - self.min_z
        )