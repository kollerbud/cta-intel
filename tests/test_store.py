"""Tests for the Parquet store and DuckDB views in pipelines.store."""

from __future__ import annotations

import pandas as pd

from pipelines.store import create_views, get_connection, write_all, write_dataset


def test_write_dataset_creates_parquet(tmp_path, valid_bus_routes):
    assert write_dataset(valid_bus_routes, "bus_routes", root=tmp_path) == 3
    back = pd.read_parquet(
        tmp_path / "bus_routes.parquet", dtype_backend="numpy_nullable"
    )
    assert len(back) == 3


def test_write_dataset_is_idempotent(tmp_path, valid_bus_routes):
    assert write_dataset(valid_bus_routes, "bus_routes", root=tmp_path) == 3
    assert write_dataset(valid_bus_routes, "bus_routes", root=tmp_path) == 0
    back = pd.read_parquet(tmp_path / "bus_routes.parquet")
    assert len(back) == 3


def test_write_dataset_merges_only_new_rows(tmp_path, valid_bus_routes, make_bus_routes):
    assert write_dataset(valid_bus_routes, "bus_routes", root=tmp_path) == 3

    overlap = make_bus_routes(
        [
            {"date": "2024-01-01", "route": "1", "rides": 999},
            {"date": "2024-01-03", "route": "1", "rides": 520},
            {"date": "2024-01-03", "route": "2", "rides": 530},
        ]
    )
    assert write_dataset(overlap, "bus_routes", root=tmp_path) == 2

    back = pd.read_parquet(tmp_path / "bus_routes.parquet")
    assert len(back) == 5
    # the duplicate (2024-01-01, route '1') is upserted to its new value 999
    assert back["rides"].sum() == 999 + 600 + 510 + 520 + 530
    dup = back[
        (back["date"].astype(str) == "2024-01-01") & (back["route"] == "1")
    ]
    assert dup["rides"].iloc[0] == 999


def test_write_empty_dataframe_adds_nothing(tmp_path, make_bus_routes):
    assert write_dataset(make_bus_routes([]), "bus_routes", root=tmp_path) == 0
    assert not (tmp_path / "bus_routes.parquet").exists()


def test_create_views_run_against_parquet(
    tmp_path,
    make_ridership,
    make_bus_routes,
    make_rail_entries,
    make_rail_stations,
    make_bus_route_info,
):
    write_all(
        {
            "ridership": make_ridership(
                [
                    {"date": "2024-01-01", "bus": 1000, "rail_boardings": 500, "total_rides": 1500},
                    {"date": "2024-01-02", "bus": 1100, "rail_boardings": 520, "total_rides": 1620},
                ]
            ),
            "bus_routes": make_bus_routes(
                [
                    {"date": "2024-01-01", "route": "1", "rides": 500},
                    {"date": "2024-01-02", "route": "1", "rides": 510},
                ]
            ),
            "rail_entries": make_rail_entries(
                [{"date": "2024-01-01", "station_id": "40350", "rides": 300}]
            ),
            "rail_stations": make_rail_stations(
                [
                    {
                        "station_id": "40350",
                        "station_name": "UIC-Halsted",
                        "latitude": 41.875474,
                        "longitude": -87.649707,
                        "ada": True,
                        "blue": True,
                        "lines": "blue",
                    }
                ]
            ),
            "bus_route_info": make_bus_route_info(
                [{"route": "1", "route_name": "INDIANA/HYDE PARK", "runs_weekday": True}]
            ),
        },
        root=tmp_path,
    )

    conn = get_connection()
    views = create_views(conn, root=tmp_path)

    assert "v_daily_ridership" in views
    assert "rail_stations" in views
    assert "bus_route_info" in views
    assert conn.execute("SELECT COUNT(*) FROM v_daily_ridership").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM rail_stations").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM bus_route_info").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM v_ridership_recovery"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM v_route_concentration"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM v_mode_change"
    ).fetchone()[0] >= 1


def test_write_dimension_dataset_is_idempotent(tmp_path, valid_rail_stations):
    assert write_dataset(valid_rail_stations, "rail_stations", root=tmp_path) == 2
    assert write_dataset(valid_rail_stations, "rail_stations", root=tmp_path) == 0
    back = pd.read_parquet(tmp_path / "rail_stations.parquet")
    assert len(back) == 2


def test_write_dimension_upserts_on_key(tmp_path, valid_bus_route_info, make_bus_route_info):
    assert write_dataset(valid_bus_route_info, "bus_route_info", root=tmp_path) == 2
    update = make_bus_route_info(
        [
            {"route": "1", "route_name": "RENAMED"},
            {"route": "2", "route_name": "COTTAGE GROVE"},
        ]
    )
    assert write_dataset(update, "bus_route_info", root=tmp_path) == 1
    back = pd.read_parquet(
        tmp_path / "bus_route_info.parquet", dtype_backend="numpy_nullable"
    )
    # upsert updates route '1', adds route '2', and keeps the untouched 'X9'
    assert len(back) == 3
    assert set(back["route"]) == {"1", "2", "X9"}
    assert back[back["route"] == "1"]["route_name"].iloc[0] == "RENAMED"
