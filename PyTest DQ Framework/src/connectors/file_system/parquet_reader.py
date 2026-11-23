import os
from pathlib import Path

import pandas as pd


class ParquetReader:
    """
    Reads Parquet datasets from the file system into a pandas DataFrame.

    A dataset may be a single ``.parquet`` file or a folder (optionally with
    partition subfolders such as ``partition_date=2000-01``). Files are read one by
    one and concatenated, so only the columns physically stored in the files are
    returned (hive partition folder names are not added as columns).

    ``PARQUET_DATA_ROOT`` (optional env variable) remaps the ``/parquet_data`` prefix
    for local runs outside the Jenkins container, e.g.
    ``PARQUET_DATA_ROOT=C:/work/parquet_data``. Tests always keep the canonical
    ``/parquet_data/<dataset>`` path.
    """

    CANONICAL_ROOT = "/parquet_data"

    def __init__(self, root_override: str | None = None):
        self.root_override = root_override or os.environ.get("PARQUET_DATA_ROOT")

    def _resolve(self, path: str) -> Path:
        normalized = str(path).replace("\\", "/")
        if self.root_override and normalized.startswith(self.CANONICAL_ROOT):
            normalized = self.root_override.rstrip("/\\") + normalized[len(self.CANONICAL_ROOT):]
        return Path(normalized)

    def list_files(self, path: str, include_subfolders: bool = False) -> list[Path]:
        resolved = self._resolve(path)
        if resolved.is_file():
            return [resolved]
        if not resolved.is_dir():
            raise FileNotFoundError(f"Parquet path does not exist: {resolved}")
        pattern = "**/*.parquet" if include_subfolders else "*.parquet"
        return sorted(p for p in resolved.glob(pattern) if p.is_file())

    def process(self, path: str, include_subfolders: bool = False) -> pd.DataFrame:
        files = self.list_files(path, include_subfolders=include_subfolders)
        if not files:
            raise FileNotFoundError(
                f"No parquet files found under {self._resolve(path)} "
                f"(include_subfolders={include_subfolders})"
            )
        frames = [pd.read_parquet(f) for f in files]
        return pd.concat(frames, ignore_index=True)
