# Architecture

**Analysis Date:** 2026-01-30

## Pattern Overview

**Overall:** Three-tier layered architecture with thread-based concurrency model

**Key Characteristics:**
- **Main Thread (UI)**: PySide6 widgets and event loop - never blocked with long operations
- **Worker Thread (QThread)**: Job orchestration, business logic, database I/O
- **Multiprocessing Pool**: CPU-bound document processing operations (bypasses Python GIL)
- **Signal/Slot Communication**: Thread-safe messaging between UI and workers using Qt signals
- **Pickle-Serializable Results**: All worker-to-pool communication uses serializable dataclasses

## Layers

**Presentation (UI Layer):**
- Purpose: User interaction, real-time progress display, configuration management
- Location: `src/ui/`
- Contains: PySide6 widgets (QMainWindow, QDialog), signal definitions, UI state
- Depends on: ConfigManager, DatabaseManager, JobWorker, ProgressDialog
- Used by: QApplication event loop
- Examples: `src/ui/main_window.py` (orchestrates all UI), `src/ui/progress_dialog.py` (progress monitoring)

**Business Logic (Worker Thread Layer):**
- Purpose: Job orchestration, pool management, database operations, signal emission
- Location: `src/workers/`
- Contains: JobWorker QThread that manages multiprocessing pools
- Depends on: Processor modules, DatabaseManager, BackupManager, Logger
- Used by: MainWindow (starts worker, connects signals)
- Key: JobWorker.run() executes in background thread, emits progress signals to UI

**Document Processing (Multiprocessing Pool Layer):**
- Purpose: CPU-bound transformations of .docx files using python-docx
- Location: `src/processors/`
- Contains: Module-level `process_document()` functions (multiprocessing entry points), helper functions
- Depends on: python-docx, ProcessorResult dataclass
- Used by: JobWorker submits jobs via Pool.apply_async()
- Key: All processor functions must be picklable (module-level, no closures)

**Infrastructure (Core Layer):**
- Purpose: Application setup, configuration, logging, backups
- Location: `src/core/`
- Contains: ConfigManager (JSON config), Logger (rotating file handler), BackupManager (file backups)
- Depends on: Standard library, python-docx (for backup validation)
- Used by: Main entry point, all other layers

**Data (Database Layer):**
- Purpose: Job tracking, result storage, settings persistence, backup registry
- Location: `src/database/`
- Contains: DatabaseManager (SQLite thread-safe wrapper)
- Depends on: SQLite3, standard library
- Used by: JobWorker (stores results), UI (queries job history), BackupManager (registers backups)

## Data Flow

**User Initiates Job:**

1. User selects operation (Search & Replace, Metadata, etc.) in MainWindow
2. User configures parameters in dynamic config panel
3. User selects files via file browser or drag-and-drop
4. User clicks "Start Processing" button

**Processing Execution:**

1. MainWindow creates JobWorker thread with:
   - List of file paths
   - Operation type (e.g., 'search_replace')
   - Configuration dict (operation-specific params)
   - References to DatabaseManager and BackupManager

2. MainWindow connects JobWorker signals to UI slots:
   - `progress_updated` → MainWindow.update_progress()
   - `job_completed` → MainWindow.show_results()
   - `error_occurred` → MainWindow.show_error()

3. MainWindow creates ProgressDialog and shows it (modal)

4. MainWindow calls `worker.start()` (spawns background thread)

**Worker Thread Execution:**

1. JobWorker.run() executes in background QThread:
   - Updates job status in database to 'running'
   - Loads processor module dynamically (importlib)
   - Creates backups for all files (BackupManager.create_backup())
   - Creates multiprocessing Pool with (cpu_count - 1) workers

2. JobWorker submits all files to pool at once:
   - `pool.apply_async(processor_module.process_document, args=(file_path, config))`
   - Returns AsyncResult objects stored in list

3. JobWorker collects results in order:
   - Loops through AsyncResult objects
   - Calls `async_result.get(timeout=60)` (blocks until worker completes)
   - Each result is ProcessorResult (success, file_path, changes_made, error_message, duration_seconds)

**Result Handling:**

1. For each result, JobWorker:
   - Stores result in database via `self._store_result(result, backup_path)`
   - Updates counters (success_count, failure_count)
   - Calculates progress percentage: `(processed_count / total_count) * 100`
   - Emits progress_updated signal: `(percentage, current_file, success_count, failure_count)`

2. UI receives progress_updated signal (via Qt event loop):
   - ProgressDialog.update_progress() is called (slot)
   - Updates progress bar, elapsed time, remaining time, success/failure counts
   - Displays current file being processed

3. After all files processed:
   - JobWorker emits job_completed signal with final stats
   - ProgressDialog closes
   - MainWindow displays results window (HistoryWindow)
   - Job status updated to 'completed' or 'cancelled'

**State Management:**

- **Job State**: Stored in database (jobs table) - status transitions: pending → running → completed/cancelled
- **Result State**: Stored in database (job_results table) - per-file outcomes with timestamps
- **UI State**: Held in MainWindow (selected_files, current_operation, config params)
- **Backup State**: Registry in database (backups table) with file paths and timestamps
- **Worker State**: Thread-safe _cancelled flag in JobWorker (GIL-protected boolean)

## Key Abstractions

**ProcessorResult (src/processors/__init__.py):**
- Purpose: Picklable dataclass for multiprocessing communication
- Fields: success (bool), file_path (str), changes_made (int), error_message (str), duration_seconds (float)
- Pattern: Used by all processors as return type; must use only basic types for pickle serialization

**Operation Type:**
- Purpose: Maps operation ID to processor module (e.g., 'search_replace' → src.processors.search_replace)
- Pattern: Dynamic import via importlib.import_module() in JobWorker._load_processor()
- Supported: 'search_replace', 'metadata', 'table_format', 'style_enforce', 'validate'

**Signal/Slot Pattern:**
- Purpose: Thread-safe communication from background thread to UI thread
- Examples:
  - `progress_updated = Signal(int, str, int, int)` emitted from JobWorker.run()
  - Slot: `def update_progress(self, percentage, current_file, success_count, failure_count):`
- Key: Signals automatically marshal calls across thread boundaries

## Entry Points

**Application Start (src/main.py):**
- Location: `main()` function
- Triggers: `python -m src.main` or PyInstaller executable
- Responsibilities:
  1. Call `multiprocessing.freeze_support()` (critical for PyInstaller)
  2. Set up runtime directories (data/, backups/, logs/)
  3. Initialize logger
  4. Load configuration (ConfigManager)
  5. Initialize database (DatabaseManager)
  6. Create QApplication and MainWindow
  7. Enter event loop via `app.exec()`

**Job Processing (src/workers/job_worker.py):**
- Location: JobWorker.run() method
- Triggers: Automatically when MainWindow calls `self.worker.start()`
- Responsibilities: Orchestrate entire document processing pipeline

**Document Processing (src/processors/*.py):**
- Location: `process_document(file_path: str, config: Dict) → ProcessorResult`
- Triggers: Called by multiprocessing pool via `pool.apply_async()`
- Responsibilities: Transform single document and return result

**UI Event Loop (src/ui/main_window.py):**
- Location: MainWindow.__init__() and methods connected to button clicks
- Triggers: QApplication.exec() running
- Responsibilities: Handle user input, create/manage workers, display progress

## Error Handling

**Strategy:** Defensive with fallback recovery

**Patterns:**

**Processor Level** (document processing):
- Wrapped in try-except, returns ProcessorResult with success=False and error_message
- No exception propagates beyond processor function
- Backup file preserved regardless of processing failure

Example from `src/processors/search_replace.py`:
```python
def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    try:
        doc = Document(file_path)
        changes = perform_search_replace(doc, config)
        if changes > 0:
            doc.save(file_path)
        return ProcessorResult(success=True, ...)
    except Exception as e:
        return ProcessorResult(success=False, error_message=str(e), ...)
```

**Worker Thread Level** (JobWorker):
- try-except around entire job execution
- Graceful handling of multiprocessing.TimeoutError
- Per-file error handling in result collection loop
- Emits error_occurred signal for unrecoverable errors

**UI Level** (MainWindow):
- try-except in event handlers
- Dialog boxes for user-facing errors
- Error messages logged and displayed to user

**Database Level** (DatabaseManager):
- Context manager with automatic rollback on exception
- check_same_thread=False for thread-safe access
- Foreign key constraints enforced

## Cross-Cutting Concerns

**Logging:**
- Configured in `src/core/logger.py` with setup_logger()
- Rotating file handler (10MB max, 10 backups) at `logs/app.log`
- Console handler (INFO level), file handler (DEBUG level)
- All UTF-8 encoding for Windows compatibility
- Pattern: `logger = setup_logger()` at module level, then `logger.info/debug/warning/error()`

**Validation:**
- Configuration validation in ConfigManager (loads defaults if missing)
- File path validation in BackupManager and JobWorker
- Document validity checked during backup creation via python-docx
- Input validation in UI (file selection, parameter ranges)

**Authentication:**
- Not applicable - single-user desktop application
- File-based configuration (config.json)
- SQLite database with no authentication

**UTF-8 Encoding (Windows Critical):**
- ConfigManager: `open(path, 'r', encoding='utf-8')`
- DatabaseManager: SQLite connections with UTF-8 pragma
- Logger: RotatingFileHandler with encoding='utf-8'
- Backup validation: python-docx handles internally
- Pattern: Every file operation explicitly specifies `encoding='utf-8'`

---

*Architecture analysis: 2026-01-30*
