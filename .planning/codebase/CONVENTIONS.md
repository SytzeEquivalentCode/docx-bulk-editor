# Coding Conventions

**Analysis Date:** 2026-01-30

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules
- Processor modules: `{operation}_name.py` (e.g., `search_replace.py`, `style_enforcer.py`, `table_formatter.py`)
- Test files: `test_{module_name}.py` for unit tests, `test_{component}.py` for integration tests
- UI files: `{component}_window.py` or `{component}_dialog.py` (e.g., `main_window.py`, `progress_dialog.py`, `settings_dialog.py`)
- Worker threads: `{operation}_worker.py` (e.g., `job_worker.py`)
- Config/core: descriptive names like `config.py`, `logger.py`, `backup.py`, `db_manager.py`

**Functions:**
- `snake_case` for all function names
- Private helper functions prefixed with `_` (e.g., `_compile_pattern`, `_check_heading_hierarchy`, `_standardize_fonts`)
- Top-level processor functions named `process_document()` (entry point for multiprocessing)
- Main operation logic in `perform_{operation}()` function (e.g., `perform_search_replace()`, `perform_style_enforcement()`)
- Validation/check functions named `_check_{item}()` or `_validate_{item}()` (e.g., `_check_heading_hierarchy()`, `_check_empty_paragraphs()`)
- Formatting/formatting functions named `_format_{item}()` (e.g., `_format_validation_report()`)

**Variables:**
- `snake_case` for all variable names
- Constants in `UPPER_SNAKE_CASE` (rare in this codebase; configuration uses lowercase keys)
- Class attributes in `snake_case`
- Loop variables: single letter acceptable for simple iteration (`i`, `row`, `col`), descriptive for complex operations
- Boolean variables prefixed with `is_`, `has_`, `should_`, `can_` (e.g., `use_regex`, `case_sensitive`, `whole_words`)
- Config variables match key names in JSON config exactly (e.g., `search_term`, `replace_term`, `font_size_pt`)

**Types:**
- Type hints used throughout (Python 3.11+ syntax: `str | None` instead of `Optional[str]`)
- Union types use `|` syntax: `Path | str`
- Generic types: `Dict[str, Any]`, `List[str]`, `Optional[str]`
- Dataclass decorators for result objects: `@dataclass` on `ProcessorResult`

## Code Style

**Formatting:**
- Tool: Black (configured in `pyproject.toml`)
- Line length: 120 characters
- String quotes: double quotes (`"`)
- Indentation: 4 spaces

**Configuration:**
```toml
[tool.black]
line-length = 120
target-version = ['py311']
```

**Linting:**
- Tool: ruff (for fast linting)
- Additional tools: pylint, mypy for deeper analysis
- Run before commit: `ruff check src/`, `mypy src/ --ignore-missing-imports`

## Import Organization

**Order:**
1. Standard library (`import sys`, `import os`, `from pathlib import Path`)
2. Third-party libraries (`from PySide6.QtWidgets import ...`, `from docx import Document`, `import pytest`)
3. Local imports (`from src.processors import ProcessorResult`, `from src.core.config import ConfigManager`)

**Path Aliases:**
- No path aliases configured; all imports use absolute paths from project root
- Example: `from src.processors.search_replace import process_document`
- Relative imports not used (even though possible within modules)

**Examples from codebase:**
```python
# src/main.py
import sys
import multiprocessing
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.core.config import ConfigManager
from src.core.logger import setup_logger
from src.database.db_manager import DatabaseManager
from src.ui.main_window import MainWindow
```

```python
# src/processors/search_replace.py
import re
import time
from typing import Dict, Any
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table

from src.processors import ProcessorResult
```

## Error Handling

**Patterns:**
- Try-except at processor entry points: `process_document()` catches all exceptions and returns `ProcessorResult` with `success=False` and `error_message`
- No uncaught exceptions from processor functions; all errors converted to `ProcessorResult` objects for multiprocessing serialization
- Context managers used for resource cleanup: `with db.get_connection() as conn:` (database), `with open(..., encoding='utf-8') as f:` (files)
- Logger used for error reporting: `logger.error()`, `logger.exception()` with full traceback

**Windows UTF-8 Encoding (CRITICAL):**
- **All file operations explicitly specify `encoding='utf-8'`**
- Database connections use explicit UTF-8 setup: `encoding='utf-8'` in `json.dump()`, SQLite with Row factory
- JSON files: `open(..., 'r', encoding='utf-8')` and `open(..., 'w', encoding='utf-8')`
- RotatingFileHandler: `encoding='utf-8'` parameter
- Example from `src/core/config.py`:
```python
with open(self.config_path, 'r', encoding='utf-8') as f:
    self._config = json.load(f)
```

**Exception handling philosophy:**
- Processor errors don't crash application; they're recorded in `ProcessorResult`
- UI errors are caught at main thread level; critical errors show dialog
- Database errors: context manager automatically rolls back on exception
- Invalid file paths or corrupt documents: caught and reported in results

## Logging

**Framework:** Built-in `logging` module with `RotatingFileHandler` (not print statements)

**Patterns:**
- Get logger: `logger = setup_logger()` or `logger = get_logger()`
- Log levels: `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`, `logger.exception()`
- Use `logger.exception()` when catching exceptions to include full traceback
- All loggers configured with UTF-8 encoding for Windows compatibility

**Configuration:**
- File handler: DEBUG level, rotating at 10MB, keeps 10 backups (`logs/app.log`)
- Console handler: configurable level (default INFO)
- Format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- Example from `src/main.py`:
```python
logger = setup_logger()
logger.info('='* 60)
logger.info('DOCX Bulk Editor v1.0.0 - Application Starting')
logger.exception(f'Fatal error during application startup: {e}')
```

## Comments

**When to Comment:**
- Complex algorithms (pattern compilation, heading hierarchy checking)
- Non-obvious behavior or workarounds
- Windows-specific code (Unicode handling, path conversion)
- Configuration dictionary keys that aren't self-documenting

**JSDoc/TSDoc:**
- Python docstrings used extensively for all functions, classes, methods
- Triple-quoted strings (`"""..."""`) for module, class, and function docstrings
- Format: Google-style docstrings with Args, Returns, Examples sections

**Example from `src/processors/search_replace.py`:**
```python
def perform_search_replace(doc: Document, config: Dict[str, Any]) -> int:
    """Perform search and replace operations on a document.

    Args:
        doc: python-docx Document object
        config: Configuration dictionary containing:
            - search_term: Text or regex pattern to search for
            - replace_term: Replacement text
            - use_regex: If True, treat search_term as regex pattern
            - case_sensitive: If True, perform case-sensitive matching

    Returns:
        Total number of replacements made across all document sections
    """
```

## Function Design

**Size:**
- Aim for functions under 50 lines for testability
- Processor functions (`process_document`) tend to be 20-30 lines
- Helper functions (`_check_heading_hierarchy`) vary 30-60 lines depending on complexity

**Parameters:**
- Use type hints on all parameters
- Config parameters passed as `Dict[str, Any]`
- No mutable default arguments
- Processor functions take `(file_path: str, config: Dict[str, Any])`

**Return Values:**
- Processor functions return `ProcessorResult` (dataclass)
- Helper functions return primitives (`int` for change count, `bool` for validation checks, `List[Dict]` for issues)
- Context managers return generators with `yield`

**Example structure:**
```python
def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    """Entry point for multiprocessing."""
    try:
        # Load and operate
        result = perform_operation(doc, config)
        return ProcessorResult(success=True, changes_made=result, ...)
    except Exception as e:
        return ProcessorResult(success=False, error_message=str(e), ...)

def perform_operation(doc: Document, config: Dict[str, Any]) -> int:
    """Main operation logic."""
    changes = 0
    # Iterate and modify
    for item in doc.items:
        changes += helper_function(item, config)
    return changes

def _helper_function(item, config: Dict[str, Any]) -> int:
    """Single responsibility."""
    # Do one thing
    return changes_count
```

## Module Design

**Exports:**
- `__all__` used in `__init__.py` files to define public API
- Example from `src/processors/__init__.py`:
```python
@dataclass
class ProcessorResult:
    """Picklable result for multiprocessing compatibility."""
    ...

__all__ = ['ProcessorResult']
```

**Barrel Files:**
- `src/processors/__init__.py` exports `ProcessorResult` (used by all processors)
- `src/ui/__init__.py` exports UI components
- `src/core/__init__.py` exports core infrastructure
- Each processor is standalone module (no re-export needed)

**Module purpose examples:**
- `src/processors/search_replace.py`: Only contains `process_document()`, `perform_search_replace()`, and `_compile_pattern()`
- `src/database/db_manager.py`: Single `DatabaseManager` class with all database operations
- `src/core/config.py`: Single `ConfigManager` class for configuration management
- `src/core/logger.py`: Module-level functions `setup_logger()` and `get_logger()`

## Multiprocessing Compatibility

**Critical constraint:** Functions must be picklable for multiprocessing.Pool

**Rules:**
- All processor functions defined at module level (not nested in classes)
- No lambda functions in processors
- Only basic types in `ProcessorResult` dataclass (bool, str, int, float, Optional)
- Configuration passed as `Dict[str, Any]` (picklable)
- No closure variables or external state

**Pattern:**
```python
# ✅ CORRECT - Module-level function
def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    # Implementation
    pass

# ❌ WRONG - Nested function (not picklable)
class Processor:
    def process_document(self, file_path: str, config: Dict[str, Any]) -> ProcessorResult:
        # Not callable from multiprocessing.Pool
        pass
```

## Threading Patterns

**Main Thread (UI only):**
- No blocking operations; all long-running work delegated to QThread workers
- Qt signals/slots for thread-safe communication

**Worker Threads (QThread):**
- Inherit from `QThread`, implement `run()` method
- Emit signals for progress updates: `self.progress_updated.emit(percent, filename)`
- Use multiprocessing.Pool for CPU-bound work
- Catch all exceptions and emit error signal

**Example from codebase pattern:**
```python
class JobWorker(QThread):
    progress_updated = Signal(int, str)
    job_completed = Signal(dict)
    error_occurred = Signal(str)

    def run(self):
        try:
            with Pool(processes=cpu_count() - 1) as pool:
                # Submit work
                self.progress_updated.emit(percent, file)
            self.job_completed.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))
```

## Database Patterns

**Thread safety:**
- `check_same_thread=False` on SQLite connections to allow multi-threaded access
- Context manager pattern for connection handling: `with db.get_connection() as conn:`
- Automatic commit on success, rollback on exception

**Encoding:**
- UTF-8 support explicit in SQLite configuration
- File paths stored as strings (converted from Path objects)

**Transactions:**
- Context manager handles commit/rollback automatically
- No explicit transaction management needed

---

*Convention analysis: 2026-01-30*
