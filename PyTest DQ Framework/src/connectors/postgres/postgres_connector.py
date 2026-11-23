import pandas as pd
import psycopg2


class PostgresConnectorContextManager:
    """
    Context manager around a psycopg2 connection.

    Usage:
        with PostgresConnectorContextManager(db_host=..., db_name=..., db_port=...,
                                             db_user=..., db_password=...) as db:
            df = db.get_data_sql("select 1 as one")
    """

    def __init__(self, db_host: str, db_name: str, db_port, db_user: str, db_password: str):
        self.db_host = db_host
        self.db_name = db_name
        self.db_port = int(db_port)
        self.db_user = db_user
        self.db_password = db_password
        self.connection = None

    def __enter__(self):
        self.connection = psycopg2.connect(
            host=self.db_host,
            dbname=self.db_name,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
        )
        # Read-only usage: autocommit avoids leaving transactions open between queries.
        self.connection.autocommit = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        # Do not suppress exceptions raised inside the `with` block.
        return False

    def get_data_sql(self, sql: str) -> pd.DataFrame:
        """Execute a query and return the result set as a pandas DataFrame."""
        if self.connection is None:
            raise RuntimeError("Connection is not open. Use the connector as a context manager.")
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
