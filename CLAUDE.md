# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DOCX Bulk Editor** is a lightweight Windows desktop application for batch processing Microsoft Word (.docx) documents. Built with Python 3.11+ and PySide6 (Qt 6), it provides a native desktop experience for search/replace operations, metadata management, formatting enforcement, and document validation across hundreds of files simultaneously.

**Status**: Early development phase - project setup and initial implementation in progress.

**Key Architecture**: Single-process desktop application with PySide6 UI, QThread workers for background tasks, and multiprocessing pools for CPU-bound document processing.

## Critical Windows Considerations

### Unicode Handling (ESSENTIAL)

**ALWAYS** explicitly specify `encoding='utf-8'` when opening files on Windows:

```python
# ✅ CORRECT - Explicit UTF-8 encoding
with open('config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# ❌ WRONG - Relies on system default (cp1252 on Windows)
with open('config.json', 'r') as f:
    data = json.load(f)
```

This applies to ALL file operations: reading, writing, JSON, SQLite, logs, and configuration files.

### Path Handling

- Use `pathlib.Path` for cross-platform path operations
- Always use raw strings or forward slashes for Windows paths: `r"C:\path\to\file"` or `"C:/path/to/file"`
- Support UNC paths for network shares: `\\server\share\file.docx`

## Development Setup

### Prerequisites

```bash
# Python 3.11+ required
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Install development/testing dependencies
pip install -r requirements-dev.txt
```

### Core Dependencies

**Production** (`requirements.txt`):
```
PySide6>=6.8.0          # Qt 6 for Python - GUI framework
python-docx>=1.1.0      # Word document manipulation
lxml>=5.1.0             # XML processing for python-docx
pyinstaller>=6.3.0      # Windows .exe packaging
```

**Development/Testing** (`requirements-dev.txt`):
```
pytest==8.0.0              # Testing framework
pytest-qt==4.3.1           # PySide6 testing utilities
pytest-cov==4.1.0          # Code coverage
pytest-xdist==3.5.0        # Parallel test execution
pytest-benchmark==4.0.0    # Performance benchmarking
black==24.2.0              # Code formatting
pylint==3.0.3              # Static analysis
mypy==1.8.0                # Type checking
ruff==0.2.2                # Fast linting
hypothesis==6.98.0         # Property-based testing
```

See `requirements-dev.txt` for complete list of development dependencies.

## Architecture Overview

### Threading Model (CRITICAL)

```
┌─────────────────────────────────────────────────┐
│  MAIN THREAD (UI Only)                          │
│  - QMainWindow, widgets, dialogs                │
│  - User input handling                          │
│  - UI updates ONLY                              │
│  - NEVER block with long operations             │
└────────────────┬────────────────────────────────┘
                 │ Qt Signals/Slots
                 ↓
┌─────────────────────────────────────────────────┐
│  WORKER THREAD (QThread)                        │
│  - Job orchestration & business logic           │
│  - Multiprocessing pool management              │
│  - SQLite database operations                   │
│  - Emits progress signals to UI                 │
└────────────────┬────────────────────────────────┘
                 │ Multiprocessing (IPC)
                 ↓
┌─────────────────────────────────────────────────┐
│  MULTIPROCESSING POOL (N=CPU_COUNT-1 workers)   │
│  - CPU-bound document processing                │
│  - python-docx operations                       │
│  - Each process has isolated memory             │
│  - Returns results via serialization (pickle)   │
└─────────────────────────────────────────────────┘
```

**Key Rules**:
1. **Main Thread**: UI updates only - never call long-running operations
2. **Worker Thread**: All business logic, database I/O, pool management
3. **Multiprocessing Pool**: Document processing (bypasses Python GIL for true parallelism)
4. **Communication**: Main↔Worker via Qt signals/slots (thread-safe), Worker↔Pool via multiprocessing

### PyInstaller Compatibility

**CRITICAL**: Multiprocessing requires special handling in frozen executables:

```python
# main.py
import multiprocessing

if __name__ == "__main__":
    # REQUIRED for PyInstaller + multiprocessing
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

## Project Structure (Planned)

```
docx-bulk-editor/
├── src/                          # Source code
│   ├── main.py                   # Application entry point
│   ├── ui/                       # PySide6 UI components
│   │   ├── main_window.py        # Main application window
│   │   ├── progress_dialog.py   # Real-time progress display
│   │   ├── results_window.py    # Job results viewer
│   │   ├── history_window.py    # Job history browser
│   │   └── settings_dialog.py   # Configuration UI
│   ├── workers/                  # Background threads
│   │   └── job_worker.py         # QThread job orchestration
│   ├── processors/               # Document processors (multiprocessing)
│   │   ├── search_replace.py    # Search & replace operations
│   │   ├── metadata.py           # Metadata management
│   │   ├── table_formatter.py   # Table formatting
│   │   ├── style_enforcer.py    # Style standardization
│   │   └── validator.py          # Document validation
│   ├── database/                 # SQLite database layer
│   │   ├── db_manager.py         # Database connection & operations
│   │   └── models.py             # Data models (jobs, results, backups)
│   ├── core/                     # Core infrastructure
│   │   ├── config.py             # Configuration management
│   │   ├── backup.py             # Backup creation/restoration
│   │   └── logger.py             # Logging setup
│   └── utils/                    # Utility functions
│       └── file_utils.py         # File handling helpers
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── test_documents/           # Sample .docx files for testing
├── assets/                       # Application resources
│   ├── icon.ico                  # Windows application icon
│   └── images/                   # UI images
├── config.json                   # Default configuration
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Python project metadata
├── docx_bulk_editor.spec        # PyInstaller spec file
├── PRD.txt                       # Product Requirements Document
└── CLAUDE.md                     # This file
```

**Runtime directories** (created at first launch):
```
docx_bulk_editor/
├── data/
│   ├── app.db                    # SQLite database
│   └── cache/                    # Temporary cache
├── backups/                      # Document backups (configurable)
│   └── YYYY-MM-DD/               # Daily backup folders
└── logs/                         # Application logs
    ├── app.log                   # Current log
    └── app.log.1                 # Rotated logs
```

## Testing Strategy

### Test Coverage Goal: >80%

This project has a comprehensive automated test suite with ~150-200 tests when fully implemented.

### Test Infrastructure

**Configuration Files**:
- `pytest.ini` - pytest configuration with markers, coverage settings
- `.coveragerc` - Coverage.py configuration (80% threshold)
- `tests/conftest.py` - Shared fixtures and test utilities
- `.github/workflows/test.yml` - CI/CD pipeline (GitHub Actions)

**Dependencies** (in `requirements-dev.txt`):
```
pytest==8.0.0              # Test framework
pytest-qt==4.3.1           # PySide6 GUI testing
pytest-cov==4.1.0          # Coverage reporting
pytest-xdist==3.5.0        # Parallel test execution
pytest-benchmark==4.0.0    # Performance benchmarking
pytest-mock==3.12.0        # Mocking utilities
hypothesis==6.98.0         # Property-based testing
black==24.2.0              # Code formatting
pylint==3.0.3              # Static analysis
mypy==1.8.0                # Type checking
ruff==0.2.2                # Fast linting
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures (docx_factory, test_db, qtbot, etc.)
├── README.md                # Comprehensive testing guide
├── test_documents/          # Static test .docx files + generation script
├── unit/                    # Unit tests (~60% of suite)
│   ├── test_search_replace.py
│   ├── test_metadata.py
│   ├── test_backup.py
│   ├── test_config.py
│   └── test_db_manager.py
├── integration/             # Integration tests (~25% of suite)
│   ├── test_worker_to_pool.py
│   ├── test_database_backup.py
│   └── test_end_to_end_job.py
├── gui/                     # GUI tests (~10% of suite)
│   ├── test_main_window.py
│   ├── test_progress_dialog.py
│   └── test_settings_dialog.py
└── performance/             # Performance tests (~5% of suite)
    ├── test_processing_speed.py
    ├── test_memory_usage.py
    └── test_startup_time.py
```

### Test Fixtures (Shared Resources)

Key fixtures in `tests/conftest.py`:

**Document Creation**:
```python
def test_example(docx_factory):
    """Create test documents programmatically."""
    doc = docx_factory(
        content="Paragraph 1\nParagraph 2",
        filename="test.docx",
        author="Test Author",
        add_table=True,
        add_heading=True
    )
    assert doc.exists()
```

**Pre-made Documents**:
- `sample_docx` - Simple 3-paragraph document
- `complex_docx` - Document with tables and formatting
- `large_docx` - 50+ paragraphs for performance tests
- `multiple_docx` - List of 10 test documents

**Environment**:
- `temp_workspace` - Isolated workspace with data/, backups/, logs/ structure
- `test_db` - In-memory SQLite database (fresh for each test)
- `mock_config` - Standard configuration for testing

**Windows-Specific**:
- `unicode_filename` - Filenames with non-ASCII characters (tëst_文档_файл.docx)
- `unc_path` - UNC network paths (\\\\localhost\\C$\\...)

**GUI Testing**:
- `qapp` - QApplication instance (session-scoped)
- `qtbot` - pytest-qt fixture for GUI interactions

### Test Markers (Categories)

Tests are organized with markers for selective execution:

```bash
# Run by category
pytest -m unit           # Unit tests (fast, isolated)
pytest -m integration    # Integration tests (multi-component)
pytest -m gui            # GUI tests (require display)
pytest -m performance    # Performance benchmarks
pytest -m windows        # Windows-specific tests
pytest -m slow           # Tests that take >5 seconds
pytest -m smoke          # Quick smoke tests for CI

# Combine markers
pytest -m "unit and not slow"  # Fast unit tests only
```

### Running Tests

**Quick Commands** (see `TESTING_QUICK_START.md` for full reference):

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html
start htmlcov/index.html  # View report

# Development workflow (fast feedback)
pytest -m "unit and not slow"

# Run tests in parallel (faster on multi-core)
pytest -n auto

# Run specific category
pytest tests/unit -v
pytest tests/gui -v
pytest tests/performance -m performance --benchmark-only

# Stop on first failure
pytest -x

# Before committing (full check)
pytest --cov=src --cov-fail-under=80
```

### Test Categories in Detail

**Unit Tests** (60% of suite):
- Test individual components in isolation
- Processors (search/replace, metadata, table formatting, validation)
- Database operations (CRUD, transactions, queries)
- Configuration management (loading, saving, validation)
- Backup/restore functionality
- File utilities and helpers
- **Target coverage**: 90-95%

**Integration Tests** (25% of suite):
- Test component interactions
- Worker thread → Multiprocessing pool communication
- Database → Backup manager coordination
- UI signals → Worker slots (end-to-end job flow)
- Error recovery and rollback scenarios
- **Target coverage**: 85%

**GUI Tests** (10% of suite) - Using pytest-qt:
```python
@pytest.mark.gui
def test_progress_dialog_updates(qtbot):
    """Test GUI interaction with qtbot."""
    dialog = ProgressDialog()
    qtbot.addWidget(dialog)

    # Spy on signals
    with qtbot.waitSignal(dialog.cancelled, timeout=1000):
        QTest.mouseClick(dialog.cancel_button, Qt.LeftButton)

    assert dialog.was_cancelled is True
```

GUI tests cover:
- File selection and validation
- Button states and user interactions
- Progress updates and cancellation
- Signal/slot connections
- Keyboard shortcuts
- **Target coverage**: 70%

**Performance Tests** (5% of suite) - Verify PRD targets:
```python
@pytest.mark.performance
def test_processing_speed(benchmark, docx_factory):
    """Verify processing speed meets 10-50 docs/min target."""
    doc = docx_factory(content="Test " * 100)
    config = {"find": "Test", "replace": "Sample"}

    result = benchmark(process_document, str(doc), config)

    assert result.success is True
    # Benchmark reports timing automatically
```

Performance targets:
- Startup time: < 3 seconds
- Processing speed: 10-50 documents/minute
- Memory usage: < 500MB for 500 documents
- UI responsiveness: 60 FPS during processing

**Windows-Specific Tests**:
```python
@pytest.mark.windows
def test_unicode_paths(unicode_filename, docx_factory):
    """Test Unicode character handling on Windows."""
    doc = docx_factory(
        content="Test",
        filename=unicode_filename.name  # tëst_文档_файл.docx
    )
    assert doc.exists()

@pytest.mark.windows
def test_unc_path_handling(unc_path):
    """Test UNC network path support."""
    assert str(unc_path).startswith("\\\\")
```

Tests for:
- Unicode paths and filenames (UTF-8 vs cp1252 encoding)
- UNC network paths (`\\server\share\file.docx`)
- File locking scenarios
- High DPI display scaling (125%, 150%, 200%)

### Coverage Requirements

**Overall target**: >80% code coverage

**Coverage by module**:
- Processors: 95%+ (critical business logic)
- Database: 90%+ (data integrity critical)
- Workers: 85%+ (threading complexity)
- UI: 70%+ (GUI testing harder)
- Utils: 95%+ (should be fully tested)

**Check coverage**:
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View detailed report
start htmlcov/index.html

# Fail if below 80%
pytest --cov=src --cov-fail-under=80
```

### CI/CD Integration

**GitHub Actions** (`.github/workflows/test.yml`):

Automated testing on:
- Every push to main/master
- Every pull request
- Python versions: 3.11, 3.12, 3.13

**Jobs**:
1. **test** - Unit + integration + GUI smoke tests (all Python versions)
2. **performance** - Benchmark tests (main branch only)
3. **slow-tests** - Full suite including slow tests (main branch only)

**Artifacts uploaded**:
- Coverage reports (HTML + XML for Codecov)
- Benchmark results (JSON)

**Quality checks**:
- Linting (ruff)
- Type checking (mypy)
- Code formatting (black)
- Coverage threshold enforcement (80%)

### Test Execution Times

Target execution times for fast feedback:

- Unit tests: <30 seconds
- Integration tests: <2 minutes
- GUI tests: <3 minutes
- Performance tests: <5 minutes
- **Full suite**: <6 minutes

Use markers to run fast tests during development:
```bash
pytest -m "unit and not slow"  # ~10-15 seconds
```

### Writing New Tests

**Pattern for Unit Tests**:
```python
"""Unit tests for module_name."""

import pytest
from src.module import function_to_test

@pytest.mark.unit
def test_basic_functionality(docx_factory):
    """Test basic operation."""
    doc = docx_factory(content="Test content")
    result = function_to_test(doc)
    assert result.success is True

@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
])
def test_multiple_cases(input, expected):
    """Test multiple scenarios."""
    assert function_to_test(input) == expected
```

**Best Practices**:
1. Test one behavior per test
2. Use descriptive test names
3. Follow Arrange-Act-Assert pattern
4. Use fixtures to avoid code duplication
5. Mark tests appropriately (unit, gui, slow, etc.)
6. Test edge cases and error conditions
7. Keep tests fast (mock slow operations)
8. Test behavior, not implementation

### Troubleshooting Tests

**Common Issues**:

| Issue | Solution |
|-------|----------|
| Qt platform plugin error | `pip install --force-reinstall PySide6` |
| Unicode decode errors (Windows) | Use `encoding='utf-8'` in all file operations |
| Database locked errors | Use in-memory DB: `DatabaseManager(":memory:")` |
| Multiprocessing fails | Add `freeze_support()` in `if __name__ == "__main__":` |
| Slow test execution | Run fast tests only: `pytest -m "unit and not slow"` |

### Documentation

**Full documentation**: `tests/README.md` (comprehensive 300+ line guide)
**Quick reference**: `TESTING_QUICK_START.md` (common commands)

Both documents cover:
- Detailed test organization
- Fixture usage examples
- Writing new tests
- Performance optimization
- CI/CD integration
- Troubleshooting guide

## Key Implementation Patterns

### Document Processor Template

All processors follow this pattern for multiprocessing compatibility:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

@dataclass
class ProcessorResult:
    """Must be picklable for multiprocessing."""
    success: bool
    file_path: str
    changes_made: int
    error_message: str | None = None
    duration_seconds: float = 0.0

def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    """
    Top-level function for multiprocessing.
    Must be defined at module level (not nested).
    """
    try:
        # Load document
        doc = Document(file_path)

        # Perform operation
        changes = perform_operation(doc, config)

        # Save if changes made
        if changes > 0:
            doc.save(file_path)

        return ProcessorResult(
            success=True,
            file_path=file_path,
            changes_made=changes
        )
    except Exception as e:
        return ProcessorResult(
            success=False,
            file_path=file_path,
            changes_made=0,
            error_message=str(e)
        )

def perform_operation(doc: Document, config: Dict[str, Any]) -> int:
    """Isolated operation logic (easier to test)."""
    # Implementation here
    pass
```

### Worker Thread Pattern

```python
from PySide6.QtCore import QThread, Signal

class JobWorker(QThread):
    # Define signals for UI updates (thread-safe)
    progress_updated = Signal(int, str)  # (percentage, current_file)
    job_completed = Signal(dict)  # results
    error_occurred = Signal(str)  # error_message

    def __init__(self, files: list[str], config: dict):
        super().__init__()
        self.files = files
        self.config = config
        self._cancelled = False

    def run(self):
        """Executes in background thread."""
        try:
            # Create multiprocessing pool
            with Pool(processes=cpu_count() - 1) as pool:
                # Submit jobs
                results = []
                for i, file_path in enumerate(self.files):
                    if self._cancelled:
                        break

                    result = pool.apply_async(
                        process_document,
                        args=(file_path, self.config)
                    )
                    results.append(result)

                    # Emit progress (thread-safe)
                    progress = int((i + 1) / len(self.files) * 100)
                    self.progress_updated.emit(progress, file_path)

                # Collect results
                final_results = [r.get() for r in results]
                self.job_completed.emit(final_results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self):
        """Thread-safe cancellation."""
        self._cancelled = True
```

### UI Integration Pattern

```python
class MainWindow(QMainWindow):
    def start_processing(self):
        """User clicked 'Start' button."""
        # Disable UI during processing
        self.start_button.setEnabled(False)

        # Create worker thread
        self.worker = JobWorker(self.selected_files, self.config)

        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.job_completed.connect(self.show_results)
        self.worker.error_occurred.connect(self.show_error)

        # Start worker (non-blocking)
        self.worker.start()

    def update_progress(self, percentage: int, current_file: str):
        """Called from worker thread via signal (thread-safe)."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Processing: {current_file}")

    def show_results(self, results: dict):
        """Called when job completes."""
        self.start_button.setEnabled(True)
        # Display results dialog
```

## Backup Strategy

**Before ANY modification**:
1. Copy original file to `backups/YYYY-MM-DD/{filename}.{timestamp}.backup.docx`
2. Store backup metadata in SQLite (`backups` table)
3. Auto-cleanup backups older than N days (default: 7)

**On error**: Offer one-click restoration from backup via UI

**Backup validation**: After creating backup, verify it's readable before proceeding with modification

## Database Schema

**SQLite** (`data/app.db`) with thread-safe access (`check_same_thread=False`):

Key tables:
- `jobs`: Processing job records (operation, config, status, timestamps)
- `job_results`: Per-file results for each job
- `backups`: Backup file registry with paths and metadata
- `settings`: User preferences (key-value store)
- `audit_log`: Event tracking for compliance

See PRD.txt section 9 (lines 989-1076) for complete schema.

## Performance Targets

From PRD (Section 13):
- **Startup time**: < 3 seconds
- **Processing speed**: 10-50 documents/minute (depends on operation)
- **Memory footprint**: < 500MB for 500 documents
- **UI responsiveness**: 60 FPS during processing (main thread never blocked)
- **.exe size**: < 200MB (PyInstaller bundle)

## Packaging for Distribution

### PyInstaller Configuration

Create `docx_bulk_editor.spec`:
- Single-file executable: `onefile=True`
- No console window: `console=False`
- Include data files: `config.json`, `assets/`
- Hidden imports: `multiprocessing`, `docx`, `lxml`, `PySide6`
- Exclude unnecessary: `tkinter`, `matplotlib`, `numpy` (if not used)
- UPX compression: `upx=True`

### Build Command

```bash
pyinstaller docx_bulk_editor.spec --clean
```

Output: `dist/docx_bulk_editor.exe` (~150-200MB)

## Common Pitfalls & Solutions

### ❌ Pitfall: Blocking UI with long operations
**✅ Solution**: Always use QThread workers for operations >100ms

### ❌ Pitfall: Forgetting `encoding='utf-8'` on Windows
**✅ Solution**: Use explicit UTF-8 in all file operations

### ❌ Pitfall: Multiprocessing failing in PyInstaller .exe
**✅ Solution**: Add `multiprocessing.freeze_support()` in `if __name__ == "__main__":` guard

### ❌ Pitfall: SQLite "database is locked" errors
**✅ Solution**: Use connection with `check_same_thread=False` and proper transaction management

### ❌ Pitfall: Nested functions in processors (can't pickle)
**✅ Solution**: Define all processor functions at module level for multiprocessing

## Specialized Agents Available

Three custom Claude Code agents are configured for this project:

1. **python-frontend-specialist**: PySide6 UI, QThread threading, Windows UI considerations
2. **python-backend-specialist**: python-docx, multiprocessing, SQLite, performance optimization
3. **python-qa-engineer**: pytest, GUI testing, performance testing, bug identification

Invoke with `@agent-name` in prompts for specialized assistance.

## TaskMaster Integration

This project uses TaskMaster AI MCP for task management. Tasks are stored in `.taskmaster/tasks/tasks.json`.

A Stop hook automatically prompts for the next task after each completion. See `CLAUDE_CODE_SETUP.md` for details.

## Reference Documentation

- **PRD**: See `PRD.txt` for complete architecture, features, and requirements
- **PySide6 Docs**: https://doc.qt.io/qtforpython/
- **python-docx**: https://python-docx.readthedocs.io/
- **PyInstaller**: https://pyinstaller.org/en/stable/

## Implementation Phases

Current: **Phase 0** - Project Setup

Phases (from PRD section 10):
1. **Phase 0-1**: Project setup, core infrastructure (Days 1-7)
2. **Phase 2**: Document processors migration (Days 8-14)
3. **Phase 3**: Core UI implementation (Days 15-21)
4. **Phase 4**: Advanced UI features (Days 22-28)
5. **Phase 5**: PyInstaller packaging (Days 29-32)
6. **Phase 6**: Testing & polish (Days 33-35)

## Quick Commands Reference

```bash
# ============================================================================
# Development Setup
# ============================================================================

# Activate virtual environment
.\venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Install development/testing dependencies
pip install -r requirements-dev.txt

# ============================================================================
# Running the Application
# ============================================================================

# Start application
python src/main.py

# ============================================================================
# Testing (see TESTING_QUICK_START.md for full reference)
# ============================================================================

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html
start htmlcov/index.html  # View coverage report

# Development workflow (fast tests only)
pytest -m "unit and not slow"

# Run tests in parallel (faster)
pytest -n auto

# Run by category
pytest -m unit           # Unit tests
pytest -m integration    # Integration tests
pytest -m gui            # GUI tests
pytest -m performance    # Performance benchmarks

# Before committing (full quality check)
pytest --cov=src --cov-fail-under=80
ruff check src/
mypy src/ --ignore-missing-imports
black src/

# ============================================================================
# Code Quality
# ============================================================================

# Format code
black src/

# Lint code
pylint src/

# Fast linting
ruff check src/

# Type checking
mypy src/ --ignore-missing-imports

# ============================================================================
# Packaging & Distribution
# ============================================================================

# Build executable
pyinstaller docx_bulk_editor.spec --clean

# Test executable (on clean VM recommended)
.\dist\docx_bulk_editor.exe
```
