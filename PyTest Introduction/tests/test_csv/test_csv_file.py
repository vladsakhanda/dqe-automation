import re
import pytest


def test_file_not_empty(csv_data):
  assert (
      len(csv_data) > 0
  ), f"Custom Error: The CSV file is empty! Total rows: {len(csv_data)}"


@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Expected failure: dataset contains duplicate rows.")
def test_duplicates(csv_data):
  row_tuples = [tuple(sorted(row.items())) for row in csv_data]
  unique_rows = set(row_tuples)
  assert len(unique_rows) == len(csv_data), (
      f"Custom Error: Duplicate rows detected! Total rows: {len(csv_data)},"
      f" Unique rows: {len(unique_rows)}"
  )


@pytest.mark.validate_csv
def test_validate_schema(validate_schema):
  assert validate_schema is True, "Custom Error: Schema validation failed."


@pytest.mark.validate_csv
@pytest.mark.skip(reason="Skipping age validation temporarily.")
def test_age_column_valid(csv_data):
  for row in csv_data:
    age_val = str(row.get("age", "")).strip()
    assert age_val.isdigit(), f"Custom Error: Non-numeric age found: '{age_val}'"
    age_int = int(age_val)
    assert (
        0 <= age_int <= 100
    ), f"Custom Error: Age {age_int} is out of valid bounds (0-100)."


@pytest.mark.validate_csv
def test_email_column_valid(csv_data):
  email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
  for row in csv_data:
    email = str(row.get("email", "")).strip()
    assert re.match(
        email_regex, email
    ), f"Custom Error: Invalid email format detected: '{email}'"


@pytest.mark.parametrize(
    "target_id, expected_is_active",
    [
        ("1", False),
        ("2", True),
    ],
)
def test_active_players(csv_data, target_id, expected_is_active):
  found = False
  for row in csv_data:
    if str(row.get("id")) == target_id:
      found = True
      actual_status = row.get("is_active")
      is_match = (
          actual_status == expected_is_active
          or str(actual_status).lower() == str(expected_is_active).lower()
      )
      assert is_match, (
          f"Custom Error: For ID {target_id}, expected is_active to be"
          f" {expected_is_active}, but got {actual_status}"
      )
  assert found, f"Custom Error: ID {target_id} not found in CSV data."


def test_active_player(csv_data):
  target_id = "2"
  found = False
  for row in csv_data:
    if str(row.get("id")) == target_id:
      found = True
      actual_status = row.get("is_active")
      assert str(actual_status).lower() == "true", (
          f"Custom Error: Expected is_active to be True for id=2, got {actual_status}"
      )
  assert found, f"Custom Error: ID {target_id} not found."