import pytest
import json
from unittest.mock import Mock, patch
from backend.services.onshape_ids import (
    normalize_instance_type,
    validate_element_type,
)
from backend.services.onshape_bom import (
    parse_mass,
    has_material,
    process_bom_data,
)


class TestBomAnalysis:
    """Test cases for BOM analysis functionality."""

    def test_parse_mass_lbs(self):
        """Test parsing mass in pounds."""
        assert parse_mass("1.5 lb") == 1.5
        assert parse_mass("2.0 lbs") == 2.0
        assert parse_mass("3 pounds") == 3.0

    def test_parse_mass_kg(self):
        """Test parsing mass in kilograms and converting to pounds."""
        # 1 kg = 2.20462 lbs
        assert abs(parse_mass("1 kg") - 2.20462) < 0.001
        assert abs(parse_mass("2.5 kgs") - 5.51155) < 0.001

    def test_parse_mass_grams(self):
        """Test parsing mass in grams and converting to pounds."""
        # 1 g = 0.00220462 lbs
        assert abs(parse_mass("1000 g") - 2.20462) < 0.001
        assert abs(parse_mass("500 grams") - 1.10231) < 0.001

    def test_parse_mass_invalid(self):
        """Test parsing invalid mass values."""
        assert parse_mass("") is None
        assert parse_mass("N/A") is None
        assert parse_mass("invalid") is None
        assert parse_mass("1.5") == 1.5  # Default to pounds

    def test_has_material_string(self):
        """Test material detection with string values."""
        assert has_material("Aluminum 6061") is True
        assert has_material("") is False
        assert has_material("   ") is False

    def test_has_material_dict(self):
        """Test material detection with dictionary values."""
        assert has_material({"displayName": "Aluminum 6061", "id": "123"}) is True
        assert has_material({"id": "123"}) is True
        assert has_material({}) is False
        assert has_material(None) is False

    def test_process_bom_data_valid(self):
        """Test processing valid BOM data."""
        bom_data = {
            "bomTable": {
                "headers": [
                    {"id": "item", "name": "Item"},
                    {"id": "name", "name": "Name"},
                    {"id": "quantity", "name": "Quantity"},
                    {"id": "mass", "name": "Mass"},
                    {"id": "material", "name": "Material"},
                ],
                "rows": [
                    {
                        "item": "1",
                        "name": "Part A",
                        "quantity": "2",
                        "mass": "1.5 lb",
                        "material": "Aluminum 6061",
                        "document": {
                            "documentId": "doc1",
                            "workspaceId": "ws1",
                            "elementId": "elem1",
                            "partId": "part1",
                        },
                    },
                    {
                        "item": "2",
                        "name": "Part B",
                        "quantity": "1",
                        "mass": "2.0 kg",
                        "material": "",
                        "document": {
                            "documentId": "doc2",
                            "workspaceId": "ws2",
                            "elementId": "elem2",
                            "partId": "part2",
                        },
                    },
                ],
            }
        }

        result = process_bom_data(bom_data)

        # Check weight metrics
        assert result["weight_metrics"]["unit"] == "lb"
        assert (
            abs(result["weight_metrics"]["total_weight"] - (1.5 * 2 + 2.0 * 2.20462))
            < 0.001
        )
        assert result["weight_metrics"]["rows_counted"] == 2
        assert result["weight_metrics"]["rows_skipped"] == 0

        # Check missing material parts
        assert len(result["missing_material_parts"]) == 1
        assert result["missing_material_parts"][0]["name"] == "Part B"

    def test_process_bom_data_empty(self):
        """Test processing empty BOM data returns empty result."""
        result = process_bom_data({})
        assert result["weight_metrics"]["total_weight"] == 0.0
        assert result["weight_metrics"]["rows_counted"] == 0
        assert len(result["missing_material_parts"]) == 0

        result = process_bom_data({"bomTable": None})
        assert result["weight_metrics"]["total_weight"] == 0.0
        assert result["weight_metrics"]["rows_counted"] == 0
        assert len(result["missing_material_parts"]) == 0

    def test_process_bom_data_with_zero_quantity(self):
        """Test processing BOM data with zero quantity rows."""
        bom_data = {
            "bomTable": {
                "headers": [
                    {"id": "item", "name": "Item"},
                    {"id": "quantity", "name": "Quantity"},
                    {"id": "mass", "name": "Mass"},
                ],
                "rows": [
                    {"item": "1", "quantity": "0", "mass": "1.5 lb"},
                    {"item": "2", "quantity": "1", "mass": "2.0 lb"},
                ],
            }
        }

        result = process_bom_data(bom_data)

        # Zero quantity row should be skipped
        assert result["weight_metrics"]["rows_counted"] == 1
        assert result["weight_metrics"]["rows_skipped"] == 1
        assert result["weight_metrics"]["total_weight"] == 2.0

    def test_subassembly_detection_and_mass_calculation(self):
        """Test hierarchical subassembly detection and mass calculation."""
        bom_data = {
            "headers": [
                {"id": "5ace8269c046ad612c65a0ba", "name": "Item"},  # Item number
                {"id": "57f3fb8efa3416c06701d60d", "name": "Name"},  # Part name
                {"id": "5ace84d3c046ad611c65a0dd", "name": "Quantity"},  # Quantity
                {"id": "57f3fb8efa3416c06701d626", "name": "Mass"},  # Weight
                {"id": "57f3fb8efa3416c06701d615", "name": "Material"},  # Material
            ],
            "rows": [
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1",
                        "57f3fb8efa3416c06701d60d": "Main Assembly", 
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d626": "",  # No direct mass
                        "57f3fb8efa3416c06701d615": ""
                    },
                    "itemSource": {"documentId": "doc1"}
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.1", 
                        "57f3fb8efa3416c06701d60d": "Subassembly A",
                        "5ace84d3c046ad611c65a0dd": 2,
                        "57f3fb8efa3416c06701d626": "",  # No direct mass
                        "57f3fb8efa3416c06701d615": ""
                    },
                    "itemSource": {"documentId": "doc1"}
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.1.1",
                        "57f3fb8efa3416c06701d60d": "Part A1", 
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d626": "2.5 lb",
                        "57f3fb8efa3416c06701d615": "Steel"
                    },
                    "itemSource": {"documentId": "doc1"}
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.1.2",
                        "57f3fb8efa3416c06701d60d": "Part A2",
                        "5ace84d3c046ad611c65a0dd": 1, 
                        "57f3fb8efa3416c06701d626": "1.5 lb",
                        "57f3fb8efa3416c06701d615": ""  # Missing material
                    },
                    "itemSource": {"documentId": "doc1"}
                },
                {
                    "headerIdToValue": {
                        "5ace8269c046ad612c65a0ba": "1.2",
                        "57f3fb8efa3416c06701d60d": "Part B",
                        "5ace84d3c046ad611c65a0dd": 1,
                        "57f3fb8efa3416c06701d626": "3.0 lb", 
                        "57f3fb8efa3416c06701d615": "Aluminum"
                    },
                    "itemSource": {"documentId": "doc1"}
                }
            ]
        }

        result = process_bom_data(bom_data, "doc1")

        # Check that subassemblies are detected
        parts = result["missing_material_parts"]
        
        main_assembly = next(p for p in parts if p["item"] == "1")
        subassembly_a = next(p for p in parts if p["item"] == "1.1") 
        part_a1 = next(p for p in parts if p["item"] == "1.1.1")
        part_a2 = next(p for p in parts if p["item"] == "1.1.2")
        part_b = next(p for p in parts if p["item"] == "1.2")

        # Verify hierarchy detection
        assert main_assembly["isSubassembly"] is True
        assert main_assembly["indentLevel"] == 0
        assert main_assembly["hasChildren"] is True
        
        assert subassembly_a["isSubassembly"] is True
        assert subassembly_a["indentLevel"] == 1
        assert subassembly_a["hasChildren"] is True
        assert subassembly_a["parentId"] == "1"
        
        assert part_a1["isSubassembly"] is False
        assert part_a1["indentLevel"] == 2
        assert part_a1["parentId"] == "1.1"
        
        assert part_b["isSubassembly"] is False
        assert part_b["indentLevel"] == 1
        assert part_b["parentId"] == "1"

        # Verify mass calculations
        # Subassembly A should have mass = 2.5 + 1.5 = 4.0 lb per unit
        # With quantity 2, total = 8.0 lb
        assert abs(subassembly_a["calculatedMass"] - 4.0) < 0.001
        assert abs(subassembly_a["mass_lb"] - 4.0) < 0.001
        
        # Main assembly should have mass = (4.0 * 2) + 3.0 = 11.0 lb
        assert abs(main_assembly["calculatedMass"] - 11.0) < 0.001
        assert abs(main_assembly["mass_lb"] - 11.0) < 0.001

        # Verify missing material propagation
        # Part A2 has missing material but has mass, so should not propagate as missing mass
        assert subassembly_a["hasChildrenMissingMass"] is False  # Part A2 has mass despite missing material
        assert main_assembly["hasChildrenMissingMass"] is False  # No children missing mass
        
        # Verify total weight calculation includes hierarchy
        # Total should be: Main Assembly * quantity = 11.0 * 1 = 11.0 lb
        assert abs(result["weight_metrics"]["total_weight"] - 11.0) < 0.001


class TestInstanceTypeNormalization:
    """Test cases for instance type normalization."""

    def test_normalize_workspace_variants(self):
        """Test normalization of workspace instance types."""
        assert normalize_instance_type("WORKSPACE") == "w"
        assert normalize_instance_type("workspace") == "w"
        assert normalize_instance_type("Workspace") == "w"
        assert normalize_instance_type("w") == "w"
        assert normalize_instance_type("W") == "w"

    def test_normalize_version_variants(self):
        """Test normalization of version instance types."""
        assert normalize_instance_type("VERSION") == "v"
        assert normalize_instance_type("version") == "v"
        assert normalize_instance_type("Version") == "v"
        assert normalize_instance_type("v") == "v"
        assert normalize_instance_type("V") == "v"

    def test_normalize_edge_cases(self):
        """Test normalization of edge cases."""
        assert normalize_instance_type("") == "w"  # Default to workspace
        assert normalize_instance_type(None) == "w"  # Default to workspace
        assert (
            normalize_instance_type("unknown") == "w"
        )  # Unknown defaults to workspace
        assert (
            normalize_instance_type("PARTSTUDIO") == "w"
        )  # Unrecognized defaults to workspace


class TestElementTypeValidation:
    """Test cases for element type validation."""

    def test_validate_assembly_types(self):
        """Test validation of assembly element types."""
        # Valid assembly types
        validate_element_type("ASSEMBLY")
        validate_element_type("assembly")
        validate_element_type("Assembly")

    def test_validate_invalid_types(self):
        """Test validation of invalid element types."""
        from backend.common.backend_exceptions import ClientException
        
        with pytest.raises(ClientException):
            validate_element_type("PARTSTUDIO")

        with pytest.raises(ClientException):
            validate_element_type("DRAWING")

        with pytest.raises(ClientException):
            validate_element_type("")

        with pytest.raises(ClientException):
            validate_element_type(None)


if __name__ == "__main__":
    pytest.main([__file__])
