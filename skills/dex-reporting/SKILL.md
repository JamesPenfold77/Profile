---
name: dex-reporting
description: Generating the Australian DSS Data Exchange (DEX) bulk-upload XML from Profile (CHSP/FMHSS etc.) and diagnosing DEX rejections. Use when changing the DEXREPORT / DEXLOADORG macros, when a DEX upload returns validation or business-rule errors, or when adding DEX fields (e.g. CHSP Stage 3). Covers how the macros fit together, the XSD sequence-order trap, OrganisationData.xml requirement codes, common rejection causes and their fixes, and sharing output without PHI.
---

# Skill: DEX (Data Exchange) Reporting from Profile

Built up on the NWRH (North and West Remote Health, formerly the `QCG` folder)
DEX work in Sep 2026 — `Profile/Customers/NWRH/`. The same macro set and DEX
rules apply to any Profile customer reporting CHSP / FMHSS / Emergency Relief
activity to DSS.

## The pieces

| Piece | Role |
|---|---|
| **DEXREPORT_TEST** macro | Runs a stored query (FOQ) of Dex Items for a date range, builds `DEXFileUpload` XML (Clients, Cases, Sessions), validates it, saves it. The one to edit for output changes. |
| **DEXLOADORG_TEST** macro | Library loaded via `ExecuteGlobal`. Reads `OrganisationData.xml` into lookups: per-ServiceTypeId requirement flags (`RequiresAssistanceQuantity`, `RequiresTimeMinutes`, Stage 3 `Requires*`, ...), `Add*IfNeeded` element writers, Outlet+Activity → OutletActivityId. |
| **GLBLFORMS** macro | Shared form helpers (also `ExecuteGlobal`-loaded), incl. `GetSLK` (reads the client's `SLK581` Registry Key, or `"Not Found"`). |
| **CASETYPEMAP** macro | Builds the `CaseType Reason Mapping` shortcode (Code = Case Type, Description = comma list of valid appointment Reason Codes) from `Program, Cases & Service Mapping.xlsx`. |
| `OrganisationData.xml` | Downloaded from the DEX portal. Activities, outlets, ServiceTypeIds and each ServiceType's `ServiceTypeSpecificRequirements/Code`s. **Has no version or export date inside it** — tell versions apart by file date and content (Stage 3 files contain codes like `SUBCONTRACTORDELIVERED`). |
| `DEXFileUpload.xsd` | The DEX upload schema. Kept next to `OrganisationData*.xml`; the report validates against it before saving. |
| CHSP Service Contact CEF form | Captures the Stage 3 answers per Contact (`Subcontractor` HRI + a pipe-delimited `ServiceDetails` HRI decoded by `DecodeServiceDetails`). |

Settings are at the top of DEXREPORT_TEST's `Main`: `aQueryName` (which FOQ),
`aStartdate`/`aEnddate`, `bVerbose` (Info log lines on/off), `iOutputMode`
(1 real file, 2 anonymised file, 3 both). Paths switch on
`Profile.CurrentUserCode` (a developer's local paths vs `H:\`), in both
DEXREPORT_TEST and DEXLOADORG_TEST — check both when a run reads or writes the
wrong place. Output name: `DEX-TEST-<query name> <yyyy-mm-dd HHMM>.xml`.

## Session element order (the #1 cause of schema rejections)

`Session` in `DEXFileUpload.xsd` is an `xs:sequence`. Elements out of order are
rejected even when every value is correct. Required order (optional elements
may be absent, but never out of place):

```
SessionId, CaseId, SessionDate, ServiceTypeId, TotalNumberOfUnidentifiedClients,
FeesCharged, MoneyBusinessCommunityEducationWorkshopCode, InterpreterPresent,
ServiceSettingCode, SessionClients, TimeMinutes, TotalCost, Quantity, Topic,
HardshipTypeCode, ExternalReferralDestinationCode, ExtraItems,
IsSubcontractorDelivered, IsVolunteerDirectService, ServiceLocationSettingCode,
IsOvernightSupportIncluded, EngagementTimeMinutes, TripTimeMinutes, TripDistanceKm,
IsMealProvided, IsMealCookedOffsite, IsItemsTextureModified,
MainMealCount, LightMealCount, DessertCount, BeverageCount, SnackCount
```

Notable traps: TimeMinutes/TotalCost/**Quantity** (Quantity is *after*
TotalCost); Trip**Time** before Trip**Distance**; Overnight straight after
Location; meal counts end Dessert, Beverage, **Snack**. Re-check the XSD before
adding any new element — slot it in, don't append. Validate locally (MSXML
recipe and the `^...$` pattern trap: **vb-profile-macros** skill, "Building
and validating XML").

## Business rules (not in the XSD)

The XSD marks most elements optional; what's actually *required* comes from
`OrganisationData.xml`:

- `ServiceType/ServiceTypeSpecificRequirements/Code` per ServiceTypeId:
  `ASSISTANCEQUANTITY`, `ASSISTANCEMINUTES`, `ASSISTANCECOSTAMOUNT`, and the
  CHSP Stage 3 codes `SUBCONTRACTORDELIVERED`, `VOLUNTEERDIRECTSERVICE`,
  `SERVICELOCATIONSETTINGCODE`, `OVERNIGHTSUPPORTINCLUDED`, `ENGAGEMENTTIME`,
  `TRIPTIME`, `TRIPDISTANCE`, `MEALPROVIDED`, `MEALCOOKEDOFFSITE`,
  `ITEMSTEXTUREMODIFIED`, `MAINMEALCOUNT`, `LIGHTMEALCOUNT`, `DESSERTCOUNT`,
  `BEVERAGECOUNT`, `SNACKCOUNT`.
- `ActivitySpecificRequirement/Code = FEESCHARGEDSESSIONMANDT` → FeesCharged.
- Each OrganisationActivity lists the ServiceTypeIds it allows — a session
  whose ServiceTypeId isn't in its case's activity is rejected by DEX.

Stage 3 fields apply to sessions from **01-Jul-2026**; earlier sessions are
written without them. NWRH also had a one-off rule: CHSP sessions 01-Jul to
30-Sep-2026 (before the new CEF form reached production) get per-Case-Type
**defaults** for any uncaptured Stage 3 answer (`ApplyStage3Defaults`,
from `New Dex Changes 2026 - Stage 3.docx`); "Meal type not required when Meal
Provided = No". Treat those as customer decisions, not DEX rules.

## Common DEX errors → cause → fix

| DEX / log message | Cause | Fix |
|---|---|---|
| `The element 'Session' has invalid child element 'X'` | Element order (above) | Fix the order in the macro |
| `Quantity is a required field` (or TimeMinutes) | Session written without the assistance element — e.g. the Reason Code check skipped it, or no appointment | Macro now excludes invalid-Reason sessions and logs "missing Quantity" before saving; find the cause in the log |
| `Appointment Reason Code 'X' is not valid for Case Type Y` (macro log) | Service/reason booked on the wrong case (e.g. meal reason `CLON` on a Domestic Assistance case, respite `CHSPR` on Personal Care) | Move the encounter to the correct case, or correct the reason. Checked against the session's **own** Case Type |
| `OutputCode ... is not numeric: SERV-0010` / `OutputCode missing` (macro log) | Non-CHSP service (HCP, QCCS community transport, care-management) on a CHSP case, or a service with no DEX ServiceTypeId as its OutputCode | Correct the service on the encounter, or give the service its numeric ServiceTypeId as OutputCode. Session is excluded until then |
| `MacId is a required field` / `Client id: K... requires additional data for Has MacId` | Client on a CHSP case has no **MAC Ref Number** card (read by `GetMacId`) | Add the card to the client |
| `DEXOUTLET Registry key missing for POS <name>` → blank `OutletActivityId` (XSD: unsignedInt) | Case's Service POS has no `DEXOUTLET` Registry Key | Add the key with the DEX OutletName (e.g. `Townsville`) — or fix the case's POS if it's wrong |
| `Cannot detach clients from a case until the clients have been removed from all associated sessions` | Case already in DEX with a different ClientId — ClientId is `SourceRef` if set, else Filenum, so adding a SourceRef later changes it | Check whether the client's SourceRef changed or the case's patient was changed after first upload |
| `Encounter has a null link for Appointment` (macro log) | Encounter not created from an appointment | Link/book the appointment; meanwhile TimeMinutes comes from the encounter duration |
| Many "missing mandatory X answer" lines for one session | Usually the wrong-case-type problem above (defaults are per Case Type, requirements per ServiceTypeId) — or a pre-Stage 3 date before that gate existed | See the Reason Code row |

DEX returns two different CSV shapes: **schema** errors (`Line Number, Line
Position, Error Message`) and **business-rule** errors (`Entity Type, Parent
Entity Details, Entity Id, Error Description, Error Type`). Group business
errors by `Entity Type` + message with digits masked to see the pattern; map
`Entity Id` (SessionId) back to the XML's ServiceTypeId and element tags.

Before diagnosing a response, confirm it came from the current run — once, an
old file was renamed and re-uploaded (byte-identical XML). Compare hashes /
session date ranges against the report period.

## PHI

DEX files contain names, DOB, addresses, disabilities and service history.
Default to inspecting **structure only** (tag names, IDs, codes, counts) and
masking values in error text. Only read values when the user confirms the
file is dummy/test data. For sharing, use `iOutputMode = 2` or `3`:

- `... ANON.xml` — dummy IDs (`ANON-C0001`/`ANON-K0001`/`ANON-S0001`, new
  per run, consistent across Client/Case/Session), names `Test`/`Client0001`,
  DOB → 1 January same year, SLK rebuilt (`LINES0101yyyy` + real sex digit;
  `Not Found` kept), Suburb/`9999`, MacId dummy only where present; everything
  else kept. Starts with an XML comment "NOT FOR DEX UPLOAD" and is
  XSD-validated.
- `... ANON map.csv` — real → dummy IDs. **Contains real IDs — the user
  keeps it; never share or read it.**
- The on-screen log and the DEX response CSV still contain real IDs/Filenums.

## Source files (NWRH)

`Profile/Customers/NWRH/`: the macros (`Macro - (DEXREPORT_TEST) ... (TEST vX.Y - ...).jfa`,
`Macro - (DEXLOADORG_TEST) ...jfa`, `Macro - (GLBLFORMS) ...jfa`),
`Case Type Reason Mapping Short Code (LKUP).jfa`, `OrganisationData.xml`,
`DEXFileUpload (1).xsd`, `Program, Cases & Service Mapping.xlsx`,
`New Dex Changes 2026 - Stage 3.docx`, `chsp-guide-to-data-exchange-dex-stage-3-changes.pdf`,
DEX responses in `Results/`. Macro file format: **jfa-format** skill, "Macro
(TYPT) files".
