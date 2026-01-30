# Phase 3: Core Infrastructure Tests - Research

**Researched:** 2026-01-30
**Domain:** pytest testing for Python infrastructure (config, backup, logging, database)
**Confidence:** HIGH

## Summary

Phase 3 focuses on testing foundational infrastructure components that were already implemented and have existing test files. The research reveals that:

1. **All four components already have comprehensive test files** - test_config.py (262 lines), test_backup.py (746 lines), test_logger.py (302 lines), and test_db_manager.py (496 lines) exist with good coverage patterns
2. **Testing patterns are already established** - Tests use temp directories, in-memory databases, programmatic fixtures, and class-based organization with pytest markers
3. **The standard stack is already in use** - pytest 8.0.0, pytest-cov 4.1.0, pathlib for paths, sqlite3 for database, logging.handlers.RotatingFileHandler for logs

The main task is to **verify completeness, fill gaps, and ensure all success criteria are met**. This is not greenfield testing—it's auditing and enhancing existing tests.

**Primary recommendation:** Run existing tests, verify they meet success criteria from CONTEXT.md, identify any gaps in error condition coverage, and add missing test cases rather than rewriting from scratch.

## Standard Stack

The project already uses these libraries (from existing test files and requirements-dev.txt):

### Core Testing
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.0.0 | Test framework | Industry standard for Python testing, fixture system |
| pytest-cov | 4.1.0 | Coverage reporting | Integrated with pytest, HTML/XML reports |
| pytest-mock | 3.12.0 | Mocking utilities | pytest-native mocking interface |

### Core Infrastructure Dependencies
| Library | Version | Purpose | Already Used In |
|---------|---------|---------|----------------|
| pathlib | stdlib | Cross-platform paths | All existing tests, ConfigManager |
| sqlite3 | stdlib | Database testing | DatabaseManager, in-memory DBs |
| logging.handlers | stdlib | Log rotation testing | Logger setup_logger() |
| json | stdlib | Config parsing | ConfigManager load/save |
| shutil | stdlib | File operations | BackupManager copy2/restore |
| python-docx | 1.1.0+ | Document validation | BackupManager._validate_backup() |

### Test Isolation Tools
| Library | Purpose | Pattern Used |
|---------|---------|--------------|
| tmp_path | pytest built-in fixture | Provides isolated temp directory per test |
| :memory: | SQLite in-memory mode | Fresh database per test, no file I/O |
| monkeypatch | pytest built-in | Mock filesystem errors (not used yet) |
| threading | stdlib | Test thread-safety (used in test_db_manager.py) |

**Installation:**
```bash
pip install -r requirements-dev.txt  # All dependencies already specified
```

## Architecture Patterns

### Established Test Patterns (From Existing Tests)

#### Pattern 1: Class-Based Organization with Markers
**What:** Tests organized into classes by feature area, marked with @pytest.mark.unit
**When to use:** All infrastructure tests
**Example:**
```python
# From test_config.py
class TestConfigManager:
    """Test suite for ConfigManager class."""

    @pytest.mark.unit
    def test_load_save_utf8(self, tmp_path):
        """Test load/save with UTF-8 characters."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)
        config.set("test.emoji", "Hello 😀 World 🎉")
        # Reload and verify...
```

#### Pattern 2: Temp Directory Isolation
**What:** Each test gets fresh tmp_path fixture, auto-cleanup after test
**When to use:** All tests that need file I/O
**Example:**
```python
# From test_backup.py
def test_create_backup_success(self, sample_docx, backup_dir, db_manager):
    """Test successful backup creation."""
    manager = BackupManager(backup_dir, db_manager)
    backup_path = manager.create_backup(sample_docx)
    assert backup_path is not None
    assert backup_path.exists()
```

#### Pattern 3: In-Memory Database Per Test
**What:** DatabaseManager(":memory:") for each test, no shared state
**When to use:** All database-dependent tests (BackupManager, job tracking)
**Example:**
```python
# From test_backup.py
@pytest.fixture
def db_manager(tmp_path):
    """Provide DatabaseManager for testing."""
    db_path = tmp_path / "test.db"
    return DatabaseManager(db_path)
```

#### Pattern 4: Programmatic Document Creation
**What:** Create .docx files in tests using python-docx API, no static files
**When to use:** BackupManager tests needing documents
**Example:**
```python
# From test_backup.py
@pytest.fixture
def sample_docx(tmp_path):
    """Create a sample .docx file for testing."""
    doc_path = tmp_path / "test_document.docx"
    doc = Document()
    doc.add_paragraph("This is a test document.")
    doc.save(doc_path)
    return doc_path
```

#### Pattern 5: Error Path Testing with pytest.raises
**What:** Test exception handling with pytest.raises context manager
**When to use:** Invalid inputs, corrupt files, missing resources
**Example:**
```python
# From test_config.py
def test_invalid_json(self, tmp_path):
    """Test handling of invalid JSON files."""
    config_path = tmp_path / "invalid.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        ConfigManager(config_path)
```

#### Pattern 6: Integration Tests with Real Components
**What:** Test multiple components together (BackupManager + DatabaseManager)
**When to use:** Verify component interactions
**Example:**
```python
# From test_backup.py
class TestBackupManagerIntegration:
    def test_backup_database_record(self, sample_docx, backup_dir, db_manager):
        """Test backup is recorded in database."""
        manager = BackupManager(backup_dir, db_manager)
        backup_path = manager.create_backup(sample_docx)

        # Verify database record
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backups WHERE backup_path = ?", ...)
            row = cursor.fetchone()

        assert row is not None
```

### Anti-Patterns to Avoid
- **❌ Shared state between tests** - Each test should be isolated
- **❌ File-based databases in tests** - Use :memory: for speed and isolation
- **❌ Static test files** - Generate documents programmatically for reproducibility
- **❌ Testing implementation details** - Test behavior, not internal methods (except for _validate_backup which is critical)
- **❌ Sleeping for timing** - Use deterministic waits or mock time

## Don't Hand-Roll

Problems that have existing solutions in the project:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temporary directories | Manual tempfile.mkdtemp | pytest tmp_path fixture | Auto-cleanup, path objects, per-test isolation |
| Test fixtures | Copy-paste setup code | pytest @pytest.fixture | Reusable, dependency injection, scopes |
| Coverage reporting | Manual tracking | pytest-cov with --cov flag | Integrated, HTML reports, line-by-line coverage |
| Database testing | Mock SQLite | :memory: database | Real SQLite, no mocking, fast |
| File encoding | Default encoding | encoding='utf-8' explicitly | Windows cp1252 compatibility |
| Path operations | os.path.join | pathlib.Path | Cross-platform, cleaner API |

**Key insight:** The project's testing infrastructure is already well-designed. Don't reinvent patterns—follow existing test_*.py examples.

## Common Pitfalls

### Pitfall 1: Windows Encoding Issues (CRITICAL)
**What goes wrong:** Tests pass on Linux/Mac but fail on Windows due to cp1252 vs UTF-8
**Why it happens:** Python defaults to system encoding on Windows (cp1252, not UTF-8)
**How to avoid:** **ALWAYS** use `encoding='utf-8'` in all file operations
**Warning signs:** UnicodeDecodeError on Windows, tests with emoji/Chinese characters fail
**Example:**
```python
# ❌ WRONG - Will fail on Windows with Unicode
with open(config_path, 'r') as f:
    data = json.load(f)

# ✅ CORRECT - Explicit UTF-8
with open(config_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
```
**Test coverage:** test_config.py already has test_load_save_utf8(), test_unicode_in_keys_and_values()

### Pitfall 2: SQLite Foreign Key Enforcement
**What goes wrong:** Foreign key constraints not enforced, CASCADE delete doesn't work
**Why it happens:** SQLite requires `PRAGMA foreign_keys = ON` per connection
**How to avoid:** DatabaseManager already handles this in get_connection()
**Warning signs:** Orphaned records, cascade deletes don't work
**Test coverage:** test_db_manager.py has TestForeignKeys class

### Pitfall 3: Log File Rotation Boundary
**What goes wrong:** Logs written at maxBytes boundary may lose data
**Why it happens:** RotatingFileHandler rotates mid-write if size exceeded
**How to avoid:** Use atomic writes, test rotation explicitly
**Warning signs:** Truncated log entries, missing log lines
**Test coverage:** test_logger.py has test_file_rotation() but uses small file size (1KB)

### Pitfall 4: Backup Validation Race Condition
**What goes wrong:** Backup created but validation fails due to timing
**Why it happens:** File written but not fully flushed to disk before validation
**How to avoid:** shutil.copy2() already handles this (waits for complete write)
**Warning signs:** Intermittent validation failures, more common on slow I/O
**Test coverage:** test_backup.py has test_validate_valid_backup() and test_validate_corrupt_backup()

### Pitfall 5: In-Memory Database Persistence
**What goes wrong:** In-memory database lost between connections
**Why it happens:** Each sqlite3.connect(":memory:") creates NEW database
**How to avoid:** DatabaseManager maintains persistent connection for :memory: (lines 36-43)
**Warning signs:** Test data disappears, "table not found" errors
**Test coverage:** test_db_manager.py line 482+ tests :memory: initialization

### Pitfall 6: Thread-Safety Testing Flakiness
**What goes wrong:** Thread-safety tests fail intermittently
**Why it happens:** Race conditions, timing-dependent behavior
**How to avoid:** Use locks, check_same_thread=False, sufficient thread count
**Warning signs:** Tests pass locally but fail in CI, non-deterministic failures
**Test coverage:** test_db_manager.py TestThreadSafety class with 5 threads × 10 operations

### Pitfall 7: ConfigManager Dot Notation Edge Cases
**What goes wrong:** get("key.sub") returns None when intermediate value is not dict
**Why it happens:** Dot notation assumes nested dicts, but value could be string
**How to avoid:** ConfigManager.get() checks isinstance(value, dict) at line 68
**Warning signs:** Unexpected None returns, AttributeError: 'str' has no attribute 'get'
**Test coverage:** test_config.py has test_get_with_non_dict_intermediate()

## Code Examples

Verified patterns from existing test files:

### Testing ConfigManager with Unicode
```python
# Source: test_config.py lines 15-29
@pytest.mark.unit
def test_load_save_utf8(self, tmp_path):
    """Test load/save with UTF-8 characters (emoji, Chinese)."""
    config_path = tmp_path / "test_config.json"
    config = ConfigManager(config_path)

    # Set values with Unicode characters
    config.set("test.emoji", "Hello 😀 World 🎉")
    config.set("test.chinese", "测试中文字符")

    # Reload and verify persistence
    config2 = ConfigManager(config_path)
    assert config2.get("test.emoji") == "Hello 😀 World 🎉"
    assert config2.get("test.chinese") == "测试中文字符"
```

### Testing BackupManager with Database Integration
```python
# Source: test_backup.py lines 148-169
@pytest.mark.unit
def test_backup_database_record(self, sample_docx, backup_dir, db_manager):
    """Test backup is recorded in database."""
    manager = BackupManager(backup_dir, db_manager)

    # Create backup without job_id
    backup_path = manager.create_backup(sample_docx)

    # Verify database record
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM backups WHERE backup_path = ?",
            (str(backup_path.resolve()),)
        )
        row = cursor.fetchone()

    assert row is not None
    assert row["original_path"] == str(sample_docx.resolve())
    assert row["job_id"] is None  # No job_id provided
    assert row["restored"] == 0
    assert row["size_bytes"] > 0
```

### Testing Logger Rotation
```python
# Source: test_logger.py lines 118-149
@pytest.mark.unit
def test_file_rotation(self, tmp_path):
    """Test file rotation when size limit is reached."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger with very small max size for testing
    logger = logging.getLogger("test_rotation")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    # Create handler with 1KB max size
    from logging.handlers import RotatingFileHandler
    log_file = log_dir / "test_rotation.log"
    handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=1024,  # 1KB for testing
        backupCount=10,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Write enough data to trigger rotation
    large_message = "X" * 200
    for i in range(10):  # Write 2KB total
        logger.info(large_message)

    # Verify rotation occurred
    rotated_file = Path(str(log_file) + ".1")
    assert rotated_file.exists()
```

### Testing DatabaseManager Foreign Keys
```python
# Source: test_db_manager.py lines 217-249
@pytest.mark.unit
def test_foreign_key_cascade_delete(self, tmp_path):
    """Test job_results CASCADE delete when parent job is deleted."""
    db = DatabaseManager(tmp_path / "data" / "test.db")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Create a job
        job_id = db.generate_id()
        cursor.execute("""
            INSERT INTO jobs (id, created_at, operation, config, status)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, datetime.now().isoformat(), "test", "{}", "pending"))

        # Create job results
        result_id = db.generate_id()
        cursor.execute("""
            INSERT INTO job_results (id, job_id, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (result_id, job_id, "test.docx", "success", datetime.now().isoformat()))

        # Delete job (should cascade to job_results)
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()

        # Verify result was deleted (CASCADE)
        cursor.execute("SELECT COUNT(*) as count FROM job_results WHERE job_id = ?", (job_id,))
        assert cursor.fetchone()["count"] == 0
```

### Testing Transaction Rollback
```python
# Source: test_db_manager.py lines 307-332
@pytest.mark.unit
def test_connection_rollback_on_error(self, tmp_path):
    """Test connection rolls back on exception."""
    db = DatabaseManager(tmp_path / "data" / "test.db")

    # Try to insert invalid data
    with pytest.raises(sqlite3.IntegrityError):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Insert valid data
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, ("key1", "value1", datetime.now().isoformat()))

            # Try to insert duplicate key (should fail and rollback)
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, ("key1", "value2", datetime.now().isoformat()))

    # Verify no data was committed (transaction rolled back)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM settings")
        assert cursor.fetchone()["count"] == 0
```

## State of the Art

This project uses current patterns (as of 2025):

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unittest.TestCase | pytest with fixtures | pytest 3.0+ (2016) | Simpler syntax, better fixtures, less boilerplate |
| Mock library | unittest.mock (stdlib) | Python 3.3+ (2012) | No external dependency for basic mocking |
| tempfile.mkdtemp | pytest tmp_path fixture | pytest 3.9+ (2018) | Auto-cleanup, pathlib.Path objects |
| @mock.patch decorators | pytest monkeypatch fixture | pytest 2.7+ (2015) | Cleaner test code, auto-cleanup |
| Manual coverage | pytest-cov plugin | Coverage.py 4.0+ (2015) | Integrated reporting, parallel support |

**Deprecated/outdated:**
- `unittest.TestCase` - Still works but pytest's function-based tests are simpler
- `nose` testing framework - Unmaintained since 2016, use pytest
- `@mock.patch` everywhere - Use sparingly, prefer real components or monkeypatch

**Current best practices (reflected in existing tests):**
- Function-based tests with pytest fixtures (not unittest.TestCase)
- Explicit encoding='utf-8' for Windows compatibility
- In-memory databases for speed (not mocked database)
- Programmatic test data generation (not static files)
- Class-based organization for grouping related tests

## Open Questions

Things that couldn't be fully resolved:

1. **Database Migration Testing**
   - What we know: DatabaseManager has _init_database() that creates schema
   - What's unclear: How to test schema migrations when tables already exist
   - Recommendation: Not required for Phase 3 (per CONTEXT.md "Claude's Discretion"). If needed, test by creating DB, modifying schema version, running migration function.

2. **Windows-Specific File Locking**
   - What we know: BackupManager handles PermissionError gracefully
   - What's unclear: Whether to test file locking scenarios (file open in Word)
   - Recommendation: Not required (per CONTEXT.md "not required"). Current error handling is sufficient.

3. **Logger Performance Under Load**
   - What we know: RotatingFileHandler is thread-safe
   - What's unclear: Whether to test high-throughput logging scenarios
   - Recommendation: Not needed for this phase. Performance tests are Phase 6 concern.

4. **Backup Cleanup During Active Processing**
   - What we know: cleanup_old_backups() checks restored flag
   - What's unclear: Edge case where backup is being created during cleanup
   - Recommendation: Current implementation is safe (cleanup only deletes old backups, not recent ones). Add integration test if time permits.

## Sources

### Primary (HIGH confidence)
- Existing test files: tests/unit/test_config.py, test_backup.py, test_logger.py, test_db_manager.py (direct codebase inspection)
- Implementation files: src/core/config.py, backup.py, logger.py, src/database/db_manager.py (direct codebase inspection)
- Project CLAUDE.md: Testing strategy section (lines 199-549)
- Phase CONTEXT.md: Test isolation strategy and error conditions (direct from phase planning)

### Secondary (MEDIUM confidence)
- pytest documentation (pytest.org) - verified fixture patterns match existing tests
- Python logging.handlers documentation - RotatingFileHandler behavior
- sqlite3 documentation - :memory: database behavior and foreign keys

### Tertiary (LOW confidence)
- None - all findings verified against actual codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, verified in requirements-dev.txt
- Architecture: HIGH - Patterns established in 4 existing test files totaling 1800+ lines
- Pitfalls: HIGH - Identified from actual code (e.g., DatabaseManager :memory: handling, ConfigManager dot notation edge cases)
- Error conditions: MEDIUM - Some error paths tested, but CONTEXT.md requests additional coverage

**Research date:** 2026-01-30
**Valid until:** 60 days (testing patterns stable, pytest 8.0 released Feb 2024)

**Gaps identified from success criteria:**
1. ConfigManager: Missing corrupt JSON error message validation (line 115 raises but doesn't verify message)
2. BackupManager: Disk full scenario not tested (CONTEXT.md requests this)
3. Logger: Unicode edge cases tested but rotation boundary edge case needs verification
4. DatabaseManager: Schema migration testing deferred (not blocking for Phase 3)

**Next steps for planner:**
1. Audit existing tests against success criteria
2. Identify specific missing test cases (not entire test files)
3. Focus on error conditions from CONTEXT.md (disk full, constraint violations)
4. Verify Windows-specific behavior (encoding, paths with spaces)
