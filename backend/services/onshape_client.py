"""Shared Onshape API client for element pre-flight checks and BOM fetching."""

import logging
from typing import Dict, Any, Tuple
from backend.common import connect
from backend.common.backend_exceptions import ClientException, ServerException
from onshape_api.endpoints.assemblies import get_assembly_bom
from onshape_api.endpoints.documents import get_document_element
from onshape_api.paths.doc_path import ElementPath
from .onshape_ids import build_api_path, ERROR_TYPES, MODE_NAMES

logger = logging.getLogger(__name__)


def get_onshape_api():
    """Get authenticated Onshape API client using API keys for local testing.

    Returns:
        Authenticated Onshape API instance
    """
    from onshape_api import make_key_api
    return make_key_api(load_dotenv=True)


def preflight_element_check(
    api, document_id: str, wvm: str, wvmid: str, element_id: str, mode: str
) -> Dict[str, Any]:
    """Perform pre-flight check to verify element access and type.

    Args:
        api: Authenticated Onshape API instance
        document_id: Document ID
        wvm: Instance type (w/v)
        wvmid: Instance ID
        element_id: Element ID
        mode: Mode name for error responses

    Returns:
        Element data if access verified

    Raises:
        ClientException: If pre-flight check fails (400 with structured response)
    """
    try:
        # Build API path using shared helper
        api_path = build_api_path(document_id, wvm, wvmid, element_id)
        logger.info(f"Pre-flight check: {api_path}")

        # Create element path for API call
        element_path = ElementPath(
            document_id=document_id,
            instance_id=wvmid,
            instance_type=wvm,
            element_id=element_id,
        )

        # Call the same /elements/... endpoint used by Standard App
        element_data = get_document_element(api, element_path)

        if not element_data:
            # Element not found
            raise ClientException(
                _build_preflight_error_response(
                    "404 Not Found", document_id, wvm, wvmid, element_id, mode
                )
            )

        logger.info(
            f"Element access verified: {element_data.get('elementType', 'unknown')}"
        )
        return element_data

    except Exception as e:
        error_str = str(e).lower()

        if "not found" in error_str or "404" in error_str:
            reason = "404 Not Found"
        elif (
            "unauthorized" in error_str
            or "403" in error_str
            or "forbidden" in error_str
        ):
            reason = "403 Forbidden"
        else:
            reason = str(e)

        # Return structured 400 response with computed IDs
        raise ClientException(
            _build_preflight_error_response(
                reason, document_id, wvm, wvmid, element_id, mode
            )
        )


def fetch_bom_data(
    api,
    document_id: str,
    wvm: str,
    wvmid: str,
    element_id: str,
    original_instance_type: str = None,
) -> Dict[str, Any]:
    """Fetch BOM data from Onshape with retry logic for 403 errors.

    Args:
        api: Authenticated Onshape API instance
        document_id: Document ID
        wvm: Instance type (w/v)
        wvmid: Instance ID
        element_id: Element ID
        original_instance_type: Original instance type for retry logic

    Returns:
        BOM data from Onshape

    Raises:
        ServerException: If BOM fetch fails after retry
    """
    try:
        # Build API path using shared helper
        api_path = build_api_path(document_id, wvm, wvmid, element_id)
        logger.info(f"BOM API call: {api_path}")

        # Create element path for API call
        element_path = ElementPath(
            document_id=document_id,
            instance_id=wvmid,
            instance_type=wvm,
            element_id=element_id,
        )

        # Fetch BOM data
        bom_data = get_assembly_bom(api, element_path)
        logger.info(
            f"BOM API call successful: {len(bom_data.get('bomTable', {}).get('rows', []))} rows"
        )
        return bom_data

    except Exception as e:
        error_str = str(e).lower()

        # Retry rule: On 403 from BOM, re-check mapping and retry once
        if (
            "403" in error_str
            and original_instance_type
            and original_instance_type != wvm
        ):
            logger.info(
                f"Retrying BOM call with original instance type: {original_instance_type}"
            )

            try:
                # Retry with original instance type
                retry_path = build_api_path(
                    document_id, original_instance_type, wvmid, element_id
                )
                logger.info(f"Retry BOM call: {retry_path}")

                retry_element_path = ElementPath(
                    document_id=document_id,
                    instance_id=wvmid,
                    instance_type=original_instance_type,
                    element_id=element_id,
                )

                bom_data = get_assembly_bom(api, retry_element_path)
                logger.info("Retry BOM call successful")
                return bom_data

            except Exception as retry_error:
                logger.error(f"Retry BOM call failed: {str(retry_error)}")
                raise ServerException(
                    f"BOM fetch failed after retry: {str(retry_error)}"
                )

        # Log error details for debugging
        logger.error(f"BOM fetch error: {str(e)}")
        logger.error(f"Element path: {document_id}/{wvm}/{wvmid}/e/{element_id}")

        # Log token info without exposing sensitive data
        try:
            token_info = api.oauth.token
            if token_info:
                logger.error(f"Token audience: {token_info.get('audience', 'unknown')}")
                logger.error(f"Token scope: {token_info.get('scope', 'unknown')}")
                logger.error(f"Token tenant: {token_info.get('tenant', 'unknown')}")
        except Exception as token_log_error:
            logger.error(f"Could not log token info: {token_log_error}")

        raise ServerException(f"Failed to fetch BOM data: {str(e)}")


def _build_preflight_error_response(
    reason: str, document_id: str, wvm: str, wvmid: str, element_id: str, mode: str
) -> str:
    """Build structured error response for pre-flight failures.

    Args:
        reason: Error reason (e.g., "403 Forbidden", "404 Not Found")
        document_id: Document ID
        wvm: Instance type (w/v)
        wvmid: Instance ID
        element_id: Element ID
        mode: Mode name

    Returns:
        JSON string for error response
    """
    import json

    error_response = {
        "error": ERROR_TYPES["PRE_FLIGHT_FAILED"],
        "reason": reason,
        "ids": {
            "documentId": document_id,
            "wvm": wvm,
            "wvmid": wvmid,
            "elementId": element_id,
        },
        "mode": mode,
    }

    return json.dumps(error_response)
