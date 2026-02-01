---
phase: 04-gui-tests
plan: 01
subsystem: testing
tags: [pytest-qt, PySide6, GUI testing, monkeypatch, QFileDialog]

# Dependency graph
requires:
  - phase: 01-test-infrastructure
    provides: pytest-qt fixtures, conftest.py with qapp and docx_factory
provides:
  - TestMainWindowFileSelection class with 5 tests for file dialog mocking
  - TestMainWindowOperationSwitching class with 4 tests for UI panel switching
  - TestMainWindowJobValidation class with 4 tests for job flow validation
affects: [04-02-ProgressDialog-tests, 04-03-HistoryWindow-tests, integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "monkeypatch for non-blocking QFileDialog/QMessageBox in GUI tests"
    - "Test classes organized by feature area (file selection, operation switching, validation)"

key-files:
  created: []
  modified:
    - tests/gui/test_main_window.py

key-decisions:
  - "Use monkeypatch.setattr() for mocking QFileDialog and QMessageBox to avoid blocking tests"
  - "Organize new tests into classes (TestMainWindowFileSelection, etc.) while keeping original 9 tests as module-level functions for backward compatibility"
  - "Test operation panel switching by checking widget attributes (hasattr) rather than inspecting layout"

patterns-established:
  - "Mock file dialogs by replacing getOpenFileNames/getExistingDirectory with lambda returning test paths"
  - "Mock message boxes by capturing calls in a list for assertion, avoiding actual dialog display"
  - "Use qtbot.addWidget() for every window instance to ensure proper cleanup"

# Metrics
duration: 19min
completed: 2026-02-01
---

# Phase 04 Plan 01: MainWindow Extended Tests Summary

**Comprehensive MainWindow GUI test coverage: file selection dialogs, operation switching, and job validation with pytest-qt monkeypatch patterns**

## Performance

- **Duration:** 19 min
- **Started:** 2026-02-01T09:30:11Z
- **Completed:** 2026-02-01T09:49:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added 13 new tests to test_main_window.py (from 10 to 22 total tests)
- Complete coverage of GUI-01 (file selection) and GUI-02 (job validation) requirements
- All tests use non-blocking dialog mocking patterns from pytest-qt best practices

## Task Commits

Each task was committed atomically:

1. **Task 1: Add file selection and operation switching tests** - `d510eee` (test)
   - TestMainWindowFileSelection: 5 tests for file dialogs
   - TestMainWindowOperationSwitching: 4 tests for operation panels

2. **Task 2: Add job flow validation tests** - `47b5254` (test)
   - TestMainWindowJobValidation: 4 tests for validation logic

## Files Created/Modified
- `tests/gui/test_main_window.py` - Extended with 13 new tests in 3 test classes

## Decisions Made

**1. Monkeypatch for dialog mocking**
- Rationale: Modal dialogs (QFileDialog, QMessageBox) block test execution. Monkeypatch provides clean, non-blocking alternatives.
- Pattern: `monkeypatch.setattr(QFileDialog, 'getOpenFileNames', lambda *args: (paths, ''))`

**2. Class organization for new tests**
- Rationale: Group related tests into classes for better organization and markers. Keeps existing module-level tests unchanged.
- Benefit: Easier to run subsets like `pytest -k TestMainWindowFileSelection`

**3. Widget attribute checking for panel verification**
- Rationale: After operation switching, verify config panel changed by checking widget attributes (e.g., `hasattr(window, 'validate_heading_check')`)
- Alternative considered: Inspect layout children - rejected as brittle to implementation changes

## Deviations from Plan

**Auto-fixed Issues**

**1. [Rule 3 - Blocking] Missing QFileDialog import**
- **Found during:** Task 1 test execution
- **Issue:** NameError: name 'QFileDialog' is not defined - tests failed immediately
- **Fix:** Added `QFileDialog` to imports: `from PySide6.QtWidgets import QMessageBox, QFileDialog`
- **Files modified:** tests/gui/test_main_window.py
- **Verification:** All tests passed after adding import
- **Committed in:** d510eee (part of Task 1 commit)

**2. [Rule 1 - Bug] Incorrect MagicMock re-import in test**
- **Found during:** Task 2 test execution (test_close_window_stops_running_worker)
- **Issue:** UnboundLocalError from `from unittest.mock import MagicMock` inside function - shadowed top-level import
- **Fix:** Changed to use existing `Mock` from top-level imports: `cancel_spy = Mock()`
- **Files modified:** tests/gui/test_main_window.py
- **Verification:** Test passed after fix
- **Committed in:** 47b5254 (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking import, 1 bug)
**Impact on plan:** Both auto-fixes were necessary for tests to run. No scope creep.

## Issues Encountered

None - plan executed smoothly after auto-fixes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next plans:**
- ProgressDialog tests (04-02) can use same monkeypatch patterns
- HistoryWindow tests (04-03) can use same class organization approach
- Integration tests can build on MainWindow test patterns

**Coverage metrics:**
- MainWindow coverage improved from ~38% to ~69% with these tests
- GUI test suite now has 22 tests total in test_main_window.py

---
*Phase: 04-gui-tests*
*Completed: 2026-02-01*
