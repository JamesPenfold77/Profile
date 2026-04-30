# Reference Samples

This directory is a reference for **byte-precise JFA samples** — actual exports from Profile EMR that import cleanly. The skills (`skills/jfa-format/`, `skills/pdf-to-jfa-generator/`) refer to two specific samples by name. This README documents them and how to obtain them.

We don't commit the sample binaries themselves because:

- They're easy to obtain from Profile (one-click export of an existing form template), and
- Their content is fully captured in the generator's `fixtures.py` (boilerplate spliced verbatim) and the **jfa-format** skill's reference tables (per-field semantics).

## Sample 1: minimal blank form

**Filename**: `Form_Template_-_Form.jfa` (or whatever the export defaults to)

**Size**: ~16 KB, 4 records (HEAD / LNVR / 1× OBSV class 100503 / 1× OBSV class 100502)

**How to obtain**: in Profile, find a CDO Form template named "Form" (or any blank form template with concept code `z..UB`) and export it via the form designer's File → Export menu.

**Why we care**: this is the **canonical reference for the boilerplate** — root form properties, the 16-entry macros block, the NoteBook prelude with TPage wrapper, the Page_1 panel header, the closing `end` chain, and the NZDF context row. The fixtures in `generators/pdf_to_jfa/fixtures.py` are byte-precise lifts from this file:

- `NZDF_CONTEXT_ROW` — the entire OBSV 100503 line, verbatim
- `_MACROS_B64` / `MACROS_BLOCK` — the entire `Macros.Strings = (...)` block, verbatim
- `ROOT_FORM_PROPS`, `NOTEBOOK_PRELUDE`, `DFM_CLOSING` — the structural boilerplate, with a few `{caption}` / `{client_w}` / `{client_h}` / `{nb_w}` / `{nb_h}` substitution points

If `fixtures.py` ever needs to be regenerated from the source sample (for instance, if Profile changes the boilerplate format in a future version), the byte-extraction steps are:

1. Open the sample in a hex editor or Python (`open(path, 'rb')`)
2. Locate the OBSV 100503 line (line 3, after HEAD and LNVR, separated by `\r\n`)
3. Take that line's bytes verbatim as `NZDF_CONTEXT_ROW`
4. In the OBSV 100502 line, jaffa-decode field [13] (the DFM)
5. Slice at `Macros.Strings = (` and the matching `)` to get `MACROS_BLOCK`
6. Slice the DFM bytes before `Macros.Strings` to get `ROOT_FORM_PROPS` (replace `Caption = 'Form'`, `ClientHeight = 630`, `ClientWidth = 657` with `{caption}`, `{client_h}`, `{client_w}` placeholders)
7. Slice between the macros block close paren and the first child object inside Page_1 to get `NOTEBOOK_PRELUDE` (replace `Width = 1519`, `Height = 629` with `{nb_w}`, `{nb_h}`)
8. The closing 4 lines (`      end\r\n    end\r\n  end\r\n  end\r\n` — Page_1, TPage, NoteBook, IVisualForm) become `DFM_CLOSING`

## Sample 2: populated busy form

**Filename**: `Sample_Form_Template_Consent_for_Health_Care.jfa` (or similar)

**Size**: ~586 KB, 44 records (HEAD / LNVR / 2× OBSV class 100503 / 1× OBSV class 100502 / 23× class 100511 / 7× class 100517 / 9× class 100519)

**How to obtain**: in Profile, find any CDO Form template that has substantial input controls (signatures, dates, checkboxes) and a non-trivial DFM. The actual "Consent for Health Care" form is one example; any complex form will demonstrate the field-row classes.

**Why we care**: this sample demonstrates everything the minimal sample doesn't:

- **Field row classes** — 100511 (text), 100517 (date), 100519 (boolean) — including their fixed type-token pairs (`zZ.1BD`/`zZ.1BE` for text, `zZ.1BF`/`zZ.1BG` for date, `zZ.1BH`/`zZ.1BI` for checkbox, `zZ.1BJ`/`zZ.1BK` for radio)
- **Multi-row 100503 context chains** — the busy sample uses two: NM=Accession then NM=Provider (Provider's [4] points back to Accession's [3])
- **HRI / TI binding** — DFM controls have `HRI = 166122` and corresponding OBSV field rows have `TI=166122` in their NM= attribute
- **TICDOImage with embedded PNG** — the sample's "imgBackground" control demonstrates the `TdxPNGImage` stream prefix that's NOT documented anywhere else
- **TICDOSignature property set** — `Center = True`, `Proportional = True`, `SignaturePromptText`, `WhenCaptureSignature = wcsWhenPrinting`
- **TICDOEdit-as-date** — date inputs are NOT a separate `TICDODateEdit` class; they're `TICDOEdit` with `EditType = edtyDate`, `EditKind = edkdDate`, `ShowButton = ShowBtnFocus`, `ShowButtonStyle = btnStDown`
- **NM= quoting rule** — values containing spaces are wrapped in literal double-quotes (`"NM=Consent for Health Care"`)

If you need to extend the generator to emit field rows (data binding mode), this sample is the reference for what the row layout looks like.

## Working with samples

Quick decode of an OBSV row's DFM payload:

```python
def jaffa_decode(value):
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == '\\' and i + 2 < len(value):
            try:
                out.append(chr(int(value[i+1:i+3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(ch)
        i += 1
    return ''.join(out)

with open('Form_Template_-_Form.jfa', encoding='utf-8-sig', newline='') as f:
    content = f.read()
lines = content.split('\r\n')
form_def = lines[3].split('\t')   # OBSV 100502 row
dfm = jaffa_decode(form_def[13])
print(dfm)
```

Quick byte-level inventory:

```bash
python3 -c "
import re
with open('Form_Template_-_Form.jfa', 'rb') as f:
    raw = f.read()
print('Bytes:', len(raw))
print('BOM:', raw[:3] == b'\xef\xbb\xbf')
print('CRLFs:', len(re.findall(b'\\r\\n', raw)))
print('First 200 bytes (repr):', repr(raw[:200]))
"
```

For the full structural rules these samples demonstrate, see the **jfa-format** and **pdf-to-jfa-generator** skills.
