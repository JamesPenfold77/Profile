---
name: ih-edit-jfa-forms
description: Read and edit .jfa CDO form-definition files (OBSV export rows containing a serialized Delphi TIVisualForm + VBScript macros). Use when the user wants to view, add fields to, or otherwise modify a .jfa form template.
---

# Editing .jfa CDO Form Files

A `.jfa` file is a tab-delimited export of one or more "OBSV" (Observations) rows from
Intrahealth Profile's CDO form designer. One row (usually the largest, often 100k+ characters)
is the actual form: a serialized Delphi `TIVisualForm` — controls (`TICDOCheckBox`,
`TICDOEdit`, `TICDOLabel`, `TICDOComboBox`, `TICDORichEdit`, etc.) plus a `Macros.Strings`
block containing named VBScript macros (`onbillabletick`, `OnedtminsMChange`,
`OnbtnInvoiceNowMClick`, `OnNDISCefFormMValidateSave`, `OnNDISCefFormMRepresentationRtf`, etc.)
that drive the form's runtime behaviour.

**Read this whole skill before editing anything.** The file uses two separate, easy-to-confuse
escaping schemes, and getting them mixed up will corrupt the file.

## The two escaping schemes

1. **`\0d\0a`** — a literal 5-character sequence (`\`,`0`,`d`,`\`,`0`,`a`) marking the CRLF
   between physical lines of the underlying DFM/Pascal source (e.g. between
   `object X: TICDOCheckBox` and its `Left = 20` property line, or between two `'...' +`
   wrapped continuation lines of a long Delphi string literal). This is **cosmetic** —
   Pascal string-literal concatenation (`'a' +` newline `'b'` == `'ab'`) means these breaks
   can be inserted or moved without changing the logical value, as long as they never land
   inside what should be one token. In practice, match the file's own convention of not
   splitting a literal string's visible text (e.g. a billing-code description) across one
   of these breaks, even though it's probably safe — no need to introduce a new case to worry about.

2. **`^^^`** — three literal caret characters marking an embedded newline **inside** a
   macro's VBScript source text (each `Macros.Strings` entry is one long Pascal string —
   Pascal can't embed a raw newline in a string literal, so the export tool uses `^^^` as a
   stand-in; Profile's macro engine presumably expands it back to a real line break before
   running the script). Every logical line of VBScript inside a macro body is separated by `^^^`.

Do not confuse the two. `\0d\0a` is about the DFM/export file's own line wrapping;
`^^^` is about line breaks *within* a macro's source code.

**`\0d\0a` is one instance of a general escape, not a special case.** The underlying Jaffa
field encoding hex-escapes *any* control character or literal backslash as `\<2 lowercase hex
digits>` (`\0d`/`\0a` for CR/LF, `\09` for tab, `\5c` for a literal backslash itself). A literal
backslash shows up inside macro source far more often than you'd expect — RTF control codes
(`\rtf1`, `\par`, `\cf1`, ...) in any macro that builds `RepresentationRtf`, and VBScript's `\`
integer-division operator (`(x - 1) \ 15`) — and every one of those is stored as `\5c`, not a raw
backslash byte. This matters most when you rewrap a long string (see "Bulk edits" below): never
let a physical-line boundary fall in the middle of a `\5c`/`\0d`/`\0a`/etc. run, or you leave a
bare backslash that isn't followed by two hex digits, and Profile's import throws
`EConvertError: Invalid hex digit ''` while decoding that field.

**A `\0d\0a` boundary is not a safe place to splice new code by itself — it can fall
mid-token inside the macro's own VBScript string literal.** After expanding `\0d\0a` to
real newlines, every resulting "line" is just one `'...' +` wrapped chunk of Delphi's own
DFM text; Delphi wraps at a fixed column count with no awareness of what VBScript token it
is cutting through. Concretely: `if Form.Controls_("x").Text = "" then aMessage = aMessage
& "- Encounter Type` can be one physical line, with the next physical line starting `" &
vbCRLF^^^ ...` — the closing `"` of the VBScript string literal is on the *next* Delphi
line, with no `^^^` anywhere near it. Inserting new content at that line boundary splices
it into the middle of `"- Encounter Type"`, corrupting the string, even though the edit
"looks" clean in the expanded file (every line still ends in `' +` or is followed by
another line). Only a real `^^^` is a guaranteed-safe macro-internal line-break; a bare
`\0d\0a`-derived line break is not. Before trusting any splice point, **fully decode the
edited item back to plain VBScript** (reverse both the `'...' +`/`#39` Pascal-string
concatenation and the `^^^` markers) and read the result — do not just eyeball the
expanded-with-real-newlines file, since that view still contains the misleading Delphi
wrap points. A decode that produces a stray, unclosed, or oddly-split string literal means
the splice landed on a Delphi wrap boundary instead of a real macro newline.

## Workflow

Always regenerate from the current file — never trust a cached expanded copy from an earlier
session or an earlier point in the conversation. If the user has opened and saved the file in
the real CDO designer in between, the byte layout may have changed even if the logical form
hasn't (re-wrap points, property order, etc.).

**This is not a theoretical warning — it happens routinely and goes beyond re-wrapping.**
Confirmed in practice across one multi-turn editing session: the root form's `Left`/`Top`/
`ClientHeight` changed (the designer's own last-window-position bookkeeping), a label got
dragged to a new `Left`/`Top`, a new `TICDOImage` control appeared that Claude never added, and
a macro's own loop bound (`If i <= 5` → `If i <= 6`) had been hand-corrected by the human. None
of that is something to "fix" or revert — it's the user's own work landing between your turns.
Diff your edited region against whatever is *currently on disk* at the start of every turn, not
against a copy from three turns ago, and don't be surprised when unrelated property values have
moved; that's a signal to re-extract, not a bug in your own last edit.

### 1. Locate the target row and back it up

```bash
awk '{print NR": "length($0)}' "path/to/form.jfa"   # find the long row (the form)
cp "path/to/form.jfa" "/tmp/form.jfa.bak"            # always back up before writing
sed -n '4p' "path/to/form.jfa" > /tmp/rowN.txt        # extract just that row (adjust row #)
```

### 2. Expand `\0d\0a` into real newlines for readability

```bash
awk '{gsub(/\\\\0d\\\\0a/,"\n"); print}' /tmp/rowN.txt > /tmp/rowN_expanded.txt
```

(The doubled backslashes in the awk pattern are required — this is the pattern that actually
matched in testing; a naive `\\0d\\0a` pattern silently matches nothing.)

Now `/tmp/rowN_expanded.txt` is one logical DFM line per text line — read it with Read/Grep as
normal to find controls (`object cbBillable2: TICDOCheckBox ... end`) and macros
(`'onbillabletick='#39'macro onbillabletick^^^Sub Main()^^^...'`).

### 3. Make edits with the Edit tool

- For **new controls**: insert a complete `object Name: TIClassName ... end` block next to a
  similar existing control, matching its property style. Do not invent an `HRI` value for
  persisted fields (see "HRI / field-dictionary caveat" below) — leave it unset unless the
  user supplies a real one.
- **Styling — ask first.** When creating a new form, or when the user asks to modernise or
  redesign one, offer the optional "modern" style: Segoe UI, a blue header bar, rounded
  section cards, rounded icon buttons and orange difference highlighting.
  - It's documented in the **jfa-format** skill (`Profile/skills/jfa-format/SKILL.md`,
    "Optional modern form style").
  - The reference form is `Profile/Customers/QCG/Form Template - Demographic Information.jfa`.
  - Ask before using it, because it isn't always appropriate (printed forms, paper-replica
    consent forms, forms that must match a customer's set).
  - A second, smaller reference is `Profile/Customers/Hauora Waikato/Way Back Phone Client
    V1.5.6.jfa` (rounded input frames, header glyph, secondary button).
  - Before handing a restyled form over, run `jfa_layout_check.py` and `jfa_preview.py` from
    `Profile/skills/jfa-format/tools/` and show the user the preview PNG.
  - Never restyle an existing form as a side effect of another edit. Match the existing
    form's look unless the user says otherwise.
- For **shifting layout**: existing controls' `Top`/`Left` are plain integers — safe to edit directly.
- For **macro logic**: many macros use hardcoded index loops (e.g. `for i = 1 to 6`,
  `for i = 1 to 10`, `for i = 7 to 10`) over `cbbillable<i>` / `edtmins<i>` controls, spanning
  budget-lockout, tick/untick field-locking, minutes totals/rounding, save validation, and the
  invoicing macro's `AddNewActions` calls. Adding a new item that doesn't fit the contiguous
  numeric convention (e.g. billable-only, breaking the 1–6/7–10 split) means duplicating each
  loop's body as an explicit hardcoded block for the new index, rather than extending the loop
  range — safer than renumbering existing controls across every macro that references them by
  name. Map out **every** location that touches the relevant index range before editing any of
  them (grep for `for i = ` and the specific control-name prefixes).
- Keep each Edit's `old_string` short but unique; when inserting between two existing wrapped
  lines that split mid-word (e.g. `...  form` / `.controls_("x")...`), either insert at a clean
  boundary or explicitly re-pair the split token in your replacement (add the trailing word
  fragment to the end of your inserted line) so nothing merges or drops incorrectly.
- **When inserting content between two `^^^`-separated macro lines, count the carets on both
  sides of the splice.** The total carets between the end of your inserted block and the start
  of whatever follows must be a clean multiple of 3, or a stray `^` is left as a literal
  character in the macro source — Profile's macro engine will reject it as an "invalid
  character" rather than silently ignoring it (hit this in practice: ended an inserted block
  with `^^^` (3, clean) right before an existing line that itself started with a leftover `^`
  from its original pairing, for 4 total — one orphaned caret). After any such insertion, grep
  the surrounding text back out and count.
- **When shifting one control's `Top` down, grep for every other control in the same visual
  area** (labels, footnotes, version stamps) before assuming only the "row" controls need
  moving — it's easy to shift a checkbox/edit pair and miss a `TICDOLabel` sitting just below or
  beside it, which then overlaps the shifted content instead.

### 4. Recollapse to raw format

Do **not** use `sed`/`awk` `printf` with literal `\0d\0a` in the format string for this step —
both bash's and awk's own backslash-escape processing will mangle it (verified: it silently
turns `\0d\0a` into stray characters). Use a small Python script instead, building the
separator with `chr(92)` to avoid every layer of escape reinterpretation:

```python
with open(r'C:\path\to\rowN_expanded.txt', 'r', encoding='utf-8', newline='') as f:
    content = f.read()

lines = content.split('\n')
if lines and lines[-1] == '':
    lines = lines[:-1]

sep = chr(92) + '0d' + chr(92) + '0a'
joined = sep.join(lines)          # NOT `+ sep` — see trap below

with open(r'C:\path\to\rowN_collapsed_raw.txt', 'w', encoding='utf-8', newline='') as f:
    f.write(joined)
```

Run it with a real Windows path (`python3 script.py`), not a Git Bash `/tmp/...` POSIX path —
`python3` in this environment resolves to a Windows executable that can't see Git Bash's `/tmp`
path mapping.

**Trap: don't append a trailing `sep` after the join.** An earlier version of this snippet did
`sep.join(lines) + sep`, which is only correct when the text you expanded is an *isolated field*
that itself ends exactly on a `\0d\0a` boundary. The much more common case — extracting the
*whole* `sed -n 'Np'` row (steps 1-2 above) — includes the OBSV row's remaining tab-delimited
fields (flags, language tag, etc.) *after* the DFM blob's own closing `end`; those trailing
fields are plain text with no `\0d\0a` following them. `awk`'s own `print` appends one real `\n`
at the very end regardless, so after `content.split('\n')` the last element is an empty string —
strip *that* (the `if lines[-1] == ''` line already does this), then `sep.join(lines)` alone
reconstructs the original byte-for-byte. Adding `+ sep` back on top inserts one spurious
`\0d\0a` right at the true end of the row, silently corrupting it. Verify this each time: expand
then immediately recollapse the *unmodified* row and confirm it's byte-identical (module the
`sed`-added trailing newline, see the tail check in step 5) to the original before trusting any
real edit built on the same pipeline.

### 5. Reassemble the full file and verify before overwriting

```bash
JFA="path/to/form.jfa"
sed -n '1,3p' "$JFA" > /tmp/rebuilt.txt          # rows before the edited row, unchanged
cat /tmp/rowN_collapsed_raw.txt >> /tmp/rebuilt.txt
printf '\n' >> /tmp/rebuilt.txt
sed -n '5,33p' "$JFA" >> /tmp/rebuilt.txt        # rows after the edited row, unchanged

# Verify unrelated rows are byte-identical before trusting the rebuild:
diff <(sed -n '1,3p' "$JFA") <(sed -n '1,3p' /tmp/rebuilt.txt) && echo "unchanged rows OK"
diff <(sed -n '5,33p' "$JFA") <(sed -n '5,33p' /tmp/rebuilt.txt) && echo "unchanged rows OK"

cp /tmp/rebuilt.txt "$JFA"   # only after the diffs above pass
```

**Then fix the row-separator line endings.** Git Bash's `sed`/`cat`/`printf` all emit bare LF
regardless of the source file's line endings — if the original `.jfa` used CRLF between its
tab-delimited rows (check with `file "$JFA"` — it'll say "with CRLF line terminators" or won't),
the rebuild above silently downgrades all of them to LF. This is a different thing from the
`\0d\0a`/`^^^` *escaped text* inside row 4 — those are literal backslash-digit-letter
characters, untouched by real newline-byte conversion — but the actual OS-level bytes
separating row 1 from row 2, etc., do get mangled. Confirm and fix in one step:

```python
path = r'C:\path\to\form.jfa'
with open(path, 'rb') as f:
    data = f.read()
print('CRLF:', data.count(b'\r\n'), 'lone LF:', data.count(b'\n') - data.count(b'\r\n'))
# If the backup/original has CRLF but this shows 0, and lone CR is 0 too, a straight
# LF -> CRLF replace is safe (won't double up existing CRLF):
if data.count(b'\r\n') == 0 and data.count(b'\n') > 0:
    with open(path, 'wb') as f:
        f.write(data.replace(b'\n', b'\r\n'))
```

Compare against a backup taken *before any session ever touched the file* — a backup made
mid-session may already carry this regression forward from an earlier rebuild.

Then sanity-check the edited row itself:

```bash
awk '{n=gsub(/object /,"X"); print n}' "$JFA"    # object-block count — compare to backup, should
awk '{n=gsub(/object /,"X"); print n}' "$JFA.bak"  # differ by exactly the number of controls added
grep -o "YourNewFieldName" "$JFA" | wc -l         # confirm new identifiers/strings are present and intact
```

### 6. Bump the version label

Most forms carry a static text label somewhere on the canvas whose `Caption` is a version
stamp: `<version> <initials> <date ddmmyyyy>`, e.g. `V 1.5 JP 09072026`. The control's
*name* varies by form (`laVersion`, `lblVersion`, `VersionLabel`, ...) — don't assume a
fixed name. Find it with a wildcard/content search across every `TICDOLabel` in the
expanded DFM: match on the *name* loosely (anything containing `version` or `label`,
case-insensitive) combined with a *caption* that fits the shape (a version-like token,
some initials, an 8-digit date) — the caption shape is the more reliable signal since it's
what's actually distinctive, not the name.

After any Claude-made change to a form's jfa file, bump this label as a minor version
increment with `Claude` as the initials and today's date in `ddmmyyyy` format, matching the
label's own existing spacing/punctuation convention but always with an upper-case `V` —
e.g. `V 1.5 JP 09072026` becomes `V 1.5.1 Claude 10092026` for a change made on 10
September 2026. Do not touch the major/minor numbers the human owner controls (`1.5` here)
beyond appending the next `.N`; the human reviewer bumps to the next clean version (e.g.
`1.6`) with their own initials once the change is tested and approved — never write a clean
(non-`.N`-suffixed) version number or substitute your own initials for the reviewer's on
that final bump.

**Trap: `.N` keeps incrementing past single digits — it never rolls into the minor
version.** Across a run of several Claude-only edits in one session with no human review in
between, `.9` becomes `.10`, not a bump to the next minor (`1.0.9` → `1.0.10`, **not**
`1.1.0`). Rolling over to the minor is exactly the "clean version bump" reserved for the
human reviewer — doing it yourself because the `.N` looks like it's getting long is the same
mistake as writing a bare `1.6` yourself. Keep appending `.N` indefinitely (`.10`, `.11`, ...)
until a human actually reviews and cleans it up.

**If no such label exists on this form**, create one rather than skipping the step. Copy
the font properties from a known-good example verbatim (as of 2026-09, that's just
`Font.Color = clGray` with no other `Font.*` override — check the reference example you're
copying from in case a given form's convention differs) and place it toward the bottom-left
of the form, mirroring the reference's layout convention: `Left` a small fixed offset from
the form edge (e.g. `14`), `Top` near the bottom of the client area, `Anchors =
[akLeft, akBottom]` with `AnchorBottom = True` so it stays bottom-left if the form is
resized. Seed its `Caption` as `V 1.0.1 Claude ddmmyyyy` (starting the human owner at
`1.0` since there's no prior version to increment from).

### 7. Tell the user to verify in the real designer

Nothing here can runtime-test the VBScript macros or confirm the DFM still loads correctly in
Delphi. Always tell the user to open the file in the actual CDO form designer to visually
confirm layout and exercise the macro logic before relying on it or deploying it.

## Troubleshooting: `EReadError: Property X does not exist` on import

Importing a `.jfa` can fail in Profile.exe with a dialog like:

```
EReadError: Error reading IVisualForm.PrintPaperSize: Property PrintPaperSize does not exist
Profile.exe 9.0.8.1  Date/time: 01/09/2026 10:22:30
```

This means the installed Profile.exe build's compiled `TIVisualForm` (or whichever class is
named) does not have that property registered as published — the DFM stream reader hits a
property name it doesn't recognize on the target class and aborts. This happens when the
`.jfa` carries a property that was added to the CDO Form component in a *newer* Profile.exe
build than the one doing the import; it is a version mismatch between the file's origin and
the runtime being tested against, not a sign of a corrupted or hand-edited file. Confirmed in
practice for `PrintPaperSize` / `PrintPaperID` on the top-level form object — a pair that
sits alongside the older `PaperName`/`PaperID`/`PaperWidth`/`PaperHeight` properties and is
present verbatim in known-good template files too, so seeing the property isn't itself
suspicious; only the target Profile.exe's age determines whether it errors.

**Real fix:** import against (or upgrade to) a Profile.exe build that has the property. This
is the only fix if the property actually controls behaviour the form needs.

**Workaround, when the property has a clear older equivalent already in the same form (as
with `PrintPaperSize`/`PrintPaperID` next to `PaperName`/`PaperID`/`PaperWidth`/`PaperHeight`):**
delete the offending `PropertyName = value\0d\0a` line(s) from the row so the older build's
reader never encounters them:

1. Extract the row and locate the exact line (see steps 1-2 above for extracting/expanding).
2. Do a small, targeted text replace — no need for a full expand/edit/recollapse pass for a
   single-property deletion like this, but still verify before writing:
   ```python
   with open(path, 'r', encoding='utf-8-sig', newline='') as f:
       content = f.read()
   old = "  PrintPaperSize = 'Default'\\0d\\0a  PrintPaperID = 0\\0d\\0a"
   assert content.count(old) == 1, "expected exactly one occurrence"
   content = content.replace(old, '', 1)
   with open(path, 'w', encoding='utf-8-sig', newline='') as f:
       f.write(content)
   ```
   Read `old` back with `repr()` first to get the file's literal escape characters right
   (it's the 6-char sequence `\`,`0`,`d`,`\`,`0`,`a`, not a real CR/LF) — do not hand-type it.
3. Re-grep for the property name afterwards to confirm zero occurrences remain, and diff
   surrounding context (e.g. the property immediately before/after) to confirm nothing else moved.

**Only strip a property when you can identify a genuine fallback already present in the same
form** (as here, where the Paper* quartet covers the same paper-size concept). Don't blindly
delete an unfamiliar property just to silence this error — some properties have no safe
default and removing them will silently change the form's layout or behaviour rather than
just falling back gracefully. If the next `EReadError` names a property with no obvious
older equivalent, that's a sign to get the matching Profile.exe build rather than keep
stripping properties.

## Bulk edits: reflowing a macro's text or deleting one entirely

The workflow above (steps 1-6) assumes small, targeted edits that land inside the *existing*
`'...' +` wrap structure without changing its shape much. Removing many lines from a macro body,
or removing a whole named macro, is a different scale of edit and has its own traps.

### `Macros.Strings` is an array of `EventName=<macro source>` items, not one blob

The property is a Delphi `TStrings` array literal: `Macros.Strings = ( 'item1...' 'item2...' )`.
Each array item is its own Pascal string constant, wrapped across physical lines the same way
as any other long DFM string (`'...' +` continuation). The tell for where one item ends and the
next begins: a physical line whose quoted content ends *without* a trailing `' +` closes that
item; the next non-blank line starts a fresh item. Each item's decoded text has the shape
`SomeEventName=<macro source, using ^^^ for its internal line breaks>` — e.g.
`OncmbVenueMChange=Sub Main()^^^  if getIDFromControl(...`. Knowing this lets you treat "delete
this whole macro" as "delete this whole array item" rather than trying to hollow out its body in
place.

Before deleting a whole item, grep the *entire* Macros.Strings block for
`runmacro("<TheEventNameYouAreDeleting>")`. A macro isn't only invoked automatically by its
event name matching a control's event — it can also be called explicitly from another macro's
body (e.g. `form.runmacro("OnListControl1MSelectItem")`). Remove or update those call sites too;
otherwise the DFM still parses fine but the form errors at runtime when the missing macro is
invoked.

**Trap: a single logical item can splice in a literal apostrophe two different ways, and a
decoder must handle both.** Most items are one continuous `'...'` Delphi string (with an
embedded apostrophe written as doubled `''`, e.g. `'OnbtnSignClientMClick=''macro...'`). But
several of the file's own original macros instead use Delphi's character-constant splice —
`'EventName='#39'macro EventName^^^...'` — where `#39` sits *outside* any quotes as its own
token, standing for one literal apostrophe, implicitly concatenated with the quoted pieces on
either side. Both forms decode to the exact same logical string and are equally valid to write.
A naive decoder that just greedily matches everything between the first and last `'` on a
physical line will "leak" a literal `#39` into the decoded text as three stray characters
instead of turning it into an apostrophe — write your own decode/verify script to treat a
physical line as a sequence of `'...'`/`#NN` tokens (concatenating each token's contribution),
not as one big quoted blob, or its "verification" will falsely flag a corruption that isn't
there (or worse, miss a real one).

### Orphaned variables after removing a control reference

Deleting the line that references a removed control can leave a local variable dangling if a
*later* line in the same macro still uses that variable, e.g.:

```
set alist = form.controls_("lstproviders")   ' <- you delete this line (control removed)
...
alist.addrow                                  ' <- still here, now references an undefined var
```

A plain text search for the deleted control's name will **not** catch this — the orphaned line
no longer mentions the control by name. After removing any `set x = ... controls_("...")` line,
trace every later use of `x` in that same macro body and remove or adjust those too.

### The DFM text-parser's line-length limit

If your edit changes a macro's length enough that you reflow it into fresh physical lines
(rather than editing in place within the existing wrap points), you can hit a limit that never
shows up with small in-place edits: Profile's DFM text parser rejects a physical line above
roughly 90 characters (including the leading indentation, the quotes, and the trailing `' +`)
with `EParserError: Line too long on line N` when the form is next opened in the CDO designer.
Writing an edited macro back out as one long unwrapped Pascal string line — even though nothing
in the DFM format's own grammar demands wrapping — reliably trips this.

When reflowing, wrap at a fixed content length per physical line (~50 raw characters worked
reliably; the original file's own lines top out around 90 total), using the same
`'...' +` continuation style as the rest of the file. **Treat every `\XX` hex-escape run
(see the escaping-schemes note above) as an atomic unit that must never straddle a wrap
boundary.** A naive char-count-based wrapper will eventually cut between the backslash and its
two hex digits, which is exactly the `EConvertError: Invalid hex digit ''` failure mode described
above — and it's easy to trigger even at a "safe-looking" wrap width, because these escape runs
(RTF codes, the `\` operator) can occur anywhere in the source, not only at the deliberate
line-break positions you're inserting.

### Verify before writing back

After rewriting a `Macros.Strings` item (or the whole block):

1. Confirm every backslash in the rewritten field is followed by exactly two hex digits — scan
   for `\` and check `field[pos+1:pos+3]` matches `[0-9a-fA-F]{2}` for every occurrence.
2. Confirm the new file's max physical-line length doesn't exceed the original file's own max
   (a cheap proxy for the parser's undocumented limit, since the exact number isn't documented
   anywhere we've found).
3. Re-parse the rewritten `Macros.Strings` array using the same item-boundary logic you used to
   read it, and diff the result against the macro text you intended, *before* writing the file.
   This catches wrap-point corruption (split escapes, dropped/duplicated characters) that a
   visual read-through of the wrapped text easily misses.
4. Check `object `/`end` counts (or another cheap structural count) are unchanged from the
   original if you didn't intend to touch the control tree, to confirm the edit stayed scoped to
   the macros block.

**Trap: `difflib.SequenceMatcher` gets slow (100+ seconds, can time out) once the row passes
roughly 60-70 KB with lots of repetitive text** (many near-identical `Form.Controls_("...")`
calls make its LCS search pathological). Once a form has grown that large, prefer either:
- **Anchor slicing**: pick a handful of substrings that appear verbatim and unchanged on both
  sides, in file order (a control name, a macro's event-name marker, a property line just past
  where you edited), and assert each between-anchor segment is byte-identical. This is what the
  numbered steps above are already doing at small scale; it just needs to scale to more anchors
  as the file grows.
- **Full positional character diff**, when every edit is length-preserving (e.g. swapping
  `Left = 167` for `Left = 195` — same digit count) or you can align around a single known
  length delta: compare `old[i] != new[i]` for every index directly (strip the harmless
  sed-added trailing newline first) and group the differing indices into contiguous runs. This
  is O(n) and, on this kind of file, finds exactly the touched bytes in well under a second where
  `SequenceMatcher` would still be spinning.

Either way, the goal is the same as point 3 above — prove the *only* differences from the prior
version are the ones you intended — just don't reach for the slowest tool once the file is large.

None of this replaces step 6 above — still tell the user to open the file in the real CDO
designer to confirm it imports and the macro logic behaves as expected.

## Alternative workflow: decode the whole DFM field

For anything bigger than a one-line tweak, it's simpler to work on the fully decoded DFM than on
the `\0d\0a`-expanded row:

1. Split the file on CRLF, take the `100502` row, split on tabs, and Jaffa-decode field [13]
   (`\xx` -> char). **Assert that re-encoding the decoded text gives back the original field**
   before changing anything; this proves the round trip is lossless for this file.
2. Edit the decoded DFM as ordinary text (it has real CRLFs).
3. Re-encode (`\` -> `\5c`, every char < 0x20 -> `\%02x`), put it back in field [13], rejoin
   with tabs and CRLF, and write with the UTF-8 BOM.

To change macros this way, tokenise `Macros.Strings` into items (a `'...'`/`#NN` token joined to
the previous one by `+` or by no whitespace continues the item; whitespace without `+` starts a
new one). Then replace only the items you're changing, and keep every other item's raw text
byte-for-byte. Write each new item as `'...' +` lines of about 58 characters, doubling any `'`
inside a chunk. Keep the macro source itself in a `.vbs` file (lines joined with `^^^`), so it
can be compile-checked with `cscript` (see the **vb-profile-macros** skill). Afterwards
re-parse the written file and assert:
- every changed item equals the intended text;
- every other item is unchanged;
- the max physical line length is no longer than the original's;
- every `\` in the field is followed by two hex digits.

## Patterns for macro-driven forms (confirmed against `UICDO_VisualForm.pas`)

### A form that records an Encounter but is never saved itself

Typical for a call-log or launcher form. The OK button does the work, and the form record
itself is thrown away.

- Root `NeedToSave = False`.
- `OnMValidateSave = '<macro>'`, which sets `Profile.Variable("CanSave").Value = False` and
  `Profile.Variable("ShowMessage").Value = False`, then shows its own message ("This form is not
  saved, click OK..."). This blocks the toolbar Save.
- **The OK button macro** validates the mandatory fields and lists any that are missing in one
  `Profile.MsgBox`, then exits. If everything is there, it creates the Encounter/Contact in a
  `Profile.StartMapTransaction` ... `.Commit` block. Then it sets `Form.Vars("Saved") = 1` and
  calls `Form.Close`. A runtime error before `Form.Close` leaves the form open with nothing
  lost, which is the behaviour you want.
- **Cancel and the window's X are handled in one place:** `OnMCloseQuery`. The Cancel button
  just calls `Form.Close`. The close-query macro exits if `Form.Vars("Saved") = 1`. Otherwise it
  compares a snapshot of the editable controls with the one Preload saved in
  `Form.Vars("InitState")` (e.g. `Text`/`Checked` values joined with `|`). If they differ it asks
  `Profile.MsgBox("Do you want to Cancel without saving?", vbYesNo + vbQuestion, title)`, and on
  No sets `Profile.Variable("CanClose").Value = False`.
  - Source facts behind this:
    - `FormCloseQuery` only runs the `OnMCloseQuery` macro when the form `IsModified(True)` and
      is visible. An untouched form closes without asking.
    - With `NeedToSave = False` the "save changes?" dialog is skipped (answer = No). The new form
      record and its contact link are then deleted.
    - `Form.Close` from a macro does go through `FormCloseQuery`. Only printing sets
      `fRunningMacro`, which would block it.
  - The snapshot is needed because values that Preload fills in can count as "modified".
    Comparing against the snapshot asks only when the user really changed something.
- Don't save in `OnMClose`. It runs after the form has already decided to close, so it can't
  keep the form open when validation fails. The user loses their note.
- **`OnMAfterSave` never runs on a form that is never saved.** If the user asks for something
  "in the after-save event" on such a form (e.g. a "Create a Task?" prompt), put it in the OK
  macro after the Encounter commit, and explain why.

### Moving a form to another folder

The folder is the `100503` context row's NM attribute (field [9]), e.g. `"NM=Way Back"` ->
`"NM=Triage Forms"`. Keep the double quotes when the name has a space. Leave the form-def row's
`FD=` id alone; it points at that row's id, not its name.

### One-shot checkbox actions

A checkbox `OnMClick` fires on every click, including unticking. If an action must happen once
(e.g. create a task), guard it with a `Form.Vars("Done")` flag set in Preload. After the action,
set `.Checked = True` and `.Enabled = False`. Or better, replace the checkbox with a prompt at
OK time.

## HRI / field-dictionary caveat

Controls that persist a value to its own database column carry an `HRI = <integer>` property
(a field-dictionary ID from Profile's schema, e.g. `HRI = 2378104`). Not all controls have one —
some checkboxes and helper fields are used purely within macro logic and never save to a
discrete field. This file lives outside the repo's source tree, so there's no local way to look
up or validate a real HRI against Profile's field dictionary. **Never invent an HRI value for a
new field** — a made-up number could collide with an unrelated real field in the live system.
If a new persisted field is needed, tell the user it requires a real HRI registered through
their normal Profile admin/field-dictionary process, and leave the property unset until they
supply one.
