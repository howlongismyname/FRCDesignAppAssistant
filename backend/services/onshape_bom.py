"""Dedicated service for BOM data fetching and processing."""

import logging
from typing import Dict, Any, Optional
from .onshape_client import fetch_bom_data
from ..domain.weight_calculator import parse_mass
from ..domain.bom_analyzer import (
    has_material, detect_bom_format, extract_part_data_from_row,
    detect_subassembly_status, determine_current_document_status, build_document_info
)
from ..domain.hierarchy_builder import build_hierarchy, calculate_hierarchical_masses

logger = logging.getLogger(__name__)




def process_bom_data(bom_data: dict, document_id: str = None) -> Dict[str, Any]:
    """Process BOM data to extract weight and material information.

    Args:
        bom_data: Raw BOM data from Onshape

    Returns:
        Processed data with weight metrics and missing material report
    """
    # Detect BOM format and extract headers and rows
    headers, rows = detect_bom_format(bom_data)

    # If no rows, return empty result instead of raising
    if not rows:
        return {
            "weight_metrics": {
                "unit": "lb",
                "total_weight": 0.0,
                "rows_counted": 0,
                "rows_skipped": 0,
            },
            "missing_material_parts": [],
        }

    # Build header index for easier access
    header_index = {}
    for i, header in enumerate(headers):
        if "id" in header:
            header_index[header["id"]] = i

    # Process rows
    total_weight_lb = 0.0
    rows_counted = 0
    rows_skipped = 0
    missing_material_parts = []

    # First pass: collect all rows and analyze hierarchy
    processed_rows = []
    hierarchy_info = {}
    
    for row_index, row in enumerate(rows):
        try:
            # Extract values using headerIdToValue format
            header_values = row.get("headerIdToValue", {})
            item_source = row.get("itemSource", {})
            
            # Check for hierarchy indicators in the raw row data
            # Onshape may provide indentation level, path info, or parent-child relationships
            indent_level = row.get("indentLevel", 0)  # Common hierarchy indicator
            parent_id = row.get("parentId") or row.get("parent")  # Parent reference
            item_path = row.get("path", [])  # Path from root to this item
            is_assembly = row.get("isAssembly", False)  # Direct assembly flag
            
            # Alternative hierarchy detection from item path or name formatting
            if not indent_level and item_path:
                indent_level = len(item_path) - 1  # Calculate depth from path
            elif not indent_level and header_values.get("5ace8269c046ad612c65a0ba"):
                # Detect hierarchy level from item number using dot notation depth
                # Per Part ID nesting logic: numeric depth = hierarchy depth
                # Examples: "1" = level 0, "11.2" = level 1, "11.2.1" = level 2
                item_num = str(header_values.get("5ace8269c046ad612c65a0ba", ""))
                # Skip placeholder IDs like "--" which are not true BOM nodes
                if item_num and item_num != "--" and not item_num.startswith("--"):
                    indent_level = item_num.count('.') if '.' in item_num else 0

            # Extract the key values - handle both new and legacy formats
            if header_values:
                # New API format with headerIdToValue
                part_name = header_values.get("57f3fb8efa3416c06701d60d", "")  # Part name
                weight_str = header_values.get("57f3fb8efa3416c06701d626", "")  # Weight
                quantity_raw = header_values.get("5ace84d3c046ad611c65a0dd", 1)  # Quantity
                material_data = header_values.get("57f3fb8efa3416c06701d615", "")  # Material
            else:
                # Legacy format with direct row values
                part_name = row.get("name", "")
                weight_str = row.get("mass", "")
                quantity_raw = row.get("quantity", 1)
                material_data = row.get("material", "")

            # Safely convert quantity to float
            try:
                quantity = float(quantity_raw) if quantity_raw is not None else 1.0
            except (ValueError, TypeError):
                quantity = 1.0

            # Skip if quantity is 0
            if quantity == 0:
                rows_skipped += 1
                continue

            # Parse weight data - extract numeric value from strings like "0.114 lb"
            weight_lb = None
            if weight_str and isinstance(weight_str, str):
                weight_lb = parse_mass(weight_str)

            # Determine if this is a subassembly
            # A subassembly typically has children (next items have higher indent level)
            # or is explicitly marked as assembly, or lacks direct mass but has components
            if header_values:
                item_id = str(header_values.get("5ace8269c046ad612c65a0ba", row_index))
            else:
                item_id = str(row.get("item", row_index))
            
            # Primary subassembly detection: Use hasChildren property if provided by Onshape
            current_item_num = str(header_values.get("5ace8269c046ad612c65a0ba", "")) if header_values else str(row.get("item", ""))
            
            # Check for explicit hasChildren property from Onshape BOM data
            has_children_explicit = row.get("hasChildren", False)
            
            # Use explicit hasChildren as primary determinant according to Part ID nesting logic
            is_subassembly = has_children_explicit
            has_children = has_children_explicit
            
            # Fallback: If no explicit hasChildren property, use item numbering logic
            if not has_children_explicit and current_item_num:
                # Look through all remaining rows to find potential children
                for check_index in range(row_index + 1, len(rows)):
                    check_row = rows[check_index]
                    check_header_values = check_row.get("headerIdToValue", {})
                    check_item_num = str(check_header_values.get("5ace8269c046ad612c65a0ba", "")) if check_header_values else str(check_row.get("item", ""))
                    
                    # If this item number starts with current item number + ".", it's a child
                    # E.g., current="1.2", potential child="1.2.1" or "1.2.3"
                    if current_item_num and check_item_num.startswith(current_item_num + "."):
                        # Ensure it's a direct child, not a grandchild
                        # Direct child would have exactly one more level: "1.2" -> "1.2.1", not "1.2.1.1"
                        child_parts = check_item_num.split('.')
                        current_parts = current_item_num.split('.')
                        if len(child_parts) == len(current_parts) + 1:
                            is_subassembly = True
                            has_children = True
                            break
            
            # Per Part ID nesting logic: hasChildren property should be the decisive factor
            # No additional fallback logic - rely only on explicit hasChildren or actual child detection

            # Create enhanced part object with hierarchy information
            part_info = {
                "part_name": part_name if part_name else f"Part {row_index + 1}",
                "weight": weight_lb,
                "quantity": quantity,
                "material": material_data,
                # Additional metadata for UI
                "item": item_id,
                "name": part_name if part_name else f"Part {row_index + 1}",
                "mass_lb": weight_lb,
                "missingMaterial": not has_material(material_data),
                "document": {
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
                    ),
                },
                # Add flag to indicate if part is from current document or imported
                "isCurrentDocument": (
                    item_source.get("documentId") == document_id
                    if item_source and item_source.get("documentId")
                    else (row.get("document", {}).get("documentId") == document_id 
                          if row.get("document", {}).get("documentId") else False)
                ),
                # NEW: Hierarchy and subassembly information per Part ID nesting logic
                "isSubassembly": is_subassembly,
                "indentLevel": indent_level,
                "parentId": parent_id,
                "itemPath": item_path,
                "hasChildren": has_children,  # Primary determinant for assembly vs part
                "children": [],  # Will be populated in second pass
                "calculatedMass": None,  # Will be calculated for subassemblies
                "hasChildrenMissingMass": False,  # Will be calculated
                "directMass": weight_lb,  # Original individual mass
                "rowIndex": row_index,  # For tracking
            }

            # Store for hierarchy processing
            processed_rows.append(part_info)
            hierarchy_info[item_id] = part_info

        except Exception as e:
            logger.error(f"Error processing BOM row {row_index}: {str(e)}")
            logger.error(f"Row data: {row}")
            rows_skipped += 1
            continue
    
    # Second pass: Build parent-child relationships and calculate hierarchical masses
    build_hierarchy(processed_rows)
    calculate_hierarchical_masses(processed_rows)
    
    # Third pass: Calculate totals and build final results
    total_weight_lb = 0.0
    rows_counted = 0
    for part in processed_rows:
        if part["quantity"] > 0:
            rows_counted += 1
            # Use calculated mass for subassemblies, direct mass for individual parts
            effective_mass = part.get("calculatedMass") or part.get("directMass")
            if effective_mass and part["quantity"]:
                # For hierarchical data, only count top-level items to avoid double counting
                # For flat data (legacy), count all items
                is_hierarchical = any(p.get("indentLevel", 0) > 0 for p in processed_rows)
                if not is_hierarchical or part["indentLevel"] == 0:
                    total_weight_lb += effective_mass * part["quantity"]

    return {
        "weight_metrics": {
            "unit": "lb",
            "total_weight": round(total_weight_lb, 6),
            "rows_counted": rows_counted,
            "rows_skipped": rows_skipped,
        },
        "missing_material_parts": processed_rows,  # Now includes hierarchy info
    }




def fetch_and_process_bom(
    api,
    document_id: str,
    wvm: str,
    wvmid: str,
    element_id: str,
    original_instance_type: str = None,
) -> Dict[str, Any]:
    """Fetch BOM data from Onshape and process it.

    Args:
        api: Authenticated Onshape API instance
        document_id: Document ID
        wvm: Instance type (w/v)
        wvmid: Instance ID
        element_id: Element ID
        original_instance_type: Original instance type for retry logic

    Returns:
        Processed BOM data with weight metrics and missing material report
    """
    # Fetch raw BOM data
    bom_data = fetch_bom_data(
        api, document_id, wvm, wvmid, element_id, original_instance_type
    )

    # Log raw BOM data at DEBUG level for troubleshooting
    logger.debug(f"Raw BOM data received: {bom_data}")

    # Process the BOM data
    return process_bom_data(bom_data, document_id)
