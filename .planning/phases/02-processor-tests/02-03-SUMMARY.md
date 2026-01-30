---
phase: 02-processor-tests
plan: 03
subsystem: testing
tags: [search-replace, unit-tests, consolidation]

dependency-graph:
  requires:
    - "02-01 (extended fixtures: docx_factory, docx_with_table)"
  provides:
    - "Consolidated search/replace test suite (61 tests)"
    - "92% coverage of search_replace.py"
  affects:
    - "No downstream impacts"

tech-stack:
  used:
    - pytest: Test framework with markers and parametrize
    - python-docx: Document generation for tests
    - fixtures: docx_factory, docx_with_table, tmp_path, large_docx

files:
  created:
    - tests/unit/test_search_replace.py (1074 lines, 61 tests)
  deleted:
    - tests/unit/test_search_replace_patterns.py (removed in prior commit)
    - tests/unit/test_paragraph_replacement.py (removed in prior commit)
    - tests/unit/test_table_header_footer.py (removed in prior commit)

metrics:
  duration: "11 min"
  completed: "2026-01-30"
  tests_added: 61
  coverage: "91.93% (search_replace.py)"
---

# Phase 02 Plan 03: Search & Replace Test Consolidation Summary

Consolidated and converted Search & Replace processor tests to use programmatic document generation via docx_factory fixture.

## Key Deliverables

### test_search_replace.py (61 tests, 1074 lines)

**Test Classes:**
1. **TestPatternCompilation (18 tests)**
   - Literal search: case sensitive/insensitive, whole words, special chars, parentheses, brackets
   - Regex search: basic, case handling, capture groups, word boundaries, alternation
   - Unicode and emoji support
   - subn replacement functionality

2. **TestParagraphReplacement (15 tests)**
   - Format preservation: bold, italic, underline
   - Multiple occurrences, case insensitive, regex replacement
   - Unicode, emoji, partial run, multi-run handling
   - Empty paragraph and run edge cases

3. **TestTableReplacement (8 tests)**
   - Basic replacement, all cells, format preservation
   - Multiple paragraphs per cell, no match, empty table
   - Unicode in tables, nested table handling

4. **TestHeaderFooterReplacement (5 tests)**
   - Header replacement, footer replacement, both
   - Disabled flags, multiple sections

5. **TestPerformSearchReplace (3 tests)**
   - All sections, body-only, tables-only

6. **TestProcessDocument (5 tests)**
   - Success case, saves document, file not found
   - Corrupted file handling, no match returns zero

7. **TestEdgeCases (7 tests)**
   - Empty document, empty search term
   - Replacement with empty string (deletion)
   - Parametrized scenarios, large document
   - Special characters in replacement

## Migration Approach

**Before:** 3 files with static .docx dependencies
- test_search_replace_patterns.py (used shutil.copy)
- test_paragraph_replacement.py (used test_docs_dir fixture)
- test_table_header_footer.py (used static file copies)

**After:** 1 consolidated file with programmatic generation
- All documents created via docx_factory, docx_with_table, or tmp_path
- No static file dependencies
- Tests organized by concern into classes
- All tests marked with @pytest.mark.unit

## Verification Results

```
pytest tests/unit/test_search_replace.py -v
============================= 61 passed in 11.97s =============================

search_replace.py coverage: 91.93%
```

## Deviations from Plan

**Minor deviation:** Task 3 (remove deprecated files) was already completed by a parallel plan execution (02-04). The files had been deleted in commit `183cb7a`. No additional action needed.

## Commits

| Hash | Message |
|------|---------|
| 9448b14 | test(02-03): add consolidated search/replace tests - pattern, paragraph, table |
| 0cd09d3 | test(02-03): add header/footer and process_document tests |

## Success Criteria Verification

- [x] test_search_replace.py exists with 40+ tests (61 tests)
- [x] All tests use docx_factory or tmp_path (programmatic generation)
- [x] Old test files removed (by prior commit 183cb7a)
- [x] Pattern compilation, paragraph, table, header/footer, process_document all tested
- [x] Error paths tested (file not found, corrupted file, no match)

## Next Steps

Phase 2 plans continue with metadata (02-04), style_enforcer, and validator test consolidation. This plan provides the pattern for consolidating processor tests.
