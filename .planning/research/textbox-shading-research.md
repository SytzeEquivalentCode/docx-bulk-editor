# Text Box Access and Shading Modification in python-docx

**Researched:** 2026-03-31
**Domain:** OOXML text box structures, python-docx lxml internals, shading manipulation
**Confidence:** HIGH (all code examples validated end-to-end on this project's environment)

## Summary

python-docx has **no built-in API** for accessing text box content. This is a known, long-standing limitation (GitHub issue #413, still open). Text boxes are stored as `w:txbxContent` elements inside either VML (`v:textbox`) or DrawingML (`wps:txbx`) structures, and modern Word documents typically include **both representations** wrapped in `mc:AlternateContent`.

The workaround is to use **lxml xpath directly** on python-docx element objects, bypassing python-docx's `BaseOxmlElement.xpath()` method (which only supports built-in namespaces) and instead calling `lxml.etree.ElementBase.xpath()` with a custom namespace map that includes `mc`, `wps`, `v`, and other missing prefixes.

**Primary recommendation:** Use `etree.ElementBase.xpath(element, './/w:txbxContent', namespaces=TEXTBOX_NSMAP)` to find all text box content elements across all document parts (body, headers, footers), then manipulate `w:shd` elements within them using the same `qn()` and `OxmlElement` patterns already used in this project's `table_formatter.py`.

## Text Box Representation in OOXML

### Two Formats, One Wrapper

Modern Word (2010+) produces text boxes using **both** DrawingML (new) and VML (legacy) inside an `mc:AlternateContent` wrapper:

```xml
<mc:AlternateContent>
  <!-- Modern apps use this (DrawingML) -->
  <mc:Choice Requires="wps">
    <w:drawing>
      <wp:anchor ...>
        <a:graphic>
          <a:graphicData uri="...">
            <wps:wsp>
              <wps:txbx>
                <w:txbxContent>
                  <w:p>
                    <w:pPr><w:shd w:val="clear" w:fill="FFFF00"/></w:pPr>
                    <w:r><w:t>Text here</w:t></w:r>
                  </w:p>
                </w:txbxContent>
              </wps:txbx>
            </wps:wsp>
          </a:graphicData>
        </a:graphic>
      </wp:anchor>
    </w:drawing>
  </mc:Choice>

  <!-- Older apps fall back to this (VML) -->
  <mc:Fallback>
    <w:pict>
      <v:shape type="#_x0000_t202">
        <v:textbox>
          <w:txbxContent>
            <w:p>
              <w:pPr><w:shd w:val="clear" w:fill="FFFF00"/></w:pPr>
              <w:r><w:t>Text here</w:t></w:r>
            </w:p>
          </w:txbxContent>
        </v:textbox>
      </v:shape>
    </w:pict>
  </mc:Fallback>
</mc:AlternateContent>
```

**Critical insight:** The text content appears **twice** -- once in `mc:Choice` (DrawingML) and once in `mc:Fallback` (VML). When modifying shading, **both copies must be updated** to keep the document consistent regardless of which rendering path a viewer uses.

### Older Documents (Pre-2010)

Some older documents have standalone VML without the `mc:AlternateContent` wrapper:

```xml
<w:pict>
  <v:shape type="#_x0000_t202">
    <v:textbox>
      <w:txbxContent>
        <!-- paragraphs here -->
      </w:txbxContent>
    </v:textbox>
  </v:shape>
</w:pict>
```

### Universal Finder

The XPath `.//w:txbxContent` finds **all** text box content elements regardless of whether they are in DrawingML, VML, mc:AlternateContent, or standalone structures. This is the recommended approach.

## Required Namespaces

python-docx's built-in `nsmap` is **missing** several namespaces needed for text box access. These must be provided manually:

```python
# Namespaces already in python-docx nsmap:
#   w, a, wp, r, w14

# Namespaces MISSING from python-docx nsmap (must define ourselves):
TEXTBOX_NSMAP = {
    # From python-docx (include for completeness in xpath calls)
    'w':   'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a':   'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':  'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',

    # NOT in python-docx -- required for text box access
    'mc':  'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'v':   'urn:schemas-microsoft-com:vml',
    'o':   'urn:schemas-microsoft-com:office:office',
}
```

**Verified:** These URIs are correct per the OOXML specification and work with lxml xpath on python-docx element objects.

## Accessing Text Boxes via lxml xpath

### The python-docx xpath Problem

python-docx overrides lxml's `xpath()` method on its `BaseOxmlElement` class. This override auto-injects its own namespace map but **does not accept a `namespaces` keyword argument**. Calling `element.xpath('.//mc:AlternateContent', namespaces=TEXTBOX_NSMAP)` raises `TypeError`.

### The Solution: Call lxml's xpath Directly

python-docx elements inherit from `lxml.etree.ElementBase`. Call the **base class** xpath method:

```python
import lxml.etree as etree

def xpath_with_ns(element, query, nsmap=TEXTBOX_NSMAP):
    """Run XPath with custom namespaces on a python-docx element.

    python-docx's BaseOxmlElement.xpath() only supports built-in namespaces.
    This bypasses it to call lxml's xpath directly.
    """
    return etree.ElementBase.xpath(element, query, namespaces=nsmap)
```

**Verified:** This approach works. The MRO is: `CT_Body -> BaseOxmlElement -> ElementBase -> _Element -> object`. Calling `ElementBase.xpath` with `namespaces=` works correctly.

## Working Code: Find All Text Boxes in a Document

```python
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import lxml.etree as etree


TEXTBOX_NSMAP = {
    'w':   'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a':   'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':  'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'mc':  'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'v':   'urn:schemas-microsoft-com:vml',
    'o':   'urn:schemas-microsoft-com:office:office',
}

# XPath queries
XPATH_ALL_TXBX = './/w:txbxContent'                                    # Universal
XPATH_DRAWINGML = './/mc:Choice//wps:txbx/w:txbxContent'               # DrawingML only
XPATH_VML_FALLBACK = './/mc:Fallback//v:textbox/w:txbxContent'          # VML fallback
XPATH_VML_STANDALONE = './/w:pict//v:textbox/w:txbxContent'             # Standalone VML


def _xpath(element, query):
    """Run XPath with text-box namespaces on a python-docx element."""
    return etree.ElementBase.xpath(element, query, namespaces=TEXTBOX_NSMAP)


def get_all_document_roots(doc):
    """Yield (name, xml_element) for every part that can contain text boxes.

    Text boxes can appear in:
    - Document body
    - Section headers (default, first-page, even-page)
    - Section footers (default, first-page, even-page)
    """
    yield ('body', doc.element.body)

    for i, section in enumerate(doc.sections):
        for hf_attr in [
            'header', 'first_page_header', 'even_page_header',
            'footer', 'first_page_footer', 'even_page_footer',
        ]:
            try:
                hf = getattr(section, hf_attr)
                if hf is not None:
                    yield (f'section[{i}].{hf_attr}', hf._element)
            except (AttributeError, KeyError):
                pass


def find_all_textbox_content(doc):
    """Find all w:txbxContent elements across all document parts.

    Returns list of (part_name, txbxContent_element) tuples.
    """
    results = []
    for part_name, root in get_all_document_roots(doc):
        for txbx in _xpath(root, XPATH_ALL_TXBX):
            results.append((part_name, txbx))
    return results
```

## Working Code: Modify Shading Inside Text Boxes

### Find and Remove All Shading

```python
def find_shading_in_textboxes(doc):
    """Find all w:shd elements inside text boxes across the entire document.

    Returns list of (part_name, shd_element, context) tuples where context
    is 'paragraph' or 'run'.
    """
    results = []
    for part_name, txbx in find_all_textbox_content(doc):
        # Paragraph-level shading: w:p/w:pPr/w:shd
        for shd in _xpath(txbx, './/w:pPr/w:shd'):
            results.append((part_name, shd, 'paragraph'))

        # Run-level shading: w:r/w:rPr/w:shd
        for shd in _xpath(txbx, './/w:rPr/w:shd'):
            results.append((part_name, shd, 'run'))

    return results


def remove_shading_from_textboxes(doc):
    """Remove all shading (w:shd) from text boxes throughout the document.

    Handles both paragraph-level and run-level shading.
    Returns count of shading elements removed.
    """
    count = 0
    for part_name, shd, context in find_shading_in_textboxes(doc):
        parent = shd.getparent()
        parent.remove(shd)
        count += 1
    return count


def clear_shading_fill_in_textboxes(doc):
    """Set all text box shading fills to 'auto' (transparent).

    Unlike remove_shading_from_textboxes, this preserves the w:shd element
    but neutralizes the visible fill color. This is safer if the shd element
    carries other attributes (e.g., w:val pattern) that should be preserved.

    Returns count of shading elements cleared.
    """
    count = 0
    for part_name, shd, context in find_shading_in_textboxes(doc):
        fill = shd.get(qn('w:fill'))
        if fill and fill.upper() != 'AUTO':
            shd.set(qn('w:fill'), 'auto')
            count += 1
    return count
```

### Modify Specific Shading Colors

```python
def replace_shading_color_in_textboxes(doc, old_color_hex, new_color_hex):
    """Replace a specific shading color in text boxes.

    Args:
        doc: python-docx Document object
        old_color_hex: Color to find (e.g., 'FFFF00' for yellow), case-insensitive
        new_color_hex: Replacement color (e.g., 'FFFFFF' for white, or 'auto' for none)

    Returns count of shading elements modified.
    """
    old_upper = old_color_hex.upper()
    count = 0
    for part_name, shd, context in find_shading_in_textboxes(doc):
        fill = shd.get(qn('w:fill'))
        if fill and fill.upper() == old_upper:
            shd.set(qn('w:fill'), new_color_hex)
            count += 1
    return count
```

## Integration with Existing Processor Pattern

This project's processors (e.g., `table_formatter.py`) already use `qn()` and `OxmlElement` from `docx.oxml`. The text box code fits naturally:

```python
# In a processor function (module-level for multiprocessing compatibility):

def process_textbox_shading(doc, config):
    """Remove or modify shading in text boxes."""
    action = config.get('textbox_shading_action', 'remove')  # 'remove', 'clear', 'replace'
    changes = 0

    if action == 'remove':
        changes = remove_shading_from_textboxes(doc)
    elif action == 'clear':
        changes = clear_shading_fill_in_textboxes(doc)
    elif action == 'replace':
        old_color = config.get('old_color', 'FFFF00')
        new_color = config.get('new_color', 'auto')
        changes = replace_shading_color_in_textboxes(doc, old_color, new_color)

    return changes
```

## Document Parts That Can Contain Text Boxes

Text boxes can appear in any of these document parts. All must be searched:

| Part | Access Path | Element Type |
|------|-------------|--------------|
| Document body | `doc.element.body` | `CT_Body` |
| Default header | `section.header._element` | `CT_HdrFtr` |
| First-page header | `section.first_page_header._element` | `CT_HdrFtr` |
| Even-page header | `section.even_page_header._element` | `CT_HdrFtr` |
| Default footer | `section.footer._element` | `CT_HdrFtr` |
| First-page footer | `section.first_page_footer._element` | `CT_HdrFtr` |
| Even-page footer | `section.even_page_footer._element` | `CT_HdrFtr` |

**Note:** Accessing a header/footer that doesn't exist in the document will cause python-docx to **create** one. This is generally harmless (it creates an empty header/footer), but if you want to avoid side effects, check `section.header.is_linked_to_previous` before accessing the element. However, for a bulk shading removal tool, creating empty headers is acceptable.

## Shading Element Structure

### Paragraph-Level Shading

```xml
<w:p>
  <w:pPr>
    <w:shd w:val="clear" w:color="auto" w:fill="FFFF00"/>
  </w:pPr>
  <w:r>...</w:r>
</w:p>
```

XPath from txbxContent: `.//w:pPr/w:shd`

### Run-Level Shading

```xml
<w:r>
  <w:rPr>
    <w:shd w:val="clear" w:color="auto" w:fill="00FF00"/>
  </w:rPr>
  <w:t>highlighted text</w:t>
</w:r>
```

XPath from txbxContent: `.//w:rPr/w:shd`

### w:shd Attributes

| Attribute | Meaning | Common Values |
|-----------|---------|---------------|
| `w:val` | Shading pattern | `clear` (solid fill), `pct10`, `pct25`, etc. |
| `w:color` | Pattern foreground color | `auto`, hex like `000000` |
| `w:fill` | Background fill color | `auto` (none), hex like `FFFF00` |
| `w:themeFill` | Theme-based fill | `accent1`, `background1`, etc. |
| `w:themeFillTint` | Tint of theme fill | Hex like `66` |
| `w:themeFillShade` | Shade of theme fill | Hex like `BF` |

**To remove visible shading:** Either remove the `w:shd` element entirely, or set `w:fill="auto"`. Both work. Removing the element is cleaner; setting to `auto` is safer if other attributes matter.

**To handle theme-based shading:** Also clear `w:themeFill`, `w:themeFillTint`, and `w:themeFillShade` attributes:

```python
def clear_shading_completely(shd_element):
    """Remove all fill-related attributes from a w:shd element."""
    for attr in ['w:fill', 'w:themeFill', 'w:themeFillTint', 'w:themeFillShade']:
        clark = qn(attr)
        if clark in shd_element.attrib:
            del shd_element.attrib[clark]
    # Set fill to auto to ensure no visible color
    shd_element.set(qn('w:fill'), 'auto')
```

## Common Pitfalls

### 1. Forgetting the Dual-Copy Problem

**What goes wrong:** Modifying shading in DrawingML text boxes but not VML fallback (or vice versa). Document looks correct in modern Word but wrong in older viewers, or the unmodified copy overwrites changes on re-save.

**How to avoid:** Use the universal XPath `.//w:txbxContent` which finds **all** copies. Process every result. Do not filter by DrawingML vs VML.

### 2. Using python-docx's xpath() Instead of lxml's

**What goes wrong:** `element.xpath('.//mc:AlternateContent', namespaces={...})` raises `TypeError: BaseOxmlElement.xpath() got an unexpected keyword argument 'namespaces'`.

**How to avoid:** Always use `etree.ElementBase.xpath(element, query, namespaces=TEXTBOX_NSMAP)`.

### 3. Forgetting Headers and Footers

**What goes wrong:** Text boxes in headers/footers are missed. Users report "it didn't remove all the shading."

**How to avoid:** Always iterate all document parts using `get_all_document_roots(doc)`.

### 4. Creating Empty Headers by Accessing Them

**What goes wrong:** Accessing `section.header` on a section without a header creates an empty one, adding XML to the document that wasn't there before.

**Acceptable trade-off:** For a bulk editor that modifies documents anyway, this is harmless. If purity is needed, check the section's XML for existing header references before accessing.

### 5. Theme-Based Shading Not Cleared

**What goes wrong:** Setting `w:fill="auto"` but leaving `w:themeFill` -- Word ignores `w:fill` and uses the theme color instead.

**How to avoid:** Use `clear_shading_completely()` to remove all fill-related attributes.

## Alternative: Using iter() with Clark Notation

For simpler cases where you just need to find `w:txbxContent` elements without complex XPath:

```python
# Clark notation (no namespace map needed)
CLARK_TXBX = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}txbxContent'
CLARK_SHD = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd'

# iter() walks the entire element tree
for txbx in doc.element.body.iter(CLARK_TXBX):
    for shd in txbx.iter(CLARK_SHD):
        # Process shading
        pass
```

**Trade-off:** `iter()` is simpler but cannot distinguish paragraph-level vs run-level shading. Use XPath when you need context-aware queries.

## Sources

### Primary (HIGH confidence -- verified with working code)
- python-docx namespace module source (`docx/oxml/ns.py`) -- inspected directly
- python-docx element hierarchy verified: CT_Body -> BaseOxmlElement -> ElementBase -> _Element
- All code examples in this document were executed and validated on this project's Python environment

### Secondary (MEDIUM-HIGH confidence)
- [Rik Voorhaar: How to edit Microsoft Word documents in Python](https://www.rikvoorhaar.com/blog/python_docx) -- TextBox class pattern, XPath queries, dual-copy insight
- [python-docx GitHub Issue #413](https://github.com/python-openxml/python-docx/issues/413) -- Confirms no built-in API for text boxes
- [OOXML txbxContent reference](https://c-rex.net/projects/samples/ooxml/e1/Part4/OOXML_P4_DOCX_txbxContent_topic_ID0EB421.html) -- Element specification
- [OOXML v:textbox reference](https://www.datypic.com/sc/ooxml/e-v_textbox.html) -- VML text box specification
- [Office Open XML DrawingML Shapes](http://officeopenxml.com/drwShape.php) -- DrawingML structure
- [OOXML Markup Compatibility](https://wiki.openoffice.org/wiki/OOXML/Markup_Compatibility_and_Extensibility) -- mc:AlternateContent structure
- [python-docx Section API docs](https://python-docx.readthedocs.io/en/latest/api/section.html) -- Header/footer access
- [python-docx Working with Headers and Footers](https://python-docx.readthedocs.io/en/latest/user/hdrftr.html)
