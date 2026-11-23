# DQ run — transformation defect summary

| Field | Value |
| --- | --- |
| Run | `pytest tests -m "parquet_data"` (15 tests) |
| Result | **7 passed, 8 failed** |
| Expected | Postgres 3NF query derived from [parquet-aggregated-data-mapping.md](../../docs/parquet-aggregated-data-mapping.md) (no `data_dev` SQL) |
| Actual | `/parquet_data/<dataset>` written by the `data_dev` pipeline |
| Source volume | `visits` 83 317 rows, 4 facilities (one per facility type), 30 patients |

All failures are explained by the Parquet transformation deviating from the mapping. No expected SQL was changed to make checks pass.

**Jenkins job `dq_tests`, build #1** (status UNSTABLE): `8 failed, 7 passed, 5 deselected` — same failing tests as below.
Source data grows daily, so absolute numbers in the build differ slightly from the local analysis below:

| Test | Jenkins build #1 assertion |
| --- | --- |
| `facility_name_min…::test_check_count` | expected 35 719, actual 44 669 (+8 950) |
| `facility_name_min…::test_check_uniqueness` | 8 950 duplicated keys (17 900 rows) on `facility_name`, `visit_date` |
| `facility_type_avg…::test_check_count` | expected 35 719, actual 25 934 (−9 785) |
| `patient_sum…::test_check_count` | expected 120, actual 64 (−56) |
| `patient_sum…::test_check_not_null_values` | `full_name`: 4 nulls out of 64 rows |

The detailed numbers below come from a local run against the same containers shortly before the build.

## Summary

| # | Dataset | Failed tests | Defect | Severity |
| --- | --- | --- | --- | --- |
| D1 | `facility_name_min_time_spent_per_visit_date` | completeness, count, uniqueness | Every row of facility **Escobar-Kennedy** is written twice (+8 937 duplicate rows) | High |
| D2 | `facility_type_avg_time_spent_per_visit_date` | completeness, count | Facility type **Urgent Care** is missing entirely (−8 935 rows) | High |
| D3 | `facility_type_avg_time_spent_per_visit_date` | completeness, count | Visits before **2000-11-01** are filtered out (−839 rows) | Medium |
| D4 | `patient_sum_treatment_cost_per_facility_type` | completeness, count, not-null | Patients with id 1–15 are collapsed into one row per facility type with `full_name = NULL` | High |
| D5 | `patient_sum_treatment_cost_per_facility_type` | completeness | `sum_treatment_cost` sign is flipped (negative) for facility type **Clinic** | High |

Passed: all 3 smoke tests, uniqueness and not-null for `facility_type_avg_time_spent_per_visit_date`, not-null for `facility_name_min_time_spent_per_visit_date`, uniqueness for `patient_sum_treatment_cost_per_facility_type`.

## Details

### D1 — `facility_name_min_time_spent_per_visit_date`: duplicated facility rows

- **Tests:** `test_check_data_completeness`, `test_check_count`, `test_check_uniqueness`
- **Mapping:** grain `facility_name`, `visit_date`; `min_time_spent = min(duration_minutes)`; no filters → one row per facility per day (35 670 rows).
- **Parquet:** 44 607 rows; 35 670 distinct grain keys. All 8 937 day-rows of **Escobar-Kennedy** (2000-01-01 … 2026-11-09) appear twice with identical values; other facilities have exactly one row per day. `min_time_spent` values match the expected value for every key (no measure error).
- **Root cause (transformation):** that facility's rows are appended twice (e.g. `UNION ALL` of a facility-specific subset, or a join that fans out for this facility). Not in the mapping.

### D2 — `facility_type_avg_time_spent_per_visit_date`: Urgent Care missing

- **Tests:** `test_check_data_completeness`, `test_check_count`
- **Mapping:** grain `facility_type`, `visit_date`; `avg_time_spent = round(avg(duration_minutes), 2)`; **Filters: —**.
- **Parquet:** 25 896 rows vs 35 670 expected. Facility type `Urgent Care` (8 935 expected rows) has 0 rows. Present keys have the correct rounded average (0 value differences).
- **Root cause (transformation):** an extra filter on `facility_type` (excluding Urgent Care) that is not in the mapping.

### D3 — `facility_type_avg_time_spent_per_visit_date`: early dates cut off

- **Tests:** same as D2.
- **Mapping:** no date filter; source visits start 2000-01-01.
- **Parquet:** earliest `visit_date` is 2000-11-01 for all facility types; 839 rows for 2000-01-01 … 2000-10-31 (Clinic 282, Hospital 279, Specialty Center 278) are missing. Partitions `partition_date=2000-01` … `2000-10` do not exist.
- **Root cause (transformation):** an extra `visit_timestamp` lower-bound filter not in the mapping.

### D4 — `patient_sum_treatment_cost_per_facility_type`: patients collapsed, NULL `full_name`

- **Tests:** `test_check_data_completeness`, `test_check_count` (120 expected vs 64 actual), `test_check_not_null_values` (`full_name`: 4 nulls).
- **Mapping:** grain `facility_type`, `full_name = first_name || ' ' || last_name`; `full_name` not null → 30 patients × 4 types = 120 rows.
- **Parquet:** per facility type, 15 named rows (patients id 16–30) plus one row with `full_name = NULL`. The NULL row's amount equals exactly the sum of `treatment_cost` of patients id 1–15 for that type (Clinic 26 468 836.15, Hospital 26 206 194.08, …).
- **Root cause (transformation):** patients 1–15 lose their name (`CASE`/`UNION` branch producing `NULL` name) and are grouped into a single bucket. Breaks the mapped grain and the not-null rule.

### D5 — `patient_sum_treatment_cost_per_facility_type`: negative cost for Clinic

- **Tests:** `test_check_data_completeness`
- **Mapping:** `sum_treatment_cost = SUM(v.treatment_cost)`, "Can't be negative". Source `treatment_cost` is 50.03 … 4 999.98, so all sums are positive.
- **Parquet:** all 16 Clinic rows are negative (e.g. April Cook −1 843 467.56, expected +1 843 467.56). Absolute values match the expected sums for all 60 named rows; only the sign differs for Clinic.
- **Root cause (transformation):** sign inversion applied to `facility_type = 'Clinic'`.

## Notes

- `TAS §2.3` lists the measure of `facility_name_min_time_spent_per_visit_date` as `avg_time_spent`; the mapping (which wins) and the Parquet schema use `min_time_spent`. Tests follow the mapping.
- Parquet partition folders (`partition_date=YYYY-MM`, `facility_type_partition=...`) are storage only and are not compared as columns.
- A non-negative check on `sum_treatment_cost` is not part of the mandatory test set; D5 is caught by completeness. It could be added as an extra validity check later.
