# Slot Availability Report — User Guide

**Macro:** `TESTAPPTRULE`
**Version:** April 2026

---

## 1. Purpose

The Slot Availability Report macro generates a list of appointment slots for a
specified date range, filtered by provider group, location (POS), and appointment
type. Each slot is marked as **Available**, **Booked**, or **Locked**, giving
practice managers a clear picture of scheduling capacity.

The report is produced as a Profile Stored Report List, which can be viewed,
sorted, and printed from within Profile.

---

## 2. How to Run

The macro is invoked by calling `GenerateSlotReport` from `Sub Main()`. To change
the report parameters, edit the values at the top of `Main`:

```
aStartDate     — first date to include (e.g. #01-APR-2026#)
aEndDate       — last date to include  (e.g. #30-APR-2026#)
aApptTypeCodes — comma-separated appointment type codes to filter on
                 e.g. "CONSULT" or "CONSULT,FOLLOWUP"
                 Leave as "" to include all appointment types
aProvGrpCodes  — comma-separated provider group codes to filter on
                 e.g. "SPEC1" or "SPEC1,GP"
                 Leave as "" to include all providers
aPosIDs        — comma-separated POS (location) integer IDs to filter on
                 e.g. "3" or "3,4"
                 Leave as "" to include all locations
bIncludeBooked — True  = show all slots (available, booked, and locked)
                 False = show available slots only
```

---

## 3. Report Output

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

## 4. Processing Logic

### 4.1 Overview

The macro works by loading **Personal Appointment Rules** from Profile and expanding
each rule into individual time slots for each day in the report range. For each
generated slot it checks whether an existing appointment already occupies that slot,
and records the result.

### 4.2 Step 1 — Build Filter Dictionaries

Three in-memory dictionaries are built from the input parameters before any API
calls are made:

**Appointment Type Dictionary** (`aApptTypeDict`)
Maps each requested appointment type code to `1`. Used later to quickly test
whether a rule's default appointment type is in the requested set. If
`aApptTypeCodes` is empty, the dictionary remains empty and all appointment types
are accepted.

**POS Dictionary** (`aPosDict`)
Maps each requested POS ID string to `1`. Built for reference — the POS IDs are
also passed directly to the server-side rule filter (see step 4.3).

**Provider Code Dictionary** (`aProviderCodeDict`)
This is the most important dictionary. It maps `Provider.Code` (string) to
`Provider.ID` (integer) for every provider who is a member of any requested
provider group. Provider groups are **recursive** — a group can contain both
individual providers and nested child groups. The macro handles this by calling
`CollectProviderCodes` recursively for each group, descending into child groups
via `GroupMembers` to any depth. A visited-group guard prevents infinite loops
if circular group references exist.

The resulting dictionary is a flat, de-duplicated set of all transitive provider
members across all requested groups.

### 4.3 Step 2 — Load Appointment Rules from Server

A `ISAppointmentRuleFilter` is configured and submitted to the server:

- `DateRangeKind = 3` (sarfValidRange) — returns only rules whose validity period
  overlaps the requested date range, reducing the result set.
- `StartDate` / `EndDate` — the report date range.
- `POSes` — the server filters rules to the requested POS locations.
- `Providers` — the integer Provider IDs from `aProviderCodeDict` are added,
  so the server only returns rules for providers in the requested groups.

Only rules of **RuleType = 1** (Personal Appointment Rules, `sartPersonal`) are
processed. Other rule types (blockouts, availability markers) are skipped.

### 4.4 Step 3 — Per-Rule Filtering

For each returned rule, two client-side filters are applied before any slot
generation occurs:

**Appointment Type Filter**
The rule's default appointment type code (`TypeCode.Code`) is read. If
`aApptTypeDict` is populated and the rule's type code is not in it, the rule is
skipped. If `TypeCode` is nil (no default type configured on the rule), it is
treated as an empty string and will not match a non-empty filter.

**Provider Group Membership Filter**
The rule's `ProviderID` is used to load the provider via `Profile.LoadProviderById`
(integer ID lookup — not `Profile.LoadProvider` which takes a code string). The
provider's `Code` is then tested against `aProviderCodeDict`. This check is
redundant when a group filter was specified (the server already filtered by
provider), but acts as a safety net to ensure providers not in any requested group
are never included.

If both filters pass, provider FullName is resolved via `Profile.LoadProviderById`
and cached in `aProvNameDict` keyed by ProviderID, to avoid repeated API calls
across the slot loop.

### 4.5 Step 4 — Date Walk

The date walk is **clamped** to the intersection of the report date range and the
rule's own validity window (`RuleStart` to `RuleFinish`). This avoids calling
`CheckDayIsActive` on dates where the rule is not in effect, even if those dates
fall within the report range.

For each date in the clamped range, `CheckDayIsActive` is called to determine
whether the rule fires on that day. This is a VB reimplementation of the internal
Delphi function, which is not exposed via the COM scripting layer. It handles all
four rule cycle types:

| CycleType | Value | Description |
|---|---|---|
| sarctOnce | 5 | Active on every day within the validity window |
| sarctAbsolute | 0 | Repeats on a fixed day cycle from RuleStart |
| sarctWeekly | 1 | Repeats on specific days of the week |
| sarctWeekMonthly | 2 | Repeats on specific week-of-month positions |

### 4.6 Step 5 — Slot Expansion

For each active day, slots are generated by walking from the session start time
(`TimeStart`) to the session end time (`TimeFinish`) in steps of
`Duration + Skip` minutes. A slot is only emitted if it fits completely within
the session window (with a one-second tolerance to absorb floating point drift).

The slot start time carries the **full date and time** — i.e. the date integer
plus the fractional time from `TimeStart`. This is important for the booking
overlap test, which compares against `aAppt.BookTime` (a full DateTime value).

### 4.7 Step 6 — Booking Status Check (`IsSlotBooked`)

For each generated slot, `IsSlotBooked` is called to determine whether an existing
appointment occupies that slot. It loads all appointments for the provider on that
date via `aProvider.LoadAppointments(aDate, "")` and tests each against the slot
window using a strict overlap condition:

```
appointment starts before slot ends
AND
appointment ends after slot starts
```

An **epsilon of 0.5/1440** (half a minute in DateTime units) is applied to both
sides of the overlap test. This absorbs the tiny floating point drift that results
from dividing appointment duration (in minutes) by 1440 to convert to DateTime
fractional days. Without this epsilon, an appointment ending at exactly 10:45
would produce an `aApptEnd` value fractionally greater than 10:45, causing the
adjacent next slot (10:45–11:00) to be falsely marked as Booked.

Only non-cancelled appointments at the matching POS are considered. The function
returns:

| Return | Meaning |
|---|---|
| `""` | No overlapping appointment — slot is available |
| `"Booked"` | Overlapping appointment with a patient (`PatientId > 0`) |
| `"Locked"` | Overlapping appointment with no patient (blocked slot) |

### 4.8 Step 7 — Row Output

If `bIncludeBooked` is `True`, all slots are written to the report regardless of
status. If `False`, only slots with status `""` (available) are written. The
booking status string is written directly to column 8 of the report row.

### 4.9 Step 8 — Save and Display

After all rules are processed, the report is saved under the current user
(`aRept.Save 0`) and displayed (`aRept.PrintIt`).

---

## 5. Helper Functions

### PadTwo(n)
Formats an integer as a two-digit zero-padded string. Used by `FormatTime`.

### FormatTime(aTime)
Extracts the time portion of a DateTime value and returns it as `hh:mm`.
Uses integer arithmetic on the fractional day value rather than `Format()`,
which is not available in the Profile scripting environment.

### CheckDayIsActive(aRule, aDate)
Returns `True` if the appointment rule fires on the given date. This is a VB
reimplementation of the internal Delphi method `_TBAppointmentRule.CheckDayIsActive`,
which is not exposed through the COM scripting layer.

### CollectProviderCodes(aGrpObj, aCodeDict, aVisitedIDs)
Recursively walks a provider group and all its nested child groups, collecting
`Provider.Code → Provider.ID` into `aCodeDict`. The `aVisitedIDs` dictionary
prevents infinite recursion if circular group references exist in the data.

### IsSlotBooked(aProviderID, aPosID, aDate, aSlotStart, aSlotEnd)
Tests whether any existing non-cancelled appointment occupies the given slot
window. Returns `""`, `"Booked"`, or `"Locked"` as described in section 4.7.

---

## 6. Known Limitations

- The report is generated from **appointment rules only**. Ad-hoc slots or
  appointments that exist outside a rule pattern will not appear as available slots.
- The POS filter is applied server-side by integer ID. If `aPosIDs` is passed as
  a comma-separated string, each value is individually parsed and added to the filter.
- The appointment type filter matches only on the rule's **default** appointment
  type code (`TypeCode.Code`). Rules with no default type configured will not match
  a non-empty appointment type filter.
- `IsSlotBooked` loads all appointments for a provider on a given date for every
  slot check. For providers with many appointments or large date ranges, this may
  be slow. A future optimisation would be to cache appointments per provider/date.

---

## 7. Debugging Notes

- The macro name `TESTAPPTRULE` is placed on the first line. When a runtime error
  occurs, Profile displays the first few lines of the macro in the error dialog,
  making it immediately clear which macro failed.
- Any `stop` statements remaining in the code are debug breakpoints and should be
  removed before deploying to a production environment.
