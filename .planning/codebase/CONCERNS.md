# Codebase Concerns

**Analysis Date:** 2026-01-30

## Tech Debt

**Silent Exception Handling in Metadata Processor:**
- Issue: `src/processors/metadata.py` lines 93-95 and 103-105 use bare `except: pass` blocks that silently ignore errors when setting metadata properties. Properties that fail silently are never logged or reported to the user.
- Files: `src/processors/metadata.py`
- Impact: Failed metadata modifications appear to succeed, user gets wrong result without knowing which fields were actually changed. No audit trail of failures.
- Fix approach: Replace `except: pass` with specific exception logging `except Exception as e: logger.warning(f"Failed to set {field}: {e}")`. Count and report failed modifications in result.

**Bare Exception Handling in Style Enforcer:**
- Issue: `src/processors/style_enforcer.py` line 206-208 catches `KeyError` with bare `pass`, silently skipping missing styles without logging.
- Files: `src/processors/style_enforcer.py`
- Impact: When a document references a style that doesn't exist, the enforcer silently skips it. User has no visibility into which styles were not applied.
- Fix approach: Log specific warning about missing style and include in result metadata.

**Placeholder Detection Not Fully Implemented:**
- Issue: Validator mentions placeholder detection (`src/ui/main_window.py` line 541) with `[TODO]` in comments, and processor has placeholder patterns defined (`src/processors/validator.py` line 190) but UI checkbox labeled "Find placeholder text ({{var}}, [TODO], etc.)" - unclear if feature is complete.
- Files: `src/ui/main_window.py`, `src/processors/validator.py`
- Impact: Feature may be partial implementation leading to confusion about what placeholder detection actually does.
- Fix approach: Complete placeholder detection implementation and document expected behavior, or remove incomplete UI controls.

**Hard-Coded Timeout Without Configuration Flexibility:**
- Issue: Processing timeout is configurable (`config.json` line 11, `src/workers/job_worker.py` line 164) but defaults to 60 seconds per file globally. Complex documents or slow operations exceed this without per-operation tuning.
- Files: `config.json`, `src/workers/job_worker.py`
- Impact: Long-running operations (large document processing, complex regex) timeout and fail, even if they eventually would succeed. Users must manually adjust global config.
- Fix approach: Add per-operation timeout configuration option with sensible defaults (regex searches may need 120s+, metadata changes only need 10s).

**Backup Creation Failures Don't Block Processing:**
- Issue: `src/workers/job_worker.py` lines 148-158 log backup creation failures as warnings but continue processing without modifying files. Backup failures are tracked but not exposed in UI or final results.
- Files: `src/workers/job_worker.py`
- Impact: User may lose original files on error because backups weren't created, but they're unaware - they see "processing completed" without knowing some files aren't recoverable.
- Fix approach: Consider stricter backup validation: either fail the job if ANY backup fails, OR clearly mark files without backups in results UI.

## Known Bugs

**Possible Race Condition in SQLite with Multiprocessing Pool:**
- Symptoms: Occasional "database is locked" errors under heavy load with many worker processes
- Files: `src/database/db_manager.py`, `src/workers/job_worker.py`
- Trigger: Run large batch (100+ files) on multi-core machine with quick operations (search/replace)
- Cause: Multiple worker processes may attempt to write results to SQLite simultaneously. While `check_same_thread=False` allows cross-thread access, concurrent writes from multiple processes can exceed SQLite's lock handling.
- Workaround: Reduce pool size, increase `timeout=30.0` in `db_manager.py` line 87, or implement result queue with single writer thread.

**Window Geometry Not Fully Restored:**
- Symptoms: Main window sometimes appears at wrong position/size on startup
- Files: `src/ui/main_window.py` (lines 88 and geometry restoration logic not fully visible in sample)
- Trigger: Launch application, close at non-standard window size, relaunch
- Cause: Geometry restoration likely doesn't account for multi-monitor setups or DPI changes.
- Workaround: Resize window manually.

**Backup Restore Doesn't Update Database Status:**
- Symptoms: After restoring a backup via UI, the `restored` flag in backups table may not be updated consistently
- Files: `src/core/backup.py` (restore logic)
- Trigger: Restore backup, then check database state
- Cause: Restore path updates database but state tracking is incomplete.
- Workaround: Restore works, but audit trail shows incomplete.

## Security Considerations

**No Input Validation on File Paths:**
- Risk: Malicious or unusual file paths (UNC paths, paths with special characters) could cause unexpected behavior or errors. While python-docx handles many edge cases, the application doesn't pre-validate paths.
- Files: `src/workers/job_worker.py`, `src/core/backup.py`
- Current mitigation: File selection uses Qt file dialogs which pre-filter to .docx files
- Recommendations:
  - Add path validation before backup creation (check for UNC, symlinks, special chars)
  - Reject paths containing null bytes or control characters
  - Validate file is actually a DOCX (check magic bytes) not just extension

**Regex Injection Possible in Search/Replace:**
- Risk: If user provides untrusted regex patterns (e.g., from imported config), malformed regex could cause DoS via excessive backtracking
- Files: `src/processors/search_replace.py`
- Current mitigation: User-provided patterns, typical users don't input malicious regex
- Recommendations:
  - Add regex complexity limits (max alternation depth, backref counts)
  - Catch `re.error` exceptions and show user-friendly error message
  - Consider using `regex` library with timeout support instead of `re` module

**Database Queries Use Parametrized Statements (Good):**
- Status: SQLite injection properly prevented via `cursor.execute(query, params)` pattern throughout
- Files: All db_manager, workers, UI components
- No action needed

**Config File Allows Arbitrary Settings:**
- Risk: `config.json` loaded without schema validation; could inject invalid values causing runtime errors
- Files: `src/core/config.py`
- Current mitigation: Defaults provided in code for missing keys
- Recommendations:
  - Add config schema validation on load (pydantic or jsonschema)
  - Validate backup directory is within reasonable paths (not system32 or other protected dirs)
  - Validate timeout/pool_size are reasonable integers (not negative)

## Performance Bottlenecks

**Main Window is 1139 Lines - Complex Component:**
- Problem: `src/ui/main_window.py` is very large and handles too many responsibilities (file selection, config management, job orchestration, operation selection)
- Files: `src/ui/main_window.py` (1139 lines)
- Cause: Single monolithic UI class doing layout + business logic + state management
- Improvement path:
  - Extract operation-specific panels into separate `OperationPanel` base class with subclasses
  - Move file selection logic to separate `FileSelector` component
  - Extract job orchestration to separate `JobOrchestrator` class
  - Reduce main window to ~500-600 lines for clarity and maintainability

**Database Connection Overhead in Result Storage Loop:**
- Problem: Each result stored individually (`src/workers/job_worker.py` line 216 calls `_store_result()`) which creates new DB connection per file processed
- Files: `src/workers/job_worker.py`
- Cause: Results stored one-by-one in result collection loop rather than batched
- Improvement path:
  - Collect all results in memory during processing
  - Batch insert results at end (one or few DB transactions for all results)
  - Reduces DB overhead from N connections to 1-2 connections

**Progress Signal Emission Frequency Configurable But May Still Be High:**
- Problem: Progress updates emitted for every file processed (could be 1000+ signals for large batches). Signal handler `update_progress()` updates UI labels/progress bar on every call.
- Files: `src/workers/job_worker.py` line 222, `config.json` line 22
- Cause: Qt signals between threads have overhead; high frequency can bottleneck even with `progress_update_interval_ms: 100`
- Improvement path:
  - Filter progress updates to only emit every N files or every M milliseconds
  - Implement rate limiting in signal emission

## Fragile Areas

**Multiprocessing Pool Cleanup on Error:**
- Files: `src/workers/job_worker.py`
- Why fragile: If exception raised before pool cleanup (line 170), pool may not terminate cleanly. Context manager helps but early return/exception paths may leak processes.
- Safe modification: Test all exception paths thoroughly. Ensure every code path reaches `with` statement properly or add try/finally around pool creation.
- Test coverage: Integration tests should verify pool cleanup under cancellation and error conditions.

**Backup Validation Using Document Load:**
- Files: `src/core/backup.py` lines 140-150
- Why fragile: `Document(backup_path)` loads entire document into memory just to validate. For large documents (100MB+), this is slow and memory-intensive. If validation fails, file is deleted.
- Safe modification:
  - Use cheaper validation (check file size, ZIP signature) before expensive Document load
  - Don't delete backup on failed validation - move to quarantine folder for inspection
  - Add timeout to validation operation
- Test coverage: Test with corrupted documents, truncated files, and very large documents.

**JSON Serialization of Operation Config to Database:**
- Files: `src/ui/main_window.py` line 851 stores `str(operation_config)` not JSON
- Why fragile: Using `str(dict)` produces Python repr format, not valid JSON. This can be parsed back but is brittle if format changes.
- Safe modification: Use `json.dumps(operation_config)` and `json.loads()` for round-tripping. Validate schema.
- Test coverage: Load historical configs, verify round-trip integrity.

**Style Name Lookup Without Validation:**
- Files: `src/processors/style_enforcer.py` line 203-208
- Why fragile: Code assumes `doc.styles[target_style]` exists without checking. KeyError caught silently. If style name changes in Word, all matching breaks silently.
- Safe modification: Use `try/except` with logging. Verify style exists before attempting assignment. Report unmatchable styles to user.
- Test coverage: Test with documents missing expected styles.

## Scaling Limits

**Multiprocessing Pool Fixed at CPU Count - 1:**
- Current capacity: On 4-core machine, 3 worker processes; on 16-core, 15 workers
- Limit: Pool size not adjustable per job. If user has other applications, pool takes all available cores.
- Scaling path:
  - Make pool size configurable in Settings UI (slider 1-N cores)
  - Show recommended pool size based on file count (don't create 15 processes for 3 files)
  - Add dynamic pool resizing based on system load

**Backup Storage Accumulation:**
- Current capacity: 7 days retention default (~140 daily subdirectories over a year). No size limit.
- Limit: If processing 100+ large documents daily with backups, storage can grow to GB+
- Scaling path:
  - Implement size-based cleanup (delete oldest backups when total exceeds threshold)
  - Add UI display of backup storage usage
  - Option to compress old backups

**Database Growth Without Maintenance:**
- Current capacity: No VACUUM, index optimization, or table rotation implemented
- Limit: Over time with many jobs, `job_results` table grows large (1 row per file per job). No automatic cleanup.
- Scaling path:
  - Implement job result archival (move old results to separate table or file)
  - Add database VACUUM on startup if database grew beyond threshold
  - Implement result cleanup policy (delete results older than N days)

## Dependencies at Risk

**python-docx Dependency on Old lxml:**
- Risk: `python-docx>=1.1.0` may have transitive dependency on older lxml versions; lxml sometimes has security issues in older versions
- Impact: Security vulnerability in XML parsing could affect document processing
- Migration plan:
  - Update `requirements.txt` to specify `lxml>=5.1.0` explicitly (already in CLAUDE.md but not enforced in requirements.txt)
  - Add security scanning in CI/CD (tools like Snyk or GitHub security alerts)
  - Subscribe to python-docx release notifications

**PyInstaller PyQt6 vs PySide6 Compatibility:**
- Risk: `docx_bulk_editor.spec` built for PySide6, but PyInstaller updates may introduce compatibility issues
- Impact: Frozen executable may break with new PyInstaller versions
- Migration plan:
  - Pin PyInstaller version in requirements.txt
  - Test frozen executable in CI/CD against target Python versions
  - Maintain alternative build using PyQt6 if needed

## Missing Critical Features

**No Error Recovery UI:**
- Problem: When processing fails partway through (e.g., 50 files succeed, 10 fail), user has no easy way to retry just the failed files
- Blocks: Can't resume partial jobs; must restart entire batch
- Recommendations:
  - Add "Retry Failed" button in results window
  - Store which files failed and allow re-queueing them
  - Optionally apply different config to retry (e.g., simpler operation)

**No Processing Logs in UI:**
- Problem: `logs/app.log` contains detailed processing info but user can't view it from UI
- Blocks: Can't diagnose issues without opening log files manually
- Recommendations:
  - Add "View Logs" button in history/results window
  - Show last N lines of current job log in progress dialog
  - Export logs with job results

**No Dry-Run / Preview Mode:**
- Problem: User must process documents to see what changes would be made; no way to preview
- Blocks: High-risk operations (large search/replace) can't be tested safely first
- Recommendations:
  - Add "Preview" mode that processes one file and shows changes without saving
  - Show before/after diff for preview document
  - Add "Undo Last Job" to restore from backups easily

## Test Coverage Gaps

**Silent Failure Paths Not Tested:**
- What's not tested: Exception paths where errors are silently ignored (metadata processor, style enforcer)
- Files: `src/processors/metadata.py`, `src/processors/style_enforcer.py`
- Risk: Bugs in error handling go undetected. User sees success but modifications didn't actually happen.
- Priority: **HIGH** - These are data integrity issues
- Approach: Add specific tests that verify which exceptions are handled and how they're reported

**Multiprocessing Pool Failure Scenarios:**
- What's not tested: Pool failures (worker process crash, pool.terminate() called), timeout behavior with large documents
- Files: `src/workers/job_worker.py`
- Risk: Unhandled process crashes could leave inconsistent state or orphaned processes
- Priority: **HIGH** - Threading/multiprocessing bugs are hard to reproduce
- Approach: Add integration tests that simulate worker process failures, timeouts, and cancellations

**Backup/Restore Round-Trip:**
- What's not tested: Full cycle - create backup, modify file, restore backup, verify contents are identical
- Files: `src/core/backup.py`
- Risk: Data loss if backup/restore mechanism is broken
- Priority: **HIGH** - Critical feature for data safety
- Approach: Add comprehensive backup integration tests with various document types

**Database Concurrency:**
- What's not tested: Multiple jobs writing results simultaneously (multiprocessing scenario)
- Files: `src/database/db_manager.py`, `src/workers/job_worker.py`
- Risk: Race conditions, data corruption, or deadlocks under load
- Priority: **HIGH** - Data integrity issue
- Approach: Add concurrent job tests that spawn multiple JobWorker threads

**UI State Management During Job:**
- What's not tested: UI behavior when job completes, is cancelled, or fails - state of buttons, dialogs, etc.
- Files: `src/ui/main_window.py`, `src/ui/progress_dialog.py`
- Risk: UI left in invalid state (buttons disabled when shouldn't be, dialogs not closed, etc.)
- Priority: **MEDIUM** - UX issue
- Approach: Add pytest-qt GUI tests for job lifecycle

**Large File Handling:**
- What's not tested: Processing of documents near/over max_file_size_mb limit (100MB default)
- Files: Config and all processors
- Risk: Unexpected behavior, memory issues, or timeouts with large documents
- Priority: **MEDIUM** - Performance/stability issue
- Approach: Add performance tests with synthetic large documents

---

*Concerns audit: 2026-01-30*
