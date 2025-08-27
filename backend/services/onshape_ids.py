"""Shared Onshape ID extraction, validation, and normalization utilities."""

from typing import Dict, Any
from backend.common.backend_exceptions import ClientException


def normalize_instance_type(instance_type: str) -> str:
    """Normalize instance type to match Onshape API expectations.

    Args:
        instance_type: Instance type string (case-insensitive)

    Returns:
        Normalized instance type: 'w' for WORKSPACE, 'v' for VERSION
    """
    if not instance_type:
        return "w"  # Default to workspace

    normalized = instance_type.upper()
    if normalized == "WORKSPACE":
        return "w"
    elif normalized == "VERSION":
        return "v"
    elif normalized in ["W", "V"]:
        return normalized.lower()
    else:
        # Default to workspace for unknown types
        return "w"


def validate_element_type(element_type: str, required_type: str = "ASSEMBLY") -> None:
    """Validate that the element type matches the required type.

    Args:
        element_type: Element type string
        required_type: Required element type (default: ASSEMBLY)

    Raises:
        ClientException: If element type doesn't match required type
    """
    if not element_type or element_type.upper() != required_type.upper():
        raise ClientException(
            f"Element type validation failed. Expected: {required_type}, Got: {element_type}"
        )


def extract_onshape_ids(query_params: Dict[str, Any]) -> Dict[str, str]:
    """Extract and normalize Onshape IDs from query parameters.

    Args:
        query_params: Flask request query parameters

    Returns:
        Dictionary with normalized IDs: documentId, wvm, wvmid, elementId

    Raises:
        ClientException: If required parameters are missing
    """
    document_id = query_params.get("documentId")
    instance_type_raw = query_params.get("instanceType", "w")
    instance_id = query_params.get("instanceId")
    element_id = query_params.get("elementId")

    if not all([document_id, instance_id, element_id]):
        raise ClientException(
            "Missing required parameters: documentId, instanceId, elementId"
        )

    # Normalize instance type using the same logic as Standard App
    wvm = normalize_instance_type(instance_type_raw)

    return {
        "documentId": document_id,
        "wvm": wvm,
        "wvmid": instance_id,
        "elementId": element_id,
        "instanceType": instance_type_raw,  # Keep original for retry logic
    }


def build_api_path(did: str, wvm: str, wvmid: str, eid: str) -> str:
    """Build Onshape API path for element access.

    Args:
        did: Document ID
        wvm: Instance type (w/v)
        wvmid: Instance ID
        eid: Element ID

    Returns:
        API path string: /d/{did}/{wvm}/{wvmid}/e/{eid}
    """
    return f"/d/{did}/{wvm}/{wvmid}/e/{eid}"


# Constants for error responses
ERROR_TYPES = {
    "PRE_FLIGHT_FAILED": "PreFlightFailed",
    "INVALID_ELEMENT_TYPE": "InvalidElementType",
    "BOM_FETCH_FAILED": "BomFetchFailed",
}

MODE_NAMES = {
    "STANDARD": "Standard App",
    "DESIGN_ASSISTANT": "Design Assistant",
}
