# Phase 5: Integration & E2E Tests - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Full workflow validation with cross-component integration tests. Tests verify that UI, workers, processors, database, and backup systems work together correctly. This phase validates the "glue" between components that were tested individually in prior phases.

</domain>

<decisions>
## Implementation Decisions

### Workflow Coverage
- Test all 5 processors with full E2E workflows (search_replace, metadata, table_formatter, style_enforcer, validator)
- Use medium batch sizes (10-20 documents) for realistic multi-file handling
- Start tests from full UI flow (MainWindow → ProgressDialog → results) — not worker layer
- Verify both file changes AND database records (job tracking, history) for complete validation

### Failure Scenarios
- Use corrupt/invalid documents to trigger real processor errors (not mock injection)
- Expected behavior on partial failure: continue processing all files, collect errors, report summary at end
- Verify failed files are NOT modified — compare to original or confirm restored from backup
- Test user-initiated cancellation: verify partial results saved, no corruption, proper status

### Component Boundaries
- Database: In-memory SQLite (fast, isolated, same schema as production)
- Backups: Real backup operations to temp directory — test actual backup/restore functionality
- Processors: In-process execution (not multiprocessing pool) — faster, easier to debug
- Threading: Qt signal spying with qtbot.waitSignal() for proper async testing

### Test Environment
- Complete isolated workspace per test (data/, backups/, logs/ directories)
- Generate test documents programmatically via docx_factory fixture
- Design for parallel execution (pytest-xdist compatible with -n auto)
- 60-second timeout per test to catch hangs

### Claude's Discretion
- Specific corrupt document types to create (malformed XML, locked files, etc.)
- Exact number of documents per test within 10-20 range
- Signal timeout values for qtbot.waitSignal()
- Cleanup strategy implementation details

</decisions>

<specifics>
## Specific Ideas

- Tests should verify the complete user journey: select files → configure operation → start → progress updates → completion → view results in history
- Cancellation test should verify mid-processing cancel doesn't leave documents in corrupted state
- Database verification should check job status transitions (pending → running → completed/failed)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-integration-e2e-tests*
*Context gathered: 2026-02-01*
