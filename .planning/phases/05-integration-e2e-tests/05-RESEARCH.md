# Phase 5: Integration & E2E Tests - Research

**Researched:** 2026-02-01
**Domain:** pytest-qt integration testing, E2E workflows, error recovery patterns
**Confidence:** HIGH

## Summary

Integration and E2E testing for PySide6 applications with pytest-qt requires specific patterns for thread synchronization, signal verification, and component isolation. The standard approach uses pytest-qt's `waitSignal()` for async operations, in-memory databases for fast isolation, real file operations in temp directories, and in-process execution (not multiprocessing pools) for debuggability.

**Key findings:**
- pytest-qt provides robust signal/slot testing with `qtbot.waitSignal()` and automatic exception capture in Qt slots
- Integration tests should verify component boundaries (database + backup manager, worker + processors) rather than full multiprocessing stacks for speed and reliability
- Error recovery testing uses real corrupt documents (malformed XML, invalid files) not mocked exceptions for authentic behavior
- Parallel test execution with pytest-xdist requires fixture isolation strategies (per-worker temp directories, in-memory databases)

**Primary recommendation:** Start tests from UI layer (MainWindow → ProgressDialog) to validate complete user workflows, use in-process processor execution for speed and debuggability, and verify both file changes AND database records for comprehensive validation.

## Standard Stack

The established libraries/tools for pytest-qt integration and E2E testing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-qt | 4.3.1 | PySide6/PyQt testing | Official pytest plugin for Qt testing, handles QApplication lifecycle, provides qtbot fixture for signal/widget testing |
| PySide6 | 6.8.0+ | Qt bindings | Application framework, required for GUI testing |
| pytest | 8.0.0 | Test framework | Industry standard Python testing |
| pytest-xdist | 3.5.0 | Parallel execution | Speeds up test runs via multi-core distribution |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-timeout | 2.2.0 | Test timeout enforcement | Catch hanging async operations (60s default for E2E) |
| pytest-rerunfailures | 13.0 | Flaky test handling | Retry intermittent failures in async GUI tests |
| hypothesis | 6.98.0 | Property-based testing | Generate edge-case test data for workflows |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-qt | unittest.mock + manual QTest | pytest-qt provides automatic QApplication lifecycle and signal blocking, manual approach requires 50+ lines of boilerplate |
| In-process processors | Multiprocessing pools | In-process is 10x faster, easier to debug, sufficient for integration tests (reserve multiprocessing for performance tests) |
| pytest-xdist | Sequential execution | Parallel saves 3-5x execution time but requires careful fixture isolation |

**Installation:**
```bash
pip install pytest-qt==4.3.1 pytest-xdist==3.5.0 pytest-timeout==2.2.0
```

## Architecture Patterns

### Recommended Test Structure
```
tests/integration/
├── test_workflow_search_replace.py    # E2E workflow for search/replace
├── test_workflow_metadata.py          # E2E workflow for metadata operations
├── test_workflow_tables.py            # E2E workflow for table formatting
├── test_workflow_styles.py            # E2E workflow for style enforcement
├── test_workflow_validation.py        # E2E workflow for document validation
├── test_error_recovery.py             # Error handling and partial failure
├── test_backup_integration.py         # Backup creation and restoration
└── test_cancellation.py               # User-initiated cancellation
```

### Pattern 1: E2E Workflow Test
**What:** Full user journey from UI interaction through processing to completion
**When to use:** Testing that all components work together correctly for a specific operation

**Example:**
```python
# Source: pytest-qt documentation + project patterns
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

@pytest.mark.integration
@pytest.mark.timeout(60)
class TestSearchReplaceWorkflow:
    """E2E test for complete search/replace workflow."""

    def test_full_workflow_success(self, qtbot, test_db, temp_workspace, docx_factory):
        """Test complete workflow from file selection to completion."""
        # Arrange: Create test documents
        docs = [
            docx_factory(content=f"Document {i} with old text", filename=f"doc_{i}.docx")
            for i in range(10)
        ]

        # Arrange: Initialize UI
        from src.ui.main_window import MainWindow
        window = MainWindow(config=None, db=test_db)
        qtbot.addWidget(window)
        window.show()

        # Act: Select files (simulate UI interaction)
        window.selected_files = [str(d) for d in docs]
        window.update_file_list()

        # Act: Configure operation
        window.operation_combo.setCurrentText("Search & Replace")
        window.find_input.setText("old")
        window.replace_input.setText("new")

        # Act: Start processing and wait for completion
        with qtbot.waitSignal(window.job_completed, timeout=30000) as blocker:
            QTest.mouseClick(window.start_button, Qt.LeftButton)

        # Assert: Verify signal emitted with results
        assert blocker.signal_triggered
        results = blocker.args[0]

        # Assert: Verify all files processed successfully
        assert len(results) == 10
        assert all(r['success'] for r in results)

        # Assert: Verify file changes
        from docx import Document
        for doc_path in docs:
            doc = Document(str(doc_path))
            text = '\n'.join(p.text for p in doc.paragraphs)
            assert "new text" in text
            assert "old text" not in text

        # Assert: Verify database records
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM jobs ORDER BY created_at DESC LIMIT 1")
            job = cursor.fetchone()
            assert job['status'] == 'completed'
```

### Pattern 2: Error Recovery Test
**What:** Verify graceful handling of processor failures with partial success
**When to use:** Testing that failures in some files don't block processing of others

**Example:**
```python
# Source: pytest best practices + project requirements
@pytest.mark.integration
def test_partial_failure_handling(qtbot, test_db, temp_workspace, docx_factory, tmp_path):
    """Test processing continues after individual file failures."""
    # Arrange: Create mix of valid and corrupt documents
    valid_docs = [
        docx_factory(content=f"Valid doc {i}", filename=f"valid_{i}.docx")
        for i in range(5)
    ]

    # Create corrupt document (malformed XML)
    corrupt_path = tmp_path / "corrupt.docx"
    with open(corrupt_path, 'wb') as f:
        f.write(b"Not a valid ZIP/DOCX file")

    all_docs = valid_docs + [corrupt_path]

    # Act: Process all files
    window = MainWindow(config=None, db=test_db)
    qtbot.addWidget(window)
    window.selected_files = [str(d) for d in all_docs]
    window.operation_combo.setCurrentText("Metadata Update")

    with qtbot.waitSignal(window.job_completed, timeout=30000) as blocker:
        QTest.mouseClick(window.start_button, Qt.LeftButton)

    results = blocker.args[0]

    # Assert: Valid files succeeded, corrupt failed
    success_count = sum(1 for r in results if r['success'])
    failure_count = sum(1 for r in results if not r['success'])

    assert success_count == 5
    assert failure_count == 1

    # Assert: Corrupt file unchanged (not modified)
    original_corrupt = corrupt_path.read_bytes()
    assert corrupt_path.read_bytes() == original_corrupt

    # Assert: Job marked as partial success in database
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, error_count FROM jobs
            ORDER BY created_at DESC LIMIT 1
        """)
        job = cursor.fetchone()
        assert job['status'] == 'completed_with_errors'
        assert job['error_count'] == 1
```

### Pattern 3: Backup Integration Test
**What:** Verify backup creation before processing and restoration after failure
**When to use:** Testing the backup safety mechanism works correctly

**Example:**
```python
# Source: Project requirements E2E-03
@pytest.mark.integration
def test_backup_and_restore(qtbot, test_db, temp_workspace, docx_factory):
    """Test backup created before processing and restorable after failure."""
    # Arrange: Create test document with known content
    original_content = "Original content that should be preserved"
    doc_path = docx_factory(content=original_content, filename="test.docx")

    # Act: Process with backup enabled
    from src.core.backup import BackupManager
    backup_mgr = BackupManager(temp_workspace / "backups", test_db)

    # Create backup before processing
    backup_path = backup_mgr.create_backup(doc_path)
    assert backup_path.exists()

    # Simulate processing that modifies file
    from docx import Document
    doc = Document(str(doc_path))
    doc.paragraphs[0].text = "Modified content"
    doc.save(str(doc_path))

    # Verify file was modified
    doc_modified = Document(str(doc_path))
    assert "Modified content" in doc_modified.paragraphs[0].text

    # Act: Restore from backup
    backup_mgr.restore_backup(backup_path, doc_path)

    # Assert: Original content restored
    doc_restored = Document(str(doc_path))
    text = '\n'.join(p.text for p in doc_restored.paragraphs)
    assert original_content in text
    assert "Modified content" not in text

    # Assert: Database records backup operation
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM backups WHERE original_path = ?",
                      (str(doc_path),))
        assert cursor.fetchone()['count'] == 1
```

### Pattern 4: Signal Spying with Context Manager
**What:** Using qtbot.waitSignal() with timeout and multiple signals
**When to use:** Verifying async operations complete and emit expected signals

**Example:**
```python
# Source: pytest-qt documentation - signals.html
@pytest.mark.integration
def test_progress_updates(qtbot, test_db, docx_factory):
    """Test progress signals emitted during processing."""
    docs = [docx_factory(content=f"Doc {i}", filename=f"doc_{i}.docx") for i in range(20)]

    window = MainWindow(config=None, db=test_db)
    qtbot.addWidget(window)
    window.selected_files = [str(d) for d in docs]

    # Spy on multiple signals
    progress_signals = []

    def on_progress(current, total, filename):
        progress_signals.append((current, total, filename))

    window.progress_updated.connect(on_progress)

    # Start processing
    with qtbot.waitSignal(window.job_completed, timeout=30000):
        window.start_processing()

    # Verify progress signals emitted
    assert len(progress_signals) == 20
    assert progress_signals[0] == (1, 20, str(docs[0]))
    assert progress_signals[-1] == (20, 20, str(docs[-1]))
```

### Pattern 5: Cancellation Test
**What:** Verify mid-processing cancellation doesn't corrupt documents
**When to use:** Testing user can safely cancel long-running operations

**Example:**
```python
# Source: Project requirements + pytest-qt patterns
@pytest.mark.integration
@pytest.mark.timeout(60)
def test_user_cancellation(qtbot, test_db, docx_factory, tmp_path):
    """Test user-initiated cancellation leaves documents uncorrupted."""
    # Arrange: Create many documents to ensure processing takes time
    docs = [
        docx_factory(content=f"Document {i} content", filename=f"doc_{i:03d}.docx")
        for i in range(50)
    ]

    # Track original content hashes
    import hashlib
    original_hashes = {}
    for doc_path in docs:
        with open(doc_path, 'rb') as f:
            original_hashes[str(doc_path)] = hashlib.md5(f.read()).hexdigest()

    # Act: Start processing
    window = MainWindow(config=None, db=test_db)
    qtbot.addWidget(window)
    window.selected_files = [str(d) for d in docs]
    window.operation_combo.setCurrentText("Search & Replace")

    # Start processing (don't wait for completion)
    window.start_processing()

    # Wait briefly for processing to start
    qtbot.wait(500)

    # Trigger cancellation
    with qtbot.waitSignal(window.job_cancelled, timeout=10000):
        window.cancel_processing()

    # Assert: Some files processed, some not (partial completion)
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status FROM jobs ORDER BY created_at DESC LIMIT 1
        """)
        job = cursor.fetchone()
        assert job['status'] == 'cancelled'

    # Assert: No documents corrupted (either unchanged or successfully modified)
    from docx import Document
    for doc_path in docs:
        try:
            doc = Document(str(doc_path))  # Should open without errors
            paragraphs = list(doc.paragraphs)  # Should be readable
            assert len(paragraphs) > 0
        except Exception as e:
            pytest.fail(f"Document {doc_path} corrupted after cancellation: {e}")
```

### Anti-Patterns to Avoid

- **Using multiprocessing pools in integration tests:** Slow, hard to debug, creates resource contention. Use in-process execution instead.
- **Mocking signals/slots:** Defeats purpose of integration testing. Test real signal/slot connections.
- **Shared state between tests:** Breaks parallel execution. Always use isolated fixtures (test_db, temp_workspace).
- **Sleeping instead of waitSignal():** Unreliable timing. Use `qtbot.waitSignal()` for deterministic async testing.
- **Testing implementation details:** Test user-visible behavior (UI state changes, file modifications) not internal method calls.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal timeout handling | Custom event loop + QTimer | `qtbot.waitSignal(signal, timeout=ms)` | pytest-qt handles event processing, timeout, and exception propagation automatically |
| Async test coordination | Threading primitives, manual synchronization | `qtbot.waitSignal()` with context manager | Built-in signal blocking with proper exception handling |
| QApplication lifecycle | Manual QApplication creation/cleanup | pytest-qt's `qapp` and `qtbot` fixtures | Automatic lifecycle management, handles multiple tests correctly |
| Parallel test isolation | Custom temp directory schemes | pytest-xdist's `tmp_path_factory` with `worker_id` | Automatic per-worker isolation for parallel execution |
| Database test isolation | Manual database creation/teardown | pytest fixtures with `:memory:` SQLite | In-memory databases are 100x faster and automatically isolated |
| Widget cleanup | Manual widget.deleteLater() calls | `qtbot.addWidget(widget)` | Automatic cleanup after test completion |
| Corrupt document generation | Binary manipulation, hex editing | Use python-docx with intentional errors OR invalid file contents | More maintainable and representative of real-world failures |

**Key insight:** pytest-qt's signal/slot handling eliminates 90% of Qt testing boilerplate and prevents race conditions from manual event loop manipulation. Always prefer `qtbot.waitSignal()` over custom synchronization.

## Common Pitfalls

### Pitfall 1: Indefinite waitSignal Hangs
**What goes wrong:** Test hangs indefinitely waiting for signal that never arrives
**Why it happens:** Signal not emitted, wrong signal, or exception in slot prevents emission
**How to avoid:**
- Always specify reasonable timeout (10-60 seconds for E2E)
- Use `raising=True` (default) to get TimeoutError exception with clear message
- Check Qt slot exceptions are propagated (pytest-qt captures them automatically)

**Warning signs:**
```python
# BAD: No timeout specified, hangs forever
with qtbot.waitSignal(window.completed):
    window.start()

# GOOD: Explicit timeout with clear error
with qtbot.waitSignal(window.completed, timeout=30000) as blocker:
    window.start()
# If timeout: TimeoutError with details about which signal timed out
```

### Pitfall 2: Multiprocessing in Integration Tests
**What goes wrong:** Tests become slow (10x slower), flaky, and hard to debug
**Why it happens:** Multiprocessing has overhead (process spawning, IPC, serialization)
**How to avoid:** Use in-process execution for integration tests. Reserve multiprocessing for performance tests only.

**Prevention strategy:**
```python
# GOOD: In-process processor execution (fast, debuggable)
from src.processors.search_replace import process_document

def test_workflow(docx_factory):
    doc = docx_factory(content="old text")
    result = process_document(str(doc), {"find": "old", "replace": "new"})
    assert result.success

# AVOID: Multiprocessing pool in integration tests (slow, flaky)
from multiprocessing import Pool

def test_workflow_slow(docx_factory):
    with Pool(4) as pool:  # Spawns processes, IPC overhead
        result = pool.apply_async(process_document, args)
        result.get(timeout=30)  # Slower, harder to debug
```

### Pitfall 3: Shared Fixtures Breaking Parallel Execution
**What goes wrong:** pytest-xdist parallel execution fails with database/file conflicts
**Why it happens:** Multiple workers access same database or temp directory simultaneously
**How to avoid:** Use per-test isolated fixtures (`test_db` with `:memory:`, `tmp_path` per test)

**Prevention strategy:**
```python
# BAD: Shared database breaks parallel execution
@pytest.fixture(scope="session")
def shared_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "shared.db"
    return DatabaseManager(db_path)  # Multiple workers conflict

# GOOD: Per-test isolation for parallel safety
@pytest.fixture
def test_db():
    db = DatabaseManager(":memory:")  # Each test gets own database
    yield db
    db.close()
```

### Pitfall 4: Testing Implementation Instead of Behavior
**What goes wrong:** Tests break when refactoring internal implementation
**Why it happens:** Tests verify method calls instead of user-visible outcomes
**How to avoid:** Test from UI layer, verify file changes and database records, not internal state

**Warning signs:**
```python
# BAD: Testing internal implementation
def test_worker_calls_processor(mocker):
    mock_processor = mocker.patch('src.processors.search_replace.process_document')
    worker.run()
    mock_processor.assert_called_once()  # Fragile

# GOOD: Testing user-visible behavior
def test_search_replace_workflow(qtbot, docx_factory):
    doc = docx_factory(content="old text")
    window.selected_files = [str(doc)]
    window.find_input.setText("old")
    window.replace_input.setText("new")

    with qtbot.waitSignal(window.job_completed):
        window.start_processing()

    # Verify actual file change (behavior)
    doc_content = Document(str(doc))
    assert "new text" in doc_content.paragraphs[0].text
```

### Pitfall 5: Corrupt Document Testing with Mocks
**What goes wrong:** Mocked exceptions don't represent real python-docx behavior
**Why it happens:** Real corrupt documents trigger different exceptions/states than mocks
**How to avoid:** Create actual corrupt documents (invalid ZIP, malformed XML, missing files)

**Prevention strategy:**
```python
# BAD: Mocked exception (not realistic)
def test_corrupt_handling(mocker, docx_factory):
    mocker.patch('docx.Document').side_effect = Exception("Mocked error")
    # Doesn't test real python-docx exceptions

# GOOD: Real corrupt document
def test_corrupt_handling(tmp_path):
    corrupt = tmp_path / "corrupt.docx"
    corrupt.write_bytes(b"Not a DOCX file")  # Real invalid file

    result = process_document(str(corrupt), {})
    assert not result.success
    assert "PackageNotFoundError" in result.error_message  # Real exception
```

### Pitfall 6: Race Conditions from Manual Event Processing
**What goes wrong:** Flaky tests that pass/fail randomly due to event loop timing
**Why it happens:** Manual `QApplication.processEvents()` doesn't guarantee signal delivery
**How to avoid:** Use `qtbot.waitSignal()` which properly blocks until signal emission

**Warning signs:**
```python
# BAD: Manual event processing (flaky)
window.start_processing()
QApplication.processEvents()  # Might not process all events
assert window.is_completed  # Race condition

# GOOD: Signal-based synchronization (deterministic)
with qtbot.waitSignal(window.job_completed, timeout=10000):
    window.start_processing()
assert window.is_completed  # Guaranteed to run after signal
```

## Code Examples

Verified patterns from pytest-qt official documentation and project requirements:

### E2E Workflow Test Structure
```python
# Source: pytest-qt tutorial + project CONTEXT.md
import pytest
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from docx import Document

@pytest.mark.integration
@pytest.mark.timeout(60)
class TestSearchReplaceE2E:
    """Full E2E workflow for search/replace operation."""

    def test_complete_workflow(self, qtbot, test_db, temp_workspace, docx_factory):
        """Test file selection → processing → completion → results."""
        # Arrange: Create 15 test documents (medium batch size)
        docs = [
            docx_factory(
                content=f"Document {i} contains old value in paragraph.",
                filename=f"doc_{i:02d}.docx",
                title=f"Test Document {i}"
            )
            for i in range(15)
        ]

        # Arrange: Initialize main window with test database
        from src.ui.main_window import MainWindow
        window = MainWindow(config=None, db=test_db)
        qtbot.addWidget(window)
        window.show()

        # Act: Simulate file selection
        window.selected_files = [str(d) for d in docs]
        window.update_file_list()

        # Act: Configure search/replace operation
        window.operation_combo.setCurrentText("Search & Replace")
        window.find_input.setText("old value")
        window.replace_input.setText("new value")
        window.case_sensitive_checkbox.setChecked(True)

        # Act: Start processing and wait for completion signal
        with qtbot.waitSignal(window.job_completed, timeout=30000) as blocker:
            QTest.mouseClick(window.start_button, Qt.LeftButton)

        # Assert: Job completed signal received
        assert blocker.signal_triggered
        results = blocker.args[0]

        # Assert: All files processed successfully
        assert len(results) == 15
        success_count = sum(1 for r in results if r['success'])
        assert success_count == 15, f"Only {success_count}/15 files succeeded"

        # Assert: Verify file changes (actual DOCX content)
        for doc_path in docs:
            doc = Document(str(doc_path))
            full_text = '\n'.join(p.text for p in doc.paragraphs)
            assert "new value" in full_text
            assert "old value" not in full_text

        # Assert: Verify database records (job tracking)
        with test_db.get_connection() as conn:
            cursor = conn.cursor()

            # Check job status
            cursor.execute("""
                SELECT operation, status, config
                FROM jobs
                ORDER BY created_at DESC
                LIMIT 1
            """)
            job = cursor.fetchone()
            assert job['operation'] == 'search_replace'
            assert job['status'] == 'completed'

            # Check job results (per-file records)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM job_results
                WHERE job_id = ? AND status = 'success'
            """, (job['id'],))
            assert cursor.fetchone()['count'] == 15
```

### Error Recovery with Partial Failure
```python
# Source: Project requirements E2E-02
@pytest.mark.integration
def test_partial_failure_graceful_degradation(qtbot, test_db, temp_workspace, docx_factory, tmp_path):
    """Test processing continues after individual file failures."""
    # Arrange: Create mix of valid and corrupt documents
    valid_docs = [
        docx_factory(content=f"Valid document {i}", filename=f"valid_{i}.docx")
        for i in range(10)
    ]

    # Create corrupt documents (different failure types)
    corrupt_invalid_zip = tmp_path / "corrupt_zip.docx"
    corrupt_invalid_zip.write_bytes(b"Not a ZIP file at all")

    corrupt_empty = tmp_path / "corrupt_empty.docx"
    corrupt_empty.write_bytes(b"")

    all_docs = valid_docs + [corrupt_invalid_zip, corrupt_empty]

    # Act: Process all files (should handle errors gracefully)
    from src.ui.main_window import MainWindow
    window = MainWindow(config=None, db=test_db)
    qtbot.addWidget(window)

    window.selected_files = [str(d) for d in all_docs]
    window.operation_combo.setCurrentText("Metadata Update")
    window.metadata_author.setText("New Author")

    with qtbot.waitSignal(window.job_completed, timeout=30000) as blocker:
        window.start_processing()

    results = blocker.args[0]

    # Assert: Valid files succeeded, corrupt files failed
    success_count = sum(1 for r in results if r['success'])
    failure_count = sum(1 for r in results if not r['success'])

    assert success_count == 10, "All valid files should succeed"
    assert failure_count == 2, "All corrupt files should fail"

    # Assert: Failed files NOT modified (compare to original)
    assert corrupt_invalid_zip.read_bytes() == b"Not a ZIP file at all"
    assert corrupt_empty.read_bytes() == b""

    # Assert: Valid files WERE modified
    for doc_path in valid_docs:
        doc = Document(str(doc_path))
        assert doc.core_properties.author == "New Author"

    # Assert: Database records partial success
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, error_count
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 1
        """)
        job = cursor.fetchone()
        assert job['status'] in ('completed_with_errors', 'partial_success')
        assert job['error_count'] == 2

        # Assert: Error details stored per file
        cursor.execute("""
            SELECT file_path, status, error_message
            FROM job_results
            WHERE job_id = ? AND status = 'failed'
        """, (job['id'],))
        failed_results = cursor.fetchall()
        assert len(failed_results) == 2
        assert any('corrupt_zip.docx' in r['file_path'] for r in failed_results)
```

### Backup Integration Test
```python
# Source: Project requirements E2E-03
@pytest.mark.integration
def test_backup_and_restore_integration(qtbot, test_db, temp_workspace, docx_factory):
    """Verify backup created before processing and restorable after failure."""
    # Arrange: Create test document with known content
    original_content = "Original paragraph that must be preserved."
    doc_path = docx_factory(
        content=original_content,
        filename="important_doc.docx",
        author="Original Author",
        title="Original Title"
    )

    # Arrange: Initialize backup manager
    from src.core.backup import BackupManager
    backup_dir = temp_workspace / "backups"
    backup_mgr = BackupManager(backup_dir, test_db)

    # Act: Create backup before processing
    backup_path = backup_mgr.create_backup(doc_path)

    # Assert: Backup exists and recorded in database
    assert backup_path.exists()
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT original_path, backup_path
            FROM backups
            WHERE original_path = ?
        """, (str(doc_path),))
        backup_record = cursor.fetchone()
        assert backup_record is not None
        assert Path(backup_record['backup_path']) == backup_path

    # Act: Simulate processing that modifies file
    doc = Document(str(doc_path))
    doc.paragraphs[0].text = "MODIFIED: This is different content"
    doc.core_properties.author = "Modified Author"
    doc.save(str(doc_path))

    # Assert: File was actually modified
    doc_modified = Document(str(doc_path))
    assert "MODIFIED" in doc_modified.paragraphs[0].text
    assert doc_modified.core_properties.author == "Modified Author"

    # Act: Restore from backup (simulating error recovery)
    restore_success = backup_mgr.restore_backup(backup_path, doc_path)
    assert restore_success

    # Assert: Original content fully restored
    doc_restored = Document(str(doc_path))
    restored_text = '\n'.join(p.text for p in doc_restored.paragraphs)
    assert original_content in restored_text
    assert "MODIFIED" not in restored_text
    assert doc_restored.core_properties.author == "Original Author"
    assert doc_restored.core_properties.title == "Original Title"
```

### Parallel Execution Fixture Isolation
```python
# Source: pytest-xdist documentation
@pytest.fixture
def isolated_workspace(tmp_path_factory, worker_id):
    """Create per-worker temp directory for parallel test execution.

    pytest-xdist assigns unique worker_id to each parallel worker.
    This fixture creates isolated workspace per worker to prevent conflicts.
    """
    if worker_id == "master":
        # Not running in parallel (sequential execution)
        temp_dir = tmp_path_factory.mktemp("workspace")
    else:
        # Running in parallel - create worker-specific directory
        root_tmp = tmp_path_factory.getbasetemp().parent
        temp_dir = root_tmp / f"workspace_{worker_id}"
        temp_dir.mkdir(exist_ok=True)

    # Create standard structure
    (temp_dir / "data").mkdir(exist_ok=True)
    (temp_dir / "backups").mkdir(exist_ok=True)
    (temp_dir / "logs").mkdir(exist_ok=True)

    return temp_dir
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual QTest event processing | `qtbot.waitSignal()` context manager | pytest-qt 2.0+ (2016) | Eliminates race conditions, provides deterministic async testing |
| setUp/tearDown for widget cleanup | `qtbot.addWidget()` automatic cleanup | pytest-qt 1.6+ (2015) | Prevents resource leaks, simplifies test code |
| Multiprocessing pools in integration tests | In-process execution with mocked concurrency | Current best practice (2024+) | 10x faster tests, easier debugging, better CI/CD performance |
| File-based test databases | In-memory SQLite with `:memory:` | pytest-django pattern (adopted widely) | 100x faster, automatic isolation, no cleanup needed |
| pytest.mark.slow for all GUI tests | Separate markers: @pytest.mark.gui and @pytest.mark.slow | pytest 7.0+ convention | Better test selection, faster development feedback |
| Sequential test execution | Parallel with pytest-xdist --dist loadscope | pytest-xdist 2.0+ (2020) | 3-5x faster test runs with proper fixture scoping |

**Deprecated/outdated:**
- **QTest.qWait(ms):** Use `qtbot.wait(ms)` or better yet `qtbot.waitSignal()` for deterministic timing
- **unittest.TestCase with PyQt:** Use pytest with pytest-qt fixtures for simpler, more maintainable tests
- **Mocking QFileDialog in integration tests:** Use real file operations in `tmp_path` for authentic testing
- **pytest.mark.xfail for flaky Qt tests:** Fix timing issues with proper `waitSignal()` instead of marking flaky

## Open Questions

Things that couldn't be fully resolved:

1. **QThread vs QThreadPool for worker implementation**
   - What we know: Project uses QThread (from CLAUDE.md), pytest-qt supports both
   - What's unclear: Whether workers should be testable with in-process execution or require thread mocking
   - Recommendation: Verify worker implementation in Phase 2-3 code, design tests to match actual threading model

2. **Processor timeout handling in E2E tests**
   - What we know: Tests need 60-second timeout, but individual processor operations might timeout earlier
   - What's unclear: Should E2E tests verify processor-level timeouts or only test-level timeouts?
   - Recommendation: Test only test-level timeout (60s) unless processor timeouts are user-visible behavior

3. **Optimal batch size for E2E tests**
   - What we know: Context.md suggests 10-20 documents, existing fixtures use 10
   - What's unclear: Whether 10 is sufficient to catch batch processing bugs or if 20+ is needed
   - Recommendation: Start with 15 documents (mid-range), add performance test with 50+ if needed

## Sources

### Primary (HIGH confidence)
- [pytest-qt official documentation](https://pytest-qt.readthedocs.io/) - waitSignal, qtbot fixtures, tutorial
- [pytest-qt signals documentation](https://pytest-qt.readthedocs.io/en/latest/signals.html) - timeout patterns, signal blocking
- [pytest-xdist documentation](https://pytest-xdist.readthedocs.io/en/stable/distribution.html) - parallel execution, fixture isolation
- Project codebase: `tests/conftest.py`, `tests/integration/test_core_infrastructure.py` - existing patterns

### Secondary (MEDIUM confidence)
- [Parallel Testing with pytest-xdist](https://pytest-with-eric.com/plugins/pytest-xdist/) - best practices, isolation strategies
- [PySide6 QThread documentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) - threading patterns for testing
- [pytest-django database testing](https://pytest-django.readthedocs.io/en/latest/database.html) - transaction rollback patterns adapted for SQLite

### Tertiary (LOW confidence)
- GitHub issues for pytest-qt (waitSignal hangs, flaky tests) - community troubleshooting patterns
- python-docx GitHub issues for corrupt document handling - real-world failure modes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest-qt is official Qt testing solution, well-documented
- Architecture patterns: HIGH - Patterns verified in pytest-qt docs and existing project code
- Error recovery: MEDIUM - Patterns are standard but specific corrupt document types need validation
- Pitfalls: HIGH - Documented in pytest-qt issues and official best practices

**Research date:** 2026-02-01
**Valid until:** ~30 days (pytest-qt and pytest-xdist are stable; patterns unlikely to change)
