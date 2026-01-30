# Phase 2: Processor Tests - Research

**Researched:** 2026-01-30
**Domain:** python-docx testing with pytest, document processor validation patterns
**Confidence:** HIGH

## Summary

Processor testing validates five document processors (Search & Replace, Metadata, Table Formatter, Style Enforcer, Validator) using pytest with comprehensive behavior coverage. The codebase already has strong infrastructure in place: conftest.py with docx_factory fixture for programmatic document generation, pytest.ini with markers, and ProcessorResult dataclass for multiprocessing compatibility.

**Key research findings:**
- Existing test patterns in test_search_replace_patterns.py and test_metadata.py demonstrate mature testing approach with edge cases (Unicode, emoji, error handling)
- python-docx requires reload-and-verify pattern: don't trust ProcessorResult.changes_made alone; reload document and verify actual content changes
- Table/style processors need XML manipulation testing (borders, shading) since python-docx lacks high-level APIs for some formatting operations
- pytest parametrize is essential for covering edge cases efficiently (multiple input/output combinations in single test function)
- Header/footer testing has complexities (is_linked_to_previous behavior, section inheritance) that require careful verification

**Primary recommendation:** Follow existing test patterns in test_search_replace_patterns.py and test_metadata.py as templates. Extend docx_factory fixture with table/style helpers. Use parametrized tests for edge case coverage. Verify actual document content after every operation (reload pattern).

## Standard Stack

The project already has all required testing dependencies installed.

### Core Testing Framework
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.0.0 | Test framework | 52% of Python developers use pytest (JetBrains 2023 survey) - dominant framework |
| python-docx | 1.1.0+ | Document manipulation | Official library for .docx operations - already in use |
| docx | N/A | Not to be confused with python-docx | python-docx is the correct package |

### Supporting Test Tools
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | 4.1.0 | Coverage reporting | Every test run (already in pytest.ini addopts) |
| pytest-xdist | 3.5.0 | Parallel execution | For faster test runs: pytest -n auto |
| pytest-mock | 3.12.0 | Mocking utilities | Mock file I/O errors, permission denied scenarios |
| hypothesis | 6.98.0 | Property-based testing | Generate edge cases automatically (optional, advanced) |
| pytest-benchmark | 4.0.0 | Performance testing | Measure processor speed (already used in tests/performance/) |

### Existing Infrastructure (Already Available)
| Component | Location | Purpose |
|-----------|----------|---------|
| docx_factory | tests/conftest.py | Programmatic .docx creation |
| temp_workspace | tests/conftest.py | Isolated temp directories with cleanup |
| pytest markers | pytest.ini | Test categorization (unit, slow, edge_case, etc.) |
| ProcessorResult | src/processors/__init__.py | Picklable result dataclass for multiprocessing |
| Helper assertions | tests/conftest.py | assert_docx_contains_text(), assert_docx_property() |

**Installation:**
All dependencies already installed via requirements-dev.txt. No additional packages needed.

## Architecture Patterns

### Recommended Test File Structure
```
tests/unit/
├── test_search_replace.py       # Consolidate existing test_search_replace_patterns.py + new tests
├── test_metadata.py              # Already exists, may need consolidation
├── test_table_formatter.py       # New file (similar structure to existing)
├── test_style_enforcer.py        # New file
└── test_validator.py             # New file
```

### Pattern 1: AAA Pattern (Arrange-Act-Assert)
**What:** Structure every test in three phases: setup, execution, verification
**When to use:** Every test function
**Example:**
```python
# Source: Existing test_search_replace_patterns.py (lines 188-218)
def test_process_document_success(docx_factory):
    """Test process_document end-to-end success case."""
    from src.processors.search_replace import process_document
    from docx import Document

    # ARRANGE: Create test document
    doc_path = docx_factory(content="Hello world\nHello again")
    config = {
        'search_term': 'Hello',
        'replace_term': 'Goodbye',
        'use_regex': False,
        'case_sensitive': True,
        'whole_words': False,
        'search_body': True,
        'search_tables': False,
        'search_headers': False,
        'search_footers': False
    }

    # ACT: Process document
    result = process_document(str(doc_path), config)

    # ASSERT: Verify result AND reload document to check actual changes
    assert result.success is True
    assert result.changes_made == 2
    assert result.duration_seconds > 0

    # CRITICAL: Reload and verify actual content
    doc = Document(str(doc_path))
    text = '\n'.join([para.text for para in doc.paragraphs])
    assert 'Goodbye' in text
    assert 'Hello' not in text
```

### Pattern 2: Reload-and-Verify (CRITICAL for Document Testing)
**What:** After processor execution, reload document from disk and verify actual changes
**When to use:** Every test that modifies documents
**Why:** Don't trust ProcessorResult.changes_made alone - verify actual document content changed
**Example:**
```python
# Source: Existing test_metadata.py (lines 222-243)
def test_process_document_success(temp_doc):
    """Test process_document wrapper function with successful operation."""
    config = {
        'metadata_operations': {
            'set': {
                'author': 'Test Author',
                'title': 'Test Title'
            }
        }
    }

    result = process_document(str(temp_doc), config)

    # Check ProcessorResult
    assert result.success is True
    assert result.changes_made == 2

    # CRITICAL: Verify changes were actually saved
    doc = Document(temp_doc)
    assert doc.core_properties.author == 'Test Author'
    assert doc.core_properties.title == 'Test Title'
```

### Pattern 3: Parametrized Edge Cases
**What:** Use @pytest.mark.parametrize to test multiple scenarios with single test function
**When to use:** Testing similar behavior with different inputs (Unicode, special chars, empty values)
**Example:**
```python
# Source: pytest documentation + project conventions
@pytest.mark.parametrize("input_text,search,replace,expected", [
    ("Hello", "Hello", "Goodbye", "Goodbye"),           # Basic replacement
    ("中文测试", "测试", "TEST", "中文TEST"),              # Unicode
    ("😀 emoji", "😀", "🎉", "🎉 emoji"),               # Emoji
    ("test (a)", "(a)", "(b)", "test (b)"),            # Regex special chars
    ("", "anything", "replaced", ""),                   # Empty document
    ("unchanged", "notfound", "replaced", "unchanged"), # No match
])
def test_search_replace_scenarios(docx_factory, input_text, search, replace, expected):
    """Test search/replace with various edge cases."""
    doc_path = docx_factory(content=input_text)
    config = {
        'search_term': search,
        'replace_term': replace,
        'use_regex': False,
        'case_sensitive': True,
        'whole_words': False
    }

    result = process_document(str(doc_path), config)

    # Reload and verify
    doc = Document(str(doc_path))
    actual_text = '\n'.join([p.text for p in doc.paragraphs])
    assert actual_text == expected
```

### Pattern 4: Fixture-Based Document Factory Extensions
**What:** Extend docx_factory with specialized helpers for tables and styles
**When to use:** Tests requiring specific document structures (tables, styled paragraphs)
**Example:**
```python
# Add to tests/conftest.py
@pytest.fixture
def docx_with_table(docx_factory):
    """Create document with multi-row table."""
    def _create(rows=3, cols=2, **kwargs):
        # Use tmp_path from docx_factory's closure
        doc = Document()
        table = doc.add_table(rows=rows, cols=cols)
        for i, row in enumerate(table.rows):
            for j, cell in enumerate(row.cells):
                cell.text = f"R{i}C{j}"

        filepath = kwargs.get('filename', 'table_test.docx')
        # Save and return path (implementation details)
        return filepath
    return _create

# Usage in tests
def test_table_formatting(docx_with_table):
    doc_path = docx_with_table(rows=5, cols=3)
    config = {'table_options': {'standardize_borders': True}}
    result = process_document(str(doc_path), config)

    # Reload and verify border properties
    doc = Document(str(doc_path))
    # Check XML for border properties
```

### Pattern 5: Preservation Checks
**What:** Verify unchanged parts of document remain unchanged
**When to use:** All processor tests (ensure operations are surgical, not destructive)
**Example:**
```python
def test_metadata_preserves_content(docx_factory):
    """Verify metadata changes don't affect document content."""
    original_content = "Paragraph 1\nParagraph 2\nParagraph 3"
    doc_path = docx_factory(content=original_content, author="Old Author")

    config = {
        'metadata_operations': {
            'set': {'author': 'New Author'}
        }
    }

    result = process_document(str(doc_path), config)

    # Reload
    doc = Document(str(doc_path))

    # Verify metadata changed
    assert doc.core_properties.author == 'New Author'

    # PRESERVATION CHECK: Content unchanged
    actual_content = '\n'.join([p.text for p in doc.paragraphs])
    assert actual_content == original_content
```

### Anti-Patterns to Avoid
- **Static .docx files in repo:** Use docx_factory instead - reproducible, version-controlled as code
- **Trusting ProcessorResult alone:** Always reload document and verify actual content
- **Testing implementation details:** Test behavior (what changes), not XML structure directly
- **Massive test functions:** One behavior per test; use parametrize for variations
- **Ignoring error paths:** Test file not found, corrupt documents, missing config keys

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test document generation | Static binary .docx files | docx_factory fixture | Already implemented, reproducible, version-controlled |
| Test data permutations | Copy-paste test functions | @pytest.mark.parametrize | DRY, easier to add cases, pytest -k filtering |
| XML verification helpers | Raw lxml parsing | python-docx API + selective XML checks | python-docx abstracts XML complexity; only drop to XML for borders/shading |
| File cleanup | Manual os.remove() calls | pytest tmp_path fixture | Automatic cleanup, isolated per test |
| Mocking file errors | Custom exception raising | pytest-mock fixture | Standard library, well-tested |
| Edge case generation | Manual list of test cases | hypothesis library (optional) | Automatically generates edge cases, finds bugs you didn't anticipate |

**Key insight:** The project already has mature testing infrastructure (conftest.py fixtures, ProcessorResult dataclass, existing test patterns). Don't reinvent - follow and extend existing patterns.

## Common Pitfalls

### Pitfall 1: Not Reloading Documents After Modification
**What goes wrong:** Test asserts on ProcessorResult.changes_made but doesn't verify actual document content changed
**Why it happens:** ProcessorResult reports "2 changes made" but document.save() might fail silently
**How to avoid:** Always reload document from disk and verify expected changes present
**Warning signs:** Tests pass but documents unchanged in manual testing
**Example:**
```python
# BAD: Only checks result
result = process_document(str(doc_path), config)
assert result.changes_made == 2  # INSUFFICIENT

# GOOD: Reload and verify
result = process_document(str(doc_path), config)
assert result.success is True
doc = Document(str(doc_path))  # Reload from disk
assert doc.core_properties.author == 'Expected Value'  # Verify actual change
```

### Pitfall 2: Header/Footer is_linked_to_previous Complexity
**What goes wrong:** Tests assume headers/footers are independent per section, but they inherit by default
**Why it happens:** python-docx headers use "linked to previous" inheritance - if not explicitly set, headers inherit from prior section
**How to avoid:** Check is_linked_to_previous property; set it to False to break inheritance
**Warning signs:** Header changes affect multiple sections unexpectedly
**Source:** [Header and Footer — python-docx documentation](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/header.html)
**Example:**
```python
def test_header_per_section(docx_factory):
    """Test header changes apply only to target section."""
    doc_path = docx_factory(content="Section 1")
    doc = Document(str(doc_path))

    # Add second section
    doc.add_section()

    # CRITICAL: Break inheritance
    section = doc.sections[1]
    section.header.is_linked_to_previous = False

    # Now section 1 and section 2 have independent headers
    doc.sections[1].header.paragraphs[0].text = "Section 2 Header"

    # Verify sections have different headers
    assert doc.sections[0].header.paragraphs[0].text != doc.sections[1].header.paragraphs[0].text
```

### Pitfall 3: Table Border/Shading Requires XML Manipulation
**What goes wrong:** Looking for high-level python-docx API for cell borders; doesn't exist
**Why it happens:** python-docx has limited table formatting APIs; borders/shading require OxmlElement manipulation
**How to avoid:** Use existing patterns in table_formatter.py (_set_cell_shading, _apply_table_borders); test by verifying XML properties or visual inspection
**Warning signs:** Can't find cell.border or cell.shading in python-docx docs
**Source:** [Table Cell — python-docx documentation](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/table/table-cell.html)
**Example:**
```python
# From src/processors/table_formatter.py (lines 163-178)
def _set_cell_shading(cell, color_hex: str):
    """Set cell background color."""
    tc = cell._tc  # Access underlying XML
    tcPr = tc.get_or_add_tcPr()

    shd = OxmlElement('w:shd')  # Create XML element directly
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

# Test by checking XML or cell._tc properties
def test_cell_shading(docx_with_table):
    doc_path = docx_with_table(rows=2, cols=2)
    config = {'table_options': {'header_background': True}}
    result = process_document(str(doc_path), config)

    doc = Document(str(doc_path))
    # Check first row cells have shading
    first_cell = doc.tables[0].rows[0].cells[0]
    tcPr = first_cell._tc.tcPr
    shd = tcPr.find(qn('w:shd'))
    assert shd is not None
    assert shd.get(qn('w:fill')) == 'D9D9D9'  # Light gray
```

### Pitfall 4: Unicode Encoding Issues on Windows
**What goes wrong:** Tests pass on developer machine but fail on Windows CI due to cp1252 encoding
**Why it happens:** Windows defaults to cp1252 encoding; must explicitly specify UTF-8 when opening files
**How to avoid:** Always use encoding='utf-8' in all file operations (this project's CLAUDE.md emphasizes this)
**Warning signs:** UnicodeDecodeError on Windows CI, tests with Chinese/emoji characters fail
**Example:**
```python
# BAD: Relies on system default encoding
with open('test.txt', 'r') as f:  # cp1252 on Windows
    data = f.read()

# GOOD: Explicit UTF-8
with open('test.txt', 'r', encoding='utf-8') as f:
    data = f.read()

# Note: python-docx handles encoding internally, but config files, logs need explicit encoding
```

### Pitfall 5: Not Testing Error Paths
**What goes wrong:** Only testing happy path (valid inputs); processors crash on invalid inputs in production
**Why it happens:** Error handling seems obvious so gets skipped; "we'll add it later"
**How to avoid:** For every processor, test: file not found, corrupt document, missing config keys, permission denied
**Warning signs:** ProcessorResult always returns success=True in tests
**Example:**
```python
# From existing test_search_replace_patterns.py (lines 221-237)
def test_process_document_file_not_found():
    """Test process_document handles missing file gracefully."""
    from src.processors.search_replace import process_document

    config = {
        'find': 'test',
        'replace': 'sample',
        'use_regex': False,
        'case_sensitive': True,
        'whole_words': False
    }

    result = process_document('/nonexistent/file.docx', config)

    assert result.success is False  # Should fail gracefully
    assert result.changes_made == 0
    assert result.error_message is not None
```

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: Basic Processor Test with Reload Verification
```python
# Source: test_metadata.py (lines 68-84)
@pytest.mark.unit
def test_set_single_metadata_field():
    """Test setting a single metadata field."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'author': 'New Author'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.author == 'New Author'
```

### Example 2: End-to-End Processor Test with File I/O
```python
# Source: test_metadata.py (lines 222-243)
@pytest.mark.unit
def test_process_document_success(temp_doc):
    """Test process_document wrapper function with successful operation."""
    config = {
        'metadata_operations': {
            'set': {
                'author': 'Test Author',
                'title': 'Test Title'
            }
        }
    }

    result = process_document(str(temp_doc), config)

    # Verify ProcessorResult
    assert result.success is True
    assert result.changes_made == 2
    assert result.error_message is None
    assert result.duration_seconds > 0

    # CRITICAL: Verify changes were saved
    doc = Document(temp_doc)
    assert doc.core_properties.author == 'Test Author'
    assert doc.core_properties.title == 'Test Title'
```

### Example 3: Parametrized Unicode/Emoji Edge Cases
```python
# Source: test_metadata.py (lines 200-219)
@pytest.mark.unit
def test_unicode_metadata_values():
    """Test setting metadata with Unicode characters."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'author': '作者名',
                'title': 'Document 文档',
                'keywords': 'test, 测试, émoji 😀'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 3
    assert doc.core_properties.author == '作者名'
    assert doc.core_properties.title == 'Document 文档'
    assert doc.core_properties.keywords == 'test, 测试, émoji 😀'
```

### Example 4: Parametrized Pattern Compilation Tests
```python
# Source: test_search_replace_patterns.py (lines 152-166)
@pytest.mark.unit
def test_unicode_search():
    """Test pattern compilation with Unicode characters."""
    pattern = _compile_pattern('测试', use_regex=False, case_sensitive=True, whole_words=False)

    assert pattern.search('这是测试文本') is not None
    assert pattern.search('This is a test') is None


@pytest.mark.unit
def test_emoji_search():
    """Test pattern compilation with emoji characters."""
    pattern = _compile_pattern('😀', use_regex=False, case_sensitive=True, whole_words=False)

    assert pattern.search('Hello 😀 World') is not None
    assert pattern.search('Hello World') is None
```

### Example 5: Error Path Testing
```python
# Source: test_metadata.py (lines 428-448)
@pytest.mark.unit
def test_set_invalid_property_type(temp_doc):
    """Test that setting property to invalid type doesn't crash (edge case for exception handler)."""
    config = {
        'metadata_operations': {
            'set': {
                'revision': 'not_a_number',  # revision should be int, this triggers exception
                'author': 'Valid Author'  # This should succeed
            }
        }
    }

    result = process_document(str(temp_doc), config)

    # Should succeed overall (exception is caught)
    assert result.success is True
    # Only the valid property should be changed
    assert result.changes_made == 1

    # Verify valid property was set, invalid was skipped
    doc = Document(temp_doc)
    assert doc.core_properties.author == 'Valid Author'
```

### Example 6: Table Processor with XML Verification
```python
# Source: Synthesized from table_formatter.py patterns
@pytest.mark.unit
def test_apply_header_background(docx_with_table):
    """Test header row background application."""
    doc_path = docx_with_table(rows=3, cols=2)

    config = {
        'table_options': {
            'standardize_borders': False,
            'header_background': True,
            'zebra_striping': False
        }
    }

    result = process_document(str(doc_path), config)

    assert result.success is True
    assert result.changes_made == 1  # One table formatted

    # Reload and verify
    doc = Document(str(doc_path))
    table = doc.tables[0]

    # Check first row cells have gray background (XML level)
    from docx.oxml.ns import qn
    for cell in table.rows[0].cells:
        tcPr = cell._tc.tcPr
        shd = tcPr.find(qn('w:shd'))
        assert shd is not None, "Header cell should have shading"
        assert shd.get(qn('w:fill')) == 'D9D9D9', "Should be light gray"

    # Check second row cells don't have background (preservation check)
    for cell in table.rows[1].cells:
        tcPr = cell._tc.tcPr
        if tcPr is not None:
            shd = tcPr.find(qn('w:shd'))
            # Either no shading element or white background
            assert shd is None or shd.get(qn('w:fill')) in [None, 'FFFFFF', 'auto']
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static test .docx files | Programmatic docx_factory | Phase 01 (2026-01-30) | Reproducible, version-controlled, no binary files |
| Separate tests per input | @pytest.mark.parametrize | pytest 2.3+ (2023) | DRY, easier to add test cases |
| unittest.TestCase classes | pytest functions/classes | pytest 8.0 (2024) | Simpler syntax, better fixtures |
| Manual test discovery | pytest automatic discovery | pytest core feature | No test registration needed |
| Implicit test dependencies | Explicit fixtures | pytest core feature | Clear dependencies, better error messages |

**Deprecated/outdated:**
- **unittest framework for new tests**: This project uses pytest exclusively (pytest.ini configured)
- **Static .docx files in tests/test_documents/**: Use docx_factory instead (programmatic generation)
- **Doctest in processors**: Not used in this project; pytest is the standard

## Open Questions

Things that couldn't be fully resolved:

1. **Header/Footer Testing Depth**
   - What we know: Phase 02 context says "headers/footers are lower priority" for Search & Replace
   - What's unclear: Should table_formatter/style_enforcer test headers/footers? They don't currently process them
   - Recommendation: Test header/footer for Search & Replace only (basic coverage). Skip for other processors unless requirements explicitly mention them.

2. **Table Formatter Visual Verification**
   - What we know: Border/shading requires XML-level verification (tcPr elements)
   - What's unclear: Should tests verify visual appearance (human inspection) or just XML properties?
   - Recommendation: Verify XML properties in automated tests. Document expected visual appearance in test docstrings for manual spot-checking.

3. **Style Enforcer Heading Detection Heuristics**
   - What we know: _enforce_heading_styles() uses heuristics (short text, bold, large font) to detect headings
   - What's unclear: Are these heuristics stable? What about false positives?
   - Recommendation: Test known-good cases (short bold text becomes heading) and known-bad cases (long bold text stays paragraph). Accept that heuristics may evolve.

4. **Validator Severity Levels**
   - What we know: Validator returns issues with 'severity' field ('warning', 'info')
   - What's unclear: Should severity affect ProcessorResult? Should UI treat them differently?
   - Recommendation: Test that correct severity assigned for each issue type. Leave UI treatment to later phases (Phase 03+).

## Sources

### Primary (HIGH confidence)
- **Existing codebase**: src/processors/*.py - All five processors examined
- **Existing tests**: tests/unit/test_search_replace_patterns.py, tests/unit/test_metadata.py - Established patterns
- **Project infrastructure**: tests/conftest.py, pytest.ini - Fixture and marker configurations
- [pytest documentation - Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) - Official parametrize guide
- [python-docx documentation - Headers and Footers](https://python-docx.readthedocs.io/en/latest/user/hdrftr.html) - Official header/footer API
- [python-docx documentation - Table Cell](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/table/table-cell.html) - Table formatting details
- [python-docx documentation - Section objects](https://python-docx.readthedocs.io/en/latest/api/section.html) - Section and header/footer API

### Secondary (MEDIUM confidence)
- [Pytest Parametrized Tests Guide](https://pytest-with-eric.com/introduction/pytest-parameterized-tests/) - Edge case testing strategies
- [Advanced Pytest Patterns - Fiddler AI](https://www.fiddler.ai/blog/advanced-pytest-patterns-harnessing-the-power-of-parametrization-and-factory-methods) - Factory pattern examples
- [python-docx GitHub test suite](https://github.com/python-openxml/python-docx/blob/master/tests/parts/test_document.py) - How python-docx itself is tested
- [GeeksforGeeks python-docx Tables Tutorial](https://www.geeksforgeeks.org/python/working-with-tables-python-docx-module/) - Table manipulation examples

### Tertiary (LOW confidence)
- [python-docx Issue #433 - Cell Borders](https://github.com/python-openxml/python-docx/issues/433) - Community discussion on border limitations
- [python-docx Issue #476 - Table Styles](https://github.com/python-openxml/python-docx/issues/476) - Border issues in custom styles

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already installed, pytest extensively documented
- Architecture: HIGH - Existing test patterns are mature and proven (test_search_replace_patterns.py, test_metadata.py)
- Pitfalls: HIGH - Based on actual codebase issues (XML manipulation, header inheritance) and Windows encoding requirements (CLAUDE.md)

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable domain, python-docx 1.x API is stable)
