# Generate Parquet DQ Tests

Complete this skill as Step 2 of the PyTest DQ Framework assignment. Read first:

- PyTest DQ Framework/docs/test-automation-strategy.md — §5 Skill contract, §6 Test design standard
- docs/parquet-aggregated-data-mapping.md — dataset definitions (expected SQL comes from here)

Do not paste expected SQL for the three named datasets into this skill.
Do not instruct the agent to copy SQL from `data_dev/`.

When finished, every TODO below must be replaced. Run the Skill review checklist before using the skill to generate tests.

## When this skill applies

This skill applies when generating automated PyTest data quality checks for aggregated Parquet datasets against PostgreSQL 3NF source tables based strictly on `docs/parquet-aggregated-data-mapping.md`. 
- **Framework exists**: PyTest DQ Framework with PostgreSQL and Parquet connectors, conftest.py, pytest.ini, and reporting library.
- **Allowed paths**: `PyTest DQ Framework/tests/dq checks/parquet_files/`.
- **Refuse**: Do not apply if mapping is missing, if using `data_dev` pipeline SQL as expected results, or if generating UI/API/Selenium tests.

## Inputs you must have

- Required inputs: `docs/parquet-aggregated-data-mapping.md` for dataset schemas, joins, grains, and expected SQL definitions.
- If mapping is missing: Stop execution and report that `docs/parquet-aggregated-data-mapping.md` is required.
- **Forbidden sources**: `data_dev/queries.py` or raw pipeline implementation SQL.

## Hard rules

1. **File Path & Location**: Generate one test file per dataset under `PyTest DQ Framework/tests/dq checks/parquet_files/`.
2. **Source vs Target**: Compare expected PostgreSQL 3NF query results (Source) against Parquet dataset files (Target).
3. **Mapping-only SQL**: Use expected SQL derived exclusively from `docs/parquet-aggregated-data-mapping.md`. Never copy SQL from `data_dev/`.
4. **No Dataset SQL in SKILL.md**: Do not embed concrete dataset expected SQL queries in this skill definition file.
5. **Library Methods Only**: Use reusable DQ library methods (e.g. `assert_completeness`, `assert_count_match`, `assert_uniqueness`, `assert_not_null`, `assert_smoke`).
6. **PyTest Markers**: Always decorate test functions with `@pytest.mark.parquet_data` and `@pytest.mark.dq`.
7. **Not-Null & Uniqueness**: Explicitly validate uniqueness on grain columns and non-null constraints on mandatory measure/dimension columns.

## Workflow

1. Read dataset definition and expected SQL mapping from `docs/parquet-aggregated-data-mapping.md`.
2. Generate PyTest module under `PyTest DQ Framework/tests/dq checks/parquet_files/` following TAS §6 template.
3. Include smoke test (target not empty), count match, completeness / row-by-row reconciliation, uniqueness on grain, and not-null checks.
4. Run pytest with `-m parquet_data` and verify HTML report generation.

## Template

```python
import pytest
from dq_library.assertions import (
    assert_smoke,
    assert_count_match,
    assert_completeness,
    assert_uniqueness,
    assert_not_null
)

@pytest.mark.parquet_data
@pytest.mark.dq
def test_dataset_smoke(parquet_dataset):
    assert_smoke(parquet_dataset)

@pytest.mark.parquet_data
@pytest.mark.dq
def test_dataset_count(postgres_conn, parquet_dataset):
    assert_count_match(postgres_conn, parquet_dataset, expected_sql="...")

@pytest.mark.parquet_data
@pytest.mark.dq
def test_dataset_completeness(postgres_conn, parquet_dataset):
    assert_completeness(postgres_conn, parquet_dataset, expected_sql="...", keys=[...])

@pytest.mark.parquet_data
@pytest.mark.dq
def test_dataset_uniqueness(parquet_dataset):
    assert_uniqueness(parquet_dataset, keys=[...])

@pytest.mark.parquet_data
@pytest.mark.dq
def test_dataset_not_null(parquet_dataset):
    assert_not_null(parquet_dataset, columns=[...])