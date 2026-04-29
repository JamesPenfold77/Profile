"""
DFM writer for CDO Forms.

Emits a Delphi text DFM (object IVisualForm: TIVisualForm ... end) with:
  - aNoteBook: TICDONoteBook
    - Page_1: TICDOPanel
      - <controls>: TICDOLabel / TICDOEdit / TICDODateEdit / TICDOSignature / TICDOImage

PDF-to-DFM coordinate conversion:
  PDF points are at 72 DPI. Profile DFM client coordinates are in pixels at
  96 DPI logical (the standard Windows GUI scaling). One PDF point therefore
  maps to 96/72 = 1.3333... DFM pixels. This default holds for the prior
  sample's IVisualForm dimensions; override DPI_SCALE if a sample shows
  otherwise.

Calibration TODO:
  When the sample JFA is available, compare its IVisualForm.ClientWidth /
  ClientHeight to the source page in points, and update DPI_SCALE if needed.
"""
from __future__ import annotations
import base64
from io import StringIO
from .layout import (
    FormLayout, LayoutItem, Label, Edit, DateEdit, Signature, Image, Rect,
)


# 1 PDF point = 1/72 inch; DFM uses 96 DPI logical pixels.
DPI_SCALE = 96.0 / 72.0


def pt_to_px(pt: float) -> int:
    """Convert PDF points to DFM client pixels."""
    return int(round(pt * DPI_SCALE))


# Standard Profile CDO Form macro entry points. The exact names are inferred
# from the prior sample analysis; if a real sample shows different identifiers,
# replace this list.
STANDARD_MACRO_HOOKS = [
    'OnFormShow=',
    'OnFormHide=',
    'OnFormCreate=',
    'OnFormDestroy=',
    'OnFormSave=',
    'OnFormLoad=',
    'OnFormValidate=',
    'OnFieldChange=',
    'OnButtonClick=',
]


class DFMBuilder:
    """Indented text emitter for DFM output."""
    def __init__(self):
        self.buf = StringIO()
        self.depth = 0

    def write(self, line: str = ''):
        if line:
            self.buf.write('  ' * self.depth)
            self.buf.write(line)
        self.buf.write('\r\n')

    def open(self, header: str):
        self.write(header)
        self.depth += 1

    def close(self):
        self.depth -= 1
        self.write('end')

    def value(self) -> str:
        return self.buf.getvalue()


def _quote(s: str) -> str:
    """Quote a string for DFM output. Doubles embedded single quotes."""
    return "'" + s.replace("'", "''") + "'"


def _emit_label(b: DFMBuilder, item: Label):
    x = pt_to_px(item.rect.x); y = pt_to_px(item.rect.y)
    w = pt_to_px(item.rect.w); h = pt_to_px(item.rect.h)
    b.open(f'object {item.name}: TICDOLabel')
    b.write(f'Left = {x}'); b.write(f'Top = {y}')
    b.write(f'Width = {w}'); b.write(f'Height = {h}')
    b.write('AutoSize = True' if item.auto_size else 'AutoSize = False')
    if item.word_wrap:
        b.write('WordWrap = True')
    if '\n' in item.text:
        lines = item.text.split('\n')
        parts = [_quote(ln) for ln in lines]
        b.write(f'Caption = {" + #13#10 + ".join(parts)}')
    else:
        b.write(f'Caption = {_quote(item.text)}')
    style_parts = []
    if item.bold:
        style_parts.append('fsBold')
    if item.italic:
        style_parts.append('fsItalic')
    style_str = '[' + (', '.join(style_parts) if style_parts else '') + ']'
    b.write('Color = clBlack')
    b.write('Font.Charset = DEFAULT_CHARSET')
    b.write("Font.Name = 'Arial'")
    b.write(f'Font.Size = {item.font_size}')
    b.write(f'Font.Style = {style_str}')
    b.write('ParentFont = False')
    b.write('Transparent = True')
    b.close()


def _emit_edit(b: DFMBuilder, item: Edit):
    x = pt_to_px(item.rect.x); y = pt_to_px(item.rect.y)
    w = pt_to_px(item.rect.w); h = pt_to_px(item.rect.h)
    b.open(f'object {item.name}: TICDOEdit')
    b.write(f'Left = {x}'); b.write(f'Top = {y}')
    b.write(f'Width = {w}'); b.write(f'Height = {h}')
    b.write(f'HRI = {item.hri}')
    b.write(f'TabOrder = {item.tab_order}')
    if item.max_length:
        b.write(f'MaxLength = {item.max_length}')
    b.close()


def _emit_date(b: DFMBuilder, item: DateEdit):
    x = pt_to_px(item.rect.x); y = pt_to_px(item.rect.y)
    w = pt_to_px(item.rect.w); h = pt_to_px(item.rect.h)
    # Class name TBC: TICDODateEdit is the natural name. If a real sample
    # uses TICDOEdit + a date mask, swap this here.
    b.open(f'object {item.name}: TICDODateEdit')
    b.write(f'Left = {x}'); b.write(f'Top = {y}')
    b.write(f'Width = {w}'); b.write(f'Height = {h}')
    b.write(f'HRI = {item.hri}')
    b.write(f'TabOrder = {item.tab_order}')
    b.close()


def _emit_signature(b: DFMBuilder, item: Signature):
    x = pt_to_px(item.rect.x); y = pt_to_px(item.rect.y)
    w = pt_to_px(item.rect.w); h = pt_to_px(item.rect.h)
    b.open(f'object {item.name}: TICDOSignature')
    b.write(f'Left = {x}'); b.write(f'Top = {y}')
    b.write(f'Width = {w}'); b.write(f'Height = {h}')
    b.write(f'HRI = {item.hri}')
    b.write(f'TabOrder = {item.tab_order}')
    b.close()


def _emit_image(b: DFMBuilder, item: Image):
    x = pt_to_px(item.rect.x); y = pt_to_px(item.rect.y)
    w = pt_to_px(item.rect.w); h = pt_to_px(item.rect.h)
    with open(item.image_path, 'rb') as f:
        png_bytes = f.read()
    hex_data = png_bytes.hex().upper()

    b.open(f'object {item.name}: TICDOImage')
    b.write(f'Left = {x}'); b.write(f'Top = {y}')
    b.write(f'Width = {w}'); b.write(f'Height = {h}')
    if item.stretch:
        b.write('Stretch = True')
    if item.proportional:
        b.write('Proportional = True')
    # Picture.Data is a Delphi TPngImage stream: length-prefixed class name
    # 'TPngImage' (0x09 + 'TPngImage') followed by the PNG bytes.
    prefix = '0954506E67496D616765'
    full_hex = prefix + hex_data
    full_lines = [full_hex[i:i+64] for i in range(0, len(full_hex), 64)]
    b.open('Picture.Data = {')
    for ln in full_lines:
        b.write(ln)
    b.depth -= 1
    b.write('}')
    b.close()


def _emit_item(b: DFMBuilder, item: LayoutItem):
    if isinstance(item, Label): _emit_label(b, item)
    elif isinstance(item, Edit): _emit_edit(b, item)
    elif isinstance(item, DateEdit): _emit_date(b, item)
    elif isinstance(item, Signature): _emit_signature(b, item)
    elif isinstance(item, Image): _emit_image(b, item)
    else: raise TypeError(f"Unknown layout item: {type(item).__name__}")


def write_dfm(layout: FormLayout) -> str:
    """Build the full DFM text for a CDO Form."""
    client_w = pt_to_px(layout.page_width_pt)
    client_h = pt_to_px(layout.page_height_pt)

    b = DFMBuilder()
    b.open('object IVisualForm: TIVisualForm')
    b.write('Left = 0'); b.write('Top = 0')
    b.write(f'Caption = {_quote(layout.caption)}')
    b.write(f'ClientHeight = {client_h}')
    b.write(f'ClientWidth = {client_w}')
    b.write('Color = clBtnFace')
    b.write('Font.Charset = DEFAULT_CHARSET')
    b.write("Font.Name = 'Arial'")
    b.write('Font.Size = 10')
    b.write('Font.Style = []')
    b.write('OldCreateOrder = False')
    b.write('PixelsPerInch = 96')
    b.write('TextHeight = 13')
    b.write('RepresentationMethod = rmStructuredText')
    b.open('Macros.Strings = (')
    for hook in STANDARD_MACRO_HOOKS:
        b.write(_quote(hook))
    b.depth -= 1
    b.write(')')

    b.open('object aNoteBook: TICDONoteBook')
    b.write('Left = 0'); b.write('Top = 0')
    b.write(f'Width = {client_w}'); b.write(f'Height = {client_h}')
    b.write('Align = alClient')

    b.open('object Page_1: TICDOPanel')
    b.write('Left = 0'); b.write('Top = 0')
    b.write(f'Width = {client_w}'); b.write(f'Height = {client_h}')
    b.write("Caption = 'Page 1'")
    b.write('TabOrder = 0')

    for item in layout.items:
        _emit_item(b, item)

    b.close()  # Page_1
    b.close()  # aNoteBook
    b.close()  # IVisualForm

    return b.value()
