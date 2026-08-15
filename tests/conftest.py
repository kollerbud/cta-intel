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
