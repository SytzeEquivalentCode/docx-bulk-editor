# Testing Patterns

**Analysis Date:** 2026-01-30

## Test Framework

**Runner:**
- pytest 8.0.0
- Config file: `pytest.ini`
- Additional plugins: pytest-qt (4.3.1), pytest-cov (4.1.0), pytest-mock (3.12.0), pytest-xdist (3.5.0), pytest-benchmark (4.0.0)

**Run Commands:**
```bash
pytest                                    # Run all tests with coverage
pytest -m "unit and not slow"            # Fast unit tests (development)
pytest -n auto                           # Run tests in parallel
pytest --cov=src --cov-report=html      # Generate HTML coverage report
pytest -m unit                           # Unit tests only
pytest -m integration                    # Integration tests only
pytest -m gui                            # GUI tests only
pytest -m performance --benchmark-only   # Performance benchmarks only
```

**Coverage Configuration:**
- Target: >80% overall coverage
- HTML reports generated automatically to `htmlcov/`
- XML reports generated for CI/CD integration
- Command line: `--cov-report=term-missing:skip-covered`

## Test File Organization

**Location:**
- Unit tests and integration tests co-located in `tests/` directory
- Separated by type (`tests/unit/`, `tests/integration/`, `tests/gui/`, `tests/performance/`)
- Test documents stored in `tests/test_documents/`
- Shared fixtures in `tests/conftest.py`

**Naming:**
- Test files: `test_{component}.py` (e.g., `test_search_replace.py`, `test_backup.py`)
- Test functions: `test_{action}_{scenario}` (e.g., `test_literal_case_sensitive()`, `test_create_backup_success()`)
- Test classes: `Test{Component}{Aspect}` (e.g., `TestHeadingHierarchy`, `TestBackupCreation`, `TestDatabaseInitialization`)

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures (qapp, docx_factory, test_db, etc.)
├── unit/                          # Unit tests (~60% of suite)
│   ├── test_search_replace.py    # Processor tests
│   ├── test_search_replace_patterns.py
│   ├── test_metadata.py
│   ├── test_style_enforcer.py
│   ├── test_validator.py
│   ├── test_table_formatter.py
│   ├── test_backup.py            # Core infrastructure tests
│   ├── test_config.py
│   ├── test_db_manager.py
│   ├── test_logger.py
│   └── test_processor_result.py
├── integration/                   # Integration tests (~25% of suite)
│   ├── test_core_infrastructure.py
│   └── test_end_to_end_job.py
├── gui/                           # GUI tests (~10% of suite)
│   ├── test_main_window.py
│   ├── test_progress_dialog.py
│   └── test_settings_dialog.py
├── performance/                   # Performance tests (~5% of suite)
│   └── test_processing_speed.py
└── test_documents/                # Test data
    ├── create_test_docs.py
    └── create_specialized_test_docs.py
```

## Test Structure

**Suite Organization:**

Unit tests use class-based organization for related tests:

```python
class TestComponentName:
    """Test suite for component_name."""

    def test_action_succeeds(self, fixture):
        """Describe expected behavior."""
        # Arrange
        data = fixture

        # Act
        result = function_under_test(data)

        # Assert
        assert result.success is True
```

Integration tests may use flat function structure or classes depending on complexity:

```python
class TestCoreInfrastructureIntegration:
    """Tests for multi-component interactions."""

    def test_full_initialization(self, clean_environment):
        """Test all components work together."""
        # Arrange-Act-Assert pattern
        pass
```

**Patterns:**
- Arrange-Act-Assert (AAA) pattern used consistently
- One assertion per test (or closely related assertions)
- Descriptive test names that explain the scenario
- Test docstrings explain what's being tested and why

## Mocking

**Framework:** pytest-mock (built on unittest.mock)

**Patterns:**
- Fixtures used for test objects (docx_factory, sample_docx, complex_docx, test_db, test_config)
- Mocking used sparingly; prefer real objects when possible
- Mock database with in-memory SQLite: `DatabaseManager(":memory:")`
- Qt signals/slots tested with pytest-qt's `qtbot` fixture

**What to Mock:**
- Database connections (use in-memory database fixture instead)
- File I/O that's tested separately (use fixtures with tmp_path)
- External APIs/services (not applicable in current codebase)
- Long-running operations in integration tests (time-sensitive operations)

**What NOT to Mock:**
- Document creation (use docx_factory fixture)
- Configuration loading (use test_config fixture)
- Logger (let it log during tests; log file captured)
- Database schema (run actual schema in test database)

**Example from `tests/unit/test_search_replace.py`:**
```python
def test_literal_special_chars_escaped():
    """Test literal search escapes special regex characters."""
    special_chars = r'.*+?[]{}()^$|\\'

    pattern = _compile_pattern(special_chars, use_regex=False, case_sensitive=True, whole_words=False)

    # Should match the literal string, not interpret as regex
    assert pattern.search(special_chars) is not None
    assert pattern.search('anything') is None  # .* should not match anything
```

## Fixtures and Factories

**Test Data:**

Key fixtures from `tests/conftest.py`:

**Document Fixtures:**
- `docx_factory(content, filename, author, title, add_table, add_heading)` - Factory for creating test documents
- `sample_docx` - Pre-built simple document (heading + 3 paragraphs)
- `complex_docx` - Pre-built document with tables and formatting
- `multiple_docx` - List of 10 test documents (for batch processing tests)

**Environment Fixtures:**
- `temp_workspace` - Isolated workspace with `data/`, `backups/`, `logs/` directories
- `test_config` - ConfigManager with test settings pointing to temp_workspace
- `test_db` - DatabaseManager with in-memory SQLite database

**Special Fixtures:**
- `qapp` - Single QApplication instance (session-scoped)
- `qtbot` - pytest-qt fixture for GUI interaction and signal testing
- `unicode_filename` - Path with Unicode characters (Windows testing)
- `unc_path` - UNC network path simulation (Windows-only)
- `mock_config` - Dictionary with standard test configuration

**Location:**
- Main fixtures: `tests/conftest.py`
- Component-specific fixtures: defined within test file (e.g., `tests/unit/test_backup.py` defines `db_manager`, `backup_dir`, `sample_docx`)

**Example fixture usage:**
```python
def test_search_replace(docx_factory):
    """Create test documents programmatically."""
    doc_path = docx_factory(
        content="Hello world\nGoodbye world",
        filename="test.docx",
        author="Test Author"
    )
    assert doc_path.exists()

    # Operate on document
    result = process_document(str(doc_path), config)
    assert result.success is True
```

## Coverage

**Requirements:** 80% minimum code coverage (enforced in CI/CD)

**Coverage by module:**
- Processors (search_replace, metadata, style_enforcer, validator, table_formatter): 90-95%
- Database (db_manager): 90%+
- Core infrastructure (config, logger, backup): 85-90%
- UI: 70% (harder to test GUI)
- Utils: 95%+

**View Coverage:**
```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser
start htmlcov/index.html

# View missing lines
cat htmlcov/status.json  # Detailed coverage data
```

**Coverage reports automatically generated:**
- HTML: `htmlcov/index.html` (visual coverage browser)
- XML: `coverage.xml` (for CI/CD integration with Codecov)
- Terminal: `--cov-report=term-missing:skip-covered` (shows which lines not covered)

## Test Types

**Unit Tests** (60% of suite, ~90-95 tests):
- Scope: Single function or class in isolation
- Speed: <100ms each
- Approach: Direct function calls with mocked dependencies
- Location: `tests/unit/`
- Examples: Testing `_compile_pattern()`, `_check_heading_hierarchy()`, Config.get(), DatabaseManager.insert_job()

**Integration Tests** (25% of suite, ~30-40 tests):
- Scope: Multiple components working together
- Speed: 1-5 seconds
- Approach: Real objects, minimal mocking
- Location: `tests/integration/`
- Examples: Config → Logger → Database chain, Worker → Pool → Database flow, UTF-8 round-trip through all layers

**GUI Tests** (10% of suite, ~15 tests):
- Scope: PySide6 UI components and interactions
- Speed: 1-3 seconds (requires event loop)
- Approach: pytest-qt's qtbot fixture for interaction
- Location: `tests/gui/`
- Examples: File selection, button clicks, signal emission, window state
- Pattern:
```python
@pytest.mark.gui
def test_main_window_initialization(qtbot, test_config, test_db):
    """Test MainWindow starts up correctly."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    assert window.isVisible() is False  # Not shown until show() called
    window.show()
    assert window.isVisible() is True
```

**Performance Tests** (5% of suite, ~5 tests):
- Scope: Benchmarking and resource usage
- Speed: Variable (includes time measurement)
- Approach: pytest-benchmark for accurate measurements
- Location: `tests/performance/`
- Markers: `@pytest.mark.performance`, `@pytest.mark.slow`
- Command: `pytest -m performance --benchmark-only`
- Examples: Processing speed (target 10-50 docs/min), memory usage

## Test Markers

Markers defined in `pytest.ini`:

```ini
markers =
    unit: Unit tests (fast, isolated component tests)
    integration: Integration tests (multi-component interactions)
    gui: GUI tests (require display, use pytest-qt)
    performance: Performance benchmarks and profiling
    windows: Windows-specific tests (paths, Unicode, file locks)
    slow: Tests that take >5 seconds to run
    smoke: Quick smoke tests for CI fast feedback
```

**Usage:**
```python
@pytest.mark.unit
def test_basic_functionality():
    """Fast, isolated test."""
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_multi_component_flow():
    """Integration test that takes time."""
    pass

@pytest.mark.gui
def test_button_click(qtbot):
    """Requires Qt event loop."""
    pass

@pytest.mark.windows
def test_unicode_path(unicode_filename):
    """Windows-specific behavior."""
    pass
```

**Running by marker:**
```bash
pytest -m unit                     # Fast tests only
pytest -m "unit and not slow"     # Fastest tests
pytest -m integration              # Integration tests
pytest -m gui                      # GUI tests
pytest -m "not gui"                # Skip GUI tests
```

## Common Patterns

**Async Testing (Qt Signals):**

Using pytest-qt's `qtbot` to wait for signals:

```python
@pytest.mark.gui
def test_progress_signal_updates_ui(qtbot):
    """Test signal emission updates UI."""
    dialog = ProgressDialog()
    qtbot.addWidget(dialog)

    # Spy on signal
    with qtbot.waitSignal(dialog.progress_updated, timeout=1000):
        dialog.update_progress(50, "test.docx")

    assert dialog.progress_bar.value() == 50
```

**Error Testing:**

Testing error cases and exception handling:

```python
@pytest.mark.unit
def test_invalid_regex_raises_error(docx_factory):
    """Test invalid regex pattern is caught."""
    doc_path = docx_factory()
    config = {"search_term": "[invalid", "use_regex": True}

    result = process_document(str(doc_path), config)

    assert result.success is False
    assert "invalid" in result.error_message.lower()
```

**Parametrized Testing:**

Testing multiple scenarios with one test:

```python
@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
    ("input3", "output3"),
])
def test_multiple_cases(input, expected):
    """Test multiple scenarios."""
    assert function_under_test(input) == expected
```

**Fixture-based Testing:**

```python
class TestBackupManagerInitialization:
    """Test suite for BackupManager initialization."""

    def test_initialization(self, backup_dir, db_manager):
        """Test initialization with correct parameters."""
        manager = BackupManager(backup_dir, db_manager, retention_days=14)

        assert manager.backup_dir == backup_dir
        assert manager.db_manager == db_manager
        assert manager.retention_days == 14

    def test_backup_directory_created(self, backup_dir, db_manager):
        """Test backup directory is created automatically."""
        assert not backup_dir.exists()

        manager = BackupManager(backup_dir, db_manager)

        assert backup_dir.exists()
```

## CI/CD Integration

**GitHub Actions** (`.github/workflows/test.yml`):

Automated testing on:
- Every push to main/master
- Every pull request
- Python versions: 3.11, 3.12, 3.13

**Jobs:**
1. **test** - Unit + integration + GUI smoke tests (all Python versions)
2. **performance** - Benchmark tests (main branch only)
3. **slow-tests** - Full suite including slow tests (main branch only)

**Quality checks:**
- Linting: ruff
- Type checking: mypy
- Code formatting: black
- Coverage threshold: 80% minimum

**Artifacts uploaded:**
- Coverage reports (HTML + XML)
- Benchmark results (JSON)

## Test Execution Times

Target execution times for feedback speed:

- Unit tests: <30 seconds (with coverage)
- Integration tests: <2 minutes
- GUI tests: <3 minutes
- Performance tests: <5 minutes
- **Full suite: <6 minutes**

**Development workflow:**
```bash
# Fast feedback (10-15 seconds)
pytest -m "unit and not slow"

# Complete unit check (30 seconds)
pytest -m unit --cov=src

# Before commit (6 minutes)
pytest --cov=src --cov-fail-under=80
```

## Writing New Tests

**Pattern for Unit Tests:**

```python
"""Unit tests for module_name."""

import pytest
from src.module import function_to_test


@pytest.mark.unit
def test_basic_functionality(docx_factory):
    """Test basic operation succeeds."""
    # Arrange
    doc = docx_factory(content="Test content")
    config = {"key": "value"}

    # Act
    result = function_to_test(doc, config)

    # Assert
    assert result.success is True


@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
])
def test_multiple_cases(input, expected):
    """Test multiple scenarios."""
    assert function_to_test(input) == expected


@pytest.mark.unit
def test_error_handling():
    """Test error case is handled."""
    result = function_to_test(invalid_input)
    assert result.success is False
```

**Pattern for Class-based Tests:**

```python
class TestComponentName:
    """Test suite for ComponentName."""

    def test_initialization(self, fixture):
        """Test component initializes correctly."""
        component = ComponentName(fixture)
        assert component.property == expected_value

    def test_operation_succeeds(self, fixture):
        """Test operation works as expected."""
        component = ComponentName(fixture)
        result = component.operation()
        assert result.success is True

    def test_error_case(self, fixture):
        """Test error is handled properly."""
        component = ComponentName(fixture)
        result = component.operation(invalid_input)
        assert result.success is False
```

**Best Practices:**
1. Test one behavior per test
2. Use descriptive test names that explain the scenario
3. Follow Arrange-Act-Assert pattern
4. Use fixtures to avoid code duplication
5. Mark tests appropriately (@pytest.mark.unit, @pytest.mark.slow, etc.)
6. Test edge cases and error conditions
7. Keep tests fast (mock slow operations)
8. Test behavior, not implementation details
9. Parametrize tests with multiple inputs
10. Use clear assertion messages when needed

## Troubleshooting Tests

**Common Issues:**

| Issue | Solution |
|-------|----------|
| Qt platform plugin error | `pip install --force-reinstall PySide6` |
| Unicode decode errors | Always use `encoding='utf-8'` in all file operations |
| Database locked errors | Use in-memory DB in fixtures: `DatabaseManager(":memory:")` |
| Multiprocessing fails in tests | Ensure processors are at module level, not nested |
| Slow test execution | Run fast tests only: `pytest -m "unit and not slow"` |
| Import errors | Ensure `tests/` directory is in Python path (pytest handles this) |
| Signal timeout in GUI tests | Increase timeout or verify signal is actually emitted |
| Fixture scope issues | Use appropriate scope (function=default, session=qapp) |
| Temporary file cleanup | Use pytest's `tmp_path` fixture (auto-cleaned) |

## Test Dependencies

**From requirements-dev.txt:**
```
pytest==8.0.0              # Core testing framework
pytest-qt==4.3.1           # Qt/PySide6 testing
pytest-cov==4.1.0          # Coverage reporting
pytest-timeout==2.2.0      # Prevent hanging tests
pytest-mock==3.12.0        # Mocking utilities
pytest-xdist==3.5.0        # Parallel execution
pytest-benchmark==4.0.0    # Performance benchmarking
coverage[toml]==7.4.0      # Coverage measurement
hypothesis==6.98.0         # Property-based testing (edge cases)
faker==24.0.0              # Generate fake test data
freezegun==1.4.0           # Mock datetime for tests
```

---

*Testing analysis: 2026-01-30*
