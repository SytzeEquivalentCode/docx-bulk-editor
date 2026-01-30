# External Integrations

**Analysis Date:** 2026-01-30

## APIs & External Services

**Status: No External APIs**

This is an offline-first, standalone desktop application with zero network integrations. No API calls, webhooks, or external service dependencies are present in the codebase.

**Note on .env.example:**
- File: `.env.example` contains API key placeholders (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
- These are **NOT USED** by the DOCX Bulk Editor application
- Likely artifact from shared development environment or template project
- The actual application code contains no references to these APIs
- Verified: No `requests`, `urllib`, `boto3`, or external API client imports in `src/`

## Data Storage

**Databases:**
- SQLite (builtin Python module)
  - Connection: `sqlite3.connect()` with `check_same_thread=False` for thread-safety
  - Client: Python standard library `sqlite3` module
  - File location: `data/app.db`
  - Schema initialization: `src/database/db_manager.py` class `DatabaseManager`
  - Tables: jobs, job_results, backups, settings, audit_log (see PRD section 9)

**File Storage:**
- Local filesystem only
  - Document storage: User-selected directories (file browser selection)
  - Backup storage: `backups/` directory with date-based organization (`YYYY-MM-DD/`)
  - Configuration: `config.json` in application root
  - Logs: `logs/` directory with rotating file handler (10MB max, 10 backups)
  - Cache: `data/cache/` for temporary processing artifacts

**No Cloud Storage:**
- Not detected; offline-only operation
- No S3, Azure Blob, Google Drive, Dropbox, or similar integrations

**Caching:**
- In-memory caching: None currently implemented
- File-based cache: `data/cache/` directory (location exists but functionality not visible in code)

## Authentication & Identity

**Auth Provider:**
- Custom/None - No authentication implemented
- Single-user desktop application - No user identity required
- No login, OAuth, Azure AD, or credential management

## Monitoring & Observability

**Error Tracking:**
- None - No error tracking service (Sentry, Rollbar, etc.) detected
- Local logging only

**Logs:**
- File-based logging via Python `logging` module
  - Configuration: `src/core/logger.py` function `setup_logger()`
  - Handler: `RotatingFileHandler` with UTF-8 encoding
  - Location: `logs/app.log` (rotating: max 10MB per file, keeps 10 backups)
  - Default level: INFO (configurable via `config.json` logging.level)
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Console output: Also logs to console at INFO level

## CI/CD & Deployment

**Hosting:**
- Desktop application (no hosting required)
- Distribution: Windows .exe via PyInstaller
  - Entry point: `src/main.py` with `multiprocessing.freeze_support()`
  - Spec file: `docx_bulk_editor.spec` (for building)
  - Target: Single-file portable executable (~150-200MB)

**CI Pipeline:**
- Not detected in current codebase
- GitHub Actions workflow would typically go in `.github/workflows/` (not present)
- Manual build process: `pyinstaller docx_bulk_editor.spec --clean`

**Version Control:**
- Git repository present (`.git/` directory exists)
- Recent commits include testing improvements and feature additions
- No automatic deployment configured

## Environment Configuration

**Required env vars:**
- None required for core operation
- Application is fully self-contained

**Optional env vars (unused):**
- `.env.example` contains placeholders (not referenced by code):
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - PERPLEXITY_API_KEY
  - GOOGLE_API_KEY
  - MISTRAL_API_KEY
  - XAI_API_KEY
  - GROQ_API_KEY
  - OPENROUTER_API_KEY
  - AZURE_OPENAI_API_KEY
  - OLLAMA_API_KEY
  - GITHUB_API_KEY

**Secrets location:**
- No secrets management system required
- No API keys needed for operation
- Backup paths and settings stored in local `config.json` (not secrets)

## Webhooks & Callbacks

**Incoming Webhooks:**
- None - Standalone desktop app, no network listening

**Outgoing Webhooks:**
- None - No external service notifications

**IPC (Inter-Process Communication):**
- Multiprocessing Pool: Worker processes communicate via pickle serialization
  - File: `src/workers/job_worker.py` uses `multiprocessing.Pool.apply_async()`
  - Results serialized via pickle for transport from child processes
  - No network transport - all within same machine

**Qt Signals (Thread Communication):**
- Signals for main UI thread ↔ worker thread communication
  - `progress_updated(int, str, int, int)` - Progress updates
  - `job_completed(dict)` - Job completion with results
  - `error_occurred(str)` - Error notifications
  - Thread-safe mechanism built into PySide6

## Windows-Specific Considerations

**UNC Path Support:**
- Network shares supported (file browser accepts `\\server\share\path`)
- Handled by pathlib.Path cross-platform support

**Encoding:**
- All file operations use explicit `encoding='utf-8'`
  - JSON config: `src/core/config.py` lines 32, 46
  - Logging: `src/core/logger.py` - UTF-8 file handler
  - Database: `src/database/db_manager.py` - SQLite UTF-8 support
  - Backup: `src/core/backup.py` - Implicit UTF-8 via python-docx

## Zero External Dependencies

**Design Philosophy:**
- No internet connectivity required
- No cloud services
- No API integrations
- No third-party authentication
- No external data sources
- All processing is local, isolated, and offline

**Advantages:**
- Works on air-gapped/offline machines
- No network latency
- No rate limiting
- No service outages
- No authentication tokens
- Complete data privacy (no cloud transmission)

---

*Integration audit: 2026-01-30*
