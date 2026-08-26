#!/usr/bin/env python3
"""Collect analysis-ready weather data for Hawatch route points.

The input is ``hawatch_route_points_catalog.json``. The script:

1. loads every enabled, geolocated Point (or only selected routes/points),
2. fetches Copernicus GLO-90 elevations in one or more batched requests,
3. queries Open-Meteo in scenarios that isolate:
   - normal target-elevation forecast,
   - raw model-grid elevation,
   - nearest-cell versus terrain-aware land-cell selection,
   - ECMWF/GFS/ICON model disagreement,
4. keeps the complete API responses and adds point/route diagnostics,
5. writes one JSON file that can be uploaded for deeper analysis.

Only the Python standard library is required (Python 3.10+).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


SCRIPT_VERSION = "1.0.0"
SCHEMA_VERSION = "hawatch.point-weather-probe.v1"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
TIMEZONE = "Asia/Tehran"
USER_AGENT = f"hawatch-point-weather-probe/{SCRIPT_VERSION}"


CORE_HOURLY = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "wet_bulb_temperature_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "snow_depth",
    "weather_code",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "visibility",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "freezing_level_height",
    "cape",
    "lifted_index",
    "convective_inhibition",
    "boundary_layer_height",
    "is_day",
]

RICH_EXTRA_HOURLY = [
    "soil_temperature_0cm",
    "soil_temperature_6cm",
    "soil_moisture_0_to_1cm",
    "soil_moisture_1_to_3cm",
    "soil_moisture_3_to_9cm",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "uv_index",
    "sunshine_duration",
    "vapour_pressure_deficit",
]

PRESSURE_LEVEL_HPA = (925, 850, 700, 600, 500)
PRESSURE_LEVEL_HOURLY = [
    f"{variable}_{level}hPa"
    for level in PRESSURE_LEVEL_HPA
    for variable in (
        "temperature",
        "relative_humidity",
        "cloud_cover",
        "wind_speed",
        "wind_direction",
        "geopotential_height",
    )
]

CURRENT_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "wet_bulb_temperature_2m",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "visibility",
    "freezing_level_height",
    "cape",
    "is_day",
]

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "sunrise",
    "sunset",
    "daylight_duration",
    "sunshine_duration",
    "uv_index_max",
    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "snowfall_sum",
    "precipitation_hours",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "cape_max",
    "visibility_min",
]

SAFE_HOURLY = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "visibility",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "freezing_level_height",
    "cape",
]

SAFE_CURRENT = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

SAFE_DAILY = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "snowfall_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "sunrise",
    "sunset",
]

MODEL_SPREAD_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "snowfall",
    "visibility",
    "wind_speed_10m",
    "wind_gusts_10m",
    "freezing_level_height",
    "cape",
]


def unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


RICH_HOURLY = unique(CORE_HOURLY + RICH_EXTRA_HOURLY + PRESSURE_LEVEL_HOURLY)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    model: str
    elevation_mode: str
    cell_selection: str
    variable_set: str
    include_daily: bool
    purpose: str


SCENARIOS = [
    Scenario(
        "best_match_target_land_rich",
        "best_match",
        "target",
        "land",
        "rich",
        True,
        "Primary product: selected point elevation and terrain-aware land cell.",
    ),
    Scenario(
        "best_match_raw_land_core",
        "best_match",
        "raw_grid",
        "land",
        "core",
        False,
        "Expose raw model-grid elevation to measure downscaling impact.",
    ),
    Scenario(
        "best_match_target_nearest_core",
        "best_match",
        "target",
        "nearest",
        "core",
        False,
        "Measure land-cell versus nearest-cell selection impact.",
    ),
    Scenario(
        "ecmwf_ifs025_target_land",
        "ecmwf_ifs025",
        "target",
        "land",
        "core",
        False,
        "ECMWF deterministic comparison at selected point elevation.",
    ),
    Scenario(
        "gfs_seamless_target_land",
        "gfs_seamless",
        "target",
        "land",
        "core",
        False,
        "GFS deterministic comparison at selected point elevation.",
    ),
    Scenario(
        "icon_seamless_target_land",
        "icon_seamless",
        "target",
        "land",
        "core",
        False,
        "ICON deterministic comparison at selected point elevation.",
    ),
]

MODEL_SCENARIO_IDS = {
    "ecmwf_ifs025_target_land",
    "gfs_seamless_target_land",
    "icon_seamless_target_land",
}
PRIMARY_SCENARIO_ID = "best_match_target_land_rich"


class ApiRequestError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_008.8
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.asin(min(1.0, math.sqrt(a)))


def chunks(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_url(base_url: str, params: dict[str, Any]) -> str:
    return f"{base_url}?{urllib.parse.urlencode(params, safe=',')}"


def get_json(
    url: str,
    *,
    timeout_seconds: float,
    max_attempts: int = 4,
) -> tuple[Any, dict[str, str]]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
                headers = {
                    key.lower(): value
                    for key, value in response.headers.items()
                    if key.lower()
                    in {
                        "date",
                        "etag",
                        "last-modified",
                        "cache-control",
                        "x-ratelimit-limit",
                        "x-ratelimit-remaining",
                    }
                }
                return payload, headers
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:4000]
            last_error = ApiRequestError(
                f"HTTP {exc.code} for {url}", status=exc.code, body=body
            )
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise last_error from exc
            if attempt == max_attempts:
                raise last_error from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == max_attempts:
                raise ApiRequestError(f"Request failed for {url}: {exc}") from exc
        time.sleep(min(2 ** (attempt - 1), 8))
    raise ApiRequestError(f"Request failed for {url}: {last_error}")


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read catalog {path}: {exc}") from exc
    if not isinstance(catalog, dict):
        raise ValueError("Catalog root must be a JSON object")
    if not isinstance(catalog.get("points"), list):
        raise ValueError("Catalog must contain a points array")
    if not isinstance(catalog.get("routes"), list):
        raise ValueError("Catalog must contain a routes array")
    return catalog


def select_catalog_data(
    catalog: dict[str, Any],
    *,
    route_ids: set[str],
    point_ids: set[str],
    include_disabled: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    all_points = {point["id"]: dict(point) for point in catalog["points"]}
    all_routes = {route["id"]: dict(route) for route in catalog["routes"]}

    unknown_routes = sorted(route_ids - all_routes.keys())
    unknown_points = sorted(point_ids - all_points.keys())
    if unknown_routes:
        raise ValueError(f"Unknown route ids: {', '.join(unknown_routes)}")
    if unknown_points:
        raise ValueError(f"Unknown point ids: {', '.join(unknown_points)}")

    if route_ids:
        selected_route_ids = set(route_ids)
    elif point_ids:
        selected_route_ids = {
            route_id
            for route_id, route in all_routes.items()
            if any(
                relation.get("point_id") in point_ids
                for relation in route.get("point_sequence", [])
            )
        }
    else:
        selected_route_ids = set(all_routes)
    selected_routes = [all_routes[route_id] for route_id in all_routes if route_id in selected_route_ids]

    required_point_ids = set(point_ids)
    if not point_ids:
        for route in selected_routes:
            for relation in route.get("point_sequence", []):
                if relation.get("weather_sample", True):
                    required_point_ids.add(relation["point_id"])

    points: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for point_id in all_points:
        if point_id not in required_point_ids:
            continue
        point = all_points[point_id]
        reasons = []
        if point.get("latitude") is None or point.get("longitude") is None:
            reasons.append("missing_coordinates")
        if not point.get("weather_sampling_enabled", False) and not include_disabled:
            reasons.append("weather_sampling_disabled")
        if reasons:
            skipped.append(
                {
                    "point_id": point_id,
                    "name_fa": point.get("name_fa"),
                    "reasons": reasons,
                }
            )
            continue
        point["point_id"] = point.pop("id")
        point["catalog_elevation_m"] = optional_float(point.get("elevation_m"))
        points.append(point)

    selected_point_ids = {point["point_id"] for point in points}
    usable_routes = []
    for route in selected_routes:
        copied = dict(route)
        copied["point_sequence"] = [
            relation
            for relation in route.get("point_sequence", [])
            if relation["point_id"] in selected_point_ids
            and relation.get("weather_sample", True)
        ]
        usable_routes.append(copied)

    return points, usable_routes, skipped


def assign_dem_and_target_elevations(
    points: list[dict[str, Any]],
    *,
    batch_size: int,
    timeout_seconds: float,
    errors: list[dict[str, Any]],
) -> None:
    total_batches = math.ceil(len(points) / batch_size)
    for batch_number, point_batch in enumerate(chunks(points, batch_size), start=1):
        params = {
            "latitude": ",".join(f"{point['latitude']:.7f}" for point in point_batch),
            "longitude": ",".join(f"{point['longitude']:.7f}" for point in point_batch),
        }
        url = build_url(ELEVATION_URL, params)
        print(f"[elevation {batch_number}/{total_batches}] {len(point_batch)} points")
        try:
            payload, _headers = get_json(url, timeout_seconds=timeout_seconds)
            elevations = payload.get("elevation", []) if isinstance(payload, dict) else []
            if len(elevations) != len(point_batch):
                raise ApiRequestError(
                    f"Elevation response count mismatch: expected {len(point_batch)}, "
                    f"received {len(elevations)}"
                )
            for point, elevation in zip(point_batch, elevations):
                point["dem_elevation_m"] = optional_float(elevation)
        except ApiRequestError as exc:
            errors.append(
                {
                    "stage": "elevation",
                    "batch_number": batch_number,
                    "point_ids": [point["point_id"] for point in point_batch],
                    "status": exc.status,
                    "message": str(exc),
                    "response_body": exc.body,
                    "request_url": url,
                }
            )
            for point in point_batch:
                point["dem_elevation_m"] = None

    for point in points:
        catalog_elevation = point.get("catalog_elevation_m")
        dem_elevation = point.get("dem_elevation_m")
        if catalog_elevation is not None:
            point["target_elevation_m"] = catalog_elevation
            point["target_elevation_source"] = "catalog"
        elif dem_elevation is not None:
            point["target_elevation_m"] = dem_elevation
            point["target_elevation_source"] = "open_meteo_copernicus_glo90"
        else:
            point["target_elevation_m"] = None
            point["target_elevation_source"] = "missing_raw_grid_fallback"
        point["catalog_minus_dem_m"] = (
            round(catalog_elevation - dem_elevation, 1)
            if catalog_elevation is not None and dem_elevation is not None
            else None
        )


def scenario_params(
    point_batch: Sequence[dict[str, Any]],
    scenario: Scenario,
    *,
    hourly: Sequence[str],
    current: Sequence[str],
    daily: Sequence[str],
    forecast_hours: int,
    past_hours: int,
) -> dict[str, Any]:
    if scenario.elevation_mode == "target":
        elevations = [
            "nan"
            if point.get("target_elevation_m") is None
            else f"{point['target_elevation_m']:.1f}"
            for point in point_batch
        ]
    else:
        elevations = ["nan"] * len(point_batch)

    params: dict[str, Any] = {
        "latitude": ",".join(f"{point['latitude']:.7f}" for point in point_batch),
        "longitude": ",".join(f"{point['longitude']:.7f}" for point in point_batch),
        "elevation": ",".join(elevations),
        "timezone": TIMEZONE,
        "models": scenario.model,
        "cell_selection": scenario.cell_selection,
        "forecast_hours": forecast_hours,
        "past_hours": past_hours,
        "hourly": ",".join(hourly),
        "current": ",".join(current),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }
    if daily:
        params["daily"] = ",".join(daily)
    return params


def normalise_location_responses(payload: Any, expected: int) -> list[dict[str, Any]]:
    responses = payload if isinstance(payload, list) else [payload]
    if len(responses) != expected:
        raise ApiRequestError(
            f"Forecast response count mismatch: expected {expected}, received {len(responses)}"
        )
    if not all(isinstance(response, dict) for response in responses):
        raise ApiRequestError("Forecast response contains a non-object item")
    return responses


def fetch_forecasts(
    points: list[dict[str, Any]],
    scenarios: Sequence[Scenario],
    *,
    batch_size: int,
    forecast_hours: int,
    past_hours: int,
    timeout_seconds: float,
    pause_seconds: float,
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    total_batches = math.ceil(len(points) / batch_size)
    total_requests = total_batches * len(scenarios)
    request_number = 0

    for scenario in scenarios:
        for batch_number, point_batch in enumerate(chunks(points, batch_size), start=1):
            request_number += 1
            hourly = RICH_HOURLY if scenario.variable_set == "rich" else CORE_HOURLY
            current = CURRENT_VARIABLES
            daily = DAILY_VARIABLES if scenario.include_daily else []
            fallback_used = False
            params = scenario_params(
                point_batch,
                scenario,
                hourly=hourly,
                current=current,
                daily=daily,
                forecast_hours=forecast_hours,
                past_hours=past_hours,
            )
            url = build_url(FORECAST_URL, params)
            print(
                f"[forecast {request_number}/{total_requests}] {scenario.scenario_id}, "
                f"batch {batch_number}/{total_batches}, {len(point_batch)} points"
            )
            try:
                try:
                    payload, headers = get_json(url, timeout_seconds=timeout_seconds)
                except ApiRequestError as first_exc:
                    if first_exc.status != 400:
                        raise
                    fallback_used = True
                    hourly = SAFE_HOURLY
                    current = SAFE_CURRENT
                    daily = SAFE_DAILY if scenario.include_daily else []
                    params = scenario_params(
                        point_batch,
                        scenario,
                        hourly=hourly,
                        current=current,
                        daily=daily,
                        forecast_hours=forecast_hours,
                        past_hours=past_hours,
                    )
                    url = build_url(FORECAST_URL, params)
                    payload, headers = get_json(url, timeout_seconds=timeout_seconds)

                responses = normalise_location_responses(payload, len(point_batch))
                fetched_at = utc_now()
                for point, response in zip(point_batch, responses):
                    returned_lat = optional_float(response.get("latitude"))
                    returned_lon = optional_float(response.get("longitude"))
                    returned_elevation = optional_float(response.get("elevation"))
                    grid_distance = (
                        haversine_m(
                            point["latitude"],
                            point["longitude"],
                            returned_lat,
                            returned_lon,
                        )
                        if returned_lat is not None and returned_lon is not None
                        else None
                    )
                    target_elevation = point.get("target_elevation_m")
                    records.append(
                        {
                            "point_id": point["point_id"],
                            "scenario_id": scenario.scenario_id,
                            "model_requested": scenario.model,
                            "elevation_mode": scenario.elevation_mode,
                            "cell_selection": scenario.cell_selection,
                            "fallback_variable_set_used": fallback_used,
                            "variables_requested": {
                                "hourly": hourly,
                                "current": current,
                                "daily": daily,
                            },
                            "fetched_at_utc": fetched_at,
                            "response_headers": headers,
                            "returned_grid": {
                                "latitude": returned_lat,
                                "longitude": returned_lon,
                                "elevation_m": returned_elevation,
                                "distance_from_requested_point_m": (
                                    round(grid_distance, 1)
                                    if grid_distance is not None
                                    else None
                                ),
                                "target_minus_returned_elevation_m": (
                                    round(target_elevation - returned_elevation, 1)
                                    if target_elevation is not None
                                    and returned_elevation is not None
                                    else None
                                ),
                            },
                            "api_response": response,
                        }
                    )
            except ApiRequestError as exc:
                errors.append(
                    {
                        "stage": "forecast",
                        "scenario_id": scenario.scenario_id,
                        "batch_number": batch_number,
                        "point_ids": [point["point_id"] for point in point_batch],
                        "status": exc.status,
                        "message": str(exc),
                        "response_body": exc.body,
                        "request_url": url,
                    }
                )
            if pause_seconds > 0 and request_number < total_requests:
                time.sleep(pause_seconds)
    return records


def hourly_rows(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hourly = record.get("api_response", {}).get("hourly", {})
    times = hourly.get("time", [])
    result: dict[str, dict[str, Any]] = {}
    for index, timestamp in enumerate(times):
        row = {}
        for variable, values in hourly.items():
            if variable == "time" or not isinstance(values, list):
                continue
            row[variable] = values[index] if index < len(values) else None
        result[timestamp] = row
    return result


def point_grid_diagnostics(
    points: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    point_map = {point["point_id"]: point for point in points}
    by_point: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_point[record["point_id"]].append(record)
        by_scenario[record["scenario_id"]].append(record)

    point_results = {}
    for point_id, point in point_map.items():
        selected = by_point.get(point_id, [])
        distances = [
            record["returned_grid"].get("distance_from_requested_point_m")
            for record in selected
            if record["returned_grid"].get("distance_from_requested_point_m") is not None
        ]
        elevation_differences = [
            record["returned_grid"].get("target_minus_returned_elevation_m")
            for record in selected
            if record["returned_grid"].get("target_minus_returned_elevation_m") is not None
        ]
        point_results[point_id] = {
            "name_fa": point.get("name_fa"),
            "coordinate_confidence": point.get("coordinate_confidence"),
            "catalog_elevation_m": point.get("catalog_elevation_m"),
            "dem_elevation_m": point.get("dem_elevation_m"),
            "catalog_minus_dem_m": point.get("catalog_minus_dem_m"),
            "scenario_count": len(selected),
            "max_grid_distance_m": max(distances) if distances else None,
            "max_abs_target_grid_elevation_difference_m": (
                max(abs(value) for value in elevation_differences)
                if elevation_differences
                else None
            ),
            "review_flags": unique(
                (["catalog_dem_difference_ge_150m"]
                 if point.get("catalog_minus_dem_m") is not None
                 and abs(point["catalog_minus_dem_m"]) >= 150
                 else [])
                + (["returned_grid_distance_ge_10km"]
                   if distances and max(distances) >= 10_000
                   else [])
                + (["returned_grid_distance_ge_2km"]
                   if distances and 2_000 <= max(distances) < 10_000
                   else [])
            ),
        }

    scenario_results = {}
    for scenario_id, selected in by_scenario.items():
        grid_groups: dict[str, list[str]] = defaultdict(list)
        distances = []
        for record in selected:
            grid = record["returned_grid"]
            lat = grid.get("latitude")
            lon = grid.get("longitude")
            if lat is not None and lon is not None:
                grid_groups[f"{lat:.6f},{lon:.6f}"].append(record["point_id"])
            if grid.get("distance_from_requested_point_m") is not None:
                distances.append(grid["distance_from_requested_point_m"])
        scenario_results[scenario_id] = {
            "record_count": len(selected),
            "unique_grid_count": len(grid_groups),
            "mean_grid_distance_m": round(statistics.fmean(distances), 1)
            if distances
            else None,
            "max_grid_distance_m": max(distances) if distances else None,
            "shared_grid_cells": {
                grid: point_ids
                for grid, point_ids in grid_groups.items()
                if len(point_ids) > 1
            },
        }
    return {"by_point": point_results, "by_scenario": scenario_results}


def model_spread_diagnostics(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    model_records = [
        record for record in records if record["scenario_id"] in MODEL_SCENARIO_IDS
    ]
    by_point: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in model_records:
        by_point[record["point_id"]].append(record)

    result = {}
    for point_id, selected in by_point.items():
        rows_by_model = {
            record["model_requested"]: hourly_rows(record) for record in selected
        }
        all_times = sorted(
            set().union(*(set(rows) for rows in rows_by_model.values()))
        )
        hourly_spreads = []
        for timestamp in all_times:
            spread_row: dict[str, Any] = {
                "time": timestamp,
                "model_count": sum(timestamp in rows for rows in rows_by_model.values()),
            }
            for variable in MODEL_SPREAD_VARIABLES:
                values = []
                model_values = {}
                for model, rows in rows_by_model.items():
                    value = optional_float(rows.get(timestamp, {}).get(variable))
                    if value is not None:
                        values.append(value)
                        model_values[model] = value
                spread_row[variable] = {
                    "models": model_values,
                    "spread_max_minus_min": round(max(values) - min(values), 3)
                    if len(values) >= 2
                    else None,
                }
            hourly_spreads.append(spread_row)

        summary = {}
        for horizon in (24, 48, 72):
            horizon_rows = hourly_spreads[:horizon]
            variable_summary = {}
            for variable in MODEL_SPREAD_VARIABLES:
                values = [
                    row[variable]["spread_max_minus_min"]
                    for row in horizon_rows
                    if row[variable]["spread_max_minus_min"] is not None
                ]
                variable_summary[variable] = {
                    "mean_spread": round(statistics.fmean(values), 3) if values else None,
                    "max_spread": max(values) if values else None,
                }
            summary[f"first_{horizon}_rows"] = variable_summary
        result[point_id] = {
            "models_received": sorted(rows_by_model),
            "summary": summary,
            "hourly": hourly_spreads,
        }
    return result


def route_weather_diagnostics(
    routes: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    primary = {
        record["point_id"]: hourly_rows(record)
        for record in records
        if record["scenario_id"] == PRIMARY_SCENARIO_ID
    }
    route_results = {}
    for route in routes:
        ordered_point_ids = [
            relation["point_id"]
            for relation in sorted(
                route.get("point_sequence", []), key=lambda item: item["sequence"]
            )
            if relation["point_id"] in primary
        ]
        timestamps = sorted(
            set().union(*(set(primary[point_id]) for point_id in ordered_point_ids))
        ) if ordered_point_ids else []
        hourly = []
        for timestamp in timestamps:
            point_rows = {
                point_id: primary[point_id].get(timestamp, {})
                for point_id in ordered_point_ids
            }

            def values(variable: str) -> dict[str, float]:
                found = {}
                for point_id, row in point_rows.items():
                    value = optional_float(row.get(variable))
                    if value is not None:
                        found[point_id] = value
                return found

            temperatures = values("temperature_2m")
            gusts = values("wind_gusts_10m")
            visibility = values("visibility")
            precipitation = values("precipitation")
            snowfall = values("snowfall")
            freezing = values("freezing_level_height")
            hourly.append(
                {
                    "time": timestamp,
                    "temperature_range_c": (
                        round(max(temperatures.values()) - min(temperatures.values()), 2)
                        if len(temperatures) >= 2
                        else None
                    ),
                    "coldest_point_id": min(temperatures, key=temperatures.get)
                    if temperatures
                    else None,
                    "max_gust_kmh": max(gusts.values()) if gusts else None,
                    "max_gust_point_id": max(gusts, key=gusts.get) if gusts else None,
                    "min_visibility_m": min(visibility.values()) if visibility else None,
                    "min_visibility_point_id": min(visibility, key=visibility.get)
                    if visibility
                    else None,
                    "max_hourly_precipitation_mm": max(precipitation.values())
                    if precipitation
                    else None,
                    "max_hourly_snowfall_cm": max(snowfall.values()) if snowfall else None,
                    "min_freezing_level_m": min(freezing.values()) if freezing else None,
                }
            )
        route_results[route["id"]] = {
            "name_fa": route.get("name_fa"),
            "point_ids": ordered_point_ids,
            "point_count": len(ordered_point_ids),
            "hourly": hourly,
        }
    return route_results


def write_json_atomic(path: Path, payload: dict[str, Any], *, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        handle.write("\n")
    os.replace(temporary, path)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Open-Meteo diagnostics for Hawatch catalog points."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("hawatch_route_points_catalog.json"),
        help="Point/route catalog JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path; default contains a UTC timestamp.",
    )
    parser.add_argument(
        "--route",
        action="append",
        default=[],
        help="Only collect a route id; repeat for multiple routes.",
    )
    parser.add_argument(
        "--point",
        action="append",
        default=[],
        help="Only collect a point id; repeat for multiple points.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Only run a scenario id; repeat for multiple scenarios.",
    )
    parser.add_argument("--forecast-hours", type=int, default=72)
    parser.add_argument("--past-hours", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--request-pause", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include disabled points only if they still have coordinates.",
    )
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate selection and print request plan without network calls.",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.forecast_hours <= 384:
        parser.error("--forecast-hours must be between 1 and 384")
    if not 0 <= args.past_hours <= 92 * 24:
        parser.error("--past-hours is outside the supported range")
    if not 1 <= args.batch_size <= 100:
        parser.error("--batch-size must be between 1 and 100")
    if args.request_pause < 0:
        parser.error("--request-pause cannot be negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    catalog_path = args.catalog.expanduser().resolve()
    try:
        catalog = load_catalog(catalog_path)
        points, routes, skipped = select_catalog_data(
            catalog,
            route_ids=set(args.route),
            point_ids=set(args.point),
            include_disabled=args.include_disabled,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    scenario_map = {scenario.scenario_id: scenario for scenario in SCENARIOS}
    unknown_scenarios = sorted(set(args.scenario) - scenario_map.keys())
    if unknown_scenarios:
        print(
            f"ERROR: unknown scenarios: {', '.join(unknown_scenarios)}",
            file=sys.stderr,
        )
        return 2
    scenarios = (
        [scenario_map[scenario_id] for scenario_id in args.scenario]
        if args.scenario
        else list(SCENARIOS)
    )
    if not points:
        print("ERROR: selection contains no usable points", file=sys.stderr)
        return 2

    forecast_requests = math.ceil(len(points) / args.batch_size) * len(scenarios)
    elevation_requests = math.ceil(len(points) / args.batch_size)
    print(
        f"Selected {len(points)} unique points, {len(routes)} routes, "
        f"{len(scenarios)} scenarios."
    )
    print(
        f"Plan: {elevation_requests} elevation + {forecast_requests} forecast "
        f"HTTP requests; skipped points: {len(skipped)}."
    )
    if args.dry_run:
        for point in points:
            print(
                f"- {point['point_id']}: {point.get('name_fa')} "
                f"({point['latitude']}, {point['longitude']}, "
                f"elevation={point.get('catalog_elevation_m')})"
            )
        return 0

    errors: list[dict[str, Any]] = []
    assign_dem_and_target_elevations(
        points,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout,
        errors=errors,
    )
    records = fetch_forecasts(
        points,
        scenarios,
        batch_size=args.batch_size,
        forecast_hours=args.forecast_hours,
        past_hours=args.past_hours,
        timeout_seconds=args.timeout,
        pause_seconds=args.request_pause,
        errors=errors,
    )

    output_path = args.output
    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = Path(f"hawatch_point_weather_{stamp}.json")
    output_path = output_path.expanduser().resolve()

    diagnostics = {
        "grid_and_elevation": point_grid_diagnostics(points, records),
        "model_spread": model_spread_diagnostics(records),
        "routes": route_weather_diagnostics(routes, records),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "script": {
            "name": Path(__file__).name,
            "version": SCRIPT_VERSION,
            "python": platform.python_version(),
        },
        "run": {
            "completed_at_utc": utc_now(),
            "timezone": TIMEZONE,
            "catalog_path": str(catalog_path),
            "catalog_schema_version": catalog.get("schema_version"),
            "forecast_hours": args.forecast_hours,
            "past_hours": args.past_hours,
            "batch_size": args.batch_size,
            "selected_route_ids": args.route,
            "selected_point_ids": args.point,
            "api_endpoints": {
                "forecast": FORECAST_URL,
                "elevation": ELEVATION_URL,
            },
            "notes": [
                "Every current/hourly value is model-derived, not a station observation.",
                "Catalog elevation is sent when available; otherwise GLO-90 DEM elevation is used.",
                "Returned grid coordinates and elevation are preserved for trust diagnostics.",
                "Raw-grid and nearest-cell scenarios are diagnostics, not the intended public forecast.",
                "No safety score or go/no-go threshold is applied in this probe.",
            ],
        },
        "scenario_definitions": [scenario.__dict__ for scenario in scenarios],
        "variables": {
            "rich_hourly": RICH_HOURLY,
            "core_hourly": CORE_HOURLY,
            "current": CURRENT_VARIABLES,
            "daily": DAILY_VARIABLES,
            "safe_fallback_hourly": SAFE_HOURLY,
            "model_spread": MODEL_SPREAD_VARIABLES,
        },
        "skipped_points": skipped,
        "routes": routes,
        "points": points,
        "forecast_records": records,
        "diagnostics": diagnostics,
        "errors": errors,
    }
    write_json_atomic(output_path, payload, pretty=args.pretty)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {output_path} ({size_mb:.2f} MiB)")
    print(f"Forecast records: {len(records)}; errors: {len(errors)}")
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
