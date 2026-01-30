# Phase 1: Test Infrastructure - Research

**Researched:** 2026-01-30
**Domain:** Python testing infrastructure (pytest, python-docx, SQLite)
**Confidence:** HIGH

## Summary

Phase 1 focuses on ensuring pytest collects tests successfully and providing foundational fixtures for programmatic test document generation and database isolation. Current investigation reveals **tests are already collecting successfully** (288 tests found) with a well-structured conftest.py in place. The primary research question shifts from "how to fix imports" to "how to validate and potentially enhance existing infrastructure."

Key findings:
- **Import resolution is working**: Tests collect without `ModuleNotFoundError` because `src/__init__.py` exists and pytest's default `prepend` mode adds test directories to `sys.path`
- **Existing fixtures are comprehensive**: conftest.py already provides `docx_factory`, `test_db`, `temp_workspace`, and specialized fixtures following pytest best practices
- **In-memory database pattern is correctly implemented**: Uses persistent connection for `:memory:` databases to maintain schema across operations

**Primary recommendation:** Validate existing fixtures meet requirements rather than rebuilding from scratch. Focus on verification, documentation, and gap analysis.

## Standard Stack

The established libraries/tools for Python testing with pytest, python-docx, and SQLite:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.0.0 | Testing framework | Industry standard for Python testing, fixture system, powerful assertion introspection |
| pytest-qt | 4.3.1 | PySide6 GUI testing | Official Qt testing integration, qtbot fixture for signal/slot verification |
| python-docx | 1.1.0+ | Document manipulation | De facto standard for .docx file operations in Python |
| sqlite3 | 3.50.4 (stdlib) | Database | Built-in Python module, zero dependencies, perfect for testing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | 4.1.0 | Coverage reporting | Always - required for 80% coverage target |
| pytest-mock | 3.12.0 | Mocking utilities | When mocking external dependencies (not for database tests) |
| hypothesis | 6.98.0 | Property-based testing | For testing edge cases with generated inputs |
| faker | 24.0.0 | Fake data generation | When tests need realistic but random data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | pytest has better fixture system, cleaner syntax, more ecosystem support |
| `:memory:` SQLite | File-based test DB | In-memory is faster (10-100x) and provides perfect isolation |
| python-docx | docx2python | python-docx has better write support and active maintenance |

**Installation:**
```bash
# Already in requirements-dev.txt
pip install -r requirements-dev.txt
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py          # Shared fixtures for entire test suite
├── unit/                # Unit tests (fast, isolated)
│   └── conftest.py      # Unit-specific fixtures (if needed)
├── integration/         # Integration tests (multi-component)
├── gui/                 # GUI tests (require display)
└── performance/         # Performance benchmarks
```

**Current state:** ✅ Already implemented correctly

### Pattern 1: Factory Fixtures for Document Generation
**What:** Fixture returns a callable that creates test documents on demand
**When to use:** When tests need customized documents with varying content/metadata

**Example:**
```python
# In conftest.py
@pytest.fixture
def docx_factory(tmp_path):
    """Factory for creating test .docx files."""
    def _create_docx(
        content: str = "",
        filename: str = "test.docx",
        author: str | None = None,
        title: str | None = None,
        add_table: bool = False,
        add_heading: bool = False
    ) -> Path:
        doc = Document()

        if add_heading:
            doc.add_heading("Test Document", level=0)

        if content:
            for line in content.split("\n"):
                if line.strip():
                    doc.add_paragraph(line)

        if add_table:
            table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Header 1"
            table.cell(0, 1).text = "Header 2"

        if author:
            doc.core_properties.author = author
        if title:
            doc.core_properties.title = title

        file_path = tmp_path / filename
        doc.save(str(file_path))
        return file_path

    return _create_docx

# In test
def test_search_replace(docx_factory):
    doc_path = docx_factory(
        content="Hello world\nGoodbye world",
        filename="test.docx"
    )
    # doc_path is Path object to .docx file
```

**Source:** [pytest fixtures documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html)

### Pattern 2: In-Memory Database with Persistent Connection
**What:** Use `:memory:` SQLite with persistent connection to maintain schema across fixture operations
**When to use:** Always for unit/integration tests requiring database

**Example:**
```python
# In conftest.py
@pytest.fixture
def test_db(temp_workspace):
    """Create fresh in-memory SQLite database."""
    from src.database.db_manager import DatabaseManager

    # Create in-memory database (auto-initializes schema)
    db = DatabaseManager(":memory:")
    yield db
    db.close()

# In test
def test_job_creation(test_db):
    job_id = test_db.create_job(operation="search_replace")
    assert job_id is not None
```

**Critical detail:** For `:memory:` databases, DatabaseManager uses a **persistent connection** stored in `_persistent_conn` attribute. This is essential because each new connection to `:memory:` creates a separate, empty database. The persistent connection ensures schema and data persist across operations within the fixture scope.

**Source:** [SQLite in-memory documentation](https://www.sqlite.org/inmemorydb.html)

### Pattern 3: Pytest Scope Hierarchy
**What:** Match fixture scope to actual resource needs
**When to use:** Always - affects test isolation and performance

**Scope hierarchy (highest to lowest):**
```
session → package → module → class → function
```

**Best practices:**
- **function scope (default)**: Use for test-specific data (docx files, database instances)
- **session scope**: Use for expensive one-time setup (QApplication instance)
- **module/class scope**: Rarely needed - breaks test isolation

**Current state:** ✅ Correctly implemented
- `qapp` = session (QApplication created once)
- `test_db` = function (fresh database per test)
- `docx_factory` = function (creates files in tmp_path per test)

**Source:** [pytest fixture scopes documentation](https://docs.pytest.org/en/stable/reference/fixtures.html)

### Pattern 4: Workspace Isolation
**What:** Create temporary directory structure matching application layout
**When to use:** Integration tests needing data/, backups/, logs/ directories

**Example:**
```python
@pytest.fixture
def temp_workspace(tmp_path):
    """Create isolated workspace with app directory structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "data").mkdir()
    (workspace / "backups").mkdir()
    (workspace / "logs").mkdir()
    return workspace
```

**Source:** [pytest tmp_path documentation](https://docs.pytest.org/en/stable/how-to/tmp_path.html)

### Anti-Patterns to Avoid

- **Mocking the database**: Use real in-memory SQLite instead of mocks - faster, more reliable, tests actual SQL
- **Pre-generated binary test files**: Use programmatic generation instead - version-controllable, reproducible, customizable
- **Shared state between tests**: Each test should get fresh fixtures (function scope) - prevents test order dependencies
- **Nested conftest.py without reason**: Only split when fixtures are truly specific to subdirectory - avoid duplication

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test file cleanup | Manual `os.remove()` in teardown | pytest `tmp_path` fixture | Automatic cleanup, unique paths, works across platforms |
| Database mocking | Custom mock objects | Real in-memory SQLite | Faster, tests actual SQL, catches schema errors |
| GUI signal testing | Manual `QTimer` + event loop | pytest-qt `qtbot.waitSignal()` | Handles timeouts, races, provides clear error messages |
| Temporary directories | `tempfile.mkdtemp()` + manual cleanup | pytest `tmp_path` | Automatic cleanup, better error messages, pytest integration |
| Fixture dependencies | Implicit order via naming | Explicit fixture parameters | pytest linearizes dependencies, self-documenting |

**Key insight:** pytest's fixture system handles resource lifecycle (setup/teardown), dependency resolution, and cleanup automatically. Custom solutions almost always have edge cases with cleanup failures or race conditions.

## Common Pitfalls

### Pitfall 1: Multiple Connections to `:memory:` Database
**What goes wrong:** Creating new SQLite connections to `:memory:` results in separate, empty databases

**Example of broken code:**
```python
# BROKEN - each connection sees different data
db = DatabaseManager(":memory:")
with db.get_connection() as conn1:
    conn1.execute("CREATE TABLE test (id INTEGER)")

# This would create NEW empty database (if using new connection)
with db.get_connection() as conn2:
    # Would fail - table doesn't exist in this connection's database
    conn2.execute("SELECT * FROM test")
```

**Why it happens:** SQLite `:memory:` creates a new database for each connection. The database is destroyed when its connection closes.

**How to avoid:** Use persistent connection stored in instance variable for in-memory databases:
```python
# CORRECT - DatabaseManager implementation
def __init__(self, db_path):
    if db_path == ":memory:":
        self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_database()  # Schema created once

def get_connection(self):
    if self._is_memory:
        yield self._persistent_conn  # Reuse same connection
```

**Warning signs:**
- Tests fail with "no such table" errors
- Schema initialization runs but tables aren't found
- Database appears empty despite writes

**Source:** [SQLite in-memory databases](https://www.sqlite.org/inmemorydb.html)

### Pitfall 2: Import Errors from Missing `__init__.py`
**What goes wrong:** `ModuleNotFoundError: No module named 'src'` when running tests

**Why it happens:** Python requires `__init__.py` files to treat directories as packages. Without them, pytest cannot import from `src/` even if it's in `sys.path`.

**How to avoid:**
```bash
# Verify __init__.py exists in all package directories
src/__init__.py
src/core/__init__.py
src/database/__init__.py
src/processors/__init__.py
src/ui/__init__.py
src/utils/__init__.py
```

**Alternative solution (if editable install preferred):**
```bash
# Install package in editable mode
pip install -e .
```

**Warning signs:**
- Tests fail with `ModuleNotFoundError`
- `import src.module` works in REPL but not in tests
- Some imports work, others fail (inconsistent `__init__.py`)

**Source:** [pytest import mechanisms](https://docs.pytest.org/en/stable/explanation/pythonpath.html)

### Pitfall 3: Windows UTF-8 Encoding Issues
**What goes wrong:** Test documents with Unicode characters fail to load or corrupt on Windows

**Why it happens:** Windows defaults to cp1252 encoding. Python file operations without explicit `encoding='utf-8'` use system default.

**How to avoid:**
```python
# ALWAYS specify encoding on Windows
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# python-docx save() is safe - handles encoding internally
doc.save(str(file_path))  # ✅ No encoding parameter needed
```

**Warning signs:**
- `UnicodeDecodeError` when reading JSON config
- Test files with "tëst_文档_файл.docx" fail to process
- Tests pass on Linux/Mac but fail on Windows

**Source:** Project CLAUDE.md Windows considerations

### Pitfall 4: Fixture Scope Too Wide
**What goes wrong:** Tests pass in isolation but fail when run together, or changes from one test leak into another

**Why it happens:** Using `scope="module"` or `scope="session"` for fixtures that should be isolated per test

**How to avoid:**
```python
# WRONG - database shared across all tests in module
@pytest.fixture(scope="module")
def test_db():
    return DatabaseManager(":memory:")

# CORRECT - fresh database per test
@pytest.fixture  # scope="function" is default
def test_db():
    db = DatabaseManager(":memory:")
    yield db
    db.close()
```

**Warning signs:**
- Tests pass individually (`pytest test_file.py::test_name`) but fail in suite
- Test order affects results
- Cleanup code in one test affects next test

**Source:** [pytest fixture scopes](https://docs.pytest.org/en/stable/reference/fixtures.html)

### Pitfall 5: Not Closing Database Connections
**What goes wrong:** "Database is locked" errors, resource leaks, tests hang

**Why it happens:** SQLite locks database files. Unclosed connections hold locks.

**How to avoid:**
```python
# Use context manager OR explicit close
@pytest.fixture
def test_db():
    db = DatabaseManager(":memory:")
    yield db
    db.close()  # ✅ Cleanup always runs

# Or use autouse cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_workers():
    yield
    import gc
    gc.collect()  # Force cleanup of any lingering resources
```

**Warning signs:**
- Intermittent "database is locked" errors
- Tests pass when run individually but fail in parallel
- Process doesn't exit after tests complete

## Code Examples

Verified patterns from official sources and existing codebase:

### Creating Test Documents (python-docx)
```python
# Source: https://python-docx.readthedocs.io/en/latest/user/quickstart.html
from docx import Document
from pathlib import Path

def create_test_document(output_path: Path):
    """Create test .docx with paragraphs, headings, and metadata."""
    doc = Document()

    # Add heading (level 0 = title, 1-9 = heading levels)
    doc.add_heading('Test Document Title', level=0)

    # Add paragraphs
    doc.add_paragraph('First paragraph of content.')
    doc.add_paragraph('Second paragraph of content.')

    # Add table
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = 'Header 1'
    table.cell(0, 1).text = 'Header 2'
    table.cell(1, 0).text = 'Data 1'
    table.cell(1, 1).text = 'Data 2'

    # Set metadata (core properties)
    doc.core_properties.author = 'Test Author'
    doc.core_properties.title = 'Sample Document'

    # Save (python-docx handles encoding internally)
    doc.save(str(output_path))
    return output_path
```

### Using Factory Fixtures
```python
# Source: tests/conftest.py (existing implementation)
def test_document_creation(docx_factory):
    """Test creating customized document."""
    doc_path = docx_factory(
        content="Line 1\nLine 2\nLine 3",
        filename="custom.docx",
        author="Test Author",
        title="Test Title",
        add_heading=True,
        add_table=False
    )

    # Verify file exists
    assert doc_path.exists()

    # Verify content
    from docx import Document
    doc = Document(str(doc_path))
    assert len(doc.paragraphs) == 4  # heading + 3 content paragraphs
    assert doc.core_properties.author == "Test Author"
```

### In-Memory Database Testing
```python
# Source: tests/unit/test_db_manager.py (existing implementation)
def test_job_creation(test_db):
    """Test creating and retrieving job record."""
    # test_db is DatabaseManager(":memory:") with schema initialized

    job_id = test_db.create_job(
        operation="search_replace",
        config={"find": "test", "replace": "example"}
    )

    # Verify job created
    assert job_id is not None

    # Retrieve and verify
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()

    assert job["operation"] == "search_replace"
    assert job["status"] == "pending"
```

### Helper Utilities for Assertions
```python
# Source: tests/conftest.py (existing implementation)
def assert_docx_contains_text(docx_path: Path, expected_text: str):
    """Verify text exists in document."""
    from docx import Document
    doc = Document(str(docx_path))
    full_text = "\n".join([para.text for para in doc.paragraphs])
    assert expected_text in full_text, f"Expected '{expected_text}' not found"

def assert_docx_property(docx_path: Path, property_name: str, expected_value: str):
    """Verify document metadata property."""
    from docx import Document
    doc = Document(str(docx_path))
    actual = getattr(doc.core_properties, property_name)
    assert actual == expected_value, f"{property_name} = '{actual}', expected '{expected_value}'"

# Usage in tests
def test_metadata_update(docx_factory):
    doc_path = docx_factory(author="Original Author")
    # ... perform metadata update operation ...
    assert_docx_property(doc_path, "author", "Updated Author")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unittest.TestCase | pytest with fixtures | ~2015 | Cleaner syntax, better isolation, ecosystem support |
| Pre-generated .docx test files | Programmatic generation via fixtures | 2020+ | Version control friendly, reproducible, customizable |
| File-based test databases | In-memory SQLite | Always available | 10-100x faster, perfect isolation, no cleanup needed |
| Manual sys.path manipulation | pytest pythonpath config or editable install | pytest 7.0+ (2021) | Standardized, works across environments |
| Mocking database for tests | Real in-memory database | 2010+ | Tests actual SQL, catches schema bugs, faster |

**Deprecated/outdated:**
- `pytest.config` (removed in pytest 5.0): Use `pytestconfig` fixture instead
- `tmpdir` fixture: Use `tmp_path` (returns `Path` object instead of `py.path.local`)
- `pytest.mark.parametrize(..., ids=lambda x: str(x))`: Use `ids=` with list of strings

## Open Questions

Things that couldn't be fully resolved:

1. **Should test_db fixture support both in-memory and file-based modes?**
   - What we know: In-memory is always faster and provides better isolation
   - What's unclear: Are there integration tests that need file-based persistence?
   - Recommendation: Start with in-memory only, add file-based variant if needed (e.g., `test_db_persistent` fixture)

2. **Should conftest.py be split into multiple files?**
   - What we know: Current conftest.py is ~488 lines with clear sections
   - What's unclear: Team preference on file size vs. consolidation
   - Recommendation: Keep single file until it exceeds ~800 lines or team requests split

3. **Do we need specialized fixtures for multiprocessing tests?**
   - What we know: Multiprocessing requires `freeze_support()` on Windows
   - What's unclear: How to test worker pools without actual processes (slow)
   - Recommendation: Defer to Phase 2 when worker tests are implemented

## Sources

### Primary (HIGH confidence)
- [pytest fixtures documentation](https://docs.pytest.org/en/stable/reference/fixtures.html) - Official pytest fixture reference
- [pytest import mechanisms](https://docs.pytest.org/en/stable/explanation/pythonpath.html) - Official pytest import documentation
- [python-docx quickstart](https://python-docx.readthedocs.io/en/latest/user/quickstart.html) - Official python-docx documentation
- [python-docx API reference](https://python-docx.readthedocs.io/en/latest/api/document.html) - Document and core_properties API
- [SQLite in-memory databases](https://www.sqlite.org/inmemorydb.html) - Official SQLite documentation
- `tests/conftest.py` - Existing implementation (verified working, 288 tests collect)
- `src/database/db_manager.py` - DatabaseManager implementation with in-memory support

### Secondary (MEDIUM confidence)
- [Pytest Conftest With Best Practices](https://pytest-with-eric.com/pytest-best-practices/pytest-conftest/) - Community best practices
- [How to Setup Memory Database Test with PyTest](https://medium.com/@johnidouglasmarangon/how-to-setup-memory-database-test-with-pytest-and-sqlalchemy-ca2872a92708) - Pattern examples
- [How to Solve ModuleNotFoundError With Pytest](https://betterstack.com/community/questions/how-to-solve-the-modulenotfounderror-with-pytest/) - Solutions verified against official docs
- [4 Proven Ways To Define Pytest PythonPath](https://pytest-with-eric.com/introduction/pytest-pythonpath/) - Community solutions

### Tertiary (LOW confidence)
- [Testing CRUD Operations with SQLite](https://noplacelikelocalhost.medium.com/testing-crud-operations-with-sqlite-a-time-saving-guide-for-developers-7c74405d63d5) - General patterns only
- [Mastering python-docx](https://www.w3resource.com/python/mastering-python-docx.php) - Tutorial, not authoritative

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified as industry standard with active maintenance
- Architecture: HIGH - Patterns verified in official documentation and existing codebase
- Pitfalls: HIGH - Based on official documentation + real project experience (existing tests demonstrate patterns)

**Research date:** 2026-01-30
**Valid until:** 60 days (stable ecosystem - pytest, python-docx, SQLite are mature)

**Key discovery:** Tests are already collecting successfully. The infrastructure exists and follows best practices. Phase 1 planning should focus on **validation and documentation** rather than building from scratch.
