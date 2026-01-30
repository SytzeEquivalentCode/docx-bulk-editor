# Technology Stack

**Analysis Date:** 2026-01-30

## Languages

**Primary:**
- Python 3.11+ (tested on 3.13.7) - All application code, document processing, UI, database layer

**Secondary:**
- None - Pure Python codebase

## Runtime

**Environment:**
- Python 3.11, 3.12, 3.13 (supported versions)
- Operating System: Windows 10+ (primary), macOS/Linux (future support planned)

**Package Manager:**
- pip (PyPI)
- Lockfile: `requirements-lock.txt` present

**Execution Model:**
- Multiprocessing for CPU-bound document processing
- QThread workers for UI thread management
- PyInstaller for Windows .exe distribution (single-file, portable)

## Frameworks

**Core:**
- PySide6 6.10.1 - Qt 6 for Python desktop GUI framework
  - File: `src/ui/main_window.py`, `src/ui/progress_dialog.py`, `src/ui/settings_dialog.py`, `src/ui/history_window.py`
  - Threading: QThread workers (`src/workers/job_worker.py`)
  - Signals/slots for thread-safe UI updates

**Document Processing:**
- python-docx 1.2.0 - Microsoft Word .docx file manipulation
  - File: `src/processors/search_replace.py`, `src/processors/metadata.py`, `src/processors/style_enforcer.py`, `src/processors/table_formatter.py`, `src/processors/validator.py`
  - Reads/writes .docx files via ZIP + XML parsing

**Data Management:**
- sqlite3 (builtin) - Local database for job history, results, backups
  - File: `src/database/db_manager.py`
  - Database location: `data/app.db`

**Testing:**
- pytest 9.0.1 - Test framework
  - Config: `pyproject.toml` [tool.pytest.ini_options]
  - pytest-qt 4.5.0 - PySide6/Qt testing utilities
  - pytest-cov 7.0.0 - Code coverage reporting
  - pytest-mock 3.12.0 - Mocking utilities
  - pytest-xdist 3.5.0 - Parallel test execution

**Build/Dev:**
- PyInstaller 6.17.0 - Windows .exe packaging for distribution
  - Config: `docx_bulk_editor.spec` (when created)
- Black 25.11.0 - Code formatting (line-length: 120)
- Pylint 4.0.3 - Static code analysis
- Mypy 1.8.0 - Type checking
- Ruff 0.2.2 - Fast linting
- Coverage 7.12.0 - Coverage measurement

## Key Dependencies

**Critical (Production):**
- PySide6 6.10.1 - Must have for GUI; provides Qt6 bindings
  - Includes: PySide6_Essentials 6.10.1, PySide6_Addons 6.10.1, shiboken6 6.10.1
- python-docx 1.2.0 - Document manipulation; no replacement in Python ecosystem
- lxml 6.0.2 - XML processing (required by python-docx for correct XML handling)

**Infrastructure:**
- sqlite3 - Builtin Python module; no external dependency required

**Build Distribution:**
- PyInstaller 6.17.0 - Converts Python scripts to Windows executable
- pyinstaller-hooks-contrib 2025.10 - Hooks for third-party libraries

**Development Only:**
- faker 24.0.0 - Generates fake test data
- freezegun 1.4.0 - Mocks datetime for testing
- hypothesis 6.98.0 - Property-based test generation
- Sphinx 7.2.6 - Documentation generation (optional)

## Configuration

**Environment:**
- No environment variables required for core operation
- Optional: .env.example shows possible API keys (not used by core app)
  - File: `.env.example` (legacy - contains API keys for external services not integrated)

**Build:**
- `pyproject.toml` - Python project metadata
  - Python version requirement: >=3.11
  - Black config: line-length=120, target-version=['py311']
  - Pytest config: testpaths=["tests"]
- `config.json` - Application runtime configuration (user settings)
  - File: `config.json`
  - Settings: backup retention, processing pool size, UI theme, logging level
  - Auto-generated with defaults on first run

## Platform Requirements

**Development:**
- Python 3.11+
- Virtual environment (venv)
- pip (Python package installer)
- Windows 10+ (for testing PySide6)

**Production/Distribution:**
- Windows 10+ (via PyInstaller .exe)
- No external dependencies required (everything bundled in .exe)
- No Python installation required for end users
- Estimated .exe size: 150-200MB (PyInstaller bundle with all dependencies)

**Runtime Directories (Created at First Launch):**
- `data/app.db` - SQLite database
- `data/cache/` - Temporary cache
- `backups/` - Document backups (organized by date YYYY-MM-DD)
- `logs/` - Application logs (rotating handler, 10MB max per file, 10 backups)

## Dependencies Summary

**Total Production Dependencies:** 4
1. PySide6 >= 6.8.0
2. python-docx >= 1.1.0
3. lxml >= 5.1.0
4. pyinstaller >= 6.3.0

**Total Development Dependencies:** 19 (listed in `requirements-dev.txt`)

All dependencies pinned in `requirements-lock.txt` for reproducible builds.

## Multiprocessing Architecture

**Process Model:**
```
Main Thread (UI)
    ↓ Qt Signals
Worker Thread (QThread)
    ↓ Multiprocessing IPC
Process Pool (N = CPU_count - 1)
    - Isolated document processing
    - Parallel execution for CPU-bound operations
```

**Critical Detail:**
- PyInstaller requires `multiprocessing.freeze_support()` in `if __name__ == "__main__":` guard
- File: `src/main.py` line 67
- Failure to include causes multiprocessing to fail in frozen executables

---

*Stack analysis: 2026-01-30*
