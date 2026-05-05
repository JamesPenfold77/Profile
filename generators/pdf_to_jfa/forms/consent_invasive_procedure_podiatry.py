"""
Client Consent for Invasive Procedure (Podiatry) — NWRH Form 4023J.

Layout strategy:
  - Page background: rasterized PDF at 96 DPI with mask regions painted
    white over (a) the example "04/09/21" date in the source, (b) the
    blank fillable cell-line spaces, and (c) the entire "Where applicable:"
    panel (italic header + 2 checkbox rows + their text). Embedded as a
    single full-canvas TICDOImage at (0,0).
  - 3x TISliceImageEditor controls overlaid on the foot-diagram strip —
    one per panel (Plain anatomical / Dorsal / Plantar). The slice editor
    lets the podiatrist mark up the foot diagrams ("indicate area of
    nail/tissue to be removed") with pen / line / rect / ellipse tools.
    The foot images themselves stay in the page-background PNG; the slice
    editors are transparent overlays positioned over each panel so marks
    land visually on top of the image.
  - 3x TICDOSignature pads:
        * Patient signature ("Signed:" row)
        * Witness signature ("Witness:" row)
        * Podiatrist signature (bottom row, under "Signature" caption)
  - 3x TICDOEdit:
        * Signatory's name on the "I, ___ authorise" line
        * Patient name + relationship on line 2
        * Podiatrist name in block letters (bottom row, left column)
  - 1x TICDOMemo for the procedure description (multi-line area above
    "(state procedure precisely)" caption).
  - 2x TICDOCheckBox + 2x TICDOLabel (wrapping) + 1x TICDOLabel (italic
    header) — replacing the entire "Where applicable:" panel from the
    source PDF (mask blanks the whole panel; native controls render text
    + checkboxes with proper alignment).
  - 3x TICDOEdit-as-date (patient signature date, witness date,
    podiatrist signature date).

  Total: 1 background image + 3 slice editors + 15 input/label items.

Coordinate calibration:
  First-pass coordinates derived from PDF point positions (extracted via
  pdfplumber) converted to 96-DPI pixels (px = pt × 96/72 = pt × 4/3).
  Underlines in this form are table-cell bottom borders rather than
  underscore characters, so positions are anchored to the cell-bottom
  underline rather than to a label baseline. Expect ~5–15 px drift on
  first import; round-trip into Profile's form designer to refine.

Concept:    z..UB
Folder:     NZDF (verbatim from minimal-sample fixture)
Form name:  Client Consent Invasive Procedure Podiatry (NWRH 4023J)
"""
from __future__ import annotations
from pathlib import Path

from ..layout import (
    FormLayout, Rect, Image, Label, Edit, DateEdit, Memo, Signature, CheckBox,
    SliceImageEditor,
)


# Page image dimensions: A4 portrait at 96 DPI = 794 x 1123 px.
PAGE_W = 794
PAGE_H = 1123

# NoteBook canvas: width matches client viewport (no empty column on right);
# height matches page image.
NOTEBOOK_W = 820
NOTEBOOK_H = PAGE_H

# Path to the masked background PNG. Resolved relative to this file so the
# generator works regardless of working directory. Regenerate via
# `python -m generators.pdf_to_jfa.forms.regenerate_podiatry_consent_background`.
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_BACKGROUND = _THIS_DIR / 'assets' / 'podiatry_consent_background.png'


def _pt(p: float) -> int:
    """Convert PDF points to 96-DPI pixels (DFM coordinate space)."""
    return int(round(p * 96 / 72))


def build_layout(form_def_id: int = 90000020,
                 background_path: str | Path | None = None) -> FormLayout:
    """Construct the FormLayout for the Podiatry consent form.

    Args:
        form_def_id:     synthetic OBSV [3] for the 100502 row (Profile remaps).
        background_path: PNG to embed. Defaults to the bundled masked image
                         at assets/podiatry_consent_background.png.
    """
    bg = Path(background_path) if background_path else DEFAULT_BACKGROUND

    layout = FormLayout(
        form_name='ConsentInvasiveProcedurePodiatry',
        caption='Client Consent for Invasive Procedure (Podiatry)',
        concept_code='z..UB',
        concept_display_name='Client Consent for Invasive Procedure (Podiatry)',
        folder_category='NZDF',
        form_def_id=form_def_id,
        # Visible viewport — A4 width, partial-height for screen scrolling.
        client_width=NOTEBOOK_W,
        client_height=620,
        # NoteBook canvas: full A4 page height; horizontal matches client.
        notebook_width=NOTEBOOK_W,
        notebook_height=NOTEBOOK_H,
    )

    # Full-page background image. The image is exactly PAGE_W x PAGE_H px and
    # already includes everything except: the example date, the cell underlines
    # for input fields, and the entire Where-applicable panel (all painted white
    # by the mask). The foot diagrams ARE in the background — slice editors
    # below sit transparently on top of them.
    layout.add(Image(
        name='imgBackground',
        rect=Rect(0, 0, PAGE_W, PAGE_H),
        image_path=str(bg),
        stretch=False,       # 1:1 pixel mapping (image already at canvas size)
        proportional=False,
    ))

    # ============================================================
    # Slice editors — one per foot panel.
    # The foot-image table-cell extends from x_pt=59.7..535.6, y_pt=329.4..479.9.
    # Within it, gap analysis (probe via column whiteness in the rasterized
    # image) found two clean vertical gaps at page-px x≈376 and x≈553,
    # giving three panels:
    #   Panel 1 (Plain feet, R/L):    x_px=87..376  → x_pt=65..282
    #   Panel 2 (Dorsal feet, R/L):   x_px=376..553 → x_pt=282..415
    #   Panel 3 (Plantar feet, R/L):  x_px=553..714 → x_pt=415..535
    # First-pass (y_pt=330..445) put the editors over empty space at the top
    # of the cell — the foot drawings actually start at y_pt≈360 and end
    # around y_pt≈455 (above the R/L caption labels at y_pt≈456..466 and
    # the "Dorsal"/"Plantar" labels at y_pt≈460..470).
    # Calibrated after first import showed slice editors were ~30 pt too
    # high; corrected here.
    # ============================================================
    SLICE_Y = _pt(360)   # top of foot drawings (was 330, 30pt too high)
    SLICE_H = _pt(95)    # cover drawings, leave clearance above R/L labels

    layout.add(SliceImageEditor(
        name='sliceFeetPlain',
        rect=Rect(_pt(65), SLICE_Y, _pt(282) - _pt(65), SLICE_H),
        tab_order=0,
        show_toolbar=True,
    ))
    layout.add(SliceImageEditor(
        name='sliceFeetDorsal',
        rect=Rect(_pt(282), SLICE_Y, _pt(415) - _pt(282), SLICE_H),
        tab_order=1,
        show_toolbar=True,
    ))
    layout.add(SliceImageEditor(
        name='sliceFeetPlantar',
        rect=Rect(_pt(415), SLICE_Y, _pt(535) - _pt(415), SLICE_H),
        tab_order=2,
        show_toolbar=True,
    ))

    # ============================================================
    # Header / patient details cell ("I, ___ authorise the performance upon
    # ___ of the following operation:")
    # Row 1 underline y_pt≈183 (cell-row bottom). Row 2 underline y_pt≈211.
    # Edit controls are 22 px tall, anchored so their bottom sits at the
    # underline (slightly above so the typed text rests above the line).
    # ============================================================
    EDIT_H = 22

    # Signatory name — "I, ___ authorise the performance upon"
    # Spans from after "I," (x_pt=72) to just before "authorise" (x_pt=360).
    layout.add(Edit(
        name='edtSignatoryName',
        rect=Rect(_pt(73), _pt(183) - EDIT_H, _pt(360) - _pt(73), EDIT_H),
        tab_order=3,
    ))

    # Patient name + relationship — second line, full-width up to "of"
    # Italic caption "(myself or name of patient and relationship)" sits
    # below this and is preserved in the background image.
    layout.add(Edit(
        name='edtPatientNameRelationship',
        rect=Rect(_pt(66), _pt(211) - EDIT_H, _pt(360) - _pt(66), EDIT_H),
        tab_order=4,
    ))

    # ============================================================
    # Procedure description (multi-line) — cells 3 & 4 above the italic
    # "(state procedure precisely)" caption at y_pt=305.9.
    # The fillable area is roughly y_pt=246..303, full cell width.
    # Use a Memo for multi-line input.
    # ============================================================
    layout.add(Memo(
        name='memoProcedure',
        rect=Rect(_pt(66), _pt(247),
                  _pt(535) - _pt(66), _pt(303) - _pt(247)),
        tab_order=5,
    ))

    # ============================================================
    # "Where applicable:" panel — replaces the entire on-page panel
    # (italic header + 2 checkbox rows + their text) with native controls.
    # The background mask covers PDF y_pt=480..555 across the full cell
    # width, so this whole region is clean white.
    #
    # First import attempt overlaid TICDOCheckBox controls over the source
    # PDF's Word-table-cell checkbox squares. The leading "I" of "I note..."
    # was being clipped by the right edge of the on-page checkbox cell — no
    # alignment of mask + control kept both the "I" visible and the on-page
    # checkbox hidden. Solution: wipe the whole panel and re-render it with
    # native controls.
    #
    # Layout:
    #   y=482   italic Label "Where applicable:" (~16 px tall)
    #   y=502   row 1: CheckBox + wrapping Label (under-16 supervision)
    #   y=528   row 2: CheckBox + wrapping Label (student under direction)
    # CheckBox at x=66 (cell-left + small inset). Label sits to the right
    # of the CheckBox at x=85 with word-wrap so the text occupies up to
    # two visual lines (matching the original PDF's wrap point).
    # ============================================================
    layout.add(Label(
        name='lblWhereApplicable',
        rect=Rect(_pt(60), _pt(482), _pt(120), 14),
        text='Where applicable:',
        italic=True,
        font_size=10,
    ))

    CB_SIZE = 14
    CB_X = _pt(66)
    LBL_X = _pt(85)            # ~5 pt gap right of the checkbox
    LBL_W = _pt(540) - LBL_X    # extends to right cell border
    LBL_H = 24                  # two-line wrap height

    layout.add(CheckBox(
        name='cbUnder16Accompanied',
        rect=Rect(CB_X, _pt(502), CB_SIZE, CB_SIZE),
        caption='',
        tab_order=6,
    ))
    layout.add(Label(
        name='lblUnder16Text',
        rect=Rect(LBL_X, _pt(502), LBL_W, LBL_H),
        text='I note that my child, if under 16 MUST BE ACCOMPANIED by '
             'myself or another responsible adult and I will arrange this.',
        word_wrap=True,
        auto_size=False,
        font_size=10,
    ))

    layout.add(CheckBox(
        name='cbStudentDirected',
        rect=Rect(CB_X, _pt(528), CB_SIZE, CB_SIZE),
        caption='',
        tab_order=7,
    ))
    layout.add(Label(
        name='lblStudentText',
        rect=Rect(LBL_X, _pt(528), LBL_W, LBL_H),
        text='I fully understand that the aforementioned operation may be '
             'performed by a student under the direction of the podiatrist.',
        word_wrap=True,
        auto_size=False,
        font_size=10,
    ))

    # ============================================================
    # Patient signature row — "Signed: ___ Date: ___"
    # Underline at y_pt=666 (cell-row bottom).
    # ============================================================
    SIG_H = 22

    layout.add(Signature(
        name='sigPatient',
        rect=Rect(_pt(100), _pt(666) - SIG_H, _pt(339) - _pt(100), SIG_H),
        tab_order=8,
    ))
    layout.add(DateEdit(
        name='dtPatientSig',
        rect=Rect(_pt(365), _pt(666) - EDIT_H, _pt(535) - _pt(365), EDIT_H),
        tab_order=9,
    ))

    # ============================================================
    # Witness signature row — "Witness: ___ Date: ___"
    # Underline at y_pt=696.8.
    # Witness signature pad starts a bit further right (x_pt=105) since the
    # "Witness:" label is wider than "Signed:".
    # ============================================================
    layout.add(Signature(
        name='sigWitness',
        rect=Rect(_pt(105), _pt(697) - SIG_H, _pt(339) - _pt(105), SIG_H),
        tab_order=10,
    ))
    layout.add(DateEdit(
        name='dtWitness',
        rect=Rect(_pt(365), _pt(697) - EDIT_H, _pt(535) - _pt(365), EDIT_H),
        tab_order=11,
    ))

    # ============================================================
    # Podiatrist row — "Signed: <Name> <Signature> <Date>"
    # The label "Signed:" is at x_pt=65..95, y_pt=734..744. The italic
    # caption row "(Podiatrist- Name in block letters) / Signature / Date"
    # sits BELOW the underlines, at y_pt=746..757.
    # Underlines at y_pt=744 (cell-row bottom).
    # Three columns:
    #   Name:      x_pt=100..297   (above "(Podiatrist- Name in block letters)")
    #   Signature: x_pt=302..425   (above "Signature" caption at x_pt=329..368)
    #   Date:      x_pt=430..535   (above "Date" caption at x_pt=468..487)
    # ============================================================
    layout.add(Edit(
        name='edtPodiatristName',
        rect=Rect(_pt(100), _pt(744) - EDIT_H, _pt(297) - _pt(100), EDIT_H),
        tab_order=12,
    ))
    layout.add(Signature(
        name='sigPodiatrist',
        rect=Rect(_pt(302), _pt(744) - SIG_H, _pt(425) - _pt(302), SIG_H),
        tab_order=13,
    ))
    layout.add(DateEdit(
        name='dtPodiatrist',
        rect=Rect(_pt(430), _pt(744) - EDIT_H, _pt(535) - _pt(430), EDIT_H),
        tab_order=14,
    ))

    return layout
