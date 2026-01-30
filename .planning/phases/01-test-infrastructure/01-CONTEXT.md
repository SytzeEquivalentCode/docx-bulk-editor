# Phase 1: Test Infrastructure - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the broken test environment so pytest collects tests without import errors. Establish programmatic test document generation via fixtures and provide isolated SQLite instances for database tests.

</domain>

<decisions>
## Implementation Decisions

### docx_factory fixture
- Core elements only: paragraphs, headings, basic text
- Returns file path (Path object), not Document object — matches how processors work
- Creates files in pytest's tmp_path — auto-cleaned
- Content as plain text with \n for paragraph breaks — easy to use
- Optional metadata parameter: docx_factory(metadata={'author': 'Test'})

### Test document complexity
- docx_factory only — no pre-generated sample files
- Defer tables/headers/footers support to Phase 2 when processors need it
- Full validation: verify created files open without errors in python-docx

### Database isolation
- In-memory SQLite only (":memory:") — fastest, fully isolated
- Function scope — fresh database per test, full isolation
- Auto-create schema — fixture returns ready-to-use database with all tables

### Import structure
- conftest.py adds src/ to sys.path — no install step needed
- Absolute imports: `from src.processors import search_replace`
- Add __init__.py to src/ and all subdirectories — full package structure

### Claude's Discretion
- Whether to include a job_factory fixture for pre-populating test data (decide based on test complexity in Phase 2+)
- Exact error messages for validation failures
- conftest.py organization (single file vs split)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard pytest patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-test-infrastructure*
*Context gathered: 2026-01-30*
