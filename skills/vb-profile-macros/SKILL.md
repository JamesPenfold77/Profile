# Skill: Profile VB Macro Development

This skill defines the rules and patterns Claude must follow when writing or
reviewing VB macro code for the Intrahealth Profile EMR system.

---

## 1. VB Language Constraints

This is the Profile embedded VB scripting environment, NOT standard VBA or VBScript.
The following constraints apply:

### Forbidden syntax
- **No `GoTo` statements** — not supported. Use structured `If`/`ElseIf`/`End If`
  blocks and boolean flag variables instead.
- **No labelled `Next` statements** — `Next i` is a syntax error.
  Use `Next` alone and add the variable as a comment: `Next  'i`
- **No `On Error GoTo label`** — use `On Error Resume Next` followed by
  explicit error checks, then `On Error GoTo 0` to restore normal handling.
- **No `Format()` function** — raises "Type mismatch: 'Format'" at runtime.
  Use `FormatDateTime` for dates, and a manual `FormatTime` helper for times
  (see section 7).
- **No declaratives before `Sub Main()`** — `Dim`, `Const`, and any other
  declarative statement cause a syntax error if placed between the macro name
  header comment and `Sub Main()`. Declaratives may appear at module scope,
  but only *after* `Sub Main()` (i.e. after its `End Sub`). The cleanest
  pattern is to declare everything inside the `Sub`/`Function` that uses it.
  See Section 9 for the full placement rule.
- **`Const` only accepts a literal constant** — a bare string or numeric
  literal. Assigning the result of a function call (e.g. `Chr()`, `Chr(13) &
  Chr(10)`) raises "Expected literal constant". Use `Dim` plus a normal
  assignment statement instead for any value that isn't a literal.
- **No `ByVal`/`ByRef` at a call site** — these keywords are only valid
  inside a `Sub`/`Function`'s own parameter declaration. Writing them again
  when *calling* that Sub/Function is a syntax error, and since a macro's
  Subs/Functions are typically compiled together as one module, one bad call
  like this can fail the whole macro's compile — breaking every code path in
  the file, not just the one being called.
- **`And`/`Or` do not short-circuit** — both sides are always evaluated. A
  guard like `If bHasAppt And thisAppt.Duration > 0 Then` still touches
  `thisAppt` when `bHasAppt` is False (runtime error on `Nothing`), and
  `If UBound(a) >= 2 And a(2) = "X"` throws "Subscript out of range". Nest the
  test as two `If`s instead.

### Confirmed working (safe to use)

- **Line continuation `_`** — confirmed in production macros (DEXREPORT_TEST,
  DEXLOADORG_TEST: multi-line `If ... Or ... _` conditions, `MsgBox` text,
  `Err.Raise` arguments), including a continued `Case "A", "B", _` list.
- **`For Each` over a `Scripting.Dictionary`** (iterates keys) and over
  collections returned by `Profile.LoadShortCodes`.
- **Implicit locals in `Main`** — variables only used inside `Main` need no
  `Dim`; anything read by another Sub/Function must be a module-level `Dim`
  placed after `Main` (see Section 9 — a variable only *assigned* in `Main`
  is local to `Main` and silently Empty elsewhere).

### Correct patterns

```vb
' WRONG - GoTo not supported
If someCondition Then GoTo Skip
  DoSomething
Skip:

' CORRECT - use boolean flag
Dim bSkip
bSkip = False
If someCondition Then bSkip = True
If Not bSkip Then
  DoSomething
End If
```

```vb
' WRONG - labelled Next
For i = 0 To 10
  For j = 0 To 5
  Next j
Next i

' CORRECT - unlabelled Next with comment
For i = 0 To 10
  For j = 0 To 5
  Next  'j
Next  'i
```

```vb
' WRONG - GoTo error handler
On Error GoTo ErrHandler
  ...
ErrHandler:

' CORRECT - inline error handling
On Error Resume Next
aValue = someObject.SomeProperty
On Error GoTo 0
If aValue = "" Then
  ' handle the error case
End If
```

```vb
' WRONG - Format() not available
Format(aDate, "dd/mm/yyyy")
Format(aTime, "hh:mm")

' CORRECT - use FormatDateTime for dates, FormatTime helper for times
FormatDateTime(aDate, 2)   ' 2 = vbShortDate
FormatTime(aTime)          ' see FormatTime / PadTwo in section 7
```

```vb
' WRONG - Const with a function-call expression: "Expected literal constant"
Const cTab = Chr(9)
Const cCRLF = Chr(13) & Chr(10)

' CORRECT - Dim plus a normal assignment
Dim cTab
Dim cCRLF
cTab = Chr(9)
cCRLF = Chr(13) & Chr(10)

' Const is still fine for actual literals:
Const cSctpName = "CasetypeMapping"
```

```vb
' WRONG - ByVal/ByRef at the call site - syntax error
Function IsFaceToFace(ByVal aShortCode)
  ...
End Function

If IsFaceToFace(ByVal aType) Then   ' syntax error here

' CORRECT - ByVal/ByRef belongs only in the declaration; call plainly
If IsFaceToFace(aType) Then
```

```vb
' WRONG — declarative before Sub Main() causes a syntax error
' Macro: MyMacro
Const olMailItem = 0      ' syntax error on this line
Dim aRept                 ' syntax error on this line

Sub Main()
  ...
End Sub

' CORRECT — declare inside Sub Main (preferred) ...
' Macro: MyMacro
Sub Main()
  Const olMailItem = 0
  Dim aRept
  ...
End Sub

' ... or at module scope *after* Sub Main() if truly shared between Subs
' Macro: MyMacro
Sub Main()
  ...
End Sub

Dim aRept                 ' module-level — OK here, after Sub Main()
```

---

## 2. Profile Type Library — Key Factory Methods

Always use `Profile.` factory methods rather than `CreateObject("Profile.xxx")`.

| Purpose | Correct call |
|---|---|
| Load appointment rules | `Profile.CreateAppointmentRuleFilter` |
| Load stored queries | `Profile.MakeFindObjectQueriesLoader()` |
| Query run parameters | `CreateFindObjectQueryRunParam` |
| Create provider group filter | `Profile.CreateProviderGroupFilter` |
| Load provider groups | `Profile.LoadProviderGroups(aFilter)` |
| Load provider by **code string** | `Profile.LoadProvider(aCode)` |
| Load provider by **integer ID** | `Profile.LoadProviderById(aID)` |
| Import a Jaffa/Shortcode (.jfa) file | `Profile.JaffaImportByPath(sInPath, [sOutPath], [iReportStyle])` |
| Load existing Shortcode records for a Type | `Profile.LoadShortCodes(aType)` |
| Load a single Shortcode by Code + Type name | `LoadShortCodebyCodeSCTName(aCode, aTypeName)` (no `Profile.` prefix — global function, like `CreateFindObjectQueryRunParam` below) |
| Load another macro's source (to share code) | `Profile.LoadShortCodeByCodeType(aMacroCode, 10).MacroText` — see Section 11 |
| Log window for a long-running macro | `Profile.CreateOutputWindow` → `.AddText aLine` |
| Modal progress bar | `Profile.CreateModalProcessDisplay(False)` → `.ProcessName`, `.MaxValue`, `.Position`, `.Caption`, `.AllowCancel` |
| Registry Key values on a Provider/POS or Patient | `aObj.GetRegistryKeysByCode("KEYCODE")` → `.Count`, `.Item(0).KeyValue` |

**IMPORTANT — two different LoadProvider methods:**

```vb
' WRONG — LoadProvider takes a code string; passing an integer ID gives wrong result
Set aProvObj = Profile.LoadProvider(aRule.ProviderID)

' CORRECT — use LoadProviderById when you have an integer ID
Set aProvObj = Profile.LoadProviderById(aRule.ProviderID)
```

### JaffaImportByPath — importing a generated .jfa file

`Profile.JaffaImportByPath(BSTR sInPath, [in opt] BSTR sOutPath, [in opt] long iReportStyle) : void`

Imports a Jaffa-format lookup/shortcode file (the `.jfa` format — HEAD/LNVR/SCTP/SHTC
records etc.) directly into Profile, the same as using the file import UI. `sInPath`
is the only required argument; `sOutPath` (an optional report file) and
`iReportStyle` may be omitted in a late-bound call.

Import matches an existing record by its **Code**, not by any GUID field in the
file. When a macro generates a `.jfa` file meant to update existing records
(e.g. re-running against a changed spreadsheet), leave each record's GUID field
blank rather than generating a new one — a freshly generated GUID would not
match the GUID already stored against the existing record, so Profile would
create a duplicate instead of updating it.

Being a Profile API call, wrap it per the Section 10 error-handling pattern, and
prompt for confirmation before importing since it mutates live Profile data:

```vb
iResp = MsgBox("Import this file into Profile now?", 4 + 32, "Confirm Import")
If iResp = 6 Then   ' vbYes
  On Error Resume Next
  Profile.JaffaImportByPath cOutPath
  If Err.Number <> 0 Then
    MsgBox "Import failed: " & Err.Description
    Err.Clear
  Else
    MsgBox "Import completed."
  End If
  On Error GoTo 0
End If
```

### The SHTC (Shortcode) record layout, per the Jaffa Specification

The authoritative field layout for every Jaffa record type — including field
names and order — lives in the Jaffa Specification export (a tab-delimited
schema dump generated by Profile itself; ask the user for its path if a macro
needs to touch a record type not already covered here). For `SHTC`, in field
order (0-indexed position of each in the tab-delimited `.jfa` line):

| idx | Field | idx | Field | idx | Field |
|---|---|---|---|---|---|
| 0 | RecordType | 10 | **IsDeleted** | 20 | Tag |
| 1 | LineVersion | 11 | Privacy | 21 | MasterVersion |
| 2 | Type | 12 | **GUID** | 22 | MasterDateTime |
| 3 | Code | 13 | Color | 23 | ParentCodeGUID |
| 4 | Description | 14 | OwnerPPPU | 24 | OwnerPPPUGUID |
| 5 | TypeCode | 15 | Rate | 25 | AlertTypeLevel |
| 6 | ParentCode | 16 | Rate2 | 26 | AlwaysVisible |
| 7 | Output | 17 | AllowMultiple | 27 | GenderIdentityPreferredPronoun |
| 8 | RefSysName | 18 | ParentCodeSysId | 28 | CustomProps |
| 9 | RefSysNum | 19 | SystemID | 29 | *(EndOfFields terminator, always blank)* |

`IsDeleted` is a plain `"F"`/`"T"` boolean field, same convention as other
boolean-ish fields in this format (blank also reads as not-deleted on some
record types, e.g. `SCTP`). Writing a Code's record with `IsDeleted = "T"`
deletes that Shortcode entry on import.

### Pattern: reconcile Profile against a source list, deleting what's gone

When a macro regenerates a Jaffa file from an external source (a spreadsheet,
a query) and that source is the sole source of truth, removed rows should
delete the corresponding Profile record, not just leave it untouched. Do this
by loading what Profile already has, crossing off everything the source still
confirms, and writing a delete record for anything left over:

```vb
Dim aExistingDict
Dim aExistingShtc
Dim aItem

Set aExistingDict = CreateObject("Scripting.Dictionary")

On Error Resume Next
Set aExistingShtc = Profile.LoadShortCodes(cSctpName)
On Error GoTo 0

If Not (aExistingShtc Is Nothing) Then
  For Each aItem In aExistingShtc
    If Not aExistingDict.Exists(aItem.Code) Then
      aExistingDict.Add aItem.Code, True   ' value is unused - only key membership matters
    End If
  Next  'aItem
End If

' ... while writing each Code found in the source, remove it as matched:
'   If aExistingDict.Exists(aKey) Then aExistingDict.Remove aKey
'
' ... afterward, whatever remains in aExistingDict no longer exists in the
' source - write each as a delete record, GUID left blank same as normal
' records, relying on Code matching (see IMPORTANT note below on why GUID
' can't be populated here):
'   Join(Array("SHTC", "3", cSctpName, aDelKey, "", ..., "T", "", "", ...), cTab)
```

**IMPORTANT — `aItem.GUID` is not exposed here, confirmed by a runtime error:**
an earlier version of this pattern tried `aItem.GUID` to carry the real GUID
into delete records for precise targeting. That raised `Object doesn't
support this property or method: 'aItem.GUID'` at runtime — the object
`Profile.LoadShortCodes` returns does not expose `GUID` through the COM
scripting layer, even though `GUID` is a real field in the underlying SHTC
record (per the Jaffa Specification table above) and `aItem.Code` works fine
on the same object. This is the same class of gap documented for
`CheckDayIsActive` in Section 3 — a field/method that exists on the internal
Delphi interface but isn't surfaced on the scripting-layer object. Don't
assume a field name from the Jaffa Specification (or from another record
type's loader) will resolve as a property on a `Load*` object without
testing it — treat each property as unverified until confirmed at runtime.

Because of this, delete records here leave GUID blank exactly like
create/update records — deletion relies on Code matching, the same mechanism
JaffaImportByPath uses for updates (see above). There is currently no known
way to get a Shortcode's real GUID from this macro environment; if a future
need requires it, that would need re-testing (e.g. a different property
name) rather than reusing `aItem.GUID`.

**Confirmed working in production (2026-08-05):** this Code-matching,
blank-GUID-on-every-record design — including the delete path — was verified
against a real Profile environment (CASETYPEMAP macro v1.3, the
CaseType Reason Mapping shortcode type) and correctly handled both updates
and deletions. Treat this pattern as validated, not merely a theoretical
workaround for the missing GUID property.

`Profile.LoadShortCodes` itself was not documented anywhere before being
confirmed in a live session — if a similarly-named loader is needed for
another record type and isn't in this table, treat both the method's
existence and every property on its returned items as unverified until
confirmed the same way (by testing against Profile, or by the person who
knows Profile's COM surface) rather than guessing at a name.

### Pattern: validate a Code against a Shortcode's Description list

A common need is checking whether a value (e.g. an appointment Reason Code)
is one of the comma-delimited values in a Shortcode's Description — as
CASETYPEMAP writes them (see the reconcile pattern above). Use
`LoadShortCodebyCodeSCTName(aCode, aTypeName)` — note **no `Profile.`
prefix**, it is a global function like `CreateFindObjectQueryRunParam` in
Section 5 — to fetch a single Shortcode record by its own Code plus its
Shortcode Type name, and check membership in its Description list:

```vb
' Function: isReasonValid
' Returns True if aReasonCode is a permitted Reason Code for aCaseTypeCode,
' per the "CaseType Reason Mapping" shortcode (Code = Case Type Code,
' Description = comma-delimited Reason Codes). Intentionally uncached -
' see the note below on why, for an Object Macro on Appointment Save.
Function isReasonValid(aCaseTypeCode, aReasonCode)
  Dim aServiceList
  Dim sDescription
  Dim sHaystack
  Dim sNeedle

  isReasonValid = False
  If aCaseTypeCode = "" Then Exit Function
  If aReasonCode = "" Then Exit Function

  On Error Resume Next
  Set aServiceList = LoadShortCodebyCodeSCTName(aCaseTypeCode, "CaseType Reason Mapping")
  On Error GoTo 0
  If aServiceList Is Nothing Then Exit Function

  sDescription = ""
  On Error Resume Next
  sDescription = aServiceList.Description
  On Error GoTo 0

  sHaystack = "," & Trim(sDescription) & ","
  sNeedle = "," & Trim(aReasonCode) & ","

  isReasonValid = (InStr(1, sHaystack, sNeedle, vbTextCompare) > 0)
End Function
```

Key points:
- **Pad both sides with the delimiter before searching** —
  `"," & Description & ","` vs `"," & aReasonCode & ","` — not a bare
  `InStr(Description, aReasonCode)`. Without the padding this is a plain
  substring search with no concept of token boundaries, so checking
  `"OT"` would false-positive by matching inside `"BLUECAREOT"` even
  though `"OT"` was never a real entry in that list. The comma padding
  forces the match onto a whole comma-delimited token.
- This is faster than `Split` + loop and should be preferred: `Split`
  allocates an array and copies every substring into it up front, then a
  loop pays interpreter overhead for two more function calls (`Trim`,
  `StrComp`) per iteration. `InStr` does one native substring search over
  the string as-is — no array, one call, no loop. Negligible per call on a
  short list, but this runs on every Appointment Save across a clinic, so
  it's worth avoiding the extra interpreter overhead on that hot path.
- `vbTextCompare` as `InStr`'s 4th argument makes the match
  case-insensitive; `Trim` on both sides handles stray whitespace. The
  4-argument form requires the explicit `1` start-position argument.
- `LoadShortCodebyCodeSCTName` and `.Description` are wrapped in
  `On Error Resume Next` per Section 10, since — as the GUID incident above
  shows — an unverified Profile object/property can throw instead of
  returning `Nothing` on a miss.
- A `Split` + loop variant (walking each comma-separated value with
  `StrComp`) is a fine fallback if `InStr`'s 4-argument compare-mode form
  ever behaves unexpectedly in this dialect, but has not been needed —
  prefer the `InStr` version above.

**Do not add caching (`Static`/module-level Dictionary) here by default.**
It's tempting, but only pays off if the *same execution* calls this function
more than once for the *same* key (e.g. validating several Reason Code
fields on one appointment against the same Case Type) — check that before
reaching for it. It is actively useless, not just unnecessary, in the common
case this function was written for: an Object Macro triggered by Appointment
Save, running server-side, called exactly once per save, with no state
persisted between separate trigger firings (confirmed by the person running
it in that environment). In that shape, a `Static` cache resets to empty on
every single call — every save re-populates it from scratch and then reads
it back once — so it adds the complexity and risk of an unverified `Static`
construct for zero actual benefit. A single `LoadShortCodebyCodeSCTName`
call plus a scan over a short comma list is already about as efficient as a
one-shot lookup can be; there is no meaningfully faster way to do it once.
Only reach for the cached variant if the call-count-per-execution question
above comes back "more than once."

---

## 3. Profile Type Library — Appointment Rules API

### Loading rules

```vb
Dim aFilter
Set aFilter = Profile.CreateAppointmentRuleFilter
aFilter.DateRangeKind = 3   ' 0=sarfCurrentlyValid, 1=sarfCurrentAndFuture,
                             ' 2=sarfExpired, 3=sarfValidRange, 4=sarfAll
aFilter.StartDate = aStartDate
aFilter.EndDate   = aEndDate

Dim aRules
Set aRules = aFilter.Load   ' Returns ISCollection
```

**IMPORTANT — DateRangeKind selection:**
- Use `sarfCurrentlyValid` (0) only when you want rules valid *today*.
- When generating a report for a specific date range, use `sarfValidRange` (3)
  with `StartDate`/`EndDate` so the server pre-excludes rules whose validity
  period doesn't overlap the report window.
- `Providers` and `POSes` on the filter are server-side integer collections and
  should be populated before calling `.Load` to reduce the result set.

### Clamping the date walk to the rule's validity window

Even with `sarfValidRange`, a rule's validity period may only partially overlap
the report range. Clamp the date walk to the intersection to avoid calling
`CheckDayIsActive` on dates outside the rule.

```vb
Dim aRuleFinish
aRuleFinish = aRule.RuleFinish

Dim aWalkStart, aWalkEnd
aWalkStart = Int(aStartDate)
If Int(aRule.RuleStart) > aWalkStart Then aWalkStart = Int(aRule.RuleStart)

aWalkEnd = Int(aEndDate)
If aRuleFinish <> 0 And Int(aRuleFinish) < aWalkEnd Then
  aWalkEnd = Int(aRuleFinish)
End If

Dim aDate
aDate = aWalkStart
Do While aDate <= aWalkEnd
  If CheckDayIsActive(aRule, aDate) Then
    ' ... expand slots
  End If
  aDate = aDate + 1
Loop  'aDate
```

### Iterating rules

```vb
Dim i
For i = 0 To aRules.Count - 1
  Dim aRule
  Set aRule = aRules.Item(i)
  ' ... work with aRule (ISAppointmentRule)
Next  'i
```

### ISAppointmentRule RuleType enum values

**IMPORTANT:** `sartUnknown = 0` is the first value in the Delphi enum, so all
real/bookable rule types have values > 0. Do NOT test `RuleType = 0` expecting
to match Personal Appointment Rules — that matches nothing in practice.

| RuleType value | Constant | Description |
|---|---|---|
| 0 | `sartUnknown` | Unknown/unrecognised — never returned for real rules |
| 1 | `sartPersonal` | Personal Appointment Rule — bookable slots ✓ |
| 2 | `sartPersonalAvailable` | Personal Available — marks availability, not bookable |
| 3 | `sartCommonBlockOut` | Common Blockout — system-wide unavailability |
| 4 | `sartPersonalBlockOut` | Personal Blockout — provider-specific unavailability |

To target only Personal Appointment Rules:
```vb
If aRule.RuleType = 1 Then   ' sartPersonal only
```

### ISAppointmentRule properties

| Property | Type | Notes |
|---|---|---|
| `ID` | Integer | Unique rule ID |
| `RuleType` | Integer | See enum table above |
| `RuleName` | String | Descriptive name |
| `RuleStart` | DateTime | Rule effective from |
| `RuleFinish` | DateTime | Rule effective to — **0 means no expiry** |
| `TimeStart` | DateTime | Daily session start — available on all rule types |
| `TimeFinish` | DateTime | Daily session end — available on all rule types |
| `Duration` | Integer | Minutes — **RuleType=1 (sartPersonal) only. Raises error on other types.** |
| `Skip` | Integer | Gap between appointments (mins) — RuleType=1 only |
| `MeetingLimit` | Integer | Max concurrent — RuleType=1 only |
| `TypeCode.Code` | String | Default appt type short code — RuleType=1 only, may be nil |
| `ProviderID` | Integer | Provider — personal rules only (RuleType=1,2,4) |
| `PosID` | Integer | Point of Service ID — all rule types |
| `Priority` | Integer | 0=default, 80=blockout |
| `RuleCycleType` | Integer | 0=Absolute, 1=Weekly, 2=WeekMonthly, 5=Once |
| `RulePeriod` | Integer | Cycle period in days (Weekly) or used by Absolute |
| `RuleDayCount` | Integer | Number of active day entries |
| `RuleDay(i)` | Integer | Day index value for entry i (1-based, sorted ascending) |
| `Macro` | String | Associated macro script name |

**`CheckDayIsActive` is NOT exposed through the COM scripting layer.**
Use the `CheckDayIsActive` VB function below instead.

### CheckDayIsActive — VB reimplementation

`CheckDayIsActive` exists on the internal Delphi `IBAppointmentRule` interface
but is not exposed via `ISAppointmentRule`. Use this VB function, translated
directly from `_TBAppointmentRule.CheckDayIsActive` in `UBAppointmentRules.pas`.

RuleCycleType values: 0=Absolute, 1=Weekly, 2=WeekMonthly, 5=Once.

```vb
' CheckDayIsActive — VB reimplementation of _TBAppointmentRule.CheckDayIsActive
' Returns True if aRule fires on aDate. Pass a pure date (no time component).
' Source: Profile/Common/Business/UBAppointmentRules.pas
Function CheckDayIsActive(aRule, aDate)
  CheckDayIsActive = False

  Dim aDay
  aDay = Int(aDate)

  ' Must be within the rule's validity window
  If Int(aRule.RuleStart) > aDay Then Exit Function
  If aRule.RuleFinish <> 0 And Int(aRule.RuleFinish) < aDay Then Exit Function

  Dim aCycleDay
  Dim aCycleType
  aCycleType = aRule.RuleCycleType

  ' sarctOnce (5) — fires on every day within the validity window
  If aCycleType = 5 Then
    CheckDayIsActive = True
    Exit Function

  ' sarctAbsolute (0)
  ElseIf aCycleType = 0 Then
    Dim aMaxDayAbs
    If aRule.RulePeriod > 0 Then
      aMaxDayAbs = aRule.RulePeriod
    Else
      aMaxDayAbs = 1
    End If
    aCycleDay = (Int(aDay) - Int(aRule.RuleStart)) Mod aMaxDayAbs + 1

  ' sarctWeekly (1)
  ElseIf aCycleType = 1 Then
    ' Find Monday of the week containing RuleStart.
    ' VB Weekday: 1=Sun,2=Mon...7=Sat  (same as Delphi DayOfWeek)
    ' Delphi: i = DayOfWeek(RuleStart)-2; if i<0 then i+=7  => 0=Mon..6=Sun
    Dim iWeek
    iWeek = Weekday(aRule.RuleStart) - 2
    If iWeek < 0 Then iWeek = iWeek + 7
    Dim aBaseWeek
    aBaseWeek = Int(aRule.RuleStart) - iWeek
    Dim aMaxDayWeek
    If aRule.RulePeriod > 0 Then
      ' Round up to full weeks: period + (6 - ((period-1) mod 7))
      aMaxDayWeek = aRule.RulePeriod + (6 - ((aRule.RulePeriod - 1) Mod 7))
    Else
      aMaxDayWeek = 7
    End If
    aCycleDay = (Int(aDay) - Int(aBaseWeek)) Mod aMaxDayWeek + 1

  ' sarctWeekMonthly (2)
  ElseIf aCycleType = 2 Then
    Dim aYear, aMonth, aDayNum
    aYear   = Year(aDay)
    aMonth  = Month(aDay)
    aDayNum = Day(aDay)
    Dim aMonthStart
    aMonthStart = DateSerial(aYear, aMonth, 1)
    ' iWM = DayOfWeek(aMonthStart)-1; if iWM<1 then iWM+=7
    Dim iWM
    iWM = Weekday(aMonthStart) - 1
    If iWM < 1 Then iWM = iWM + 7
    aCycleDay = ((aDayNum - 1) Mod 7) + iWM
    If aCycleDay > 7 Then aCycleDay = aCycleDay - 7
    aCycleDay = aCycleDay + ((aDayNum - 1) \ 7) * 7

  Else
    Exit Function   ' unsupported cycle type
  End If

  ' Check aCycleDay against the rule's stored active day list
  Dim aDayCount
  aDayCount = aRule.RuleDayCount
  If aDayCount > 0 Then
    Dim j
    For j = 0 To aDayCount - 1
      If aRule.RuleDay(j) = aCycleDay Then
        CheckDayIsActive = True
        Exit Function
      End If
    Next  'j
  Else
    ' No days configured — fires only on cycle day 1
    If aCycleDay = 1 Then CheckDayIsActive = True
  End If

End Function
```

### IsSlotBooked — returns booking status string

Returns a string indicating the status of a slot:
- `""` — available (no overlapping appointment)
- `"Booked"` — overlapping non-cancelled appointment with a patient (`PatientId > 0`)
- `"Locked"` — overlapping non-cancelled appointment with no patient (e.g. a blocked slot)

`aSlotStart` and `aSlotEnd` must carry the full date+time (not just the time fraction).
Use `Profile.LoadProviderById` — NOT `Profile.LoadProvider` — when loading by integer ID.

**IMPORTANT — floating point epsilon required in overlap test:**
DateTime arithmetic using `/1440` introduces tiny floating point drift. Without an
epsilon, an appointment ending at exactly 10:45 produces `aApptEnd` fractionally
*greater* than the slot start of 10:45, causing the adjacent next slot to be falsely
marked Booked. Always use `cEpsilon = 0.5 / 1440` (half a minute) in the overlap
comparison to absorb this drift.

```vb
' WRONG — no epsilon; adjacent slot falsely matches due to floating point drift
If aApptStart < aSlotEnd And aApptEnd > aSlotStart Then ...

' CORRECT — epsilon absorbs /1440 floating point error at exact boundaries
Dim cEpsilon
cEpsilon = 0.5 / 1440   ' half a minute in DateTime units
If aApptStart < (aSlotEnd - cEpsilon) And aApptEnd > (aSlotStart + cEpsilon) Then ...
```

```vb
Function IsSlotBooked(aProviderID, aPosID, aDate, aSlotStart, aSlotEnd)
  IsSlotBooked = ""
  Dim aProvider
  Set aProvider = Profile.LoadProviderById(aProviderID)
  Dim aAppts
  Set aAppts = aProvider.LoadAppointments(aDate, "")
  Dim k
  Dim cEpsilon
  cEpsilon = 0.5 / 1440   ' half a minute — absorbs /1440 floating point drift
  For k = 0 To aAppts.Count - 1
    Dim aAppt
    Set aAppt = aAppts.Item(k)
    If aAppt.PosID = aPosID And Not aAppt.IsCancelled Then
      Dim aApptStart, aApptEnd
      aApptStart = aAppt.BookTime
      aApptEnd   = aAppt.BookTime + (aAppt.Duration / 1440)
      ' Epsilon prevents adjacent appointments (end == start) from falsely matching
      If aApptStart < (aSlotEnd - cEpsilon) And aApptEnd > (aSlotStart + cEpsilon) Then
        If aAppt.PatientId > 0 Then
          IsSlotBooked = "Booked"
        Else
          IsSlotBooked = "Locked"
        End If
        Exit Function
      End If
    End If
  Next  'k
End Function
```

### Calling IsSlotBooked in GenerateSlotReport

```vb
  ' Booking status check — sBookedStatus is "", "Booked", or "Locked"
  Dim sBookedStatus
  sBookedStatus = IsSlotBooked(aRule.ProviderID, aRule.PosID, aDate, aSlotStart, aSlotEnd)

  If bIncludeBooked Or sBookedStatus = "" Then
    aRept.AddRow
    aRowNum = aRowNum + 1
    aRept.Cells(aRowNum, 0).Value = aRule.RuleName
    aRept.Cells(aRowNum, 1).Value = aProvFullName
    aRept.Cells(aRowNum, 2).Value = FormatDateTime(aDate, 2)
    aRept.Cells(aRowNum, 3).Value = FormatTime(aSlotStart)
    aRept.Cells(aRowNum, 4).Value = FormatTime(aSlotEnd)
    aRept.Cells(aRowNum, 5).Value = CStr(aRule.Duration)
    aRept.Cells(aRowNum, 6).Value = CStr(aRule.PosID)
    aRept.Cells(aRowNum, 7).Value = aTypeCode
    aRept.Cells(aRowNum, 8).Value = sBookedStatus   ' "", "Booked", or "Locked"
  End If
```

### Calculating duration safely across rule types

`Duration` is only valid on RuleType=1 (`sartPersonal`) rules. For all other
types, calculate from `TimeStart`/`TimeFinish`:

```vb
Dim aRuleDuration
If aRule.RuleType = 1 Then
  aRuleDuration = aRule.Duration
Else
  aRuleDuration = (aRule.TimeFinish - aRule.TimeStart) * 24 * 60
End If
```

### Guarding nullable properties

`TypeCode` is nil on rules with no default appointment type. Always guard it:

```vb
Dim aTypeCode
aTypeCode = ""
On Error Resume Next
aTypeCode = aRule.TypeCode.Code
On Error GoTo 0
```

---

## 4. Profile Type Library — Provider Group API

### ISProviderGroups — use .Items(n) not .Item(n)

**IMPORTANT:** The `ISProviderGroups` collection uses `.Items(n)` (plural) to
access elements, not `.Item(n)`. Using `.Item(n)` causes a runtime error.

```vb
' WRONG
Set aGrpObj = aGroups.Item(0)

' CORRECT
Set aGrpObj = aGroups.Items(0)
```

Note: `ISCollection` (returned by appointment rule filter `.Load`) uses `.Item(n)`.
The two collections have different accessor names — always check which type you have.

### ISProviderGroup properties and methods

| Member | Type | Notes |
|---|---|---|
| `ID` | Integer | Group ID |
| `Code` | String | Group code e.g. `"GP"` |
| `Name` | String | Display name |
| `ContainsPPPU(aPppuID)` | Boolean | True if provider is a **direct** current member (does NOT recurse into sub-groups) |
| `ContainsPPPUOnDate(aPppuID, aDate)` | Boolean | True if provider was a direct member on the given date |
| `PPPUMembers` | ISProviders | Direct provider members of this group |
| `GroupMembers` | ISProviderGroups | Child groups nested inside this group |

### Provider groups are recursive — always use CollectProviderCodes

**CRITICAL:** Provider groups can contain both providers (`PPPUMembers`) and nested
child groups (`GroupMembers`). `ContainsPPPU` only tests **direct** membership —
it does NOT recurse into sub-groups.

**WRONG — misses providers in sub-groups:**
```vb
' This only checks direct PPPU members; child groups are silently ignored
If aGrpObj.ContainsPPPU(aRule.ProviderID) Then ...
```

**CORRECT — always use the recursive helper below.**

The canonical pattern is to resolve all group codes into a flat dictionary of
`Provider.Code -> Provider.ID` before the rule loop, using a recursive walk that
descends into `GroupMembers` to any depth. Use `Provider.Code` (not ID) as the
key because it is the stable, human-meaningful identifier.

```vb
' CollectProviderCodes — recursively collects Provider.Code -> Provider.ID
' into aCodeDict from aGrpObj and all its nested child groups.
' aVisitedIDs (Dictionary of group ID strings) prevents infinite loops
' from circular group references.
Sub CollectProviderCodes(aGrpObj, aCodeDict, aVisitedIDs)
  Dim aGrpID
  aGrpID = CStr(aGrpObj.ID)
  If aVisitedIDs.Exists(aGrpID) Then Exit Sub
  aVisitedIDs.Add aGrpID, 1

  ' Add direct PPPU members by Code
  Dim aMembers
  Set aMembers = aGrpObj.PPPUMembers
  Dim m
  For m = 0 To aMembers.Count - 1
    Dim aMember
    Set aMember = aMembers.Item(m)
    Dim aCode
    aCode = aMember.Code
    If aCode <> "" And Not aCodeDict.Exists(aCode) Then
      aCodeDict.Add aCode, aMember.ID
    End If
  Next  'm

  ' Recurse into child groups
  Dim aChildGroups
  Set aChildGroups = aGrpObj.GroupMembers
  Dim g
  For g = 0 To aChildGroups.Count - 1
    CollectProviderCodes aChildGroups.Items(g), aCodeDict, aVisitedIDs
  Next  'g
End Sub
```

### Pattern: resolve group codes to a flat provider code dictionary

Call this once before the rule loop. The resulting `aProviderCodeDict` maps
`Provider.Code` (string key) to `Provider.ID` (integer value).

```vb
Dim aProviderCodeDict
Set aProviderCodeDict = CreateObject("Scripting.Dictionary")

If aProvGrpCodes <> "" Then
  Dim aToken
  For Each aToken In Split(aProvGrpCodes, ",")
    aToken = Trim(aToken)
    If aToken <> "" Then
      Dim aGrpFilter
      Set aGrpFilter = Profile.CreateProviderGroupFilter
      aGrpFilter.Code = aToken
      Dim aGroups
      Set aGroups = Profile.LoadProviderGroups(aGrpFilter)
      If aGroups.Count > 0 Then
        Dim aVisited
        Set aVisited = CreateObject("Scripting.Dictionary")
        CollectProviderCodes aGroups.Items(0), aProviderCodeDict, aVisited
      End If
    End If
  Next  'aToken
End If

' Populate server-side provider filter from the resolved IDs:
' aProvCode                    = "SMITH"  (string key   — Provider.Code)
' aProviderCodeDict(aProvCode) = 1042     (integer value — Provider.ID)
If aProviderCodeDict.Count > 0 Then
  Dim aProvCode
  For Each aProvCode In aProviderCodeDict.Keys
    aFilter.Providers.Add aProviderCodeDict(aProvCode)   ' value is the integer ID
  Next  'aProvCode
End If
```

### Per-rule membership check using Provider.Code

```vb
' Load provider by integer ID — use LoadProviderById, NOT LoadProvider
' (LoadProvider takes a code string; LoadProviderById takes an integer ID)
Dim aRuleProvCode
aRuleProvCode = ""
On Error Resume Next
aRuleProvCode = Profile.LoadProviderById(aRule.ProviderID).Code
On Error GoTo 0

Dim bProvGrpMatch
bProvGrpMatch = True
If aProviderCodeDict.Count > 0 Then
  bProvGrpMatch = (aRuleProvCode <> "" And aProviderCodeDict.Exists(aRuleProvCode))
End If
```

### Loading a provider by integer ID vs code string

```vb
' Load by code string (e.g. from user input or a stored code)
Set aProvider = Profile.LoadProvider("SMITH")

' Load by integer ID (e.g. from aRule.ProviderID)
Set aProvider = Profile.LoadProviderById(aRule.ProviderID)

' WRONG — LoadProvider("123") treats "123" as a code string, not an ID
Set aProvider = Profile.LoadProvider(aRule.ProviderID)
```

---

## 5. Profile Type Library — Stored Query API

```vb
Dim aFilter
Set aFilter = Profile.MakeFindObjectQueriesLoader()
aFilter.Name = "Q1 - My Query Name"
Dim aReport
Set aReport = aFilter.Load

Dim aRunParam
Set aRunParam = CreateFindObjectQueryRunParam
aRunParam.RowCountLimit = 10000000
aRunParam.OutputFileName = aFOFileName
aRunParam.IsAppendFile = True

Dim aQuery
Set aQuery = aReport.Item(0)
aQuery.Parameters(0).AskValue = "param1value"
aQuery.Parameters(1).AskValue = "param2value"
aQuery.Run(aRunParam)
```

---

## 6. Form Controls API

```vb
' Get a control by name
Set aControl = Controls_("ControlName")

' List box / checked list
aControl.RowCount          ' number of rows
aControl.Checked(i)        ' True/False
aControl.Cells(i, 0)       ' value in column 0 of row i
aControl.Cells(i, 1)       ' value in column 1 of row i

' Combo box
Controls_("cboName").Text  ' selected text
```

**IMPORTANT — visibility property is `IsVisible`, not `Visible`:** CDO Form
controls fetched via `Controls_()` expose `IsVisible`, not the standard VCL
`Visible` property. Setting `.Visible` on one of these objects is a runtime
error. This was confirmed against a real form-repositioning macro
(`SetServiceFields`) that toggles controls' visibility/position based on a
selected service.

```vb
' WRONG - Controls_() objects don't expose Visible
aCtrl.Visible = False

' CORRECT
aCtrl.IsVisible = False
```

`Enabled` and `Top`/`Left` are unaffected — those set normally as shown in the
`SetServiceFields` pattern below.

### Pattern: reposition/hide a set of controls by a keyed lookup

A common CDO Form need: given some driving value (e.g. a selected Service
Name), show and position one set of controls, and hide/disable every other
control group tied to a different value. Encode each group as a
`"key1;key2|control1;control2"` string (keys before `|`, controls after,
both `;`-separated), and drive Top/Left from array position rather than
literal per-row property values:

```vb
Sub SetServiceFields(ServiceName)
  Dim aRows(6)
  Dim aLefts(3)
  Dim aRowParts
  Dim aServices
  Dim aControlNames
  Dim aCtrl
  Dim bMatch
  Dim i
  Dim j
  Dim iPos
  Dim iTop

  aRows(0) = "IndivualSupport;GroupSupport;Respite;Meal;Home Maintenance;Domestic Assistance;Transport|lblVolunteer;rbVolunteerYes;rbVolunteerNo"
  aRows(1) = "IndivualSupport;Meal|lblLocation;rbCommunity;rbHome"
  aRows(2) = "Meal|lblMealType;rbMain;rbLight;rbSnack;rbBeveridge"
  aRows(3) = "Meal|lblPrepOffsite;rbOffsiteYes;rbOffsiteNo"
  aRows(4) = "Meal;Respite|lblOverNight;rbOvernightYes;rbOvernightNo"
  aRows(5) = "Respite|lblMealsProvided;rbMealsGivenYes;rbMealsGivenNo"
  aRows(6) = "Transport|lblClientEngagement;edtClientTime"

  aLefts(0) = 75
  aLefts(1) = 160
  aLefts(2) = 235
  aLefts(3) = 320

  For i = 0 To UBound(aRows)
    aRowParts = Split(aRows(i), "|")
    aServices = Split(aRowParts(0), ";")
    aControlNames = Split(aRowParts(1), ";")

    bMatch = False
    For j = 0 To UBound(aServices)
      If Trim(aServices(j)) = ServiceName Then bMatch = True
    Next  'j

    ' Row Top starts at 460 for matched rows, +40 per row index
    iTop = 460 + (i * 40)

    For j = 0 To UBound(aControlNames)
      Set aCtrl = Nothing
      On Error Resume Next
      Set aCtrl = Controls_(Trim(aControlNames(j)))
      On Error GoTo 0

      If Not (aCtrl Is Nothing) Then
        If bMatch Then
          aCtrl.IsVisible = True
          aCtrl.Enabled = True
          aCtrl.Top = iTop
          If j = 0 Then
            aCtrl.Left = 20
          Else
            iPos = j - 1
            If iPos <= UBound(aLefts) Then aCtrl.Left = aLefts(iPos)
          End If
        Else
          aCtrl.IsVisible = False
          aCtrl.Enabled = False
          aCtrl.Top = 555
        End If
      End If
    Next  'j
  Next  'i
End Sub
```

Key points:
- The first control in each row's list is treated as the row's Label and
  gets `Left = 20`; subsequent controls take the next position from a fixed
  `Left` array (`75, 160, 235, 320`).
- `Controls_()` is wrapped in `On Error Resume Next` per Section 10 — a
  control name from the data that doesn't exist on this particular form
  instance shouldn't abort the whole loop.
- Fixed-size `Dim aRows(6)` / `Dim aLefts(3)` plus one assignment per line is
  used instead of `Array(...)` with line-continuation (`_`). That was written
  before line-continuation was confirmed working (see Section 1 "Confirmed
  working") — either style is fine now; one assignment per line is still
  easier to diff.

---

## 7. Common Patterns

### Date and time formatting

`Format()` is **not available** in the Profile VB scripting environment — it raises
a "Type mismatch: 'Format'" runtime error. Use the following instead:

```vb
' Dates — use FormatDateTime with vbShortDate (2)
FormatDateTime(aDate, 2)   ' e.g. "08/04/2026" per locale short date setting

' Times — Format() not available; use this helper pair instead:
Function PadTwo(n)
  If n < 10 Then
    PadTwo = "0" & CStr(n)
  Else
    PadTwo = CStr(n)
  End If
End Function

Function FormatTime(aTime)
  ' Extracts hh:mm from a DateTime value (ignores date portion)
  Dim aTotalMins
  aTotalMins = CInt(Int((aTime - Int(aTime)) * 1440 + 0.5))
  FormatTime = PadTwo(aTotalMins \ 60) & ":" & PadTwo(aTotalMins Mod 60)
End Function
```

### Building a comma-separated code list from a checked listbox

`GetCodes` reads column 1, which holds the code string (e.g. appointment type
code, provider group code). Use this for lists where column 1 is the code.

```vb
Function GetCodes(aControlName)
  Dim aList
  Set aList = Controls_(aControlName)
  Dim aCode
  aCode = ""
  Dim i
  For i = 0 To aList.RowCount - 1
    If aList.Checked(i) = True Then
      aCode = aCode & aList.Cells(i, 1) & ", "
    End If
  Next  'i
  If aCode <> "" Then aCode = Mid(aCode, 1, Len(aCode) - 2)  ' remove trailing ", "
  GetCodes = aCode
End Function
```

Note: trim **2** characters (`, `), not 1.

### POS location list column layout

The `LstLocation` list is populated from a providers filter and uses this column layout:

| Column | Content | Type |
|---|---|---|
| 0 | `ThisItem.ID` | Integer — POS ID, used for rule matching via `aRule.PosID` |
| 1 | `ThisItem.Code` | String — POS code e.g. `"WGTN"` |
| 2 | `ThisItem.FullName` | String — display name |

**IMPORTANT:** `aRule.PosID` is an integer. The POS filter must compare against
column 0 (the ID), not column 1 (the code). These are different values and will
never match each other.

LoadList population code:
```vb
For i = 0 To aPOSList.Count - 1
  Set ThisItem = aPOSList.Item(i)
  aListControl.AddRow
  aRowNum = aRowNum + 1
  aListControl.Cells(aRowNum, 0) = ThisItem.ID        ' POS ID — for rule matching
  aListControl.Cells(aRowNum, 1) = ThisItem.Code      ' POS code — for display/SQL
  aListControl.Cells(aRowNum, 2) = ThisItem.FullName  ' Full name — for display
Next  'i
```

### Getting selected POS IDs for rule matching

Use `GetPosIDs` (reads column 0) rather than `GetCodes` (reads column 1) when
the result will be matched against `aRule.PosID`:

```vb
Function GetPosIDs(aControlName)
  Dim aList
  Set aList = Controls_(aControlName)
  Dim aIDs
  aIDs = ""
  Dim i
  For i = 0 To aList.RowCount - 1
    If aList.Checked(i) = True Then
      aIDs = aIDs & aList.Cells(i, 0) & ", "   ' column 0 = POS ID
    End If
  Next  'i
  If aIDs <> "" Then aIDs = Mid(aIDs, 1, Len(aIDs) - 2)
  GetPosIDs = aIDs
End Function
```

Then in Main:
```vb
aApptCodes        = GetCodes("LstApptType")       ' codes -> column 1
aApptProvGrpCodes = GetCodes("LstProviderGroup")  ' codes -> column 1
ApptPosIDs        = GetPosIDs("LstLocation")      ' IDs   -> column 0
```

### Duration range parameter

```vb
Function GetDurationParameter
  Select Case Controls_("cboDuration").Text
    Case "<60 Mins"       GetDurationParameter = "0,59"
    Case "60 to 90 Mins"  GetDurationParameter = "60,90"
    Case "90 to 120 Mins" GetDurationParameter = "90,120"
    Case ">120 Mins"      GetDurationParameter = "121,600"
    Case Else             GetDurationParameter = "0,600"
  End Select
End Function
```

Note: always include a space between `Case` and the string literal.

### Temporary file handling

```vb
Dim FSO
Set FSO = CreateObject("Scripting.FileSystemObject")
Dim cOutputFolder
cOutputFolder = FSO.GetSpecialFolder(2)   ' 2 = temp folder
Dim aFileName
aFileName = cOutputFolder & "\" & FSO.GetTempName

' Always clean up before and after use
If FSO.FileExists(aFileName) Then FSO.DeleteFile aFileName, True
```

### Result dictionary key collision avoidance

When merging results from multiple sources (SQL queries + rule-based), prefix
keys to avoid collisions:

```vb
' SQL query results  -> key is aFields(0)  e.g. "10045"
' Rule-based results -> key is "RULE_" & aRule.ID  e.g. "RULE_88"
```

---

## 8. Macro Name Header — Required on First Line

**ALWAYS place the macro name as a comment on the very first line of every macro.**

When a runtime error occurs, Profile displays the first few lines of the macro
source in the error dialog. Having the macro name on line 1 immediately identifies
which macro failed — essential when multiple macros share similar code or when
errors are reported by users who may not know which macro they were running.

```vb
' Macro: SlotAvailabilityReport
' -----------------------------------------------------------------------
' Slot Availability Report — generates available/booked slot list
' for a date range, provider group, and POS selection.
' -----------------------------------------------------------------------

Sub Main()
  ...
End Sub

Dim aRept   ' module-level stored report — declared AFTER Sub Main()
```

The name comment must be **line 1** — not after a blank line, not after a `Dim`
statement. Profile counts from the top of the file when truncating the error
display, so anything pushed below line 1 may not appear.

**Nothing may appear between the header comment and `Sub Main()` except more
comments.** Declaratives (`Dim`, `Const`, etc.) placed there produce a syntax
error. See Section 9 for full placement rules.

### Version history block

**Every time a new version of a macro is generated, add a version block**
immediately after the macro name line, above the description. Each block
follows this exact format:

```vb
'----------------------------------------------------------
'Version 1.0
'Author: Intrahealth Date: 17-Sep-24
'1 to 2 line Brief description
'----------------------------------------------------------
```

History accumulates in **descending order — latest version first** — so the
most recent block sits directly under the macro name line, with older
versions stacked below it:

```vb
' Macro: SlotAvailabilityReport
'----------------------------------------------------------
'Version 1.1
'Author: Intrahealth Date: 03-Nov-24
'Added POS filter and fixed epsilon rounding on slot overlap check
'----------------------------------------------------------
'Version 1.0
'Author: Intrahealth Date: 17-Sep-24
'Initial version — available/booked slot list for a date range
'----------------------------------------------------------
' -----------------------------------------------------------------------
' Slot Availability Report — generates available/booked slot list
' for a date range, provider group, and POS selection.
' -----------------------------------------------------------------------

Sub Main()
  ...
End Sub
```

Every block is still just a `'` comment, so this stays entirely within the
"comments only before `Sub Main()`" rule above — do not let a version bump be
the reason a `Dim`/`Const` sneaks above `Sub Main()`.

Some older macros (e.g. DEXREPORT_TEST) put `Sub Main()` on line 1 and the
version history as comments inside it — that also works; keep whichever
layout the macro already uses.

### Macro file name and description track the version

A macro exported as a `.jfa` (a `TYPT` record — see the **jfa-format** skill,
"Macro (TYPT) files") has a description field that Profile shows in its macro
list, and the file name usually repeats it, e.g.
`Macro - (DEXREPORT_TEST) Generate Dex Report as XML file (TEST v11.15 - output mode real, anonymised or both).jfa`.
On every versioned update, change **both** the file name and the TYPT
description to the new `vX.Y - <short summary>`, and keep the previous file
as a `.bak` (the old file name makes it obvious which version it holds).
A stale file name (e.g. still "v11.1" when the macro is internally 11.4) makes
it easy to import or edit the wrong version.

---

## 9. Variable Declaration

### Placement rule

**Nothing may appear between the macro name header and `Sub Main()` except
comments.** `Dim`, `Const`, and any other declarative statement in that region
cause a syntax error. The Profile VB parser only accepts declaratives at module
scope *after* `Sub Main()` (i.e. after its `End Sub`).

In order of preference:

1. **Inside the `Sub`/`Function` that uses it** — the default. Applies to
   locals, loop counters, and anything whose lifetime does not need to span
   multiple routines.
2. **At module scope after `Sub Main()`** — for state that genuinely must be
   shared between routines (e.g. a module-level stored report object
   referenced from several helper subs).

```vb
' WRONG — Const/Dim before Sub Main() is a syntax error
' Macro: MyMacro
Const cSomething = 0       ' syntax error
Dim aSharedState           ' syntax error

Sub Main()
  ...
End Sub
```

```vb
' CORRECT — declare inside the Sub/Function (preferred)
' Macro: MyMacro
Sub Main()
  Const cSomething = 0
  Dim aLocalState
  ...
End Sub
```

```vb
' CORRECT — module-level Dim placed after Sub Main() for genuinely shared state
' Macro: MyMacro
Sub Main()
  Set aSharedState = SomeFactory
  DoHelperWork
End Sub

Sub DoHelperWork
  aSharedState.AddRow
End Sub

Dim aSharedState   ' module-level — OK here, after Sub Main()/other Subs
```

### Naming conventions

- Use consistent prefixes: `a` for objects/arrays, `b` for booleans,
  `c` for constants/string literals, `i`/`j` for loop counters.

---

## 10. Error Handling

Wrap all file I/O and Profile API calls in error handling:

```vb
On Error Resume Next
  ' ... risky operation
  If Err.Number <> 0 Then
    aRept.AddText "Error: " & Err.Description
    Err.Clear
  End If
On Error GoTo 0
```

---

## 11. Sharing code between macros (ExecuteGlobal)

A macro can pull in another macro's Subs/Functions/module variables at run time:

```vb
Sub Main()
 ExecuteGlobal Profile.LoadShortCodeByCodeType("GLBLFORMS", 10).MacroText
 ExecuteGlobal Profile.LoadShortCodeByCodeType("DEXLOADORG_TEST", 10).MacroText
 ...
```

- `10` is the Shortcode type for macros; `.MacroText` is the macro's source.
- Everything in the loaded macro becomes global, **including its own
  `Sub Main`**. The caller's `Main` that is already running carries on
  normally, but any *later* call to `Main` runs the library's version
  (confirmed with `cscript`). Generally: a Sub/Function with the same name in
  two loaded macros is silently replaced by the one loaded last — avoid name
  clashes between a macro and the libraries it loads.
- Its module-level variables — even ones declared `Private` — are readable
  from the calling macro (confirmed with `cscript`; read them inside
  `On Error Resume Next` in case Profile's engine differs). Prefer calling the
  library's public functions over reaching into its variables, though: if the
  library changes, a caller that reads its internals breaks silently.
- A library macro that sets file paths at module level (e.g. DEXLOADORG_TEST's
  `aPath` to `OrganisationData V3.xml`, per `Profile.CurrentUserCode`) runs
  that code at `ExecuteGlobal` time — check those paths when a report reads
  the "wrong" file.

## 12. Testing macros offline with cscript

Windows' own `cscript.exe` runs VBScript, so a macro can be compile-checked and
unit-tested on the dev machine without Profile. This caught real bugs several
times (a VBScript `And` guard, a stub-invisible `Set` of `Empty`, off-by-one
list counts) before the macro was ever imported.

**Compile check (whole macro).** VBScript compiles the entire file before
running anything, and a file whose top level only *declares* `Sub Main` never
calls it — so appending one line and running it proves the whole macro
parses, without executing any Profile code:

```bash
python -c "s=open('macro.vbs',encoding='utf-8').read(); open('syntax.vbs','w',encoding='utf-8',newline='').write(s.replace('\n','\r\n')+'\r\nWScript.Echo \"compiled OK\"\r\n')"
cscript //nologo syntax.vbs
```

(If the check script itself fails to build — e.g. a Python escape error — the
old `syntax.vbs` is still on disk and will print "compiled OK" for the
*previous* version. Delete it first, or put the version number in the echo.)

**Unit tests with stubs.** Copy the routines under test out of the macro
(slice by `Function Name` ... `End Function`), then add VBScript `Class` stubs
for the Profile objects they touch and a few test calls. Patterns that work:

- Stub `ErrorMessage` as `Sub ErrorMessage(a,b,m) : WScript.Echo "LOG: " & m : End Sub`
  to see every log line.
- Stub `Profile` as a global object: `Class PF ... End Class` then
  `Dim Profile : Set Profile = New PF`.
- A stub collection that real code walks with `For Each` must be a COM
  enumerable — a VBScript `Class` isn't. Return a `Scripting.Dictionary`
  whose **keys** are the stub objects (`d.Add aObj, 1`); `For Each` over a
  Dictionary yields its keys.
- Real code that does `Set x = Profile.LoadSomething(...)` needs the stub to
  return an **object**, not an `Array()` — `Set` of an array fails (and, under
  `On Error Resume Next`, silently leaves `x` unset).
- VBScript can't `Set` a variable to `Empty`, so the `IsEmpty(aEncounter.Attendance)`
  branch can't be driven from a stub property; test the `Is Nothing` branch
  instead and note the other as untestable offline.
- Feed stubs from real exported data where possible (e.g. parse the
  `CaseType Reason Mapping` shortcode `.jfa` export into `AddSC` stub calls)
  so tests run against the live mapping, not hand-typed values.
- **Include a negative control**: after a test passes, deliberately break
  the input (e.g. swap two XML elements) and confirm the test fails — this
  proves the test can actually detect the problem.

**Tooling traps from this environment:** writing the harness through a bash
heredoc often mangles backslashes (Windows paths, `\N` in Python strings
become escape errors). Write harness files with the Write tool, or use
forward-slash paths where the path doesn't matter. MSXML 3.0 and 6.0
(`Msxml2.DOMDocument`, `MSXML2.DOMDocument.6.0`, `MSXML2.XMLSchemaCache.6.0`)
and `Scripting.FileSystemObject`/`Scripting.Dictionary` are all available to
`cscript`, so XML-building code can be tested for real.

## 13. Building and validating XML (MSXML)

Macros that produce XML for external systems (e.g. the DEX upload in
DEXREPORT_TEST — see the **dex-reporting** skill) build it with MSXML:

```vb
Set aXMLDoc = CreateObject("Msxml2.DOMDocument")        ' MSXML 3.0
Set aRoot = aXMLDoc.createNode(1, "DEXFileUpload", "")  ' 1 = NODE_ELEMENT
aXMLDoc.AppendChild aRoot
' child elements via a small AddXmlNode(parent, name, value) helper
aXMLDoc.save aFileName
```

**Element order matters when the schema uses `xs:sequence`.** An element
written out of order is rejected ("invalid child element" / "Element X is
unexpected according to content model") even though its value is fine, and
optional elements (`minOccurs="0"`) must still sit in their sequence slot.
When several Subs each append elements to the same parent, the order of the
*calls* is the element order — keep a comment at the call site listing the
required order, and flag-then-emit where one routine computes a value that
the schema wants later (e.g. compute Quantity early, write it after TotalCost).

**Validate against the XSD before saving** so errors show up in the macro's
own log instead of the recipient's rejection report:

1. Load the XSD into an `MSXML2.DOMDocument.6.0` and add it to an
   `MSXML2.XMLSchemaCache.6.0` (`aSchemas.Add "", aXsdDoc` — empty target
   namespace).
2. The document to check must also be `DOMDocument.6.0` — an MSXML 3.0 doc
   can't use a 6.0 schema cache. Copy it with `aCheck.loadXML aXMLDoc.xml`.
3. Set `aCheck.validateOnParse = False` **before** `loadXML` (otherwise an
   invalid document fails to load at all), and
   `aCheck.setProperty "MultipleErrorMessages", True`.
4. `Set aErr = aCheck.validate()` → `aErr.errorCode = 0` means valid; otherwise
   loop `aErr.allErrors` (`.length`, `.item(i).reason`, `.item(i).errorXPath`).
   `errorXPath` looks like `/DEXFileUpload/Sessions[1]/Session[3]/DessertCount[1]`
   — select the `Session[3]` part and read its ID child to tell the user which
   record is wrong.
5. **`^`/`$` in `xs:pattern`.** In the XSD standard (which MSXML follows) `^`
   and `$` are *literal* characters and every pattern is already anchored to
   the whole value. Some schemas (DEX's, written for .NET, which treats them as
   anchors) use `^...$` — under MSXML every value then fails. Strip a leading
   `^` and trailing unescaped `$` from each `xs:pattern` in the loaded XSD
   before adding it to the schema cache; that reproduces the check the
   recipient applies.
6. If the XSD file is missing, log a warning and carry on — don't block the run.

Schema validation only catches structure and types. **Business rules** (e.g.
"ServiceTypeId 302 requires Quantity") aren't in the XSD — those elements are
usually optional there — so check them separately against whatever data
source defines them.

**File names.** Windows doesn't allow `\ / : * ? " < > |` in file names —
use `yyyy-mm-dd HHMM` (no colon) for timestamps, and replace those characters
(e.g. with `-`) in any user-supplied part such as a query name. Commas are fine.

**Sharing output that contains patient data.** When the output holds PHI and
may need to be shared for troubleshooting, give the macro an output switch
(real file / anonymised file / both) rather than anonymising by hand. Build
the anonymised copy from the *finished* document (so it always has the same
structure) with dummy IDs kept consistent wherever the same ID appears, write
a private real→dummy mapping file alongside it, and mark it (e.g. an XML
comment "NOT FOR UPLOAD") — see the **dex-reporting** skill for the DEX
implementation.

---

## 14. Source References

- COM scripting layer (rules):    `Profile/Common/Infrastructure/Scripting/USAppointmentRule.pas`
- COM scripting layer (groups):   `Profile/Common/Infrastructure/Scripting/USProviderGroups.pas`
- COM scripting layer (profile):  `Profile/Common/Infrastructure/Scripting/USProfileEx.pas`
- Filter interface (rules):       `Profile/Common/Infrastructure/Scripting/USAppointmentRuleFilter.pas`
- Business logic (rules):         `Profile/Common/Business/UBAppointmentRules.pas`
- Technical overview:             `docs/Technical/Appointments/appointment-rules-and-templates-overview.md`

All in repo: `https://github.com/intrahealth-source/profile`
