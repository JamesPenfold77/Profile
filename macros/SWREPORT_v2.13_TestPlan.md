# SWREPORT v2.13 Test Plan

## Setup

Before any testing, capture a known-good **baseline**:

1. **In a test Profile environment**, run the existing production v2.7 (or whatever version is currently live) for a fixed reporting period. Something small is fine for a first pass — e.g. **one week** of data, enough to have cases/encounters/appointments without being slow. Save the output.
2. Then for each subsequent test, run v2.13 for the **same exact period** so outputs can be compared.
3. **Also plan a 3-month run** for the performance test at the end.

Keep each v2.13 output file with a clear name (e.g. `v2.13_1week_testrunA.xlsx`).

---

## Section 1 — Regression: unchanged sections must match baseline

Purpose: confirm v2.13 hasn't silently broken any counts that were correct in v2.7.

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 1.1 | **Appointment Summary section — all rows, all columns** | Same numbers as v2.7 baseline (except the two swapped rows) | Every cell matches except "Client Contact" and "Client Related Consult" rows — those should be swapped relative to v2.7 but have the same values |
| 1.2 | **Number of Encounters section — existing POS/Provider/MilService columns** | Same numbers as v2.7 baseline | Row-by-row match on cols 3 through (end of MilServices). The 7 new columns are additions — ignore them for this test. |
| 1.3 | **Non-Specified row gone** | Row removed from both Encounters and Per Presenting sections | Row labeled "Non-Specified" is not present |
| 1.4 | **Total not linked to a case row gone** | Row removed from Encounters section | Row labeled "Total not linked to a case" not present |
| 1.5 | **Highest Presenting section — all cells** | Same numbers as v2.7 baseline for existing columns | Match |
| 1.6 | **Monitoring codes section** | Same numbers as v2.7 baseline for existing columns | Match |

---

## Section 2 — Cases section expansion (v2.10)

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 2.1 | **6 rows present under Cases section** | Three "- Social Work" + three "- Social Work (HSB)" rows | All 6 labels appear, in the expected order |
| 2.2 | **Social Work rows match v2.7 baseline** | The first 3 rows (Social Work) have same numbers as the 3 rows in v2.7 baseline, except Open Cases column | Match for New Cases, Cases Closed; Open Cases differs (now "as at end date" not "as at today") |
| 2.3 | **Open Cases - Social Work uses end date, not today** | The description should read "as at DD/MM/YYYY" where DD/MM/YYYY is the report end date | Description string is correct |
| 2.4 | **HSB case type resolves** | No MsgBox warning appears when the macro runs. If Profile has no SWHSB cases in the period, the rows appear with all zeros. If it has some, they appear with counts. | No "Case type SWHSB not found" MsgBox. If you DO see the MsgBox, the case-type code needs checking. |
| 2.5 | **HSB row totals are independent of Social Work totals** | A case that's classed as SWHSB in Profile appears in the HSB rows only, not the Social Work rows | Sum of "New Cases - Social Work" + "New Cases - Social Work (HSB)" ≤ total new cases across all case types in the period |

---

## Section 3 — New columns (v2.11)

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 3.1 | **Column structure** | Order: `Type, Data details, Total, POS×11, Providers×N, MilServices×7, Gender×3, Ethnicity×4` | Count 7 new columns on the right side; check headers match template exactly including trailing spaces: `Male `, `Female`, `Gender Diverse `, `NZ Maori `, `Pakeha/NZ European`, `Pasifika`, `Other` |
| 3.2 | **Group-header row (row 1) present** | Row above the column headers with labels in the first column of each group | Labels: `Locations` in col 4, `Providers` in first provider col, `Service` in first milservice col, `Gender` in col "Male ", `Ethnicity` in col "NZ Maori " |
| 3.3 | **Gender bucket rules** | Pick any single row (e.g. New Cases - Social Work): sum of Male + Female + Gender Diverse = Total column | `Total == Male + Female + GenderDiverse` on that row |
| 3.4 | **Ethnicity bucket rules** | Same row: sum of NZ Maori + Pakeha/NZ European + Pasifika + Other = Total column | `Total == Maori + Pakeha + Pasifika + Other` on that row |
| 3.5 | **Gender bucketing — spot check** | Pick 3 patients from the case list in Profile, note their `Patient.Sex` values. Manually check which bucket they should land in. | Each patient counted in exactly one Gender column |
| 3.6 | **Ethnicity bucketing — MoH prioritisation** | Find a patient in Profile with multiple ethnicities including Maori (code 21). They should be in the "NZ Maori " bucket, not any other. Try a patient with only code 11. They should be in Pakeha. Try a patient with code 30. They should be in Pasifika. Try a patient with code 40 (Asian). They should be in Other. | All four bucketing rules work correctly |
| 3.7 | **Empty/missing Sex** | If any patients in your dataset have blank/NULL Sex, they go to Gender Diverse | Count matches expectation |
| 3.8 | **Empty ethnicity codes** | Patients with all 6 ethnicity codes blank → Other bucket | Count matches |

---

## Section 4 — Demographic Data section (v2.12)

This is the highest-risk section because it's a brand-new cross-tab built by a new sub.

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 4.1 | **Section present and positioned correctly** | New "Demographic data" header row between "Number of Per Presenting" and "Highest Presenting Reasons", with 7 rows after it | Position correct, 7 rows with exact labels: `Gender - Male `, `Gender - Female`, `Gender Diverse `, `Ethnicity - NZ Maori `, `Ethnicity - Pakeha/NZ European`, `Ethnicity - Pasifika`, `Ethnicity - Other` |
| 4.2 | **Description text appears only on first Gender and first Ethnicity row** | Gender - Male row has description text, Gender - Female and Gender Diverse rows have blank. Ethnicity - NZ Maori has description text, rest have blank. | Match template |
| 4.3 | **Gender rows Total sum = Ethnicity rows Total sum** | Both sums equal total unique patients in the report period | `Male_total + Female_total + GenderDiverse_total == Maori_total + Pakeha_total + Pasifika_total + Other_total` |
| 4.4 | **Total col matches "Total Number Of Individuals" row above** | Above this section, there's a "Total Number Of Individuals" row with a Total value. Both Gender sum and Ethnicity sum should equal that value (if patient population is encounters-based as designed). | `Gender_sum == Ethnicity_sum == TotalNumberOfIndividuals row Total` |
| 4.5 | **Self-crossings blank** | Gender - Male row: Gender columns (Male, Female, Gender Diverse) should all be blank or "0". Similarly for other Gender rows. Ethnicity - NZ Maori row: Ethnicity columns all blank. Similarly for other Ethnicity rows. | 3 Gender cells blank on each Gender row (9 blank cells total); 4 Ethnicity cells blank on each Ethnicity row (16 blank cells total) |
| 4.6 | **Cross-tab cells populated** | Gender - Male row: NZ Maori column should contain count of unique Male AND Maori patients. This should be ≤ min(Male_total, Maori_total). | Value populated and plausible |
| 4.7 | **POS/Provider/MilService columns populated on all rows** | Each Demographic row has counts in POS/Provider/MilService columns | Non-zero values where expected; zeros grayed out for absent buckets |
| 4.8 | **Row sum check — POS columns** | For Gender - Male row: sum of 11 POS columns ≤ Total. (Could be less if some patients have no POS, or more if patients are counted at multiple POSs but unique per bucket per POS — my dedup is per (demo_row, col_bucket, patient), so a male patient at 2 POSs counts in both POS columns, meaning sum CAN exceed Total.) | Plausible; expect POS_sum ≥ Total if many patients visit multiple POSs |

⚠ **Key check for 4.8:** if you see the POS-column sum much larger than the Total, that's expected behaviour (unique-patient per POS, not unique-patient overall). Not a bug unless it seems wildly inflated.

---

## Section 5 — Performance (v2.13)

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 5.1 | **Same-period regression** | Run v2.13 for the same 1-week period as v2.7 baseline. All unchanged numbers from Section 1 still match. Additionally, numbers are identical between multiple runs of v2.13 on the same data. | No change in outputs; caching is transparent |
| 5.2 | **1-month timing** | Run v2.13 on 1 month of data. Note wall-clock time. Then run the same macro (without caching — pre-2.13 version if available) for the same period. | v2.13 ≤ pre-2.13 time. Ideally noticeably faster, but same-time is acceptable (means the caches aren't hurting) |
| 5.3 | **3-month timing** | Run v2.13 on the problem case — 3 months of data. Note whether it completes without timing out. | Completes. Note wall-clock time for record. |
| 5.4 | **Run twice in same session (cache warm)** | Run v2.13 once, then close/reopen report and run again for a different period. Macro shouldn't carry cache state between runs. | Both runs produce correct output (caches get reinitialised in `Main()`) |

---

## Section 6 — Edge cases and error handling

| # | Test | Expected | Pass criterion |
|---|------|----------|----------------|
| 6.1 | **Empty reporting period** | Run for a date range with no data | Macro completes, produces report with zero counts, no crash |
| 6.2 | **Patient with no Sex, no Ethnicity codes** | If such a patient exists and has encounters, they contribute to Gender Diverse and Other buckets | Counted correctly |
| 6.3 | **Patient with only blank strings in all ethnicity codes** | Goes to Other | Counted correctly |
| 6.4 | **Case with no ClosedOn set (still open)** | Should appear in "All Open Cases" row, not in "Cases Closed" row | Correct placement |
| 6.5 | **Case closed exactly on end date** | Case with ClosedOn == aEndDate should be marked as NOT still open (per my logic `ClosedOn <= aAsAtDate → bStillOpen = False`) | Edge-case behaviour as designed; verify matches business intent |
| 6.6 | **If SWHSB case type doesn't exist** | MsgBox warning + HSB rows emit zeros | Warning appears, rows are zeros, macro completes |

---

## Section 7 — Cosmetic / visual checks

| # | Test | Expected |
|---|------|----------|
| 7.1 | Column widths look reasonable (old columns unchanged) |
| 7.2 | Zero values grayed out (existing `cGrayColour` behaviour still applies to new columns) |
| 7.3 | Red section headers still red |
| 7.4 | No orphan/garbage rows anywhere |
| 7.5 | Report title shows `V2.13` |

---

## Priority — if short on time

**Must-run:** 1.1, 1.2, 2.1, 2.4, 3.3, 3.4, 4.3, 4.5, 5.3

Those nine tests cover: regression hasn't broken things, HSB works, Gender/Ethnicity bucket sums are consistent, cross-tab math is consistent, self-crossings are blank, and perf is acceptable on the problem case.

**Nice-to-have:** everything else — catches subtler issues but unlikely to block a release if the must-runs pass.
