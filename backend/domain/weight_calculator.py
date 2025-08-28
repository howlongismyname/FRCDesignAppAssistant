"""Weight calculation business logic for BOM data."""

from typing import Optional, List, Dict, Any
from .models import BomPart, WeightMetrics


def parse_mass(mass_str: str) -> Optional[float]:
    """Parse mass string and convert to pounds.

    Args:
        mass_str: Mass string like "1.5 lb", "2.3 kg", "500 g"

    Returns:
        Mass in pounds, or None if parsing fails
    """
    if not mass_str or mass_str == "N/A":
        return None

    try:
        # Split by space to separate number and unit
        parts = mass_str.strip().split()
        if len(parts) == 0:
            return None

        value = float(parts[0])
        unit = parts[1].lower() if len(parts) > 1 else "lb"

        # Convert to pounds
        if unit in ["kg", "kgs", "kilogram", "kilograms"]:
            return value * 2.20462
        elif unit in ["g", "gram", "grams"]:
            return value * 0.00220462
        elif unit in ["lb", "lbs", "pound", "pounds"]:
            return value
        else:
            # Default to pounds if unit is unrecognized
            return value

    except (ValueError, IndexError):
        return None


def calculate_total_weight(parts: List[BomPart]) -> WeightMetrics:
    """Calculate total weight from BOM parts.
    
    Args:
        parts: List of BOM parts to calculate weight for
        
    Returns:
        WeightMetrics with total weight and counting information
    """
    total_weight_lb = 0.0
    rows_counted = 0
    rows_skipped = 0
    
    # Determine if this is hierarchical data
    is_hierarchical = any(part.indent_level > 0 for part in parts)
    
    for part in parts:
        if part.quantity <= 0:
            rows_skipped += 1
            continue
            
        rows_counted += 1
        
        # Get effective mass (calculated for subassemblies, direct for parts)
        effective_mass = part.get_effective_mass()
        
        if effective_mass and part.quantity:
            # For hierarchical data, only count top-level items to avoid double counting
            # For flat data (legacy), count all items
            if not is_hierarchical or part.indent_level == 0:
                total_weight_lb += effective_mass * part.quantity
    
    return WeightMetrics(
        unit="lb",
        total_weight=round(total_weight_lb, 6),
        rows_counted=rows_counted,
        rows_skipped=rows_skipped
    )


def convert_mass_to_pounds(value: float, unit: str) -> float:
    """Convert mass value to pounds based on unit.
    
    Args:
        value: Numeric mass value
        unit: Unit string (kg, g, lb, etc.)
        
    Returns:
        Mass value converted to pounds
    """
    unit_lower = unit.lower()
    
    if unit_lower in ["kg", "kgs", "kilogram", "kilograms"]:
        return value * 2.20462
    elif unit_lower in ["g", "gram", "grams"]:
        return value * 0.00220462
    elif unit_lower in ["lb", "lbs", "pound", "pounds"]:
        return value
    else:
        # Default to pounds if unit is unrecognized
        return value


def extract_mass_from_string(mass_str: str) -> tuple[Optional[float], str]:
    """Extract numeric value and unit from mass string.
    
    Args:
        mass_str: Mass string like "1.5 lb", "2.3 kg"
        
    Returns:
        Tuple of (numeric_value, unit) or (None, "") if parsing fails
    """
    if not mass_str or mass_str == "N/A":
        return None, ""

    try:
        parts = mass_str.strip().split()
        if len(parts) == 0:
            return None, ""

        value = float(parts[0])
        unit = parts[1] if len(parts) > 1 else "lb"
        
        return value, unit

    except (ValueError, IndexError):
        return None, ""