"""Upsert validated CTA dataframes into a SQLite database via SQLAlchemy."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Date,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    Column,
    create_engine,
    select,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/cta.db")

metadata = MetaData()

ridership_table = Table(
    "ridership",
    metadata,
    Column("date", Date, nullable=False),
    Column("day_type", String, nullable=True),
    Column("bus", Integer, nullable=True),
    Column("rail_boardings", Integer, nullable=True),
    Column("total_rides", Integer, nullable=True),
    UniqueConstraint("date", name="uq_ridership_date"),
)

bus_routes_table = Table(
    "bus_routes",
    metadata,
    Column("date", Date, nullable=False),
    Column("route", String, nullable=False),
    Column("day_type", String, nullable=True),
    Column("rides", Integer, nullable=True),
    UniqueConstraint("date", "route", name="uq_bus_routes_date_route"),
)

rail_entries_table = Table(
    "rail_entries",
    metadata,
    Column("date", Date, nullable=False),
    Column("station_id", String, nullable=False),
    Column("station_name", String, nullable=True),
    Column("day_type", String, nullable=True),
    Column("rides", Integer, nullable=True),
    UniqueConstraint("date", "station_id", name="uq_rail_entries_date_station"),
)

TABLES: dict[str, dict] = {
    "ridership": {"table": ridership_table, "unique_cols": ["date"]},
    "bus_routes": {"table": bus_routes_table, "unique_cols": ["date", "route"]},
    "rail_entries": {"table": rail_entries_table, "unique_cols": ["date", "station_id"]},
}


def get_engine(db_path: str | Path = DEFAULT_DB_PATH) -> Engine:
    """Return a SQLAlchemy engine for the SQLite database."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def init_db(engine: Engine) -> None:
    """Create tables if they do not already exist."""
    metadata.create_all(engine)


def _existing_keys(engine: Engine, table: Table, unique_cols: list[str]) -> set[tuple]:
    cols = [table.c[c] for c in unique_cols]
    with engine.connect() as conn:
        rows = conn.execute(select(*cols)).all()
    return {tuple(row) for row in rows}


def load_dataframe(df: pd.DataFrame, name: str, engine: Engine) -> int:
    """Upsert rows into the named table, returning the number of new rows added."""
    config = TABLES[name]
    table: Table = config["table"]
    unique_cols: list[str] = config["unique_cols"]

    if df.empty:
        return 0

    normalized = df.copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date

    existing = _existing_keys(engine, table, unique_cols)
    incoming_keys = normalized[unique_cols].apply(tuple, axis=1)
    new_rows = normalized[~incoming_keys.isin(existing)]

    if new_rows.empty:
        return 0

    records = new_rows.astype(object).where(new_rows.notna(), None).to_dict("records")
    stmt = sqlite_insert(table).on_conflict_do_nothing(index_elements=unique_cols)
    with engine.begin() as conn:
        conn.execute(stmt, records)
    return len(new_rows)


def load_all(
    dataframes: dict[str, pd.DataFrame], db_path: str | Path = DEFAULT_DB_PATH
) -> dict[str, int]:
    """Load all datasets, returning a mapping of dataset name to rows added."""
    engine = get_engine(db_path)
    init_db(engine)
    return {
        name: load_dataframe(df, name, engine)
        for name, df in dataframes.items()
    }


def main(argv: list[str] | None = None) -> dict[str, int]:
    """Run extract -> validate -> load and print a summary of rows added."""
    import argparse

    from pipelines import extract
    from pipelines import validate as validate_module

    parser = argparse.ArgumentParser(
        prog="python -m pipelines.load",
        description="Ingest CTA datasets from the Chicago Data Portal into SQLite.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum rows to pull per dataset (default: pull everything).",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Path to the SQLite database (default: {DEFAULT_DB_PATH}).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    engine = get_engine(args.db)
    init_db(engine)

    frames = extract.extract_all(limit=args.limit)
    for name, df in frames.items():
        logger.info("Extracted %d rows for '%s'.", len(df), name)
        validate_module.validate(name, df)
        logger.info("Validated '%s'.", name)

    totals: dict[str, int] = {}
    for name, df in frames.items():
        totals[name] = load_dataframe(df, name, engine)

    print("Rows added:")
    for name, count in totals.items():
        print(f"  {name}: {count}")
    print(f"  total: {sum(totals.values())}")
    return totals


if __name__ == "__main__":  # pragma: no cover
    main()
