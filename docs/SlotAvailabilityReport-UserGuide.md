# Slot Availability Report — User Guide

**Macro:** `APPTSLOTREPT`
**Version:** April 2026

---

## 1. Purpose

The Slot Availability Report macro generates a list of appointment slots for a
specified date range, filtered by provider group, location (POS), appointment
type, and slot duration. Each slot is marked as **Available**, **Booked**, or
**Locked**, giving practice managers a clear picture of scheduling capacity.

The report is produced as a Profile Stored Report List, which can be viewed,
sorted, and printed from within Profile.

---

## 2. How to Invoke

The macro is stored as a short code in Profile and loaded at runtime by a calling
form:

```vb
Dim sApptRept
sApptRept = Profile.LoadShortCodeByCodeType("APPTSLOTREPT", 10).MacroText
executeGlobal sApptRept
```

Once loaded, the calling form invokes `GenerateSlotReport` directly, passing all
parameters.

For standalone testing, edit the values in `Sub Main()` at the top of the macro
and run it directly from the Profile macro editor.

---

## 3. Parameters

`GenerateSlotReport` accepts the following parameters:

| Parameter | Type | Description |
|---|---|---|
| `aStartDate` | Date | First date to include in the report |
| `aEndDate` | Date | Last date to include in the report |
| `aApptTypeCodes` | String | Comma-separated appointment type short codes to filter on. `""` = all types |
| `aProvGrpCodes` | String | Comma-separated provider group codes to filter on. `""` = all providers |
| `aPosIDs` | String | Comma-separated POS (location) integer IDs to filter on. `""` = all locations |
| `aApptDuration` | String | Duration band to filter on (see values below). `""` = all durations |
| `bIncludeBooked` | Boolean | `True` = show all slots; `False` = show available slots only |

### Duration Band Values (`aApptDuration`)

| Value | Meaning |
|---|---|
| `"<60 Mins"` | Slots with duration less than 60 minutes |
| `"60 to 90 Mins"` | Slots with duration 60 to 90 minutes (inclusive) |
| `"90 to 120 Mins"` | Slots with duration 91 to 120 minutes (inclusive) |
| `">120 Mins"` | Slots with duration greater than 120 minutes |
| `""` | No duration filter — all durations included |

The duration filter is applied at the **appointment rule level** — rules whose
configured slot duration falls outside the requested band are skipped entirely,
avoiding unnecessary date walking and slot expansion.

---

## 4. Report Output

The report displays one row per generated appointment slot with the following columns:

| Column | Description |
|---|---|
| RuleName | Internal appointment rule name (hidden — width 0) |
| Provider | Provider full name |
| Date | Slot date |
| Start | Slot start time (hh:mm) |
| End | Slot end time (hh:mm) |
| Duration | Slot duration in minutes |
| POS | Point of Service (location) ID |
| ApptType | Appointment type code |
| Booked | Booking status: blank = available, `Booked` = patient booked, `Locked` = slot blocked with no patient |

The **RuleName** column is intentionally hidden (width 0) but is included as the
first column so that if `OnDblClick` navigation is added later, the rule context
is available from the selected row.

---

## 5. Processing Logic

### 5.1 Overview

The macro works by loading **Personal Appointment Rules** from Profile and expanding
each rule into individual time slots for each day in the report range. For each
generated slot it checks whether an existing appointment already occupies that slot,
and records the result.

### 5.2 Step 1 — Resolve Duration Filter

`GetDurationRange` converts the `aApptDuration` label into a minimum and maximum
minute value (`aDurMinMins`, `aDurMaxMins`). If `aApptDuration` is empty, the
function returns `False` and no duration filtering is applied. These values are
used in step 5.5 to skip rules whose duration falls outside the requested band.

### 5.3 Step 2 — Build Filter Dictionaries

Three in-memory dictionaries are built from the input parameters before any API
calls are made:

**Appointment Type Dictionary** (`aApptTypeDict`)
Maps each requested appointment type code to `1`. Used later to quickly test
whether a rule's default appointment type is in the requested set. If
`aApptTypeCodes` is empty, the dictionary remains empty and all appointment types
are accepted.

**POS Dictionary** (`aPosDict`)
Maps each requested POS ID string to `1`. The POS IDs are also passed directly
to the server-side rule filter.

**Provider Code Dictionary** (`aProviderCodeDict`)
Maps `Provider.Code` (string) to `Provider.ID` (integer) for every provider who
is a member of any requested provider group. Provider groups are **recursive** —
a group can contain both individual providers and nested child groups. The macro
handles this by calling `CollectProviderCodes` recursively for each group,
descending into child groups via `GroupMembers` to any depth. A visited-group
guard prevents infinite loops if circular group references exist.

The resulting dictionary is a flat, de-duplicated set of all transitive provider
members across all requested groups.

### 5.4 Step 3 — Load Appointment Rules from Server

A `ISAppointmentRuleFilter` is configured and submitted to the server:

- `DateRangeKind = 3` (sarfValidRange) — returns only rules whose validity period
  overlaps the requested date range, reducing the result set.
- `StartDate` / `EndDate` — the report date range.
- `POSes` — the server filters rules to the requested POS locations.
- `Providers` — the integer Provider IDs from `aProviderCodeDict` are added,
  so the server only returns rules for providers in the requested groups.

Only rules of **RuleType = 1** (Personal Appointment Rules, `sartPersonal`) are
processed. Other rule types (blockouts, availability markers) are skipped.

### 5.5 Step 4 — Per-Rule Filtering

For each returned rule, three client-side filters are applied before any slot
generation occurs:

**Duration Filter**
The rule's `Duration` (integer minutes) is compared against `aDurMinMins` and
`aDurMaxMins`. If the rule's duration falls outside the requested band, the rule
is skipped entirely. This is the most efficient filter — it avoids the date walk
and all subsequent processing for non-matching rules.

**Appointment Type Filter**
The rule's default appointment type code (`TypeCode.Code`) is read. If
`aApptTypeDict` is populated and the rule's type code is not in it, the rule is
skipped. `TypeCode` is guarded with `On Error Resume Next` as it may be nil.

**Provider Group Membership Filter**
The rule's `ProviderID` is used to load the provider via `Profile.LoadProviderById`
(integer ID lookup — not `Profile.LoadProvider` which takes a code string). The
provider's `Code` is then tested against `aProviderCodeDict`.

If all three filters pass, the provider FullName is resolved via
`Profile.LoadProviderById` and cached in `aProvNameDict` keyed by ProviderID, to
avoid repeated API calls across the slot loop.

### 5.6 Step 5 — Date Walk

The date walk is **clamped** to the intersection of the report date range and the
rule's own validity window (`RuleStart` to `RuleFinish`). This avoids calling
`CheckDayIsActive` on dates where the rule is not in effect.

For each date in the clamped range, `CheckDayIsActive` is called to determine
whether the rule fires on that day. It handles all four rule cycle types:

| CycleType | Value | Description |
|---|---|---|
| sarctOnce | 5 | Active on every day within the validity window |
| sarctAbsolute | 0 | Repeats on a fixed day cycle from RuleStart |
| sarctWeekly | 1 | Repeats on specific days of the week |
| sarctWeekMonthly | 2 | Repeats on specific week-of-month positions |

### 5.7 Step 6 — Slot Expansion

For each active day, slots are generated by walking from the session start time
(`TimeStart`) to the session end time (`TimeFinish`) in steps of
`Duration + Skip` minutes. A slot is only emitted if it fits completely within
the session window (with a one-second tolerance to absorb floating point drift).

The slot start time carries the **full date and time** — the date integer plus
the fractional time from `TimeStart` — so the booking overlap test compares
correctly against `aAppt.BookTime`.

### 5.8 Step 7 — Booking Status Check (`IsSlotBooked`)

For each generated slot, `IsSlotBooked` loads all appointments for the provider
on that date and tests each against the slot window using a strict overlap
condition. An **epsilon of 0.5/1440** (half a minute) is applied to both sides
of the test to absorb floating point drift from `Duration / 1440` arithmetic,
preventing adjacent slots from being falsely marked Booked.

| Return | Meaning |
|---|---|
| `""` | No overlapping appointment — slot is available |
| `"Booked"` | Overlapping non-cancelled appointment with a patient |
| `"Locked"` | Overlapping non-cancelled appointment with no patient |

### 5.9 Step 8 — Row Output and Save

If `bIncludeBooked` is `True`, all slots are written to the report. If `False`,
only available slots (`sBookedStatus = ""`) are written. After all rules are
processed the report is saved under the current user (`aRept.Save 0`) and
displayed (`aRept.PrintIt`).

---

## 6. Helper Functions

| Function | Description |
|---|---|
| `PadTwo(n)` | Formats an integer as a two-digit zero-padded string |
| `FormatTime(aTime)` | Extracts hh:mm from a DateTime value using integer arithmetic (Format() is unavailable in Profile scripting) |
| `GetDurationRange(aApptDuration, aMinMins, aMaxMins)` | Converts a duration label to min/max minutes; returns False if no filter |
| `CheckDayIsActive(aRule, aDate)` | VB reimplementation of the internal Delphi method — not exposed via COM |
| `CollectProviderCodes(aGrpObj, aCodeDict, aVisitedIDs)` | Recursively resolves a provider group tree to a flat Provider.Code dictionary |
| `IsSlotBooked(aProviderID, aPosID, aDate, aSlotStart, aSlotEnd)` | Returns booking status string for a slot |

---

## 7. Known Limitations

- The report is generated from **appointment rules only**. Ad-hoc slots outside
  a rule pattern will not appear.
- The appointment type filter matches only on the rule's **default** appointment
  type code. Rules with no default type will not match a non-empty type filter.
- The duration filter is applied at the **rule level**. All slots generated by a
  rule have the same duration, so rule-level filtering is equivalent to slot-level
  filtering.
- `IsSlotBooked` loads all appointments for a provider on a given date for every
  slot check. A future optimisation would cache appointments per provider/date.

---

## 8. Debugging Notes

- The macro name `APPTSLOTREPT` is placed on the very first line so that Profile
  displays it in the error dialog when a runtime error occurs.
- Remove any `stop` debug statements before deploying to production.
