"""CLI entrypoint for the CTA ingestion pipeline.

Runs extract -> validate -> store (Parquet) and registers DuckDB views.
Parquet is the primary storage and DuckDB the primary query engine
(see pipelines.store).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> dict[str, int]:
    """Run extract -> validate -> store (Parquet) and print a summary of rows added."""
    import argparse

    from pipelines import extract
    from pipelines import store
    from pipelines import validate as validate_module

    parser = argparse.ArgumentParser(
        prog="python -m pipelines.load",
        description="Ingest CTA datasets from the Chicago Data Portal into Parquet.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum rows to pull per dataset (default: pull everything).",
    )
    parser.add_argument(
        "--root",
        default=str(store.PARQUET_ROOT),
        help=f"Directory to write Parquet files (default: {store.PARQUET_ROOT}).",
    )
    parser.add_argument(
        "--duckdb",
        default=None,
        help="Optional path to a persistent DuckDB database file (default: in-memory).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    frames = extract.extract_all(limit=args.limit)
    for name, df in frames.items():
        logger.info("Extracted %d rows for '%s'.", len(df), name)
        validate_module.validate(name, df)
        logger.info("Validated '%s'.", name)

    totals = store.write_all(frames, root=args.root)

    conn = store.get_connection(args.duckdb)
    views = store.create_views(conn, root=args.root)

    print("Rows added to Parquet:")
    for name, count in totals.items():
        print(f"  {name}: {count}")
    print(f"  total: {sum(totals.values())}")
    print(f"Registered {len(views)} DuckDB views ({', '.join(views)}).")
    if args.duckdb:
        conn.close()
    return totals


if __name__ == "__main__":  # pragma: no cover
    main()
