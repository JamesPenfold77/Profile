#!/usr/bin/env python3
"""Decode the Intrahealth document template sidecar back to a .docx file.

Inverse of build_template_sidecar.py. Used when the .docx binary is needed
on disk but only the sidecar is available (e.g. when the binary cannot be
fetched cleanly through a binary-hostile transport).

Usage:
    python3 scripts/decode_template_sidecar.py docs/Intrahealth_Document_Template.docx.b64
    python3 scripts/decode_template_sidecar.py SIDECAR --out /path/to/output.docx

Without --out, the .docx is written next to the sidecar with the .b64 suffix
stripped. Verifies the SHA-256 declared in the sidecar header against the
decoded bytes.
"""

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

SENTINEL = "<<<BASE64_PAYLOAD_BEGINS_BELOW>>>"


def decode_sidecar(sidecar_path: Path, out_path: Path) -> None:
    text = sidecar_path.read_text(encoding="ascii")

    if SENTINEL not in text:
        sys.exit(f"ERROR: sentinel not found in sidecar \u2014 file may be corrupt or "
                 f"a different format: {sidecar_path}")

    header, payload = text.split(SENTINEL, 1)

    # Pull the declared SHA-256 from the header so we can verify the round-trip.
    declared_sha = None
    m = re.search(r"SHA-256:\s+([0-9a-f]{64})", header)
    if m:
        declared_sha = m.group(1)

    binary = base64.b64decode(payload)
    actual_sha = hashlib.sha256(binary).hexdigest()

    if declared_sha and declared_sha != actual_sha:
        sys.exit(f"ERROR: SHA-256 mismatch \u2014 sidecar may be corrupt.\n"
                 f"  declared: {declared_sha}\n"
                 f"  actual:   {actual_sha}")

    out_path.write_bytes(binary)
    print(f"Decoded {sidecar_path} -> {out_path} ({len(binary)} bytes)")
    if declared_sha:
        print(f"  SHA-256 verified: {actual_sha}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sidecar", type=Path, help="Path to the .b64 sidecar")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output .docx path (default: sidecar with .b64 suffix removed)")
    args = parser.parse_args()

    if not args.sidecar.is_file():
        sys.exit(f"ERROR: not a file: {args.sidecar}")

    if args.out is None:
        if args.sidecar.suffix != ".b64":
            sys.exit("ERROR: sidecar does not end in .b64 \u2014 please supply --out explicitly")
        args.out = args.sidecar.with_suffix("")

    decode_sidecar(args.sidecar, args.out)


if __name__ == "__main__":
    main()
