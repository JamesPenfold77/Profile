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

### Loading groups by code and testing provider membership

```vb
Dim aGrpFilter
Set aGrpFilter = Profile.CreateProviderGroupFilter
aGrpFilter.Code = "GP"

Dim aGroups
Set aGroups = Profile.LoadProviderGroups(aGrpFilter)

If aGroups.Count > 0 Then
  Dim aGrpObj
  Set aGrpObj = aGroups.Items(0)   ' ISProviderGroup — note: Items not Item
  If aGrpObj.ContainsPPPU(aRule.ProviderID) Then
    ' provider is a member
  End If
End If
```

### ISProviderGroup properties and methods

| Member | Type | Notes |
|---|---|---|
| `ID` | Integer | Group ID |
| `Code` | String | Group code e.g. `"GP"` |
| `Name` | String | Display name |
| `ContainsPPPU(aPppuID)` | Boolean | True if provider is a current member |
| `ContainsPPPUOnDate(aPppuID, aDate)` | Boolean | True if provider was a member on the given date |
| `PPPUMembers` | ISProviders | All current provider members |

### Pattern: pre-load group objects for efficient multi-rule checking

When filtering many rules by group, load the group objects once into a dictionary
before the rule loop, then call `ContainsPPPU` per rule:

```vb
Dim aGroupObjDict
Set aGroupObjDict = CreateObject("Scripting.Dictionary")
Dim aToken
For Each aToken In Split(aProvGrpCodes, ",")
  aToken = Trim(aToken)
  If aToken <> "" And Not aGroupObjDict.Exists(aToken) Then
    Dim aGrpFilter
    Set aGrpFilter = Profile.CreateProviderGroupFilter
    aGrpFilter.Code = aToken
    Dim aGroups
    Set aGroups = Profile.LoadProviderGroups(aGrpFilter)
    If aGroups.Count > 0 Then
      aGroupObjDict.Add aToken, aGroups.Items(0)  ' note: Items not Item
    End If
  End If
Next  'aToken

' Then per rule:
Dim bProvGrpMatch
bProvGrpMatch = True
If aGroupObjDict.Count > 0 Then
  bProvGrpMatch = False
  Dim aGrpCode
  For Each aGrpCode In aGroupObjDict.Keys
    Dim aGrpObj
    Set aGrpObj = aGroupObjDict(aGrpCode)
    If aGrpObj.ContainsPPPU(aRule.ProviderID) Then
      bProvGrpMatch = True
    End If
  Next  'aGrpCode
End If
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

Usage:
```vb
aRept.AddText Join(Array( _
  aRule.RuleName, _
  FormatDateTime(aDate, 2), _
  FormatTime(aSlotStart), _
  FormatTime(aSlotEnd), _
  CStr(aRule.Duration), _
  CStr(aRule.ProviderID), _
  CStr(aRule.PosID), _
  aTypeCode), vbTab)
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

## 8. Variable Declaration

- Place all module-level `Dim` statements **at the top of the module**, before
  any `Sub` or `Function`.
- Declare variables at the top of the `Sub`/`Function` in which they are used.
- Use consistent prefixes: `a` for objects/arrays, `b` for booleans,
  `c` for constants/strings, `i`/`j` for loop counters.

---

## 9. Error Handling

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

## 10. Source References

- COM scripting layer (rules):    `Profile/Common/Infrastructure/Scripting/USAppointmentRule.pas`
- COM scripting layer (groups):   `Profile/Common/Infrastructure/Scripting/USProviderGroups.pas`
- Filter interface (rules):       `Profile/Common/Infrastructure/Scripting/USAppointmentRuleFilter.pas`
- Business logic (rules):         `Profile/Common/Business/UBAppointmentRules.pas`
- Technical overview:             `docs/Technical/Appointments/appointment-rules-and-templates-overview.md`

All in repo: `https://github.com/intrahealth-source/profile`
