#!/usr/bin/env python3
"""
Simple test script to verify the backend design assistant endpoints.
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"  # Adjust if your backend runs on different port
DESIGN_ASSISTANT_BASE = f"{BASE_URL}/app/designassistant"


def test_ingest_endpoint():
    """Test the BOM ingest endpoint."""
    print("Testing BOM ingest endpoint...")

    # Sample BOM data
    sample_bom = {
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
                    "name": "Test Part A",
                    "quantity": "2",
                    "mass": "1.5 lb",
                    "material": "Aluminum 6061",
                },
                {
                    "item": "2",
                    "name": "Test Part B",
                    "quantity": "1",
                    "mass": "2.0 kg",
                    "material": "",
                },
            ],
        }
    }

    try:
        response = requests.post(
            f"{DESIGN_ASSISTANT_BASE}/ingest",
            json=sample_bom,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Ingest endpoint working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Ingest endpoint failed: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def test_weight_metrics_endpoint():
    """Test the weight metrics endpoint."""
    print("\nTesting weight metrics endpoint...")

    try:
        response = requests.get(f"{DESIGN_ASSISTANT_BASE}/metrics/weight")

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Weight metrics endpoint working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Weight metrics endpoint failed: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def test_missing_material_endpoint():
    """Test the missing material report endpoint."""
    print("\nTesting missing material report endpoint...")

    try:
        response = requests.get(f"{DESIGN_ASSISTANT_BASE}/reports/missing-material")

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Missing material report endpoint working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Missing material report endpoint failed: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def test_available_documents_endpoint():
    """Test the available documents endpoint."""
    print("\nTesting available documents endpoint...")

    # Test parameters
    params = {
        "documentId": "test_doc_123",
        "instanceType": "w",
        "instanceId": "test_ws_456",
        "elementId": "test_elem_789",
        "elementType": "ASSEMBLY",
    }

    try:
        response = requests.get(
            f"{DESIGN_ASSISTANT_BASE}/available-documents", params=params
        )

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Available documents endpoint working!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Available documents endpoint failed: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def main():
    """Run all tests."""
    print("🧪 Testing Design Assistant Backend Endpoints")
    print("=" * 50)

    # Test endpoints
    test_ingest_endpoint()
    test_weight_metrics_endpoint()
    test_missing_material_endpoint()
    test_available_documents_endpoint()

    print("\n" + "=" * 50)
    print("✅ Testing complete!")


if __name__ == "__main__":
    main()
