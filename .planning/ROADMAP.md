# Roadmap: DOCX Bulk Editor Test Suite

## Overview

Build comprehensive test coverage for the DOCX Bulk Editor application, validating all functionality from document processors through core infrastructure to GUI components. Tests serve as living documentation of expected behavior, ensuring every user-facing feature has automated validation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Test Infrastructure** - Validate existing test environment and document infrastructure readiness
- [x] **Phase 2: Processor Tests** - Validate all five document processors with comprehensive behavior coverage
- [ ] **Phase 3: Core Infrastructure Tests** - Test configuration, backup, logging, and database layers
- [ ] **Phase 4: GUI Tests** - Validate UI components with pytest-qt for user interactions
- [ ] **Phase 5: Integration & E2E Tests** - Test full workflows and cross-component interactions

## Phase Details

### Phase 1: Test Infrastructure
**Goal**: Tests collect successfully and programmatic document generation is available
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. pytest collects all test files without import errors
  2. docx_factory fixture generates test documents with specified content and structure
  3. in-memory database fixture provides isolated SQLite instances for tests
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Validate existing fixtures and update project state
- [x] 01-02-PLAN.md — Fix pytest pythonpath configuration (gap closure)

### Phase 2: Processor Tests
**Goal**: All document processors validated with comprehensive behavior coverage
**Depends on**: Phase 1
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04, PROC-05, PROC-06
**Success Criteria** (what must be TRUE):
  1. Search & Replace processor handles all replacement scenarios (plain text, regex, case-insensitive) and document locations (paragraphs, tables, headers, footers)
  2. Metadata processor reads and writes all metadata fields correctly
  3. Table Formatter applies formatting rules across various table structures
  4. Style Enforcer standardizes styles according to configuration
  5. Validator reports all validation rule violations accurately
**Plans**: 7 plans

Plans:
- [x] 02-01-PLAN.md — Extend conftest.py with fixture helpers (docx_with_table, docx_with_metadata)
- [x] 02-02-PLAN.md — Create comprehensive table_formatter processor tests
- [x] 02-03-PLAN.md — Consolidate and convert search_replace tests to programmatic docs
- [x] 02-04-PLAN.md — Convert metadata tests to programmatic document generation
- [x] 02-05-PLAN.md — Verify all processor tests pass (checkpoint)
- [x] 02-06-PLAN.md — Validate style_enforcer processor tests (PROC-05)
- [x] 02-07-PLAN.md — Validate validator processor tests (PROC-06)

### Phase 3: Core Infrastructure Tests
**Goal**: Core infrastructure components validated for configuration, backup, logging, and database operations
**Depends on**: Phase 2
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04
**Success Criteria** (what must be TRUE):
  1. ConfigManager loads defaults, saves configurations, and handles missing files correctly
  2. BackupManager creates backups before processing, restores after failures, and cleans up old backups per retention policy
  3. Logger rotates files correctly and uses UTF-8 encoding on Windows
  4. DatabaseManager performs CRUD operations, handles transactions, and applies schema migrations correctly
**Plans**: 4 plans

Plans:
- [ ] 03-01-PLAN.md — Fix failing schema validation test (schema drift)
- [ ] 03-02-PLAN.md — Add error condition tests from CONTEXT.md
- [ ] 03-03-PLAN.md — Add pytest markers for test filtering consistency
- [ ] 03-04-PLAN.md — Verify Phase 3 success criteria (checkpoint)

### Phase 4: GUI Tests
**Goal**: UI components validated for user interactions using pytest-qt
**Depends on**: Phase 3
**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04
**Success Criteria** (what must be TRUE):
  1. MainWindow handles file selection via browse and drag-drop, switches between operations correctly
  2. MainWindow starts and cancels jobs correctly with worker thread integration
  3. ProgressDialog updates progress, displays elapsed time, and handles cancellation
  4. HistoryWindow lists jobs, filters results, and displays detailed result views
**Plans**: TBD

Plans:
- [ ] TBD (after planning)

### Phase 5: Integration & E2E Tests
**Goal**: Full workflows validated with cross-component integration tests
**Depends on**: Phase 4
**Requirements**: E2E-01, E2E-02, E2E-03
**Success Criteria** (what must be TRUE):
  1. Full job workflow executes from file selection through processing to completion without errors
  2. Processor failures are handled gracefully with error reporting and partial completion
  3. Backups are created before processing and can restore files after failures
**Plans**: TBD

Plans:
- [ ] TBD (after planning)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Test Infrastructure | 2/2 | Complete | 2026-01-30 |
| 2. Processor Tests | 7/7 | Complete | 2026-01-30 |
| 3. Core Infrastructure Tests | 0/4 | In Progress | - |
| 4. GUI Tests | 0/TBD | Not started | - |
| 5. Integration & E2E Tests | 0/TBD | Not started | - |
