---
name: generate-parquet-dq-tests
description: >-
  Creates one PyTest data quality module per aggregated Parquet dataset under
  `PyTest DQ Framework/tests/dq checks/parquet_files/`, deriving the expected Postgres
  query only from docs/parquet-aggregated-data-mapping.md (smoke, completeness, count,
  uniqueness, not-null). Invoke explicitly with a dataset name. Refuses to edit framework
  code, conftest.py, pytest.ini, Jenkinsfile, or to use data_dev/ SQL as expected results.
disable-model-invocation: true
---

# Generate Parquet DQ tests

Team playbook for writing a Parquet data quality test module. Sources of truth:

- `PyTest DQ Framework/docs/test-automation-strategy.md` — **§5 Skill contract**, **§6 Test design standard**
- `docs/parquet-aggregated-data-mapping.md` — dataset definitions (expected SQL is derived from here only)

This skill is dataset-agnostic: it explains *how* to turn a mapping section into a test module.
It never contains expected SQL for a concrete dataset.

## When this skill applies

Apply when the user explicitly invokes `generate-parquet-dq-tests` and asks for DQ tests of an
aggregated Parquet dataset written under `/parquet_data/<dataset_name>/`, validated against the
PostgreSQL 3NF tables (`facilities`, `visits`, `patients`).

Preconditions (check before writing anything):

- Framework exists: `src/connectors/postgres/postgres_connector.py`, `src/connectors/file_system/parquet_reader.py`,
  `src/data_quality/data_quality_validation_library.py`, `tests/conftest.py` with fixtures
  `db_connection`, `parquet_reader`, `data_quality_library`, and `tests/pytest.ini`.
- The dataset has its own section in `docs/parquet-aggregated-data-mapping.md`.

Allowed write path: `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py` only.

Refuse (or stop and ask) when:

- the request is to change framework code, `conftest.py`, `pytest.ini`, `requirements.txt` or `Jenkinsfile`
  (unless the user explicitly asks for that, separately from this skill);
- the dataset has no mapping section;
- the user asks to take expected SQL from `data_dev/` or to "make the test green" by changing expected SQL;
- the request is for UI / API / Selenium / Robot tests.

## Inputs you must have

| Input | Where it comes from |
| --- | --- |
| Dataset name | User; equals the folder name under `/parquet_data/` and the mapping section heading |
| Target columns, transformations, source tables/columns, comments (grouping / not null / format / rounding) | Mapping table for that dataset |
| Filters, partitioning | Mapping bullets under the table (`Filters`, `Partitioned`) |
| Requirement id, author | User; if not given use `TICKET-1234` and ask for the author name (or leave `<name>` for the user) |

If the mapping section is missing or ambiguous (e.g. unknown source column), stop and report what is
missing. Do not guess from the Parquet content or from pipeline code.

**Forbidden sources:** anything under `data_dev/` (`queries.py`, `src/data/parquet_loader.py`, etc.),
Parquet previews used to "tune" the query, and `tests/test_examples.py` placeholder fixture names.
Reading the live Postgres schema (`\d <table>`) to confirm column/key names is allowed.

## Hard rules

1. **One module per dataset**: `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`
   (same snake_case as the Parquet folder). Never put two datasets in one file.
2. **Direction**: `source_data` = Postgres query (expected, via `db_connection.get_data_sql`),
   `target_data` = Parquet (actual, via `parquet_reader.process`). Never swap them.
3. **Mapping-only expected SQL**: built with the derivation rules below. Never read or copy SQL from `data_dev/`.
4. **No additions**: no `UNION`, extra `WHERE`, `HAVING`, `CASE`, `ABS`, sign flips, `DISTINCT`, `COALESCE`
   or `LIMIT` unless the mapping explicitly states them.
5. **Column names**: every `source_data` column is aliased exactly to the mapping target column name;
   no extra columns (partition helper columns are not in the mapping and must not be selected).
6. **Target path**: `'/parquet_data/<dataset_name>'` with `include_subfolders=True` (datasets are partitioned).
7. **Markers**: every test has `@pytest.mark.parquet_data` and `@pytest.mark.<dataset_name>`;
   `@pytest.mark.smoke` only on `test_check_dataset_is_not_empty`. If the dataset marker is not in
   `tests/pytest.ini`, tell the user to register it (the suite runs with `--strict-markers`).
8. **Mandatory tests** (exact names): `test_check_dataset_is_not_empty`, `test_check_data_completeness`,
   `test_check_count`, `test_check_uniqueness`, `test_check_not_null_values`.
9. **Library only**: tests call `DataQualityLibrary` methods (`check_dataset_is_not_empty`,
   `check_data_completeness`, `check_count`, `check_duplicates`, `check_not_null_values`). No pandas
   logic or bare `assert` in test bodies; no comparison of a dataset with itself.
10. **Uniqueness on grain**: `check_duplicates(target_data, [<grouping columns>])` — the columns marked
    `grouping` in the mapping.
11. **Not-null list** = all mapped target columns marked `not null` (normally all output columns).

## Workflow

1. Read TAS §5–§6 and the mapping section for the requested dataset.
2. Write down (in your reply, not in the file) the derivation: tables + join keys, grouping columns,
   measures with transformation/rounding, filters, output aliases.
3. Build the expected SQL with the rules in **SQL derivation (generic)**.
4. Fill the **Template** below; replace every `<placeholder>`; keep the header docstring.
5. Self-check against the **Hard rules** and the review checklist in TAS §5.5.
6. Report the created file path and the derivation summary. Do not run the suite unless asked.

## Template

Full module skeleton from TAS §6.2 (placeholders only):

```python
"""
Description: Data Quality checks for <dataset_name> dataset.
Requirement(s): <TICKET-ID>
Author(s): <name>
"""

import pytest


@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    -- expected query derived from mapping (grain + measures + joins)
    """
    return db_connection.get_data_sql(source_query)


@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/<dataset_name>'
    return parquet_reader.process(target_path, include_subfolders=True)


@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.<dataset_name>
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_data_completeness(source_data, target_data, data_quality_library):
    data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_uniqueness(target_data, data_quality_library):
    data_quality_library.check_duplicates(target_data, ['<grain_col_1>', '<grain_col_2>'])


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(target_data, ['<col_1>', '<col_2>', '<col_3>'])
```

## SQL derivation (generic)

Apply in order; each step uses only the mapping row(s) of the dataset.

1. **Tables**: collect every `Source` value (`table.<name>` → `<name>`). `visits` is the fact table and the
   `FROM` table; give tables short aliases (`v`, `f`, `p`).
2. **Joins**: inner joins along foreign keys only — `visits.facility_id = facilities.id`,
   `visits.patient_id = patients.id`. Join a dimension table only if one of its columns is mapped.
3. **Dimensions (grain)**: columns whose comment says `grouping`. Each appears in `SELECT` with the
   mapping alias and in `GROUP BY` as the same expression.
   - Date from a timestamp (`visit_timestamp` → `visit_date`): `CAST(<ts> AS DATE)` — a day-level date,
     because the sample shows `YYYY-MM-DD` and partitioning by year-month is storage only, not grain.
   - Concatenations: follow the `format` comment literally (e.g. two columns separated by a single
     space → `<col_a> || ' ' || <col_b>`), in the order stated by the format, not the order of the
     `Source column` cell.
4. **Measures**: the `Transformation` cell (`min`, `max`, `avg`, `sum`, `count`) over the mapped source
   column. Apply rounding only when the comment says so (`ROUND(<agg>::numeric, <n>)`). No other casts,
   `ABS`, or sign changes — a comment such as "can't be negative" is a property the data must satisfy,
   not something the query should enforce.
5. **Aliases**: every output column `AS <target column>` exactly as in the mapping; output only mapped columns.
6. **Filters**: add a `WHERE` only if the `Filters` bullet lists one (`—` means none).
7. **Partitioning**: ignore for SQL; it only means `include_subfolders=True` on the reader.
8. **Stop**. Do not adjust the query to match Parquet output, and do not read ETL SQL.

## After generation

- Running pytest only if the user asks:
  `pytest tests -m "<dataset_name>" --db_host=... --db_port=... --db_name=... --db_user=... --db_password=... --html=html_report/report.html`
  (run from `PyTest DQ Framework/`; locally set `PARQUET_DATA_ROOT` if `/parquet_data` is copied elsewhere).
- A failed check is a candidate **transformation defect**. Report per TAS §10: dataset, test, what the
  mapping expects, what the Parquet contains (from the assertion message), probable root cause.
- Never rewrite expected SQL, loosen checks, add `xfail`/`skip`, or drop a mandatory test to obtain a green run.
  Change expected SQL only if it contradicts the mapping, and say so explicitly.

---

## Skill review (self-check before Step 3)

Reject your own skill if any of these are true:

- [x] Contains concrete expected SQL for `facility_name_min_time_spent_per_visit_date`, `facility_type_avg_time_spent_per_visit_date`, or `patient_sum_treatment_cost_per_facility_type` — **No**: only generic derivation rules and placeholders.
- [x] Tells the agent to use `data_dev/` or parquet loader SQL — **No**: `data_dev/` is listed as a forbidden source.
- [x] Omits completeness, count, uniqueness, or not-null — **No**: all are mandatory (Hard rule 8) and in the template.
- [x] Swaps Postgres vs Parquet fixtures or generates trivial always-pass checks — **No**: source = Postgres, target = Parquet (Hard rule 2); no self-comparison (Hard rule 9).
- [x] Any section still says `TODO` — **No**.
