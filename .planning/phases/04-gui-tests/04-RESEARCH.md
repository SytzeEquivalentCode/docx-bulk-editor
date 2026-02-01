# Phase 4: GUI Tests - Research

**Researched:** 2026-02-01
**Domain:** pytest-qt with PySide6 GUI testing
**Confidence:** HIGH

## Summary

Researched pytest-qt framework for testing PySide6 GUI applications. The standard approach uses the `qtbot` fixture for widget lifecycle management, signal-based waiting mechanisms (`waitSignal`/`waitUntil`) for asynchronous behavior, and monkeypatch-based mocking for blocking dialogs. Existing test infrastructure in `conftest.py` already provides critical fixtures (`qapp`, `test_db`, `test_config`, `docx_factory`).

Key findings:
- pytest-qt handles QApplication lifecycle automatically through `qtbot` fixture
- Signal/slot testing requires `waitSignal()` context managers, NOT arbitrary sleeps
- Modal dialogs MUST be mocked using monkeypatch - cannot interact with actual blocking UI
- Drag-and-drop testing uses QMimeData + simulated QDragEnterEvent/QDropEvent
- Worker thread integration should mock workers completely - real threading tested in Phase 5

**Primary recommendation:** Use pytest-qt's `qtbot` fixture with signal-based waiting and monkeypatch mocking for all GUI tests. Always prefer widget methods (setText, setCurrentIndex) over event simulation for reliability.

## Standard Stack

The established libraries/tools for PySide6 GUI testing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-qt | 4.3.1+ | PySide6/PyQt testing plugin | Official pytest plugin for Qt testing, handles qApp lifecycle |
| PySide6.QtTest | (bundled) | QTest utilities | Official Qt testing module with mouse/keyboard simulation |
| unittest.mock | (stdlib) | Mocking worker threads/dialogs | Standard library mocking, works seamlessly with pytest |
| pytest-mock | 3.12.0+ | pytest-native mocking | Cleaner syntax than unittest.mock, automatic cleanup |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-xvfb | 3.0.0+ | Virtual display for CI | Headless testing in GitHub Actions or other CI environments |
| pytest-cov | 4.1.0+ | GUI code coverage | Measure coverage of UI code paths |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-qt | Raw QTest | pytest-qt provides better fixtures, signal handling, and pytest integration |
| monkeypatch | actual dialog interaction | Interacting with modal dialogs blocks tests; monkeypatch is fast and reliable |
| QTest.mouseClick | widget.method() | Direct widget methods are more reliable than simulated events |

**Installation:**
```bash
# Already in requirements-dev.txt
pip install pytest-qt==4.3.1 pytest-mock==3.12.0
```

## Architecture Patterns

### Recommended Test File Structure
```
tests/gui/
├── __init__.py
├── test_main_window.py          # MainWindow tests (file selection, operations, jobs)
├── test_progress_dialog.py      # ProgressDialog tests (updates, cancellation)
├── test_history_window.py       # HistoryWindow tests (filtering, display)
└── conftest.py (if needed)      # GUI-specific fixtures
```

### Pattern 1: Basic Widget Test with qtbot
**What:** Standard pattern for testing widget initialization and state
**When to use:** All GUI tests that interact with widgets

**Example:**
```python
# Source: pytest-qt official documentation
@pytest.mark.gui
def test_widget_initialization(qtbot, test_config, test_db):
    """Test widget initializes correctly."""
    widget = MainWindow(test_config, test_db)
    qtbot.addWidget(widget)  # Register for cleanup

    # Assert initial state
    assert widget.windowTitle() == "DOCX Bulk Editor v1.0"
    assert widget.start_button.isEnabled() is False
```

### Pattern 2: Signal Waiting for Asynchronous Operations
**What:** Use `qtbot.waitSignal()` to wait for Qt signals instead of arbitrary sleeps
**When to use:** Testing worker threads, timers, delayed UI updates

**Example:**
```python
# Source: pytest-qt signals documentation
@pytest.mark.gui
def test_worker_completion_signal(qtbot, test_config, test_db):
    """Test worker emits completion signal."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Mock worker to avoid real processing
    with patch('src.ui.main_window.JobWorker') as mock_worker_class:
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker

        # Wait for signal with timeout
        with qtbot.waitSignal(mock_worker.job_completed, timeout=5000) as blocker:
            window.start_processing()
            mock_worker.job_completed.emit({"status": "completed"})

        # Verify signal received
        assert blocker.signal_triggered
```

### Pattern 3: Mocking Modal Dialogs
**What:** Use monkeypatch to replace dialog methods with test doubles
**When to use:** Testing QMessageBox, QFileDialog, custom modal dialogs

**Example:**
```python
# Source: pytest-qt dialogs documentation
@pytest.mark.gui
def test_error_dialog_shown(qtbot, test_config, test_db, monkeypatch):
    """Test error shows message box."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Mock QMessageBox.critical to avoid blocking
    critical_calls = []
    def mock_critical(parent, title, message):
        critical_calls.append((title, message))
        return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, 'critical', mock_critical)

    # Trigger error
    window._on_error("Test error message")

    # Verify dialog would have been shown
    assert len(critical_calls) == 1
    assert "Test error message" in critical_calls[0][1]
```

### Pattern 4: Drag-and-Drop Testing
**What:** Simulate drag-and-drop with QMimeData and event objects
**When to use:** Testing file drop zones, drag reordering

**Example:**
```python
# Source: Existing test_main_window.py (verified pattern)
@pytest.mark.gui
def test_drag_drop_files(qtbot, test_config, test_db, docx_factory):
    """Test drag-and-drop file selection."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    test_files = [docx_factory(filename=f"file{i}.docx") for i in range(2)]

    # Create mime data with file URLs
    from PySide6.QtCore import QMimeData, QUrl, QPoint
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(f)) for f in test_files])

    # Simulate drag enter
    drag_enter = QDragEnterEvent(
        QPoint(10, 10), Qt.CopyAction, mime_data,
        Qt.LeftButton, Qt.NoModifier
    )
    window.dragEnterEvent(drag_enter)
    assert drag_enter.isAccepted()

    # Simulate drop
    drop_event = QDropEvent(
        QPoint(10, 10), Qt.CopyAction, mime_data,
        Qt.LeftButton, Qt.NoModifier
    )
    window.dropEvent(drop_event)

    # Verify files added
    assert len(window.selected_files) == 2
```

### Pattern 5: Mock Worker Threads in GUI Tests
**What:** Replace actual workers with MagicMock to test UI-worker integration
**When to use:** GUI tests that would normally create worker threads (Phase 4)

**Example:**
```python
# Pattern derived from test_main_window.py + pytest-mock best practices
@pytest.mark.gui
def test_start_job_creates_worker(qtbot, test_config, test_db, mocker):
    """Test that start button creates and starts worker."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)
    window.selected_files = [Path("test.docx")]
    window._update_ui_state()

    # Mock worker class completely
    mock_worker_class = mocker.patch('src.ui.main_window.JobWorker')
    mock_worker_instance = MagicMock()
    mock_worker_class.return_value = mock_worker_instance

    # Mock ProgressDialog
    mocker.patch('src.ui.main_window.ProgressDialog')

    # Click start
    QTest.mouseClick(window.start_button, Qt.LeftButton)

    # Verify worker created and started
    mock_worker_class.assert_called_once()
    mock_worker_instance.start.assert_called_once()
    assert window.start_button.isEnabled() is False
```

### Pattern 6: Testing Table/List Widget Population
**What:** Verify table/list widgets display correct data
**When to use:** Testing HistoryWindow job listing, result details

**Example:**
```python
@pytest.mark.gui
def test_history_table_population(qtbot, test_db):
    """Test that job history populates table correctly."""
    # Create test job in database
    job_id = test_db.create_job(
        operation="search_replace",
        config={"find": "test"},
        status="completed"
    )

    window = HistoryWindow(test_db)
    qtbot.addWidget(window)

    # Verify table has one row
    assert window.jobs_table.rowCount() == 1

    # Verify data in cells
    operation_item = window.jobs_table.item(0, 1)  # Column 1 = operation
    assert operation_item.text() == "search_replace"
```

### Anti-Patterns to Avoid
- **Using time.sleep() instead of qtbot.waitSignal()**: Sleep causes flaky tests; signals are deterministic
- **Testing real worker threads in GUI phase**: Workers tested separately in integration phase; mock in GUI tests
- **Interacting with actual modal dialogs**: Dialogs block test execution; always monkeypatch
- **Using QTest.mouseClick for simple operations**: Direct widget methods (setText, click) are more reliable
- **Not registering widgets with qtbot.addWidget()**: Causes resource leaks and Qt warnings

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Waiting for signals | `time.sleep()` loops | `qtbot.waitSignal()` | Arbitrary sleeps cause flaky tests; waitSignal is deterministic |
| QApplication lifecycle | Manual QApp creation/cleanup | `qtbot` fixture | pytest-qt handles singleton pattern and cleanup automatically |
| Modal dialog testing | Custom dialog automation | `monkeypatch` fixture | Modal dialogs block execution; mocking is fast and reliable |
| Worker thread testing in GUI | Real QThread instances | `unittest.mock.MagicMock` | GUI tests validate UI only; integration tests cover real threading |
| Asserting signal emission | Manual tracking with slots | `qtbot.assertNotEmitted()` | Built-in context manager for negative assertions |

**Key insight:** pytest-qt provides specialized fixtures designed for Qt's event loop and signal/slot architecture. Using generic testing patterns (sleeps, manual event loops) creates unreliable tests.

## Common Pitfalls

### Pitfall 1: Missing DISPLAY Environment Variable
**What goes wrong:** Tests crash immediately with `abort()` when Qt cannot find a display
**Why it happens:** CI environments (GitHub Actions, Docker) don't have GUI displays by default
**How to avoid:** Install pytest-xvfb plugin or manually set up virtual framebuffer (Xvfb)
**Warning signs:**
```
qt.qpa.xcb: could not connect to display
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
```

**Solution:**
```bash
# Install pytest-xvfb
pip install pytest-xvfb

# pytest automatically uses virtual display
pytest tests/gui/
```

### Pitfall 2: Qt Library Conflicts with Other Packages
**What goes wrong:** Tests fail on CI but work locally when using opencv-python, matplotlib, or similar
**Why it happens:** These packages bundle their own Qt libraries and modify Qt environment variables
**How to avoid:** Use headless variants (opencv-python-headless) or isolate dependencies
**Warning signs:** Segmentation faults, Qt version conflicts, missing xcb plugins

**Solution:**
```bash
# Use headless opencv
pip uninstall opencv-python
pip install opencv-python-headless
```

### Pitfall 3: Not Waiting for Signals Properly
**What goes wrong:** Test fails intermittently with "signal not received" or passes when it should fail
**Why it happens:** Using `time.sleep()` instead of `qtbot.waitSignal()` creates race conditions
**How to avoid:** Always use `qtbot.waitSignal()` with appropriate timeout for async operations
**Warning signs:** Tests that fail on CI but pass locally, or vice versa

**Solution:**
```python
# ❌ WRONG - race condition
def test_worker_completion_bad(qtbot):
    window.start_job()
    time.sleep(2)  # Hope worker finishes in 2 seconds
    assert window.results is not None

# ✅ CORRECT - deterministic
def test_worker_completion_good(qtbot):
    with qtbot.waitSignal(window.worker.finished, timeout=5000):
        window.start_job()
    assert window.results is not None
```

### Pitfall 4: Forgetting to Register Widgets with qtbot
**What goes wrong:** Qt warnings about "QObject::~QObject: Timers cannot be stopped from another thread"
**Why it happens:** Widgets not cleaned up properly, causing Qt to complain during test teardown
**How to avoid:** Always call `qtbot.addWidget(widget)` for every widget created in tests
**Warning signs:** Qt warnings in test output, occasional crashes during cleanup

**Solution:**
```python
@pytest.mark.gui
def test_window(qtbot, test_config, test_db):
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)  # CRITICAL - ensures proper cleanup
    # ... test code
```

### Pitfall 5: Testing Widget Interactions vs Widget Methods
**What goes wrong:** Tests become flaky when using QTest.keyClicks/mouseClick for simple operations
**Why it happens:** Event simulation requires event loop processing, adding timing complexity
**How to avoid:** Prefer direct widget methods (setText, setCurrentIndex) over event simulation
**Warning signs:** Tests that occasionally fail with "event not processed" or timing issues

**Solution:**
```python
# ❌ LESS RELIABLE - requires event processing
def test_search_input_unreliable(qtbot):
    QTest.keyClicks(window.search_input, "test query")
    assert window.search_input.text() == "test query"

# ✅ MORE RELIABLE - direct method call
def test_search_input_reliable(qtbot):
    window.search_input.setText("test query")
    assert window.search_input.text() == "test query"

# Use QTest methods ONLY when testing event handling itself
def test_keyboard_shortcut(qtbot):
    QTest.keyClick(window, Qt.Key_S, Qt.ControlModifier)
    # Testing that Ctrl+S actually triggers start
```

### Pitfall 6: Modal Dialog Blocking Tests
**What goes wrong:** Test hangs indefinitely when code shows a QMessageBox or QFileDialog
**Why it happens:** Modal dialogs block execution waiting for user input
**How to avoid:** Always monkeypatch dialog methods before triggering code that shows dialogs
**Warning signs:** Tests that hang and never complete

**Solution:**
```python
# ❌ BLOCKS FOREVER
def test_error_handling_blocks(qtbot):
    window.process_file("invalid.docx")  # Shows error dialog
    # Test never reaches this line

# ✅ MOCKED, NON-BLOCKING
def test_error_handling_works(qtbot, monkeypatch):
    critical_called = []
    monkeypatch.setattr(
        QMessageBox, 'critical',
        lambda *args: critical_called.append(args)
    )
    window.process_file("invalid.docx")
    assert len(critical_called) == 1
```

### Pitfall 7: Incorrect Signal/Slot Connection Assumptions
**What goes wrong:** Test passes but actual UI doesn't work, or vice versa
**Why it happens:** Mocking changes connection behavior, or test doesn't verify connections
**How to avoid:** Test both that signal is emitted AND that connected slot is called
**Warning signs:** UI works in manual testing but fails in real use, or tests pass but feature broken

**Solution:**
```python
@pytest.mark.gui
def test_progress_signal_connection(qtbot, mocker):
    """Verify signal connection, not just emission."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Spy on the slot method to verify it's called
    update_spy = mocker.spy(window, '_on_progress_updated')

    # Create mock progress dialog
    window.progress_dialog = MagicMock()

    # Emit signal (would come from worker in real scenario)
    window._on_progress_updated(50, "file.docx", 10, 2)

    # Verify slot was called with correct args
    update_spy.assert_called_once_with(50, "file.docx", 10, 2)
    window.progress_dialog.update_progress.assert_called_once()
```

## Code Examples

Verified patterns from official sources and existing tests:

### Testing ProgressDialog Updates
```python
# Source: Derived from ProgressDialog implementation + pytest-qt patterns
@pytest.mark.gui
def test_progress_dialog_update(qtbot):
    """Test progress dialog updates correctly."""
    dialog = ProgressDialog()
    qtbot.addWidget(dialog)

    # Update progress
    dialog.update_progress(
        percentage=50,
        current_file="test.docx",
        processed_count=5,
        failed_count=1
    )

    # Verify UI elements updated
    assert dialog.progress_bar.value() == 50
    assert "test.docx" in dialog.current_file_label.text()
    assert dialog.success_label.text() == "Success: 4"  # 5 - 1
    assert dialog.failure_label.text() == "Failed: 1"
```

### Testing ProgressDialog Cancellation
```python
# Source: pytest-qt signal patterns
@pytest.mark.gui
def test_progress_dialog_cancellation(qtbot):
    """Test cancel button emits cancelled signal."""
    dialog = ProgressDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    # Wait for cancelled signal
    with qtbot.waitSignal(dialog.cancelled, timeout=1000) as blocker:
        QTest.mouseClick(dialog.cancel_button, Qt.LeftButton)

    # Verify signal emitted
    assert blocker.signal_triggered
```

### Testing HistoryWindow Filtering
```python
# Source: Derived from HistoryWindow implementation
@pytest.mark.gui
def test_history_window_filter_by_operation(qtbot, test_db):
    """Test filtering jobs by operation type."""
    # Create test jobs with different operations
    test_db.create_job(operation="search_replace", config={}, status="completed")
    test_db.create_job(operation="metadata", config={}, status="completed")
    test_db.create_job(operation="search_replace", config={}, status="failed")

    window = HistoryWindow(test_db)
    qtbot.addWidget(window)

    # Initially shows all 3 jobs
    assert window.jobs_table.rowCount() == 3

    # Filter by search_replace
    window.operation_filter.setCurrentText("search_replace")

    # Should show only 2 jobs
    qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 2, timeout=1000)
    assert window.jobs_table.rowCount() == 2
```

### Testing Elapsed Time Display
```python
# Source: Derived from ProgressDialog time tracking
@pytest.mark.gui
def test_progress_dialog_elapsed_time(qtbot, monkeypatch):
    """Test elapsed time updates correctly."""
    # Mock time to control elapsed calculation
    import time
    fake_start = 1000.0
    fake_current = 1065.0  # 65 seconds elapsed

    monkeypatch.setattr(time, 'time', lambda: fake_current)

    dialog = ProgressDialog()
    dialog.start_time = fake_start
    qtbot.addWidget(dialog)

    # Update progress (triggers time recalculation)
    dialog.update_progress(50, "test.docx", 5, 0)

    # Verify elapsed time shows 00:01:05
    assert "00:01:05" in dialog.elapsed_label.text()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QTest-only testing | pytest-qt plugin | 2015 (pytest-qt 1.0) | Better fixtures, pytest integration, signal handling |
| Manual event loop running | qtbot.waitSignal() | pytest-qt 1.4 (2015) | Eliminates race conditions and arbitrary sleeps |
| Interacting with modal dialogs | monkeypatch mocking | Long-standing best practice | Prevents test blocking, much faster |
| Arbitrary time.sleep() | qtbot.waitUntil() | pytest-qt 2.0 (2016) | Deterministic waiting for conditions |
| Qt 5 xcb bundling | Separate xcb packages | Qt 5.15+ (2020) | Requires explicit xcb package installation on CI |

**Deprecated/outdated:**
- Using raw QTest without pytest-qt: pytest-qt provides better lifecycle management
- Manual QApplication creation in tests: qtbot fixture handles this automatically
- Testing GUI + worker threads together: Separate concerns (Phase 4 = GUI only, Phase 5 = integration)

## Open Questions

Things that couldn't be fully resolved:

1. **Exact xcb package requirements for Qt 6.8+**
   - What we know: Qt 6.5+ requires xcb-cursor0, Qt 6.8 may have additional dependencies
   - What's unclear: Complete list of xcb packages needed for PySide6 6.8.0 on Ubuntu/Debian CI
   - Recommendation: Use tlambert03/setup-qt-libs GitHub Action OR install comprehensive xcb set:
     ```bash
     libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1
     libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 libxcb-cursor0
     ```

2. **Best practice for testing QComboBox currentTextChanged vs currentIndexChanged**
   - What we know: Both signals exist, setText() triggers one, setCurrentIndex() triggers the other
   - What's unclear: Which signal to test when verifying operation switching behavior
   - Recommendation: Test the signal your code actually connects to (check implementation)

3. **Performance impact of qtbot.waitUntil() polling interval**
   - What we know: waitUntil polls callback function periodically until condition met
   - What's unclear: Default polling interval, whether it's configurable, performance implications
   - Recommendation: Prefer waitSignal when possible (event-driven); use waitUntil sparingly

## Sources

### Primary (HIGH confidence)
- [pytest-qt Official Documentation](https://pytest-qt.readthedocs.io/en/latest/) - Introduction, best practices, core patterns
- [pytest-qt Signals Guide](https://pytest-qt.readthedocs.io/en/latest/signals.html) - waitSignal/waitUntil patterns and parameters
- [pytest-qt Troubleshooting](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html) - Common issues, CI setup, xcb dependencies
- [pytest-qt Modal Dialogs](https://pytest-qt.readthedocs.io/en/latest/note_dialogs.html) - Monkeypatch pattern for QMessageBox/QFileDialog
- [PySide6 QtTest Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtTest/index.html) - Official QTest module reference
- Existing test infrastructure: `tests/conftest.py`, `tests/gui/test_main_window.py` (verified working patterns)

### Secondary (MEDIUM confidence)
- [Headless Testing with pytest-qt (ilManzo's blog)](https://ilmanzo.github.io/post/testing_pyside_gui_applications/) - Practical CI setup examples
- [pytest-qt GitHub Repository](https://github.com/pytest-dev/pytest-qt) - Source code, issue discussions
- [PythonGUIs Multithreading Tutorial](https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/) - Worker thread patterns

### Tertiary (LOW confidence)
- WebSearch results about drag-and-drop testing (known limitations, workarounds needed)
- Stack Overflow discussions about QThread mocking (varied approaches, no consensus)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest-qt is the official, well-documented solution for Qt testing
- Architecture: HIGH - Patterns verified in official docs and existing working tests
- Pitfalls: HIGH - Documented in official troubleshooting guide and observed in project tests
- Don't hand-roll: HIGH - pytest-qt specifically designed to solve these problems
- Drag-and-drop: MEDIUM - Pattern works but has known limitations in Qt framework itself
- xcb dependencies: MEDIUM - Qt 6.8 is recent, dependency list may be incomplete

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - pytest-qt is stable, but PySide6 updates frequently)
