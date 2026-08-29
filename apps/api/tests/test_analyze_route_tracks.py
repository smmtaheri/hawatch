"""Unit tests for offline GPX analyzer (synthetic fixtures; no tracks/ dependency)."""

from __future__ import annotations

import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hawatch.offline import analyze_route_tracks as analyzer


def _write_gpx(points: list[tuple[float, float, float | None, str | None]]) -> Path:
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>',
    ]
    for lat, lon, ele, when in points:
        attrs = f'lat="{lat}" lon="{lon}"'
        body = ""
        if ele is not None:
            body += f"<ele>{ele}</ele>"
        if when is not None:
            body += f"<time>{when}</time>"
        rows.append(f"<trkpt {attrs}>{body}</trkpt>")
    rows.append("</trkseg></trk></gpx>")
    handle = tempfile.NamedTemporaryFile("w", suffix=".gpx", delete=False, encoding="utf-8")
    handle.write("\n".join(rows))
    handle.close()
    return Path(handle.name)


def test_recorded_timestamps_produce_elapsed_and_moving():
    start = datetime(2024, 6, 1, 6, 0, tzinfo=timezone.utc)
    points = []
    for index in range(6):
        when = (start + timedelta(seconds=60 * index)).isoformat().replace("+00:00", "Z")
        points.append((35.88 + index * 0.001, 51.42, 3000 + index * 10, when))
    path = _write_gpx(points)
    result = analyzer.analyze_track(
        gpx_path=path,
        summit=(35.885, 51.42),
        route_points=None,
        track_meta={"timestamp_quality": "recorded", "route_slug": "demo"},
    )
    assert result["timestamp_quality"] == "recorded"
    assert result["recorded_elapsed_minutes"] == pytest.approx(5.0, abs=0.1)
    assert result["moving_minutes_estimate"] is not None
    assert result["moving_minutes_estimate"] > 0
    assert result["timestamp_time_diagnostic"] is None
    path.unlink(missing_ok=True)


def test_synthetic_timestamps_null_out_time_metrics():
    start = datetime(2024, 6, 1, 6, 0, tzinfo=timezone.utc)
    points = []
    for index in range(6):
        when = (start + timedelta(seconds=40 * index)).isoformat().replace("+00:00", "Z")
        points.append((35.88 + index * 0.001, 51.42, 3000 + index * 20, when))
    path = _write_gpx(points)
    result = analyzer.analyze_track(
        gpx_path=path,
        summit=(35.885, 51.42),
        route_points=None,
        track_meta={"timestamp_quality": "synthetic_unusable", "route_slug": "kalkchal"},
    )
    assert result["timestamp_quality"] == "synthetic_unusable"
    assert result["recorded_elapsed_minutes"] is None
    assert result["moving_minutes_estimate"] is None
    assert result["timestamp_time_diagnostic"]
    assert "synthetic_unusable" in result["timestamp_time_diagnostic"]
    assert result["distance_km"] is not None and result["distance_km"] > 0
    path.unlink(missing_ok=True)


def test_distance_and_summit_cut():
    points = [
        (35.880, 51.420, 3000, None),
        (35.882, 51.420, 3100, None),
        (35.884, 51.420, 3200, None),
        (35.886, 51.420, 3150, None),
        (35.888, 51.420, 3100, None),
    ]
    path = _write_gpx(points)
    result = analyzer.analyze_track(
        gpx_path=path,
        summit=(35.884, 51.420),
        route_points=None,
        track_meta={"timestamp_quality": "recorded"},
    )
    assert result["cut"]["cut_index"] == 2
    assert result["point_count_cut"] == 3
    assert result["point_count_raw"] == 5
    assert result["distance_km"] == pytest.approx(
        analyzer.haversine_m((35.880, 51.420), (35.882, 51.420)) / 1000.0
        + analyzer.haversine_m((35.882, 51.420), (35.884, 51.420)) / 1000.0,
        abs=0.01,
    )
    path.unlink(missing_ok=True)


def test_ascent_smoothing_reduces_gps_noise():
    points = []
    base = 3000.0
    for index in range(20):
        lat = 35.88 + index * 0.000225
        ele = base + (50 if index % 2 == 0 else -40) + index * 5
        points.append((lat, 51.42, ele, None))
    path = _write_gpx(points)
    cut = analyzer.parse_gpx_track(path)
    robust = analyzer.robust_smoothed_ascent_m(cut)
    raw_gain = 0.0
    for previous, current in zip(cut, cut[1:]):
        if previous["ele"] is not None and current["ele"] is not None:
            delta = current["ele"] - previous["ele"]
            if delta > 0:
                raw_gain += delta
    assert robust["robust_smoothed_ascent_m"] is not None
    assert robust["net_elevation_change_m"] is not None
    assert robust["robust_smoothed_ascent_m"] < raw_gain
    assert math.isfinite(robust["robust_smoothed_ascent_m"])
    path.unlink(missing_ok=True)
