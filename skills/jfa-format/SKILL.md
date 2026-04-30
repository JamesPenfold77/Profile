# Skill: JFA (Jaffa) File Format

Status: **partially validated** — earlier source-reading combined with empirical validation against a working CDO Form sample (April 2026). The first-pass pipeline at `generators/pdf_to_jfa/` produces JFA files that import cleanly into Profile EMR (Hello World form + Pelvic Floor consent form, both validated end-to-end). Remaining unknowns are in "Open questions" at the end.

This skill captures everything established so far. For the generator pipeline that produces JFAs from PDFs, see the **pdf-to-jfa-generator** skill.

## Naming

Profile calls the format **Jaffa** internally — JFA is the on-disk extension. Source code uses the prefix `J` extensively (`TJLine`, `TJField`, `TJFile`, `JaffaLines`, `JaffaWriter`, `JaffaParser`, …).

## Tooling

Standalone CLI: `Profile/JaffaEncoder/JaffaEncoder.dpr`
- Usage: `JaffaEncoder.exe <source> <target> ENCODE|DECODE`
- DECODE: file (possibly encrypted, possibly mixed plaintext + encrypted lines) → plain text
- ENCODE: plain text → file with every line `LineEncrypt`-ed
- Useful for inspecting real on-disk JFA files (the on-the-wire form is encrypted) and for round-tripping a hand-authored plain text file through `LineEncrypt` to produce something Profile will accept.

**Empirically observed**: CDO Form template JFA files exported from Profile and accepted on import (`Form_Template_-_Form.jfa`, `Sample_Form_Template_Consent_for_Health_Care.jfa`) are **plain text, no per-line encryption**. The encryption pathway exists but is not used for this category of file.

Sample on-disk JFAs live in `Profile/Client/JaffaFiles/`. Two byte-precise reference samples are also in `generators/pdf_to_jfa/reference_samples/`:

- **`Form_Template_-_Form.jfa`** — minimal blank form. 4 records (HEAD/LNVR/1×100503/1×100502), ~16 KB. The canonical reference for boilerplate. The macros block, NoteBook prelude, and NZDF context row are spliced verbatim from this file in the generator's `fixtures.py`.
- **`Sample_Form_Template_Consent_for_Health_Care.jfa`** — busy populated form. 44 records, ~586 KB. Demonstrates field-row classes (100511/100517/100519) and a fully-populated DFM with ~30 controls.

Parser unit: `Profile/Common/Business/UBJaffaParser.pas` (`TBJaffaParser` / `IBJaffaParser`).
Writer unit: `Profile/Common/Business/UIJaffaFileDeclarations.pas` (`TJLineProcessor`, `TJaffaWriter`, `TJaffaValueEncoding`, `TJaffaLine`/`TJaffaLineEx`).
Type/metadata declarations: `Profile/Common/Business/UBJaffaFileDeclarations.pas`, `UBJaffaFileDeclarationsImpl.pas`, `UBJaffaFileDeclarationsCustom.pas` — **not yet read**.

## File-level structure (validated)

These invariants are confirmed against working samples and the Hello World round-trip — getting any of them wrong causes Profile to reject the file with "incorrect format":

- **UTF-8 with BOM** (`EF BB BF`) at the start of file. Written unconditionally by `TJaffaWriter.WriteLine` when the writer flag `aIsBeginOfJaffa` is true on the first call.
- **CRLF (`\r\n`)** between lines, written as ANSI bytes `#13#10`.
- **Tab (`\t` / `#9`) field delimiter** within each line. No trailing tab on the last field.
- Per-line encryption is independent. A single JFA can mix plain and encrypted lines. The HEAD line in particular tends to be unencrypted so the parser can detect encoding before it has a key. CDO Form template JFAs we've worked with are entirely plaintext.
- The parser also accepts ANSI, UTF-16LE, UTF-16BE encodings (auto-detected via BOM, then fallback to ASCII-sample heuristics). UTF-32 is detected but not supported.

**Trap the comma-separator assumption costs you**: visual inspection of a JFA in some tools renders tab characters as variable-width gaps that look like comma separators. They are tabs. Generating with commas instead of tabs is the #1 cause of "incorrect format" rejection.

## Lines

Every line begins with two immutable fields: **line code** (e.g. `HEAD`, `LNVR`, `OBSV`, `SHRS`) and **line version** (integer string).

Per-line metadata table is `JaffaLines: array[TJLine] of TBJaffaLineData` and contains, per line type:
- `Code: string`
- `Version: Integer` (current)
- `OldestVersion: Integer` (oldest still readable)
- `UnicodeCompatibleVersion: Integer` (lines at this version or above use `TJaffaValueEncoding` for field decoding)
- `FirstField: TJField`, `LastField: TJField` — ranges into the global `TJField` enum
- `FieldCount: Integer` — expected number of fields; mismatch is a *warning*, parser pads with `''` to match.
- `Title: string`

The exact contents of this table per line type are defined in `UBJaffaFileDeclarationsImpl.pas` (or similar) — not yet read.

### Line types we have seen in practice

| Code | Version | Fields | Notes |
|------|---------|--------|-------|
| `HEAD` | 3 | 15 | File header |
| `LNVR` | 3 |  6 | Line versions block — declares `(lineCode, version)` pairs the body uses |
| `OBSV` | 2 | 44 | The "observation" workhorse line — used for both data observations and form-template definitions |
| `SHRS` | 2 |  ? | Declared in LNVR but not used in any sample we've decoded |

### HEAD line layout (validated)

| # | Value | Notes |
|---|-------|-------|
| 0 | `HEAD` | tag |
| 1 | `3`    | format version |
| 2 | `1`    | batch number |
| 3 | `OBSV` | primary record type |
| 4 | `CDO Observations` | description |
| 5 | `Intrahealth` | system |
| 6 | `dd/mm/yyyy` | date (e.g. `30/04/2026`) |
| 7 | `HH.MM` | time, period as separator (e.g. `06.42`) |
| 8 | `M` | mode |
| 9 | empty | |
| 10 | empty | |
| 11 | `F` | flag |
| 12–14 | empty | |

**Trap**: positions of `M` and `F` matter. M is at [8], F is at [11], not adjacent. Earlier guesses placed F at [9].

### LNVR line layout (validated)

`LNVR \t 3 \t OBSV \t 2 \t SHRS \t 2`

Constant across all samples — emit verbatim.

## Field encoding

For lines whose version `>= UnicodeCompatibleVersion`, every field value passes through `TJaffaValueEncoding` round-trip:

- Escape character: `\` (backslash).
- "Special" characters are anything `< #32` (control chars: `#9` tab, `#10` LF, `#13` CR, `#7` bell, `#8` BS, etc.) or the backslash itself.
- Encoding produces `\<2 lower-case hex digits>`, e.g.:
  - `#9`  → `\09`
  - `#13` → `\0d`
  - `#10` → `\0a`
  - `\` → `\5c`
- Decoding inverts. `\\` is a literal `\`; `\<hex><hex>` is the byte; anything else is an error (`Unexpected end of encoded value`).
- This is exactly how the embedded DFM in the sample's form-definition row keeps real CRLFs intact: each source-line break appears as the literal four-character sequence `\0d\0a` in the field.
- **Commas pass through unencoded** — they are not field separators (tabs are).

```python
def jaffa_encode(value: str) -> str:
    out = []
    for ch in value:
        c = ord(ch)
        if ch == '\\':   out.append('\\5c')
        elif ch == '\t': out.append('\\09')
        elif ch == '\r': out.append('\\0d')
        elif ch == '\n': out.append('\\0a')
        elif c < 0x20:   out.append(f'\\{c:02x}')
        else:            out.append(ch)
    return ''.join(out)
```

### Null sentinel

- `cSignificantNullValue = '~null~'`. A field whose decoded value equals `~null~` represents SQL NULL (distinct from `''`, which is empty string).
- Writers prepend a `\` if the *encoded* value happens to equal `~null~`, producing `\~null~`. The parser undoes that: a field whose stored value is `\~null~` decodes to literal `~null~`.

## OBSV line (line code `OBSV`, version 2, 44 fields)

Field offsets confirmed empirically from decoded samples. The exact `TJField` names from `UBJaffaFileDeclarations.pas` are not yet known.

| # | Field | Notes |
|---|-------|-------|
| 0 | line code = `OBSV` | immutable |
| 1 | line version = `2` | immutable |
| 2 | **Class code** | observation type discriminator (see "Class codes") |
| 3 | **Object id** | unique id of this observation. Synthetic ids are remapped on import. |
| 4 | **Parent id** | for field rows: form-def id. For the form-def itself: empty. For top-level context rows: empty. |
| 5 | **Sequence / TabOrder** | 0-based ordinal within parent (form-def-relative); on 100503 rows, semantics unclear (varies 1, 17, 52 across samples) |
| 6 | namespace = `IH` | constant on form-def and field rows; **empty on 100503 context rows** |
| 7 | **Type code A** | per-class-code constant; see "zZ tokens" |
| 8 | **Type code B** | per-class-code constant |
| 9 | **NM= attribute string** | comma-separated `KEY=value` pairs (NOT tab-separated); see "NM= attributes" |
| 10 | (empty) | reserved |
| 11 | `2147483647` | Int32.MaxValue — sentinel/permission flag |
| 12 | `0` | flag |
| 13 | **DFM blob** | only on the form-def (class 100502) row; full Delphi `object … end` text, with field-encoding applied to control chars. Empty on every other row. |
| 14 | `0` | display flag — set on every field row, blank elsewhere |
| 18 | `0` | only set on date and boolean rows (100517 / 100519); meaning unknown |
| 34 | `F` | bool flag on form-def row; meaning unknown |
| 35 | `F` | bool flag on form-def row; meaning unknown |
| 39 | `EN` | language tag on form-def row |
| others | (empty) | reserved for richer observation types (numeric range, units, codings, etc.) |

The exact meaning of fields 10–43 needs to come from `UBJaffaFileDeclarations.pas`.

### Class codes (field [2] of OBSV)

| Code | Role | Distinguishing fields |
|------|------|----------------------|
| `100503` | **Context / tenancy / folder** marker. Forms a chain: the form-def's `FD=` references the deepest 100503 row's id. | NM= only. Folder-like: `NM=NZDF`, `NM=Accession`, `NM=Provider`, `NM=Consent Forms`, etc. |
| `100502` | **CDO Form definition.** Carries the embedded DFM in [13]. | `EEML=T`, `FD=<context-row-id>`, full DFM in [13] |
| `100511` | Edit / text control field | `TI=<HRI>` |
| `100517` | Date control field | `NULLTIME=0`, `TI=<HRI>` |
| `100519` | Boolean control field (checkboxes + radio buttons) | `TI=<HRI>` |

We have not yet found these constants defined in source. Other class codes presumably exist for memo, numeric, list, etc. Worth grepping for `100502` literals in the Profile codebase, though they may be looked up via a database table rather than hard-coded.

### Concept-pair tokens (fields [7] and [8] of OBSV)

| Pair | Used by | Meaning |
|------|---------|---------|
| `z..UB` / `z..UC` | 100502 form-def | Generic blank form (minimal sample, Hello World, Pelvic Floor consent) |
| `z..0K` / `z..4O` | 100502 form-def | Specific form type — Consent for Health Care |
| `zZ.1BD` / `zZ.1BE` | 100511 | Text-shaped field |
| `zZ.1BF` / `zZ.1BG` | 100517 / 100511(date-shaped) | Date-shaped field |
| `zZ.1BH` / `zZ.1BI` | 100519 | Checkbox-shaped field |
| `zZ.1BJ` / `zZ.1BK` | 100519 | Radio-shaped field (Yes/No pair) |

These look like base-36-like encoded ids and are paired (A/B). Field-row class tokens are **fixed type indicators** (text/date/boolean shape); form-def class tokens are **per-form**.

For a new form-def, use the same pair as the working sample with the same form concept (`z..UB` → `z..UC` is the safe default for blank forms — confirmed working with Hello World and the Pelvic Floor consent form).

### NM= attribute string (field [9] of OBSV)

Comma-separated `KEY=value` pairs (commas are NOT field separators since tabs are). Confirmed keys:

- `NM` — display name. Always present.
- `TI` — HRI of the matching DFM control. Required for field rows; absent on the form-def row itself (which only has `FD`).
- `FD` — context-row id (only on the form-def row, value matches the **immediate parent** in the 100503 chain — for a single-context form like Hello World this is the NZDF row's id; for a deeper chain like Consent for Health Care, this is the deepest row's id, e.g. the Provider row).
- `EEML=T` — flag: form has an embedded eML structured-text definition.
- `NULLTIME=0` — date-field semantics; meaning probably "no implicit time component".

**Quoting rule** (validated): if the `NM` value contains a space, wrap the entire `NM=...` portion in literal double-quote characters:

- `NM=Form,EEML=T,FD=4474196` — no spaces, no quotes
- `"NM=Consent for Health Care",EEML=T,FD=26229672` — value has spaces, quoted

## DFM payload (field [13] on the form-def row)

Standard Delphi text DFM (`object IVisualForm: TIVisualForm … end`), with line breaks encoded as the literal four-character sequence `\0d\0a` (because the writer applies `TJaffaValueEncoding.Encode` to the field value and CR/LF are control chars).

### Root form properties (validated, 18 properties before Macros block)

```
Left = 0
Top = 0
Caption = '<form name>'
ClientHeight = <int>
ClientWidth = <int>
Color = clBtnFace
KeyPreview = True
OldCreateOrder = False
PopupMenu = RunTimePopupMenu
NeedToSave = True
RepresentationMethod = rmStructuredText
PrintMethod = pmDefault
PaperName = 'Undefined'
PaperID = 0
PaperWidth = 0
PaperHeight = 0
PrintPaperSize = 'Default'
PrintPaperID = 0
```

Then `Macros.Strings = (...)` with **16 standard entries** (Pascal-style code templates with `#39` for embedded apostrophes and `#13#10` for line breaks). Treat as a verbatim fixture — copy the bytes whole from `Form_Template_-_Form.jfa`. Reconstructing it character-by-character is fragile and offers no benefit.

Then `PixelsPerInch = 96`, `TextHeight = 13`, then the NoteBook structure.

### NoteBook structure (validated)

```
object aNoteBook: TICDONoteBook
  Width = <canvas width>     ← can exceed ClientWidth (scrollable)
  Height = <canvas height>
  Color = clGray
  ParentColor = False
  TabOrder = 0
  OnPageChanged = aNoteBookPageChanged
  object TPage                  ← unnamed wrapper, do not omit
    Caption = 'Page_1'
    object Page_1: TICDOPanel   ← actual page panel
      Name = 'Page_1'
      Align = alClient
      Color = clWhite
      ...
    end
  end
end
```

The unnamed `TPage` wrapper between `aNoteBook` and `Page_1` is mandatory — omitting it makes the form unimportable. The NoteBook can be larger than the ClientWidth/ClientHeight; that's a scrollable canvas.

### Control palette (validated against working samples)

| Class | Purpose | Required properties |
|-------|---------|---------------------|
| `TICDOLabel` | Static text | `Caption`, `TechTranslation = False`, `Modified = True` |
| `TICDOEdit` | Single-line text input | `DefaultTabHandle`, `AllowTypingTemplates`, `CharCase = ecNormal`, `Visible`, `ShowHint` |
| `TICDOEdit` (date variant) | Date input | adds `EditType = edtyDate`, `EditKind = edkdDate`, `ShowButton = ShowBtnFocus`, `ShowButtonStyle = btnStDown` |
| `TICDOMemo` | Multi-line plain text | `TabOrder` |
| `TICDORichEdit` | RTF-rich-text input | `InputFormat = ifRTF`, `OutputFormat = ofRTF` |
| `TICDOSignature` | Signature pad | `Center`, `Proportional`, `SignaturePromptText`, `WhenCaptureSignature = wcsWhenPrinting` |
| `TICDOCheckBox` | Boolean checkbox | `CheckedValue = 'TRUE'`, `UncheckedValue = 'FALSE'` |
| `TICDORadioButton` | Radio button | `CheckedValue = 'TRUE'`, `Group = '<group name>'` |
| `TICDOImage` | Raster overlay | `Picture.Data` is a hex stream prefixed with `0B546478504E47496D616765` (length 11 + `'TdxPNGImage'`), NOT standard `TPngImage` |
| `TICDOBevel`, `TICDOShape` | Decorative | |
| `TICDOButton` | Action button | |
| `TICDOComboBox`, `TICDOListControl` | Selection inputs | |

**Common traps**:
- `TICDODateEdit` does NOT exist. Date inputs are `TICDOEdit` with the EditType/EditKind/ShowButton flags above.
- `TICDOImage` uses DevExpress `TdxPNGImage`, not standard `TPngImage`. Wrong prefix bytes will break image rendering.
- Single quotes in DFM string literals are escaped by **doubling** (`'O''Brien'`), not backslash.

Each input control carries an `HRI = <integer>` property. **HRI is the join key between DFM controls and OBSV field rows: every OBSV field row's `TI=` must match exactly one control's `HRI`.**

Unit definitions for these `TICDO*` controls have not yet been located — almost certainly under `Profile/Common/Form/` or `Profile/Common/Infrastructure/`.

## Reading existing JFAs

```python
def parse_jfa(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        content = f.read()
    lines = content.split('\r\n')
    if lines[-1] == '':
        lines = lines[:-1]
    return [line.split('\t') for line in lines]

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
```

For a quick structural sanity check on any JFA:
- File must start with BOM (`EF BB BF`)
- Line count: 4 (minimal form) or N+4 where N is the number of input controls
- HEAD has 15 fields, LNVR has 6, OBSV rows have 44
- The DFM in field [13] of the 100502 row decodes to text starting with `object IVisualForm: TIVisualForm`

## Producing JFAs

For PDF → JFA generation, see the **pdf-to-jfa-generator** skill and the pipeline at `generators/pdf_to_jfa/`. Architectural summary:

1. HEAD line (15 fields).
2. LNVR line declaring `OBSV` v2 and `SHRS` v2.
3. One or more `100503` rows for the import context (the "folder" / tenancy chain). The minimal form uses 1 (NZDF); the busy sample uses 2 (Accession + Provider).
4. One `100502` row carrying the DFM in field [13].
5. (Layout-only: skip.) One field row per input control: `100511`/`100517`/`100519` chosen by control type, with `TI=<HRI>` matching, sequential TabOrder, common parent id = form-def id.
6. Apply `TJaffaValueEncoding.Encode` to every field value (especially the DFM blob).
7. Join with tabs, terminate with CRLF, prepend UTF-8 BOM.

CDO Form template JFAs do **not** require encryption — the plaintext form is accepted.

## Open questions / remaining source reads

In rough priority order:

1. **`UBJaffaFileDeclarations.pas`** — `TJLine`, `TJField`, `TJFile` enums; the `JaffaLines` metadata table (so we know exact field count / version requirements per line type and the meaning of every field offset, including OBSV [10]–[43]).
2. **`UBJaffaFileDeclarationsImpl.pas`** — implementation of the helpers `GetJLineTypeFromCode`, `GetJLineFieldNumberFromLineType`, etc. — confirms expected field counts and any post-decode validation.
3. **`UBJaffaFileDeclarationsCustom.pas`** — likely contains custom/extended line types.
4. **`MakeJaffaHeaderLine`** and **`MakeJaffaVersionLine`** — tells us the exact layout the writer uses for HEAD and LNVR (including where fields like `M`/`F`/`F` originate).
5. **`UBJaffaEncryptionUtils.pas`** — `LineEncrypt` / `LineDecrypt` / `IsLineEncrypted`. Tells us whether we can hand-encrypt or must shell out to JaffaEncoder.exe (currently moot for CDO Form templates which are plaintext).
6. **CDO form definition / scripting** — find where the 1005xx class codes are defined, where `TICDO*` controls live, and how HRIs are allocated. Likely in `Profile/Common/Form/` or near the CDO scripting layer.
7. **HRI / TI allocation in production** — whether termset concept ids must pre-exist in the database or are auto-created on import. This blocks data-binding for generated forms; layout-only forms work fine without resolving this.
8. **The 100503 row's [5] field** — varies (1, 17, 52) across samples; semantics not understood. Currently preserved verbatim from the source sample.
