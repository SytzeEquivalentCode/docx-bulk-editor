"""Unit tests for Search & Replace processor.

Tests cover:
- Pattern compilation (literal, regex, case sensitivity, whole words)
- Paragraph replacement with formatting preservation
- Table cell replacement
- Header and footer replacement
- Edge cases and error handling

Consolidated from: test_search_replace_patterns.py, test_paragraph_replacement.py,
                  test_table_header_footer.py
"""

import pytest
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor

from src.processors.search_replace import (
    process_document,
    perform_search_replace,
    _compile_pattern,
    _replace_in_paragraph,
    _replace_in_table,
)
from src.processors import ProcessorResult


# ============================================================================
# Pattern Compilation Tests
# ============================================================================

class TestPatternCompilation:
    """Tests for _compile_pattern function."""

    @pytest.mark.unit
    def test_literal_case_sensitive(self):
        """Literal search with case sensitivity."""
        pattern = _compile_pattern('Test', use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search('Test') is not None
        assert pattern.search('test') is None
        assert pattern.search('Testing') is not None

    @pytest.mark.unit
    def test_literal_case_insensitive(self):
        """Literal search without case sensitivity."""
        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)

        assert pattern.search('test') is not None
        assert pattern.search('Test') is not None
        assert pattern.search('TEST') is not None

    @pytest.mark.unit
    def test_literal_whole_words_only(self):
        """Literal search with whole words only."""
        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=True)

        assert pattern.search('test') is not None
        assert pattern.search('a test here') is not None
        assert pattern.search('testing') is None
        assert pattern.search('pretest') is None

    @pytest.mark.unit
    def test_literal_escapes_special_chars(self):
        """Literal search escapes regex special characters."""
        special_chars = r'.*+?[]{}()^$|\\'
        pattern = _compile_pattern(special_chars, use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search(special_chars) is not None
        assert pattern.search('anything') is None

    @pytest.mark.unit
    def test_literal_parentheses(self):
        """Literal search with parentheses (common in legal text)."""
        pattern = _compile_pattern('(a)', use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search('(a)') is not None
        assert pattern.search('a') is None

    @pytest.mark.unit
    def test_literal_brackets(self):
        """Literal search with brackets."""
        pattern = _compile_pattern('[test]', use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search('[test]') is not None
        assert pattern.search('test') is None

    @pytest.mark.unit
    def test_regex_basic_pattern(self):
        """Regex search with basic pattern."""
        pattern = _compile_pattern(r'\d+', use_regex=True, case_sensitive=True, whole_words=False)

        assert pattern.search('123') is not None
        assert pattern.search('abc') is None

    @pytest.mark.unit
    def test_regex_case_insensitive(self):
        """Regex search with case insensitivity."""
        pattern = _compile_pattern(r'[a-z]+', use_regex=True, case_sensitive=False, whole_words=False)

        assert pattern.search('abc') is not None
        assert pattern.search('ABC') is not None

    @pytest.mark.unit
    def test_regex_case_sensitive(self):
        """Regex search with case sensitivity."""
        pattern = _compile_pattern(r'[a-z]+', use_regex=True, case_sensitive=True, whole_words=False)

        assert pattern.search('abc') is not None
        assert pattern.search('ABC') is None

    @pytest.mark.unit
    def test_regex_capture_groups(self):
        """Regex search with capture groups."""
        pattern = _compile_pattern(r'(\w+)@(\w+)\.com', use_regex=True, case_sensitive=False, whole_words=False)

        match = pattern.search('user@example.com')
        assert match is not None
        assert match.group(1) == 'user'
        assert match.group(2) == 'example'

    @pytest.mark.unit
    def test_regex_word_boundaries(self):
        """Regex search with user-defined word boundaries."""
        pattern = _compile_pattern(r'\btest\b', use_regex=True, case_sensitive=False, whole_words=False)

        assert pattern.search('test') is not None
        assert pattern.search('a test here') is not None
        assert pattern.search('testing') is None
        assert pattern.search('pretest') is None

    @pytest.mark.unit
    def test_regex_alternation(self):
        """Regex search with alternation (OR)."""
        pattern = _compile_pattern(r'cat|dog', use_regex=True, case_sensitive=False, whole_words=False)

        assert pattern.search('I have a cat') is not None
        assert pattern.search('I have a dog') is not None
        assert pattern.search('I have a bird') is None

    @pytest.mark.unit
    def test_whole_words_ignored_in_regex_mode(self):
        """whole_words parameter is ignored in regex mode."""
        pattern = _compile_pattern(r'test', use_regex=True, case_sensitive=False, whole_words=True)

        # Should match as substring since regex mode ignores whole_words
        assert pattern.search('testing') is not None

    @pytest.mark.unit
    def test_unicode_search(self):
        """Pattern compilation with Unicode characters."""
        pattern = _compile_pattern('测试', use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search('这是测试文本') is not None
        assert pattern.search('This is a test') is None

    @pytest.mark.unit
    def test_emoji_search(self):
        """Pattern compilation with emoji characters."""
        pattern = _compile_pattern('😀', use_regex=False, case_sensitive=True, whole_words=False)

        assert pattern.search('Hello 😀 World') is not None
        assert pattern.search('Hello World') is None

    @pytest.mark.unit
    def test_subn_replacement(self):
        """Compiled pattern can perform substitution."""
        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)

        text = 'This is a test. Testing 123.'
        new_text, count = pattern.subn('REPLACED', text)

        assert count == 2
        assert 'REPLACED' in new_text

    @pytest.mark.unit
    def test_subn_whole_words(self):
        """Substitution with whole words only."""
        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=True)

        text = 'This is a test. Testing 123.'
        new_text, count = pattern.subn('REPLACED', text)

        assert count == 1
        assert new_text == 'This is a REPLACED. Testing 123.'

    @pytest.mark.unit
    def test_multiline_regex(self):
        """Regex pattern with multiline text."""
        pattern = _compile_pattern(r'^test', use_regex=True, case_sensitive=False, whole_words=False)

        # Without MULTILINE flag, ^ only matches start of string
        assert pattern.search('test\nmore') is not None
        assert pattern.search('start\ntest') is None


# ============================================================================
# Paragraph Replacement Tests (Formatting Preservation)
# ============================================================================

class TestParagraphReplacement:
    """Tests for _replace_in_paragraph function with formatting preservation."""

    @pytest.mark.unit
    def test_replace_in_empty_paragraph(self, docx_factory):
        """Replacement in empty paragraph doesn't crash."""
        doc_path = docx_factory(content="")
        doc = Document(str(doc_path))
        # Add empty paragraph
        paragraph = doc.add_paragraph('')

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_paragraph(paragraph, pattern, 'REPLACED')

        assert count == 0

    @pytest.mark.unit
    def test_preserves_bold_formatting(self, tmp_path):
        """Bold formatting preserved after replacement."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('Hello world')
        run.bold = True

        doc_path = tmp_path / "bold.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('Hello', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'Goodbye')

        assert count == 1
        assert 'Goodbye' in doc.paragraphs[0].text
        assert doc.paragraphs[0].runs[0].bold is True

    @pytest.mark.unit
    def test_preserves_italic_formatting(self, tmp_path):
        """Italic formatting preserved after replacement."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('Important text')
        run.italic = True

        doc_path = tmp_path / "italic.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('Important', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'Critical')

        assert count == 1
        assert doc.paragraphs[0].runs[0].italic is True

    @pytest.mark.unit
    def test_preserves_underline_formatting(self, tmp_path):
        """Underline formatting preserved after replacement."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('Underlined text')
        run.underline = True

        doc_path = tmp_path / "underline.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('text', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'content')

        assert count == 1
        assert any(run.underline for run in doc.paragraphs[0].runs)

    @pytest.mark.unit
    def test_multiple_occurrences_same_paragraph(self, tmp_path):
        """Multiple occurrences in same paragraph all replaced."""
        doc = Document()
        doc.add_paragraph('test test test')

        doc_path = tmp_path / "multi.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'REPLACED')

        assert count == 3
        assert doc.paragraphs[0].text == 'REPLACED REPLACED REPLACED'

    @pytest.mark.unit
    def test_case_insensitive_preserves_formatting(self, tmp_path):
        """Case-insensitive replacement preserves formatting on both matches."""
        doc = Document()
        p = doc.add_paragraph()
        run1 = p.add_run('Test')
        run1.bold = True
        p.add_run(' and ')
        run2 = p.add_run('test')
        run2.italic = True

        doc_path = tmp_path / "case.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'REPLACED')

        assert count == 2
        assert doc.paragraphs[0].runs[0].bold is True
        assert doc.paragraphs[0].runs[2].italic is True

    @pytest.mark.unit
    def test_regex_replacement_preserves_formatting(self, tmp_path):
        """Regex replacement preserves formatting."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('Call 555-1234 or 555-5678')
        run.bold = True

        doc_path = tmp_path / "regex.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern(r'\d{3}-\d{4}', use_regex=True, case_sensitive=False, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'XXX-XXXX')

        assert count == 2
        assert 'XXX-XXXX' in doc.paragraphs[0].text
        assert doc.paragraphs[0].runs[0].bold is True

    @pytest.mark.unit
    def test_unicode_replacement(self, tmp_path):
        """Unicode text replacement preserves characters."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('测试 test 测试')
        run.bold = True

        doc_path = tmp_path / "unicode.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('测试', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, '替换')

        assert count == 2
        assert '替换 test 替换' == doc.paragraphs[0].text

    @pytest.mark.unit
    def test_whole_word_replacement_with_formatting(self, tmp_path):
        """Whole word replacement preserves formatting."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('test testing tested')
        run.underline = True

        doc_path = tmp_path / "whole.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=True)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'REPLACED')

        assert count == 1  # Only 'test', not 'testing' or 'tested'
        assert 'REPLACED' in doc.paragraphs[0].text
        assert doc.paragraphs[0].runs[0].underline is True

    @pytest.mark.unit
    def test_no_replacement_returns_zero(self, tmp_path):
        """No match returns zero count."""
        doc = Document()
        doc.add_paragraph('This is a test')

        doc_path = tmp_path / "nomatch.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('notfound', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'REPLACED')

        assert count == 0
        assert doc.paragraphs[0].text == 'This is a test'

    @pytest.mark.unit
    def test_replace_emoji(self, tmp_path):
        """Replacing text with emoji preserves formatting."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('Hello World')
        run.italic = True

        doc_path = tmp_path / "emoji.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('World', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, '😀')

        assert count == 1
        assert 'Hello 😀' == doc.paragraphs[0].text
        assert doc.paragraphs[0].runs[0].italic is True

    @pytest.mark.unit
    def test_replace_partial_run_text(self, tmp_path):
        """Replacing part of a run's text."""
        doc = Document()
        p = doc.add_paragraph()
        run = p.add_run('abcdefgh')
        run.bold = True

        doc_path = tmp_path / "partial.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('cde', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'XYZ')

        assert count == 1
        assert doc.paragraphs[0].text == 'abXYZfgh'
        assert doc.paragraphs[0].runs[0].bold is True

    @pytest.mark.unit
    def test_replace_across_multiple_runs(self, tmp_path):
        """Replacement when text spans multiple runs."""
        doc = Document()
        p = doc.add_paragraph()
        p.add_run('Hello ')
        p.add_run('World')

        doc_path = tmp_path / "multirun.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        # The pattern looks at paragraph.text which joins all runs
        pattern = _compile_pattern('Hello World', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(doc.paragraphs[0], pattern, 'Goodbye Earth')

        # Should find and replace the text
        assert count == 1

    @pytest.mark.unit
    def test_empty_run_handling(self, docx_factory):
        """Replacing in paragraphs with empty runs."""
        doc_path = docx_factory(content="Test paragraph")
        doc = Document(str(doc_path))
        para = doc.paragraphs[0]

        # Add a run with empty text
        para.add_run("")

        pattern = _compile_pattern('Test', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_paragraph(para, pattern, 'Sample')

        assert count == 1
        assert 'Sample' in para.text


# ============================================================================
# Table Replacement Tests
# ============================================================================

class TestTableReplacement:
    """Tests for _replace_in_table function."""

    @pytest.mark.unit
    def test_replace_in_table_basic(self, docx_with_table):
        """Basic text replacement in table cells."""
        doc_path = docx_with_table(rows=2, cols=2)
        doc = Document(str(doc_path))
        table = doc.tables[0]

        pattern = _compile_pattern('Header', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_table(table, pattern, 'TITLE')

        assert count == 2
        assert table.cell(0, 0).text == 'TITLE 1'
        assert table.cell(0, 1).text == 'TITLE 2'

    @pytest.mark.unit
    def test_replace_in_all_cells(self, tmp_path):
        """Replacement across all table cells."""
        doc = Document()
        table = doc.add_table(rows=3, cols=3)
        for row in table.rows:
            for cell in row.cells:
                cell.text = 'test'

        doc_path = tmp_path / "allcells.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'REPLACED')

        assert count == 9

    @pytest.mark.unit
    def test_replace_preserves_cell_formatting(self, tmp_path):
        """Table replacement preserves cell formatting."""
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.cell(0, 0)
        run = cell.paragraphs[0].add_run('Bold Text')
        run.bold = True

        doc_path = tmp_path / "formatted.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('Bold', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'STRONG')

        assert count == 1
        assert 'STRONG' in doc.tables[0].cell(0, 0).text
        assert doc.tables[0].cell(0, 0).paragraphs[0].runs[0].bold is True

    @pytest.mark.unit
    def test_multiple_paragraphs_per_cell(self, tmp_path):
        """Replacement in cells with multiple paragraphs."""
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.cell(0, 0)
        cell.paragraphs[0].text = 'First test'
        cell.add_paragraph('Second test')
        cell.add_paragraph('Third test')

        doc_path = tmp_path / "multipara.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'REPLACED')

        assert count == 3

    @pytest.mark.unit
    def test_no_match_in_table(self, docx_with_table):
        """Table replacement when no matches found."""
        doc_path = docx_with_table(rows=2, cols=2)
        doc = Document(str(doc_path))

        pattern = _compile_pattern('notfound', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'REPLACED')

        assert count == 0

    @pytest.mark.unit
    def test_empty_table(self, tmp_path):
        """Replacement in empty table."""
        doc = Document()
        doc.add_table(rows=2, cols=2)

        doc_path = tmp_path / "empty.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'REPLACED')

        assert count == 0

    @pytest.mark.unit
    def test_unicode_in_table(self, tmp_path):
        """Unicode replacement in table cells."""
        doc = Document()
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = '测试 1'
        table.cell(1, 0).text = '测试 2'

        doc_path = tmp_path / "unicode_table.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('测试', use_regex=False, case_sensitive=True, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, '替换')

        assert count == 2
        assert '替换' in doc.tables[0].cell(0, 0).text

    @pytest.mark.unit
    def test_nested_table_handling(self, tmp_path):
        """Test that table replacement handles gracefully."""
        doc = Document()
        outer_table = doc.add_table(rows=1, cols=1)
        outer_table.cell(0, 0).text = 'test outer'

        doc_path = tmp_path / "nested.docx"
        doc.save(str(doc_path))
        doc = Document(str(doc_path))

        pattern = _compile_pattern('test', use_regex=False, case_sensitive=False, whole_words=False)
        count = _replace_in_table(doc.tables[0], pattern, 'REPLACED')

        assert count == 1
