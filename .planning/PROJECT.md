# DOCX Bulk Editor - Test Suite

## What This Is

A comprehensive test suite validating all functionality of the DOCX Bulk Editor application. Tests serve as living documentation of expected behavior, covering document processors, core infrastructure, UI components, and end-to-end workflows.

## Core Value

Every user-facing feature has a test that documents and validates its correct behavior.

## Requirements

### Validated

- ✓ Search & Replace processor — existing (`src/processors/search_replace.py`)
- ✓ Metadata processor — existing (`src/processors/metadata.py`)
- ✓ Table Formatter processor — existing (`src/processors/table_formatter.py`)
- ✓ Style Enforcer processor — existing (`src/processors/style_enforcer.py`)
- ✓ Validator processor — existing (`src/processors/validator.py`)
- ✓ Configuration management — existing (`src/core/config.py`)
- ✓ Backup management — existing (`src/core/backup.py`)
- ✓ Logging infrastructure — existing (`src/core/logger.py`)
- ✓ Database layer — existing (`src/database/db_manager.py`)
- ✓ Main window UI — existing (`src/ui/main_window.py`)
- ✓ Progress dialog — existing (`src/ui/progress_dialog.py`)
- ✓ History window — existing (`src/ui/history_window.py`)
- ✓ Job worker thread — existing (`src/workers/job_worker.py`)

### Active

- [ ] Fix test infrastructure (import issues preventing test collection)
- [ ] Unit tests for Search & Replace processor (all behaviors)
- [ ] Unit tests for Metadata processor (all behaviors)
- [ ] Unit tests for Table Formatter processor (all behaviors)
- [ ] Unit tests for Style Enforcer processor (all behaviors)
- [ ] Unit tests for Validator processor (all behaviors)
- [ ] Unit tests for ConfigManager (load, save, defaults, validation)
- [ ] Unit tests for BackupManager (create, restore, cleanup)
- [ ] Unit tests for Logger (setup, rotation, encoding)
- [ ] Unit tests for DatabaseManager (CRUD, transactions, migrations)
- [ ] GUI tests for MainWindow (file selection, operation switching, start/cancel)
- [ ] GUI tests for ProgressDialog (updates, cancellation, completion)
- [ ] GUI tests for HistoryWindow (job listing, result viewing)
- [ ] Integration tests for JobWorker (orchestration, pool management, signals)
- [ ] E2E tests for full processing workflows (file → processor → result)
- [ ] Programmatic test document generation fixtures

### Out of Scope

- Performance benchmarking — behavior validation only, not speed metrics
- Stress testing — focus on correctness, not load handling
- Cross-platform testing — Windows only for this effort
- Visual regression testing — functional behavior only

## Context

**Current Test State:**
- 19 test files exist across unit/, integration/, gui/, performance/
- Tests fail to collect due to `ModuleNotFoundError: No module named 'src'`
- pytest, pytest-qt, pytest-cov already configured in requirements-dev.txt
- Test infrastructure exists but is broken

**Test Framework:**
- pytest 9.0.1 with pytest-qt 4.5.0 for GUI testing
- pytest-cov for coverage reporting
- pytest-mock for mocking
- Fixtures generate test documents programmatically via python-docx

**Architecture Considerations:**
- Processors are multiprocessing-compatible (module-level functions)
- UI tests need QApplication instance (qapp fixture)
- Worker tests may need mocked multiprocessing pools
- Database tests should use in-memory SQLite

## Constraints

- **Python**: 3.11+ (tested on 3.13.7)
- **Framework**: PySide6 6.10.1 for Qt testing
- **Encoding**: All file operations must use UTF-8 (Windows critical)
- **Isolation**: Tests must not modify production database or files

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix existing tests before expanding | Existing tests represent prior knowledge; don't discard | — Pending |
| Generate test docs programmatically | Reproducible, version-controlled, no binary files in repo | — Pending |
| Behavior coverage over line coverage | Tests document "what should happen", not just "code runs" | — Pending |

---
*Last updated: 2026-01-30 after initialization*
