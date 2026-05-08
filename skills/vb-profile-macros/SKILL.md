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
  (see section 10).
- **No declaratives before `Sub Main()`** — `Dim`, `Const`, and any other
  declarative statement cause a syntax error if placed between the macro name
  header comment and `Sub Main()`. Declaratives may appear at module scope,
  but only *after* `Sub Main()` (i.e. after its `End Sub`). The cleanest
  pattern is to declare everything inside the `Sub`/`Function` that uses it.
  See Section 12 for the full placement rule.

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
FormatTime(aTime)          ' see FormatTime / PadTwo in section 10
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

**IMPORTANT — two different LoadProvider methods:**

```vb
' WRONG — LoadProvider takes a code string; passing an integer ID gives wrong result
Set aProvObj = Profile.LoadProvider(aRule.ProviderID)

' CORRECT — use LoadProviderById when you have an integer ID
Set aProvObj = Profile.LoadProviderById(aRule.ProviderID)
```

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

## 6. Profile Type Library — Object Access Macros

Object Access macros fire when a user opens or saves a Profile business object
(Case, Patient, Contact/Encounter, etc.). They are configured against the
object type in Profile admin and run inside the same VB scripting environment
as standalone macros, with two extra context bindings: `ChangedObject` and
`MacroResult`.

### ChangedObject — the triggering object

The object that triggered the macro is bound to `ChangedObject`. Always assign
it to a typed local immediately so the rest of the macro reads naturally.

```vb
' Case Access macro
Dim aCase
Set aCase = ChangedObject

' Contact (encounter) Access macro
Dim aContact
Set aContact = ChangedObject

' Always guard against an unbound context — exit early if absent
If aCase Is Nothing Then Exit Sub
```

### MacroResult — issuing warnings back to the host

`MacroResult.AddWarning(aText)` is the Profile-native way to surface a warning
from an Object Access macro. Profile decides how to display, log, and dismiss
it; the macro just declares the warning and returns. **Do not use `MsgBox` for
this purpose** — `MsgBox` blocks the UI thread, has no Profile-side audit, and
bypasses any host-level warning handling.

```vb
If Not bMarkerPresent Then
  MacroResult.AddWarning("Please check client record in Procura prior to engagement to check relevant information")
End If
```

Multiple `AddWarning` calls in a single macro run are accumulated and presented
together by the host.

### Performance — Object Access macros run on every open/save

Object Access macros are in the user's critical path — every Case open, every
Contact save pays whatever cost the macro incurs. Two rules follow from this:

1. **Order checks cheapest-first, with early exits.** Compare the case title
   before loading anything. If 99% of case opens don't match the target title,
   99% of opens incur essentially zero cost.
2. **Avoid nested DB walks where a single indexed lookup will do.** See the
   "Prefer Case Registry tokens" guidance in Section 7 — walking encounters
   and contacts on every open is rarely the right design when a per-case
   marker can be set once at the moment the underlying condition becomes true.

```vb
' GOOD — cheap title check first; expensive work only on the 1% path
Sub Main()
  Dim aCase
  Set aCase = ChangedObject
  If aCase Is Nothing Then Exit Sub

  Dim aTitle
  aTitle = ""
  On Error Resume Next
  aTitle = aCase.CaseTitle
  On Error GoTo 0
  If aTitle <> "Procura Data Migration" Then Exit Sub   ' early exit — no DB work

  ' ... only now do the expensive checks
End Sub
```

### Skeleton — Case Access Object macro

```vb
' Macro: ExampleCaseAccess
' -----------------------------------------------------------------------
' Case Access Object macro — fires when a Case is opened.
' -----------------------------------------------------------------------

Sub Main()
  Dim aCase
  Set aCase = ChangedObject
  If aCase Is Nothing Then Exit Sub

  ' 1. Cheapest filter first (e.g. title, type, status)
  ' 2. Next-cheapest properties on the already-loaded object
  ' 3. Indexed lookups (registry keys) before any collection walks
  ' 4. Issue warnings via MacroResult.AddWarning, not MsgBox
End Sub
```

---

## 7. Profile Type Library — Case API

### Common Case properties

| Property | Type | Notes |
|---|---|---|
| `ID` | Integer | Unique case ID |
| `CaseTitle` | String | The case's display title — e.g. `"Procura Data Migration"` |
| `Patient` | Object | The client/patient on the case |

`Patient` properties such as `IsActive` are not yet documented from the COM
type library inspection; guard them with `On Error Resume Next` until
verified, and update this section once the canonical name is confirmed.

```vb
Dim bClientActive
bClientActive = False
On Error Resume Next
bClientActive = aCase.Patient.IsActive   ' confirm exact property name
On Error GoTo 0
```

### Case Registry Keys — case-scoped metadata tokens

Case Registry Keys are **case-scoped key/value tokens** intended for macros to
record state about a case without cluttering the clinical record. They live on
the Case object itself, are loaded with it, and can be looked up directly
without a DB round-trip in the hot path.

This makes them the right tool for "has X been done on this case?" markers
that a Case Access macro needs to check on every open.

#### Adding a registry key

```vb
Dim aRegKey
Set aRegKey = aCase.AddRegistryKey("PROCURA")
aRegKey.Value = "PROCURACHECK_DONE"
```

The first argument is the **code** (a category/key name); `.Value` is the
associated string value. Multiple keys with the same code are permitted — use
`GetRegistryKeysByCode` to retrieve all of them.

#### Reading registry keys

```vb
Dim aKeys
Set aKeys = aCase.GetRegistryKeysByCode("PROCURA")

Dim bMarked
bMarked = False
Dim i
For i = 0 To aKeys.Count - 1
  If aKeys.Item(i).Value = "PROCURACHECK_DONE" Then
    bMarked = True
    Exit For
  End If
Next  'i
```

#### Idempotency

Always check whether the key is already present before adding it again,
especially in Object Access macros that may fire multiple times per
business event.

```vb
Dim aKeys
Set aKeys = aCase.GetRegistryKeysByCode("PROCURA")
Dim i
For i = 0 To aKeys.Count - 1
  If aKeys.Item(i).Value = "PROCURACHECK_DONE" Then Exit Sub   ' already marked
Next  'i

Dim aRegKey
Set aRegKey = aCase.AddRegistryKey("PROCURA")
aRegKey.Value = "PROCURACHECK_DONE"
```

### Prefer Case Registry tokens over walking encounters/contacts

When a Case Access macro needs to answer "has condition X been satisfied on
this case?", there are two architectural choices:

1. **Walk the encounter/contact graph at open time** to recompute the answer
   from primary records. Correct, but expensive — it's a per-open DB cost
   that grows with case size. See Section 8 for the encounter/contact API.
2. **Set a registry-key token at the moment the condition becomes true**,
   and check it at open time with a single in-memory lookup.

Option 2 is almost always the right design for Object Access macros because:

- It moves the cost from "every case open" (frequent) to "the one event that
  satisfied the condition" (rare).
- The check at open time is an in-memory call on the already-loaded Case,
  not a DB query.
- It composes naturally with idempotency and one-off backfills.

The companion macro that sets the token typically runs as another Object
Access macro on the underlying object (e.g. on the Contact whose creation
satisfies the condition), navigates back to its parent Case, and calls
`AddRegistryKey` if the marker is not already present.

When the token approach is not appropriate — e.g. when the condition can be
*reversed* by edits/deletions to the underlying records and the registry
key has no clean way to be revoked — fall back to walking the encounter
graph and accept the per-open cost.

---

## 8. Profile Type Library — Encounter and Contact API

Use this API when the registry-key approach in Section 7 isn't viable and the
macro genuinely needs to inspect clinical notes (encounters) and their linked
contacts on a Case.

### Loading encounters via filter

```vb
Dim aFilter
Set aFilter = Profile.CreateEncounterFilter
' Scope the filter to the case before calling .Load.
' Confirm the exact property name on your Type library — common variants
' are aFilter.CaseID = aCase.ID and Set aFilter.Case = aCase.
aFilter.CaseID = aCase.ID

Dim aEncounters
Set aEncounters = aFilter.Load
```

Scope the filter as tightly as possible *before* calling `.Load`. Loading the
full encounter set and filtering in VB is dramatically slower than letting
the server filter server-side.

### Iterating encounters and their linked contacts

Each encounter exposes a `Contacts` collection. Each contact has a `TypeCode`
(the coded contact type, e.g. `"PROCURACHECK"`).

```vb
Dim i
For i = 0 To aEncounters.Count - 1
  Dim aEncounter
  Set aEncounter = aEncounters.Item(i)

  Dim aContacts
  Set aContacts = aEncounter.Contacts   ' cache once per encounter

  Dim j
  For j = 0 To aContacts.Count - 1
    Dim aContact
    Set aContact = aContacts.Item(j)

    Dim aTypeCode
    aTypeCode = ""
    On Error Resume Next
    aTypeCode = aContact.TypeCode
    On Error GoTo 0

    If UCase(aTypeCode) = "PROCURACHECK" Then
      ' ... matched
      Exit For
    End If
  Next  'j
Next  'i
```

Notes:
- **Cache `aEncounter.Contacts` into a local** — accessing it repeatedly in
  the inner loop forces COM property reads and (on some types) lazy-loads.
- **`Exit For` short-circuits**, avoiding unnecessary work once the answer
  is known. Outer loops may need a flag-and-`Exit For` pair; do NOT use
  `GoTo` (see Section 1).
- **Compare `TypeCode` with `UCase`** if there is any chance the source data
  is mixed case.

### Navigating from a Contact back to its Case

In Contact-creation Object Access macros, the macro typically needs to walk
back from the changed Contact to its parent Case (to set a registry-key
token, for example). The exact navigation chain is not yet confirmed from
type library inspection — both `aContact.Encounter.Case` and `aContact.Case`
are plausible variants. Guard the navigation until verified:

```vb
Dim aCase
Set aCase = Nothing
On Error Resume Next
Set aCase = aContact.Encounter.Case   ' confirm exact chain
On Error GoTo 0
If aCase Is Nothing Then Exit Sub
```

Once the canonical chain is confirmed against the type library, this section
should be updated and the guard removed.

---

## 9. Form Controls API

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

---

## 10. Common Patterns

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

## 11. Macro Name Header — Required on First Line

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
error. See Section 12 for full placement rules.

---

## 12. Variable Declaration

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

## 13. Error Handling

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

## 14. Source References

- COM scripting layer (rules):    `Profile/Common/Infrastructure/Scripting/USAppointmentRule.pas`
- COM scripting layer (groups):   `Profile/Common/Infrastructure/Scripting/USProviderGroups.pas`
- COM scripting layer (profile):  `Profile/Common/Infrastructure/Scripting/USProfileEx.pas`
- Filter interface (rules):       `Profile/Common/Infrastructure/Scripting/USAppointmentRuleFilter.pas`
- Business logic (rules):         `Profile/Common/Business/UBAppointmentRules.pas`
- Technical overview:             `docs/Technical/Appointments/appointment-rules-and-templates-overview.md`

All in repo: `https://github.com/intrahealth-source/profile`
