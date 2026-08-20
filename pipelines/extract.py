"""Fetch CTA datasets from the Chicago Data Portal via the Socrata SODA API."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SODA_ENDPOINT = "https://data.cityofchicago.org/resource"
DEFAULT_TIMEOUT = 60
PAGE_SIZE = 50_000

# 'L' line colour flags published as boolean columns on the stops dataset.
_LINE_COLS = ["red", "blue", "brn", "g", "o", "p", "pnk", "y"]


def _rail_stations_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten the nested ``location`` point, collapse line flags and dedupe to
    one row per station (``map_id``). Stop-level fields (direction, stop name)
    are dropped because the dimension joins to station-level entries."""
    location = df["location"]
    df["latitude"] = location.map(
        lambda v: v.get("latitude") if isinstance(v, dict) else None
    )
    df["longitude"] = location.map(
        lambda v: v.get("longitude") if isinstance(v, dict) else None
    )
    line_flags = df[_LINE_COLS].fillna(False).astype(bool)
    df["lines"] = [
        ",".join(col for col, present in zip(_LINE_COLS, row) if present)
        for row in line_flags.itertuples(index=False, name=None)
    ]
    return df.drop_duplicates(subset=["station_id"], keep="first")


def _bus_route_info_transform(df: pd.DataFrame) -> pd.DataFrame:
    """Serialize the GeoJSON ``the_geom`` object to a string so it round-trips
    through Parquet as a plain column."""
    df["geometry"] = df["geometry"].map(
        lambda v: json.dumps(v) if isinstance(v, dict) else None
    )
    return df

DATASET_CONFIG: dict[str, dict[str, Any]] = {
    "ridership": {
        "id": "6iiy-9s97",
        "date_column": "service_date",
        "renames": {"service_date": "date"},
        "string_columns": ["day_type"],
        "int_columns": ["bus", "rail_boardings", "total_rides"],
        "output_columns": ["date", "day_type", "bus", "rail_boardings", "total_rides"],
    },
    "bus_routes": {
        "id": "jyb9-n7fm",
        "date_column": "date",
        "renames": {"daytype": "day_type"},
        "string_columns": ["route", "day_type"],
        "int_columns": ["rides"],
        "output_columns": ["date", "route", "day_type", "rides"],
    },
    "rail_entries": {
        "id": "5neh-572f",
        "date_column": "date",
        "renames": {"daytype": "day_type", "stationname": "station_name"},
        "string_columns": ["station_id", "station_name", "day_type"],
        "int_columns": ["rides"],
        "output_columns": ["date", "station_id", "station_name", "day_type", "rides"],
    },
    # Reference / dimension datasets (no service date). They are refreshed in
    # full on every run and upserted on their natural key.
    "rail_stations": {
        "id": "8pix-ypme",
        "date_column": None,
        "renames": {
            "map_id": "station_id",
            ":@computed_region_43wa_7qmu": "ward",
            ":@computed_region_vrxf_vc4k": "community_area",
            ":@computed_region_6mkv_f3dw": "zip_code",
        },
        "string_columns": [
            "station_id",
            "station_name",
            "station_descriptive_name",
            "lines",
        ],
        "int_columns": ["ward", "community_area", "zip_code"],
        "float_columns": ["latitude", "longitude"],
        "bool_columns": ["ada", *_LINE_COLS],
        "output_columns": [
            "station_id",
            "station_name",
            "station_descriptive_name",
            "latitude",
            "longitude",
            "ada",
            *_LINE_COLS,
            "lines",
            "ward",
            "community_area",
            "zip_code",
        ],
        "transform": _rail_stations_transform,
    },
    "bus_route_info": {
        "id": "6uva-a5ei",
        "date_column": None,
        "renames": {
            "name": "route_name",
            "wkday": "runs_weekday",
            "sat": "runs_saturday",
            "sun": "runs_sunday",
            "the_geom": "geometry",
        },
        "string_columns": ["route", "route_name", "geometry"],
        "int_columns": [],
        "float_columns": [],
        "bool_columns": ["runs_weekday", "runs_saturday", "runs_sunday"],
        "output_columns": [
            "route",
            "route_name",
            "runs_weekday",
            "runs_saturday",
            "runs_sunday",
            "geometry",
        ],
        "transform": _bus_route_info_transform,
    },
}


def _app_token() -> str | None:
    return os.environ.get("SOCRATA_APP_TOKEN")


def fetch_dataset(
    dataset_id: str,
    *,
    limit: int | None = None,
    where: str | None = None,
    order: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Return the raw rows for a SODA dataset as a DataFrame, paginating as needed."""
    params: dict[str, str] = {}
    if where:
        params["$where"] = where
    if order:
        params["$order"] = order

    headers: dict[str, str] = {}
    token = _app_token()
    if token:
        headers["X-App-Token"] = token

    url = f"{SODA_ENDPOINT}/{dataset_id}.json"

    records: list[dict[str, Any]] = []
    offset = 0
    while True:
        if limit is not None:
            page_limit = min(PAGE_SIZE, limit - offset)
            if page_limit <= 0:
                break
        else:
            page_limit = PAGE_SIZE

        params["$offset"] = str(offset)
        params["$limit"] = str(page_limit)
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        page = response.json()
        if not page:
            break

        records.extend(page)
        if len(page) < page_limit:
            break
        offset += len(page)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


def _normalize(raw: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    df = raw.rename(columns=config["renames"])
    if df.empty:
        return df.reindex(columns=config["output_columns"])

    transform = config.get("transform")
    if transform is not None:
        df = transform(df)
    if config.get("date_column"):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in config.get("int_columns", []):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in config.get("float_columns", []):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    for col in config.get("bool_columns", []):
        df[col] = df[col].astype("boolean")
    for col in config.get("string_columns", []):
        df[col] = df[col].astype("string")
    return df[config["output_columns"]]


def extract_dataset(
    name: str,
    *,
    limit: int | None = None,
    where: str | None = None,
    order: str | None = None,
) -> pd.DataFrame:
    """Extract and normalize a single dataset by name."""
    config = DATASET_CONFIG[name]
    if order is None and config.get("date_column"):
        order = f"{config['date_column']} DESC"
    raw = fetch_dataset(config["id"], limit=limit, where=where, order=order)
    return _normalize(raw, config)


def extract_ridership(
    *, limit: int | None = None, where: str | None = None, order: str | None = None
) -> pd.DataFrame:
    """Extract CTA Ridership Daily Boarding Totals (6iiy-9s97)."""
    return extract_dataset("ridership", limit=limit, where=where, order=order)


def extract_bus_routes(
    *, limit: int | None = None, where: str | None = None, order: str | None = None
) -> pd.DataFrame:
    """Extract CTA Bus Routes Daily Totals by Route (jyb9-n7fm)."""
    return extract_dataset("bus_routes", limit=limit, where=where, order=order)


def extract_rail_entries(
    *, limit: int | None = None, where: str | None = None, order: str | None = None
) -> pd.DataFrame:
    """Extract CTA 'L' Station Entries Daily Totals (5neh-572f)."""
    return extract_dataset("rail_entries", limit=limit, where=where, order=order)


def extract_rail_stations(
    *, limit: int | None = None, where: str | None = None, order: str | None = None
) -> pd.DataFrame:
    """Extract CTA System Information List of 'L' Stops (8pix-ypme) as a
    station-level dimension keyed by ``station_id`` (== rail_entries.station_id)."""
    return extract_dataset("rail_stations", limit=limit, where=where, order=order)


def extract_bus_route_info(
    *, limit: int | None = None, where: str | None = None, order: str | None = None
) -> pd.DataFrame:
    """Extract CTA Bus Routes (6uva-a5ei) as a route dimension keyed by
    ``route`` (== bus_routes.route), providing route names and service flags."""
    return extract_dataset("bus_route_info", limit=limit, where=where, order=order)


def extract_all(*, limit: int | None = None) -> dict[str, pd.DataFrame]:
    """Extract all configured datasets, newest rows first.

    Dimension datasets (no ``date_column``) are always fetched in full so a
    ``--limit`` meant for the large time-series tables never truncates them.
    """
    frames: dict[str, pd.DataFrame] = {}
    for name, config in DATASET_CONFIG.items():
        dataset_limit = None if config.get("date_column") is None else limit
        frames[name] = extract_dataset(name, limit=dataset_limit)
    return frames
