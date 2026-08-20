"""Shared pytest fixtures for the CTA ingestion pipeline tests."""

from __future__ import annotations

import pandas as pd
import pytest


def _ridership(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([r["date"] for r in rows]),
            "day_type": pd.Series([r.get("day_type", "W") for r in rows], dtype="string"),
            "bus": pd.array([r.get("bus", 0) for r in rows], dtype="Int64"),
            "rail_boardings": pd.array(
                [r.get("rail_boardings", 0) for r in rows], dtype="Int64"
            ),
            "total_rides": pd.array(
                [r.get("total_rides", 0) for r in rows], dtype="Int64"
            ),
        }
    )


def _bus_routes(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([r["date"] for r in rows]),
            "route": pd.Series([r["route"] for r in rows], dtype="string"),
            "day_type": pd.Series([r.get("day_type", "W") for r in rows], dtype="string"),
            "rides": pd.array([r.get("rides", 0) for r in rows], dtype="Int64"),
        }
    )


def _rail_entries(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([r["date"] for r in rows]),
            "station_id": pd.Series([r["station_id"] for r in rows], dtype="string"),
            "station_name": pd.Series(
                [r.get("station_name", "Station") for r in rows], dtype="string"
            ),
            "day_type": pd.Series([r.get("day_type", "W") for r in rows], dtype="string"),
            "rides": pd.array([r.get("rides", 0) for r in rows], dtype="Int64"),
        }
    )


def _rail_stations(rows: list[dict]) -> pd.DataFrame:
    line_cols = ["red", "blue", "brn", "g", "o", "p", "pnk", "y"]
    data = {
        "station_id": pd.Series([r["station_id"] for r in rows], dtype="string"),
        "station_name": pd.Series(
            [r.get("station_name", "Station") for r in rows], dtype="string"
        ),
        "station_descriptive_name": pd.Series(
            [r.get("station_descriptive_name") for r in rows], dtype="string"
        ),
        "latitude": pd.Series(
            [r.get("latitude") for r in rows], dtype="float64"
        ),
        "longitude": pd.Series(
            [r.get("longitude") for r in rows], dtype="float64"
        ),
    }
    data["ada"] = pd.array([r.get("ada") for r in rows], dtype="boolean")
    for col in line_cols:
        data[col] = pd.array([r.get(col, False) for r in rows], dtype="boolean")
    data["lines"] = pd.Series([r.get("lines", "") for r in rows], dtype="string")
    data["ward"] = pd.array([r.get("ward") for r in rows], dtype="Int64")
    data["community_area"] = pd.array(
        [r.get("community_area") for r in rows], dtype="Int64"
    )
    data["zip_code"] = pd.array([r.get("zip_code") for r in rows], dtype="Int64")
    return pd.DataFrame(data)


def _bus_route_info(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "route": pd.Series([r["route"] for r in rows], dtype="string"),
            "route_name": pd.Series(
                [r.get("route_name") for r in rows], dtype="string"
            ),
            "runs_weekday": pd.array(
                [r.get("runs_weekday") for r in rows], dtype="boolean"
            ),
            "runs_saturday": pd.array(
                [r.get("runs_saturday") for r in rows], dtype="boolean"
            ),
            "runs_sunday": pd.array(
                [r.get("runs_sunday") for r in rows], dtype="boolean"
            ),
            "geometry": pd.Series([r.get("geometry") for r in rows], dtype="string"),
        }
    )


@pytest.fixture
def make_ridership():
    return _ridership


@pytest.fixture
def make_bus_routes():
    return _bus_routes


@pytest.fixture
def make_rail_entries():
    return _rail_entries


@pytest.fixture
def make_rail_stations():
    return _rail_stations


@pytest.fixture
def make_bus_route_info():
    return _bus_route_info


@pytest.fixture
def valid_ridership() -> pd.DataFrame:
    return _ridership(
        [
            {"date": "2024-01-01", "bus": 1000, "rail_boardings": 500, "total_rides": 1500},
            {"date": "2024-01-02", "bus": 1100, "rail_boardings": 520, "total_rides": 1620},
        ]
    )


@pytest.fixture
def valid_bus_routes() -> pd.DataFrame:
    return _bus_routes(
        [
            {"date": "2024-01-01", "route": "1", "rides": 500},
            {"date": "2024-01-01", "route": "2", "rides": 600},
            {"date": "2024-01-02", "route": "1", "rides": 510},
        ]
    )


@pytest.fixture
def valid_rail_entries() -> pd.DataFrame:
    return _rail_entries(
        [
            {"date": "2024-01-01", "station_id": "40350", "station_name": "UIC-Halsted", "rides": 300},
            {"date": "2024-01-02", "station_id": "40350", "station_name": "UIC-Halsted", "rides": 310},
            {"date": "2024-01-01", "station_id": "41130", "station_name": "Halsted-Orange", "rides": 400},
        ]
    )


@pytest.fixture
def valid_rail_stations() -> pd.DataFrame:
    return _rail_stations(
        [
            {
                "station_id": "40350",
                "station_name": "UIC-Halsted",
                "station_descriptive_name": "UIC-Halsted (Blue Line)",
                "latitude": 41.875474,
                "longitude": -87.649707,
                "ada": True,
                "blue": True,
                "lines": "blue",
                "ward": 2,
                "community_area": 28,
                "zip_code": 60607,
            },
            {
                "station_id": "41130",
                "station_name": "Halsted",
                "station_descriptive_name": "Halsted (Orange Line)",
                "latitude": 41.84678,
                "longitude": -87.648088,
                "ada": True,
                "o": True,
                "lines": "o",
                "ward": 11,
                "community_area": 31,
                "zip_code": 60608,
            },
        ]
    )


@pytest.fixture
def valid_bus_route_info() -> pd.DataFrame:
    return _bus_route_info(
        [
            {
                "route": "1",
                "route_name": "INDIANA/HYDE PARK",
                "runs_weekday": True,
                "runs_saturday": True,
                "runs_sunday": True,
                "geometry": '{"type": "MultiLineString", "coordinates": []}',
            },
            {
                "route": "X9",
                "route_name": "ASHLAND EXPRESS",
                "runs_weekday": True,
                "runs_saturday": False,
                "runs_sunday": False,
                "geometry": '{"type": "MultiLineString", "coordinates": []}',
            },
        ]
    )
