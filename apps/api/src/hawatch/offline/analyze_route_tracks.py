#!/usr/bin/env python3
"""Offline, read-only GPX analyzer for Hawatch Tochal route evidence.

Stdlib only. Never mutates catalog JSON or any database.

Algorithm (deterministic):
1. Parse GPX 1.1 track points (lat/lon/ele/time).
2. Cut ascent at the first track point whose Haversine distance to the canonical
   Tochal summit is within 1 m of the track-wide minimum distance (first closest
   approach). Round-trip files are outbound-only until first summit arrival.
3. Distance: sum of Haversine segments (Earth radius 6_371_000 m).
4. Timestamp quality comes from the manifest (`timestamp_quality`).
   When quality is not `recorded`, recorded_elapsed_minutes and
   moving_minutes_estimate are null with an explicit diagnostic.
5. Moving-time estimate (recorded only): sum segment durations except pauses,
   where a pause is dt >= 45 s AND displacement <= 10 m.
6. Robust smoothed ascent (GPX ele reference-only):
   - resample elevations every 50 m along-track
   - centered 5-sample moving average
   - sum positive deltas
   Also report net elevation change (last - first resampled elevation).
7. For each catalog RoutePoint, report nearest ordered cut track point.

Example:
  python3 scripts/analyze_route_tracks.py \\
    --manifest tracks/tochal/manifest.json \\
    --catalog apps/api/fixtures/catalog/tochal_v1.json
"""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}
EARTH_RADIUS_M = 6_371_000.0
PAUSE_GAP_SECONDS = 45.0
PAUSE_MAX_DISPLACEMENT_M = 10.0
SUMMIT_CLOSEST_TOLERANCE_M = 1.0
ASCENT_RESAMPLE_M = 50.0
ASCENT_SMOOTH_WINDOW = 5
TIMESTAMP_RECORDED = "recorded"


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def parse_gpx_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    if "." in text:
        head, rest = text.split(".", 1)
        digits = ""
        tz = ""
        for index, char in enumerate(rest):
            if char.isdigit():
                digits += char
            else:
                tz = rest[index:]
                break
        text = f"{head}.{digits[:6]}{tz}"
    when = datetime.fromisoformat(text)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def parse_gpx_track(path: Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    points: list[dict[str, Any]] = []
    for node in root.findall(".//gpx:trkpt", GPX_NS):
        ele_text = node.findtext("gpx:ele", default=None, namespaces=GPX_NS)
        time_text = node.findtext("gpx:time", default=None, namespaces=GPX_NS)
        points.append(
            {
                "lat": float(node.attrib["lat"]),
                "lon": float(node.attrib["lon"]),
                "ele": float(ele_text) if ele_text is not None else None,
                "time": parse_gpx_time(time_text),
            }
        )
    if not points:
        raise ValueError(f"No track points in {path}")
    return points


def cut_at_first_summit_approach(
    points: list[dict[str, Any]], summit: tuple[float, float]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    distances = [haversine_m((p["lat"], p["lon"]), summit) for p in points]
    min_distance = min(distances)
    cut_index = next(
        (
            index
            for index, distance in enumerate(distances)
            if distance <= min_distance + SUMMIT_CLOSEST_TOLERANCE_M
        ),
        distances.index(min_distance),
    )
    cut = points[: cut_index + 1]
    meta = {
        "cut_index": cut_index,
        "min_summit_distance_m": round(min_distance, 3),
        "cut_summit_distance_m": round(distances[cut_index], 3),
        "rule": (
            "first track point within "
            f"{SUMMIT_CLOSEST_TOLERANCE_M} m of the track-wide minimum summit distance"
        ),
    }
    return cut, meta


def along_track_distances_m(points: list[dict[str, Any]]) -> list[float]:
    along = [0.0]
    for previous, current in zip(points, points[1:]):
        along.append(
            along[-1]
            + haversine_m((previous["lat"], previous["lon"]), (current["lat"], current["lon"]))
        )
    return along


def total_distance_km(points: list[dict[str, Any]]) -> float:
    return along_track_distances_m(points)[-1] / 1000.0 if points else 0.0


def recorded_elapsed_minutes(points: list[dict[str, Any]]) -> float | None:
    if not points or points[0]["time"] is None or points[-1]["time"] is None:
        return None
    return (points[-1]["time"] - points[0]["time"]).total_seconds() / 60.0


def moving_minutes(points: list[dict[str, Any]]) -> float | None:
    """Moving-time estimate with explicit pause filter (recorded timestamps only)."""
    if not points or points[0]["time"] is None:
        return None
    total = 0.0
    saw_time = False
    for previous, current in zip(points, points[1:]):
        if previous["time"] is None or current["time"] is None:
            continue
        saw_time = True
        dt = (current["time"] - previous["time"]).total_seconds()
        if dt <= 0:
            continue
        displacement = haversine_m(
            (previous["lat"], previous["lon"]), (current["lat"], current["lon"])
        )
        if dt >= PAUSE_GAP_SECONDS and displacement <= PAUSE_MAX_DISPLACEMENT_M:
            continue
        total += dt
    return total / 60.0 if saw_time else None


def resample_elevations_by_distance(
    points: list[dict[str, Any]], step_m: float = ASCENT_RESAMPLE_M
) -> list[float]:
    """Linearly interpolate elevation every step_m along track where ele is present."""
    samples: list[tuple[float, float]] = []
    along = 0.0
    previous = None
    for point in points:
        if previous is not None:
            along += haversine_m((previous["lat"], previous["lon"]), (point["lat"], point["lon"]))
        if point["ele"] is not None:
            samples.append((along, point["ele"]))
        previous = point
    if len(samples) < 2:
        return [ele for _, ele in samples]
    end = samples[-1][0]
    if end <= 0:
        return [samples[0][1]]
    resampled: list[float] = []
    cursor = 0
    distance = 0.0
    while distance <= end + 1e-9:
        while cursor + 1 < len(samples) and samples[cursor + 1][0] < distance:
            cursor += 1
        if cursor + 1 >= len(samples):
            resampled.append(samples[-1][1])
            break
        d0, e0 = samples[cursor]
        d1, e1 = samples[cursor + 1]
        if d1 <= d0:
            resampled.append(e1)
        else:
            t = (distance - d0) / (d1 - d0)
            resampled.append(e0 + t * (e1 - e0))
        distance += step_m
    return resampled


def moving_average(values: list[float], window: int = ASCENT_SMOOTH_WINDOW) -> list[float]:
    if not values:
        return []
    half = window // 2
    smoothed: list[float] = []
    for index in range(len(values)):
        lo = max(0, index - half)
        hi = min(len(values), index + half + 1)
        chunk = values[lo:hi]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed


def robust_smoothed_ascent_m(points: list[dict[str, Any]]) -> dict[str, float | None]:
    """Resample 50 m → centered 5-sample MA → sum positive deltas. GPX ele reference-only."""
    resampled = resample_elevations_by_distance(points)
    if len(resampled) < 2:
        return {
            "robust_smoothed_ascent_m": None,
            "net_elevation_change_m": None,
            "resample_count": float(len(resampled)),
        }
    smoothed = moving_average(resampled, ASCENT_SMOOTH_WINDOW)
    gain = 0.0
    for previous, current in zip(smoothed, smoothed[1:]):
        delta = current - previous
        if delta > 0:
            gain += delta
    return {
        "robust_smoothed_ascent_m": round(gain, 1),
        "net_elevation_change_m": round(smoothed[-1] - smoothed[0], 1),
        "resample_count": float(len(resampled)),
    }


def minutes_to_index(points: list[dict[str, Any]], index: int, *, moving: bool) -> float | None:
    subset = points[: index + 1]
    return moving_minutes(subset) if moving else recorded_elapsed_minutes(subset)


def nearest_track_index(points: list[dict[str, Any]], lat: float, lon: float) -> tuple[int, float]:
    best_index = 0
    best_distance = float("inf")
    for index, point in enumerate(points):
        distance = haversine_m((point["lat"], point["lon"]), (lat, lon))
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index, best_distance


def analyze_track(
    *,
    gpx_path: Path,
    summit: tuple[float, float],
    route_points: list[dict[str, Any]] | None,
    track_meta: dict[str, Any],
) -> dict[str, Any]:
    raw = parse_gpx_track(gpx_path)
    cut, cut_meta = cut_at_first_summit_approach(raw, summit)
    along = along_track_distances_m(cut)
    timestamp_quality = str(track_meta.get("timestamp_quality") or TIMESTAMP_RECORDED)
    timestamps_usable = timestamp_quality == TIMESTAMP_RECORDED
    time_diagnostic = None
    if not timestamps_usable:
        time_diagnostic = (
            f"timestamp_quality={timestamp_quality}; "
            "recorded_elapsed_minutes and moving_minutes_estimate are null because "
            "timestamps are not treated as recorded moving time"
        )

    comparisons = []
    if route_points:
        for route_point in route_points:
            index, distance = nearest_track_index(cut, route_point["latitude"], route_point["longitude"])
            track_point = cut[index]
            elapsed_to = minutes_to_index(cut, index, moving=False) if timestamps_usable else None
            moving_to = minutes_to_index(cut, index, moving=True) if timestamps_usable else None
            comparisons.append(
                {
                    "slug": route_point["slug"],
                    "nearest_index": index,
                    "nearest_distance_m": round(distance, 2),
                    "along_track_distance_m": round(along[index], 2),
                    "track_elevation_m": track_point["ele"],
                    "elapsed_minutes": None if elapsed_to is None else round(elapsed_to, 2),
                    "moving_minutes": None if moving_to is None else round(moving_to, 2),
                }
            )

    distance_km = total_distance_km(cut)
    elapsed = recorded_elapsed_minutes(cut) if timestamps_usable else None
    moving = moving_minutes(cut) if timestamps_usable else None
    ascent = robust_smoothed_ascent_m(cut)
    return {
        "filename": gpx_path.name,
        "route_slug": track_meta.get("route_slug"),
        "wikiloc_url": track_meta.get("wikiloc_url"),
        "author": track_meta.get("author"),
        "coverage": track_meta.get("coverage"),
        "timestamp_quality": timestamp_quality,
        "timestamp_time_diagnostic": time_diagnostic,
        "license_status": track_meta.get("license_status", "unverified"),
        "catalog_applied": track_meta.get("catalog_applied"),
        "point_count_raw": len(raw),
        "point_count_cut": len(cut),
        "cut": cut_meta,
        "distance_km": round(distance_km, 2),
        "recorded_elapsed_minutes": None if elapsed is None else round(elapsed, 2),
        "moving_minutes_estimate": None if moving is None else round(moving, 2),
        "robust_smoothed_ascent_m": ascent["robust_smoothed_ascent_m"],
        "net_elevation_change_m": ascent["net_elevation_change_m"],
        "gpx_elevation_reference_only": True,
        "methods": {
            "distance": f"haversine R={EARTH_RADIUS_M}",
            "moving_pause_rule": (
                f"exclude segment when dt>={PAUSE_GAP_SECONDS}s and "
                f"displacement<={PAUSE_MAX_DISPLACEMENT_M}m; only when timestamp_quality=recorded"
            ),
            "ascent": (
                f"resample every {ASCENT_RESAMPLE_M} m, centered {ASCENT_SMOOTH_WINDOW}-sample "
                "moving average, sum positive deltas; GPX ele reference-only"
            ),
        },
        "route_point_comparisons": comparisons,
    }


def load_route_points(catalog: dict[str, Any], route_slug: str) -> list[dict[str, Any]]:
    weather_points = catalog.get("weather_points") or {}
    for route in (catalog.get("routes") or {}).values():
        if route.get("slug") != route_slug:
            continue
        rows = []
        for slug in route.get("points") or []:
            point = weather_points.get(slug)
            if not point:
                continue
            rows.append(
                {
                    "slug": slug,
                    "latitude": float(point["latitude"]),
                    "longitude": float(point["longitude"]),
                }
            )
        return rows
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="tracks/tochal/manifest.json")
    parser.add_argument("--catalog", default="apps/api/fixtures/catalog/tochal_v1.json")
    parser.add_argument("--tracks-dir", default=None)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    tracks_dir = Path(args.tracks_dir) if args.tracks_dir else manifest_path.parent
    catalog_path = Path(args.catalog)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else {}

    summit = (
        float(manifest.get("summit_latitude", 35.8843493)),
        float(manifest.get("summit_longitude", 51.4198766)),
    )
    reports = []
    for track in manifest.get("tracks") or []:
        filename = track["filename"]
        gpx_path = tracks_dir / filename
        if not gpx_path.is_file():
            reports.append({"filename": filename, "error": "missing_gpx"})
            continue
        route_slug = track.get("route_slug") or ""
        route_points = load_route_points(catalog, route_slug) if catalog else []
        reports.append(
            analyze_track(
                gpx_path=gpx_path,
                summit=summit,
                route_points=route_points,
                track_meta=track,
            )
        )

    payload = {
        "analyzer": "hawatch-analyze-route-tracks-v2",
        "read_only": True,
        "manifest": str(manifest_path),
        "catalog": str(catalog_path) if catalog else None,
        "summit": {"latitude": summit[0], "longitude": summit[1]},
        "tracks": reports,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
