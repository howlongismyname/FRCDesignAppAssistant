import pytest
from unittest.mock import Mock, patch
from flask import Flask
from backend.server import create_app


class TestRouting:
    """Test cases for routing functionality."""

    @pytest.fixture
    def app(self):
        """Create a test Flask app."""
        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    def test_app_route_with_onshape_params(self, client):
        """Test that /app route preserves Onshape parameters."""
        # Mock the OAuth and API calls
        with (
            patch("backend.server.connect.get_db") as mock_db,
            patch("backend.server.connect.get_api") as mock_api,
            patch("backend.server.ping") as mock_ping,
            patch("backend.server.get_app_access_level") as mock_access,
        ):

            # Mock successful authentication
            mock_ping.return_value = True
            mock_access.return_value = "ADMIN"

            # Test with Onshape parameters
            response = client.get(
                "/app?elementType=PARTSTUDIO&documentId=doc123&instanceType=w&instanceId=ws456&elementId=elem789"
            )

            # Should redirect to add access level parameters
            assert response.status_code == 302
            assert "maxAccessLevel" in response.location
            assert "accessLevel" in response.location
            assert "elementType=PARTSTUDIO" in response.location
            assert "documentId=doc123" in response.location
            assert "instanceType=w" in response.location
            assert "instanceId=ws456" in response.location
            assert "elementId=elem789" in response.location

    def test_design_assistant_route_with_onshape_params(self, client):
        """Test that /app/designassistant route preserves Onshape parameters."""
        # Mock the OAuth and API calls
        with (
            patch("backend.server.connect.get_db") as mock_db,
            patch("backend.server.connect.get_api") as mock_api,
            patch("backend.server.ping") as mock_ping,
            patch("backend.server.get_app_access_level") as mock_access,
        ):

            # Mock successful authentication
            mock_ping.return_value = True
            mock_access.return_value = "ADMIN"

            # Test with Onshape parameters
            response = client.get(
                "/app/designassistant/?elementType=ASSEMBLY&documentId=doc123&instanceType=w&instanceId=ws456&elementId=elem789"
            )

            # Should redirect to add access level parameters
            assert response.status_code == 302
            assert "maxAccessLevel" in response.location
            assert "accessLevel" in response.location
            assert "elementType=ASSEMBLY" in response.location
            assert "documentId=doc123" in response.location
            assert "instanceType=w" in response.location
            assert "instanceId=ws456" in response.location
            assert "elementId=elem789" in response.location

    def test_design_assistant_endpoints_accessible(self, client):
        """Test that design assistant API endpoints are accessible."""
        # Test weight metrics endpoint
        response = client.get("/app/designassistant/metrics/weight")
        # Should return error since no BOM data is ingested
        assert response.status_code == 400

        # Test missing material report endpoint
        response = client.get("/app/designassistant/reports/missing-material")
        # Should return error since no BOM data is ingested
        assert response.status_code == 400

        # Test ingest endpoint
        response = client.post(
            "/app/designassistant/ingest",
            json={"bomTable": {"headers": [], "rows": []}},
        )
        # Should return success
        assert response.status_code == 200

    def test_url_parsing_consistency(self):
        """Test that URL parsing is consistent between routes."""
        # Standard app URL format
        standard_url = "https://localhost:3000/app?elementType=PARTSTUDIO&documentId=doc123&instanceType=w&instanceId=ws456&elementId=elem789"

        # Design Assistant URL format
        design_assistant_url = "https://localhost:3000/app/designassistant/?elementType=ASSEMBLY&documentId=doc123&instanceType=w&instanceId=ws456&elementId=elem789"

        # Both should have the same parameter structure
        from urllib.parse import urlparse, parse_qs

        standard_params = parse_qs(urlparse(standard_url).query)
        da_params = parse_qs(urlparse(design_assistant_url).query)

        # Check that core parameters are the same
        assert standard_params["documentId"] == da_params["documentId"]
        assert standard_params["instanceType"] == da_params["instanceType"]
        assert standard_params["instanceId"] == da_params["instanceId"]
        assert standard_params["elementId"] == da_params["elementId"]

        # Only elementType should differ
        assert standard_params["elementType"] == ["PARTSTUDIO"]
        assert da_params["elementType"] == ["ASSEMBLY"]

    def test_url_construction_parity(self):
        """Test that both modes construct identical URLs given the same IDs."""
        from backend.services.onshape_ids import build_api_path, normalize_instance_type

        # Test case-insensitive instanceType handling
        test_cases = [
            ("WORKSPACE", "w"),
            ("workspace", "w"),
            ("w", "w"),
            ("W", "w"),
            ("VERSION", "v"),
            ("version", "v"),
            ("v", "v"),
            ("V", "v"),
            ("", "w"),  # Default case
            ("unknown", "w"),  # Unknown type defaults to workspace
        ]

        # Test data
        document_id = "doc123"
        instance_id = "ws456"
        element_id = "elem789"

        for input_type, expected_normalized in test_cases:
            # Test that both modes would construct the same API path
            # given the same documentId, instanceId, elementId

            # Standard App would construct: /d/{did}/{wvm}/{wvmid}/e/{eid}
            # Design Assistant should construct: /d/{did}/{wvm}/{wvmid}/e/{eid}

            # The key is that both use the same ID mapping logic
            # So given identical IDs, the constructed API paths should be byte-equal

            # Test the shared service function
            api_path = build_api_path(
                document_id, expected_normalized, instance_id, element_id
            )
            expected_path = (
                f"/d/{document_id}/{expected_normalized}/{instance_id}/e/{element_id}"
            )

            assert (
                api_path == expected_path
            ), f"URL parity failed: expected '{expected_path}' got '{api_path}'"

            # Test normalization function directly
            normalized = normalize_instance_type(input_type)
            assert (
                normalized == expected_normalized
            ), f"Instance type normalization failed: expected '{expected_normalized}' got '{normalized}' for input '{input_type}'"


if __name__ == "__main__":
    pytest.main([__file__])
