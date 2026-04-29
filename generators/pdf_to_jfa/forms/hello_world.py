"""
Hello World form — the simplest possible CDO form, used to validate that
the JFA generator produces a file that Profile imports cleanly.

The form contains a single TICDOLabel reading "Hello World". No input
controls, no embedded images, no termset bindings.

Concept: z..UB ("Hello World" — re-using the form-template concept)
Folder: NZDF (inherited verbatim from the minimal sample fixture)
"""
from __future__ import annotations
from ..layout import FormLayout, Rect, Label


def build_layout(form_def_id: int = 90000001) -> FormLayout:
    """Construct the FormLayout for the Hello World test form."""
    layout = FormLayout(
        form_name='HelloWorld',
        caption='Hello World',
        concept_code='z..UB',
        concept_display_name='Hello World',
        folder_category='NZDF',
        form_def_id=form_def_id,
        client_width=657,
        client_height=630,
        notebook_width=1519,
        notebook_height=629,
    )

    layout.add(Label(
        name='lblHello',
        rect=Rect(58, 33, 80, 13),
        text='Hello World',
    ))

    return layout
