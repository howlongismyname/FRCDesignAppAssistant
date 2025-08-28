# FRC Design App - Structured Storage Migration

## Overview

This document outlines the migration from Firestore to Onshape's structured storage system for BOM (Bill of Materials) data. The goal is to enable collaborative access where multiple users can see the same BOM analysis stored natively in Onshape documents.

## Architecture

### Current State (Firestore)
- BOM data stored in Google Firestore
- User-specific sessions and data isolation
- No collaborative access between users on same document

### Target State (Onshape Structured Storage)
- BOM data stored in Onshape Application Elements
- Document-native storage enables collaboration
- Multiple users can access same BOM analysis
- Date tracking for collaborative workflows

## Implementation

### API Structure

The implementation uses Onshape's Application Elements API:

```
POST /api/v12/appelements/d/{did}/w/{wid}           # Create application element
GET  /api/v12/documents/d/{did}/w/{wid}/elements    # List all document elements  
GET  /api/v12/appelements/d/{did}/w/{wid}/e/{eid}/content    # Get element content
POST /api/v12/appelements/d/{did}/w/{wid}/e/{eid}/content    # Update element content
DELETE /api/v12/appelements/d/{did}/w/{wid}/e/{eid}          # Delete element
```

### Key Files

#### Backend API Implementation
- `onshape_api/endpoints/application_elements.py` - Core AppElement API functions
- `backend/endpoints/structured_storage_test.py` - Test endpoints (remove before production)

#### Frontend Test Interface  
- `frontend/src/structured-storage-test/structured-storage-test.tsx` - Test UI component

#### Core Functions

```python
# Create application element for BOM storage
def create_application_element(api, instance_path, name, format_id="application/json", ...)

# List all document elements and filter for application elements
def list_document_elements(api, instance_path, with_thumbnails=False, ...)

# Store structured BOM data
def store_structured_data(api, element_path, data, subelement_path="data", ...)

# Retrieve application element content
def get_application_element_content(api, element_path, transaction_id=None, ...)
```

### Data Structure

BOM data stored in application elements follows this structure:

```json
{
  "frcDesignAppBomData": {
    "version": "1.0",
    "lastUpdated": "2024-01-15T10:30:00Z",
    "documentId": "68605ba7defff336ac91be4a",
    "workspaceId": "6dff963c61a7bb32207434ee",
    "testData": false,
    "bomSessions": {
      "session_id_1": {
        "timestamp": "2024-01-15T10:30:00Z",
        "user": "user@example.com",
        "bomData": {
          // Processed BOM analysis results
        }
      }
    }
  }
}
```

## Testing Status: ✅ FULLY WORKING

### ✅ Complete Working Workflow

All structured storage operations are now functional with the correct API format:

1. **List Application Elements**
   - Endpoint: `GET /test-list-app-elements`
   - Uses `/documents/d/{did}/w/{wid}/elements` to list all document elements
   - Filters results to show only application elements
   - Returns both application elements and all elements for debugging

2. **Get Element ID (Helper)**
   - Endpoint: `GET /test-get-element-id` 
   - Returns first available application element ID
   - Automatically copies ID to clipboard for easy use
   - Same authentication pattern as other endpoints

3. **Create Application Element** 
   - Endpoint: `POST /test-create-app-element`
   - Creates new application element with pre-configured subelements
   - Uses workspace-level creation path: `/appelements/d/{did}/w/{wid}`
   - Auto-creates "bomData" and "metadata" subelements to prevent "does not exist" errors
   - Returns element ID for further operations

4. **Upload Test Data** 
   - Endpoint: `POST /test-upload-data?appElementId={id}`
   - Uses `/appelements/d/{did}/w/{wid}/e/{eid}/content` endpoint
   - Employs safe storage method that handles subelement creation if needed
   - Stores structured BOM test data with weight metrics

5. **Retrieve Test Data**
   - Endpoint: `GET /test-retrieve-data?appElementId={id}`
   - Uses `/appelements/d/{did}/w/{wid}/e/{eid}/content/json` endpoint
   - Successfully retrieves and validates uploaded test data
   - Identifies test data types (uploadTest, testData flags)

6. **Cleanup Element**
   - Endpoint: `DELETE /test-cleanup-app-element?appElementId={id}`
   - Deletes test application elements
   - Uses `/appelements/d/{did}/w/{wid}/e/{eid}` endpoint

## Complete API Workflow Documentation

### Step-by-Step Structured Storage Workflow

This section documents the exact API calls and request/response formats for implementing structured storage in production.

#### 1. List Existing Application Elements

**Purpose**: Check what application elements already exist in the document

**API Call**:
```http
GET /api/v12/documents/d/{documentId}/w/{workspaceId}/elements
```

**Response**: Array of all document elements. Filter for `elementType: "APPLICATION"`

**Python Implementation**:
```python
from onshape_api.endpoints.application_elements import list_document_elements

# Get all elements
all_elements = list_document_elements(api, instance_path)

# Filter for application elements
app_elements = [elem for elem in all_elements if elem.get("elementType") == "APPLICATION"]
```

#### 2. Create New Application Element (if needed)

**Purpose**: Create a new application element with default subelements for BOM storage

**API Call**:
```http
POST /api/v12/appelements/d/{documentId}/w/{workspaceId}
```

**Request Body**:
```json
{
  "description": "FRC Design App BOM Storage",
  "formatId": "application/json",
  "name": "FRC Design App Test Element",
  "subelements": [
    {
      "baseContent": "",
      "delta": "{}",
      "subelementId": "bomData"
    },
    {
      "baseContent": "",
      "delta": "{}",
      "subelementId": "metadata"
    }
  ]
}
```

**Response**: Returns element info including `id` field for use in subsequent calls

**Python Implementation**:
```python
from onshape_api.endpoints.application_elements import create_application_element

result = create_application_element(
    api,
    instance_path,
    name="FRC Design App BOM Storage",
    description="Collaborative BOM analysis storage"
)
app_element_id = result["id"]
```

#### 3. Upload/Store BOM Data

**Purpose**: Store structured BOM analysis data in the application element

**API Call**:
```http
POST /api/v12/appelements/d/{documentId}/w/{workspaceId}/e/{elementId}/content
```

**Request Body**:
```json
{
  "changes": [
    {
      "baseContent": "",
      "delta": "{\"frcDesignAppBomData\":{\"version\":\"1.0\",\"bomSessions\":{}}}",
      "subelementId": "bomData"
    }
  ],
  "description": "Store BOM analysis data",
  "returnError": true,
  "returnJsonDifferenceFormat": "default"
}
```

**BOM Data Structure** (stored in delta as JSON string):
```json
{
  "frcDesignAppBomData": {
    "version": "1.0",
    "lastUpdated": "2024-01-28T15:30:00Z",
    "documentId": "68605ba7defff336ac91be4a",
    "workspaceId": "6dff963c61a7bb32207434ee",
    "testData": false,
    "bomSessions": {
      "assembly_element_id": {
        "elementId": "assembly_element_id",
        "bomData": {
          "weight_metrics": {
            "unit": "lb",
            "total_weight": 42.5,
            "rows_counted": 150,
            "rows_skipped": 2
          },
          "missing_material_parts": [
            {
              "part_name": "Custom Bracket",
              "weight": 0.5,
              "quantity": 4,
              "material": null,
              "missingMaterial": true
            }
          ]
        },
        "lastAnalyzed": "2024-01-28T15:30:00Z",
        "analyzedBy": "user@example.com"
      }
    }
  }
}
```

**Python Implementation**:
```python
from onshape_api.endpoints.application_elements import store_structured_data

# BOM data structure
bom_data = {
    "frcDesignAppBomData": {
        "version": "1.0",
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "documentId": document_id,
        "workspaceId": workspace_id,
        "bomSessions": {
            assembly_element_id: {
                "bomData": analysis_results,
                "lastAnalyzed": datetime.now(timezone.utc).isoformat(),
                "analyzedBy": user_email
            }
        }
    }
}

# Store data safely (handles subelement creation)
result = store_structured_data(
    api,
    element_path,
    bom_data,
    subelement_id="bomData",
    description="Store BOM analysis results"
)
```

#### 4. Retrieve/Load BOM Data

**Purpose**: Load existing BOM analysis data for collaborative access

**API Call**:
```http
GET /api/v12/appelements/d/{documentId}/w/{workspaceId}/e/{elementId}/content/json
```

**Response**: Returns the complete BOM data structure as stored

**Python Implementation**:
```python
from onshape_api.endpoints.application_elements import get_application_element_content

# Retrieve stored data
stored_data = get_application_element_content(api, element_path)

# Access BOM sessions
frc_data = stored_data.get("frcDesignAppBomData", {})
bom_sessions = frc_data.get("bomSessions", {})

# Check for existing analysis
if assembly_element_id in bom_sessions:
    existing_analysis = bom_sessions[assembly_element_id]
    print(f"Found existing analysis from {existing_analysis['analyzedBy']}")
else:
    print("No existing analysis found")
```

#### 5. Collaborative Workflow Pattern

**Purpose**: Enable multiple users to access the same BOM analysis

**Implementation Pattern**:
```python
def get_or_create_bom_storage(api, instance_path, assembly_element_id):
    """Get existing BOM storage or create new one for collaborative access"""
    
    # 1. List existing application elements
    all_elements = list_document_elements(api, instance_path)
    app_elements = [elem for elem in all_elements if elem.get("elementType") == "APPLICATION"]
    
    # 2. Look for existing FRC Design App elements
    frc_elements = [elem for elem in app_elements if "FRC Design App" in elem.get("name", "")]
    
    if frc_elements:
        # Use existing element
        app_element_id = frc_elements[0]["id"]
        element_path = ElementPath(instance_path.document_id, instance_path.wvm_id, app_element_id, instance_path.wvm)
        
        # Load existing data
        try:
            stored_data = get_application_element_content(api, element_path)
            return element_path, stored_data
        except Exception:
            # Element exists but no data yet
            return element_path, {}
    else:
        # Create new element
        result = create_application_element(api, instance_path, name="FRC Design App BOM Storage")
        app_element_id = result["id"]
        element_path = ElementPath(instance_path.document_id, instance_path.wvm_id, app_element_id, instance_path.wvm)
        return element_path, {}

def store_bom_analysis(api, element_path, assembly_element_id, analysis_results, user_email):
    """Store new BOM analysis results"""
    
    # Load existing data
    try:
        existing_data = get_application_element_content(api, element_path)
    except Exception:
        existing_data = {}
    
    # Update with new analysis
    frc_data = existing_data.get("frcDesignAppBomData", {
        "version": "1.0",
        "bomSessions": {}
    })
    
    frc_data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    frc_data["bomSessions"][assembly_element_id] = {
        "bomData": analysis_results,
        "lastAnalyzed": datetime.now(timezone.utc).isoformat(),
        "analyzedBy": user_email
    }
    
    # Store updated data
    updated_data = {"frcDesignAppBomData": frc_data}
    return store_structured_data(api, element_path, updated_data, "bomData")
```

## Authentication

1. **Primary**: OAuth authentication (matches production app)
2. **Fallback**: API key authentication (for compatibility)

```python
try:
    api = connect.get_api(db)  # OAuth
    logger.info("Using OAuth-authenticated API")
except Exception as oauth_error:
    api = get_onshape_api()    # API key fallback
    logger.warning(f"OAuth failed, using API keys: {oauth_error}")
```

## Migration Plan

### Phase 1: Validation (Current)
- [x] Implement AppElement API endpoints
- [x] Create test infrastructure
- [x] Validate basic create/list operations
- [ ] Debug and fix complete workflow
- [ ] Test all CRUD operations end-to-end

### Phase 2: Integration
- [ ] Update main BOM processing to check for existing structured storage
- [ ] Implement fallback: create structured storage if none exists
- [ ] Add collaborative access patterns
- [ ] Update UI to show collaboration indicators

### Phase 3: Migration
- [ ] Migrate existing Firestore data (optional)
- [ ] Update all BOM workflows to use structured storage
- [ ] Remove Firestore dependencies
- [ ] Clean up test infrastructure

### Phase 4: Enhancement
- [ ] Add user presence indicators
- [ ] Implement conflict resolution for concurrent edits
- [ ] Add version history for BOM changes
- [ ] Performance optimization for large documents

## Development Notes

### API Path Construction

Onshape uses different path structures for different operations:

```python
# Document-level operations (list elements)
/documents/d/{did}/w/{wid}/elements

# Workspace-level AppElement operations (create)
/appelements/d/{did}/w/{wid}  

# Element-level AppElement operations (content CRUD)
/appelements/d/{did}/w/{wid}/e/{eid}/content
```

### Error Handling

Common issues and solutions:

- **404 "Not found"**: Usually incorrect API path structure
- **405 "Method not allowed"**: Wrong HTTP method or API version mismatch
- **401 "Unauthorized"**: Authentication failure, check OAuth/API key setup

### Debugging

The test interface includes extensive logging:

```python
logger.info(f"Constructed API path: {constructed_path}")
logger.info(f"Full API base URL: {api._base_url}")
logger.info(f"Expected URL: {api._base_url}{constructed_path}")
```

## Security Considerations

- Application elements are document-scoped (workspace/version level)
- Access controlled by Onshape document permissions
- No sensitive data should be stored in BOM metadata
- API keys should never be logged or exposed

## Performance Considerations

- List operations return all document elements (can be large)
- Filter application elements on client side when possible
- Consider pagination for documents with many elements
- Cache application element IDs to avoid repeated lookups

## Cleanup

Before production deployment:

1. Remove test endpoints from `backend/endpoints/structured_storage_test.py`
2. Remove test UI component `frontend/src/structured-storage-test/structured-storage-test.tsx`
3. Remove test route registration
4. Clean up debug logging statements
5. Update documentation with final implementation details

---

*Generated: 2025-01-28*
*Status: Phase 1 (Validation) - Create/List operations working, Workflow test needs debugging*