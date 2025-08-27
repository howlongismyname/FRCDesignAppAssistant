# Design Assistant Hexagonal Architecture Migration

## Overview

This document tracks the migration of the Design Assistant module from a monolithic Flask structure to a clean Hexagonal architecture. The refactor focuses ONLY on Design Assistant functionality while preserving the main FRC catalog app unchanged.

## Current State (Before Migration)

### Backend Endpoints
Located in `/backend/endpoints/design_assistant.py` (715 lines):

#### Core BOM Endpoints
- `POST /ingest` - Ingest raw BOM JSON data and store for analysis
- `GET /bom` - Get BOM data with caching and force refresh capability
- `GET /metrics/weight` - Get weight metrics from ingested BOM data
- `GET /reports/missing-material` - Get parts missing material assignments
- `GET /available-documents` - Get document info and trigger BOM analysis
- `GET /refresh-cooldown` - Check remaining cooldown time for force refresh

#### Utility Endpoints
- `POST /cleanup-sessions` - Clean up old BOM sessions
- `GET /thumbnails/d/<ids>` - Thumbnail endpoint (placeholder)

### Backend Services
Located in `/backend/services/onshape_bom.py` (460 lines):

#### Core Functions
- `process_bom_data(bom_data, document_id)` - Process raw BOM into weight/material analysis
- `fetch_and_process_bom()` - Fetch from Onshape API and process
- `parse_mass(mass_str)` - Convert mass strings to pounds
- `has_material(material)` - Check if part has material assigned

#### Key Features
- Hierarchical BOM processing with parent-child relationships
- Mass calculation for subassemblies from components
- Material detection and missing material flagging
- Support for both legacy and new Onshape API formats
- Unit conversion (kg, g, lb)

### Current Dependencies
- **Storage**: Firestore for BOM session caching
- **Rate Limiting**: Flask session-based 30-second cooldown
- **Auth**: Existing Onshape OAuth flow
- **API Client**: Direct calls to Onshape API endpoints

### Current Issues
1. **Monolithic structure**: Single 715-line endpoint file
2. **Mixed concerns**: Business logic, API handling, caching all mixed
3. **Heavy Firestore dependency**: Could live in Onshape Structured Storage
4. **No error recovery**: Limited retry/circuit breaker patterns
5. **Difficult testing**: Tightly coupled components
6. **No webhook support**: Manual refresh only

### Frontend Components
Located in `/frontend/src/design-assistant/`:

#### Main Components
- `design-assistant.tsx` - Entry point component
- `design-assistant-home.tsx` - Core logic and data processing
- `design-assistant-card.tsx` - Individual part/assembly cards

#### Feature Components (in `components/` directory)
- `design-assistant-content.tsx` - Main content area
- `design-assistant-parts-list.tsx` - Hierarchical parts display
- `design-assistant-summary.tsx` - Summary statistics
- `design-assistant-header.tsx` - Header with cache info
- `design-assistant-debug.tsx` - Debug panel
- `design-assistant-error.tsx` - Error display
- `design-assistant-loading.tsx` - Loading state
- `design-assistant-no-parts.tsx` - Empty state

#### Current Queries
- `useDesignAssistantDocumentsQuery` - Fetch document analysis
- `useBomDataQuery` - Fetch BOM data with caching
- `useRefreshCooldownQuery` - Check refresh cooldown

## Target State (After Migration)

### New Backend Structure
```
/backend/app/
├── domain/
│   ├── bom.py              # BOM aggregates, Part/Assembly entities
│   ├── geometry.py         # Mass properties, unit conversion
│   ├── status.py           # Manufacturing status state machine  
│   ├── strategies.py       # Part classification (plate, shaft, tube)
│   └── errors.py           # Domain-specific exceptions
├── application/
│   ├── dto.py              # Request/response DTOs with Pydantic v2
│   ├── commands.py         # Use case commands
│   ├── services.py         # Application services
│   └── query.py            # Read-side query handlers
├── adapters/
│   ├── onshape_client.py   # Onshape API facade
│   ├── metadata_adapter.py # Onshape metadata operations
│   ├── storage_adapter.py  # Structured storage (replace Firestore)
│   ├── webhook_dispatcher.py # Webhook to command dispatch
│   └── cache_adapter.py    # Thin cache layer
├── infrastructure/
│   ├── http.py             # httpx client with retry/circuit breaker
│   ├── auth.py             # Onshape OAuth handling
│   ├── config.py           # Environment configuration
│   └── tasks.py            # Background task infrastructure
└── interfaces/
    ├── api.py              # Flask blueprints (DA endpoints only)
    ├── webhooks.py         # Webhook endpoints
    └── schemas.py          # API schemas
```

### Key Use Cases
1. **RefreshBomCache** - Core BOM analysis and caching
2. **GenerateThumbnails** - Generate and store part thumbnails
3. **BulkUpdateMetadata** - Batch update part metadata
4. **BuildFabPack** - Export fabrication packages

### New Capabilities
- Thumbnail generation and storage in Blob Elements
- Bulk metadata editing with batching and retries
- Fabrication package export pipeline
- Webhook-driven updates
- Idempotent operations with recovery

## Migration Phases

### Phase 1: Architecture Setup ✅
- [x] Create MIGRATION.md
- [ ] Create new directory structure
- [ ] Define domain models and ports
- [ ] Set up dependency injection container

### Phase 2: Core Migration
- [ ] Migrate RefreshBomCache use case (highest priority)
- [ ] Replace Firestore with Structured Storage
- [ ] Update rate limiting to use retry/backoff patterns
- [ ] Add webhook endpoint infrastructure

### Phase 3: New Capabilities
- [ ] Implement GenerateThumbnails use case
- [ ] Add BulkUpdateMetadata use case
- [ ] Add BuildFabPack use case
- [ ] Consolidate debug panels into diagnostics endpoint

### Phase 4: Frontend Updates
- [ ] Update API calls to use new command-based endpoints
- [ ] Add thumbnail display capabilities
- [ ] Add bulk edit UI
- [ ] Add fab pack UI

### Phase 5: Testing & Documentation
- [ ] Add unit tests for domain logic
- [ ] Add integration tests with Onshape client mocks
- [ ] Add E2E tests for key use cases
- [ ] Complete migration documentation

## Backward Compatibility

### API Compatibility
- Existing endpoint URLs preserved during transition
- Response schemas unchanged where possible
- Feature flags for new capabilities during rollout

### Data Migration
- BOM cache migrated from Firestore to Structured Storage
- Session data preserved during transition period
- Fallback to legacy storage during migration

## Success Metrics

### Technical
- [ ] All existing DA functionality works unchanged
- [ ] Main FRC catalog app unaffected
- [ ] Test coverage >80% for new architecture
- [ ] Performance equivalent or better
- [ ] All lint and type checks pass

### Operational
- [ ] Reduced external dependencies
- [ ] Better error handling and recovery
- [ ] Simplified debugging with consolidated diagnostics
- [ ] Webhook automation working

## Rollback Plan

If migration fails, rollback involves:
1. Revert to original endpoint file
2. Restore Firestore session storage
3. Re-enable legacy rate limiting
4. Remove new directory structure

Original files preserved as `.legacy` during migration.