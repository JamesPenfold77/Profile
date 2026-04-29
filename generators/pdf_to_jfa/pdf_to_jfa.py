"""
CLI driver: build a JFA file from a declarative form layout.

Usage:
    python -m generators.pdf_to_jfa.pdf_to_jfa <form_module> <out_jfa>

Example:
    python -m generators.pdf_to_jfa.pdf_to_jfa hello_world output/HelloWorld.jfa
"""
from __future__ import annotations
import importlib
import sys
from .dfm_writer import write_dfm
from .jfa_writer import write_jfa


def generate(form_module_name: str, out_path: str) -> None:
    mod = importlib.import_module(f'generators.pdf_to_jfa.forms.{form_module_name}')
    layout = mod.build_layout()

    dfm_text = write_dfm(layout)
    jfa_text = write_jfa(layout, dfm_text)

    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        f.write(jfa_text)

    print(f"Wrote {out_path}")
    print(f"  Form: {layout.caption}")
    print(f"  Concept: {layout.concept_code}")
    print(f"  Folder: {layout.folder_category}")
    print(f"  Items: {len(layout.items)}")
    print(f"  DFM size: {len(dfm_text)} chars")
    print(f"  JFA size: {len(jfa_text)} chars")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2])
