# CLAUDE.md

## Project Overview

**DOCX Bulk Editor** — Windows desktop app for batch processing Word (.docx) documents.
Built with Python 3.11+, PySide6 (Qt 6), python-docx, and SQLite.

Features: search/replace, metadata management, formatting enforcement, table formatting, document validation across hundreds of files simultaneously.

**Status**: Core infrastructure, all processors, UI, database, and test suite implemented. Managed via GSD workflow (`.planning/`).

## Critical Rules

### Unicode Handling (ESSENTIAL)

**ALWAYS** use `encoding='utf-8'` when opening files on Windows:

```python
# CORRECT
with open('file.json', 'r', encoding='utf-8') as f: ...

# WRONG — defaults to cp1252 on Windows
with open('file.json', 'r') as f: ...
```

This applies to ALL file I/O: reading, writing, JSON, logs, config files.

### Path Handling

- Use `pathlib.Path` for all path operations
- Support UNC paths: `\\server\share\file.docx`

### Multiprocessing + PyInstaller

`multiprocessing.freeze_support()` is **required** in `if __name__ == "__main__":` guard. All processor functions must be module-level (not nested) for pickle compatibility.

## Architecture

### Threading Model

```
Main Thread (UI only) ──signals/slots──> Worker Thread (QThread)
                                           │
                                           │ multiprocessing IPC
                                           ↓
                                         Process Pool (CPU_COUNT-1)
```

**Rules**:
1. **Main Thread**: UI updates only — never block with long operations (>100ms)
2. **Worker Thread**: Business logic, database I/O, pool management
3. **Process Pool**: Document processing (bypasses GIL)
4. **Communication**: Main<->Worker via Qt signals/slots, Worker<->Pool via multiprocessing

### Key Patterns

**Processors** return picklable `ProcessorResult` dataclass. See any file in `src/processors/` for the pattern.

**Workers** extend `QThread`, emit signals (`progress_updated`, `job_completed`, `error_occurred`). See `src/workers/job_worker.py`.

**UI** connects worker signals to slots, disables controls during processing. See `src/ui/main_window.py`.

### Backup Strategy

Before ANY document modification:
1. Copy original to `backups/YYYY-MM-DD/{filename}.{timestamp}.backup.docx`
2. Store metadata in SQLite `backups` table
3. Verify backup is readable before proceeding
4. Auto-cleanup after N days (default: 7)

### Database

SQLite (`data/app.db`) with `check_same_thread=False`. Tables: `jobs`, `job_results`, `backups`, `settings`, `audit_log`. See `src/database/db_manager.py` and PRD.txt section 9 for full schema.

## Development

### Setup

```bash
.\venv\Scripts\activate
pip install -r requirements.txt          # Production deps
pip install -r requirements-dev.txt      # Dev/test deps
```

### Run

```bash
python src/main.py
```

### Testing

Config in `pytest.ini`. Fixtures in `tests/conftest.py`. Coverage threshold: 80%.

```bash
pytest                                    # All tests with coverage
pytest -m "unit and not slow"             # Fast dev feedback
pytest -m gui                             # GUI tests (pytest-qt)
pytest -m integration                     # Integration tests
pytest -m performance                     # Benchmarks
pytest -n auto                            # Parallel execution
pytest -x                                 # Stop on first failure
pytest --cov=src --cov-fail-under=80      # Enforce coverage
```

Markers: `unit`, `integration`, `gui`, `performance`, `windows`, `slow`, `smoke`.

Key fixtures: `docx_factory`, `sample_docx`, `complex_docx`, `large_docx`, `multiple_docx`, `temp_workspace`, `test_db`, `mock_config`, `unicode_filename`.

### Code Quality

```bash
ruff check src/
black src/
mypy src/ --ignore-missing-imports
```

### Build Executable

```bash
pyinstaller docx_bulk_editor.spec --clean
# Output: dist/docx_bulk_editor.exe
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Startup | < 3s |
| Processing | 10-50 docs/min |
| Memory | < 500MB for 500 docs |
| UI responsiveness | 60 FPS (main thread never blocked) |
| .exe size | < 200MB |

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| UI freezes | Use QThread workers for operations >100ms |
| `encoding='utf-8'` forgotten | Always explicit on Windows |
| Multiprocessing in .exe fails | `freeze_support()` in `__main__` guard |
| SQLite "database locked" | `check_same_thread=False` + proper transactions |
| Can't pickle processor | Define functions at module level, not nested |
| Qt platform plugin error | `pip install --force-reinstall PySide6` |

## Specialized Agents

1. **python-frontend-specialist**: PySide6 UI, QThread, Windows UI
2. **python-backend-specialist**: python-docx, multiprocessing, SQLite, performance
3. **python-qa-engineer**: pytest, GUI testing, performance testing, bug identification

## Reference

- **PRD**: `PRD.txt` — full requirements, architecture, database schema
- **Testing guide**: `tests/README.md`, `TESTING_QUICK_START.md`
- **GSD state**: `.planning/` — project roadmap, phases, state tracking
- **PySide6**: https://doc.qt.io/qtforpython/
- **python-docx**: https://python-docx.readthedocs.io/
- **PyInstaller**: https://pyinstaller.org/en/stable/
