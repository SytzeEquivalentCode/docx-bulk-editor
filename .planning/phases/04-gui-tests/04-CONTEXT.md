# Phase 4: GUI Tests - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate UI components using pytest-qt for user interactions. Tests cover MainWindow (file selection, operation switching, job start/cancel), ProgressDialog (updates, elapsed time, cancellation), and HistoryWindow (job listing, filtering, result views). Worker thread integration testing belongs in Phase 5 (Integration & E2E).

</domain>

<decisions>
## Implementation Decisions

### Test Isolation Strategy
- Always mock workers in GUI tests — workers tested separately in integration phase
- Use in-memory SQLite per test via existing `test_db` fixture — each test gets fresh isolated database
- Use `docx_factory` fixture for test documents — programmatic test docs in temp dirs
- Use pytest-qt's `qtbot.waitSignal` and `waitUntil` for timing — no arbitrary sleeps

### Claude's Discretion
- Specific mock implementations for workers
- Test class organization within files
- Helper fixture design for common UI setup patterns
- Which edge cases warrant dedicated tests vs parameterized tests

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard pytest-qt patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-gui-tests*
*Context gathered: 2026-01-30*
