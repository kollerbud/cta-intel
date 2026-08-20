"""Pandera schemas and validation for CTA ingestion dataframes."""

from __future__ import annotations

import logging

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when a dataframe fails schema validation."""


def _ridership_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "date": pa.Column(pa.Timestamp, nullable=False),
            "day_type": pa.Column(str, nullable=True),
            "bus": pa.Column(int, pa.Check.ge(0), nullable=True),
            "rail_boardings": pa.Column(int, pa.Check.ge(0), nullable=True),
            "total_rides": pa.Column(int, pa.Check.ge(0), nullable=True),
        },
        unique=["date"],
        strict=True,
    )


def _bus_routes_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "date": pa.Column(pa.Timestamp, nullable=False),
            "route": pa.Column(str, nullable=False),
            "day_type": pa.Column(str, nullable=True),
            "rides": pa.Column(int, pa.Check.ge(0), nullable=True),
        },
        unique=["date", "route"],
        strict=True,
    )


def _rail_entries_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "date": pa.Column(pa.Timestamp, nullable=False),
            "station_id": pa.Column(str, nullable=False),
            "station_name": pa.Column(str, nullable=True),
            "day_type": pa.Column(str, nullable=True),
            "rides": pa.Column(int, pa.Check.ge(0), nullable=True),
        },
        unique=["date", "station_id"],
        strict=True,
    )


def _rail_stations_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "station_id": pa.Column(str, nullable=False),
            "station_name": pa.Column(str, nullable=True),
            "station_descriptive_name": pa.Column(str, nullable=True),
            "latitude": pa.Column(float, pa.Check.in_range(-90, 90), nullable=True),
            "longitude": pa.Column(float, pa.Check.in_range(-180, 180), nullable=True),
            "ada": pa.Column("boolean", nullable=True),
            "red": pa.Column("boolean", nullable=True),
            "blue": pa.Column("boolean", nullable=True),
            "brn": pa.Column("boolean", nullable=True),
            "g": pa.Column("boolean", nullable=True),
            "o": pa.Column("boolean", nullable=True),
            "p": pa.Column("boolean", nullable=True),
            "pnk": pa.Column("boolean", nullable=True),
            "y": pa.Column("boolean", nullable=True),
            "lines": pa.Column(str, nullable=True),
            "ward": pa.Column(int, pa.Check.ge(0), nullable=True),
            "community_area": pa.Column(int, pa.Check.ge(0), nullable=True),
            "zip_code": pa.Column(int, pa.Check.ge(0), nullable=True),
        },
        unique=["station_id"],
        strict=True,
    )


def _bus_route_info_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "route": pa.Column(str, nullable=False),
            "route_name": pa.Column(str, nullable=True),
            "runs_weekday": pa.Column("boolean", nullable=True),
            "runs_saturday": pa.Column("boolean", nullable=True),
            "runs_sunday": pa.Column("boolean", nullable=True),
            "geometry": pa.Column(str, nullable=True),
        },
        unique=["route"],
        strict=True,
    )


SCHEMAS: dict[str, pa.DataFrameSchema] = {
    "ridership": _ridership_schema(),
    "bus_routes": _bus_routes_schema(),
    "rail_entries": _rail_entries_schema(),
    "rail_stations": _rail_stations_schema(),
    "bus_route_info": _bus_route_info_schema(),
}


def validate(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Validate a dataframe against the schema for the named dataset.

    Raises ValidationError with the offending rows logged on failure.
    """
    schema = SCHEMAS[name]
    if df.empty:
        return df
    try:
        return schema.validate(df, lazy=True)
    except SchemaErrors as exc:
        logger.error("Validation failed for '%s' dataset.", name)
        logger.error("Offending rows:\n%s", exc.failure_cases.to_string())
        raise ValidationError(
            f"Validation failed for '{name}' dataset "
            f"with {len(exc.failure_cases)} offending row(s)."
        ) from exc
