#!/usr/bin/env python3
"""Read-only catalog, DEM and Open-Meteo contract validator.

This script never writes the catalog or the database. It is intentionally
stdlib-only so it can be used before installing the API environment.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAX_PROVIDER_DISTANCE_KM = 5.0
DEFAULT_FORECAST_VARIABLES = "temperature_2m,precipitation,weather_code"


def _request_json(url: str, *, timeout: float) -> dict | list:
    request = Request(url, headers={"User-Agent": "hawatch-catalog-validator/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _endpoint(base: str, path: str) -> str:
    clean = base.strip().rstrip("/")
    if clean.endswith(path):
        return clean
    return f"{clean}{path}"


def _distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius = 6371.0088
    lat1, lat2 = math.radians(lat_a), math.radians(lat_b)
    d_lat = lat2 - lat1
    d_lon = math.radians(lon_b - lon_a)
    value = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(value))


def _items(payload: dict | list, expected: int) -> list[dict]:
    values = payload if isinstance(payload, list) else [payload]
    if len(values) != expected or not all(isinstance(item, dict) for item in values):
        return []
    return values


def _catalog_checks(catalog: dict) -> tuple[list[str], list[str], list[dict]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(catalog.get("catalog_version"), str) or not catalog["catalog_version"].strip():
        errors.append("catalog_version must be a non-empty string")
    destination = catalog.get("destination")
    if not isinstance(destination, dict):
        errors.append("destination must be an object")
    else:
        for key in ("slug", "tile_name", "name", "short_category", "category", "category_key", "region", "image", "image_alt", "climate"):
            if not destination.get(key):
                errors.append(f"destination.{key} is required")
        try:
            latitude = float(destination["latitude"])
            longitude = float(destination["longitude"])
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors.append("destination latitude/longitude must be valid WGS84 coordinates")
    raw_points = catalog.get("weather_points")
    if not isinstance(raw_points, dict) or not raw_points:
        return ["weather_points must be a non-empty object"], warnings, []

    points: list[dict] = []
    seen_coordinates: dict[tuple[float, float], str] = {}
    for slug, row in raw_points.items():
        if not isinstance(row, dict):
            errors.append(f"{slug}: point must be an object")
            continue
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{slug}: latitude/longitude are required decimal numbers")
            continue
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            errors.append(f"{slug}: coordinates are outside WGS84 bounds")
        key = (round(latitude, 7), round(longitude, 7))
        previous = seen_coordinates.get(key)
        if previous:
            errors.append(f"{slug}: duplicate coordinates with {previous}")
        seen_coordinates[key] = slug
        elevation = row.get("elevation_m")
        if elevation is not None:
            try:
                if int(elevation) != elevation or int(elevation) < 0:
                    raise ValueError
                elevation = int(elevation)
            except (TypeError, ValueError):
                errors.append(f"{slug}: elevation_m must be a non-negative integer or null")
                elevation = None
        elif not row.get("elevation_source"):
            warnings.append(f"{slug}: catalog elevation is unresolved")
        points.append(
            {
                "slug": slug,
                "name": row.get("name", slug),
                "latitude": latitude,
                "longitude": longitude,
                "catalog_elevation_m": elevation,
                "status": row.get("status", "approved" if elevation is not None else "unresolved_elevation"),
            }
        )

    routes = catalog.get("routes")
    if not isinstance(routes, dict) or not routes:
        errors.append("routes must be a non-empty object")
    else:
        point_slugs = set(raw_points)
        for route_slug, route in routes.items():
            route_points = route.get("points") if isinstance(route, dict) else None
            if not route_points:
                errors.append(f"{route_slug}: route points are required")
                continue
            for point_slug in route_points:
                if point_slug not in point_slugs:
                    errors.append(f"{route_slug}: references missing point {point_slug}")
    return errors, warnings, points


def _query_elevation(points: list[dict], *, endpoint: str, timeout: float) -> list[dict]:
    params = {
        "latitude": ",".join(str(point["latitude"]) for point in points),
        "longitude": ",".join(str(point["longitude"]) for point in points),
    }
    payload = _request_json(f"{endpoint}?{urlencode(params)}", timeout=timeout)
    elevations = payload.get("elevation") if isinstance(payload, dict) else None
    if not isinstance(elevations, list) or len(elevations) != len(points):
        raise ValueError("elevation response cardinality does not match catalog")
    return [{**point, "dem_elevation_m": value} for point, value in zip(points, elevations, strict=True)]


def _query_forecast(points: list[dict], *, endpoint: str, forecast_days: int, timeout: float) -> list[dict]:
    known = [point for point in points if point["catalog_elevation_m"] is not None]
    unknown = [point for point in points if point["catalog_elevation_m"] is None]
    all_results: list[dict] = []
    known_land = [point for point in known if point["status"] != "provisional"]
    known_nearest = [point for point in known if point["status"] == "provisional"]
    for group, selection, include_elevation in (
        (known_land, "land", True),
        (known_nearest, "nearest", True),
        (unknown, "nearest", False),
    ):
        if not group:
            continue
        params = {
            "latitude": ",".join(f"{point['latitude']:.7f}" for point in group),
            "longitude": ",".join(f"{point['longitude']:.7f}" for point in group),
            "timezone": "Asia/Tehran",
            "models": "best_match",
            "cell_selection": selection,
            "forecast_days": str(forecast_days),
            "past_days": "0",
            "hourly": DEFAULT_FORECAST_VARIABLES,
        }
        elevations = [point["catalog_elevation_m"] for point in group]
        if include_elevation:
            params["elevation"] = ",".join(str(value) for value in elevations)
        payload = _request_json(f"{endpoint}?{urlencode(params)}", timeout=timeout)
        for point, response in zip(group, _items(payload, len(group)), strict=True):
            resolved_lat = response.get("latitude")
            resolved_lon = response.get("longitude")
            distance = None
            if isinstance(resolved_lat, (int, float)) and isinstance(resolved_lon, (int, float)):
                distance = _distance_km(point["latitude"], point["longitude"], resolved_lat, resolved_lon)
            hourly = response.get("hourly")
            all_results.append(
                {
                    **point,
                    "cell_selection": selection,
                    "provider_latitude": resolved_lat,
                    "provider_longitude": resolved_lon,
                    "provider_elevation_m": response.get("elevation"),
                    "provider_distance_km": round(distance, 3) if distance is not None else None,
                    "hour_count": len(hourly.get("time", [])) if isinstance(hourly, dict) else 0,
                }
            )
    return all_results


def validate_catalog(
    catalog_path: Path,
    *,
    forecast_url: str = "https://api.open-meteo.com",
    elevation_url: str = "https://api.open-meteo.com",
    forecast_days: int = 1,
    timeout: float = 30.0,
    allow_unresolved_elevation: bool = False,
) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    errors, warnings, points = _catalog_checks(catalog)
    report = {
        "catalog": str(catalog_path),
        "catalog_version": catalog.get("catalog_version"),
        "errors": errors,
        "warnings": warnings,
        "points": [],
    }
    if errors:
        return report
    try:
        enriched: list[dict] = []
        for index in range(0, len(points), 100):
            enriched.extend(
                _query_elevation(
                    points[index : index + 100],
                    endpoint=_endpoint(elevation_url, "/v1/elevation"),
                    timeout=timeout,
                )
            )
        forecasts = _query_forecast(
            enriched,
            endpoint=_endpoint(forecast_url, "/v1/forecast"),
            forecast_days=forecast_days,
            timeout=timeout,
        )
    except Exception as exc:  # network/provider errors are validation failures, not guesses
        report["errors"].append(f"provider validation failed: {type(exc).__name__}: {exc}")
        return report

    by_slug = {point["slug"]: point for point in forecasts}
    for point in enriched:
        result = by_slug.get(point["slug"], {**point, "provider_distance_km": None, "hour_count": 0})
        catalog_elevation = point["catalog_elevation_m"]
        dem_elevation = point["dem_elevation_m"]
        delta = None
        if catalog_elevation is not None and isinstance(dem_elevation, (int, float)):
            delta = catalog_elevation - dem_elevation
        result["dem_delta_m"] = delta
        result["elevation_status"] = "catalog" if catalog_elevation is not None else "needs_catalog_enrichment"
        report["points"].append(result)
        if catalog_elevation is None:
            report["warnings"].append(f"{point['slug']}: no catalog elevation; DEM is validation evidence only")
        elif delta is not None and abs(delta) > 100:
            report["warnings"].append(f"{point['slug']}: catalog/DEM elevation delta is {delta:g} m")
        distance = result.get("provider_distance_km")
        if distance is None or distance > MAX_PROVIDER_DISTANCE_KM:
            report["errors"].append(
                f"{point['slug']}: provider grid resolution distance {distance!r} km exceeds {MAX_PROVIDER_DISTANCE_KM} km"
            )
        if not isinstance(result.get("provider_elevation_m"), (int, float)):
            report["errors"].append(f"{point['slug']}: provider returned no elevation metadata")
        if result.get("hour_count", 0) <= 0:
            report["errors"].append(f"{point['slug']}: provider returned no hourly data")
    unresolved = [point["slug"] for point in report["points"] if point["catalog_elevation_m"] is None]
    if unresolved and not allow_unresolved_elevation:
        report["errors"].append(
            "catalog elevation unresolved for: "
            + ", ".join(unresolved)
            + "; provide a trusted elevation or run with --allow-unresolved-elevation for coordinate-only checks"
        )
    report["summary"] = {
        "point_count": len(points),
        "provider_checked": len(report["points"]),
        "unresolved_elevation_count": len(unresolved),
        "error_count": len(report["errors"]),
        "warning_count": len(report["warnings"]),
        "pass": not report["errors"],
    }
    return report


def _print_report(report: dict) -> None:
    summary = report.get("summary", {})
    print(
        "catalog={catalog_version} points={point_count} provider_checked={provider_checked} "
        "errors={error_count} warnings={warning_count} pass={pass}".format(
            catalog_version=report.get("catalog_version"), **summary
        )
    )
    for point in report.get("points", []):
        print(
            "{slug}: catalog={catalog_elevation_m!r} dem90={dem_elevation_m!r} "
            "delta={dem_delta_m!r} cell={cell_selection} grid_distance_km={provider_distance_km!r}".format(
                **point
            )
        )
    for label, entries in (("ERROR", report.get("errors", [])), ("WARNING", report.get("warnings", []))):
        for entry in entries:
            print(f"{label}: {entry}")


def main(argv: list[str] | None = None) -> int:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=repo / "apps/api/fixtures/catalog/tochal_v1.json",
        help="Catalog JSON path (default: Tochal catalog).",
    )
    parser.add_argument("--forecast-url", default="https://api.open-meteo.com")
    parser.add_argument("--elevation-url", default="https://api.open-meteo.com")
    parser.add_argument("--forecast-days", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--allow-unresolved-elevation",
        action="store_true",
        help="Run coordinate/provider checks without requiring catalog elevation for every point.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print the full JSON report.")
    args = parser.parse_args(argv)
    try:
        report = validate_catalog(
            args.catalog,
            forecast_url=args.forecast_url,
            elevation_url=args.elevation_url,
            forecast_days=args.forecast_days,
            timeout=args.timeout,
            allow_unresolved_elevation=args.allow_unresolved_elevation,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0 if report.get("summary", {}).get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
