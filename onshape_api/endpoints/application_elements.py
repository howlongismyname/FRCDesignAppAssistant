"""Onshape Application Elements API endpoints.

These endpoints allow creation and management of application elements
for structured storage within Onshape documents.

Based on official Onshape AppElement API specification.
"""

from typing import Any, Dict, Optional, List
from onshape_api.api.api_base import Api
from onshape_api.paths.api_path import api_path
from onshape_api.paths.doc_path import ElementPath, InstancePath


def create_application_element(
    api: Api, 
    instance_path: InstancePath,
    name: str,
    format_id: str = "application/json",
    description: str = "",
    json_tree: Optional[str] = None,
    location: Optional[Dict[str, Any]] = None,
    subelements: Optional[List[Dict[str, Any]]] = None,
    create_default_subelements: bool = True
) -> Dict[str, Any]:
    """Create a new application element in the document workspace.
    
    Based on: POST /api/v12/appelements/d/:did/w/:wid
    
    Args:
        api: Authenticated Onshape API instance
        instance_path: Path to the document workspace
        name: Name for the application element
        format_id: MIME type format (default: application/json)
        description: Description of the application element
        json_tree: JSON tree data as string (optional)
        location: Location info with elementId and position (optional)
        subelements: Initial sub-element contents (optional)
        create_default_subelements: Whether to create default subelements for FRC app
        
    Returns:
        Response with application element information including element ID
    """
    body = {
        "description": description,
        "formatId": format_id,
        "name": name
    }
    
    if json_tree:
        body["jsonTree"] = json_tree
    if location:
        body["location"] = location
    
    # Create default subelements for FRC Design App if requested
    if create_default_subelements and not subelements:
        subelements = [
            {
                "baseContent": "",
                "delta": "{}",
                "subelementId": "bomData"
            },
            {
                "baseContent": "",
                "delta": "{}",
                "subelementId": "metadata"
            }
        ]
    
    if subelements:
        body["subelements"] = subelements
    
    # Use workspace-level path for creation: /appelements/d/{did}/w/{wid}
    return api.post(
        api_path("appelements", instance_path, InstancePath),
        body=body
    )


def list_document_elements(
    api: Api,
    instance_path: InstancePath,
    with_thumbnails: bool = False,
    with_zip_contents: bool = False
) -> List[Dict[str, Any]]:
    """List all elements in a document workspace.
    
    Based on: GET /documents/d/:did/w/:wid/elements
    
    Args:
        api: Authenticated Onshape API instance
        instance_path: Path to the document workspace
        with_thumbnails: Include thumbnail data
        with_zip_contents: Include zip file contents
        
    Returns:
        List of all elements in the document
    """
    query_params = {
        "withThumbnails": str(with_thumbnails).lower(),
        "withZipContents": str(with_zip_contents).lower()
    }
    
    return api.get(
        api_path("documents", instance_path, InstancePath, "elements"),
        query=query_params
    )


def delete_application_element(
    api: Api,
    element_path: ElementPath
) -> Dict[str, Any]:
    """Delete an application element.
    
    Based on: DELETE /appelements/d/:did/w/:wid/e/:eid
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element to delete
        
    Returns:
        Response confirming deletion
    """
    return api.delete(
        api_path("appelements", element_path, ElementPath)
    )


def get_application_element_content(
    api: Api,
    element_path: ElementPath,
    transaction_id: Optional[str] = None,
    change_id: Optional[str] = None,
    content_format: str = "json"
) -> Dict[str, Any]:
    """Get the sub-element content of an application element.
    
    Based on: GET /appelements/d/:did/w/:wid/e/:eid/content/json
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element
        transaction_id: Optional transaction ID for specific version
        change_id: Optional change ID for specific version
        content_format: Content format (default: "json")
        
    Returns:
        Sub-element content of the application element
    """
    query_params = {}
    if transaction_id:
        query_params["transactionId"] = transaction_id
    if change_id:
        query_params["changeId"] = change_id
    
    # Only pass query if we have parameters
    if query_params:
        return api.get(
            api_path("appelements", element_path, ElementPath, f"content/{content_format}"),
            query=query_params
        )
    else:
        return api.get(
            api_path("appelements", element_path, ElementPath, f"content/{content_format}")
        )


def update_application_element_content(
    api: Api,
    element_path: ElementPath,
    changes: List[Dict[str, Any]],
    description: str = "Update from FRC Design App",
    transaction_id: Optional[str] = None,
    parent_change_id: Optional[str] = None,
    json_patch: Optional[str] = None,
    json_tree_edit: Optional[Dict[str, Any]] = None,
    property_updates: Optional[List[Dict[str, Any]]] = None,
    return_error: bool = True,
    return_json_difference_format: str = "default"
) -> Dict[str, Any]:
    """Update the content of an application element.
    
    Based on: POST /appelements/d/:did/w/:wid/e/:eid/content
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element
        changes: List of changes to apply to the element
        description: Description of the update
        transaction_id: Optional transaction ID for atomic updates
        parent_change_id: Previous change ID for conflict resolution
        json_patch: Optional JSON patch string
        json_tree_edit: Optional JSON tree edit object
        property_updates: Optional property updates
        return_error: Whether to return errors in response
        return_json_difference_format: Format for JSON differences
        
    Returns:
        Response with updated element information
    """
    # Build request body exactly matching curl example format
    body = {
        "changes": changes,
        "description": description,
        "returnError": return_error,
        "returnJsonDifferenceFormat": return_json_difference_format
    }
    
    # Add optional fields only if provided
    if json_patch:
        body["jsonPatch"] = json_patch
    if json_tree_edit is not None:
        body["jsonTreeEdit"] = json_tree_edit
    if transaction_id:
        body["transactionId"] = transaction_id
    if parent_change_id:
        body["parentChangeId"] = parent_change_id
    if property_updates:
        body["propertyUpdates"] = property_updates
    
    return api.post(
        api_path("appelements", element_path, ElementPath, "content"),
        body=body
    )


def create_subelement_change(
    subelement_id: str,
    content: Any,
    base_content: str = ""
) -> Dict[str, Any]:
    """Helper function to create a properly formatted subelement change.
    
    Args:
        subelement_id: ID of the subelement to change
        content: Content to store (will be JSON serialized)
        base_content: Base content for change calculation (usually empty string)
        
    Returns:
        Properly formatted change object for AppElement API matching curl example
    """
    import json
    
    # Convert content to JSON string (delta must be a string according to API)
    if isinstance(content, (dict, list)):
        delta_content = json.dumps(content)
    else:
        delta_content = str(content)
    
    change = {
        "baseContent": base_content,
        "delta": delta_content,
        "subelementId": subelement_id
    }
    
    return change


def store_structured_data(
    api: Api,
    element_path: ElementPath,
    data: Dict[str, Any],
    subelement_id: str = "data",
    description: str = "Store structured data",
    ensure_subelement_exists: bool = True
) -> Dict[str, Any]:
    """Convenience function to store structured data in an application element.
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element
        data: Data to store
        subelement_id: ID of the subelement to store data in
        description: Description of the update
        ensure_subelement_exists: Whether to handle subelement creation if needed
        
    Returns:
        Response with updated element information
    """
    if ensure_subelement_exists:
        return store_structured_data_safe(api, element_path, data, subelement_id, description)
    else:
        changes = [create_subelement_change(subelement_id, data)]
        return update_application_element_content(
            api, element_path, changes, description
        )


def store_structured_data_safe(
    api: Api,
    element_path: ElementPath,
    data: Dict[str, Any],
    subelement_id: str = "bomData",
    description: str = "Store structured data"
) -> Dict[str, Any]:
    """Safely store structured data, handling subelement creation if needed.
    
    This function tries to update the subelement, and if it doesn't exist,
    it will try to create it first by using an empty base content.
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element
        data: Data to store
        subelement_id: ID of the subelement to store data in
        description: Description of the update
        
    Returns:
        Response with updated element information
    """
    try:
        # First attempt: try normal update (subelement exists)
        changes = [create_subelement_change(subelement_id, data)]
        return update_application_element_content(
            api, element_path, changes, description
        )
    except Exception as e:
        error_message = str(e).lower()
        if "does not exist" in error_message or "subelement" in error_message:
            # Second attempt: try with empty base content (creates subelement)
            import json
            changes = [create_subelement_change(subelement_id, data, base_content="")]
            return update_application_element_content(
                api, element_path, changes, description + " (creating subelement)"
            )
        else:
            # Re-raise if it's a different error
            raise e


def get_subelement_content(
    api: Api,
    element_path: ElementPath,
    subelement_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get specific subelement content from an application element.
    
    Based on: GET /appelements/d/:did/w/:wid/e/:eid/content/subelements
    
    Args:
        api: Authenticated Onshape API instance
        element_path: Path to the application element
        subelement_ids: Optional list of specific subelement IDs to retrieve
        
    Returns:
        Subelement content
    """
    query_params = {}
    if subelement_ids:
        query_params["subelementIds"] = ",".join(subelement_ids)
    
    return api.get(
        api_path("appelements", element_path, ElementPath, "content/subelements"),
        query=query_params if query_params else None
    )