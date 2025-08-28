"""Unit tests for Onshape structured storage functionality.

These tests validate that we can create, read, and update BOM data 
using Onshape's application elements and JSON tree storage.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from onshape_api.endpoints.application_elements import (
    create_application_element,
    get_application_elements,
    get_application_element_content,
    update_application_element_content,
    delete_application_element
)
from onshape_api.paths.doc_path import ElementPath


class TestStructuredStorage:
    """Test cases for Onshape structured storage operations."""
    
    @pytest.fixture
    def mock_api(self):
        """Create a mock Onshape API instance."""
        api = Mock()
        api.client_id = "frc-design-app-test"
        return api
    
    @pytest.fixture
    def element_path(self):
        """Create a sample element path for testing."""
        return ElementPath("doc123", "workspace456", "elem789", "w")
    
    @pytest.fixture
    def sample_bom_data(self):
        """Create sample BOM data for testing."""
        return {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": datetime.now().isoformat(),
                "documentId": "doc123",
                "workspaceId": "workspace456",
                "bomSessions": {
                    "elem789": {
                        "elementId": "elem789",
                        "bomData": {
                            "weight_metrics": {
                                "unit": "lb",
                                "total_weight": 15.25,
                                "rows_counted": 12,
                                "rows_skipped": 2
                            },
                            "missing_material_parts": [
                                {
                                    "part_name": "Test Part 1",
                                    "weight": 2.5,
                                    "quantity": 1,
                                    "material": None,
                                    "missingMaterial": True
                                }
                            ]
                        },
                        "lastAnalyzed": datetime.now().isoformat(),
                        "analyzedBy": "test-user"
                    }
                }
            }
        }

    def test_create_application_element(self, mock_api, element_path):
        """Test creating a new application element for BOM storage."""
        # Mock API response
        expected_response = {
            "id": "app-elem-123",
            "name": "FRC BOM Data",
            "description": "BOM analysis data for FRC Design Assistant",
            "formatId": "application/json"
        }
        mock_api.post.return_value = expected_response
        
        # Call the function
        result = create_application_element(
            mock_api, 
            element_path,
            name="FRC BOM Data",
            description="BOM analysis data for FRC Design Assistant"
        )
        
        # Verify the call
        assert result == expected_response
        mock_api.post.assert_called_once()
        
        # Verify request body
        call_args = mock_api.post.call_args
        body = call_args[1]['body']
        assert body['name'] == "FRC BOM Data"
        assert body['description'] == "BOM analysis data for FRC Design Assistant"
        assert body['formatId'] == "application/json"
        assert body['applicationId'] == "frc-design-app-test"

    def test_get_application_elements(self, mock_api, element_path):
        """Test retrieving existing application elements."""
        # Mock API response
        expected_response = [
            {
                "id": "app-elem-123",
                "name": "FRC BOM Data",
                "formatId": "application/json"
            }
        ]
        mock_api.get.return_value = expected_response
        
        # Call the function
        result = get_application_elements(mock_api, element_path)
        
        # Verify the result
        assert result == expected_response
        mock_api.get.assert_called_once()

    def test_update_bom_content(self, mock_api, element_path, sample_bom_data):
        """Test updating BOM content in structured storage."""
        app_element_id = "app-elem-123"
        
        # Mock API response
        expected_response = {
            "changeId": "change-456",
            "status": "success"
        }
        mock_api.post.return_value = expected_response
        
        # Call the function
        result = update_application_element_content(
            mock_api,
            element_path, 
            app_element_id,
            sample_bom_data,
            description="Updated BOM analysis data"
        )
        
        # Verify the result
        assert result == expected_response
        mock_api.post.assert_called_once()
        
        # Verify request body
        call_args = mock_api.post.call_args
        body = call_args[1]['body']
        assert body['description'] == "Updated BOM analysis data"
        assert body['jsonTree'] == sample_bom_data

    def test_get_bom_content(self, mock_api, element_path, sample_bom_data):
        """Test retrieving BOM content from structured storage."""
        app_element_id = "app-elem-123"
        
        # Mock API response
        mock_api.get.return_value = sample_bom_data
        
        # Call the function
        result = get_application_element_content(
            mock_api,
            element_path,
            app_element_id
        )
        
        # Verify the result
        assert result == sample_bom_data
        mock_api.get.assert_called_once()
        
        # Verify we can access the BOM data structure
        bom_data = result["frcDesignAppBomData"]
        assert bom_data["version"] == "1.0"
        assert bom_data["documentId"] == "doc123"
        assert "elem789" in bom_data["bomSessions"]
        
        # Verify weight metrics
        weight_metrics = bom_data["bomSessions"]["elem789"]["bomData"]["weight_metrics"]
        assert weight_metrics["total_weight"] == 15.25
        assert weight_metrics["unit"] == "lb"

    def test_delete_application_element(self, mock_api, element_path):
        """Test deleting an application element."""
        app_element_id = "app-elem-123"
        
        # Mock API response
        expected_response = {"status": "deleted"}
        mock_api.delete.return_value = expected_response
        
        # Call the function
        result = delete_application_element(
            mock_api,
            element_path,
            app_element_id
        )
        
        # Verify the result
        assert result == expected_response
        mock_api.delete.assert_called_once()


class TestBomStorageIntegration:
    """Integration test cases for complete BOM storage workflow."""
    
    @pytest.fixture
    def mock_api(self):
        """Create a mock Onshape API instance."""
        api = Mock()
        api.client_id = "frc-design-app-test"
        return api
    
    @pytest.fixture
    def element_path(self):
        """Create a sample element path for testing."""
        return ElementPath("doc123", "workspace456", "elem789", "w")

    def test_complete_bom_storage_workflow(self, mock_api, element_path):
        """Test the complete workflow: create element, store BOM, retrieve BOM."""
        
        # Step 1: Check for existing application elements (none found)
        mock_api.get.return_value = []
        
        existing_elements = get_application_elements(mock_api, element_path)
        assert existing_elements == []
        
        # Step 2: Create new application element
        create_response = {
            "id": "app-elem-123",
            "name": "FRC BOM Data",
            "formatId": "application/json"
        }
        mock_api.post.return_value = create_response
        
        element_result = create_application_element(
            mock_api,
            element_path, 
            name="FRC BOM Data",
            description="BOM analysis data for collaborative access"
        )
        
        app_element_id = element_result["id"]
        assert app_element_id == "app-elem-123"
        
        # Step 3: Store BOM data
        bom_data = {
            "frcDesignAppBomData": {
                "version": "1.0", 
                "lastUpdated": datetime.now().isoformat(),
                "documentId": "doc123",
                "workspaceId": "workspace456",
                "bomSessions": {
                    "elem789": {
                        "elementId": "elem789",
                        "bomData": {
                            "weight_metrics": {"total_weight": 10.5, "unit": "lb"},
                            "missing_material_parts": []
                        }
                    }
                }
            }
        }
        
        update_response = {"changeId": "change-456", "status": "success"}
        mock_api.post.return_value = update_response
        
        store_result = update_application_element_content(
            mock_api,
            element_path,
            app_element_id,
            bom_data
        )
        
        assert store_result["status"] == "success"
        
        # Step 4: Retrieve BOM data (simulate another user accessing)
        mock_api.get.return_value = bom_data
        
        retrieved_data = get_application_element_content(
            mock_api,
            element_path,
            app_element_id
        )
        
        # Verify data integrity
        assert retrieved_data == bom_data
        retrieved_bom = retrieved_data["frcDesignAppBomData"]["bomSessions"]["elem789"]
        assert retrieved_bom["bomData"]["weight_metrics"]["total_weight"] == 10.5
        
        # Verify API calls were made correctly
        assert mock_api.get.call_count == 2  # get elements + get content
        assert mock_api.post.call_count == 2  # create element + update content

    def test_collaborative_access_simulation(self, mock_api, element_path):
        """Test simulation of multiple users accessing the same BOM data."""
        
        # Simulate User A storing BOM data
        app_element_id = "app-elem-123"
        user_a_data = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": "2025-01-15T10:00:00Z",
                "documentId": "doc123", 
                "bomSessions": {
                    "elem789": {
                        "bomData": {"weight_metrics": {"total_weight": 12.3}},
                        "analyzedBy": "user-a"
                    }
                }
            }
        }
        
        # User A stores data
        mock_api.post.return_value = {"status": "success"}
        update_application_element_content(mock_api, element_path, app_element_id, user_a_data)
        
        # Simulate User B retrieving the same data
        mock_api.get.return_value = user_a_data
        
        user_b_retrieved = get_application_element_content(mock_api, element_path, app_element_id)
        
        # Verify User B sees User A's analysis
        assert user_b_retrieved == user_a_data
        assert user_b_retrieved["frcDesignAppBomData"]["bomSessions"]["elem789"]["analyzedBy"] == "user-a"
        
        # Both users should see the same total weight
        weight = user_b_retrieved["frcDesignAppBomData"]["bomSessions"]["elem789"]["bomData"]["weight_metrics"]["total_weight"]
        assert weight == 12.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])