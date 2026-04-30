"""
Regenerate the masked background PNG for the Pelvic Floor consent form.

Rasterizes the source PDF at 96 DPI, then paints white over the page-number
"1" and the 9 underscore lines (Names / Signatures / Dates). Output goes to
assets/pelvic_floor_background.png next to the form module.

Usage:
    python -m generators.pdf_to_jfa.forms.regenerate_pelvic_floor_background \\
        path/to/Form_4023I_Client_Consent_Invasive_Procedure__Pelvic_Floor_.pdf

Requires: pdftoppm (poppler-utils) on PATH, Pillow installed.

The mask region coordinates were determined empirically by parsing the source
PDF with pdfplumber. They are hard-coded here because:
  1. The source PDF doesn't change.
  2. Re-running pdfplumber adds a dependency (pdfplumber is heavy).
If the source PDF is replaced, re-detect the regions with pdfplumber and
update the MASK_REGIONS_PT table below.
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
# masked region (e.g. the Signature underscore line ends just before the
# "Date:" label, so we don't pad the right edge of those rows).
# Format: (x0, y0, x1, y1, pad_left, pad_top, pad_right, pad_bot, label)
MASK_REGIONS_PT = [
    (533.6, 812.1, 538.6, 822.1, 2, 2, 2, 2, 'page number 1'),
    ( 98.9, 521.2, 531.1, 531.7, 2, 2, 2, 2, 'Client Name'),
    (115.9, 557.4, 390.4, 568.0, 2, 2, 0, 2, 'Client Signature'),
    (418.3, 557.4, 529.4, 568.0, 0, 2, 2, 2, 'Client Date'),
    (124.1, 593.5, 532.9, 604.1, 2, 2, 2, 2, 'Chaperone Name'),
    (141.0, 629.8, 398.0, 640.3, 2, 2, 0, 2, 'Chaperone Signature'),
    (425.9, 629.8, 536.9, 640.3, 0, 2, 2, 2, 'Chaperone Date'),
    (114.5, 666.0, 535.3, 676.6, 2, 2, 2, 2, 'Clinician Name'),
    (128.7, 702.3, 397.3, 712.8, 2, 2, 0, 2, 'Clinician Signature'),
    (425.3, 702.3, 536.3, 712.8, 0, 2, 2, 2, 'Clinician Date'),
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
                   help='output PNG path (default: assets/pelvic_floor_background.png)')
    args = p.parse_args()

    if args.out is None:
        args.out = Path(__file__).resolve().parent / 'assets' / 'pelvic_floor_background.png'
    regenerate(args.pdf, args.out)


if __name__ == '__main__':
    main()
