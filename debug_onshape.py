#!/usr/bin/env python3
"""
Debug script to test Onshape API connection and path construction.
Run this script to test if the API connection is working and to debug path issues.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

try:
    from backend.common.connect import get_db, get_api
    from onshape_api.paths.doc_path import ElementPath, InstanceType

    print("✓ Successfully imported required modules")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_api_connection():
    """Test the Onshape API connection."""
    print("\n=== Testing API Connection ===")
    try:
        db = get_db()
        api = get_api(db)
        print("✓ Successfully created API instance")

        # Test basic API call
        try:
            user_info = api.get("/api/users/session")
            print("✓ API connection successful")
            print(f"  User: {user_info.get('name', 'Unknown')}")
            print(f"  Company: {user_info.get('company', 'Unknown')}")
        except Exception as e:
            print(f"✗ API call failed: {e}")
            return False

    except Exception as e:
        print(f"✗ Failed to create API instance: {e}")
        return False

    return True


def test_path_construction():
    """Test path construction with sample parameters."""
    print("\n=== Testing Path Construction ===")

    # Sample parameters (replace with actual values from your error)
    sample_params = {
        "document_id": "1234567890abcdef12345678",  # Replace with actual document ID
        "instance_id": "1234567890abcdef12345678",  # Replace with actual instance ID
        "element_id": "1234567890abcdef12345678",  # Replace with actual element ID
        "instance_type": InstanceType.WORKSPACE,
    }

    try:
        element_path = ElementPath(
            document_id=sample_params["document_id"],
            instance_id=sample_params["instance_id"],
            element_id=sample_params["element_id"],
            instance_type=sample_params["instance_type"],
        )

        print("✓ Successfully created ElementPath")
        print(f"  Document ID: {element_path.document_id}")
        print(f"  Instance ID: {element_path.instance_id}")
        print(f"  Element ID: {element_path.element_id}")
        print(f"  Instance Type: {element_path.instance_type}")
        print(f"  API Path: {ElementPath.to_api_path(element_path)}")
        print(f"  API Object: {ElementPath.to_api_object(element_path)}")

    except Exception as e:
        print(f"✗ Failed to create ElementPath: {e}")
        return False

    return True


def test_assembly_api_calls(api, element_path):
    """Test the specific API calls that are failing."""
    print("\n=== Testing Assembly API Calls ===")

    try:
        # Test assembly definition
        print("Testing assembly definition...")
        definition = api.get(
            f"/api/assemblies/{element_path.document_id}/{element_path.instance_type}/{element_path.instance_id}/e/{element_path.element_id}/definition"
        )
        print("✓ Assembly definition retrieved successfully")

        # Test mass properties
        print("Testing mass properties...")
        mass_props = api.get(
            f"/api/assemblies/{element_path.document_id}/{element_path.instance_type}/{element_path.instance_id}/e/{element_path.element_id}/massproperties"
        )
        print("✓ Mass properties retrieved successfully")

        # Test workspace parts
        print("Testing workspace parts...")
        parts = api.get(
            f"/api/parts/{element_path.document_id}/{element_path.instance_type}/{element_path.instance_id}"
        )
        print("✓ Workspace parts retrieved successfully")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        return False

    return True


def main():
    """Main function to run all tests."""
    print("Onshape API Debug Script")
    print("=" * 50)

    # Test 1: API Connection
    if not test_api_connection():
        print(
            "\n❌ API connection test failed. Check your credentials and network connection."
        )
        return

    # Test 2: Path Construction
    if not test_path_construction():
        print("\n❌ Path construction test failed. Check the path parameters.")
        return

    # Test 3: Assembly API Calls (if you have valid IDs)
    print("\n=== Note ===")
    print(
        "To test assembly API calls, you need valid document, instance, and element IDs."
    )
    print(
        "Replace the sample IDs in the test_path_construction() function with your actual IDs."
    )
    print("You can get these from the Onshape URL when viewing your assembly.")

    print("\n✅ All basic tests completed successfully!")
    print("\nNext steps:")
    print("1. Check the debug output in your Flask application")
    print("2. Verify the parameters being passed from the frontend")
    print("3. Test the /debug-path endpoint to verify path construction")
    print("4. Test the /test-api endpoint to verify API connection")


if __name__ == "__main__":
    main()
