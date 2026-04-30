# Skill: PDF-to-JFA Generator

Use this skill when generating Profile EMR CDO Form JFA files from PDF source documents (or from scratch), or when extending the generator at `generators/pdf_to_jfa/`. Covers the architecture, the calibration loop (round-tripping through Profile's designer to refine control positions), the pixel-perfect-image-overlay strategy, and concrete recipes for adding new forms.

Pairs with the **jfa-format** skill, which covers the JFA file format itself (record layout, field positions, jaffa encoding, DFM payload). This skill assumes that one is the reference for "what" the format looks like and focuses on "how" to produce it.

## Architecture

```
generators/pdf_to_jfa/
├── jaffa_encoding.py     # Tab/CR/LF escaping for OBSV field values
├── layout.py             # Dataclasses: FormLayout, Rect, Edit, Signature, ...
├── fixtures.py           # Verbatim DFM/JFA templates from the minimal sample
├── dfm_writer.py         # Per-control DFM emitters
├── jfa_writer.py         # HEAD/LNVR/OBSV row assembly, BOM/CRLF/TAB
├── pdf_to_jfa.py         # CLI driver
├── reference_samples/    # Byte-precise sample JFAs from Profile
│   ├── Form_Template_-_Form.jfa
│   └── Sample_Form_Template_Consent_for_Health_Care.jfa
└── forms/                # One Python module per form
    ├── hello_world.py
    ├── consent_pelvic_floor.py
    └── regenerate_pelvic_floor_background.py
```

The design is **fixtures + emitters**: form-level boilerplate (root form properties, the 16-entry macros block, NoteBook prelude, NZDF context row) is spliced verbatim from a known-good minimal sample. Per-control DFM is emitted by hand using the property sets observed in working samples.

This split is deliberate. Boilerplate has many fiddly details that aren't documented anywhere; copying the bytes is more reliable than reconstructing them. Per-control bodies are small and predictable enough to emit programmatically.

## Generating an existing form

```bash
cd <repo>
python -m generators.pdf_to_jfa.pdf_to_jfa <form_module> <output_path>

# Example
python -m generators.pdf_to_jfa.pdf_to_jfa hello_world output/HelloWorld.jfa
python -m generators.pdf_to_jfa.pdf_to_jfa consent_pelvic_floor output/ConsentPelvicFloorEval.jfa
```

The form module name is the filename in `forms/` without `.py`.

## The pixel-perfect-image-overlay strategy

For forms based on existing PDFs, the simplest path to a faithful reproduction is:

1. **Rasterize the PDF** at 96 DPI (matches the DFM's pixel coordinate system; A4 → 794 × 1123 px)
2. **Mask out** any page elements you don't want in the digital version (page numbers, underscore lines for handwritten fields)
3. **Embed the masked PNG** as a single full-canvas `TICDOImage` at (0, 0)
4. **Overlay input controls** at pixel positions that align with the visual fields in the image

This skips the hard problem of rebuilding rich-text content (paragraph styling, bold lead-ins, etc.) as native DFM controls. The downside is that the form's text isn't searchable inside Profile and screen readers can't read it — acceptable for low-volume consent forms but not for high-volume clinical forms where saved data needs to be queryable from text content.

The masking step matters. Underscore lines and page numbers in the rasterized image will sit *under* the input controls, but their edges may peek out around the control borders. White-out regions in the image so the controls have a clean background.

### Mask region detection

`pdfplumber` reliably finds underscore characters and small text:

```python
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    underscores = [c for c in page.chars if c['text'] == '_']
    # Group consecutive underscores into runs by y-coord and x-proximity
```

Page numbers usually appear as standalone `'1'`, `'2'`, ... characters in the bottom margin. Filter `page.chars` by text content and y-position.

### Mask edge padding

Add ~2 points of padding on each edge of the mask to fully cover anti-aliased pixel edges. **Caveat**: if a label sits immediately adjacent to a masked region (e.g. the underscore line ends just before "Date:"), don't pad on that side — you'll clip the label. Use asymmetric per-edge padding:

```python
# (x0, y0, x1, y1, pad_left, pad_top, pad_right, pad_bot, label)
mask_regions = [
    (115.9, 557.4, 390.4, 568.0, 2, 2, 0, 2, 'Signature underscores'),  # right edge tight
    (418.3, 557.4, 529.4, 568.0, 0, 2, 2, 2, 'Date underscores'),       # left edge tight
]
```

## The calibration loop

First-pass control coordinates from PDF text positions are usually a few pixels off in the DFM coordinate system (observed: ~18 px low). Don't try to nail it from formulas alone. Round-trip:

1. Generate the form, import into Profile
2. Open in form designer, drag controls until they look right
3. Save / export the form back to JFA
4. Decode the new positions from the exported DFM
5. Bake the calibrated coordinates back into the form module

Reading positions out of an exported DFM:

```python
import re
def grab_props(dfm, control_name):
    body = re.search(
        rf'object {re.escape(control_name)}: T\w+(.*?)\n\s*end',
        dfm, re.DOTALL,
    ).group(1)
    props = {}
    for prop in ['Left', 'Top', 'Width', 'Height']:
        m = re.search(rf'\b{prop}\s*=\s*(\S+?)(?:\r|$)', body)
        if m: props[prop] = int(m.group(1).strip())
    return props
```

After calibration, document the manual adjustments with a comment in the form module. Future regeneration will produce the calibrated layout deterministically.

### Calibration tips from the Pelvic Floor consent session

- "Label bottom + 2 px" was too generous — controls drifted ~18 px below their labels. Closer to "underscore line center − half control height" or "label top + 4 px"
- Manual designer adjustments produce small per-row variance (e.g. Date x at 560/565/575 across three rows). Standardise these in the form module rather than preserving the variance — the variance reflects mouse imprecision, not intent
- The NoteBook width should match `client_width` to avoid an empty column on the right edge of the visible canvas
- Date controls don't need to share x-alignment with Names/Signatures — visually the original PDF design (Date beside Signature, narrower) often reads better

## Adding a new form

### 1. Write a form layout module

`forms/<form_name>.py`:

```python
from __future__ import annotations
from pathlib import Path
from ..layout import FormLayout, Rect, Image, Edit, DateEdit, Signature

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_BACKGROUND = _THIS_DIR / 'assets' / '<form_name>_background.png'


def build_layout(form_def_id: int = 90000020,
                 background_path: str | Path | None = None) -> FormLayout:
    bg = Path(background_path) if background_path else DEFAULT_BACKGROUND

    layout = FormLayout(
        form_name='<PascalName>',
        caption='<Display caption>',
        concept_code='z..UB',
        concept_display_name='<Display name>',
        folder_category='NZDF',
        form_def_id=form_def_id,
        client_width=820,
        client_height=620,
        notebook_width=820,
        notebook_height=1123,
    )

    layout.add(Image(
        name='imgBackground',
        rect=Rect(0, 0, 794, 1123),
        image_path=str(bg),
        stretch=False, proportional=False,
    ))

    # ... per-control add() calls ...
    return layout
```

### 2. Build the masked background

Either commit a regeneration helper alongside the form (preferred — see `regenerate_pelvic_floor_background.py` for a template) or commit the PNG directly. The helper approach avoids checking binary assets into git and lets the source PDF be the source of truth.

### 3. Generate, import, calibrate

```bash
python -m generators.pdf_to_jfa.pdf_to_jfa <form_name> output/<form_name>.jfa
```

Import into Profile. Adjust controls. Export back. Update the form module with the calibrated coordinates. Commit.

## Form-def-id allocation

The synthetic form-def id (OBSV [3] of the 100502 row) is remapped by Profile on import — it doesn't need to refer to an existing database row. But forms in the same generator should use **distinct** placeholder ids to make exported logs and debug output easier to trace:

```
hello_world           form_def_id = 90000001
consent_pelvic_floor  form_def_id = 90000010
<next form>           form_def_id = 90000020
```

Increment by 10 to leave room.

## Concept-pair selection

Field [7] of the 100502 row is the form's concept code. Field [8] is its paired partner concept (semantics not fully understood, but it varies in lockstep with [7] — see the **jfa-format** skill for the table of observed pairs).

The minimal blank-form sample uses `z..UB` / `z..UC`. As long as new forms use this same pair, they import cleanly. For forms with a specific clinical concept (not the generic blank-form concept), determine the right partner concept from a working sample of the same form type, or ask someone who maintains the termset.

The `jfa_writer.write_jfa()` function defaults to `('z..UB', 'z..UC')` when the layout's concept_code is `z..UB`. For other concepts, pass `concept_pair` explicitly.

## Layout-only vs data-binding modes

The generator currently produces **layout-only** forms — the form imports and renders, input controls work in-session, but saved data doesn't persist to a queryable column. To add data binding, each input control needs:

1. An `HRI = <integer>` property in its DFM block
2. A matching OBSV field row (100511 for text/date, 100517 for date-with-NULLTIME, 100519 for boolean) with `TI=<same integer>` in field [9]

The HRI/TI integer is a termset concept id. Whether these IDs need to pre-exist in the Profile database or are created on import is environment-dependent — confirm before allocating IDs for production forms. If pre-allocation is needed, pick a contiguous block (the busy reference sample uses 166122–166210) and document the range.

Adding 100511/100517/100519 row emission to the generator is straightforward — see the structure in the busy reference sample. The row layout is documented in the **jfa-format** skill.

## Common failure modes

| Symptom | Likely cause |
|---------|--------------|
| Profile rejects with "incorrect format" | Missing BOM, wrong line endings (LF instead of CRLF), comma instead of tab as separator, or wrong number of fields in some OBSV row |
| Form imports but DFM rendering is empty | DFM not jaffa-encoded properly; check field [13] of the 100502 row for unescaped tabs or CRLFs |
| Form renders but image is broken | Wrong image stream prefix (use `0B546478504E47496D616765` for TdxPNGImage, not the standard TPngImage prefix) |
| Form renders but controls are off-position | Coordinate system mismatch — DFM is pixels, not PDF points; convert via `× 96/72` |
| Form imports but a control type is missing | Likely emitting an unrecognized class name. The class palette in working samples is in the **jfa-format** skill |
| Single-quote characters in captions break rendering | Quotes in DFM strings escape by doubling (`'O''Brien'`), not backslash |
| Form imports but input controls drift below their labels by ~18 px | First-pass calibration formula is too generous — see "Calibration tips" above |

## Reference samples

Two byte-precise samples in `generators/pdf_to_jfa/reference_samples/`:

- `Form_Template_-_Form.jfa` — minimal blank form. The fixtures in `fixtures.py` are sliced verbatim from this file.
- `Sample_Form_Template_Consent_for_Health_Care.jfa` — busy populated form. Demonstrates field-row classes and ~30 controls.

If you need to verify the generator's output structure matches a known-good sample, decode both DFMs and diff the sections that should be invariant (root form props before Caption, the macros block, the NoteBook prelude). The generator's first pass through Hello World achieved byte-identical match on these sections.

## Successful round-trips

As of April 2026:

- **HelloWorld.jfa** (single TICDOLabel) — imports cleanly, renders correctly. Validates the file-level structure end-to-end.
- **ConsentPelvicFloorEval.jfa** (full-page background TICDOImage + 9 input controls: 3× TICDOEdit, 3× TICDOSignature, 3× TICDOEdit-as-date) — imports cleanly, renders correctly after one calibration round-trip. Validates the full control palette except checkbox/radio.

The next form to generate from scratch will be the first test of the checkbox/radio code paths, which are emitted by `dfm_writer.py` but have not yet been exercised against a real Profile import.
