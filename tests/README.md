# DOCX Bulk Editor - Test Suite Documentation

Comprehensive automated test suite for the DOCX Bulk Editor application.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Test Fixtures](#test-fixtures)
- [Writing Tests](#writing-tests)
- [Coverage Requirements](#coverage-requirements)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Overview

The test suite is designed to ensure code quality, performance, and reliability of the DOCX Bulk Editor. It includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **GUI Tests**: Test PySide6 UI interactions
- **Performance Tests**: Verify speed and memory targets
- **Windows-Specific Tests**: Unicode paths, UNC paths, file locks

**Coverage Target**: >80% code coverage across the codebase

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Install development/testing dependencies
pip install -r requirements-dev.txt
```

### 2. Run All Tests

```bash
# Run full test suite
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Open coverage report in browser
start htmlcov/index.html  # Windows
```

### 3. Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# GUI tests
pytest -m gui

# Performance tests
pytest -m performance --benchmark-only

# Windows-specific tests
pytest -m windows
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and utilities
├── test_documents/          # Static test .docx files
│   ├── create_test_docs.py  # Script to generate test documents
│   ├── simple_doc.docx
│   ├── complex_doc.docx
│   ├── table_doc.docx
│   ├── unicode_doc.docx
│   └── ...
├── unit/                    # Unit tests (60% of suite)
│   ├── test_search_replace.py
│   ├── test_metadata.py
│   ├── test_backup.py
│   ├── test_config.py
│   ├── test_db_manager.py
│   └── ...
├── integration/             # Integration tests (25% of suite)
│   ├── test_worker_to_pool.py
│   ├── test_database_backup.py
│   └── test_end_to_end_job.py
├── gui/                     # GUI tests (10% of suite)
│   ├── test_main_window.py
│   ├── test_progress_dialog.py
│   └── test_settings_dialog.py
├── performance/             # Performance tests (5% of suite)
│   ├── test_processing_speed.py
│   ├── test_memory_usage.py
│   └── test_startup_time.py
└── README.md               # This file
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run specific test file
pytest tests/unit/test_search_replace.py

# Run specific test function
pytest tests/unit/test_search_replace.py::test_literal_case_sensitive

# Run tests matching pattern
pytest -k "search_replace"
```

### Using Test Markers

```bash
# Unit tests only (fast feedback)
pytest -m unit

# Exclude slow tests
pytest -m "not slow"

# GUI tests with verbose output
pytest -m gui -v

# Performance benchmarks only
pytest -m performance --benchmark-only

# Smoke tests for quick validation
pytest -m smoke
```

### Parallel Execution

```bash
# Run tests in parallel (faster on multi-core CPUs)
pytest -n auto

# Use specific number of workers
pytest -n 4

# Note: Don't use parallel for GUI tests (Qt threading conflicts)
pytest tests/unit tests/integration -n auto
pytest tests/gui  # Run sequentially
```

### Coverage Reporting

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Generate XML for CI/CD
pytest --cov=src --cov-report=xml

# Fail if coverage below 80%
pytest --cov=src --cov-report=term --cov-fail-under=80
```

## Test Fixtures

### Available Fixtures

All fixtures are defined in `tests/conftest.py`:

#### Document Creation Fixtures

```python
def test_example(docx_factory):
    """Use docx_factory to create custom test documents."""
    doc_path = docx_factory(
        content="Paragraph 1\nParagraph 2",
        filename="test.docx",
        author="Test Author",
        title="Test Title",
        add_table=True,
        add_heading=True
    )
    assert doc_path.exists()
```

**Pre-made fixtures:**
- `sample_docx`: Simple document with 3 paragraphs
- `complex_docx`: Document with tables and formatting
- `large_docx`: 50+ paragraphs for performance testing
- `multiple_docx`: List of 10 test documents

#### Environment Fixtures

```python
def test_workspace(temp_workspace):
    """Use temp_workspace for isolated file operations."""
    backup_dir = temp_workspace / "backups"
    assert backup_dir.exists()

    # temp_workspace structure:
    # workspace/
    # ├── data/
    # ├── backups/
    # └── logs/
```

#### Windows-Specific Fixtures

```python
@pytest.mark.windows
def test_unicode_paths(unicode_filename):
    """Test with Unicode characters in filename."""
    # unicode_filename = "tëst_文档_файл.docx"
    assert "文档" in unicode_filename.name

@pytest.mark.windows
def test_unc_paths(unc_path):
    """Test UNC network paths (Windows only)."""
    assert str(unc_path).startswith("\\\\")
```

#### Database Fixtures

```python
def test_database(test_db):
    """Use in-memory SQLite database."""
    job_id = test_db.create_job(operation="search_replace")
    assert job_id > 0
```

#### Qt Application Fixture

```python
@pytest.mark.gui
def test_gui_component(qtbot):
    """Use qtbot for GUI testing."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Simulate user click
    QTest.mouseClick(window.button, Qt.LeftButton)

    # Wait for signal
    with qtbot.waitSignal(window.completed, timeout=1000):
        window.start_processing()
```

### Helper Functions

```python
# Verify text in document
pytest.assert_docx_contains_text(doc_path, "expected text")

# Verify metadata
pytest.assert_docx_property(doc_path, "author", "John Doe")
```

## Writing Tests

### Unit Test Template

```python
"""
Unit tests for [module_name].

Tests cover:
- [Feature 1]
- [Feature 2]
- Edge cases and error handling
"""

import pytest
from src.module import function_to_test


@pytest.mark.unit
def test_basic_functionality():
    """Test basic operation."""
    result = function_to_test("input")
    assert result == "expected_output"


@pytest.mark.unit
def test_error_handling():
    """Test error conditions."""
    with pytest.raises(ValueError):
        function_to_test(invalid_input)


@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
    ("input3", "output3"),
])
def test_multiple_cases(input, expected):
    """Test multiple input/output pairs."""
    assert function_to_test(input) == expected
```

### GUI Test Template

```python
@pytest.mark.gui
def test_button_interaction(qtbot):
    """Test GUI button interaction."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Verify initial state
    assert window.button.isEnabled() is False

    # Perform action
    window.enable_button()

    # Verify state changed
    assert window.button.isEnabled() is True

    # Simulate click
    QTest.mouseClick(window.button, Qt.LeftButton)

    # Verify result
    assert window.action_performed is True
```

### Performance Test Template

```python
@pytest.mark.performance
@pytest.mark.slow
def test_performance_benchmark(benchmark):
    """Test performance meets targets."""
    result = benchmark(function_to_test, "input")

    # Benchmark automatically measures timing
    assert result.success is True
```

## Coverage Requirements

### Target Coverage by Module

| Module | Coverage Target | Priority |
|--------|----------------|----------|
| Processors | 95%+ | Critical |
| Database | 90%+ | Critical |
| Workers | 85%+ | High |
| UI | 70%+ | Medium |
| Utils | 95%+ | High |

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# View HTML report with line-by-line coverage
pytest --cov=src --cov-report=html
start htmlcov/index.html
```

### Coverage Configuration

Coverage settings are in `.coveragerc`:
- Minimum threshold: 80%
- Excludes test files, virtual environment
- Branch coverage enabled
- Fails build if below threshold

## CI/CD Integration

### GitHub Actions Workflow

Automated testing runs on:
- **Every push** to main/master
- **Every pull request**
- **Three Python versions**: 3.11, 3.12, 3.13

Workflow jobs:
1. **test**: Unit, integration, GUI (smoke tests)
2. **performance**: Benchmarks (main branch only)
3. **slow-tests**: Full suite including slow tests (main branch only)

### Workflow File

Location: `.github/workflows/test.yml`

### Viewing Results

- Test results: GitHub Actions tab
- Coverage reports: Codecov.io (if configured)
- Benchmark results: Artifacts in GitHub Actions

## Troubleshooting

### Common Issues

#### Qt platform plugin error (GUI tests)

```
qt.qpa.plugin: Could not find the Qt platform plugin "windows"
```

**Solution**: Ensure PySide6 is installed correctly:
```bash
pip install --force-reinstall PySide6
```

#### Tests fail with encoding errors (Windows)

```
UnicodeDecodeError: 'charmap' codec can't decode...
```

**Solution**: Ensure all file operations use `encoding='utf-8'`:
```python
with open('file.txt', 'r', encoding='utf-8') as f:
    content = f.read()
```

#### Database locked errors

```
sqlite3.OperationalError: database is locked
```

**Solution**: Use in-memory database for tests:
```python
db = DatabaseManager(":memory:")
```

#### Multiprocessing tests fail in PyInstaller

**Solution**: Add freeze_support() and use `if __name__ == "__main__":` guard:
```python
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
```

#### Slow test execution

**Solution**: Run only fast tests during development:
```bash
pytest -m "unit and not slow"
```

### Getting Help

- Check test output with `-v` flag for verbose details
- Use `-x` to stop on first failure for debugging
- Use `--pdb` to drop into debugger on failure
- Review test logs in `logs/` directory (if applicable)

## Performance Targets

From PRD Section 13:

| Metric | Target | Test |
|--------|--------|------|
| Processing speed | 10-50 docs/min | `test_processing_speed.py` |
| Startup time | < 3 seconds | `test_startup_time.py` |
| Memory usage | < 500MB (500 docs) | `test_memory_usage.py` |
| UI responsiveness | 60 FPS | `test_ui_responsiveness.py` |

## Best Practices

1. **Test one thing per test**: Each test should verify a single behavior
2. **Use descriptive names**: `test_user_can_upload_file` not `test_upload`
3. **Arrange-Act-Assert**: Structure tests clearly (setup → execute → verify)
4. **Use fixtures**: Avoid code duplication with shared fixtures
5. **Mark tests appropriately**: Use markers (unit, gui, slow, etc.)
6. **Test edge cases**: Empty inputs, large inputs, invalid inputs
7. **Mock external dependencies**: Use mocks for file I/O, network, etc.
8. **Keep tests fast**: Unit tests should run in milliseconds
9. **Test behavior, not implementation**: Focus on what code does, not how
10. **Write tests first**: Consider TDD for complex features

## Contributing Tests

When adding new features:

1. Write tests first (TDD approach)
2. Ensure >80% coverage for new code
3. Add appropriate markers
4. Update this README if adding new test categories
5. Run full test suite before committing:
   ```bash
   pytest --cov=src --cov-fail-under=80
   ```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-qt documentation](https://pytest-qt.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [PySide6 Testing](https://doc.qt.io/qtforpython/tutorials/basictutorial/qttestintro.html)
