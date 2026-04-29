"""
JFA file writer.

Emits the three record types established in the prior sample analysis:

  HEAD (15 fields)  — file-wide header
  LNVR (6 fields)   — line-version block declaring (OBSV v2, SHRS v2)
  OBSV (44 fields)  — observation rows; class code in field [2] is the type discriminator

For this layout-only first pass we emit:
  - 1 HEAD line
  - 1 LNVR line
  - 2 x OBSV class 100503 (Accession + Provider context)
  - 1 x OBSV class 100502 (the form definition, carrying the DFM in field [13])

Per scope, no per-control field rows (100511/100517/100519) yet. The form
will import and render visually; the data side is added later.
"""
from __future__ import annotations
from datetime import datetime
from .layout import FormLayout
from .jaffa_encoding import encode as jaffa_encode


# Open question from prior analysis: the 'zZ.1Bx'-style tokens in OBSV fields
# [7] and [8]. From the sample we observed values like 'z..0K' and 'zZ.1BD'.
# Their meaning hasn't been confirmed against source.
SYSTEM_PARENT_TOKEN = 'z..00'   # placeholder, to confirm against sample
NAMESPACE_MARKER = 'IH'

# OBSV class codes (confirmed in prior analysis)
CLS_HEADER_OBS    = '100503'    # Accession / Provider context rows
CLS_FORM_DEF      = '100502'    # The CDO form definition (carries DFM in [13])


def _obsv_row(fields: list[str]) -> str:
    """Build a single OBSV row from 44 fields, jaffa-encoded and comma-joined."""
    if len(fields) != 44:
        fields = list(fields) + [''] * (44 - len(fields))
    return ','.join(jaffa_encode(f) for f in fields)


def _build_head(now: datetime) -> str:
    """The 15-field HEAD line."""
    fields = [
        'HEAD', '3', '1', 'OBSV', 'CDO Observations', 'Intrahealth',
        now.strftime('%d/%m/%Y'),
        now.strftime('%H.%M'),
        'M', 'F', '', '', '', '', '',
    ]
    return ','.join(jaffa_encode(f) for f in fields)


def _build_lnvr() -> str:
    """The LNVR line: declares per-record-type versions."""
    fields = ['LNVR', '3', 'OBSV', '2', 'SHRS', '2']
    return ','.join(jaffa_encode(f) for f in fields)


def _build_accession_row(layout: FormLayout, accession_id: int) -> str:
    """First 100503 row: the Accession context."""
    nm = f'NM={layout.concept_display_name}'
    fields = ['OBSV', '2', CLS_HEADER_OBS,
              str(accession_id),
              '',
              '0',
              NAMESPACE_MARKER,
              SYSTEM_PARENT_TOKEN,
              '',
              nm]
    return _obsv_row(fields)


def _build_provider_row(layout: FormLayout, provider_id: int, accession_id: int) -> str:
    """Second 100503 row: the Provider context, references the Accession."""
    nm = 'NM=Provider'
    fields = ['OBSV', '2', CLS_HEADER_OBS,
              str(provider_id),
              str(accession_id),
              '0',
              NAMESPACE_MARKER,
              SYSTEM_PARENT_TOKEN,
              '',
              nm]
    return _obsv_row(fields)


def _build_form_def_row(layout: FormLayout, dfm_text: str) -> str:
    """The 100502 row carrying the form definition.

    Field [3]  = form_def_id
    Field [7]  = form's concept code (e.g. 'z..UB')
    Field [9]  = NM=, FD=, EEML=T attributes
    Field [13] = the entire DFM, jaffa-encoded
    """
    nm_parts = [
        f'NM={layout.concept_display_name}',
        f'FD={layout.form_def_id}',
        'EEML=T',
    ]
    nm = ','.join(nm_parts)
    fields = [
        'OBSV', '2', CLS_FORM_DEF,
        str(layout.form_def_id),
        '',                              # [4] form-def has no parent
        '0',                             # [5] sequence
        NAMESPACE_MARKER,                # [6]
        layout.concept_code,             # [7] form concept code
        SYSTEM_PARENT_TOKEN,             # [8]
        nm,                              # [9] NM=,FD=,EEML=T
        '',                              # [10]
        '',                              # [11]
        '',                              # [12]
        dfm_text,                        # [13] DFM
        '',                              # [14]
    ]
    while len(fields) < 44:
        fields.append('')
    return ','.join(jaffa_encode(f) for f in fields)


def write_jfa(layout: FormLayout, dfm_text: str,
              accession_id: int = 90000001,
              provider_id: int = 90000002,
              now: datetime | None = None) -> str:
    """Build the full JFA file content.

    Returns:
        The complete JFA file content as a string. Uses CRLF line endings,
        matching Profile's writer.
    """
    if now is None:
        now = datetime.now()

    lines = [
        _build_head(now),
        _build_lnvr(),
        _build_accession_row(layout, accession_id),
        _build_provider_row(layout, provider_id, accession_id),
        _build_form_def_row(layout, dfm_text),
    ]
    return '\r\n'.join(lines) + '\r\n'
