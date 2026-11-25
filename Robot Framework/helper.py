"""Custom Robot Framework keywords for comparing the HTML report table with Parquet data.

Robot exposes every public function as a keyword, e.g. ``read_html_table`` -> ``Read Html Table``.
"""
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

# Parquet column -> header shown in the HTML report table.
PARQUET_TO_REPORT_COLUMNS = {
    "facility_type": "Facility Type",
    "visit_date": "Visit Date",
    "avg_time_spent": "Average Time Spent",
}
DATE_FORMAT = "%Y-%m-%d"
MAX_DIFF_ROWS = 50


def read_html_table(table: WebElement) -> pd.DataFrame:
    """Reads a located Plotly table (``.table`` element) into a DataFrame.

    Plotly draws the table column by column: every ``y-column`` has one header
    (``#header``) and the data cells (``.cell-text``) of that column.
    """
    columns = table.find_elements(By.CLASS_NAME, "y-column")
    if not columns:
        raise AssertionError("HTML table has no columns (class 'y-column').")

    data = {}
    for column in columns:
        header = column.find_element(By.ID, "header").text.strip()
        cells = [c.text.strip() for c in column.find_elements(By.CLASS_NAME, "cell-text")]
        # The header block also contains a 'cell-text' element - drop it.
        data[header] = [value for value in cells if value != header]

    lengths = {header: len(values) for header, values in data.items()}
    if len(set(lengths.values())) != 1:
        raise AssertionError(f"HTML table columns have different number of cells: {lengths}")
    return pd.DataFrame(data)


def read_parquet_dataset(folder: str, filter_date: str | None = None) -> pd.DataFrame:
    """Reads a partitioned Parquet dataset and keeps the columns shown in the report.

    If ``filter_date`` (``YYYY-MM-DD``) is given, only rows with
    ``visit_date >= filter_date`` are returned. The month partitions
    (``partition_date=YYYY-MM``) older than that date are skipped entirely.
    """
    filters = None
    if filter_date:
        start = pd.Timestamp(filter_date)  # raises ValueError for a bad date
        filters = [
            ("partition_date", ">=", start.strftime("%Y-%m")),
            ("visit_date", ">=", start),
        ]

    df = pd.read_parquet(folder, columns=list(PARQUET_TO_REPORT_COLUMNS), filters=filters)
    df["visit_date"] = pd.to_datetime(df["visit_date"]).dt.strftime(DATE_FORMAT)
    df["facility_type"] = df["facility_type"].astype(str)
    return df.rename(columns=PARQUET_TO_REPORT_COLUMNS).reset_index(drop=True)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Makes values comparable: numeric columns -> rounded float text, others -> stripped text."""
    result = pd.DataFrame(index=df.index)
    for column in df.columns:
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().all():
            result[column] = numeric.round(6).map(lambda v: f"{v:g}")
        else:
            result[column] = df[column].astype(str).str.strip()
    return result


def compare_dataframes(df_html: pd.DataFrame, df_parquet: pd.DataFrame):
    """Compares two DataFrames for an exact match, ignoring row order.

    Duplicates are respected: a row present twice on one side and once on the
    other is reported. Returns ``(is_equal, differences_text)``.
    """
    html_cols, parquet_cols = list(df_html.columns), list(df_parquet.columns)
    if sorted(html_cols) != sorted(parquet_cols):
        return False, f"Columns differ.\nHTML table: {html_cols}\nParquet:    {parquet_cols}"

    left = _normalize(df_html)
    right = _normalize(df_parquet[html_cols])
    keys = html_cols + ["_occurrence"]
    left["_occurrence"] = left.groupby(html_cols).cumcount()
    right["_occurrence"] = right.groupby(html_cols).cumcount()

    merged = left.merge(right, on=keys, how="outer", indicator=True)
    only_html = merged[merged["_merge"] == "left_only"][html_cols]
    only_parquet = merged[merged["_merge"] == "right_only"][html_cols]

    if only_html.empty and only_parquet.empty:
        return True, f"DataFrames match: {len(left)} rows."

    lines = [
        f"DataFrames do not match. HTML table rows: {len(left)}, Parquet rows: {len(right)}.",
        f"Rows only in HTML table ({len(only_html)}):",
        only_html.head(MAX_DIFF_ROWS).to_string(index=False) if not only_html.empty else "  none",
        f"Rows only in Parquet ({len(only_parquet)}):",
        only_parquet.head(MAX_DIFF_ROWS).to_string(index=False) if not only_parquet.empty else "  none",
    ]
    return False, "\n".join(lines)
