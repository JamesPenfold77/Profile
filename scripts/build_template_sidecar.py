#!/usr/bin/env python3
"""Regenerate the base64 sidecar for the Intrahealth document template.

The sidecar exists because some binary-fetch transport layers (notably the
GitHub MCP `get_file_contents` tool) UTF-8-decode binary file content and
permanently corrupt every byte >= 0x80. Storing the template as base64 text
in the repo lets it travel through any text-only or text-coerced channel
without loss.

Usage:
    python3 scripts/build_template_sidecar.py docs/Intrahealth_Document_Template.docx

Writes the sidecar alongside the source as <name>.docx.b64.

Run this after editing the .docx. The .docx file is the source of truth;
the sidecar is regenerated from it.
"""

import argparse
import base64
import hashlib
import sys
from pathlib import Path

SENTINEL = "<<<BASE64_PAYLOAD_BEGINS_BELOW>>>"
LINE_WIDTH = 76


def build_sidecar(docx_path: Path) -> Path:
    binary = docx_path.read_bytes()
    sha256 = hashlib.sha256(binary).hexdigest()

    b64 = base64.b64encode(binary).decode("ascii")
    wrapped = "\n".join(b64[i:i + LINE_WIDTH] for i in range(0, len(b64), LINE_WIDTH))

    header = f"""# Intrahealth Document Template - base64 sidecar
#
# Source-of-truth template stored as base64-encoded text so it can travel
# through binary-hostile transport layers (e.g. tools that UTF-8-decode
# binary file content and corrupt bytes >= 0x80).
#
# To decode, use scripts/decode_template_sidecar.py - or, in Python, split
# this file on the sentinel marker that appears after this header block, then
# base64.b64decode() the payload that follows it.
#
# To regenerate after editing the .docx:
#     python3 scripts/build_template_sidecar.py {docx_path}
#
# Original size: {len(binary)} bytes
# SHA-256:       {sha256}
#
{SENTINEL}
"""

    sidecar_path = docx_path.with_suffix(docx_path.suffix + ".b64")
    sidecar_path.write_text(header + wrapped + "\n", encoding="ascii")

    # Verify round-trip
    text = sidecar_path.read_text(encoding="ascii")
    payload = text.split(SENTINEL, 1)[1]
    decoded = base64.b64decode(payload)
    if decoded != binary:
        sys.exit(f"ERROR: round-trip verification failed for {sidecar_path}")
    if hashlib.sha256(decoded).hexdigest() != sha256:
        sys.exit(f"ERROR: SHA-256 mismatch after round-trip for {sidecar_path}")

    return sidecar_path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("docx", type=Path, help="Path to the source .docx file")
    args = parser.parse_args()

    if not args.docx.is_file():
        sys.exit(f"ERROR: not a file: {args.docx}")
    if args.docx.suffix.lower() != ".docx":
        sys.exit(f"ERROR: expected a .docx file, got: {args.docx}")

    sidecar = build_sidecar(args.docx)
    binary_size = args.docx.stat().st_size
    sidecar_size = sidecar.stat().st_size
    print(f"Wrote sidecar: {sidecar}")
    print(f"  source:  {binary_size} bytes")
    print(f"  sidecar: {sidecar_size} bytes ({sidecar_size / binary_size:.2f}x)")
    print(f"  round-trip verified: byte-identical and SHA-256 match")


if __name__ == "__main__":
    main()
