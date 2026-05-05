"""
Declarative form layout for CDO Form generation.

A FormLayout is a list of LayoutItem objects positioned in DFM pixel
coordinates (the NoteBook's coordinate system, where (0,0) is top-left of
the visible canvas). The DFM writer emits these as object positions.

Coordinate conversion (PDF points → DFM pixels) is the responsibility of
the per-form layout module, not this module — it varies by form / DPI / page.

Supported control types are anchored on what the minimal sample's DFM
demonstrates (TICDOLabel, TICDOEdit (with date variant), TICDOMemo,
TICDORichEdit, TICDOSignature, TICDOCheckBox, TICDORadioButton, TICDOImage),
plus the markup control TISliceImageEditor for click/draw markup over an image.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Rect:
    """Rectangle in DFM pixel coordinates (origin top-left, y increases down)."""
    x: float
    y: float
    w: float
    h: float


@dataclass
class LayoutItem:
    """Base class for all layout elements."""
    rect: Rect
    name: str  # DFM component name; must be a valid Pascal identifier


@dataclass
class Label(LayoutItem):
    """Static text — TICDOLabel."""
    text: str
    font_size: int = 10
    bold: bool = False
    italic: bool = False
    word_wrap: bool = False
    auto_size: bool = True


@dataclass
class Edit(LayoutItem):
    """Single-line text input — TICDOEdit."""
    hri: int = 0
    tab_order: int = 0
    label: str = ''


@dataclass
class DateEdit(LayoutItem):
    """Date input — TICDOEdit with EditType=edtyDate, EditKind=edkdDate."""
    hri: int = 0
    tab_order: int = 0
    label: str = ''


@dataclass
class Memo(LayoutItem):
    """Multi-line plain text — TICDOMemo."""
    tab_order: int = 0


@dataclass
class RichEdit(LayoutItem):
    """RTF rich-text input — TICDORichEdit."""
    tab_order: int = 0


@dataclass
class Signature(LayoutItem):
    """Signature pad — TICDOSignature."""
    hri: int = 0
    tab_order: int = 0
    label: str = ''


@dataclass
class CheckBox(LayoutItem):
    """Boolean checkbox — TICDOCheckBox."""
    caption: str = ''
    hri: int = 0
    tab_order: int = 0


@dataclass
class RadioButton(LayoutItem):
    """Radio button — TICDORadioButton."""
    caption: str = ''
    group: str = 'rbGroup'
    hri: int = 0
    tab_order: int = 0


@dataclass
class Image(LayoutItem):
    """Raster overlay — TICDOImage. image_path is a PNG on disk."""
    image_path: str = ''
    stretch: bool = True
    proportional: bool = True


@dataclass
class SliceImageEditor(LayoutItem):
    """
    Markup canvas — TISliceImageEditor.

    A drawable image-annotation control. The user can mark up the area with
    pen, line, rect, ellipse, label, etc. via the toolbar. Used here as
    transparent overlays positioned over portions of a background image
    (e.g. each foot diagram in a podiatry consent form), so the user can
    indicate areas of interest by drawing on top of them.

    No image is embedded in the DFM by this control type — the property
    layout matches the minimal sample's blank-instance template. If a
    pre-loaded background is needed for the slice itself (rather than
    relying on a form-level image underlay), it must be loaded at runtime
    via the COM API (ISeBackgroundImage.LoadFromFile).
    """
    tab_order: int = 0
    show_toolbar: bool = True
    show_hint: bool = True


@dataclass
class FormLayout:
    """Top-level form description.

    Two sets of dimensions:
      - client_width / client_height: the visible window/viewport (DFM
        ClientWidth / ClientHeight).
      - notebook_width / notebook_height: the scrollable canvas inside the
        NoteBook. Larger than the client area when the form's content
        exceeds what fits on screen.
    """
    form_name: str
    caption: str
    concept_code: str
    concept_display_name: str
    folder_category: str
    form_def_id: int

    client_width: int = 657
    client_height: int = 630
    notebook_width: int = 1519
    notebook_height: int = 629

    items: list[LayoutItem] = field(default_factory=list)

    def add(self, item: LayoutItem) -> LayoutItem:
        self.items.append(item)
        return item
