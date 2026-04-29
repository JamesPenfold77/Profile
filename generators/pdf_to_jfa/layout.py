"""
Declarative form layout for CDO Form generation.

A FormLayout is a list of LayoutItem objects, each describing a control or
static element to place on the form. Coordinates are in PDF points (origin at
top-left). The DFM writer converts these to DFM client pixels using the
configured DPI scale.

Subclassing notes for future forms:
- Image: arbitrary raster overlays (logos, header bands, full-page backgrounds).
- Label: read-only static text (rebuilt from PDF text content).
- Edit, DateEdit, Signature: input controls with HRI assignments.

This module is form-agnostic; per-form layouts live under generators/pdf_to_jfa/forms/.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# --- Geometry -----------------------------------------------------------------

@dataclass
class Rect:
    """Rectangle in PDF points (origin top-left, y increasing downward)."""
    x: float
    y: float
    w: float
    h: float

    @classmethod
    def from_pdf_box(cls, x0: float, top: float, x1: float, bottom: float) -> 'Rect':
        return cls(x=x0, y=top, w=x1 - x0, h=bottom - top)


# --- Layout items -------------------------------------------------------------

@dataclass
class LayoutItem:
    """Base class for all layout elements."""
    rect: Rect
    name: str  # DFM component name (must be a valid Pascal identifier)


@dataclass
class Label(LayoutItem):
    """Static text — TICDOLabel."""
    text: str
    font_size: int = 10
    bold: bool = False
    italic: bool = False
    word_wrap: bool = True
    auto_size: bool = False  # if False, label is constrained to rect


@dataclass
class Image(LayoutItem):
    """Raster overlay — TICDOImage. The image_path is a PNG on disk; the writer
    base64-encodes its bytes into the DFM."""
    image_path: str
    stretch: bool = True
    proportional: bool = True


@dataclass
class Edit(LayoutItem):
    """Single-line text input — TICDOEdit."""
    hri: int
    label: str = ''      # display name for the OBSV NM= attribute
    tab_order: int = 0
    max_length: int = 0  # 0 = no limit


@dataclass
class DateEdit(LayoutItem):
    """Date input — TICDODateEdit (or TICDOEdit with mask if that class doesn't exist).
    The writer chooses the class name based on the configured Profile dialect."""
    hri: int
    label: str = ''
    tab_order: int = 0


@dataclass
class Signature(LayoutItem):
    """Signature pad — TICDOSignature (confirmed in prior sample analysis)."""
    hri: int
    label: str = ''
    tab_order: int = 0


# --- Form-level container -----------------------------------------------------

@dataclass
class FormLayout:
    """Top-level form description."""
    form_name: str
    caption: str
    page_width_pt: float
    page_height_pt: float
    concept_code: str
    concept_display_name: str
    folder_category: str
    form_def_id: int
    items: list[LayoutItem] = field(default_factory=list)

    def add(self, item: LayoutItem) -> LayoutItem:
        self.items.append(item)
        return item

    def input_items(self) -> list[LayoutItem]:
        """Items that have an HRI and produce an OBSV field row."""
        return [it for it in self.items if isinstance(it, (Edit, DateEdit, Signature))]
