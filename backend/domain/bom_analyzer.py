"""BOM data analysis and processing business logic."""

from typing import Dict, Any, List, Optional, Tuple
from .models import BomPart


def has_material(material: Any) -> bool:
    """Check if a part has material assigned.

    Args:
        material: Material data from BOM

    Returns:
        True if material is present, False otherwise
    """
    if not material:
        return False

    if isinstance(material, str):
        return bool(material.strip())
    elif isinstance(material, dict):
        return bool(material.get("displayName") or material.get("id"))

    return False


def detect_bom_format(bom_data: dict) -> Tuple[List[dict], List[dict]]:
    """Detect BOM data format and extract headers and rows.
    
    Args:
        bom_data: Raw BOM data from Onshape
        
    Returns:
        Tuple of (headers, rows)
    """
    # Handle None or empty dict
    if not bom_data:
        return [], []
    
    # Handle both formats: direct format (headers/rows at root) and wrapped format (bomTable wrapper)
    if "bomTable" in bom_data:
        # Legacy format with bomTable wrapper
        bom_table = bom_data["bomTable"]
        if not bom_table or bom_table is None:
            return [], []
        headers = bom_table.get("headers", [])
        rows = bom_table.get("rows", [])
    else:
        # Direct format (current Onshape API v12)
        headers = bom_data.get("headers", [])
        rows = bom_data.get("rows", [])
    
    return headers, rows


def build_header_index(headers: List[dict]) -> Dict[str, int]:
    """Build header index for easier access to column data.
    
    Args:
        headers: List of header dictionaries with 'id' fields
        
    Returns:
        Dictionary mapping header IDs to column indices
    """
    header_index = {}
    for i, header in enumerate(headers):
        if "id" in header:
            header_index[header["id"]] = i
    return header_index


def extract_part_data_from_row(row: dict, row_index: int, document_id: str = None) -> Dict[str, Any]:
    """Extract and normalize part data from a BOM row.
    
    Args:
        row: Raw BOM row data
        row_index: Index of the row (for fallback IDs)
        document_id: Document ID for current document detection
        
    Returns:
        Dictionary with normalized part data
    """
    # Extract values using headerIdToValue format
    header_values = row.get("headerIdToValue", {})
    item_source = row.get("itemSource", {})
    
    # Check for hierarchy indicators in the raw row data
    indent_level = row.get("indentLevel", 0)
    parent_id = row.get("parentId") or row.get("parent")
    item_path = row.get("path", [])
    is_assembly = row.get("isAssembly", False)
    
    # Alternative hierarchy detection from item path or name formatting
    if not indent_level and item_path:
        indent_level = len(item_path) - 1
    elif not indent_level and header_values.get("5ace8269c046ad612c65a0ba"):
        # Detect hierarchy level from item number using dot notation depth
        item_num = str(header_values.get("5ace8269c046ad612c65a0ba", ""))
        if item_num and item_num != "--" and not item_num.startswith("--"):
            indent_level = item_num.count('.') if '.' in item_num else 0

    # Extract the key values - handle both new and legacy formats
    if header_values:
        # New API format with headerIdToValue
        part_name = header_values.get("57f3fb8efa3416c06701d60d", "")
        weight_str = header_values.get("57f3fb8efa3416c06701d626", "")
        quantity_raw = header_values.get("5ace84d3c046ad611c65a0dd", 1)
        material_data = header_values.get("57f3fb8efa3416c06701d615", "")
        item_id = str(header_values.get("5ace8269c046ad612c65a0ba", row_index))
    else:
        # Legacy format with direct row values
        part_name = row.get("name", "")
        weight_str = row.get("mass", "")
        quantity_raw = row.get("quantity", 1)
        material_data = row.get("material", "")
        item_id = str(row.get("item", row_index))

    # Safely convert quantity to float
    try:
        quantity = float(quantity_raw) if quantity_raw is not None else 1.0
    except (ValueError, TypeError):
        quantity = 1.0

    return {
        "item_id": item_id,
        "part_name": part_name if part_name else f"Part {row_index + 1}",
        "weight_str": weight_str,
        "quantity": quantity,
        "material_data": material_data,
        "indent_level": indent_level,
        "parent_id": parent_id,
        "item_path": item_path,
        "is_assembly": is_assembly,
        "header_values": header_values,
        "item_source": item_source,
        "document_id": document_id,
        "row_index": row_index
    }


def detect_hierarchy_level_from_item_number(item_num: str) -> int:
    """Detect hierarchy level from item number using dot notation.
    
    Args:
        item_num: Item number like "1", "1.2", "1.2.3"
        
    Returns:
        Hierarchy depth level (0-based)
    """
    if not item_num or item_num == "--" or item_num.startswith("--"):
        return 0
    
    return item_num.count('.') if '.' in item_num else 0


def detect_subassembly_status(
    current_item_num: str, 
    all_rows: List[dict], 
    current_row_index: int,
    has_children_explicit: bool = False
) -> Tuple[bool, bool]:
    """Detect if an item is a subassembly and has children.
    
    Args:
        current_item_num: Current item number
        all_rows: All BOM rows for child detection
        current_row_index: Index of current row
        has_children_explicit: Explicit hasChildren property from BOM data
        
    Returns:
        Tuple of (is_subassembly, has_children)
    """
    # Use explicit hasChildren as primary determinant
    if has_children_explicit:
        return True, True
    
    # Fallback: If no explicit hasChildren property, use item numbering logic
    if not current_item_num:
        return False, False
    
    # Look through all remaining rows to find potential children
    for check_index in range(current_row_index + 1, len(all_rows)):
        check_row = all_rows[check_index]
        check_header_values = check_row.get("headerIdToValue", {})
        check_item_num = str(check_header_values.get("5ace8269c046ad612c65a0ba", "")) if check_header_values else str(check_row.get("item", ""))
        
        # If this item number starts with current item number + ".", it's a child
        if current_item_num and check_item_num.startswith(current_item_num + "."):
            # Ensure it's a direct child, not a grandchild
            child_parts = check_item_num.split('.')
            current_parts = current_item_num.split('.')
            if len(child_parts) == len(current_parts) + 1:
                return True, True
    
    return False, False


def determine_current_document_status(item_source: dict, row: dict, document_id: str) -> bool:
    """Determine if a part is from the current document.
    
    Args:
        item_source: Item source data from BOM row
        row: Full BOM row data
        document_id: Current document ID
        
    Returns:
        True if part is from current document
    """
    if item_source and item_source.get("documentId"):
        return item_source.get("documentId") == document_id
    elif row.get("document", {}).get("documentId"):
        return row.get("document", {}).get("documentId") == document_id
    
    return False


def build_document_info(item_source: dict, row: dict) -> Dict[str, Any]:
    """Build document information dictionary from BOM row data.
    
    Args:
        item_source: Item source data from BOM row
        row: Full BOM row data
        
    Returns:
        Dictionary with document information
    """
    return {
        "documentId": (
            item_source.get("documentId") if item_source 
            else row.get("document", {}).get("documentId")
        ),
        "workspaceId": (
            item_source.get("wvmId")
            if item_source and item_source.get("wvmType") == "w"
            else row.get("document", {}).get("workspaceId")
        ),
        "versionId": (
            item_source.get("wvmId")
            if item_source and item_source.get("wvmType") == "v"
            else row.get("document", {}).get("versionId")
        ),
        "microversionId": (
            item_source.get("wvmId")
            if item_source and item_source.get("wvmType") == "m"
            else row.get("document", {}).get("microversionId")
        ),
        "wvmType": (
            item_source.get("wvmType") if item_source
            else row.get("document", {}).get("wvmType")
        ),
        "elementId": (
            item_source.get("elementId") if item_source 
            else row.get("document", {}).get("elementId")
        ),
        "partId": (
            item_source.get("partId") if item_source 
            else row.get("document", {}).get("partId")
        )
    }


def find_missing_material_parts(parts: List[BomPart]) -> List[BomPart]:
    """Find parts that are missing material information.
    
    Args:
        parts: List of BOM parts to analyze
        
    Returns:
        List of parts missing material information
    """
    missing_material_parts = []
    
    for part in parts:
        if not part.has_material_info():
            missing_material_parts.append(part)
    
    return missing_material_parts


def validate_bom_data_structure(bom_data: dict) -> bool:
    """Validate that BOM data has the expected structure.
    
    Args:
        bom_data: Raw BOM data to validate
        
    Returns:
        True if structure is valid, False otherwise
    """
    if not bom_data or not isinstance(bom_data, dict):
        return False
    
    # Check for either direct format or bomTable format
    if "bomTable" in bom_data:
        bom_table = bom_data["bomTable"]
        return (
            bom_table is not None and
            isinstance(bom_table.get("headers", []), list) and
            isinstance(bom_table.get("rows", []), list)
        )
    else:
        return (
            isinstance(bom_data.get("headers", []), list) and
            isinstance(bom_data.get("rows", []), list)
        )