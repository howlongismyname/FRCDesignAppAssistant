import flask
import json
from backend.common.backend_exceptions import ServerException, ClientException
from backend.services.onshape_ids import (
    extract_onshape_ids,
    MODE_NAMES,
    ERROR_TYPES,
)
from backend.services.onshape_client import (
    get_onshape_api,
)
from backend.services.onshape_bom import (
    fetch_and_process_bom,
    process_bom_data,
)
from backend.common.connect import get_session_id, get_db
from datetime import datetime, timezone
import time


router = flask.Blueprint("design_assistant", __name__)


@router.post("/ingest")
def ingest_bom():
    """Ingest BOM JSON data and store for analysis.

    Expected body: Raw BOM JSON from Onshape
    """
    try:
        bom_data = flask.request.get_json()
        if not bom_data:
            raise ClientException("No BOM data provided")

        # Process the BOM data
        processed_data = process_bom_data(bom_data)

        # Store in Firestore instead of Flask session
        db = get_db()
        session_id = get_session_id()

        # Extract document and element IDs from the request
        # This assumes the request includes these parameters
        document_id = flask.request.args.get("documentId")
        element_id = flask.request.args.get("elementId")

        if document_id and element_id:
            # Try to get workspace ID from request for part studio lookups
            instance_type = flask.request.args.get("instanceType", "w")
            workspace_id = (
                flask.request.args.get("instanceId") if instance_type == "w" else None
            )
            db.save_bom_session(
                session_id, processed_data, document_id, element_id, workspace_id
            )

        return {
            "success": True,
            "message": "BOM data ingested successfully",
            "summary": {
                "total_weight_lb": processed_data["weight_metrics"]["total_weight"],
                "parts_analyzed": processed_data["weight_metrics"]["rows_counted"],
                "missing_material_count": len(processed_data["missing_material_parts"]),
            },
        }

    except Exception as e:
        if isinstance(e, (ClientException, ServerException)):
            raise e
        raise ServerException(f"Failed to ingest BOM data: {str(e)}")


@router.get("/metrics/weight")
def get_weight_metrics():
    """Get weight metrics from ingested BOM data.

    Returns:
        Weight metrics including total weight, rows counted, and rows skipped
    """
    try:
        # Get document and element IDs from query parameters
        document_id = flask.request.args.get("documentId")
        element_id = flask.request.args.get("elementId")

        if not document_id or not element_id:
            raise ClientException("documentId and elementId are required")

        db = get_db()
        session_id = get_session_id()

        # Try to get cached data first
        bom_session = db.get_bom_session(session_id, document_id, element_id)
        if not bom_session:
            raise ClientException(
                "No BOM data available. Please ingest BOM data first."
            )

        return bom_session["bomData"]["weight_metrics"]
    except Exception as e:
        flask.current_app.logger.error(f"Error getting weight metrics: {str(e)}")
        if isinstance(e, ClientException):
            raise e
        raise ServerException(f"Failed to get weight metrics: {str(e)}")


@router.get("/reports/missing-material")
def get_missing_material_report():
    """Get report of parts missing material assignments.

    Returns:
        Array of parts missing material information
    """
    try:
        # Get document and element IDs from query parameters
        document_id = flask.request.args.get("documentId")
        element_id = flask.request.args.get("elementId")

        if not document_id or not element_id:
            raise ClientException("documentId and elementId are required")

        db = get_db()
        session_id = get_session_id()

        # Try to get cached data first
        bom_session = db.get_bom_session(session_id, document_id, element_id)
        if not bom_session:
            raise ClientException(
                "No BOM data available. Please ingest BOM data first."
            )

        return bom_session["bomData"]["missing_material_parts"]
    except Exception as e:
        flask.current_app.logger.error(
            f"Error getting missing material report: {str(e)}"
        )
        if isinstance(e, ClientException):
            raise e
        raise ServerException(f"Failed to get missing material report: {str(e)}")


@router.get("/bom")
def get_bom_data():
    """Get BOM data for the current assembly.

    Query parameters:
        - documentId: Document ID
        - instanceType: Instance type (w/v)
        - instanceId: Instance ID
        - elementId: Element ID
        - elementType: Element type (should be ASSEMBLY)
        - forceRefresh: Force refresh from Onshape API (optional)

    Returns:
        Raw BOM data from Onshape with processing details
    """
    try:
        # Extract and validate Onshape IDs using shared service
        ids = extract_onshape_ids(flask.request.args)
        element_type = flask.request.args.get("elementType", "ASSEMBLY")
        force_refresh = (
            flask.request.args.get("forceRefresh", "false").lower() == "true"
        )

        # Handle PARTSTUDIO by looking up cached assembly BOM data by workspace ID
        if element_type == "PARTSTUDIO":
            # For part studios, look up cached BOM data by workspace ID
            db = get_db()
            session_id = get_session_id()

            # Try to find cached assembly BOM data in the same workspace
            workspace_id = ids["wvmid"] if ids["wvm"] == "w" else None
            if workspace_id:
                cached_data = db.get_bom_session_by_workspace(
                    session_id, ids["documentId"], workspace_id
                )

                if cached_data:
                    # Return cached assembly data for part studio context
                    return {
                        "params": {
                            "documentId": ids["documentId"],
                            "instanceId": ids["wvmid"],
                            "instanceType": ids["wvm"],
                            "elementId": ids[
                                "elementId"
                            ],  # Keep original part studio element ID
                            "elementType": element_type,  # Keep as PARTSTUDIO
                        },
                        "weightMetrics": cached_data["bomData"]["weight_metrics"],
                        "missingMaterialParts": cached_data["bomData"][
                            "missing_material_parts"
                        ],
                        "massProperties": cached_data["bomData"].get("massProperties"),
                        "rawBomData": cached_data["bomData"].get("rawBomData"),
                        "cacheInfo": {
                            "isCached": True,
                            "lastUpdated": (
                                cached_data["lastUpdated"].isoformat()
                                if hasattr(cached_data["lastUpdated"], "isoformat")
                                else str(cached_data["lastUpdated"])
                            ),
                            "ageHours": (
                                (
                                    datetime.now(timezone.utc)
                                    - cached_data["lastUpdated"]
                                ).total_seconds()
                                / 3600
                                if hasattr(cached_data["lastUpdated"], "timestamp")
                                else None
                            ),
                        },
                        "isPartStudio": True,
                        "assemblyElementId": cached_data.get(
                            "elementId"
                        ),  # Show which assembly the data came from
                    }
                else:
                    # No cached assembly BOM data found for this workspace
                    error_response = {
                        "error": "NO_ASSEMBLY_BOM_CACHED",
                        "message": "No assembly BOM data found for this workspace. Please open and analyze an assembly in this document first.",
                        "documentId": ids["documentId"],
                        "workspaceId": workspace_id,
                        "elementId": ids["elementId"],
                        "elementType": element_type,
                    }
                    return flask.jsonify(error_response), 422
            else:
                # No workspace ID available
                error_response = {
                    "error": "NO_WORKSPACE_ID",
                    "message": "Part studio must be in a workspace for BOM lookup",
                    "documentId": ids["documentId"],
                    "elementId": ids["elementId"],
                    "elementType": element_type,
                }
                return flask.jsonify(error_response), 422

        # Get authenticated Onshape API for assemblies
        api = get_onshape_api()

        # Validate element type for Design Assistant (should be ASSEMBLY for actual processing)
        if element_type not in ["ASSEMBLY"]:
            # Return structured 422 response for non-assembly types (PARTSTUDIO is already handled above)
            error_response = {
                "error": ERROR_TYPES["INVALID_ELEMENT_TYPE"],
                "expected": "ASSEMBLY",
                "got": element_type,
                "ids": {
                    "documentId": ids["documentId"],
                    "elementId": ids["elementId"],
                },
                "mode": MODE_NAMES["DESIGN_ASSISTANT"],
            }
            return flask.jsonify(error_response), 422

        # Check Firestore cache first (unless force refresh is requested)
        db = get_db()
        session_id = get_session_id()
        cached_data = None

        if not force_refresh:
            cached_data = db.get_bom_session(
                session_id, ids["documentId"], ids["elementId"]
            )
            if cached_data:
                # Return cached data with cache info
                return {
                    "params": {
                        "documentId": ids["documentId"],
                        "instanceId": ids["wvmid"],
                        "instanceType": ids["wvm"],
                        "elementId": ids["elementId"],
                        "elementType": element_type,
                    },
                    "weightMetrics": cached_data["bomData"]["weight_metrics"],
                    "missingMaterialParts": cached_data["bomData"][
                        "missing_material_parts"
                    ],
                    "massProperties": cached_data["bomData"].get("massProperties"),
                    "rawBomData": cached_data["bomData"].get("rawBomData"),
                    "cacheInfo": {
                        "isCached": True,
                        "lastUpdated": (
                            cached_data["lastUpdated"].isoformat()
                            if hasattr(cached_data["lastUpdated"], "isoformat")
                            else str(cached_data["lastUpdated"])
                        ),
                        "ageHours": (
                            (
                                datetime.now(timezone.utc) - cached_data["lastUpdated"]
                            ).total_seconds()
                            / 3600
                            if hasattr(cached_data["lastUpdated"], "timestamp")
                            else None
                        ),
                    },
                }
        else:
            # Rate limiting for force refresh - check if user can refresh again
            last_refresh_key = (
                f"last_refresh_{session_id}_{ids['documentId']}_{ids['elementId']}"
            )
            last_refresh_time = flask.session.get(last_refresh_key, 0)
            current_time = time.time()

            if current_time - last_refresh_time < 30:  # 30 second cooldown
                remaining_time = 30 - int(current_time - last_refresh_time)
                return {
                    "error": "rate_limited",
                    "message": f"Please wait {remaining_time} seconds before refreshing again",
                    "remainingSeconds": remaining_time,
                }, 429

            # Update last refresh time
            flask.session[last_refresh_key] = current_time

        # Fetch fresh data from Onshape API
        try:
            processed_data = fetch_and_process_bom(
                api,
                ids["documentId"],
                ids["wvm"],
                ids["wvmid"],
                ids["elementId"],
                ids["instanceType"],  # Original instance type for retry logic
            )
        except ServerException as e:
            # If BOM fetch fails, check for specific error types
            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                return {"error": "unauthorized", "signInUrl": "/sign-in"}, 401
            elif "403" in error_str:
                # Return detailed 403 error for debugging
                return {
                    "error": "api_access_denied",
                    "message": "Access denied to BOM API endpoint",
                    "details": {
                        "documentId": ids["documentId"],
                        "workspaceId": ids["wvmid"],
                        "elementId": ids["elementId"],
                        "elementPath": f"{ids['documentId']}/{ids['wvm']}/{ids['wvmid']}/e/{ids['elementId']}",
                        "apiError": str(e),
                        "suggestion": "Check if the document/workspace/element exists and you have BOM access permissions"
                    }
                }, 403
            else:
                raise e

        # Fetch raw BOM data for debugging
        from backend.services.onshape_client import fetch_bom_data

        raw_bom_data = fetch_bom_data(
            api,
            ids["documentId"],
            ids["wvm"],
            ids["wvmid"],
            ids["elementId"],
            ids["instanceType"],
        )

        # Store processed data in Firestore
        bom_data = {
            "weight_metrics": processed_data["weight_metrics"],
            "missing_material_parts": processed_data["missing_material_parts"],
            "rawBomData": {
                "formatVersion": raw_bom_data.get("formatVersion"),
                "headers": raw_bom_data.get("headers", [])[
                    :3
                ],  # First 3 headers for debugging
                "firstRow": (
                    raw_bom_data.get("rows", [{}])[0]
                    if raw_bom_data.get("rows")
                    else {}
                ),  # First row for debugging
                "totalRows": len(raw_bom_data.get("rows", [])),
            },
        }

        # Save to Firestore with workspace ID for part studio lookups
        workspace_id = ids.get("wvmid") if ids.get("wvm") == "w" else None
        db.save_bom_session(
            session_id, bom_data, ids["documentId"], ids["elementId"], workspace_id
        )

        # Return both raw and processed data plus mass properties
        return {
            "params": {
                "documentId": ids["documentId"],
                "instanceId": ids["wvmid"],
                "instanceType": ids["wvm"],
                "elementId": ids["elementId"],
                "elementType": element_type,
            },
            "weightMetrics": processed_data["weight_metrics"],
            "missingMaterialParts": processed_data["missing_material_parts"],
            "massProperties": None,  # Mass properties are no longer fetched
            "rawBomData": bom_data["rawBomData"],
            "cacheInfo": {
                "isCached": False,
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "ageHours": 0,
            },
        }

    except Exception as e:
        if isinstance(e, ClientException):
            raise e
        elif isinstance(e, ServerException):
            # Check for 403 errors in ServerException
            error_str = str(e).lower()
            if "403" in error_str:
                # Safely get ids if available
                try:
                    doc_id = ids.get("documentId", "unknown") if 'ids' in locals() else "unknown"
                    workspace_id = ids.get("wvmid", "unknown") if 'ids' in locals() else "unknown"
                    element_id = ids.get("elementId", "unknown") if 'ids' in locals() else "unknown"
                    wvm = ids.get("wvm", "unknown") if 'ids' in locals() else "unknown"
                    element_path = f"{doc_id}/{wvm}/{workspace_id}/e/{element_id}" if 'ids' in locals() else "unknown"
                except:
                    doc_id = workspace_id = element_id = element_path = "unknown"
                    
                return {
                    "error": "api_access_denied", 
                    "message": "Access denied to BOM API endpoint",
                    "details": {
                        "documentId": doc_id,
                        "workspaceId": workspace_id, 
                        "elementId": element_id,
                        "elementPath": element_path,
                        "apiError": str(e),
                        "suggestion": "Check if the document/workspace/element exists and you have BOM access permissions"
                    }
                }, 403
            else:
                raise e
        # Log unexpected errors for debugging
        flask.current_app.logger.error(f"Unexpected error in get_bom_data: {str(e)}")
        flask.current_app.logger.error(f"Error type: {type(e).__name__}")
        raise ServerException(f"Failed to get BOM data: {str(e)}")


@router.get("/refresh-cooldown")
def get_refresh_cooldown():
    """Get the remaining cooldown time for force refresh."""
    try:
        ids = extract_onshape_ids(flask.request.args)
        session_id = get_session_id()

        last_refresh_key = (
            f"last_refresh_{session_id}_{ids['documentId']}_{ids['elementId']}"
        )
        last_refresh_time = flask.session.get(last_refresh_key, 0)
        current_time = time.time()

        if current_time - last_refresh_time < 30:
            remaining_time = 30 - int(current_time - last_refresh_time)
            return {"canRefresh": False, "remainingSeconds": remaining_time}
        else:
            return {"canRefresh": True, "remainingSeconds": 0}

    except Exception as e:
        flask.current_app.logger.error(f"Error checking refresh cooldown: {str(e)}")
        return {"error": "Failed to check cooldown"}, 500


@router.post("/cleanup-sessions")
def cleanup_old_sessions():
    """Clean up old BOM sessions to prevent database bloat.

    This endpoint can be called periodically (e.g., daily) to clean up old data.
    """
    try:
        db = get_db()
        max_age_hours = flask.request.args.get("maxAgeHours", "24")

        try:
            max_age_hours = int(max_age_hours)
        except ValueError:
            max_age_hours = 24

        db.cleanup_old_bom_sessions(max_age_hours)

        return {
            "success": True,
            "message": f"Cleaned up BOM sessions older than {max_age_hours} hours",
        }

    except Exception as e:
        flask.current_app.logger.error(f"Error cleaning up sessions: {str(e)}")
        raise ServerException(f"Failed to cleanup sessions: {str(e)}")


@router.get("/available-documents")
def get_available_documents():
    """Get available documents for design assistant analysis.

    This endpoint is called by the frontend to get document information
    and trigger BOM analysis.
    """
    try:
        # Extract and validate Onshape IDs using shared service
        ids = extract_onshape_ids(flask.request.args)
        element_type = flask.request.args.get("elementType", "ASSEMBLY")

        # Handle PARTSTUDIO - for get_available_documents, we allow PARTSTUDIO context
        # but return structured information about workspace matching
        if element_type == "PARTSTUDIO":
            # For part studios in get_available_documents, we don't need to do complex lookups
            # Just validate that workspace ID exists and return basic document info
            workspace_id = ids["wvmid"] if ids["wvm"] == "w" else None
            if not workspace_id:
                error_response = {
                    "error": "NO_WORKSPACE_ID",
                    "message": "Part studio must be in a workspace",
                    "documentId": ids["documentId"],
                    "elementId": ids["elementId"],
                    "elementType": element_type,
                }
                return flask.jsonify(error_response), 422

        # Validate element type for Design Assistant
        if element_type not in ["ASSEMBLY", "PARTSTUDIO"]:
            # Return structured 422 response for unsupported element types
            error_response = {
                "error": ERROR_TYPES["INVALID_ELEMENT_TYPE"],
                "expected": "ASSEMBLY or PARTSTUDIO",
                "got": element_type,
                "ids": {
                    "documentId": ids["documentId"],
                    "elementId": ids["elementId"],
                },
                "mode": MODE_NAMES["DESIGN_ASSISTANT"],
            }
            return flask.jsonify(error_response), 422

        # Log the mode and computed IDs for debugging
        flask.current_app.logger.info(
            f"Design Assistant mode - elementType: {element_type}"
        )
        flask.current_app.logger.info(
            f"Computed IDs: {{did: {ids['documentId']}, wvm: {ids['wvm']}, wvmid: {ids['wvmid']}, eid: {ids['elementId']}}}"
        )

        # Handle part studios differently - look for cached assembly data
        if element_type == "PARTSTUDIO":
            # For part studios, look up cached assembly BOM data by workspace ID
            db = get_db()
            session_id = get_session_id()

            workspace_id = ids["wvmid"] if ids["wvm"] == "w" else None
            if workspace_id:
                cached_data = db.get_bom_session_by_workspace(
                    session_id, ids["documentId"], workspace_id
                )

                if cached_data:
                    # Use cached assembly data for part studio
                    processed_data = cached_data["bomData"]
                else:
                    # No cached assembly BOM data found
                    return {
                        "error": "NO_ASSEMBLY_BOM_CACHED",
                        "message": "No assembly BOM data found for this workspace. Please open and analyze an assembly in this document first.",
                        "params": {
                            "documentId": ids["documentId"],
                            "instanceId": ids["wvmid"],
                            "instanceType": ids["wvm"],
                            "elementId": ids["elementId"],
                            "elementType": element_type,
                        },
                    }, 422
            else:
                # No workspace ID
                return {
                    "error": "NO_WORKSPACE_ID",
                    "message": "Part studio must be in a workspace for BOM lookup",
                    "params": {
                        "documentId": ids["documentId"],
                        "instanceId": ids["wvmid"],
                        "instanceType": ids["wvm"],
                        "elementId": ids["elementId"],
                        "elementType": element_type,
                    },
                }, 422
        else:
            # For assemblies, fetch from Onshape API as usual
            api = get_onshape_api()

            # Fetch and process BOM data using dedicated service
            try:
                processed_data = fetch_and_process_bom(
                    api,
                    ids["documentId"],
                    ids["wvm"],
                    ids["wvmid"],
                    ids["elementId"],
                    ids["instanceType"],  # Original instance type for retry logic
                )
            except ServerException as e:
                # If BOM fetch fails, check for specific error types
                error_str = str(e).lower()
                if "unauthorized" in error_str or "401" in error_str:
                    return {"error": "unauthorized", "signInUrl": "/sign-in"}, 401
                elif "403" in error_str:
                    # Return detailed 403 error for debugging
                    return {
                        "error": "api_access_denied",
                        "message": "Access denied to BOM API endpoint",
                        "details": {
                            "documentId": ids["documentId"],
                            "workspaceId": ids["wvmid"],
                            "elementId": ids["elementId"],
                            "elementPath": f"{ids['documentId']}/{ids['wvm']}/{ids['wvmid']}/e/{ids['elementId']}",
                            "apiError": str(e),
                            "suggestion": "Check if the document/workspace/element exists and you have BOM access permissions"
                        }
                    }, 403
                else:
                    raise e

            # Store processed data in Firestore for assemblies
            db = get_db()
            session_id = get_session_id()
            workspace_id = ids["wvmid"] if ids["wvm"] == "w" else None
            db.save_bom_session(
                session_id,
                processed_data,
                ids["documentId"],
                ids["elementId"],
                workspace_id,
            )

        # Return data in format expected by frontend
        response_data = {
            "params": {
                "documentId": ids["documentId"],
                "instanceId": ids["wvmid"],
                "instanceType": ids["wvm"],
                "elementId": ids["elementId"],
                "elementType": element_type,
            },
            "summary": {
                "totalMass": processed_data["weight_metrics"]["total_weight"],
                "totalParts": processed_data["weight_metrics"]["rows_counted"],
                "missingMaterial": len(processed_data["missing_material_parts"]),
            },
            "documents": [
                {
                    "occurrenceId": part["item"],
                    "partId": part["document"]["partId"] or part["item"],
                    "missingMaterial": True,
                    "mass": part["mass_lb"],
                    "material": None,
                }
                for part in processed_data["missing_material_parts"]
            ],
        }
        return response_data

    except Exception as e:
        if isinstance(e, ClientException):
            raise e
        elif isinstance(e, ServerException):
            # Check for 403 errors in ServerException
            error_str = str(e).lower()
            if "403" in error_str:
                # Safely get ids if available
                try:
                    doc_id = ids.get("documentId", "unknown") if 'ids' in locals() else "unknown"
                    workspace_id = ids.get("wvmid", "unknown") if 'ids' in locals() else "unknown"
                    element_id = ids.get("elementId", "unknown") if 'ids' in locals() else "unknown"
                    wvm = ids.get("wvm", "unknown") if 'ids' in locals() else "unknown"
                    element_path = f"{doc_id}/{wvm}/{workspace_id}/e/{element_id}" if 'ids' in locals() else "unknown"
                except:
                    doc_id = workspace_id = element_id = element_path = "unknown"
                    
                return {
                    "error": "api_access_denied",
                    "message": "Access denied to BOM API endpoint", 
                    "details": {
                        "documentId": doc_id,
                        "workspaceId": workspace_id,
                        "elementId": element_id, 
                        "elementPath": element_path,
                        "apiError": str(e),
                        "suggestion": "Check if the document/workspace/element exists and you have BOM access permissions"
                    }
                }, 403
            else:
                raise e
        # Log unexpected errors for debugging
        flask.current_app.logger.error(
            f"Unexpected error in get_available_documents: {str(e)}"
        )
        flask.current_app.logger.error(f"Error type: {type(e).__name__}")
        raise ServerException(f"Failed to get available documents: {str(e)}")


@router.get("/thumbnails/d/<document_id>/<instance_type>/<instance_id>/e/<element_id>")
def get_thumbnail(
    document_id: str, instance_type: str, instance_id: str, element_id: str
):
    """Get thumbnail for a specific element.

    This endpoint provides thumbnails for parts in the design assistant.
    """
    try:
        # This would need to be implemented based on the thumbnail endpoint
        # For now, return a placeholder
        return flask.jsonify({"error": "Thumbnail endpoint not yet implemented"})

    except Exception:
        raise ServerException("Failed to get thumbnail")
