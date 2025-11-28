# Testing Quick Start Guide

Fast reference for running tests in DOCX Bulk Editor.

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

## Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run fast tests only (development)
pytest -m "unit and not slow"

# Run specific category
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m gui           # GUI tests
pytest -m performance   # Performance tests

# Run specific file
pytest tests/unit/test_search_replace.py

# Run parallel (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Verbose output
pytest -v
```

## Test Markers

| Marker | Description | Command |
|--------|-------------|---------|
| `unit` | Unit tests (fast) | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |
| `gui` | GUI tests | `pytest -m gui` |
| `performance` | Performance benchmarks | `pytest -m performance` |
| `windows` | Windows-specific | `pytest -m windows` |
| `slow` | Slow tests (>5s) | `pytest -m slow` |
| `smoke` | Quick smoke tests | `pytest -m smoke` |

## Coverage

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View report
start htmlcov/index.html

# Fail if coverage < 80%
pytest --cov=src --cov-fail-under=80
```

## Before Committing

```bash
# Run full test suite with coverage check
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Run linting
ruff check src/

# Run type checking
mypy src/ --ignore-missing-imports

# Format code
black src/
```

## CI/CD

Tests run automatically on:
- Every push to main/master
- Every pull request
- Python 3.11, 3.12, 3.13

View results in GitHub Actions tab.

## Troubleshooting

```bash
# Unicode errors on Windows?
# → Ensure all file operations use encoding='utf-8'

# Qt platform plugin error?
# → pip install --force-reinstall PySide6

# Database locked errors?
# → Use in-memory DB in tests: DatabaseManager(":memory:")

# Slow tests?
# → pytest -m "unit and not slow"
```

## File Structure

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
├── integration/         # Integration tests
├── gui/                 # GUI tests
├── performance/         # Performance tests
└── test_documents/      # Test .docx files
```

## Writing New Tests

```python
import pytest

@pytest.mark.unit
def test_example(docx_factory):
    """Test description."""
    doc = docx_factory(content="Test")
    assert doc.exists()
```

## Help

```bash
# View pytest help
pytest --help

# List all available fixtures
pytest --fixtures

# List all test markers
pytest --markers

# Full documentation
# See: tests/README.md
```
