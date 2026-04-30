"""
Consent for Pelvic Floor Muscle Evaluation and Treatment.

Layout strategy:
  - Page background: rasterized PDF at 96 DPI with 10 regions masked white
    (page-number "1" + 9 underscore lines for Names/Signatures/Dates).
    Embedded as a single full-canvas TICDOImage at (0,0).
  - 9 input controls overlaid on top:
        - Name fields:      TICDOEdit, 250x22, x=200
        - Signature fields: TICDOSignature, 250x22, x=200
        - Date fields:      TICDOEdit with EditType=edtyDate, 150x22, x=560
                            (right of Signature, matching original PDF layout)
  - No HRIs in this layout-only first pass; data-binding deferred until
    visual round-trip is validated and the layout is final.

Coordinate calibration:
  Initial guesses for control positions drifted ~18-20 px low (controls
  sat below their labels with too much gap). After importing into Profile
  and adjusting in the form designer, the calibrated positions below were
  exported back to JFA and baked in here. Date x-positions had per-row
  micro-variance (560/565/575) from manual nudging; standardised to 560
  across all rows for consistency.

Concept:    z..UB
Folder:     NZDF (verbatim from minimal-sample fixture)
Form name:  Consent for Pelvic Floor Muscle Evaluation and Treatment
"""
from __future__ import annotations
from pathlib import Path

from ..layout import (
    FormLayout, Rect, Image, Edit, DateEdit, Signature,
)


# Page image dimensions (PDF rasterized at 96 DPI; A4 = 595.32 x 841.92 pt
# rounds to 794 x 1123 px at 96 DPI). Note: the calibrated DFM uses a slightly
# wider notebook (820) to match the client viewport width — this avoids a
# narrow column of empty space on the right edge of the visible canvas.
PAGE_W = 794
PAGE_H = 1123
NOTEBOOK_W = 820   # post-calibration: matches client_width
NOTEBOOK_H = 1123

# Path to the masked background PNG. Resolved relative to this file so the
# generator works regardless of the working directory.
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_BACKGROUND = _THIS_DIR / 'assets' / 'pelvic_floor_background.png'


def build_layout(form_def_id: int = 90000010,
                 background_path: str | Path | None = None) -> FormLayout:
    """Construct the FormLayout for the Pelvic Floor consent form.

    Args:
        form_def_id:     synthetic OBSV [3] for the 100502 row (Profile remaps).
        background_path: PNG to embed. Defaults to the bundled masked image
                         at assets/pelvic_floor_background.png.
    """
    bg = Path(background_path) if background_path else DEFAULT_BACKGROUND

    layout = FormLayout(
        form_name='ConsentPelvicFloorEval',
        caption='Consent for Pelvic Floor Muscle Evaluation and Treatment',
        concept_code='z..UB',
        concept_display_name='Consent for Pelvic Floor Muscle Evaluation and Treatment',
        folder_category='NZDF',
        form_def_id=form_def_id,
        # Visible viewport — A4-ish portrait for screen viewing.
        client_width=820,
        client_height=620,
        # NoteBook canvas: width matches client; height matches page image.
        notebook_width=NOTEBOOK_W,
        notebook_height=NOTEBOOK_H,
    )

    # Full-page background image (image is exactly PAGE_W x PAGE_H px).
    layout.add(Image(
        name='imgBackground',
        rect=Rect(0, 0, PAGE_W, PAGE_H),
        image_path=str(bg),
        stretch=False,       # 1:1 pixel mapping (image already at canvas size)
        proportional=False,
    ))

    # Calibrated control positions. Names + Signatures share x=200, w=250.
    # Dates share x=560, w=150. Y values from manual designer adjustment.
    # Format: (name, factory, x, y, w, h)
    controls = [
        ('edtClientName',    Edit,      200, 692, 250, 22),
        ('edtClientSig',     Signature, 200, 740, 250, 22),
        ('edtClientSigDate', DateEdit,  560, 738, 150, 22),
        ('edtChapName',      Edit,      200, 787, 250, 22),
        ('edtChapSig',       Signature, 200, 835, 250, 22),
        ('edtChapSigDate',   DateEdit,  560, 834, 150, 22),
        ('edtClinName',      Edit,      200, 885, 250, 22),
        ('edtClinSig',       Signature, 200, 935, 250, 22),
        ('edtClinSigDate',   DateEdit,  560, 931, 150, 22),
    ]
    for tab, (name, cls, x, y, w, h) in enumerate(controls):
        layout.add(cls(
            name=name,
            rect=Rect(x, y, w, h),
            tab_order=tab,
        ))

    return layout
