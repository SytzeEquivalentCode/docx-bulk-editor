# Phase 2: Processor Tests - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate all five document processors with comprehensive behavior coverage. Tests document expected behavior and serve as regression protection. Processors are: Search & Replace, Metadata, Table Formatter, Style Enforcer, and Validator.

This phase writes tests for existing processors. It does not implement new processor functionality.

</domain>

<decisions>
## Implementation Decisions

### Test organization
- One file per processor (test_search_replace.py, test_metadata.py, test_table_formatter.py, test_style_enforcer.py, test_validator.py)
- Consolidate existing test files (test_search_replace_patterns.py, test_metadata.py) into unified processor test files
- Use pytest markers for test categorization (slow, edge_case, error_path, etc.) — enables selective test runs

### Claude's Discretion
- Internal test file organization (classes vs flat functions) based on test count and complexity per processor

### Coverage priorities
- All five processors get equal depth of coverage
- Search & Replace: test body paragraphs and tables; headers/footers are lower priority
- Edge cases: Unicode (中文), emoji (😀), regex special characters, and empty documents — all explicitly tested
- Error handling: all error paths tested — invalid file, corrupt document, missing config keys, permission denied

### Test data approach
- Programmatic only — all test documents created via docx_factory fixture
- No static .docx files in repo (reproducible, version-controlled)
- Extend docx_factory with table helpers (add_table(rows, cols)) and style helpers (add_styled_paragraph(style_name))
- Metadata fixture creates documents with pre-populated standard metadata (known author, title, etc.)
- Use pytest tmp_path for auto-cleanup — no persistent test files

### Assertion patterns
- Verify both ProcessorResult AND reload document to verify actual content — don't trust reported changes_made alone
- Helper assertions in conftest.py: assert_docx_contains(), assert_metadata_equals()
- Table/style tests: check specific cells and style properties, not just structure
- Verify unchanged document parts remain unchanged (preservation checks)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following pytest conventions and existing conftest.py patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-processor-tests*
*Context gathered: 2026-01-30*
