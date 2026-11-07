from pathlib import Path
import pandas as pd
import pytest


# Fixture to read the CSV file
@pytest.fixture(scope="session")
def path_to_file():
  current_dir = Path(__file__).resolve().parent
  data_path = current_dir.parent / "src" / "data" / "data.csv"
  if not data_path.exists():
    data_path = current_dir.parent.parent / "src" / "data" / "data.csv"
  if not data_path.exists():
    pytest.fail(f"Data file not found at: {data_path}")
  return data_path


@pytest.fixture(scope="session")
def csv_data(path_to_file):
  df = pd.read_csv(path_to_file)
  return df.to_dict(orient="records")


# Fixture to validate the schema of the file
@pytest.fixture(scope="session")
def expected_schema():
  return {"id", "name", "age", "email", "is_active"}


@pytest.fixture(scope="session")
def actual_schema(csv_data):
  if not csv_data:
    return set()
  return set(csv_data[0].keys())


@pytest.fixture(scope="session")
def validate_schema(actual_schema, expected_schema):
  missing = expected_schema - actual_schema
  assert (
      not missing
  ), f"Custom Error: Schema validation failed. Missing columns: {missing}"
  return True


# Pytest hook to mark unmarked tests with a custom mark
def pytest_collection_modifyitems(session, config, items):
  for item in items:
    if not any(item.iter_markers()):
      item.add_marker(pytest.mark.unmarked)