"""
Consent for Pelvic Floor Muscle Evaluation and Treatment.

Layout strategy (per Path B decision):
  - Page background: rasterized PDF at 96 DPI with 10 regions masked white
    (page-number "1" + 9 underscore lines for Names/Signatures/Dates).
  - Background embedded as a single full-canvas TICDOImage.
  - 9 input controls overlaid on top, all 250 x 22 px, all left-aligned at
    x=132, sitting immediately below their respective labels:
        Names: TICDOEdit
        Signatures: TICDOSignature
        Dates: TICDOEdit with EditType=edtyDate / EditKind=edkdDate
    Date controls stack BELOW their Signature counterparts. This is a
    deliberate UX choice — accepting some overlap with the next group's
    Name label area to keep all controls left-aligned.
  - No HRIs (layout-only first pass; data-binding deferred).

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
# rounds to 794 x 1123 px at 96 DPI).
PAGE_W = 794
PAGE_H = 1123

# Input control geometry — all left-aligned, fixed size.
EDIT_X = 132
EDIT_W = 250
EDIT_H = 22


# Path to the masked background PNG. Resolved relative to this file so the
# generator works regardless of the working directory.
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_BACKGROUND = _THIS_DIR / 'assets' / 'pelvic_floor_background.png'


def build_layout(form_def_id: int = 90000010,
                 background_path: str | Path | None = None) -> FormLayout:
    """Construct the FormLayout for the Pelvic Floor consent form.

    Args:
        form_def_id: synthetic OBSV [3] for the 100502 row (Profile remaps).
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
        # Visible viewport — A4-ish portrait for screen viewing
        client_width=820,
        client_height=620,
        # NoteBook canvas matches the page image exactly
        notebook_width=PAGE_W,
        notebook_height=PAGE_H,
    )

    # Full-page background image (covers the entire panel).
    layout.add(Image(
        name='imgBackground',
        rect=Rect(0, 0, PAGE_W, PAGE_H),
        image_path=str(bg),
        stretch=False,       # 1:1 pixel mapping (image already at canvas size)
        proportional=False,
    ))

    # 9 input controls, top-down. Tab order matches reading order.
    # Coordinates are pre-computed to sit just below each label in the image.
    controls = [
        ('edtClientName',     710, Edit),
        ('edtClientSig',      759, Signature),
        ('edtClientSigDate',  783, DateEdit),
        ('edtChapName',       807, Edit),
        ('edtChapSig',        855, Signature),
        ('edtChapSigDate',    879, DateEdit),
        ('edtClinName',       904, Edit),
        ('edtClinSig',        952, Signature),
        ('edtClinSigDate',    976, DateEdit),
    ]
    for tab, (name, y, cls) in enumerate(controls):
        item = cls(
            name=name,
            rect=Rect(EDIT_X, y, EDIT_W, EDIT_H),
            tab_order=tab,
        )
        layout.add(item)

    return layout
