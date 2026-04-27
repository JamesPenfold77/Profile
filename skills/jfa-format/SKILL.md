# Skill: JFA (Jaffa) File Format

Status: **work in progress**, recorded April 2026. Goal: produce a generator that emits valid JFA files (specifically CDO Form templates) from external sources such as PDFs.

This skill captures everything established so far. The remaining unknowns are listed at the end with the exact files to read next.

## Naming

Profile calls the format **Jaffa** internally — JFA is the on-disk extension. Source code uses the prefix `J` extensively (`TJLine`, `TJField`, `TJFile`, `JaffaLines`, `JaffaWriter`, `JaffaParser`, …).

## Tooling

Standalone CLI: `Profile/JaffaEncoder/JaffaEncoder.dpr`
- Usage: `JaffaEncoder.exe <source> <target> ENCODE|DECODE`
- DECODE: file (possibly encrypted, possibly mixed plaintext + encrypted lines) → plain text
- ENCODE: plain text → file with every line `LineEncrypt`-ed
- Useful for inspecting real on-disk JFA files (the on-the-wire form is encrypted) and for round-tripping a hand-authored plain text file through `LineEncrypt` to produce something Profile will accept.

Sample on-disk JFAs live in `Profile/Client/JaffaFiles/` — useful as test fixtures.

Parser unit: `Profile/Common/Business/UBJaffaParser.pas` (`TBJaffaParser` / `IBJaffaParser`).
Writer unit: `Profile/Common/Business/UIJaffaFileDeclarations.pas` (`TJLineProcessor`, `TJaffaWriter`, `TJaffaValueEncoding`, `TJaffaLine`/`TJaffaLineEx`).
Type/metadata declarations: `Profile/Common/Business/UBJaffaFileDeclarations.pas`, `UBJaffaFileDeclarationsImpl.pas`, `UBJaffaFileDeclarationsCustom.pas` — **not yet read**.

## File-level structure

- **UTF-8 with BOM** (`EF BB BF`) at the start of file. Written unconditionally by `TJaffaWriter.WriteLine` when the writer flag `aIsBeginOfJaffa` is true on the first call.
- **CRLF** between lines, written as ANSI bytes `#13#10`.
- **Tab (`#9`) field delimiter** within each line. No trailing tab on the last field.
- **Per-line encryption is independent.** A single JFA can mix plain and encrypted lines. The HEAD line in particular tends to be unencrypted so the parser can detect encoding before it has a key. The parser's `IsLineEncrypted` heuristic decides per line whether to call `LineDecrypt`.
- **Encryption** is in `UBJaffaEncryptionUtils` — not yet read.
- The parser also accepts ANSI, UTF-16LE, UTF-16BE encodings (auto-detected via BOM, then fallback to ASCII-sample heuristics). UTF-32 is detected but not supported.

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

| Code | Version | Notes |
|---|---|---|
| `HEAD` | 3 | 15 fields. File header. |
| `LNVR` | 3 | 6 fields. Line versions block — declares `(lineCode, version)` pairs the body uses. |
| `OBSV` | 2 | 44 fields. The "observation" workhorse line — used for both data observations and form-template definitions. |
| `SHRS` | 2 | declared in LNVR of the sample but not used in the body. Present so importer accepts SHRS lines if encountered. |

## Field encoding

For lines whose version `>= UnicodeCompatibleVersion`, every field value passes through `TJaffaValueEncoding` round-trip:

- Escape character: `\` (backslash).
- "Special" characters are anything `< #32` (control chars: `#9` tab, `#10` LF, `#13` CR, `#7` bell, `#8` BS, etc.) or the backslash itself.
- Encoding produces `\<2 lower-case hex digits>`, e.g.:
  - `#9`  → `\09`
  - `#13` → `\0d`
  - `#10` → `\0a`
  - `\` → `\\`
- Decoding inverts. `\\` is a literal `\`; `\<hex><hex>` is the byte; anything else is an error (`Unexpected end of encoded value`).
- This is exactly how the embedded DFM in the sample's form-definition row keeps real CRLFs intact: each source-line break appears as the literal four-character sequence `\0d\0a` in the field.

### Null sentinel

- `cSignificantNullValue = '~null~'`. A field whose decoded value equals `~null~` represents SQL NULL (distinct from `''`, which is empty string).
- Writers prepend a `\` if the *encoded* value happens to equal `~null~`, producing `\~null~`. The parser undoes that: a field whose stored value is `\~null~` decodes to literal `~null~`.

## What we know about OBSV (line code `OBSV`, version 2, 44 fields)

Field offsets confirmed empirically from the decoded sample (`Sample_Form_Template_Consent_for_Health_Care.jfa`). The exact `TJField` names from `UBJaffaFileDeclarations.pas` are not yet known.

| # | Field | Notes |
|---|---|---|
| 0 | line code = `OBSV` | immutable |
| 1 | line version = `2` | immutable |
| 2 | **Class code** | observation type discriminator (see "Class codes") |
| 3 | **Object id / HRI key** | unique id of this observation. Form-def rows use this as the parent reference for child fields. |
| 4 | **Parent id** | for field rows: form-def id. For the form-def itself: empty. |
| 5 | **Sequence / TabOrder** | 0-based ordinal within parent |
| 6 | namespace = `IH` | constant marker |
| 7 | **Type code A** | per-class-code constant; see "zZ tokens" |
| 8 | **Type code B** | per-class-code constant |
| 9 | **NM= attribute string** | comma-separated `KEY=value` pairs, see "NM= attributes" |
| 10 | (empty) | reserved |
| 11 | `2147483647` | Int32.MaxValue — sentinel/permission flag |
| 12 | `0` | flag |
| 13 | **DFM blob** | only on the form-def (class 100502) row; full Delphi `object … end` text, with field-encoding applied to control chars. Empty on every other row. |
| 14 | `0` | display flag — set on every field row, blank elsewhere |
| 18 | `0` | only set on date and boolean rows; meaning unknown |
| 34 | `F` | bool flag on form-def row; meaning unknown |
| 35 | `F` | bool flag on form-def row; meaning unknown |
| 39 | `EN` | language tag on form-def row |
| others | (empty) | reserved for richer observation types (numeric range, units, codings, etc.) |

The exact meaning of fields 10–43 needs to come from `UBJaffaFileDeclarations.pas`.

### Class codes (field [2] of OBSV)

| Code | Role | Distinguishing fields |
|---|---|---|
| `100503` | Header observation (Accession, Provider). `aliasCode`-style record. | NM= only |
| `100502` | **CDO Form definition.** Carries the embedded DFM in [13]. | `EEML=T`, `FD=<formdef-id>`, full DFM in [13] |
| `100511` | Edit / text control field | `TI=<HRI>` |
| `100517` | Date control field | `NULLTIME=0`, `TI=<HRI>` |
| `100519` | Boolean control field (checkboxes + radio buttons) | `TI=<HRI>` |

We have not yet found these constants defined in source. Other class codes presumably exist for memo, numeric, list, etc. Worth grepping for `100502` literals in the Profile codebase, though they may be looked up via a database table rather than hard-coded.

### "zZ.1Bx" tokens (fields [7] and [8] of OBSV)

Per-class constants observed in the sample:

| Class | Field [7] | Field [8] |
|---|---|---|
| `100503` (header) | `1335` | `1335` (or similar) |
| `100502` (form-def) | `z..0K` | `z..4O` |
| `100511` (edit) | `zZ.1BD` | `zZ.1BE` |
| `100517` (date) | `zZ.1BF` | `zZ.1BG` |
| `100519` (boolean) | `zZ.1BH` | `zZ.1BI` (checkbox) or `zZ.1BJ` / `zZ.1BK` (radio) |

These look like base-36-like encoded ids and are paired (A/B). Meaning unknown — possibly references to entries in a system reference table. Need to search for these literals in the codebase.

### NM= attribute string (field [9] of OBSV)

Comma-separated `KEY=value` pairs. Confirmed keys:

- `NM` — display name. Always present.
- `TI` — HRI of the matching DFM control. Required for field rows; absent on the form-def row itself (which only has `FD`).
- `FD` — form-def id (only on the form-def row, value matches the parent_id used by all field rows).
- `EEML=T` — flag: form has an embedded eML structured-text definition.
- `NULLTIME=0` — date-field semantics; meaning probably "no implicit time component".

Other keys may exist — to discover by scanning more JFA samples.

## DFM payload (field [13] on the form-def row)

Standard Delphi text DFM (`object IVisualForm: TIVisualForm … end`), with line breaks encoded as the literal four-character sequence `\0d\0a` (because the writer applies `TJaffaValueEncoding.Encode` to the field value and CR/LF are control chars).

- Root: `IVisualForm: TIVisualForm` — captures form properties (`Caption`, `ClientWidth/Height`, `RepresentationMethod = rmStructuredText`, paper settings, `Macros.Strings` block with the standard nine Profile macro hooks, the embedded eML structured-text definition, etc.).
- Inside it: `aNoteBook: TICDONoteBook` → one or more `Page_n: TICDOPanel` → controls.
- CDO control classes seen: `TICDOEdit`, `TICDOSignature`, `TICDOCheckBox`, `TICDORadioButton`, `TICDOImage`. Likely others exist (memo, combo, etc.) — to be enumerated.
- Each control carries an `HRI = <integer>` property. **HRI is the join key between DFM controls and OBSV field rows: every OBSV field row's `TI=` must match exactly one control's `HRI`.**
- `TICDORadioButton` includes a `Group` string for radio mutual-exclusion.
- `TICDOCheckBox` carries `CheckedValue = 'TRUE'` / `UncheckedValue = 'FALSE'`.

Unit definitions for these `TICDO*` controls have not yet been located — almost certainly under `Profile/Common/Form/` or `Profile/Common/Infrastructure/`.

## Generator approach (planned)

For PDF → JFA (CDO Form template):

1. Detect or accept field rectangles (PDF points → DFM units, calibration TBD).
2. Render the PDF page as PNG, embed as `TICDOImage` background of `Page_1`.
3. Build a DFM string with `TICDO*` overlays at correct positions, each with a freshly allocated `HRI`. (HRI allocation strategy still needs confirming — globally unique vs per-form vs sequence-allocated.)
4. Build OBSV rows:
   - HEAD line (15 fields).
   - LNVR line declaring `OBSV` v2 and `SHRS` v2.
   - Two `100503` rows (Accession + Provider) for the import context.
   - One `100502` row carrying the DFM in field [13].
   - One field row per control: `100511`/`100517`/`100519` chosen by control type, with `TI=<HRI>` matching, sequential TabOrder, common parent id = form-def id.
5. Apply `TJaffaValueEncoding.Encode` to every field value (especially the DFM blob).
6. Join with tabs, terminate with CRLF, prepend UTF-8 BOM.
7. Optionally pipe through `JaffaEncoder.exe ENCODE` to encrypt every line, OR apply `LineEncrypt` ourselves once we know the algorithm.

## Open questions / remaining source reads

In rough priority order:

1. **`UBJaffaFileDeclarations.pas`** — `TJLine`, `TJField`, `TJFile` enums; the `JaffaLines` metadata table (so we know exact field count / version requirements per line type and the meaning of every field offset, including OBSV [10]–[43]).
2. **`UBJaffaFileDeclarationsImpl.pas`** — implementation of the helpers `GetJLineTypeFromCode`, `GetJLineFieldNumberFromLineType`, etc. — confirms expected field counts and any post-decode validation.
3. **`UBJaffaFileDeclarationsCustom.pas`** — likely contains custom/extended line types.
4. **`MakeJaffaHeaderLine`** and **`MakeJaffaVersionLine`** — tells us the exact layout the writer uses for HEAD and LNVR (including where fields like `M`/`F`/`F` originate).
5. **`UBJaffaEncryptionUtils.pas`** — `LineEncrypt` / `LineDecrypt` / `IsLineEncrypted`. Tells us whether we can hand-encrypt or must shell out to JaffaEncoder.exe.
6. **CDO form definition / scripting** — find where the 1005xx class codes are defined, where `TICDO*` controls live, and how HRIs are allocated. Likely in `Profile/Common/Form/` or near the CDO scripting layer.

## Reference: sample file we reverse-engineered

`Sample_Form_Template_Consent_for_Health_Care.jfa` — 44 lines, 1×HEAD + 1×LNVR + 42×OBSV. One CDO form definition with 39 field rows (only 25 of which had matching HRIs in the embedded DFM head — the others presumably live on `Page_2`/`Page_3` panels not visible in the partial DFM dump).
