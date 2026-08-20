"""Store validated dataframes as Parquet and expose them as DuckDB views.

Parquet is the primary data storage layer and DuckDB is the primary query
engine. Each dataset is written to a single Parquet file under ``data/parquet/``
and merged idempotently on its unique key so re-runs never duplicate rows.

DuckDB views are defined in ``sql/schema.sql`` (base tables read from Parquet)
and ``sql/kpi_views.sql`` (analytical views). ``create_views`` registers both.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_ROOT = PROJECT_ROOT / "data" / "parquet"
SQL_DIR = PROJECT_ROOT / "sql"

UNIQUE_COLS: dict[str, list[str]] = {
    "ridership": ["date"],
    "bus_routes": ["date", "route"],
    "rail_entries": ["date", "station_id"],
    "rail_stations": ["station_id"],
    "bus_route_info": ["route"],
}

VIEW_NAMES = [
    "ridership",
    "bus_routes",
    "rail_entries",
    "rail_stations",
    "bus_route_info",
    "v_daily_ridership",
    "v_weekly_ridership",
    "v_day_type",
    "v_ridership_recovery",
    "v_route_concentration",
    "v_mode_change",
]


def write_dataset(
    df: pd.DataFrame, name: str, root: str | Path = PARQUET_ROOT
) -> int:
    """Merge a dataset into its Parquet file, returning the number of new rows."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    out_path = root / f"{name}.parquet"

    if df.empty:
        return 0

    unique_cols = UNIQUE_COLS[name]
    incoming = df.copy()
    if "date" in incoming.columns:
        incoming["date"] = pd.to_datetime(incoming["date"])

    if out_path.exists():
        existing = pd.read_parquet(out_path, dtype_backend="numpy_nullable")
        before = len(existing)
        merged = pd.concat([existing, incoming], ignore_index=True)
        merged = merged.drop_duplicates(subset=unique_cols, keep="last")
        added = len(merged) - before
    else:
        merged = incoming
        added = len(merged)

    merged.to_parquet(out_path, index=False)
    logger.info("Wrote %d rows (added %d) to %s", len(merged), added, out_path)
    return added


def write_all(
    dataframes: dict[str, pd.DataFrame], root: str | Path = PARQUET_ROOT
) -> dict[str, int]:
    """Write all datasets and return a mapping of dataset name to rows added."""
    return {name: write_dataset(df, name, root) for name, df in dataframes.items()}


def get_connection(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection (in-memory by default, or a persistent file)."""
    if db_path is None:
        return duckdb.connect(":memory:")
    return duckdb.connect(str(db_path))


def create_views(
    conn: duckdb.DuckDBPyConnection, root: str | Path = PARQUET_ROOT
) -> list[str]:
    """Register the base and analytical views on ``conn`` and return their names."""
    root = Path(root).resolve().as_posix()
    for filename in ("schema.sql", "kpi_views.sql"):
        text = (SQL_DIR / filename).read_text()
        conn.execute(text.replace("data/parquet", root))
    return VIEW_NAMES
