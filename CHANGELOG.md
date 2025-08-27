# Changelog

## [2024-08-26] Design Assistant 403 Error Fix & Code Refactoring

### 🐛 Bug Fixes

-   **Resolved 403 error** in Design Assistant by using Standard App ID mapping
-   **Fixed authentication parity** between Standard App and Design Assistant flows
-   **Eliminated URL construction mismatches** that caused Onshape API failures

### 🔧 Code Refactoring

-   **Divided monolithic backend** into modular service files:
    -   `services/onshape_ids.py` - Shared ID extraction, validation, and normalization
    -   `services/onshape_client.py` - Shared API calls for element pre-flight and BOM fetch
    -   `endpoints/design_assistant.py` - Streamlined route handler using services
-   **Reduced code duplication** by extracting common functionality
-   **Enforced single responsibility** per module with functions under 50 lines
-   **Eliminated dead code** and commented segments

### ✨ New Features

-   **Structured error responses** for pre-flight failures (400) and validation errors (422)
-   **Pre-flight existence checks** using `/elements/...` endpoint before BOM calls
-   **Retry mechanism** for BOM 403 errors with single retry after wvm normalization
-   **Comprehensive logging** for debugging without exposing sensitive data

### 🏗️ Architecture Improvements

-   **Shared services layer** accessible to both Standard App and Design Assistant
-   **Consistent ID mapping** ensuring byte-equal URL construction in both modes
-   **Unified authentication** using Standard App's OAuth client and token store
-   **Modular design** with clear separation of concerns

### 🧪 Testing

-   **Enhanced test coverage** for all new service functions
-   **URL parity tests** ensuring identical API path construction
-   **Error handling tests** for pre-flight failures and retry logic
-   **No regression** in Standard App functionality

### 📊 Code Quality

-   **Reduced cyclomatic complexity** to under 10 per function
-   **Consistent error handling** with structured JSON responses
-   **Improved logging** with INFO level for URLs and ERROR for failures
-   **Type hints** and comprehensive docstrings throughout

### 🔒 Security & Performance

-   **Element type validation** preventing processing of non-assembly elements
-   **Access verification** before expensive BOM operations
-   **Efficient retry logic** with single attempt limit
-   **Session-based caching** for BOM data

### 📝 API Changes

#### New Error Response Format

**400 Pre-flight Failure:**

```json
{
  "error": "PreFlightFailed",
  "reason": "403 Forbidden" | "404 Not Found",
  "ids": {
    "documentId": "string",
    "wvm": "w" | "v",
    "wvmid": "string",
    "elementId": "string"
  },
  "mode": "Standard App" | "Design Assistant"
}
```

**422 Validation Error:**

```json
{
  "error": "InvalidElementType",
  "expected": "ASSEMBLY",
  "got": "string",
  "ids": {
    "documentId": "string",
    "elementId": "string"
  },
  "mode": "Standard App" | "Design Assistant"
}
```

### 🚀 Migration Notes

-   **No breaking changes** to existing Standard App functionality
-   **Design Assistant endpoints** now return structured error responses
-   **Shared services** can be used by other parts of the application
-   **Backward compatibility** maintained for all existing integrations

### 📁 Files Modified

-   `backend/services/onshape_ids.py` - New shared ID service
-   `backend/services/onshape_client.py` - New shared API client service
-   `backend/services/__init__.py` - Package initialization
-   `backend/endpoints/design_assistant.py` - Refactored to use services
-   `tests/test_services.py` - New comprehensive service tests
-   `tests/test_bom_analysis.py` - Updated imports and test cases
-   `tests/test_routing.py` - Enhanced URL parity testing

### 🎯 Acceptance Criteria Met

-   ✅ Design Assistant successfully calls Onshape and retrieves BOM for ASSEMBLY elements
-   ✅ Standard App functionality unchanged
-   ✅ Net code size reduced through modularization
-   ✅ All syntax checks pass
-   ✅ URL construction parity between modes achieved
-   ✅ Structured error responses implemented
-   ✅ Retry logic for 403 errors implemented
-   ✅ Comprehensive logging and debugging added

### 🔍 Technical Details

-   **ID Mapping**: `{did}` ← `documentId`, `{wvm}` ← normalized `instanceType`, `{wvmid}` ← `instanceId`, `{eid}` ← `elementId`
-   **Instance Type Normalization**: Case-insensitive mapping of WORKSPACE→w, VERSION→v
-   **Pre-flight Endpoint**: `GET /api/v12/elements/d/{did}/{wvm}/{wvmid}/e/{eid}`
-   **BOM Endpoint**: `GET /api/v12/assemblies/d/{did}/{wvm}/{wvmid}/e/{eid}/bom` with fixed query parameters
-   **Retry Logic**: Single retry with original instance type on BOM 403 errors
-   **Error Logging**: Token audience, scope, tenant (without exposing sensitive data)

The Design Assistant now uses identical authentication and ID extraction logic as the Standard App, eliminating the 403 error while maintaining clean, maintainable code architecture.
