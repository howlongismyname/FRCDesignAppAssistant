# Debugging the 404 "Not Found" Error

## Problem Summary

Your FRC Design App Assistant is encountering a 404 "Not found" error when trying to analyze an assembly. The error occurs in the `analyze_assembly_for_missing_materials` function when calling the Onshape API to get assembly definitions.

## Error Details

-   **Error Type**: 404 Not Found
-   **Location**: `backend/endpoints/design_assistant.py` line 89
-   **API Call**: `assemblies.get_assembly_definition(api, element_path)`
-   **Root Cause**: The Onshape API cannot find the requested assembly

## Possible Causes

### 1. Invalid or Malformed Parameters

-   Document ID, Instance ID, or Element ID might be incorrect
-   Instance type might be wrong (workspace vs version vs microversion)
-   Parameters might be getting corrupted during transmission

### 2. Access Permissions

-   The user might not have access to the requested document
-   The document might be private or restricted
-   OAuth token might be expired or invalid

### 3. Document State Issues

-   The document might have been deleted or moved
-   The element might not exist in the specified instance
-   The assembly might have been converted to a different type

## Debugging Steps

### Step 1: Check the Debug Output

I've added extensive debugging to the backend. Check your Flask application logs for:

```
DEBUG: Received parameters:
  elementType: ASSEMBLY
  documentId: [your-document-id]
  instanceType: [your-instance-type]
  instanceId: [your-instance-id]
  elementId: [your-element-id]
```

### Step 2: Test the Debug Endpoints

Use these new endpoints to isolate the issue:

#### Test Path Construction

```
GET /app/designassistant/debug-path?elementType=ASSEMBLY&documentId=[id]&instanceType=[type]&instanceId=[id]&elementId=[id]
```

This will show you exactly how the path is being constructed without making API calls.

#### Test API Connection

```
GET /app/designassistant/test-api
```

This will verify that your Onshape API connection is working.

### Step 3: Verify Parameters in Frontend

Check the browser console for debug logs:

```
DEBUG: Sending design assistant query with parameters: {...}
DEBUG: Making request to URL: /app/designassistant/available-documents?...
```

### Step 4: Run the Debug Script

I've created a `debug_onshape.py` script that you can run to test:

-   API connection
-   Path construction
-   Basic API calls

```bash
python debug_onshape.py
```

## Common Issues and Solutions

### Issue: Invalid Document ID

**Symptoms**: 404 error with "document not found"
**Solution**: Verify the document ID from the Onshape URL

### Issue: Wrong Instance Type

**Symptoms**: 404 error with "instance not found"
**Solution**: Check if you're using:

-   `w` for workspace
-   `v` for version
-   `m` for microversion

### Issue: Element Doesn't Exist

**Symptoms**: 404 error with "element not found"
**Solution**: Verify the element ID exists in the specified instance

### Issue: OAuth Token Expired

**Symptoms**: 401 or 403 errors
**Solution**: Re-authenticate with Onshape

## How to Get Correct Parameters

### From Onshape URL

When viewing your assembly in Onshape, the URL looks like:

```
https://cad.onshape.com/documents/[documentId]/[instanceType]/[instanceId]/e/[elementId]
```

### Example URL Breakdown

```
https://cad.onshape.com/documents/1234567890abcdef12345678/w/876543210fedcba09876543/e/abcdef1234567890abcdef12
```

-   Document ID: `1234567890abcdef12345678`
-   Instance Type: `w` (workspace)
-   Instance ID: `876543210fedcba09876543`
-   Element ID: `abcdef1234567890abcdef12`

## Next Steps

1. **Check the debug logs** in your Flask application
2. **Test the debug endpoints** to isolate the issue
3. **Verify the parameters** being sent from the frontend
4. **Run the debug script** to test API connectivity
5. **Check Onshape permissions** for the document you're trying to access

## Additional Debugging

If the issue persists, you can also:

-   Check the Onshape API documentation for the specific endpoint
-   Verify the assembly actually exists and is accessible
-   Test with a different, simpler document to isolate the issue
-   Check if there are any Onshape API rate limits or restrictions

## Files Modified

I've added debugging to these files:

-   `backend/endpoints/design_assistant.py` - Added debug logging and error handling
-   `frontend/src/queries.ts` - Added console logging
-   `debug_onshape.py` - Created debug script

The debugging will help identify exactly where the issue is occurring and provide more specific error messages to guide the resolution.
