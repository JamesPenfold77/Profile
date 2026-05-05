"""
Regenerate the masked background PNG for the Podiatry consent form.

Rasterizes the source PDF at 96 DPI, then paints white over the example
"04/09/21" date and over the blank lines/cells that will receive overlay
input controls (so the controls sit on clean white background). Output goes
to assets/podiatry_consent_background.png next to the form module.

Usage:
    python -m generators.pdf_to_jfa.forms.regenerate_podiatry_consent_background \\
        path/to/Form_4023J_Client_Consent_Invasive_Procedure__Podiatry_.pdf

Requires: pdftoppm (poppler-utils) on PATH, Pillow installed.

Mask region coordinates were derived empirically by inspecting the source
PDF with pdfplumber. They are hard-coded here because the source PDF doesn't
change. If it is replaced, re-detect the regions with pdfplumber and update
the MASK_REGIONS_PT table below.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


SCALE = 96 / 72  # PDF points -> 96-DPI image pixels


# Mask regions in PDF point coordinates, with per-edge padding (in pts).
# Asymmetric padding handles cases where a label sits adjacent to the
# masked region (so we don't clip text). The form uses Word table cell
# borders for fillable lines rather than underscore characters, so masks
# cover the empty spaces inside the cells where the user would have written.
# Format: (x0, y0, x1, y1, pad_left, pad_top, pad_right, pad_bot, label)
MASK_REGIONS_PT = [
    # ===== Cell 2: "I, ___ authorise the performance upon ___ of the following operation:" =====
    # Row 1: blank between "I," (ends ~71.5) and "authorise" (starts 361.2). Underline at
    # cell row bottom. Italic caption "(myself ...)" sits BELOW row 2 inside the cell so
    # row 1's mask must NOT extend down to it. Row 1 has only this single fillable line.
    ( 72.0, 168.0, 360.0, 183.5, 0, 0, 0, 0, 'I-name blank'),
    # Row 2: blank from cell-left to "of" (starts 361.2). Italic caption "(myself or name
    # of patient and relationship)" sits at y=212.9..222.8 — DO NOT mask below 212.
    ( 65.5, 197.0, 360.0, 211.5, 0, 0, 0, 0, 'patient-name blank'),

    # ===== Cell 4: "(state procedure precisely)" — fillable area above the italic caption =====
    # The italic caption "(state procedure precisely)" sits at y=305.9..315.9. The fillable
    # space is the region above it — cell rows above are largely empty. Mask y=246..303.
    ( 65.5, 246.0, 530.0, 303.0, 0, 0, 0, 0, 'procedure blank'),

    # ===== Cell 7 (lower text + signatures): =====
    # "Where applicable:" panel — italic header at y_pt≈482, two checkbox rows
    # spanning y_pt≈501..540. Wipe the whole block (cell border just below
    # the foot-image cell at y≈480 down to the horizontal divider above
    # "I consent to the administration..." at y≈555). Native controls
    # (italic Label + 2× CheckBox + 2× wrapping Label) replace the content.
    ( 60.0, 480.0, 540.0, 555.0, 0, 0, 0, 0, 'Where applicable: panel (entire)'),

    # Patient Signed/Date row: labels "Signed:" (ends 94.8), "Date:" (starts 339.8, ends 361.7).
    # Underline is at PDF y_pt = 666 (bottom of the cell row). Mask must include the line itself.
    (100.0, 655.0, 339.0, 668.0, 0, 0, 0, 0, 'patient signature line'),
    (365.0, 655.0, 535.0, 668.0, 0, 0, 0, 0, 'patient signature date'),

    # Witness row: "Witness:" (ends 100.5) — mask from x=105 to leave a gap from the colon.
    # Underline is at PDF y_pt = 696.8.
    (105.0, 680.0, 339.0, 698.0, 0, 0, 0, 0, 'witness line'),
    (365.0, 680.0, 535.0, 698.0, 0, 0, 0, 0, 'witness date'),

    # Podiatrist row: "Signed:" label at y=734.4..744.3 — same baseline as the underlines.
    # Below the label/underline is the italic caption row "(Podiatrist- Name in block letters)
    # / Signature / Date" at y=746.7..756.7. The example "04/09/21" date in the source PDF
    # is rendered as a graphic (not extracted text) at y_px≈972..981 = y_pt≈729..736 — i.e.,
    # ABOVE the underline at y_pt=744. So masks need to start at y=727 to cover it.
    # The underlines themselves are at y_pt=744, so mask must extend to y=746.
    (100.0, 727.0, 297.0, 746.0, 0, 0, 0, 0, 'podiatrist name line'),
    (302.0, 727.0, 425.0, 746.0, 0, 0, 0, 0, 'podiatrist signature line'),
    # Date column: cover from above-the-underline (where 04/09/21 example sits) down to
    # just before the "Date" italic caption (which starts at y=746.7).
    (430.0, 727.0, 535.0, 746.0, 0, 0, 0, 0, 'podiatrist date + example "04/09/21"'),
]


def regenerate(pdf_path: Path, out_path: Path) -> None:
    """Rasterize the PDF, mask the regions, save as PNG."""
    if not shutil.which('pdftoppm'):
        sys.exit("pdftoppm not found on PATH. Install poppler-utils.")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / 'page'
        subprocess.run(
            ['pdftoppm', '-png', '-r', '96', str(pdf_path), str(prefix)],
            check=True,
        )
        rasters = sorted(Path(td).glob('page*.png'))
        if not rasters:
            sys.exit("pdftoppm produced no output.")
        if len(rasters) > 1:
            print(f"Note: PDF has {len(rasters)} pages; using only page 1.")

        img = Image.open(rasters[0]).convert('RGB')

    draw = ImageDraw.Draw(img)
    for x0, y0, x1, y1, pl, pt, pr, pb, label in MASK_REGIONS_PT:
        px0 = (x0 - pl) * SCALE
        py0 = (y0 - pt) * SCALE
        px1 = (x1 + pr) * SCALE
        py1 = (y1 + pb) * SCALE
        draw.rectangle([px0, py0, px1, py1], fill=(255, 255, 255))

    img.save(out_path, 'PNG', optimize=True)
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes, {img.size[0]}x{img.size[1]})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('pdf', type=Path, help='source PDF path')
    p.add_argument('--out', type=Path, default=None,
                   help='output PNG path (default: assets/podiatry_consent_background.png)')
    args = p.parse_args()

    if args.out is None:
        args.out = Path(__file__).resolve().parent / 'assets' / 'podiatry_consent_background.png'
    regenerate(args.pdf, args.out)


if __name__ == '__main__':
    main()
