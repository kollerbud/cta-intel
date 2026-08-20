"""Tests for the pandera validation rules in pipelines.validate."""

from __future__ import annotations

import pytest

from pipelines.validate import ValidationError, validate


def test_valid_frames_pass(
    valid_ridership,
    valid_bus_routes,
    valid_rail_entries,
    valid_rail_stations,
    valid_bus_route_info,
):
    assert validate("ridership", valid_ridership) is not None
    assert validate("bus_routes", valid_bus_routes) is not None
    assert validate("rail_entries", valid_rail_entries) is not None
    assert validate("rail_stations", valid_rail_stations) is not None
    assert validate("bus_route_info", valid_bus_route_info) is not None


def test_negative_rides_rejected(make_bus_routes):
    df = make_bus_routes(
        [
            {"date": "2024-01-01", "route": "1", "rides": 500},
            {"date": "2024-01-01", "route": "2", "rides": -1},
        ]
    )
    with pytest.raises(ValidationError):
        validate("bus_routes", df)


def test_null_date_rejected(make_bus_routes):
    df = make_bus_routes([{"date": "2024-01-01", "route": "1", "rides": 500}])
    df.loc[0, "date"] = None
    with pytest.raises(ValidationError):
        validate("bus_routes", df)


def test_duplicate_date_route_rejected(make_bus_routes):
    df = make_bus_routes(
        [
            {"date": "2024-01-01", "route": "1", "rides": 500},
            {"date": "2024-01-01", "route": "1", "rides": 600},
        ]
    )
    with pytest.raises(ValidationError):
        validate("bus_routes", df)


def test_duplicate_date_station_rejected(make_rail_entries):
    df = make_rail_entries(
        [
            {"date": "2024-01-01", "station_id": "40350", "rides": 300},
            {"date": "2024-01-01", "station_id": "40350", "rides": 300},
        ]
    )
    with pytest.raises(ValidationError):
        validate("rail_entries", df)


def test_duplicate_date_rejected_for_ridership(make_ridership):
    df = make_ridership(
        [
            {"date": "2024-01-01", "bus": 1000, "rail_boardings": 500, "total_rides": 1500},
            {"date": "2024-01-01", "bus": 1001, "rail_boardings": 501, "total_rides": 1502},
        ]
    )
    with pytest.raises(ValidationError):
        validate("ridership", df)


def test_wrong_column_type_rejected(make_bus_routes):
    df = make_bus_routes([{"date": "2024-01-01", "route": "1", "rides": 500}])
    df["rides"] = df["rides"].astype("string")
    with pytest.raises(ValidationError):
        validate("bus_routes", df)


def test_missing_column_rejected(make_bus_routes):
    df = make_bus_routes([{"date": "2024-01-01", "route": "1", "rides": 500}])
    df = df.drop(columns=["rides"])
    with pytest.raises(ValidationError):
        validate("bus_routes", df)


def test_duplicate_station_id_rejected(make_rail_stations):
    df = make_rail_stations(
        [
            {"station_id": "40350", "station_name": "UIC-Halsted", "latitude": 41.8, "longitude": -87.6},
            {"station_id": "40350", "station_name": "UIC-Halsted", "latitude": 41.8, "longitude": -87.6},
        ]
    )
    with pytest.raises(ValidationError):
        validate("rail_stations", df)


def test_out_of_range_latitude_rejected(make_rail_stations):
    df = make_rail_stations(
        [{"station_id": "40350", "station_name": "UIC-Halsted", "latitude": 95.0, "longitude": -87.6}]
    )
    with pytest.raises(ValidationError):
        validate("rail_stations", df)


def test_duplicate_route_rejected(make_bus_route_info):
    df = make_bus_route_info(
        [
            {"route": "1", "route_name": "INDIANA/HYDE PARK"},
            {"route": "1", "route_name": "INDIANA/HYDE PARK"},
        ]
    )
    with pytest.raises(ValidationError):
        validate("bus_route_info", df)
