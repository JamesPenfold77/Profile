"""
DFM writer for CDO Forms.

Emits a Delphi text DFM matching the structure of the minimal sample
(Form_Template_-_Form.jfa). Boilerplate (root form properties, macros block,
NoteBook + TPage + Page_1 prelude, closing 'end' chain) comes from
fixtures.py — those are byte-precise lifts from the working sample.

Per-control emitters write the minimum DFM property set observed in working
samples for each control type.
"""
from __future__ import annotations
from io import StringIO
from . import fixtures
from .layout import (
    FormLayout, LayoutItem, Label, Edit, DateEdit, Memo, RichEdit,
    Signature, CheckBox, RadioButton, Image, SliceImageEditor, Rect,
)


# DFM image-stream prefix.
# Consent-for-Health-Care sample uses TdxPNGImage (DevExpress) for embedded PNGs,
# byte prefix 0B 'TdxPNGImage'. Standard Delphi TPngImage would be 09 'TPngImage'.
IMAGE_STREAM_PREFIX_HEX = '0B546478504E47496D616765'  # length(11) + 'TdxPNGImage'


# TISliceImageEditor toolbar button set, lifted verbatim from the minimal
# sample's empty-instance template. Profile's slice editor renders a toolbar
# with these tools when ToolBarVisible is True.
SLICE_EDITOR_TOOLBAR_TOOLS = (
    '[ttUndefined, ttArrow, ttPen, ttLine, ttRect, ttRoundRect, ttEllipse, '
    'ttLabel, ttEraser, ttColour, ttZoom, ttOpenImage, ttDSImage, ttStamp, '
    'ttImage, ttArrowLine, ttTwoArrowLine, ttTriangleVert, ttTriangleHoriz, '
    'ttOpenBGImage, ttRemoveBGImage]'
)


def _quote(s: str) -> str:
    """Quote a string for DFM output. Doubles embedded single quotes."""
    return "'" + s.replace("'", "''") + "'"


class _Buf:
    """Simple CRLF-aware text buffer."""
    def __init__(self) -> None:
        self.io = StringIO()

    def line(self, indent: int, text: str = '') -> None:
        if text:
            self.io.write('  ' * indent)
            self.io.write(text)
        self.io.write('\r\n')

    def write_raw(self, s: str) -> None:
        self.io.write(s)

    def value(self) -> str:
        return self.io.getvalue()


def _emit_label(b: _Buf, item: Label) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDOLabel')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    if not item.auto_size:
        b.line(5, 'AutoSize = False')
    b.line(5, f'Caption = {_quote(item.text)}')
    if item.bold or item.italic:
        styles = []
        if item.bold:
            styles.append('fsBold')
        if item.italic:
            styles.append('fsItalic')
        b.line(5, 'Font.Charset = DEFAULT_CHARSET')
        b.line(5, "Font.Name = 'Arial'")
        b.line(5, f'Font.Size = {item.font_size}')
        b.line(5, f'Font.Style = [{", ".join(styles)}]')
        b.line(5, 'ParentFont = False')
    if item.word_wrap:
        b.line(5, 'WordWrap = True')
    b.line(5, 'TechTranslation = False')
    b.line(5, 'Modified = True')
    b.line(4, 'end')


def _emit_edit(b: _Buf, item) -> None:
    """Handles both Edit and DateEdit (DateEdit adds date-specific properties)."""
    r = item.rect
    b.line(4, f'object {item.name}: TICDOEdit')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    if isinstance(item, DateEdit):
        b.line(5, 'ShowButton = ShowBtnFocus')
        b.line(5, 'ShowButtonStyle = btnStDown')
        b.line(5, 'EditType = edtyDate')
    b.line(5, 'DefaultTabHandle = True')
    b.line(5, 'AllowTypingTemplates = True')
    b.line(5, 'CharCase = ecNormal')
    b.line(5, f'TabOrder = {item.tab_order}')
    b.line(5, 'Visible = True')
    b.line(5, 'ShowHint = False')
    if item.hri:
        b.line(5, f'HRI = {item.hri}')
    if isinstance(item, DateEdit):
        b.line(5, 'EditKind = edkdDate')
    b.line(4, 'end')


def _emit_memo(b: _Buf, item: Memo) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDOMemo')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    b.line(5, f'TabOrder = {item.tab_order}')
    b.line(4, 'end')


def _emit_richedit(b: _Buf, item: RichEdit) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDORichEdit')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    b.line(5, f'TabOrder = {item.tab_order}')
    b.line(5, 'InputFormat = ifRTF')
    b.line(5, 'OutputFormat = ofRTF')
    b.line(4, 'end')


def _emit_signature(b: _Buf, item: Signature) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDOSignature')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    b.line(5, 'Center = True')
    b.line(5, 'Proportional = True')
    b.line(5, f'SignaturePromptText = {_quote(item.name)}')
    b.line(5, 'WhenCaptureSignature = wcsWhenPrinting')
    if item.hri:
        b.line(5, f'HRI = {item.hri}')
    b.line(4, 'end')


def _emit_checkbox(b: _Buf, item: CheckBox) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDOCheckBox')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    if item.caption:
        b.line(5, f'Caption = {_quote(item.caption)}')
    b.line(5, f'TabOrder = {item.tab_order}')
    if item.hri:
        b.line(5, f'HRI = {item.hri}')
    b.line(5, "CheckedValue = 'TRUE'")
    b.line(5, "UncheckedValue = 'FALSE'")
    b.line(4, 'end')


def _emit_radio(b: _Buf, item: RadioButton) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDORadioButton')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    if item.caption:
        b.line(5, f'Caption = {_quote(item.caption)}')
    b.line(5, f'TabOrder = {item.tab_order}')
    if item.hri:
        b.line(5, f'HRI = {item.hri}')
    b.line(5, "CheckedValue = 'TRUE'")
    b.line(5, f'Group = {_quote(item.group)}')
    b.line(4, 'end')


def _emit_image(b: _Buf, item: Image) -> None:
    r = item.rect
    b.line(4, f'object {item.name}: TICDOImage')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    if item.image_path:
        with open(item.image_path, 'rb') as f:
            png_bytes = f.read()
        full_hex = IMAGE_STREAM_PREFIX_HEX + png_bytes.hex().upper()
        b.line(5, 'Picture.Data = {')
        for i in range(0, len(full_hex), 64):
            b.line(6, full_hex[i:i+64])
        b.line(5, '}')
    if item.stretch:
        b.line(5, 'Stretch = True')
    b.line(4, 'end')


def _emit_slice_editor(b: _Buf, item: SliceImageEditor) -> None:
    """Emit a TISliceImageEditor — a markup canvas the user can draw on.

    Property set lifted from the minimal sample's blank-instance template
    (TISliceImageEditor1 in Form Template - Form.jfa). No image data is
    embedded — Profile loads any background image at runtime via the
    BackgroundImage COM API or the toolbar's ttOpenBGImage tool.
    """
    r = item.rect
    b.line(4, f'object {item.name}: TISliceImageEditor')
    b.line(5, f'Left = {int(r.x)}')
    b.line(5, f'Top = {int(r.y)}')
    b.line(5, f'Width = {int(r.w)}')
    b.line(5, f'Height = {int(r.h)}')
    b.line(5, 'ParentShowHint = False')
    b.line(5, f'ShowHint = {"True" if item.show_hint else "False"}')
    b.line(5, 'DefaultFont.Charset = ANSI_CHARSET')
    b.line(5, 'DefaultFont.Color = clWindowText')
    b.line(5, 'DefaultFont.Height = -11')
    b.line(5, "DefaultFont.Name = 'Tahoma'")
    b.line(5, 'DefaultFont.Style = []')
    b.line(5, 'DefaultBrush.Color = clBlack')
    b.line(5, f'DefaultToolBarSettings.ToolTypes = {SLICE_EDITOR_TOOLBAR_TOOLS}')
    b.line(5, 'DefaultToolBarSettings.DefaultTool = ttArrow')
    b.line(5, f'DefaultToolBarSettings.ToolBarVisible = {"True" if item.show_toolbar else "False"}')
    b.line(5, 'DefaultStamp.Style = gssRect')
    b.line(5, 'DefaultStamp.Size = 14')
    b.line(5, 'DefaultStamp.Color = clBlack')
    b.line(4, 'end')


def _emit_item(b: _Buf, item: LayoutItem) -> None:
    if isinstance(item, Label):
        _emit_label(b, item)
    elif isinstance(item, (Edit, DateEdit)):
        _emit_edit(b, item)
    elif isinstance(item, Memo):
        _emit_memo(b, item)
    elif isinstance(item, RichEdit):
        _emit_richedit(b, item)
    elif isinstance(item, Signature):
        _emit_signature(b, item)
    elif isinstance(item, CheckBox):
        _emit_checkbox(b, item)
    elif isinstance(item, RadioButton):
        _emit_radio(b, item)
    elif isinstance(item, Image):
        _emit_image(b, item)
    elif isinstance(item, SliceImageEditor):
        _emit_slice_editor(b, item)
    else:
        raise TypeError(f'Unsupported layout item: {type(item).__name__}')


def write_dfm(layout: FormLayout) -> str:
    """Build the full DFM text for a CDO Form.

    Splices verbatim fixtures (root form props, macros block, NoteBook prelude,
    closing 'end' chain) around per-control emissions.
    """
    b = _Buf()

    b.write_raw(fixtures.ROOT_FORM_PROPS.format(
        caption=layout.caption.replace("'", "''"),
        client_w=int(layout.client_width),
        client_h=int(layout.client_height),
    ))

    b.write_raw(fixtures.MACROS_BLOCK)

    b.write_raw(fixtures.NOTEBOOK_PRELUDE.format(
        nb_w=int(layout.notebook_width),
        nb_h=int(layout.notebook_height),
    ))

    for item in layout.items:
        _emit_item(b, item)

    b.write_raw(fixtures.DFM_CLOSING)

    return b.value()
