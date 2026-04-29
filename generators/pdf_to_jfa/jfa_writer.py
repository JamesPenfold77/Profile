"""
JFA file writer.

Layout calibrated against the minimal blank-form sample (Form_Template_-_Form.jfa).
The structure is:

  HEAD (15 fields)         tag, "3", "1", "OBSV", "CDO Observations",
                           "Intrahealth", date, time,
                           "M", "", "", "F", "", "", ""
  LNVR (6 fields)          "LNVR", "3", "OBSV", "2", "SHRS", "2"
  OBSV 100503 (44 fields)  context/tenancy row (NZDF) — verbatim from fixtures
  OBSV 100502 (44 fields)  form definition; carries DFM in field [13]

File-level: UTF-8 BOM, CRLF line endings, TAB field separator.

Per-control field rows (100511 / 100517 / 100519) are NOT emitted in this
layout-only first pass.
"""
from __future__ import annotations
from datetime import datetime
from .layout import FormLayout
from .jaffa_encoding import encode as jaffa_encode
from . import fixtures


SEP = '\t'
BOM = '\ufeff'


# Form-def [7]/[8] concept-pair. The minimal sample uses 'z..UB'/'z..UC'
# as the form concept and its paired "form definition" partner concept.
DEFAULT_CONCEPT_PAIR_FOR_UB = ('z..UB', 'z..UC')


def _obsv_row_44(fields: list[str]) -> str:
    """Build a 44-field OBSV row, jaffa-encoded and tab-joined."""
    if len(fields) < 44:
        fields = list(fields) + [''] * (44 - len(fields))
    elif len(fields) > 44:
        raise ValueError(f"OBSV row has {len(fields)} fields, max is 44")
    return SEP.join(jaffa_encode(f) for f in fields)


def _build_head(now: datetime) -> str:
    """The 15-field HEAD line, matching minimal-sample structure exactly."""
    fields = [
        'HEAD', '3', '1', 'OBSV', 'CDO Observations', 'Intrahealth',
        now.strftime('%d/%m/%Y'),
        now.strftime('%H.%M'),
        'M', '', '', 'F', '', '', '',
    ]
    return SEP.join(jaffa_encode(f) for f in fields)


def _build_lnvr() -> str:
    """The 6-field LNVR line."""
    fields = ['LNVR', '3', 'OBSV', '2', 'SHRS', '2']
    return SEP.join(jaffa_encode(f) for f in fields)


def _format_nm_field(name: str, fd_id: str) -> str:
    """Build the NM=,EEML=T,FD=... field [9] for the form-def row.

    NM is wrapped in literal double-quotes if the name contains spaces
    (matching Consent for Health Care sample's "NM=Consent for Health Care").
    Without spaces, no quotes (matching minimal's NM=Form,EEML=T,FD=4474196).
    """
    if ' ' in name:
        nm_part = f'"NM={name}"'
    else:
        nm_part = f'NM={name}'
    return f'{nm_part},EEML=T,FD={fd_id}'


def _build_form_def_row(layout: FormLayout, dfm_text: str,
                        context_row_id: str,
                        concept_pair: tuple[str, str]) -> str:
    """Build the OBSV 100502 form-definition row.

    Matches minimal-sample positions exactly:
      [3]  = form_def_id (synthetic; Profile remaps on import)
      [5]  = '0'
      [6]  = 'IH'
      [7]  = concept_pair[0]   (the form's concept code)
      [8]  = concept_pair[1]   (paired partner concept)
      [9]  = NM=...,EEML=T,FD=<context_row_id>
      [11] = '2147483647'
      [12] = '0'
      [13] = DFM (jaffa-encoded by _obsv_row_44)
      [34] = 'F'
      [35] = 'F'
      [39] = 'EN'
    """
    fields = [''] * 44
    fields[0] = 'OBSV'
    fields[1] = '2'
    fields[2] = '100502'
    fields[3] = str(layout.form_def_id)
    fields[5] = '0'
    fields[6] = 'IH'
    fields[7] = concept_pair[0]
    fields[8] = concept_pair[1]
    fields[9] = _format_nm_field(layout.concept_display_name, context_row_id)
    fields[11] = '2147483647'
    fields[12] = '0'
    fields[13] = dfm_text
    fields[34] = 'F'
    fields[35] = 'F'
    fields[39] = 'EN'
    return _obsv_row_44(fields)


def write_jfa(layout: FormLayout, dfm_text: str,
              now: datetime | None = None,
              concept_pair: tuple[str, str] | None = None) -> str:
    """Build a complete JFA file as a string.

    Returns:
        UTF-8 string starting with BOM, CRLF-terminated lines, tab-separated
        fields. Caller writes with encoding='utf-8' (not utf-8-sig) since the
        BOM is included literally in the returned string.
    """
    if now is None:
        now = datetime.now()

    if concept_pair is None:
        if layout.concept_code == DEFAULT_CONCEPT_PAIR_FOR_UB[0]:
            concept_pair = DEFAULT_CONCEPT_PAIR_FOR_UB
        else:
            concept_pair = (layout.concept_code, layout.concept_code)

    head = _build_head(now)
    lnvr = _build_lnvr()
    context_row = fixtures.NZDF_CONTEXT_ROW
    form_def = _build_form_def_row(
        layout, dfm_text,
        context_row_id=fixtures.NZDF_CONTEXT_ROW_ID,
        concept_pair=concept_pair,
    )

    lines = [head, lnvr, context_row, form_def]
    return BOM + '\r\n'.join(lines) + '\r\n'
