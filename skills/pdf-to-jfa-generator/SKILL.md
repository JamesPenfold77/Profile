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
    ├── regenerate_pelvic_floor_background.py
    ├── consent_invasive_procedure_podiatry.py
    └── regenerate_podiatry_consent_background.py
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
python -m generators.pdf_to_jfa.pdf_to_jfa consent_invasive_procedure_podiatry output/ConsentInvasiveProcedurePodiatry.jfa
```

The form module name is the filename in `forms/` without `.py`.

## The pixel-perfect-image-overlay strategy

For forms based on existing PDFs, the simplest path to a faithful reproduction is:

1. **Rasterize the PDF** at 96 DPI (matches the DFM's pixel coordinate system; A4 → 794 × 1123 px)
2. **Mask out** any page elements you don't want in the digital version (page numbers, underscore lines for handwritten fields, **example data baked into the source PDF as graphics**)
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

**Word-table-cell forms have NO underscore characters** — fillable lines are cell-row bottom borders, not `_` runs. For these forms, identify mask regions from the cell geometry instead: `page.find_tables()` returns cell bboxes; the fillable space is each cell's interior between the label text and the cell's bottom border.

**Example data baked as graphics is invisible to `page.chars`.** The Podiatry consent PDF (Form 4023J) has an example date "04/09/21" rendered as a graphic (no text characters extractable). Detect it via pixel analysis on the rasterized image: scan for dark text-like blobs in regions where input fields are expected. The `regenerate_podiatry_consent_background.py` mask table calls this out explicitly so future regenerations don't lose track of why those coordinates were chosen.

### Mask edge padding

Add ~2 points of padding on each edge of the mask to fully cover anti-aliased pixel edges. **Caveat**: if a label sits immediately adjacent to a masked region (e.g. the underscore line ends just before "Date:"), don't pad on that side — you'll clip the label. Use asymmetric per-edge padding:

```python
# (x0, y0, x1, y1, pad_left, pad_top, pad_right, pad_bot, label)
mask_regions = [
    (115.9, 557.4, 390.4, 568.0, 2, 2, 0, 2, 'Signature underscores'),  # right edge tight
    (418.3, 557.4, 529.4, 568.0, 0, 2, 2, 2, 'Date underscores'),       # left edge tight
]
```

For Word-table-cell forms, padding is usually 0 on all edges — the masks are positioned tightly inside cell interiors, so edges are already clear of labels.

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

### Calibration tips for Word-table-cell forms (Podiatry consent)

- Underline = cell-row bottom border, NOT a separate underscore line. Anchor controls so their *bottom* sits at the underline (slightly above so typed text rests above the line). Formula: `y_top = underline_y - control_height` works as a first pass.
- Cell borders intrude into masked areas — extend masks by 1–2 pt in both x directions to cover the cell-border stubs that survive otherwise.
- Word checkbox squares are tiny (≈10 pt × 10 pt). Mask precisely; controls overlaid here are ~14 px CheckBox primitives, not table cells.

## TISliceImageEditor: drawing/markup canvas

`TISliceImageEditor` (note: prefix is `TI…`, not `TICDO…`) is a markup control that lets the user draw on / annotate an image. The Profile source unit is `Profile/Client/Infrastructure/Scripting/USSliceEditor.pas`; toolbar tools include pen, line, rectangle, round-rect, ellipse, label, eraser, colour picker, zoom, image-stamp, arrow lines, triangles, and open/remove background image.

**Use it for any "indicate area on a diagram" interaction.** Examples: a podiatrist marks an area of nail/tissue on foot diagrams; a clinician circles an area on an anatomical diagram; staff annotate a patient ID photo.

**Property set is fixed** — copy the block emitted by `dfm_writer._emit_slice_editor`. The properties (`DefaultFont.*`, `DefaultBrush.*`, `DefaultToolBarSettings.*`, `DefaultStamp.*`) are not optional; they're what `TISliceImageEditor` instances always carry, lifted verbatim from the minimal sample's empty-instance template (`TISliceImageEditor1` in `Form Template - Form.jfa`).

**No image data is embedded in the DFM.** Two strategies for getting an image into the slice editor:

1. **Image stays in the form-level background**, slice editor sits transparently on top. The user draws on the slice editor; their marks visually overlay the underlying image. The image isn't owned by the slice editor and can't be replaced per-instance, but layout is dead simple. The Podiatry consent uses this strategy.
2. **Load at runtime** via the COM API: `Form.Controls_("sliceFoot1").BackgroundImage.LoadFromFile("...")`. The user (or a macro at form-open time) loads a per-instance background. Use when each form instance might use a different image.

Strategy 1 is the default; strategy 2 needs a `FormPreloadMacro` filled in. Don't bake image bytes into the slice editor's DFM — the published property `BackgroundImage` doesn't serialise as inline `Picture.Data`; experiments would be guesswork.

**Slicing a multi-panel image into separate slice editors.** For images that contain logically distinct panels (e.g. three foot diagrams in one rasterized strip), use one slice editor per panel rather than a single one over the whole strip. Each gets its own drawing layer, so marks on the Plain panel don't bleed into the Dorsal/Plantar panels. Find panel boundaries by column-darkness analysis of the rasterized image: long runs of mostly-white columns mark gaps between panels. The Podiatry consent has worked example code in `consent_invasive_procedure_podiatry.py`.

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

Either commit a regeneration helper alongside the form (preferred — see `regenerate_pelvic_floor_background.py` and `regenerate_podiatry_consent_background.py` for templates) or commit the PNG directly. The helper approach avoids checking binary assets into git and lets the source PDF be the source of truth.

### 3. Generate, import, calibrate

```bash
python -m generators.pdf_to_jfa.pdf_to_jfa <form_name> output/<form_name>.jfa
```

Import into Profile. Adjust controls. Export back. Update the form module with the calibrated coordinates. Commit.

## Form-def-id allocation

The synthetic form-def id (OBSV [3] of the 100502 row) is remapped by Profile on import — it doesn't need to refer to an existing database row. But forms in the same generator should use **distinct** placeholder ids to make exported logs and debug output easier to trace:

```
hello_world                           form_def_id = 90000001
consent_pelvic_floor                  form_def_id = 90000010
consent_invasive_procedure_podiatry   form_def_id = 90000020
<next form>                           form_def_id = 90000030
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

`TISliceImageEditor` data persistence is unclear — its content is the drawn graphics in `DrwLayer` plus any `BgLayer` image the user loaded, neither of which obviously fits the 100511/100517/100519 row schema. Likely requires a different field-row class (one that carries serialized graphics + image). Investigate by exporting a populated sample from Profile and comparing field-rows against the busy reference.

## Verifying CRLF and jaffa-encoding correctness

The generator already produces the right output, but verification scripts can deceive you. Two specific traps cost time on the Podiatry consent run; the rules below are how to avoid them next time.

**Read JFA files with `newline=''`.** Python's text-mode `open()` defaults to universal-newline translation, which silently rewrites `\r\n` to `\n` on read. A `content.split('\r\n')` then returns one part instead of five and looks like the row separators are missing. Always use `open(path, 'r', encoding='utf-8', newline='')` so `\r\n` is preserved verbatim.

```python
# Right
with open('output.jfa', 'r', encoding='utf-8', newline='') as f:
    content = f.read()
parts = content.split('\r\n')           # 5 parts: HEAD, LNVR, OBSV×2, ''

# Wrong (silent universal-newline translation)
with open('output.jfa', 'r', encoding='utf-8') as f:
    content = f.read()
parts = content.split('\r\n')           # 1 part — looks broken but isn't
```

**Count bytes, not Python escape literals.** A 1-byte CRLF at the file level is `b'\r'` + `b'\n'` (two bytes). The jaffa-encoded form is `b'\\0d\\0a'` — *four* bytes: `\`, `0`, `d`, `\`, `0`, `a` (six bytes total for the pair). When checking that DFM line breaks were properly escaped:

```python
with open('output.jfa', 'rb') as f:
    raw = f.read()

# Real CRLF row separators (HEAD/LNVR/OBSV/OBSV)
real_crlf = raw.count(b'\r\n')                  # expect 4

# Jaffa-encoded line breaks inside the DFM
jaffa_cr = raw.count(b'\x5c\x30\x64')           # = b'\0d', the byte sequence \,0,d
jaffa_lf = raw.count(b'\x5c\x30\x61')           # = b'\0a', the byte sequence \,0,a
# expect both > 0 and roughly equal (one per DFM line)

# Common mistake: b'\\\\0d' is FOUR bytes (\, \, 0, d) — won't match anything
```

If `real_crlf == 4` and `jaffa_cr / jaffa_lf` are in the thousands, the file is structurally correct: four row separators at the file level, plus the encoded line breaks inside the DFM that's stored in OBSV [13]. Anything else is a real bug.

**Sanity-check the row count and field counts before debugging the DFM.** If the four row separators are present and the field counts are right (HEAD: 15 fields, LNVR: 6, OBSV 100503: 44, OBSV 100502: 44), the framing is sound — any remaining issues are inside the DFM, not at the JFA file level.

```python
parts = content.split('\r\n')
assert len(parts) == 5  # 4 rows + trailing empty from final CRLF
assert parts[0].split('\t')[0] == 'HEAD' and len(parts[0].split('\t')) == 15
assert parts[1].split('\t')[0] == 'LNVR' and len(parts[1].split('\t')) == 6
assert parts[2].split('\t')[0:3] == ['OBSV', '2', '100503'] and len(parts[2].split('\t')) == 44
assert parts[3].split('\t')[0:3] == ['OBSV', '2', '100502'] and len(parts[3].split('\t')) == 44
```

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
| `TISliceImageEditor` import fails or shows blank | Don't omit any of the `Default*` properties — Profile's DFM streamer expects the full property set documented in `_emit_slice_editor`. Copy the block byte-for-byte from the minimal sample. |

## Reference samples

Two byte-precise samples in `generators/pdf_to_jfa/reference_samples/`:

- `Form_Template_-_Form.jfa` — minimal blank form with one of every control type (Label, Edit, Memo, RichEdit, RadioButton, CheckBox, Button, ComboBox, ListControl, Image, Bevel, Shape, **TISliceImageEditor**). The fixtures in `fixtures.py` are sliced verbatim from this file. The control palette in this sample is the canonical reference for property-set emissions.
- `Sample_Form_Template_Consent_for_Health_Care.jfa` — busy populated form. Demonstrates field-row classes and ~30 controls.

If you need to verify the generator's output structure matches a known-good sample, decode both DFMs and diff the sections that should be invariant (root form props before Caption, the macros block, the NoteBook prelude). The generator's first pass through Hello World achieved byte-identical match on these sections.

## Successful round-trips

As of May 2026:

- **HelloWorld.jfa** (single TICDOLabel) — imports cleanly, renders correctly. Validates the file-level structure end-to-end.
- **ConsentPelvicFloorEval.jfa** (full-page background TICDOImage + 9 input controls: 3× TICDOEdit, 3× TICDOSignature, 3× TICDOEdit-as-date) — imports cleanly, renders correctly after one calibration round-trip. Validates the full control palette except checkbox/radio/memo/slice.
- **ConsentInvasiveProcedurePodiatry.jfa** (background image + 3× TISliceImageEditor + 3× TICDOEdit + 3× TICDOEdit-as-date + 3× TICDOSignature + 1× TICDOMemo + 2× TICDOCheckBox = 16 items total) — generated, awaiting first import to validate the slice editor and checkbox/memo code paths against a real Profile run.
