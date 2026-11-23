import datetime as dt
import numbers
from decimal import Decimal

import numpy as np
import pandas as pd


class DataQualityLibrary:
    """
    A library of static methods for performing data quality checks on pandas DataFrames.

    This class is intended to be used in a PyTest-based testing framework to validate
    the quality of data in DataFrames. Each method performs a specific data quality
    check and uses assertions to ensure that the data meets the expected conditions.
    Assertion messages contain enough detail (rows, counts, columns) to debug a failure
    straight from the HTML report.
    """

    MAX_ROWS_IN_MESSAGE = 20
    FLOAT_PRECISION = 6

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _to_text(df: pd.DataFrame, limit: int | None = None) -> str:
        limit = limit or DataQualityLibrary.MAX_ROWS_IN_MESSAGE
        text = df.head(limit).to_string(index=False)
        if len(df) > limit:
            text += f"\n... ({len(df) - limit} more rows)"
        return text

    @staticmethod
    def _normalize_value(value):
        """Bring Postgres (Decimal, date) and Parquet (float, Timestamp) values to one form."""
        if value is None or (not isinstance(value, (str, bytes)) and pd.isna(value)):
            return None
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (numbers.Number, Decimal)):
            # int / float / Decimal / numpy scalars -> one comparable float representation
            return round(float(value), DataQualityLibrary.FLOAT_PRECISION)
        if isinstance(value, (pd.Timestamp, dt.datetime)):
            ts = pd.Timestamp(value)
            return ts.date().isoformat() if ts == ts.normalize() else ts.isoformat()
        if isinstance(value, dt.date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        for col in normalized.columns:
            normalized[col] = normalized[col].map(DataQualityLibrary._normalize_value).astype(object)
        return normalized

    # ------------------------------------------------------------------- checks
    @staticmethod
    def check_dataset_is_not_empty(df: pd.DataFrame):
        assert df is not None, "Dataset is None"
        assert not df.empty, f"Dataset is empty (rows={len(df)}, columns={list(df.columns)})"

    @staticmethod
    def check_count(df_expected: pd.DataFrame, df_actual: pd.DataFrame):
        expected, actual = len(df_expected), len(df_actual)
        assert expected == actual, (
            f"Row count mismatch: expected (source) = {expected}, actual (target) = {actual}, "
            f"difference = {actual - expected:+d}"
        )

    @staticmethod
    def check_data_completeness(df_expected: pd.DataFrame, df_actual: pd.DataFrame):
        """
        Full data set comparison, row order ignored, duplicates respected.
        Fails on column set mismatch or any row present on one side only.
        """
        expected_cols, actual_cols = set(df_expected.columns), set(df_actual.columns)
        assert expected_cols == actual_cols, (
            "Column set mismatch.\n"
            f"Missing in target: {sorted(expected_cols - actual_cols)}\n"
            f"Unexpected in target: {sorted(actual_cols - expected_cols)}"
        )

        columns = sorted(expected_cols)
        expected = DataQualityLibrary._normalize(df_expected[columns])
        actual = DataQualityLibrary._normalize(df_actual[columns])

        # Number each occurrence of identical rows so duplicates are compared as well.
        key = "__occurrence__"
        expected[key] = expected.groupby(columns, dropna=False).cumcount()
        actual[key] = actual.groupby(columns, dropna=False).cumcount()

        merged = expected.merge(actual, on=columns + [key], how="outer", indicator=True)
        only_expected = merged[merged["_merge"] == "left_only"][columns]
        only_actual = merged[merged["_merge"] == "right_only"][columns]

        if only_expected.empty and only_actual.empty:
            return

        message = [
            "Data completeness check failed: source (expected) and target (actual) differ.",
            f"Expected rows: {len(df_expected)}, actual rows: {len(df_actual)}",
            f"Rows missing in target (present only in source): {len(only_expected)}",
            f"Rows unexpected in target (present only in target): {len(only_actual)}",
        ]
        if not only_expected.empty:
            message += ["", "--- Missing in target ---",
                        DataQualityLibrary._to_text(only_expected.sort_values(columns))]
        if not only_actual.empty:
            message += ["", "--- Unexpected in target ---",
                        DataQualityLibrary._to_text(only_actual.sort_values(columns))]
        raise AssertionError("\n".join(message))

    # Backward-compatible alias for the name used in the original skeleton.
    check_data_full_data_set = check_data_completeness

    @staticmethod
    def check_duplicates(df: pd.DataFrame, column_names=None):
        subset = list(column_names) if column_names else list(df.columns)
        missing = [c for c in subset if c not in df.columns]
        assert not missing, f"Columns not found for duplicate check: {missing}"

        duplicated = df[df.duplicated(subset=subset, keep=False)]
        if duplicated.empty:
            return
        groups = (duplicated.groupby(subset, dropna=False).size()
                  .reset_index(name="occurrences").sort_values("occurrences", ascending=False))
        raise AssertionError(
            f"Found {len(groups)} duplicated key(s) ({len(duplicated)} rows) on columns {subset}.\n"
            + DataQualityLibrary._to_text(groups)
        )

    @staticmethod
    def check_not_null_values(df: pd.DataFrame, column_names=None):
        columns = list(column_names) if column_names else list(df.columns)
        missing = [c for c in columns if c not in df.columns]
        assert not missing, f"Columns not found for not-null check: {missing}. Available: {list(df.columns)}"

        null_counts = {c: int(df[c].isna().sum()) for c in columns}
        failed = {c: n for c, n in null_counts.items() if n > 0}
        if not failed:
            return
        sample = df[df[list(failed)].isna().any(axis=1)]
        raise AssertionError(
            f"Null values found (column: null count): {failed} out of {len(df)} rows.\n"
            + DataQualityLibrary._to_text(sample)
        )
