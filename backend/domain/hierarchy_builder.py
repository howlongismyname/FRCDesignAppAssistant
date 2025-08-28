"""Hierarchy building and mass calculation business logic for BOM data."""

from typing import List, Dict, Any
from .models import BomPart
from .bom_analyzer import has_material


def build_hierarchy(processed_rows: List[Dict[str, Any]]) -> None:
    """Build parent-child relationships in the processed BOM data.
    
    Args:
        processed_rows: List of processed part info dictionaries
    """
    # Create mapping for quick lookups
    item_map = {part["item"]: part for part in processed_rows}
    
    # Build parent-child relationships based on indent levels
    for i, part in enumerate(processed_rows):
        current_level = part["indentLevel"]
        
        # Find parent (previous item with lower indent level)
        parent = None
        for j in range(i - 1, -1, -1):
            prev_part = processed_rows[j]
            if prev_part["indentLevel"] < current_level:
                parent = prev_part
                break
        
        if parent:
            part["parentId"] = parent["item"]
            parent["children"].append(part["item"])
            parent["hasChildren"] = True
            
            # Update parent to be marked as subassembly if it has children
            if not parent["isSubassembly"]:
                parent["isSubassembly"] = True


def calculate_hierarchical_masses(processed_rows: List[Dict[str, Any]]) -> None:
    """Calculate masses for subassemblies based on their components.
    
    Args:
        processed_rows: List of processed part info dictionaries with hierarchy
    """
    # Create mapping for quick lookups
    item_map = {part["item"]: part for part in processed_rows}
    
    # Process from deepest level up (bottom-up calculation)
    max_level = max((part["indentLevel"] for part in processed_rows), default=0)
    
    for level in range(max_level, -1, -1):
        for part in processed_rows:
            if part["indentLevel"] == level and part["isSubassembly"]:
                calculate_subassembly_mass(part, item_map)


def calculate_subassembly_mass(subassembly: Dict[str, Any], item_map: Dict[str, Dict[str, Any]]) -> None:
    """Calculate total mass for a subassembly from its children.
    
    Args:
        subassembly: Subassembly part info dictionary
        item_map: Dictionary mapping item IDs to part info
    """
    total_mass = 0.0
    has_missing_mass = False
    has_any_mass = False
    
    # Calculate mass from direct children
    for child_id in subassembly["children"]:
        if child_id in item_map:
            child = item_map[child_id]
            
            # Use calculated mass for child subassemblies, direct mass for parts
            child_mass = child.get("calculatedMass") or child.get("directMass")
            
            if child_mass is not None:
                total_mass += child_mass * child["quantity"]
                has_any_mass = True
            else:
                has_missing_mass = True
            
            # Propagate missing mass flag from children (only for weight/mass issues, not material)
            if child.get("hasChildrenMissingMass"):
                has_missing_mass = True
    
    # Set calculated mass for subassembly
    if has_any_mass:
        subassembly["calculatedMass"] = total_mass
        # Update the displayed mass_lb field to show calculated mass
        subassembly["mass_lb"] = total_mass
        subassembly["weight"] = total_mass
    
    # Update missing mass flags
    subassembly["hasChildrenMissingMass"] = has_missing_mass
    
    # If subassembly has no direct material but has calculated mass, it may still be missing material
    if not has_material(subassembly["material"]) and subassembly.get("calculatedMass"):
        subassembly["missingMaterial"] = True


def identify_top_level_parts(processed_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify top-level parts (indent level 0) from processed BOM data.
    
    Args:
        processed_rows: List of processed part info dictionaries
        
    Returns:
        List of top-level parts only
    """
    return [part for part in processed_rows if part.get("indentLevel", 0) == 0]


def get_part_children(part_id: str, item_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all direct children of a part.
    
    Args:
        part_id: ID of the parent part
        item_map: Dictionary mapping item IDs to part info
        
    Returns:
        List of direct child parts
    """
    if part_id not in item_map:
        return []
    
    part = item_map[part_id]
    children = []
    
    for child_id in part.get("children", []):
        if child_id in item_map:
            children.append(item_map[child_id])
    
    return children


def get_part_descendants(part_id: str, item_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all descendants (children, grandchildren, etc.) of a part.
    
    Args:
        part_id: ID of the parent part
        item_map: Dictionary mapping item IDs to part info
        
    Returns:
        List of all descendant parts
    """
    descendants = []
    direct_children = get_part_children(part_id, item_map)
    
    for child in direct_children:
        descendants.append(child)
        # Recursively get descendants of this child
        child_descendants = get_part_descendants(child["item"], item_map)
        descendants.extend(child_descendants)
    
    return descendants


def calculate_part_depth(part_id: str, item_map: Dict[str, Dict[str, Any]]) -> int:
    """Calculate the maximum depth of a part's hierarchy tree.
    
    Args:
        part_id: ID of the part to calculate depth for
        item_map: Dictionary mapping item IDs to part info
        
    Returns:
        Maximum depth of the hierarchy tree
    """
    if part_id not in item_map:
        return 0
    
    part = item_map[part_id]
    
    if not part.get("children"):
        return 1
    
    max_child_depth = 0
    for child_id in part["children"]:
        child_depth = calculate_part_depth(child_id, item_map)
        max_child_depth = max(max_child_depth, child_depth)
    
    return 1 + max_child_depth


def build_hierarchy_tree(processed_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a complete hierarchy tree structure from processed BOM data.
    
    Args:
        processed_rows: List of processed part info dictionaries
        
    Returns:
        Dictionary representing the complete hierarchy tree
    """
    # First build the basic hierarchy relationships
    build_hierarchy(processed_rows)
    
    # Create item map for efficient lookups
    item_map = {part["item"]: part for part in processed_rows}
    
    # Calculate masses for subassemblies
    calculate_hierarchical_masses(processed_rows)
    
    # Identify top-level parts (roots of the tree)
    top_level_parts = identify_top_level_parts(processed_rows)
    
    # Build the tree structure
    hierarchy_tree = {
        "roots": [part["item"] for part in top_level_parts],
        "item_map": item_map,
        "total_parts": len(processed_rows),
        "top_level_count": len(top_level_parts),
        "max_depth": max([calculate_part_depth(part["item"], item_map) for part in top_level_parts]) if top_level_parts else 0
    }
    
    return hierarchy_tree


def validate_hierarchy_consistency(processed_rows: List[Dict[str, Any]]) -> List[str]:
    """Validate hierarchy consistency and return any issues found.
    
    Args:
        processed_rows: List of processed part info dictionaries
        
    Returns:
        List of error messages describing any consistency issues
    """
    errors = []
    item_map = {part["item"]: part for part in processed_rows}
    
    for part in processed_rows:
        part_id = part["item"]
        
        # Check parent-child consistency
        if part.get("parentId"):
            parent_id = part["parentId"]
            if parent_id not in item_map:
                errors.append(f"Part {part_id} references non-existent parent {parent_id}")
            else:
                parent = item_map[parent_id]
                if part_id not in parent.get("children", []):
                    errors.append(f"Part {part_id} claims parent {parent_id}, but parent doesn't list it as child")
        
        # Check children consistency
        for child_id in part.get("children", []):
            if child_id not in item_map:
                errors.append(f"Part {part_id} references non-existent child {child_id}")
            else:
                child = item_map[child_id]
                if child.get("parentId") != part_id:
                    errors.append(f"Part {part_id} lists {child_id} as child, but child doesn't reference it as parent")
        
        # Check indent level consistency
        if part.get("parentId"):
            parent = item_map[part["parentId"]]
            if part["indentLevel"] <= parent["indentLevel"]:
                errors.append(f"Part {part_id} has invalid indent level relative to parent {part['parentId']}")
    
    return errors