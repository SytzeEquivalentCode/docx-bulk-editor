# Codebase Structure

**Analysis Date:** 2026-01-30

## Directory Layout

```
docx-bulk-editor/
├── src/                          # Application source code
│   ├── main.py                   # Application entry point (multiprocessing setup, Qt initialization)
│   ├── core/                     # Infrastructure & core services
│   │   ├── config.py             # Configuration management (JSON loading/saving, dot notation)
│   │   ├── logger.py             # Logging setup (rotating file handler, UTF-8 encoding)
│   │   ├── backup.py             # Backup creation & management (daily subdirs, validation)
│   │   └── __init__.py
│   ├── database/                 # Data persistence
│   │   ├── db_manager.py         # Thread-safe SQLite wrapper (context manager pattern)
│   │   ├── migrate_add_duration.py  # Database schema migrations
│   │   └── __init__.py
│   ├── processors/               # Document processing (multiprocessing entry points)
│   │   ├── __init__.py           # ProcessorResult dataclass (picklable for multiprocessing)
│   │   ├── search_replace.py     # Search & replace with regex, whole words, case sensitivity
│   │   ├── metadata.py           # Metadata management (author, title, subject, etc.)
│   │   ├── table_formatter.py    # Table formatting (cell spacing, alignment, borders)
│   │   ├── style_enforcer.py     # Style standardization (fonts, sizes, colors)
│   │   └── validator.py          # Document validation (heading hierarchy, placeholders, etc.)
│   ├── workers/                  # Background threading
│   │   ├── job_worker.py         # QThread orchestrating multiprocessing pool
│   │   └── __init__.py
│   ├── ui/                       # PySide6 GUI components
│   │   ├── main_window.py        # Main application window (operations, config, file selection)
│   │   ├── progress_dialog.py    # Real-time progress monitoring (modal dialog)
│   │   ├── history_window.py     # Job history & results viewer
│   │   ├── settings_dialog.py    # Application preferences (log level, retention days, etc.)
│   │   └── __init__.py
│   ├── utils/                    # Utility functions
│   │   ├── file_utils.py         # File path handling, validation
│   │   └── __init__.py
│   └── __init__.py
│
├── tests/                        # Comprehensive test suite
│   ├── conftest.py               # Shared pytest fixtures (docx_factory, temp_workspace, test_db)
│   ├── unit/                     # Unit tests (~60% of suite)
│   │   ├── test_search_replace_patterns.py
│   │   ├── test_metadata.py
│   │   ├── test_style_enforcer.py
│   │   ├── test_validator.py
│   │   ├── test_backup.py
│   │   ├── test_config.py
│   │   ├── test_db_manager.py
│   │   ├── test_logger.py
│   │   ├── test_processor_result.py
│   │   ├── test_paragraph_replacement.py
│   │   ├── test_table_header_footer.py
│   │   └── __init__.py
│   ├── integration/              # Integration tests (~25% of suite)
│   │   ├── test_core_infrastructure.py
│   │   └── __init__.py
│   ├── gui/                      # GUI tests (~10% of suite)
│   │   ├── test_main_window.py
│   │   └── __init__.py
│   ├── performance/              # Performance tests (~5% of suite)
│   │   ├── test_processing_speed.py
│   │   └── __init__.py
│   ├── test_documents/           # Test document generation
│   │   ├── create_test_docs.py
│   │   └── create_specialized_test_docs.py
│   └── README.md                 # Comprehensive testing guide
│
├── assets/                       # Application resources
│   └── images/                   # UI images
│
├── .planning/                    # GSD planning & documentation
│   └── codebase/                 # Codebase analysis documents
│       ├── ARCHITECTURE.md
│       └── STRUCTURE.md
│
├── .github/                      # GitHub configuration
│   └── workflows/                # CI/CD pipelines
│
├── .taskmaster/                  # TaskMaster AI integration
│   ├── tasks/
│   │   └── tasks.json
│   ├── docs/
│   ├── reports/
│   └── templates/
│
├── .cursor/                      # Cursor AI configuration
│   └── rules/
│
├── .claude/                      # Claude Code configuration
│   ├── agents/
│   ├── commands/
│   └── hooks/
│
├── config.json                   # Default application configuration
├── requirements.txt              # Production dependencies (PySide6, python-docx, lxml, pyinstaller)
├── requirements-dev.txt          # Development dependencies (pytest, mypy, black, ruff, etc.)
├── pyproject.toml               # Python project metadata
├── docx_bulk_editor.spec        # PyInstaller specification for .exe packaging
├── CLAUDE.md                     # Development guide (threading, Unicode, architecture)
├── PRD.txt                       # Product Requirements Document
├── README.md                     # Project overview
│
├── data/                         # Runtime directory (created on first launch)
│   ├── app.db                    # SQLite database (jobs, results, backups, settings)
│   └── cache/                    # Temporary cache files
│
├── backups/                      # Document backups (created automatically)
│   └── YYYY-MM-DD/               # Daily subdirectories
│       └── {filename}.{timestamp}.backup.docx
│
└── logs/                         # Application logs (created on first launch)
    ├── app.log                   # Current log file
    └── app.log.1-10              # Rotated log files (10 backups, 10MB each)
```

## Directory Purposes

**src/:**
- Purpose: All application source code (production code only, no tests)
- Contains: Python modules organized by function (core services, data, processors, workers, UI)
- Key files: `main.py` (entry point), `core/config.py`, `database/db_manager.py`

**src/core/:**
- Purpose: Infrastructure and cross-cutting concerns
- Contains: Configuration management, logging, backup handling
- Key files: `config.py` (dot-notation JSON config), `logger.py` (rotating file handler)
- Pattern: Service classes (ConfigManager, BackupManager) initialized once at startup

**src/database/:**
- Purpose: Data persistence layer
- Contains: SQLite operations, thread-safe connection management
- Key files: `db_manager.py` (context manager for connections)
- Pattern: All database access through DatabaseManager.get_connection() context manager

**src/processors/:**
- Purpose: Document processing operations (CPU-bound)
- Contains: Module-level `process_document()` functions (multiprocessing entry points) and helpers
- Key files: `search_replace.py`, `metadata.py`, `validator.py`, `style_enforcer.py`, `table_formatter.py`
- Pattern: Each processor has `process_document(file_path, config) → ProcessorResult` at module level

**src/workers/:**
- Purpose: Background threading and job orchestration
- Contains: QThread implementations for non-blocking operations
- Key files: `job_worker.py` (manages multiprocessing pool, emits signals)
- Pattern: QThread emits signals that are connected to UI slots

**src/ui/:**
- Purpose: PySide6 GUI components
- Contains: QMainWindow, QDialog, QGroupBox subclasses
- Key files: `main_window.py` (primary UI), `progress_dialog.py` (real-time updates)
- Pattern: Each window/dialog is a class inheriting from QMainWindow or QDialog

**tests/:**
- Purpose: Automated testing (unit, integration, GUI, performance)
- Contains: pytest tests organized by category
- Key files: `conftest.py` (shared fixtures), category directories (unit/, integration/, gui/)
- Pattern: Test files mirror source structure with test_ prefix

**tests/unit/:**
- Purpose: Isolated unit tests for individual components
- Contains: Tests for processors, database, config, backup, logger
- Pattern: Uses fixtures from conftest.py (docx_factory, test_db, temp_workspace)

**tests/integration/:**
- Purpose: Tests for component interactions
- Contains: Tests for worker-to-pool communication, job flow
- Pattern: Tests multiple components working together

**tests/gui/:**
- Purpose: GUI testing with pytest-qt
- Contains: Tests for MainWindow, ProgressDialog, etc.
- Pattern: Uses qtbot fixture from pytest-qt for widget interaction

**tests/performance/:**
- Purpose: Performance benchmarking
- Contains: Tests for processing speed, memory usage
- Pattern: Uses pytest-benchmark for timing measurements

**tests/test_documents/:**
- Purpose: Test data generation
- Contains: Scripts to create .docx files for testing
- Pattern: Creates pre-made documents in temp_workspace

**data/:**
- Purpose: Runtime data storage (created on first launch)
- Contains: SQLite database, temporary cache files
- Key files: `app.db` (persistent job/result data)
- Not committed to git; created by application

**backups/:**
- Purpose: Document backup storage (created automatically)
- Contains: Daily subdirectories with backup files
- Organization: `backups/YYYY-MM-DD/{filename}.{timestamp}.backup.docx`
- Not committed to git; created by BackupManager

**logs/:**
- Purpose: Application logging (created on first launch)
- Contains: Rotating log files (10MB max, 10 backups)
- Key files: `app.log` (current), `app.log.1-10` (rotated)
- Not committed to git; created by setup_logger()

## Key File Locations

**Entry Points:**
- `src/main.py`: Application entry point (multiprocessing.freeze_support(), directory setup, Qt initialization)

**Configuration:**
- `config.json`: Default application configuration (loaded/saved by ConfigManager)
- `src/core/config.py`: ConfigManager class (dot-notation access, JSON persistence)

**Core Logic:**
- `src/workers/job_worker.py`: Job orchestration, multiprocessing pool management
- `src/processors/search_replace.py`: Search & replace with regex support
- `src/processors/validator.py`: Document validation
- `src/processors/metadata.py`: Metadata management
- `src/processors/style_enforcer.py`: Style standardization
- `src/processors/table_formatter.py`: Table formatting

**Data:**
- `src/database/db_manager.py`: Thread-safe SQLite operations
- `data/app.db`: SQLite database (runtime, created on first launch)

**UI:**
- `src/ui/main_window.py`: Primary application window (operations, file selection, progress)
- `src/ui/progress_dialog.py`: Real-time progress monitoring (modal dialog)
- `src/ui/history_window.py`: Job history and results viewer
- `src/ui/settings_dialog.py`: Application preferences

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures
- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for component interactions
- `tests/gui/`: GUI tests using pytest-qt

## Naming Conventions

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `search_replace.py`, `db_manager.py`)
- Test files: `test_{module_name}.py` (e.g., `test_search_replace.py`)
- Configuration: `config.json` (JSON format, lowercase)
- Log files: `app.log` (rolling: `app.log.1`, `app.log.2`, etc.)
- Backup files: `{original_name}.{YYYYMMDD_HHMMSS}.backup.docx`

**Directories:**
- Source code: lowercase (e.g., `src/`, `processors/`, `ui/`, `workers/`)
- Tests: lowercase with category (e.g., `tests/unit/`, `tests/integration/`)
- Data: lowercase (e.g., `data/`, `backups/`, `logs/`)
- Backup subdirs: `YYYY-MM-DD` format (ISO 8601 date)

**Python Classes:**
- PySide6 windows: `CamelCase` + "Window" or "Dialog" (e.g., `MainWindow`, `ProgressDialog`, `HistoryWindow`)
- Data models: `CamelCase` (e.g., `ProcessorResult`, `DatabaseManager`, `ConfigManager`)
- Service classes: `CamelCase` + "Manager" (e.g., `BackupManager`, `DatabaseManager`, `ConfigManager`)

**Python Functions:**
- Module-level (multiprocessing entry points): `process_document()` in each processor
- Helper functions: `lowercase_with_underscores()` (e.g., `perform_search_replace()`, `_check_empty_paragraphs()`)
- Private methods: `_lowercase_with_underscores()` prefix (e.g., `_init_ui()`, `_load_processor()`)
- Qt signals: `snake_case` (e.g., `progress_updated`, `job_completed`, `error_occurred`)
- Qt slots: `_on_{event}()` pattern (e.g., `_on_start_clicked()`, `_on_operation_selected()`)

**Variables:**
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `DEBUG`, `POOL_SIZE`)
- Instance variables: `lowercase_with_underscores` (e.g., `self.selected_files`, `self.current_operation`)
- Qt widgets: `lowercase_suffix_label` (e.g., `progress_bar`, `current_file_label`, `cancel_button`)

**Type Hints:**
- Union types: `Type1 | Type2` (Python 3.10+ pipe syntax, not Optional)
- Generics: `List[str]`, `Dict[str, Any]`, `Optional[Path]`
- File paths: `Path` (from pathlib, not str)

## Where to Add New Code

**New Feature (e.g., new document processor):**
- Primary code: `src/processors/{new_processor}.py`
  - Must include module-level `process_document(file_path: str, config: Dict[str, Any]) → ProcessorResult`
  - Helper functions below process_document() for testability
  - Example: `src/processors/search_replace.py` structure
- Configuration: Add operation type to MainWindow._create_operation_selector()
- UI: Add configuration panel method (e.g., `_show_{operation}_config()`)
- Tests: `tests/unit/test_{new_processor}.py` with unit tests, `tests/integration/` for job flow

**New UI Component:**
- Implementation: `src/ui/{component_name}.py`
- Pattern: Class inheriting from QMainWindow, QDialog, QGroupBox, or QWidget
- Integration: Import and instantiate in `src/ui/main_window.py`
- Tests: `tests/gui/test_{component_name}.py` using pytest-qt

**New Infrastructure Service (e.g., encryption):**
- Implementation: `src/core/{service_name}.py`
- Pattern: Service class with public methods, initialized once at startup
- Example: BackupManager.__init__() called in MainWindow.__init__()
- Tests: `tests/unit/test_{service_name}.py`

**Utilities:**
- Shared helpers: `src/utils/file_utils.py` or create new utility module
- Pattern: Standalone functions or utility classes with no state
- Tests: `tests/unit/test_utils.py` or dedicated test file

**Database Schema Changes:**
- Location: `src/database/migrate_*.py` for migrations
- Pattern: Create migration script with up/down functions
- Example: `src/database/migrate_add_duration.py` adds duration_seconds field

**Configuration Defaults:**
- Location: `src/core/config.py` → ConfigManager._get_defaults()
- Pattern: Nested dict structure with dot-notation keys
- Added to both: default dict and PRD section 9 documentation

**Tests:**
- Unit tests: `tests/unit/test_{module}.py` (isolated, use mocks)
- Integration tests: `tests/integration/test_{feature}.py` (component interactions)
- GUI tests: `tests/gui/test_{window}.py` (use qtbot)
- Fixtures: Add to `tests/conftest.py` if reusable across multiple tests

## Special Directories

**data/:**
- Purpose: SQLite database and cache
- Generated: Yes (created by DatabaseManager on first access)
- Committed: No (in .gitignore)
- Content: `app.db` (persistent job/result data), `cache/` (temporary files)

**backups/:**
- Purpose: Automatic document backups
- Generated: Yes (created by BackupManager before processing)
- Committed: No (in .gitignore)
- Content: Organized by date (YYYY-MM-DD) with timestamp-based filenames
- Rotation: Automatic cleanup based on retention_days config (default: 7)

**logs/:**
- Purpose: Application logging
- Generated: Yes (created by setup_logger on first call)
- Committed: No (in .gitignore)
- Content: `app.log` (current, 10MB rotating), `app.log.1-10` (backups)
- Rotation: Automatic when log reaches 10MB (RotatingFileHandler with maxBytes=10MB, backupCount=10)

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (created by /gsd:map-codebase command)
- Committed: Yes (source control)
- Content: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

---

*Structure analysis: 2026-01-30*
