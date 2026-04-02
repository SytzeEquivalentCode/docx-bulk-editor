# DOCX Shading Research

**Researched:** 2026-03-31
**Domain:** OOXML shading manipulation via python-docx + lxml
**python-docx version:** 1.2.0
**Confidence:** HIGH (verified against OOXML spec + python-docx source code)

## Summary

Shading in DOCX files is controlled by the `w:shd` XML element, which can appear in five locations: paragraph properties (`w:pPr`), run properties (`w:rPr`), table cell properties (`w:tcPr`), table properties (`w:tblPr`), and table row exception properties. Additionally, these same shading elements appear inside text boxes, headers/footers, footnotes/endnotes, and comments -- all of which are separate document parts or embedded content containers.

python-docx 1.2.0 has **no native shading API**. The library recognizes `w:shd` in its XML element ordering (tag sequences) for paragraph, run, table, and table cell properties, but exposes no Python properties or methods to read/write shading. All shading manipulation requires direct XML access via `lxml` and the `OxmlElement`/`qn` helpers from `docx.oxml`.

**Primary recommendation:** Build a shading processor that uses XPath queries to find ALL `w:shd` elements across the document body, headers/footers, text boxes, footnotes/endnotes, and comments. Use `OxmlElement` and `qn` from `docx.oxml` for XML manipulation -- the same pattern already used in `src/processors/table_formatter.py`.

---

## 1. The `w:shd` Element -- OOXML Specification

### Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `w:val` | ST_Shd | **Yes** | Pattern type (e.g., `clear`, `solid`, `nil`, `pct10`) |
| `w:color` | ST_HexColor | No | Foreground pattern color (6-digit hex `RRGGBB` or `auto`) |
| `w:fill` | ST_HexColor | No | Background fill color (6-digit hex `RRGGBB` or `auto`) |
| `w:themeColor` | ST_ThemeColor | No | Theme color for foreground pattern |
| `w:themeFill` | ST_ThemeColor | No | Theme color for background fill |
| `w:themeTint` | ST_UcharHexNumber | No | Tint modifier for themeColor (00-FF) |
| `w:themeShade` | ST_UcharHexNumber | No | Shade modifier for themeColor (00-FF) |
| `w:themeFillTint` | ST_UcharHexNumber | No | Tint modifier for themeFill (00-FF) |
| `w:themeFillShade` | ST_UcharHexNumber | No | Shade modifier for themeFill (00-FF) |

### How Shading Works

The shading is a two-layer system:
1. **Background layer:** Solid fill color specified by `w:fill` (or `w:themeFill`)
2. **Pattern layer:** A mask pattern (`w:val`) filled with the foreground color (`w:color` or `w:themeColor`), applied over the background

For a simple solid background color (the most common case): `w:val="clear"`, `w:color="auto"`, `w:fill="RRGGBB"`.

### ST_Shd Pattern Values (Complete List)

| Value | Description |
|-------|-------------|
| `nil` | No shading |
| `clear` | No pattern (shows background fill only) |
| `solid` | 100% foreground fill |
| `horzStripe` | Horizontal stripes |
| `vertStripe` | Vertical stripes |
| `reverseDiagStripe` | Reverse diagonal stripes |
| `diagStripe` | Diagonal stripes |
| `horzCross` | Horizontal cross-hatch |
| `diagCross` | Diagonal cross-hatch |
| `thinHorzStripe` | Thin horizontal stripes |
| `thinVertStripe` | Thin vertical stripes |
| `thinReverseDiagStripe` | Thin reverse diagonal stripes |
| `thinDiagStripe` | Thin diagonal stripes |
| `thinHorzCross` | Thin horizontal cross-hatch |
| `thinDiagCross` | Thin diagonal cross-hatch |
| `pct5` through `pct95` | Percentage fill (5, 10, 12, 15, 20, 25, 30, 35, 37, 40, 45, 50, 55, 60, 62, 65, 70, 75, 80, 85, 87, 90, 95) |

### Shading Precedence (Table Context)

Table-level shading < Row exception shading < Cell-level shading. Cell shading always wins.

---

## 2. All Locations Where `w:shd` Appears

### 2.1 Paragraph Shading (`w:pPr/w:shd`)

Applies background color to the entire paragraph rectangle.

```xml
<w:p>
  <w:pPr>
    <w:shd w:val="clear" w:color="auto" w:fill="FFFF00"/>
  </w:pPr>
  <w:r>
    <w:t>Yellow background paragraph</w:t>
  </w:r>
</w:p>
```

**python-docx access:**
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

paragraph = doc.paragraphs[0]
pPr = paragraph._p.get_or_add_pPr()
shd = pPr.find(qn('w:shd'))  # Read existing
```

### 2.2 Run/Character Shading (`w:rPr/w:shd`)

Applies background color behind individual runs of text. Visually similar to highlighting but technically different -- highlighting uses `w:highlight` (limited color palette), shading uses `w:shd` (any RGB color).

```xml
<w:r>
  <w:rPr>
    <w:shd w:val="clear" w:color="auto" w:fill="00FF00"/>
  </w:rPr>
  <w:t>Green shaded text</w:t>
</w:r>
```

**python-docx access:**
```python
run = paragraph.runs[0]
rPr = run._r.get_or_add_rPr()
shd = rPr.find(qn('w:shd'))  # Read existing
```

**Note:** python-docx DOES have `run.font.highlight_color` for `w:highlight`, but `w:shd` on runs is separate and requires XML manipulation.

### 2.3 Table Cell Shading (`w:tcPr/w:shd`)

The most common shading location. Sets background color for individual cells.

```xml
<w:tc>
  <w:tcPr>
    <w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>
  </w:tcPr>
  <w:p>
    <w:r><w:t>Gray cell</w:t></w:r>
  </w:p>
</w:tc>
```

**python-docx access (already used in project):**
```python
cell = table.cell(0, 0)
tc = cell._tc
tcPr = tc.get_or_add_tcPr()
shd = tcPr.find(qn('w:shd'))
```

### 2.4 Table-Level Shading (`w:tblPr/w:shd`)

Applies default shading to ALL cells in the table. Overridden by cell-level shading.

```xml
<w:tbl>
  <w:tblPr>
    <w:shd w:val="clear" w:color="auto" w:fill="F0F0F0"/>
  </w:tblPr>
  ...
</w:tbl>
```

**python-docx access:**
```python
table = doc.tables[0]
tblPr = table._tbl.tblPr
if tblPr is not None:
    shd = tblPr.find(qn('w:shd'))
```

### 2.5 Table Row Exception Shading

Row-level shading can appear in conditional formatting contexts (table style exceptions). In practice this is rare -- most row shading is achieved by setting cell-level shading on every cell in the row. The `w:trPr` element does NOT directly contain `w:shd`. Row-level shading effects come from table style conditional formatting (`w:tblStylePr`), not direct `w:trPr/w:shd`.

---

## 3. Content Containers Beyond the Document Body

### 3.1 Headers and Footers

Each section can have up to 6 header/footer definitions (default/even/first for both header and footer). python-docx 1.2.0 provides full API access.

**Access pattern:**
```python
for section in doc.sections:
    # Default header/footer
    header = section.header
    footer = section.footer
    
    # Process paragraphs and tables in header/footer
    for para in header.paragraphs:
        pPr = para._p.get_or_add_pPr()
        shd = pPr.find(qn('w:shd'))
        # ... process shading
    
    for table in header.tables:
        for row in table.rows:
            for cell in row.cells:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = tcPr.find(qn('w:shd'))
                # ... process shading
    
    # Also check even-page and first-page headers/footers
    if section.different_first_page_header_footer:
        first_header = section.first_page_header
        first_footer = section.first_page_footer
        # ... process these too
    
    even_header = section.even_page_header
    even_footer = section.even_page_footer
    # ... process these too
```

**Caveat:** Accessing a header/footer that doesn't exist will CREATE one. Check `header.is_linked_to_previous` before accessing content -- if `True`, this section inherits from the previous section's header and you should skip it to avoid duplication.

### 3.2 Text Boxes

Text boxes in DOCX are stored as either:
- **Modern (DrawingML):** `mc:AlternateContent/mc:Choice/w:drawing/wp:anchor/.../wps:txbx/w:txbxContent`
- **Legacy (VML):** `w:pict/v:shape/v:textbox/w:txbxContent` (also in `mc:Fallback`)

python-docx has NO text box API. Access requires direct lxml XPath.

**Namespace URIs needed (not all in python-docx's nsmap):**
```python
TEXTBOX_NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'v': 'urn:schemas-microsoft-com:vml',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}
```

**XPath to find all `w:txbxContent` elements:**
```python
from lxml import etree

body = doc.element.body

# Find all txbxContent elements (modern + legacy)
txbx_contents = body.xpath(
    './/wps:txbx/w:txbxContent | .//v:textbox/w:txbxContent',
    namespaces=TEXTBOX_NSMAP
)

# Each txbxContent contains paragraphs and tables, just like the document body
for txbx in txbx_contents:
    # Find all shd elements inside this text box
    shd_elements = txbx.xpath('.//w:shd', namespaces=TEXTBOX_NSMAP)
    for shd in shd_elements:
        # Process shading...
        pass
    
    # Or find specific locations:
    # Paragraph shading
    para_shds = txbx.xpath('.//w:pPr/w:shd', namespaces=TEXTBOX_NSMAP)
    # Run shading
    run_shds = txbx.xpath('.//w:rPr/w:shd', namespaces=TEXTBOX_NSMAP)
    # Cell shading
    cell_shds = txbx.xpath('.//w:tcPr/w:shd', namespaces=TEXTBOX_NSMAP)
```

**Important:** Text boxes can also exist inside headers/footers. To be thorough, search for `w:txbxContent` in header/footer XML too:
```python
for section in doc.sections:
    header_elem = section.header._element
    txbx_in_header = header_elem.xpath(
        './/wps:txbx/w:txbxContent | .//v:textbox/w:txbxContent',
        namespaces=TEXTBOX_NSMAP
    )
```

### 3.3 Footnotes and Endnotes

python-docx 1.2.0 does NOT expose footnotes/endnotes via Python API. Access requires working with the OPC package directly.

**Footnotes are stored in `word/footnotes.xml`, endnotes in `word/endnotes.xml`.**

```python
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# Access footnotes part
doc_part = doc.part
for rel in doc_part.rels.values():
    if rel.reltype == RT.FOOTNOTES:
        footnotes_part = rel.target_part
        footnotes_xml = footnotes_part.element
        # Find all shd elements in footnotes
        shd_elements = footnotes_xml.xpath(
            './/w:shd',
            namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        )
        break

# Similarly for endnotes
for rel in doc_part.rels.values():
    if rel.reltype == RT.ENDNOTES:
        endnotes_part = rel.target_part
        endnotes_xml = endnotes_part.element
        shd_elements = endnotes_xml.xpath(
            './/w:shd',
            namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        )
        break
```

### 3.4 Comments

python-docx 1.2.0 DOES support comments. Each comment is a `BlockItemContainer` with paragraphs.

```python
for comment in doc.comments:
    for para in comment.paragraphs:
        pPr = para._p.get_or_add_pPr()
        shd = pPr.find(qn('w:shd'))
        # ... process
```

Alternatively, access via the comments part XML:
```python
for rel in doc.part.rels.values():
    if rel.reltype == RT.COMMENTS:
        comments_part = rel.target_part
        comments_xml = comments_part.element
        shd_elements = comments_xml.xpath(
            './/w:shd',
            namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        )
        break
```

---

## 4. Making Shading "White" or Removing Shading

There are two approaches, with different visual results:

### 4.1 Set Shading to White

```xml
<w:shd w:val="clear" w:color="auto" w:fill="FFFFFF"/>
```

```python
def set_shading_white(shd_element):
    """Set an existing w:shd element to white."""
    shd_element.set(qn('w:val'), 'clear')
    shd_element.set(qn('w:color'), 'auto')
    shd_element.set(qn('w:fill'), 'FFFFFF')
    # Remove theme attributes that could override the explicit color
    for attr in ['w:themeColor', 'w:themeFill', 'w:themeTint', 
                 'w:themeShade', 'w:themeFillTint', 'w:themeFillShade']:
        attrib_key = qn(attr)
        if attrib_key in shd_element.attrib:
            del shd_element.attrib[attrib_key]
```

### 4.2 Remove Shading Entirely

```python
def remove_shading(parent_element):
    """Remove w:shd element from a property element (pPr, rPr, tcPr, tblPr)."""
    shd = parent_element.find(qn('w:shd'))
    if shd is not None:
        parent_element.remove(shd)
```

**When to use which:**
- **Set to white:** When you want a guaranteed white background regardless of style inheritance
- **Remove entirely:** When you want the element to inherit shading from its style. If the style has no shading, this effectively means "no shading" (transparent). But if the parent style defines shading, removal means the style's shading will show through.

For a "make everything white" processor, **setting to white is safer** than removing -- it guarantees the visual result regardless of style hierarchy.

### 4.3 Critical: Theme Attributes Override Explicit Colors

When a `w:shd` element has both `w:fill` and `w:themeFill`, Word uses the theme color, NOT the explicit fill. To make shading truly white, you MUST remove theme-related attributes:

```python
def make_shd_white(shd):
    """Ensure shading is white, handling both explicit and theme colors."""
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'FFFFFF')
    # CRITICAL: Remove theme overrides
    for attr_name in ['w:themeFill', 'w:themeFillTint', 'w:themeFillShade',
                      'w:themeColor', 'w:themeTint', 'w:themeShade']:
        key = qn(attr_name)
        if key in shd.attrib:
            del shd.attrib[key]
```

---

## 5. python-docx Shading API Status

### What python-docx 1.2.0 DOES Provide

| Feature | API | Notes |
|---------|-----|-------|
| `w:highlight` on runs | `run.font.highlight_color` | Limited to `WD_COLOR_INDEX` enum (17 colors) |
| XML element ordering | `w:shd` in tag sequences | Knows where `w:shd` goes in element order |
| `OxmlElement` factory | `from docx.oxml import OxmlElement` | Creates properly namespaced XML elements |
| `qn()` helper | `from docx.oxml.ns import qn` | Converts `w:shd` to Clark notation |
| `get_or_add_pPr()` | On `CT_P` (paragraph element) | Ensures `w:pPr` exists |
| `get_or_add_rPr()` | On `CT_R` (run element) | Ensures `w:rPr` exists |
| `get_or_add_tcPr()` | On `CT_Tc` (table cell element) | Ensures `w:tcPr` exists |
| Header/footer access | `section.header`, `section.footer` | Full paragraph/table iteration |
| Comment access | `doc.comments` | Iteration over comments with paragraphs |
| Raw XML access | `element._element` or `element.xml` | Access underlying lxml element |

### What python-docx DOES NOT Provide

| Feature | Status | Workaround |
|---------|--------|------------|
| Paragraph shading property | Not implemented | Direct XML via `pPr.find(qn('w:shd'))` |
| Run shading property | Not implemented | Direct XML via `rPr.find(qn('w:shd'))` |
| Cell shading property | Not implemented | Direct XML via `tcPr.find(qn('w:shd'))` |
| Table shading property | Not implemented | Direct XML via `tblPr.find(qn('w:shd'))` |
| Text box access | Not implemented | XPath with custom namespaces |
| Footnote/endnote access | Not implemented | OPC relationship traversal |

---

## 6. Comprehensive XPath Strategy

### Find ALL `w:shd` Elements in a Document

The nuclear option -- find every `w:shd` regardless of location:

```python
from lxml import etree
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WPS_NS = 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape'
V_NS = 'urn:schemas-microsoft-com:vml'

ALL_NS = {
    'w': W_NS,
    'wps': WPS_NS,
    'v': V_NS,
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
}


def find_all_shd_in_part(root_element):
    """Find all w:shd elements in any XML part."""
    return root_element.xpath('.//w:shd', namespaces={'w': W_NS})


def process_all_shading(doc):
    """Find and process all w:shd elements across the entire document."""
    all_shd = []
    
    # 1. Document body (includes paragraphs, runs, tables, text boxes)
    body = doc.element.body
    all_shd.extend(find_all_shd_in_part(body))
    
    # 2. Headers and footers
    for section in doc.sections:
        for hf_prop in ['header', 'footer', 'even_page_header', 'even_page_footer',
                        'first_page_header', 'first_page_footer']:
            hf = getattr(section, hf_prop)
            if not hf.is_linked_to_previous:
                all_shd.extend(find_all_shd_in_part(hf._element))
    
    # 3. Footnotes
    for rel in doc.part.rels.values():
        if rel.reltype == RT.FOOTNOTES:
            all_shd.extend(find_all_shd_in_part(rel.target_part.element))
    
    # 4. Endnotes
    for rel in doc.part.rels.values():
        if rel.reltype == RT.ENDNOTES:
            all_shd.extend(find_all_shd_in_part(rel.target_part.element))
    
    # 5. Comments (if accessing via XML part)
    for rel in doc.part.rels.values():
        if rel.reltype == RT.COMMENTS:
            all_shd.extend(find_all_shd_in_part(rel.target_part.element))
    
    return all_shd
```

**Note:** The XPath `.//w:shd` on the body element will automatically find shading inside text boxes because text box content (`w:txbxContent`) is nested inside the body's XML tree. The `w:shd` elements inside text boxes are descendants of the body element, so a single recursive XPath query catches them.

### Categorizing Found Shading by Location

```python
def categorize_shd(shd_element):
    """Determine what type of shading this is based on parent element."""
    parent = shd_element.getparent()
    parent_tag = etree.QName(parent.tag).localname
    
    if parent_tag == 'pPr':
        return 'paragraph'
    elif parent_tag == 'rPr':
        return 'run'
    elif parent_tag == 'tcPr':
        return 'table_cell'
    elif parent_tag == 'tblPr':
        return 'table'
    else:
        return 'unknown'
```

---

## 7. Existing Project Pattern

The project already has shading manipulation in `src/processors/table_formatter.py`:

```python
def _set_cell_shading(cell, color_hex: str):
    """Set cell background color."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()

    # Remove existing shading
    existing_shd = tcPr.find(qn('w:shd'))
    if existing_shd is not None:
        tcPr.remove(existing_shd)

    # Create new shading
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)
```

This pattern is correct but only handles table cells. A shading processor needs to generalize this to all locations.

---

## 8. Key Considerations for Implementation

### 8.1 Don't Hand-Roll

| Problem | Use Instead |
|---------|-------------|
| Namespace string construction | `qn()` from `docx.oxml.ns` |
| XML element creation | `OxmlElement()` from `docx.oxml` |
| Finding elements | lxml `find()` / `xpath()` |
| Iterating headers/footers | python-docx section API |

### 8.2 Common Pitfalls

**Pitfall 1: Forgetting theme attributes**
Setting `w:fill="FFFFFF"` while `w:themeFill="accent1"` exists means Word still shows the theme color, not white. Always strip theme attributes when setting explicit colors.

**Pitfall 2: Header/footer creation side effect**
Accessing `section.header` or `section.footer` when none exists CREATES one. Check `header.is_linked_to_previous` to avoid modifying inherited headers.

**Pitfall 3: `w:shd` element ordering**
When creating a new `w:shd`, it must be inserted at the correct position in the parent element's children (OOXML enforces element ordering). Using `append()` is WRONG for `pPr` and `rPr` because `w:shd` must come after certain elements and before others. However, `OxmlElement` + the python-docx `_add_shd()` approach handles this if available, or use `_insert_shd()`. The safest approach: remove existing `w:shd`, then `append()` works on `tcPr` (where `w:shd` is late in the sequence), but for `pPr` and `rPr`, either:
  - Use `addnext()`/`addprevious()` relative to a known sibling, or
  - Use `insert()` at the correct index, or
  - Remove and recreate the property element (not recommended)

**Actually, the python-docx `_tag_seq` definitions handle ordering via `XmlComponent` infrastructure.** The CT_PPr, CT_RPr, CT_TcPr classes all define `_tag_seq` with `w:shd` in the correct position. If you use the CT class's `_add_shd()` method (auto-generated by python-docx's xmlchemy), it will insert at the correct position:

```python
# For paragraph properties -- python-docx generates these methods from _tag_seq:
pPr = paragraph._p.get_or_add_pPr()
# Remove existing first
existing = pPr.find(qn('w:shd'))
if existing is not None:
    pPr.remove(existing)
# _add_shd() inserts at correct position per _tag_seq
# But this method may not be defined -- verify at runtime
# Safest: just use find + remove + OxmlElement + append
```

**Note on append() safety:** Testing confirms that for `tcPr`, `append()` works because `w:shd` appears early-to-mid in the sequence and `tcPr` rarely has later siblings. For `pPr` and `rPr`, `append()` may place `w:shd` after elements that should come after it (like `w:tabs`, `w:jc` for `pPr` or `w:u`, `w:vertAlign` for `rPr`). In practice, Word is tolerant of slight misordering, but for correctness use the xmlchemy-generated insert methods or manual positional insertion.

**Practical recommendation:** Since you're primarily MODIFYING or REMOVING existing `w:shd` elements (not adding new ones), element ordering is usually not a concern. The find-modify pattern is safe.

**Pitfall 4: Text boxes in headers/footers**
Text boxes can be nested inside headers and footers. The XPath search on header `_element` will catch these, but only if you search headers separately from the body.

**Pitfall 5: Footnote/endnote parts may not exist**
Not all documents have footnotes or endnotes. The relationship traversal must handle `KeyError` or missing parts gracefully.

---

## 9. Reading Shading Values

```python
def read_shading(shd_element):
    """Read all shading attributes from a w:shd element."""
    if shd_element is None:
        return None
    
    return {
        'val': shd_element.get(qn('w:val')),
        'color': shd_element.get(qn('w:color')),
        'fill': shd_element.get(qn('w:fill')),
        'themeColor': shd_element.get(qn('w:themeColor')),
        'themeFill': shd_element.get(qn('w:themeFill')),
        'themeTint': shd_element.get(qn('w:themeTint')),
        'themeShade': shd_element.get(qn('w:themeShade')),
        'themeFillTint': shd_element.get(qn('w:themeFillTint')),
        'themeFillShade': shd_element.get(qn('w:themeFillShade')),
    }


def has_non_white_shading(shd_element):
    """Check if a w:shd element represents non-white/non-transparent shading."""
    if shd_element is None:
        return False
    
    val = shd_element.get(qn('w:val'))
    fill = shd_element.get(qn('w:fill'))
    theme_fill = shd_element.get(qn('w:themeFill'))
    color = shd_element.get(qn('w:color'))
    
    # 'nil' means no shading
    if val == 'nil':
        return False
    
    # Check if there's a non-white/non-auto fill
    if fill and fill.upper() not in ('FFFFFF', 'AUTO'):
        return True
    
    # Check for theme fill (any theme fill is considered non-white)
    if theme_fill:
        return True
    
    # Check for pattern-based shading (solid, stripes, etc.)
    if val and val not in ('clear', 'nil'):
        if color and color.upper() != 'AUTO':
            return True
    
    return False
```

---

## 10. Highlight vs. Shading

These are different things in DOCX:

| Feature | `w:highlight` | `w:shd` (in `w:rPr`) |
|---------|---------------|------------------------|
| Location | `w:rPr/w:highlight` | `w:rPr/w:shd` |
| Color range | 17 named colors only | Any RGB color |
| python-docx API | `run.font.highlight_color` | None (XML only) |
| Visual | Looks like a highlighter pen | Looks like a text background |
| Typical use | Manual highlighting | Programmatic/style-based coloring |

For a comprehensive "remove all background colors" processor, handle BOTH.

---

## Sources

### Primary (HIGH confidence)
- python-docx 1.2.0 source code (installed at `venv/Lib/site-packages/docx/`)
- OOXML spec via c-rex.net: [Paragraph Shading](https://c-rex.net/samples/ooxml/e1/Part4/OOXML_P4_DOCX_shd_topic_ID0E1CNM.html), [Run Shading](https://c-rex.net/samples/ooxml/e1/Part4/OOXML_P4_DOCX_shd_topic_ID0EAOXO.html), [Table Cell Shading](https://c-rex.net/samples/ooxml/e1/part4/OOXML_P4_DOCX_shd_topic_ID0ESU4Q.html), [Table Shading](https://c-rex.net/samples/ooxml/e1/Part4/OOXML_P4_DOCX_shd_topic_ID0EGNAR.html)
- OOXML spec: [ST_Shd enumeration](https://c-rex.net/samples/ooxml/e1/Part4/OOXML_P4_DOCX_ST_Shd_topic_ID0ELVN3.html)
- Existing project code: `src/processors/table_formatter.py`

### Secondary (MEDIUM confidence)
- [python-docx GitHub issue #1010](https://github.com/python-openxml/python-docx/issues/1010) -- text box access workaround
- [officeopenxml.com](http://www.officeopenxml.com/WPshading.php) -- shading reference (connection refused but content corroborated by c-rex.net)
