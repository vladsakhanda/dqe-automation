"""
Description: Framework usage sample (marker `example`, never selected by `-m parquet_data`).
             Shows the direction used by the suite: source = Postgres (expected), target = Parquet (actual).
Requirement(s): TICKET-1234
Author(s): Name Surname
"""

import pandas as pd
import pytest


@pytest.fixture(scope='module')
def source_data():
    # In real modules: db_connection.get_data_sql(<expected query derived from the mapping>)
    return pd.DataFrame({'id': [1, 2, 3], 'name': ['a', 'b', 'c']})


@pytest.fixture(scope='module')
def target_data():
    # In real modules: parquet_reader.process('/parquet_data/<dataset_name>', include_subfolders=True)
    return pd.DataFrame({'id': [3, 2, 1], 'name': ['c', 'b', 'a']})


@pytest.mark.example
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.example
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)


@pytest.mark.example
def test_check_data_completeness(source_data, target_data, data_quality_library):
    data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.example
def test_check_uniqueness(target_data, data_quality_library):
    data_quality_library.check_duplicates(target_data)


@pytest.mark.example
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(target_data, ['id', 'name'])
