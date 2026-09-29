---
name: ihq-stored-query-format
description: Read Profile stored-query (.ihq) export files - the "Query by Example" queries in Profile's Stored Query view (FOQs run by macros via MakeFindObjectQueriesLoader). Use when asked to review, audit, compare or document stored queries, check which records a query selects, find its run-time parameters, or confirm its returned column order matches what a macro reads. Includes a working decoder (ihq_decode.py).
---

# Skill: Profile Stored Query (.ihq) Files

An `.ihq` file is a stored query exported from Profile's **Stored Query** view.
It is a `TQueryByExample` object saved as a **Delphi binary DFM** inside a small
Windows resource header — not text, not XML. The `file` command misreports it
(e.g. as "JPEG XL codestream"); ignore that.

**Use the decoder** in this folder rather than eyeballing bytes:

```bash
python skills/ihq-stored-query-format/ihq_decode.py "<file.ihq or folder>"          # readable summary
python skills/ihq-stored-query-format/ihq_decode.py "<file or folder>" --json       # for scripted checks
```

Validated on the seven NWRH "Dex Items for …" queries (Sep 2026): every file
decoded exactly, with the resource header's declared size matching the file.

## File layout

```
FF 0A 00                     resource type = RT_RCDATA (id 10)
"TQUERYBYEXAMPLE" 00         resource name
30 10                        memory flags
<uint32 size>                size of the DFM that follows (= file length - 25)
"TPF0"                       Delphi binary DFM signature
<shortstring class>          "TQueryByExample"
<shortstring object name>    (empty)
properties … 00              Select, Conditions, Common - each a vaList
```

Values use Delphi's `TValueType` tags: `01` list (until `00`), `02/03/04`
int8/16/32, `06` short string (1-byte length), `07` identifier, `08`/`09`
False/True, `0C` long string (4-byte length), `12` wide string (4-byte
**character** count, UTF-16). Strings are cp1252.

Each of the three properties is a **flat list of fixed-size records**, and
every record starts with the version marker string `"31"`:

### `Select` — returned columns, 7 values per record

| # | Value | Example |
|---|---|---|
| 0 | marker | `"31"` |
| 1 | field path (Profile object model, dotted) | `Encounter.Case.Case Type.Code` |
| 2 | sort order | `soUnknown` (none), `soAsc`, `soDesc` |
| 3 | group function | `gfNone` (others presumably `gfCount`, `gfSum` … — not yet seen) |
| 4 | boolean | always `False` so far — meaning unknown |
| 5 | alias | usually empty |
| 6 | SQL expression wrapping the column | `cast(&column as varchar)` — `&column` stands for the field |

Record order **is the result column order** (0-based). A macro reading the
query output by position (e.g. DEXREPORT_TEST's `cFilenum = 0 … cAction_DESCRIPTION = 11`)
breaks silently if a column is added, removed or moved in the query — always
compare the Select order with the macro's index constants.

### `Conditions` — the WHERE clause, 7 values per record

| # | Value | Example |
|---|---|---|
| 0 | marker | `"31"` |
| 1 | field path | `Encounter.Occurred` |
| 2 | operator | `opEqual`, `opLess`, `opEqualGreater`, `opIn`, `opIsNotNull`, … |
| 3 | value | literal (`Actioned`), comma list for `opIn` (`CHSPDA,CHSPHM`), empty for `opIsNull`/`opIsNotNull`, or **`?ask?`** |
| 4 | connector to the previous condition | `and` / `or`; empty on the first |
| 5 | boolean | always `False` so far — meaning unknown (possibly NOT / bracket) |
| 6 | string | always empty so far |

**`?ask?` is a run-time parameter.** Profile prompts for it when the query is
run by hand; a macro supplies it through the query's `Parameters(n).AskValue`,
numbered **in the order the `?ask?` conditions appear** (0, 1, …). The decoder
labels them `<parameter 0>`, `<parameter 1>`.

Operator symbols the decoder prints: `opEqual` =, `opNotEqual` <>, `opLess` <,
`opGreater` >, `opEqualLess` <=, `opEqualGreater` >=, `opIn` IN, `opNotIn`
NOT IN, `opLike` LIKE, `opIsNull`/`opIsNotNull`. Only `=`, `<`, `>=`, `IN`
and `IS NOT NULL` have been seen in real files — treat the others as expected
names, not verified ones.

Grouping/brackets and mixed `and`/`or` precedence haven't been seen yet. If a
query uses `or`, check in Profile's query designer how it groups before
drawing conclusions.

### `Common` — query properties (one record, 20 values seen)

| # | Value |
|---|---|
| 0 | marker `"31"` |
| 1 | integer (30 seen) — unknown |
| 2 | **query name** (as shown in the Stored Query view) |
| 3 | **description** |
| 4–15 | twelve booleans (all `True` seen) — unknown options |
| 16 | category (`Dex Items`) — *not* the Stored Query view folder; the folder (e.g. `NDIS`) isn't in the file |
| 17 | notes, as RTF |
| 18 | result-grid column layout: comma list of `"Title",Alias,Width,Type,Flag,` entries |
| 19 | boolean |

## Reviewing a query

1. Decode the whole folder and compare queries side by side — sibling queries
   are usually copies with one condition changed, so differences stand out.
2. Check **date parameters**: DEX-style period queries use
   `>= <parameter 0>` and `< <parameter 1>` (start included, end excluded —
   a month is 1st to 1st of the next month).
3. Check **list conditions** (`opIn`) against the authoritative code list —
   for NWRH Case Types, the `Cases` sheet of `Program, Cases & Service
   Mapping.xlsx` and the `CaseType Reason Mapping` shortcode export. Look for
   codes **missing** (records silently never selected), codes that don't
   exist, and case differences (`CHSPMeal` vs `CHSPMEAL`: it appears to work
   because the comparison ignores case, but fix it).
4. If a set of "split" queries is meant to cover everything together (e.g.
   Meal + no-meals + AH = all CHSP), check that their lists add up to the full
   set.
5. Compare the **Select order** with any macro that reads the results by
   position.
6. Check that the **name/description** match what the conditions do. In NWRH,
   "CHSP Cases (no meals)" actually covers only the seven home and community
   support Case Types, not all non-meal CHSP.

A worked review of the NWRH DEX queries (found CHSPSSS and FMHSSCLON in no
query, CHSPCA in the AH query) is in the "The stored queries in detail"
section of `Customers/NWRH/DEX Report - User Guide.docx`. See also the
**dex-reporting** skill.

## What the decoder can't tell you

- The Stored Query view **folder** (it's stored in Profile's database, not the file).
- How Profile turns field paths into SQL joins. For exact SQL, run the query
  in Profile with SQL logging, or ask for it.
- The meaning of the unknown booleans/integers above. If a query behaves
  unexpectedly, compare it with a copy saved after changing one option in the
  designer, to find which value moved.

**Stored queries often return patient-level data when run.** The `.ihq` file
itself holds only the definition (fields and conditions) and is safe to read.
