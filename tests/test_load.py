"""Tests for the idempotent upsert in pipelines.load."""

from __future__ import annotations

from sqlalchemy import select

from pipelines.load import (
    bus_routes_table,
    get_engine,
    init_db,
    load_dataframe,
    ridership_table,
)


def _count_rows(engine, table) -> int:
    with engine.connect() as conn:
        return conn.execute(select(table)).fetchall().__len__()


def test_first_load_adds_all_rows(tmp_path, valid_bus_routes):
    engine = get_engine(tmp_path / "cta.db")
    init_db(engine)

    assert load_dataframe(valid_bus_routes, "bus_routes", engine) == 3
    assert _count_rows(engine, bus_routes_table) == 3


def test_rerun_is_idempotent(tmp_path, valid_bus_routes):
    engine = get_engine(tmp_path / "cta.db")
    init_db(engine)

    assert load_dataframe(valid_bus_routes, "bus_routes", engine) == 3
    assert load_dataframe(valid_bus_routes, "bus_routes", engine) == 0
    assert _count_rows(engine, bus_routes_table) == 3


def test_overlapping_load_adds_only_new_rows(tmp_path, valid_bus_routes, make_bus_routes):
    engine = get_engine(tmp_path / "cta.db")
    init_db(engine)

    assert load_dataframe(valid_bus_routes, "bus_routes", engine) == 3

    overlap = make_bus_routes(
        [
            {"date": "2024-01-01", "route": "1", "rides": 999},
            {"date": "2024-01-03", "route": "1", "rides": 520},
            {"date": "2024-01-03", "route": "2", "rides": 530},
        ]
    )
    assert load_dataframe(overlap, "bus_routes", engine) == 2
    assert _count_rows(engine, bus_routes_table) == 5


def test_single_key_ridership_upsert(tmp_path, valid_ridership, make_ridership):
    engine = get_engine(tmp_path / "cta.db")
    init_db(engine)

    assert load_dataframe(valid_ridership, "ridership", engine) == 2
    assert load_dataframe(valid_ridership, "ridership", engine) == 0

    new_day = make_ridership(
        [{"date": "2024-01-03", "bus": 1200, "rail_boardings": 600, "total_rides": 1800}]
    )
    assert load_dataframe(new_day, "ridership", engine) == 1
    assert _count_rows(engine, ridership_table) == 3


def test_empty_dataframe_adds_nothing(tmp_path, make_bus_routes):
    engine = get_engine(tmp_path / "cta.db")
    init_db(engine)

    empty = make_bus_routes([])
    assert load_dataframe(empty, "bus_routes", engine) == 0
    assert _count_rows(engine, bus_routes_table) == 0
