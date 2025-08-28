"""Integration test demonstrating how structured storage would work with actual BOM data.

This test shows the complete flow from BOM processing to Onshape storage,
demonstrating the collaborative access pattern we want to achieve.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.services.onshape_bom import process_bom_data
from onshape_api.endpoints.application_elements import (
    create_application_element,
    get_application_elements, 
    update_application_element_content,
    get_application_element_content
)
from onshape_api.paths.doc_path import ElementPath


class TestBomToOnshapeStorageIntegration:
    """Integration tests showing BOM -> Onshape storage workflow."""
    
    @pytest.fixture
    def mock_api(self):
        """Create a mock Onshape API instance."""
        api = Mock()
        api.client_id = "frc-design-app"
        return api
    
    @pytest.fixture
    def assembly_element_path(self):
        """Assembly element path for BOM analysis."""
        return ElementPath("abc123", "workspace789", "assembly456", "w")
    
    @pytest.fixture
    def sample_onshape_bom(self):
        """Sample BOM data as it would come from Onshape API."""
        return {
            "formatVersion": "1.14.0",
            "headers": [
                {"id": "5ace8269c046ad612c65a0ba", "name": "Item"},
                {"id": "57f3fb8efa3416c06701d60d", "name": "Part name"},
                {"id": "57f3fb8efa3416c06701d626", "name": "Mass"},
                {"id": "5ace84d3c046ad611c65a0dd", "name": "Quantity"},
                {"id": "57f3fb8efa3416c06701d615", "name": "Material"}
            ],
            "rows": [
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1",
                        "57f3fb8efa3416c06701d60d": "Chassis Frame",
                        "57f3fb8efa3416c06701d626": "5.2 lb",
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d615": "Aluminum 6061-T6"
                    },
                    "hasChildren": True,
                    "itemSource": {
                        "documentId": "abc123",
                        "wvmType": "w", 
                        "wvmId": "workspace789",
                        "elementId": "part_studio_123"
                    }
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.1",
                        "57f3fb8efa3416c06701d60d": "Frame Rail Left",
                        "57f3fb8efa3416c06701d626": "2.1 lb", 
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d615": ""  # Missing material
                    },
                    "hasChildren": False,
                    "itemSource": {
                        "documentId": "abc123",
                        "wvmType": "w",
                        "wvmId": "workspace789", 
                        "elementId": "part_studio_123",
                        "partId": "part_rail_left"
                    }
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.2",
                        "57f3fb8efa3416c06701d60d": "Frame Rail Right",
                        "57f3fb8efa3416c06701d626": "2.1 lb",
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d615": ""  # Missing material
                    },
                    "hasChildren": False,
                    "itemSource": {
                        "documentId": "abc123",
                        "wvmType": "w",
                        "wvmId": "workspace789",
                        "elementId": "part_studio_123", 
                        "partId": "part_rail_right"
                    }
                }
            ]
        }

    def test_complete_bom_to_onshape_storage_workflow(self, mock_api, assembly_element_path, sample_onshape_bom):
        """Test complete workflow: BOM processing -> Onshape storage -> collaborative retrieval."""
        
        # Step 1: Process BOM data (as it would happen in current system)
        processed_bom = process_bom_data(sample_onshape_bom, "abc123")
        
        # Verify the processing worked correctly
        assert processed_bom["weight_metrics"]["total_weight"] > 0
        assert len(processed_bom["missing_material_parts"]) == 3  # All 3 items (including parent)
        
        # Check for missing materials 
        missing_parts = [part for part in processed_bom["missing_material_parts"] 
                        if part["missingMaterial"]]
        assert len(missing_parts) == 2  # The two frame rails without material
        
        # Step 2: Check for existing BOM storage in Onshape
        mock_api.get.return_value = []  # No existing application elements
        existing_elements = get_application_elements(mock_api, assembly_element_path)
        assert existing_elements == []
        
        # Step 3: Create new application element for BOM storage
        create_response = {
            "id": "bom-app-element-456",
            "name": "FRC Design Assistant BOM Data",
            "formatId": "application/json"
        }
        mock_api.post.return_value = create_response
        
        app_element = create_application_element(
            mock_api,
            assembly_element_path,
            name="FRC Design Assistant BOM Data",
            description="Collaborative BOM analysis data for FRC teams"
        )
        
        app_element_id = app_element["id"]
        
        # Step 4: Store processed BOM data in Onshape structured storage
        document_bom_storage = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": datetime.now().isoformat(),
                "documentId": "abc123",
                "workspaceId": "workspace789",
                "bomSessions": {
                    "assembly456": {
                        "elementId": "assembly456",
                        "elementType": "ASSEMBLY",
                        "bomData": processed_bom,
                        "lastAnalyzed": datetime.now().isoformat(),
                        "analyzedBy": "user-team-lead@example.com"
                    }
                }
            }
        }
        
        update_response = {"changeId": "change789", "status": "success"}
        mock_api.post.return_value = update_response
        
        store_result = update_application_element_content(
            mock_api,
            assembly_element_path,
            app_element_id,
            document_bom_storage,
            description="Initial BOM analysis for robot chassis"
        )
        
        assert store_result["status"] == "success"
        
        # Step 5: Simulate another team member accessing the same document
        mock_api.get.return_value = document_bom_storage
        
        retrieved_data = get_application_element_content(
            mock_api,
            assembly_element_path,
            app_element_id
        )
        
        # Verify collaborative access works
        assert retrieved_data == document_bom_storage
        
        # Verify the other team member sees the same BOM analysis
        bom_session = retrieved_data["frcDesignAppBomData"]["bomSessions"]["assembly456"]
        assert bom_session["analyzedBy"] == "user-team-lead@example.com"
        assert bom_session["bomData"]["weight_metrics"]["total_weight"] == processed_bom["weight_metrics"]["total_weight"]
        
        # They can see which parts are missing materials
        missing_materials = [part for part in bom_session["bomData"]["missing_material_parts"]
                           if part["missingMaterial"]]
        assert len(missing_materials) == 2
        assert missing_materials[0]["part_name"] == "Frame Rail Left" 
        assert missing_materials[1]["part_name"] == "Frame Rail Right"

    def test_part_studio_filtered_access(self, mock_api, sample_onshape_bom):
        """Test that part studio access only shows relevant parts from stored BOM."""
        
        # Process full assembly BOM
        processed_bom = process_bom_data(sample_onshape_bom, "abc123")
        
        # Store in Onshape (as would be done from assembly context)
        assembly_path = ElementPath("abc123", "workspace789", "assembly456", "w")
        part_studio_path = ElementPath("abc123", "workspace789", "part_studio_123", "w")
        
        document_bom_storage = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "documentId": "abc123",
                "workspaceId": "workspace789", 
                "bomSessions": {
                    "assembly456": {
                        "bomData": processed_bom
                    }
                }
            }
        }
        
        # Simulate accessing from part studio
        mock_api.get.return_value = document_bom_storage
        
        retrieved_data = get_application_element_content(
            mock_api,
            part_studio_path, 
            "bom-app-element-456"
        )
        
        # In the real implementation, we would filter this data to show only
        # parts from the current part studio (part_studio_123)
        all_parts = retrieved_data["frcDesignAppBomData"]["bomSessions"]["assembly456"]["bomData"]["missing_material_parts"]
        
        # Filter for parts from current part studio (this would be done in the service layer)
        part_studio_parts = [
            part for part in all_parts
            if part.get("document", {}).get("elementId") == "part_studio_123"
        ]
        
        # Verify we get the expected parts from this part studio
        assert len(part_studio_parts) == 3  # Chassis frame + 2 rails
        part_names = [part["part_name"] for part in part_studio_parts]
        assert "Chassis Frame" in part_names
        assert "Frame Rail Left" in part_names
        assert "Frame Rail Right" in part_names

    def test_data_freshness_and_collaboration_metadata(self, mock_api, assembly_element_path, sample_onshape_bom):
        """Test that we can track who analyzed the BOM and when."""
        
        processed_bom = process_bom_data(sample_onshape_bom, "abc123")
        
        # Simulate user A analyzing the BOM
        user_a_timestamp = "2025-01-15T10:00:00Z"
        user_a_storage = {
            "frcDesignAppBomData": {
                "version": "1.0",
                "lastUpdated": user_a_timestamp,
                "documentId": "abc123",
                "bomSessions": {
                    "assembly456": {
                        "bomData": processed_bom,
                        "lastAnalyzed": user_a_timestamp,
                        "analyzedBy": "alice@robotics-team.com"
                    }
                }
            }
        }
        
        mock_api.post.return_value = {"status": "success"}
        update_application_element_content(
            mock_api, assembly_element_path, "bom-123", user_a_storage
        )
        
        # Simulate user B accessing later
        mock_api.get.return_value = user_a_storage
        
        user_b_retrieved = get_application_element_content(
            mock_api, assembly_element_path, "bom-123"
        )
        
        # User B can see when the analysis was done and by whom
        bom_session = user_b_retrieved["frcDesignAppBomData"]["bomSessions"]["assembly456"]
        assert bom_session["analyzedBy"] == "alice@robotics-team.com"
        assert bom_session["lastAnalyzed"] == user_a_timestamp
        
        # User B knows the data is from 10 AM and can decide if they want to refresh
        from datetime import datetime
        analysis_time = datetime.fromisoformat(bom_session["lastAnalyzed"].replace("Z", "+00:00"))
        assert analysis_time.hour == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])