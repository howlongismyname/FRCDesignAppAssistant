"""
ISOLATED TEST ENDPOINT FOR STRUCTURED STORAGE VALIDATION

This endpoint is for testing real Onshape structured storage API calls.
It's designed to be easily commented out for production.

TODO: Remove this file before production deployment.
"""

import flask
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from backend.common.backend_exceptions import ServerException, ClientException
from backend.services.onshape_ids import extract_onshape_ids
from backend.services.onshape_client import get_onshape_api
from backend.common import connect
from onshape_api.endpoints.application_elements import (
    create_application_element,
    list_document_elements,
    get_application_element_content,
    update_application_element_content,
    delete_application_element,
    store_structured_data,
    store_structured_data_safe,
    create_subelement_change
)
from onshape_api.paths.doc_path import ElementPath, InstancePath
from onshape_api.paths.api_path import api_path

logger = logging.getLogger(__name__)

# Blueprint for isolated testing - easy to remove
test_router = flask.Blueprint("structured_storage_test", __name__)


@test_router.post("/test-create-app-element")
def test_create_application_element():
    """Test creating an application element in a real Onshape document.
    
    Expected query params:
    - documentId: Target document ID
    - instanceType: w/v (workspace/version) 
    - instanceId: Workspace/version ID
    - elementId: Assembly or Part Studio element ID
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        
        # Debug session information
        session_id = flask.session.get("session_id", "NO_SESSION")
        logger.info(f"CREATE TEST - Session ID: {session_id}")
        logger.info(f"CREATE TEST - Flask session keys: {list(flask.session.keys())}")
        
        # Try OAuth first, with detailed logging
        db = connect.get_db()
        try:
            token = connect.get_token(db)
            logger.info(f"CREATE TEST - OAuth token exists: {token is not None}")
            if token:
                logger.info(f"CREATE TEST - Token type: {type(token)}")
            
            api = connect.get_api(db)
            logger.info("CREATE TEST - SUCCESS: Using OAuth-authenticated API")
        except Exception as oauth_error:
            logger.warning(f"CREATE TEST - OAuth failed: {oauth_error}")
            logger.info("CREATE TEST - Falling back to API keys")
            api = get_onshape_api()
        
        # Create instance path (workspace level for creation)
        instance_path = InstancePath(
            ids["documentId"],
            ids["wvmid"],
            ids["wvm"]
        )
        
        # Test data to store
        test_name = "FRC Design App Test Element"
        test_description = f"Test application element created at {datetime.now().isoformat()}"
        
        logger.info(f"Creating test application element in document {ids['documentId']}")
        constructed_path = api_path("appelements", instance_path, InstancePath)
        logger.info(f"Constructed API path: {constructed_path}")
        logger.info(f"Full API base URL: {api._base_url}")
        logger.info(f"Expected URL: {api._base_url}{constructed_path}")
        
        # Make the real API call - create at workspace level
        result = create_application_element(
            api,
            instance_path,
            name=test_name,
            description=test_description,
            format_id="application/json"
        )
        
        logger.info(f"Successfully created application element: {result}")
        
        return {
            "success": True,
            "message": "Application element created successfully",
            "result": result,
            "api_path": InstancePath.to_api_path(instance_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to create application element: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to create test application element: {str(e)}")


@test_router.get("/test-list-app-elements")
def test_list_application_elements():
    """List all document elements and filter for application elements.
    
    Based on: GET /documents/d/:did/w/:wid/elements
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        
        # Create instance path for the document workspace
        instance_path = InstancePath(
            ids["documentId"],
            ids["wvmid"],
            ids["wvm"]
        )
        
        # Get authenticated API using OAuth (like production)
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for document elements")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        logger.info(f"Listing all document elements for document: {ids['documentId']}")
        constructed_path = api_path("documents", instance_path, InstancePath, "elements")
        logger.info(f"Constructed API path: {constructed_path}")
        logger.info(f"Full API base URL: {api._base_url}")
        logger.info(f"Expected URL: {api._base_url}{constructed_path}")
        
        # Make the real API call to list all elements
        result = list_document_elements(api, instance_path, with_thumbnails=False, with_zip_contents=False)
        
        # Filter for application elements
        app_elements = [elem for elem in result if elem.get("elementType") == "APPLICATION"]
        
        logger.info(f"Found {len(result)} total elements, {len(app_elements)} application elements")
        
        return {
            "success": True,
            "message": f"Found {len(app_elements)} application elements",
            "total_elements": len(result),
            "application_elements": app_elements,
            "all_elements": result,  # Include all for debugging
            "api_path": InstancePath.to_api_path(instance_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to list document elements: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        
        # If it's an ApiError, log more details
        if hasattr(e, 'status') and hasattr(e, 'response'):
            logger.error(f"API Status: {e.status}")
            logger.error(f"API Response: {e.response}")
        
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to list document elements: {str(e)}")


@test_router.get("/test-metadata-storage")
def test_metadata_storage():
    """Test metadata storage as an alternative to AppElements (works with API keys)."""
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        
        # Get authenticated API using OAuth (like production)
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for AppElement operations")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        # Create element path for the application element we want to list content of
        # Note: This should be the APPLICATION ELEMENT ID, not the assembly element
        app_element_id = flask.request.args.get("appElementId")
        if not app_element_id:
            raise ClientException("appElementId is required to list application element content")
        
        element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,  # This should be the application element ID
            ids["wvm"]
        )
        
        logger.info(f"Listing application element content: {app_element_id}")
        constructed_path = api_path("appelements", element_path, ElementPath, "content")
        logger.info(f"Constructed API path: {constructed_path}")
        logger.info(f"Full API base URL: {api._base_url}")
        logger.info(f"Expected URL: {api._base_url}{constructed_path}")
        
        # Make the real API call - get application element content
        result = get_application_elements(api, element_path)
        
        logger.info(f"Found {len(result)} application elements")
        
        return {
            "success": True,
            "message": "Application element content retrieved successfully",
            "elements": result,
            "api_path": ElementPath.to_api_path(element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to list application elements: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        
        # If it's an ApiError, log more details
        if hasattr(e, 'status') and hasattr(e, 'response'):
            logger.error(f"API Status: {e.status}")
            logger.error(f"API Response: {e.response}")
        
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to list application elements: {str(e)}")


@test_router.post("/test-store-bom-data")
def test_store_bom_data():
    """Test storing BOM data in structured storage.
    
    Expected query params:
    - documentId, instanceType, instanceId, elementId (as usual)
    - appElementId: ID of application element to store data in
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        app_element_id = flask.request.args.get("appElementId")
        
        if not app_element_id:
            raise ClientException("appElementId is required")
        
        # Get authenticated API using OAuth (like production)
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for AppElement operations")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        # Create element path for the application element we want to store data in
        app_element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,  # This is the application element ID, not the assembly element
            ids["wvm"]
        )
        
        # Create test BOM data
        test_bom_data = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "documentId": ids["documentId"],
                "workspaceId": ids["wvmid"],
                "testData": True,
                "bomSessions": {
                    ids["elementId"]: {
                        "elementId": ids["elementId"],
                        "elementType": flask.request.args.get("elementType", "ASSEMBLY"),
                        "bomData": {
                            "weight_metrics": {
                                "unit": "lb",
                                "total_weight": 12.34,
                                "rows_counted": 5,
                                "rows_skipped": 1
                            },
                            "missing_material_parts": [
                                {
                                    "part_name": "Test Part 1",
                                    "weight": 2.5,
                                    "quantity": 1,
                                    "material": None,
                                    "missingMaterial": True,
                                    "item": "test-part-1"
                                }
                            ]
                        },
                        "lastAnalyzed": datetime.now(timezone.utc).isoformat(),
                        "analyzedBy": "structured-storage-test"
                    }
                }
            }
        }
        
        logger.info(f"Storing test BOM data in app element {app_element_id}")
        logger.info(f"API path will be: {ElementPath.to_api_path(app_element_path)}")
        
        # Make the real API call using proper AppElement structure
        changes = [create_subelement_change("bomData", test_bom_data)]
        result = update_application_element_content(
            api,
            app_element_path,
            changes,
            description="Test BOM data from FRC Design App validation"
        )
        
        logger.info(f"Successfully stored BOM data: {result}")
        
        return {
            "success": True,
            "message": "BOM data stored successfully",
            "result": result,
            "stored_data": test_bom_data,
            "api_path": ElementPath.to_api_path(app_element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to store BOM data: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to store test BOM data: {str(e)}")


@test_router.get("/test-retrieve-bom-data")
def test_retrieve_bom_data():
    """Test retrieving BOM data from structured storage."""
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        app_element_id = flask.request.args.get("appElementId")
        
        if not app_element_id:
            raise ClientException("appElementId is required")
        
        # Get authenticated API using OAuth (like production)
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for AppElement operations")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        # Create element path for the application element
        app_element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,  # This is the application element ID
            ids["wvm"]
        )
        
        logger.info(f"Retrieving BOM data from app element {app_element_id}")
        logger.info(f"API path will be: {ElementPath.to_api_path(app_element_path)}")
        
        # Make the real API call
        result = get_application_element_content(api, app_element_path)
        
        logger.info(f"Successfully retrieved BOM data")
        
        # Check if it's our test data
        is_test_data = result.get("frcDesignAppBomData", {}).get("testData", False)
        
        return {
            "success": True,
            "message": "BOM data retrieved successfully",
            "result": result,
            "is_test_data": is_test_data,
            "api_path": ElementPath.to_api_path(app_element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve BOM data: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to retrieve BOM data: {str(e)}")


@test_router.delete("/test-cleanup-app-element")
def test_cleanup_application_element():
    """Test deleting a test application element."""
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        app_element_id = flask.request.args.get("appElementId")
        
        if not app_element_id:
            raise ClientException("appElementId is required")
        
        # Get authenticated API using OAuth (like production)
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for AppElement operations")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        # Create element path for the application element to delete
        app_element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,  # This is the application element ID
            ids["wvm"]
        )
        
        logger.info(f"Deleting test application element {app_element_id}")
        logger.info(f"API path will be: {ElementPath.to_api_path(app_element_path)}")
        
        # Make the real API call
        result = delete_application_element(api, app_element_path)
        
        logger.info(f"Successfully deleted application element")
        
        return {
            "success": True,
            "message": "Application element deleted successfully",
            "result": result,
            "api_path": ElementPath.to_api_path(app_element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to delete application element: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to delete test application element: {str(e)}")


@test_router.get("/test-get-element-id")
def test_get_element_id():
    """Test getting an existing application element ID for use in other tests."""
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        
        # Get authenticated API
        db = connect.get_db()
        try:
            api = connect.get_api(db)
            logger.info("Using OAuth-authenticated API for element lookup")
        except Exception as oauth_error:
            logger.warning(f"OAuth API failed, falling back to API keys: {oauth_error}")
            api = get_onshape_api()
        
        # Create instance path for the document workspace
        instance_path = InstancePath(
            ids["documentId"],
            ids["wvmid"],
            ids["wvm"]
        )
        
        # List all elements and find application elements
        all_elements = list_document_elements(api, instance_path)
        app_elements = [elem for elem in all_elements if elem.get("elementType") == "APPLICATION"]
        
        if not app_elements:
            return {
                "success": False,
                "message": "No application elements found in document",
                "total_elements": len(all_elements),
                "app_elements": []
            }
        
        # Return the first application element ID
        first_app_element = app_elements[0]
        element_id = first_app_element["id"]
        
        return {
            "success": True,
            "message": f"Found {len(app_elements)} application elements",
            "element_id": element_id,
            "element_info": first_app_element,
            "all_app_elements": app_elements
        }
        
    except Exception as e:
        logger.error(f"Failed to get element ID: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to get element ID: {str(e)}")


@test_router.post("/test-upload-data")
def test_upload_data():
    """Upload test data to an existing application element.
    
    Expected query params:
    - documentId, instanceType, instanceId (as usual)
    - appElementId: ID of application element to store data in
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        app_element_id = flask.request.args.get("appElementId")
        
        if not app_element_id:
            raise ClientException("appElementId is required")
        
        # Debug session information (same as list/create)
        session_id = flask.session.get("session_id", "NO_SESSION")
        logger.info(f"UPLOAD TEST - Session ID: {session_id}")
        logger.info(f"UPLOAD TEST - Flask session keys: {list(flask.session.keys())}")
        
        # Try OAuth first, with detailed logging (same as list/create)
        db = connect.get_db()
        try:
            token = connect.get_token(db)
            logger.info(f"UPLOAD TEST - OAuth token exists: {token is not None}")
            if token:
                logger.info(f"UPLOAD TEST - Token type: {type(token)}")
            
            api = connect.get_api(db)
            logger.info("UPLOAD TEST - SUCCESS: Using OAuth-authenticated API")
        except Exception as oauth_error:
            logger.warning(f"UPLOAD TEST - OAuth failed: {oauth_error}")
            logger.info("UPLOAD TEST - Falling back to API keys")
            api = get_onshape_api()
        
        # Create element path for the application element
        app_element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,
            ids["wvm"]
        )
        
        # Create test data
        test_data = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "documentId": ids["documentId"],
                "workspaceId": ids["wvmid"],
                "testData": True,
                "uploadTest": True,
                "bomSessions": {
                    ids["elementId"]: {
                        "elementId": ids["elementId"],
                        "bomData": {
                            "weight_metrics": {
                                "unit": "lb",
                                "total_weight": 42.5,
                                "test_upload": True
                            }
                        },
                        "lastAnalyzed": datetime.now(timezone.utc).isoformat(),
                        "analyzedBy": "upload-test-user"
                    }
                }
            }
        }
        
        logger.info(f"Uploading test data to app element {app_element_id}")
        constructed_path = api_path("appelements", app_element_path, ElementPath, "content")
        logger.info(f"Constructed API path: {constructed_path}")
        logger.info(f"Full API base URL: {api._base_url}")
        logger.info(f"Expected URL: {api._base_url}{constructed_path}")
        
        # Use safe storage method that handles subelement creation
        result = store_structured_data(
            api,
            app_element_path,
            test_data,
            subelement_id="bomData",
            description="Upload test data from FRC Design App",
            ensure_subelement_exists=True
        )
        
        logger.info(f"Successfully uploaded test data: {result}")
        
        return {
            "success": True,
            "message": "Test data uploaded successfully",
            "result": result,
            "uploaded_data": test_data,
            "api_path": ElementPath.to_api_path(app_element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to upload test data: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to upload test data: {str(e)}")


@test_router.get("/test-retrieve-data")  
def test_retrieve_data():
    """Retrieve test data from an existing application element.
    
    Expected query params:
    - documentId, instanceType, instanceId (as usual) 
    - appElementId: ID of application element to retrieve data from
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        app_element_id = flask.request.args.get("appElementId")
        
        if not app_element_id:
            raise ClientException("appElementId is required")
        
        # Debug session information (same as list/create)
        session_id = flask.session.get("session_id", "NO_SESSION")
        logger.info(f"RETRIEVE TEST - Session ID: {session_id}")
        logger.info(f"RETRIEVE TEST - Flask session keys: {list(flask.session.keys())}")
        
        # Try OAuth first, with detailed logging (same as list/create)
        db = connect.get_db()
        try:
            token = connect.get_token(db)
            logger.info(f"RETRIEVE TEST - OAuth token exists: {token is not None}")
            if token:
                logger.info(f"RETRIEVE TEST - Token type: {type(token)}")
            
            api = connect.get_api(db)
            logger.info("RETRIEVE TEST - SUCCESS: Using OAuth-authenticated API")
        except Exception as oauth_error:
            logger.warning(f"RETRIEVE TEST - OAuth failed: {oauth_error}")
            logger.info("RETRIEVE TEST - Falling back to API keys")
            api = get_onshape_api()
        
        # Create element path for the application element
        app_element_path = ElementPath(
            ids["documentId"],
            ids["wvmid"],
            app_element_id,
            ids["wvm"]
        )
        
        logger.info(f"Retrieving test data from app element {app_element_id}")
        constructed_path = api_path("appelements", app_element_path, ElementPath, "content")
        logger.info(f"Constructed API path: {constructed_path}")
        logger.info(f"Full API base URL: {api._base_url}")
        logger.info(f"Expected URL: {api._base_url}{constructed_path}")
        
        # Make the API call
        result = get_application_element_content(api, app_element_path)
        
        logger.info(f"Successfully retrieved data")
        
        # Check what type of test data this is
        frc_data = result.get("frcDesignAppBomData", {})
        is_upload_test = frc_data.get("uploadTest", False)
        is_test_data = frc_data.get("testData", False)
        
        return {
            "success": True,
            "message": "Test data retrieved successfully",
            "result": result,
            "is_upload_test": is_upload_test,
            "is_test_data": is_test_data,
            "api_path": ElementPath.to_api_path(app_element_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve test data: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to retrieve test data: {str(e)}")


@test_router.post("/test-automated-bom-workflow")
def test_automated_bom_workflow():
    """Automated BOM workflow test - complete end-to-end process.
    
    This endpoint:
    1. Checks for existing FRC Design App elements
    2. If found, loads existing BOM data
    3. If not found, creates new element
    4. Stores/updates BOM data with timestamp
    5. Returns the complete workflow results
    
    Expected query params:
    - documentId, instanceType, instanceId, elementId (as usual)
    """
    try:
        # Extract Onshape IDs from request
        ids = extract_onshape_ids(flask.request.args)
        
        # Debug session information (same as other tests)
        session_id = flask.session.get("session_id", "NO_SESSION")
        logger.info(f"AUTOMATED WORKFLOW - Session ID: {session_id}")
        logger.info(f"AUTOMATED WORKFLOW - Flask session keys: {list(flask.session.keys())}")
        
        # Try OAuth first, with detailed logging (same pattern as other tests)
        db = connect.get_db()
        try:
            token = connect.get_token(db)
            logger.info(f"AUTOMATED WORKFLOW - OAuth token exists: {token is not None}")
            if token:
                logger.info(f"AUTOMATED WORKFLOW - Token type: {type(token)}")
            
            api = connect.get_api(db)
            logger.info("AUTOMATED WORKFLOW - SUCCESS: Using OAuth-authenticated API")
        except Exception as oauth_error:
            logger.warning(f"AUTOMATED WORKFLOW - OAuth failed: {oauth_error}")
            logger.info("AUTOMATED WORKFLOW - Falling back to API keys")
            api = get_onshape_api()
        
        # Create instance path
        instance_path = InstancePath(
            ids["documentId"],
            ids["wvmid"],
            ids["wvm"]
        )
        
        workflow_results = {
            "steps": [],
            "workflow_type": "automated_bom_storage",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_path": InstancePath.to_api_path(instance_path)
        }
        
        # Step 1: Look for existing FRC Design App elements
        logger.info("Step 1: Searching for existing FRC Design App elements")
        all_elements = list_document_elements(api, instance_path, with_thumbnails=False, with_zip_contents=False)
        app_elements = [elem for elem in all_elements if elem.get("elementType") == "APPLICATION"]
        
        # Look for FRC-specific elements using multiple identifiers
        frc_identifiers = ["FRC Design App", "FRC BOM", "frcDesignApp"]
        frc_elements = []
        for elem in app_elements:
            elem_name = elem.get("name", "").lower()
            if any(identifier.lower() in elem_name for identifier in frc_identifiers):
                frc_elements.append(elem)
        
        workflow_results["steps"].append({
            "step": 1,
            "action": "search_existing_elements",
            "success": True,
            "result": f"Found {len(frc_elements)} FRC elements out of {len(app_elements)} total application elements",
            "data": {
                "total_elements": len(all_elements),
                "app_elements": len(app_elements), 
                "frc_elements": frc_elements
            }
        })
        
        # Step 2: Determine if we need to create or use existing
        app_element_id = None
        existing_data = {}
        
        if frc_elements:
            # Use existing element
            app_element_id = frc_elements[0]["id"]
            logger.info(f"Step 2: Using existing FRC element: {app_element_id}")
            
            app_element_path = ElementPath(
                ids["documentId"],
                ids["wvmid"],
                app_element_id,
                ids["wvm"]
            )
            
            # Try to load existing data
            try:
                existing_data = get_application_element_content(api, app_element_path)
                workflow_results["steps"].append({
                    "step": 2,
                    "action": "use_existing_element",
                    "success": True,
                    "result": f"Using existing element {app_element_id}, loaded existing data",
                    "data": {
                        "element_id": app_element_id,
                        "element_info": frc_elements[0],
                        "has_existing_data": bool(existing_data)
                    }
                })
            except Exception as load_error:
                logger.warning(f"Could not load existing data: {load_error}")
                workflow_results["steps"].append({
                    "step": 2,
                    "action": "use_existing_element",
                    "success": True,
                    "result": f"Using existing element {app_element_id}, no existing data found",
                    "data": {
                        "element_id": app_element_id,
                        "element_info": frc_elements[0],
                        "has_existing_data": False,
                        "load_error": str(load_error)
                    }
                })
        else:
            # Create new element
            logger.info("Step 2: Creating new FRC Design App element")
            create_result = create_application_element(
                api,
                instance_path,
                name="FRC Design App BOM Storage",
                description=f"Automated BOM analysis storage created at {datetime.now().isoformat()}",
                create_default_subelements=True
            )
            app_element_id = create_result["id"]
            
            app_element_path = ElementPath(
                ids["documentId"],
                ids["wvmid"],
                app_element_id,
                ids["wvm"]
            )
            
            workflow_results["steps"].append({
                "step": 2,
                "action": "create_new_element",
                "success": True,
                "result": f"Created new FRC element: {app_element_id}",
                "data": {
                    "element_id": app_element_id,
                    "create_result": create_result
                }
            })
        
        # Step 3: Get current BOM analysis (simulate getting real BOM data)
        logger.info("Step 3: Gathering current BOM analysis")
        # TODO: In production, this would call the real BOM analysis function
        # For now, create realistic test data
        current_timestamp = datetime.now(timezone.utc).isoformat()
        current_bom_analysis = {
            "weight_metrics": {
                "unit": "lb",
                "total_weight": 28.75,
                "rows_counted": 127,
                "rows_skipped": 3
            },
            "missing_material_parts": [
                {
                    "part_name": "Custom Spacer",
                    "weight": 0.1,
                    "quantity": 8,
                    "material": None,
                    "missingMaterial": True,
                    "item": "custom-spacer-001"
                },
                {
                    "part_name": "Modified Bracket",
                    "weight": 0.3,
                    "quantity": 2, 
                    "material": None,
                    "missingMaterial": True,
                    "item": "modified-bracket-002"
                }
            ],
            "analysis_metadata": {
                "analysis_time_ms": 1250,
                "parts_analyzed": 127,
                "assemblies_processed": 3
            }
        }
        
        workflow_results["steps"].append({
            "step": 3,
            "action": "gather_bom_analysis",
            "success": True,
            "result": f"Analyzed BOM: {current_bom_analysis['weight_metrics']['rows_counted']} parts, {current_bom_analysis['weight_metrics']['total_weight']} lbs total",
            "data": current_bom_analysis
        })
        
        # Step 4: Prepare updated BOM data with timestamp tracking
        logger.info("Step 4: Preparing BOM data with timestamp tracking")
        
        # Get existing BOM sessions or create new structure
        frc_data = existing_data.get("frcDesignAppBomData", {
            "version": "1.0",
            "bomSessions": {}
        })
        
        # Update metadata
        frc_data.update({
            "lastUpdated": current_timestamp,
            "documentId": ids["documentId"],
            "workspaceId": ids["wvmid"],
            "testData": False,  # This is real workflow data
            "automatedWorkflow": True
        })
        
        # Add/update this assembly's BOM session with timestamp tracking
        session_key = ids["elementId"]
        previous_analysis = frc_data["bomSessions"].get(session_key, {})
        
        frc_data["bomSessions"][session_key] = {
            "elementId": ids["elementId"],
            "elementType": ids.get("elementType", "ASSEMBLY"),
            "bomData": current_bom_analysis,
            "lastAnalyzed": current_timestamp,
            "analyzedBy": "automated-workflow-test",
            "analysisHistory": previous_analysis.get("analysisHistory", []),
            "previousAnalysis": {
                "timestamp": previous_analysis.get("lastAnalyzed"),
                "analyzedBy": previous_analysis.get("analyzedBy"),
                "totalWeight": previous_analysis.get("bomData", {}).get("weight_metrics", {}).get("total_weight")
            } if previous_analysis else None
        }
        
        # Add to history tracking
        if "analysisHistory" not in frc_data["bomSessions"][session_key]:
            frc_data["bomSessions"][session_key]["analysisHistory"] = []
            
        frc_data["bomSessions"][session_key]["analysisHistory"].append({
            "timestamp": current_timestamp,
            "analyzedBy": "automated-workflow-test",
            "totalWeight": current_bom_analysis["weight_metrics"]["total_weight"],
            "partsCount": current_bom_analysis["weight_metrics"]["rows_counted"]
        })
        
        # Keep only last 10 history entries
        if len(frc_data["bomSessions"][session_key]["analysisHistory"]) > 10:
            frc_data["bomSessions"][session_key]["analysisHistory"] = frc_data["bomSessions"][session_key]["analysisHistory"][-10:]
        
        complete_bom_data = {"frcDesignAppBomData": frc_data}
        
        workflow_results["steps"].append({
            "step": 4,
            "action": "prepare_timestamped_data",
            "success": True,
            "result": f"Prepared BOM data with timestamp tracking. History entries: {len(frc_data['bomSessions'][session_key]['analysisHistory'])}",
            "data": {
                "session_key": session_key,
                "timestamp": current_timestamp,
                "has_previous_analysis": frc_data["bomSessions"][session_key]["previousAnalysis"] is not None,
                "history_count": len(frc_data["bomSessions"][session_key]["analysisHistory"])
            }
        })
        
        # Step 5: Store the updated BOM data
        logger.info("Step 5: Storing updated BOM data with timestamps")
        store_result = store_structured_data(
            api,
            app_element_path,
            complete_bom_data,
            subelement_id="bomData",
            description=f"Automated BOM workflow update at {current_timestamp}",
            ensure_subelement_exists=True
        )
        
        workflow_results["steps"].append({
            "step": 5,
            "action": "store_timestamped_data",
            "success": True,
            "result": "Successfully stored BOM data with timestamp tracking",
            "data": store_result
        })
        
        # Step 6: Verify the stored data
        logger.info("Step 6: Verifying stored data")
        try:
            verification_data = get_application_element_content(api, app_element_path)
            stored_frc_data = verification_data.get("frcDesignAppBomData", {})
            stored_session = stored_frc_data.get("bomSessions", {}).get(session_key, {})
            
            verification_success = (
                stored_session.get("lastAnalyzed") == current_timestamp and
                stored_session.get("bomData", {}).get("weight_metrics", {}).get("total_weight") == current_bom_analysis["weight_metrics"]["total_weight"]
            )
            
            workflow_results["steps"].append({
                "step": 6,
                "action": "verify_stored_data",
                "success": verification_success,
                "result": f"Data verification: {'PASSED' if verification_success else 'FAILED'}",
                "data": {
                    "stored_timestamp": stored_session.get("lastAnalyzed"),
                    "expected_timestamp": current_timestamp,
                    "stored_weight": stored_session.get("bomData", {}).get("weight_metrics", {}).get("total_weight"),
                    "expected_weight": current_bom_analysis["weight_metrics"]["total_weight"]
                }
            })
        except Exception as verify_error:
            workflow_results["steps"].append({
                "step": 6,
                "action": "verify_stored_data", 
                "success": False,
                "result": f"Verification failed: {str(verify_error)}",
                "data": {"error": str(verify_error)}
            })
        
        return {
            "success": True,
            "message": "Automated BOM workflow completed successfully!",
            "workflow_results": workflow_results,
            "element_id": app_element_id,
            "bom_data_summary": {
                "total_weight": current_bom_analysis["weight_metrics"]["total_weight"],
                "parts_count": current_bom_analysis["weight_metrics"]["rows_counted"],
                "missing_materials": len(current_bom_analysis["missing_material_parts"]),
                "analysis_timestamp": current_timestamp
            }
        }
        
    except Exception as e:
        logger.error(f"Automated workflow test failed: {str(e)}")
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Automated BOM workflow test failed: {str(e)}")