"""Fetch CTA datasets from the Chicago Data Portal via the Socrata SODA API."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SODA_ENDPOINT = "https://data.cityofchicago.org/resource"
DEFAULT_TIMEOUT = 60

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
    """Return the raw rows for a SODA dataset as a DataFrame."""
    params: dict[str, str] = {}
    if where:
        params["$where"] = where
    if order:
        params["$order"] = order
    if limit is not None:
        params["$limit"] = str(limit)

    headers: dict[str, str] = {}
    token = _app_token()
    if token:
        headers["X-App-Token"] = token

    url = f"{SODA_ENDPOINT}/{dataset_id}.json"
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    records = response.json()
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


def _normalize(raw: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    df = raw.rename(columns=config["renames"])
    if df.empty:
        return df.reindex(columns=config["output_columns"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in config["int_columns"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in config["string_columns"]:
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
    if order is None:
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


def extract_all(*, limit: int | None = None) -> dict[str, pd.DataFrame]:
    """Extract all configured datasets, newest rows first."""
    return {name: extract_dataset(name, limit=limit) for name in DATASET_CONFIG}
