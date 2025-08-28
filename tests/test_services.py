import pytest
import json
from unittest.mock import Mock, patch
from backend.services.onshape_ids import (
    normalize_instance_type,
    validate_element_type,
    extract_onshape_ids,
    build_api_path,
    ERROR_TYPES,
    MODE_NAMES,
)
from backend.services.onshape_client import (
    get_onshape_api,
    preflight_element_check,
    fetch_bom_data,
)


class TestOnshapeIdsService:
    """Test cases for Onshape IDs service."""

    def test_normalize_instance_type_workspace(self):
        """Test normalization of workspace instance types."""
        assert normalize_instance_type("WORKSPACE") == "w"
        assert normalize_instance_type("workspace") == "w"
        assert normalize_instance_type("Workspace") == "w"
        assert normalize_instance_type("w") == "w"
        assert normalize_instance_type("W") == "w"

    def test_normalize_instance_type_version(self):
        """Test normalization of version instance types."""
        assert normalize_instance_type("VERSION") == "v"
        assert normalize_instance_type("version") == "v"
        assert normalize_instance_type("Version") == "v"
        assert normalize_instance_type("v") == "v"
        assert normalize_instance_type("V") == "v"

    def test_normalize_instance_type_edge_cases(self):
        """Test normalization of edge cases."""
        assert normalize_instance_type("") == "w"  # Default to workspace
        assert normalize_instance_type(None) == "w"  # Default to workspace
        assert (
            normalize_instance_type("unknown") == "w"
        )  # Unknown defaults to workspace
        assert (
            normalize_instance_type("PARTSTUDIO") == "w"
        )  # Unrecognized defaults to workspace

    def test_validate_element_type_success(self):
        """Test successful element type validation."""
        # Valid assembly types
        validate_element_type("ASSEMBLY")
        validate_element_type("assembly")
        validate_element_type("Assembly")

    def test_validate_element_type_failure(self):
        """Test element type validation failures."""
        from backend.common.backend_exceptions import ClientException
        
        with pytest.raises(ClientException):
            validate_element_type("PARTSTUDIO")

        with pytest.raises(ClientException):
            validate_element_type("DRAWING")

        with pytest.raises(ClientException):
            validate_element_type("")

        with pytest.raises(ClientException):
            validate_element_type(None)

    def test_extract_onshape_ids_success(self):
        """Test successful extraction of Onshape IDs."""
        query_params = {
            "documentId": "doc123",
            "instanceType": "WORKSPACE",
            "instanceId": "ws456",
            "elementId": "elem789",
        }

        result = extract_onshape_ids(query_params)

        assert result["documentId"] == "doc123"
        assert result["wvm"] == "w"  # Normalized from WORKSPACE
        assert result["wvmid"] == "ws456"
        assert result["elementId"] == "elem789"
        assert result["instanceType"] == "WORKSPACE"  # Original preserved

    def test_extract_onshape_ids_missing_params(self):
        """Test extraction with missing required parameters."""
        from backend.common.backend_exceptions import ClientException
        
        query_params = {
            "documentId": "doc123",
            # Missing instanceId and elementId
        }

        with pytest.raises(ClientException):
            extract_onshape_ids(query_params)

    def test_extract_onshape_ids_defaults(self):
        """Test extraction with default values."""
        query_params = {
            "documentId": "doc123",
            "instanceId": "ws456",
            "elementId": "elem789",
            # instanceType defaults to "w"
        }

        result = extract_onshape_ids(query_params)

        assert result["wvm"] == "w"  # Default instance type
        assert result["instanceType"] == "w"

    def test_build_api_path(self):
        """Test API path construction."""
        path = build_api_path("doc123", "w", "ws456", "elem789")
        assert path == "/d/doc123/w/ws456/e/elem789"

        path = build_api_path("doc456", "v", "ver789", "elem012")
        assert path == "/d/doc456/v/ver789/e/elem012"

    def test_error_types_constants(self):
        """Test error type constants."""
        assert ERROR_TYPES["PRE_FLIGHT_FAILED"] == "PreFlightFailed"
        assert ERROR_TYPES["INVALID_ELEMENT_TYPE"] == "InvalidElementType"
        assert ERROR_TYPES["BOM_FETCH_FAILED"] == "BomFetchFailed"

    def test_mode_names_constants(self):
        """Test mode name constants."""
        assert MODE_NAMES["STANDARD"] == "Standard App"
        assert MODE_NAMES["DESIGN_ASSISTANT"] == "Design Assistant"


class TestOnshapeClientService:
    """Test cases for Onshape client service."""

    @patch("backend.services.onshape_client.connect")
    def test_get_onshape_api(self, mock_connect):
        """Test getting authenticated Onshape API client."""
        mock_db = Mock()
        mock_api = Mock()
        mock_connect.get_db.return_value = mock_db
        mock_connect.get_api.return_value = mock_api

        result = get_onshape_api()

        mock_connect.get_db.assert_called_once()
        mock_connect.get_api.assert_called_once_with(mock_db)
        assert result == mock_api

    @patch("backend.services.onshape_client.get_document_element")
    def test_preflight_element_check_success(self, mock_get_element):
        """Test successful pre-flight element check."""
        mock_api = Mock()
        mock_element_data = {"elementType": "ASSEMBLY", "name": "Test Assembly"}
        mock_get_element.return_value = mock_element_data

        result = preflight_element_check(
            mock_api, "doc123", "w", "ws456", "elem789", "Design Assistant"
        )

        assert result == mock_element_data
        mock_get_element.assert_called_once()

    @patch("backend.services.onshape_client.get_document_element")
    def test_preflight_element_check_404(self, mock_get_element):
        """Test pre-flight check with 404 error."""
        from backend.common.backend_exceptions import ClientException
        
        mock_api = Mock()
        mock_get_element.return_value = None  # Element not found

        with pytest.raises(ClientException):
            preflight_element_check(
                mock_api, "doc123", "w", "ws456", "elem789", "Design Assistant"
            )

    @patch("backend.services.onshape_client.get_document_element")
    def test_preflight_element_check_403(self, mock_get_element):
        """Test pre-flight check with 403 error."""
        from backend.common.backend_exceptions import ClientException
        
        mock_api = Mock()
        mock_get_element.side_effect = Exception("403 Forbidden")

        with pytest.raises(ClientException):
            preflight_element_check(
                mock_api, "doc123", "w", "ws456", "elem789", "Design Assistant"
            )

    @patch("backend.services.onshape_client.get_assembly_bom")
    def test_fetch_bom_data_success(self, mock_get_bom):
        """Test successful BOM data fetch."""
        mock_api = Mock()
        mock_bom_data = {"bomTable": {"rows": [{"item": "1", "name": "Part A"}]}}
        mock_get_bom.return_value = mock_bom_data

        result = fetch_bom_data(mock_api, "doc123", "w", "ws456", "elem789")

        assert result == mock_bom_data
        mock_get_bom.assert_called_once()

    @patch("backend.services.onshape_client.get_assembly_bom")
    def test_fetch_bom_data_retry_success(self, mock_get_bom):
        """Test BOM fetch with successful retry after 403."""
        mock_api = Mock()
        # First call fails with 403, second succeeds
        mock_get_bom.side_effect = [
            Exception("403 Forbidden"),
            {"bomTable": {"rows": [{"item": "1", "name": "Part A"}]}},
        ]

        result = fetch_bom_data(
            mock_api, "doc123", "w", "ws456", "elem789", "v"
        )

        # Should have been called twice (initial + retry)
        assert mock_get_bom.call_count == 2

    @patch("backend.services.onshape_client.get_assembly_bom")
    def test_fetch_bom_data_retry_failure(self, mock_get_bom):
        """Test BOM fetch with failed retry after 403."""
        mock_api = Mock()
        # Both calls fail
        mock_get_bom.side_effect = [
            Exception("403 Forbidden"),
            Exception("403 Forbidden"),
        ]

        from backend.common.backend_exceptions import ServerException
        
        with pytest.raises(ServerException):
            fetch_bom_data(mock_api, "doc123", "w", "ws456", "elem789", "v")


if __name__ == "__main__":
    pytest.main([__file__])
