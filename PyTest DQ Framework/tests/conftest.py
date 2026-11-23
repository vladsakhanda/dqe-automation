import pytest

from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import PostgresConnectorContextManager
from src.data_quality.data_quality_validation_library import DataQualityLibrary


def pytest_addoption(parser):
    parser.addoption("--db_host", action="store", default="localhost", help="Database host")
    parser.addoption("--db_port", action="store", default="5434", help="Database port")
    parser.addoption("--db_name", action="store", default="mydatabase", help="Database name")
    parser.addoption("--db_user", action="store", default=None, help="Database user (required)")
    parser.addoption("--db_password", action="store", default=None, help="Database password (required)")


def pytest_configure(config):
    """
    Validates that all required command-line options are provided.
    """
    required_options = [
        "--db_user", "--db_password"
    ]
    # Collection-only / help runs do not need a database.
    if config.getoption("--collect-only") or config.getoption("--help"):
        return
    for option in required_options:
        if not config.getoption(option):
            pytest.exit(f"Missing required option: {option}", returncode=4)


@pytest.fixture(scope='session')
def db_connection(request):
    db_host = request.config.getoption("--db_host")
    db_name = request.config.getoption("--db_name")
    db_port = request.config.getoption("--db_port")
    db_user = request.config.getoption("--db_user")
    db_password = request.config.getoption("--db_password")

    try:
        connector = PostgresConnectorContextManager(db_user=db_user, db_password=db_password, db_host=db_host,
                                                    db_name=db_name, db_port=db_port)
        db_connector = connector.__enter__()
    except Exception as e:
        pytest.fail(f"Failed to initialize PostgresConnectorContextManager: {e}")
    try:
        yield db_connector
    finally:
        connector.__exit__(None, None, None)


@pytest.fixture(scope='session')
def parquet_reader():
    try:
        reader = ParquetReader()
    except Exception as e:
        pytest.fail(f"Failed to initialize ParquetReader: {e}")
    yield reader


@pytest.fixture(scope='session')
def data_quality_library():
    try:
        library = DataQualityLibrary()
    except Exception as e:
        pytest.fail(f"Failed to initialize DataQualityLibrary: {e}")
    yield library
