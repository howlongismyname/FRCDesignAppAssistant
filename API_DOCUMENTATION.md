# API Documentation

## Design Assistant Endpoints

The Design Assistant provides BOM (Bill of Materials) analysis functionality for Onshape assemblies.

### Base URL

All Design Assistant endpoints are prefixed with `/app/designassistant`

### Authentication

All endpoints require valid OAuth2 authentication with Onshape.

### Endpoints

#### POST /app/designassistant/ingest

Ingest raw BOM JSON data from Onshape for analysis.

**Request Body:**

```json
{
  "bomTable": {
    "headers": [...],
    "rows": [...]
  }
}
```

**Response:**

```json
{
    "success": true,
    "message": "BOM data ingested successfully",
    "summary": {
        "total_weight_lb": 12.964,
        "parts_analyzed": 117,
        "missing_material_count": 2
    }
}
```

**Error Response:**

```json
{
    "error": "ClientException",
    "message": "No BOM data provided",
    "status_code": 400
}
```

#### GET /app/designassistant/metrics/weight

Retrieve weight metrics from ingested BOM data.

**Response:**

```json
{
    "unit": "lb",
    "total_weight": 12.964,
    "rows_counted": 117,
    "rows_skipped": 2
}
```

**Error Response:**

```json
{
    "error": "ClientException",
    "message": "No BOM data available. Please ingest BOM data first.",
    "status_code": 400
}
```

#### GET /app/designassistant/reports/missing-material

Retrieve a report of parts missing material assignments.

**Response:**

```json
[
    {
        "item": "2.3",
        "name": "frame_left_tube",
        "quantity": 1,
        "part_number": null,
        "mass_lb": 0.616124,
        "document": {
            "documentId": "abc123",
            "workspaceId": "def456",
            "elementId": "ghi789",
            "partId": "jkl012"
        }
    }
]
```

**Error Response:**

```json
{
    "error": "ClientException",
    "message": "No BOM data available. Please ingest BOM data first.",
    "status_code": 400
}
```

#### GET /app/designassistant/available-documents

Get available documents for design assistant analysis. This endpoint fetches BOM data directly from Onshape and processes it.

**Query Parameters:**

-   `documentId` (required): Onshape document ID
-   `instanceType` (optional): Instance type (w/v/m), defaults to "w"
-   `instanceId` (required): Instance ID
-   `elementId` (required): Element ID
-   `elementType` (optional): Element type, defaults to "ASSEMBLY"

**Response:**

```json
{
    "params": {
        "documentId": "abc123",
        "instanceId": "def456",
        "instanceType": "w",
        "elementId": "ghi789",
        "elementType": "ASSEMBLY"
    },
    "summary": {
        "totalMass": 12.964,
        "totalParts": 117,
        "missingMaterial": 2
    },
    "documents": [
        {
            "occurrenceId": "2.3",
            "partId": "jkl012",
            "missingMaterial": true,
            "mass": 0.616124,
            "material": null
        }
    ]
}
```

#### GET /app/designassistant/thumbnails/d/{document_id}/{instance_type}/{instance_id}/e/{element_id}

Get thumbnail for a specific element (placeholder implementation).

**Path Parameters:**

-   `document_id`: Document ID
-   `instance_type`: Instance type (w/v/m)
-   `instance_id`: Instance ID
-   `element_id`: Element ID

**Response:**

```json
{
    "error": "Thumbnail endpoint not yet implemented"
}
```

### Data Processing Rules

#### Mass Parsing

-   Supports units: lb, lbs, pound(s), kg, g
-   Converts all units to pounds (lb)
-   Defaults to pounds if unit is unrecognized
-   Skips rows with mass "N/A" or empty

#### Material Detection

-   String materials: non-empty strings are considered valid
-   Object materials: must have `displayName` or `id` property
-   Null/undefined materials: considered missing

#### Quantity Handling

-   Numeric values only
-   Defaults to 1 if not specified
-   Skips rows with quantity 0

#### Subassembly Handling

-   Only includes subassemblies that carry mass
-   Respects multi-level BOM structure

### Error Handling

All endpoints return appropriate HTTP status codes:

-   `200`: Success
-   `400`: Client error (bad request, missing data)
-   `401`: Unauthorized (OAuth token expired/invalid)
-   `500`: Server error

### Rate Limiting

No specific rate limiting implemented. Respects Onshape API rate limits.

### Caching

BOM data is stored in Flask session for the duration of the user session.

### Example Usage

1. **Ingest BOM Data:**

    ```bash
    curl -X POST /app/designassistant/ingest \
      -H "Content-Type: application/json" \
      -d @bom_data.json
    ```

2. **Get Weight Metrics:**

    ```bash
    curl /app/designassistant/metrics/weight
    ```

3. **Get Missing Material Report:**

    ```bash
    curl /app/designassistant/reports/missing-material
    ```

4. **Analyze Assembly Directly:**
    ```bash
    curl "/app/designassistant/available-documents?documentId=abc123&instanceId=def456&elementId=ghi789"
    ```
