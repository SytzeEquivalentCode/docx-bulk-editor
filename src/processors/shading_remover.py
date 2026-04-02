"""Shading remover processor for DOCX documents.

Makes all shading white (FFFFFF) across all document areas:
- Body paragraphs and runs
- Tables (cell-level and table-level)
- Text boxes (DrawingML and VML)
- Headers and footers
- Footnotes and endnotes
"""

import time
from typing import Dict, Any, List

from lxml import etree
from docx import Document
from docx.oxml.ns import qn

from src.processors import ProcessorResult


# Namespace map for XPath queries — includes namespaces missing from python-docx
NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'v': 'urn:schemas-microsoft-com:vml',
}

# Theme attributes that override explicit fill colors
_THEME_ATTRS = [
    'w:themeFill', 'w:themeFillTint', 'w:themeFillShade',
    'w:themeColor', 'w:themeTint', 'w:themeShade',
]


def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    """Top-level function for multiprocessing (must be module-level).

    Args:
        file_path: Path to the DOCX file to process
        config: Configuration dictionary with shading removal options

    Returns:
        ProcessorResult with success status and shading elements modified count
    """
    start_time = time.time()

    try:
        doc = Document(file_path)
        changes = perform_shading_removal(doc, config)

        if changes > 0:
            doc.save(file_path)

        duration = time.time() - start_time
        return ProcessorResult(
            success=True,
            file_path=file_path,
            changes_made=changes,
            duration_seconds=duration
        )
    except Exception as e:
        duration = time.time() - start_time
        return ProcessorResult(
            success=False,
            file_path=file_path,
            changes_made=0,
            error_message=str(e),
            duration_seconds=duration
        )


def perform_shading_removal(doc: Document, config: Dict[str, Any]) -> int:
    """Make all shading white across the document.

    Args:
        doc: python-docx Document object
        config: Configuration dictionary containing:
            - process_body: Process body text, tables, and text boxes
            - process_tables: Process tables (only if body is disabled)
            - process_textboxes: Process text boxes (only if body is disabled)
            - process_headers_footers: Process headers and footers

    Returns:
        Number of shading elements modified
    """
    process_body = config.get('process_body', True)
    process_tables = config.get('process_tables', True)
    process_textboxes = config.get('process_textboxes', True)
    process_headers_footers = config.get('process_headers_footers', True)

    changes = 0

    # Body XPath covers paragraphs, runs, tables, AND text boxes (all nested in body)
    if process_body:
        changes += _process_shd_elements(_find_shd_elements(doc.element.body))
        changes += _process_footnotes_endnotes(doc)
    else:
        # Process tables individually if body wasn't processed
        if process_tables:
            for table in doc.tables:
                changes += _process_shd_elements(_find_shd_elements(table._tbl))

        # Process text boxes individually if body wasn't processed
        if process_textboxes:
            for txbx in _find_textbox_contents(doc.element.body):
                changes += _process_shd_elements(_find_shd_elements(txbx))

    if process_headers_footers:
        changes += _process_headers_footers(doc)

    return changes


def _process_headers_footers(doc: Document) -> int:
    """Process shading in all non-linked headers and footers."""
    changes = 0

    for section in doc.sections:
        for hf_attr in [
            'header', 'first_page_header', 'even_page_header',
            'footer', 'first_page_footer', 'even_page_footer',
        ]:
            try:
                hf = getattr(section, hf_attr)
                if hf.is_linked_to_previous:
                    continue
                changes += _process_shd_elements(_find_shd_elements(hf._element))
            except (AttributeError, KeyError):
                continue

    return changes


def _process_footnotes_endnotes(doc: Document) -> int:
    """Process shading in footnotes and endnotes via OPC parts."""
    changes = 0

    for rel in doc.part.rels.values():
        reltype = rel.reltype or ''
        if 'footnotes' in reltype or 'endnotes' in reltype:
            try:
                changes += _process_shd_elements(
                    _find_shd_elements(rel.target_part.element)
                )
            except Exception:
                continue

    return changes


def _find_shd_elements(element) -> List:
    """Find all w:shd elements under the given XML element.

    Uses lxml's ElementBase.xpath() directly to bypass python-docx's
    wrapper which doesn't accept custom namespaces.
    """
    return etree.ElementBase.xpath(element, './/w:shd', namespaces=NSMAP)


def _find_textbox_contents(element) -> List:
    """Find all w:txbxContent elements (DrawingML + VML) under the given element."""
    return etree.ElementBase.xpath(element, './/w:txbxContent', namespaces=NSMAP)


def _process_shd_elements(shd_elements: List) -> int:
    """Make a list of w:shd elements white. Returns count of modified elements."""
    changes = 0
    for shd in shd_elements:
        if _make_shd_white(shd):
            changes += 1
    return changes


def _make_shd_white(shd) -> bool:
    """Set a single w:shd element to white, stripping theme overrides.

    Returns True if the element was modified, False if already white.
    """
    fill = (shd.get(qn('w:fill')) or '').upper()
    val = shd.get(qn('w:val')) or ''
    has_theme = any(qn(attr) in shd.attrib for attr in _THEME_ATTRS)

    # Skip if already white with no theme overrides
    if fill == 'FFFFFF' and val == 'clear' and not has_theme:
        return False

    # Set to white
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'FFFFFF')

    # Strip theme attributes that override explicit fill
    for attr in _THEME_ATTRS:
        key = qn(attr)
        if key in shd.attrib:
            del shd.attrib[key]

    return True
