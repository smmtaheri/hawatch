#!/usr/bin/env python3
"""Build a reviewed fixture for missing route descent and waypoint distances.

Input is a read-only JSON snapshot of live routes with canonical RoutePoints.
No GPX is parsed and no database is written. Estimates are explicitly marked.
"""

import argparse
import json
import math
import re
from pathlib import Path


DESCENT_CALIBRATION = {
    "snapshot": "production-2026-10-12",
    "reference_routes": 157,
    "method": "max(0, ascent_m - (target_elevation_m - origin_elevation_m), checkpoint_drop_floor_m)",
    "mae_m": 28.2,
    "median_absolute_error_m": 16,
    "p90_absolute_error_m": 74,
    "within_100m": 148,
}

DISTANCE_CALIBRATION = {
    "snapshot": "production-2026-10-12",
    "reference_segments": 442,
    "method": "route_distance_scaled_by_geodesic_chord_between_ordered_route_points",
    "mae_m": 278,
    "median_absolute_error_m": 180,
    "p90_absolute_error_m": 560,
    "median_relative_error": 0.087,
}


def haversine_m(first, second):
    lat1, lon1 = map(math.radians, (first["latitude"], first["longitude"]))
    lat2, lon2 = map(math.radians, (second["latitude"], second["longitude"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6_371_000 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def estimate_descent(route):
    points = route["points"]
    elevations = [point["elevation_m"] for point in points]
    if route["ascent_m"] is None or any(value is None for value in elevations):
        raise ValueError(f"{route['slug']}: ascent and point elevations are required")

    net_rise = elevations[-1] - elevations[0]
    formula_value = route["ascent_m"] - net_rise
    checkpoint_drop_floor = sum(
        max(0, first - second) for first, second in zip(elevations, elevations[1:])
    )
    estimated = max(0, formula_value, checkpoint_drop_floor)
    conflict = formula_value < max(0, checkpoint_drop_floor)
    return estimated, {
        "method": "ascent-minus-net-elevation-with-checkpoint-lower-bound-v1",
        "formula": DESCENT_CALIBRATION["method"],
        "ascent_m": route["ascent_m"],
        "origin_elevation_m": elevations[0],
        "target_elevation_m": elevations[-1],
        "net_rise_m": net_rise,
        "unclamped_formula_m": formula_value,
        "checkpoint_drop_lower_bound_m": checkpoint_drop_floor,
        "confidence": "low" if conflict else "medium",
        "uncertainty_m": max(150, checkpoint_drop_floor - formula_value)
        if conflict
        else DESCENT_CALIBRATION["p90_absolute_error_m"],
        "lower_bound_estimate": conflict,
        "calibration": DESCENT_CALIBRATION,
        "route_source_urls": route.get("timing_source_urls", []),
    }


def estimate_segment_distances(route):
    points = route["points"]
    route_distance_m = round(route["distance_km"] * 1000)
    if len(points) < 2 or route_distance_m <= 0:
        raise ValueError(f"{route['slug']}: route length and at least two points required")
    if any(point["latitude"] is None or point["longitude"] is None for point in points):
        raise ValueError(f"{route['slug']}: canonical coordinates are required")

    existing = [point["segment_distance_m"] for point in points]
    existing[0] = 0  # Distance to the route origin is exact, not estimated.
    fixed_total = sum(value for value in existing[1:] if value is not None)
    missing = [index for index in range(1, len(points)) if existing[index] is None]
    remaining_m = route_distance_m - fixed_total
    if remaining_m < 0 or (missing and remaining_m < len(missing)):
        raise ValueError(f"{route['slug']}: curated segment values exceed route length")

    chords = [haversine_m(points[index - 1], points[index]) for index in range(1, len(points))]
    weights = [chords[index - 1] for index in missing]
    if missing and sum(weights) <= 0:
        raise ValueError(f"{route['slug']}: missing segment has no usable chord length")

    values = list(existing)
    if missing:
        allocated = [round(remaining_m * weight / sum(weights)) for weight in weights]
        allocated[-1] += remaining_m - sum(allocated)
        for index, value in zip(missing, allocated):
            if value <= 0:
                raise ValueError(f"{route['slug']}: estimated segment is not positive")
            values[index] = value

    if sum(values[1:]) != route_distance_m:
        raise ValueError(f"{route['slug']}: segment profile does not match route distance")
    return values, {
        "method": "chord-proportional-estimate-v1",
        "confidence": "low",
        "route_distance_m": route_distance_m,
        "estimated_point_slugs": [points[index]["slug"] for index in missing],
        "chord_distances_m": [round(value) for value in chords],
        "formula": DISTANCE_CALIBRATION["method"],
        "calibration": DISTANCE_CALIBRATION,
    }


def build_fixture(snapshot, fixture):
    document = json.loads(fixture.read_text())
    # The old report diagnostics are stale and can contain machine-local GPX paths.
    document.pop("diagnostics", None)
    routes_by_slug = {route["slug"]: route for route in document["routes"]}
    new_estimates = []
    errors = []
    for route in snapshot:
        has_missing_distance = any(
            point["segment_distance_m"] is None for point in route["points"]
        )
        missing_descent = route["descent_m"] is None
        if not has_missing_distance and not missing_descent:
            continue

        item = {
            "slug": route["slug"],
            "chain": [point["slug"] for point in route["points"]],
        }
        try:
            if missing_descent:
                item["descent_m"], item["evidence"] = estimate_descent(route)
            if has_missing_distance:
                (
                    item["segment_distance_m"],
                    item["segment_distance_evidence"],
                ) = estimate_segment_distances(route)
        except ValueError as error:
            errors.append({"slug": route["slug"], "reason": str(error)})
            continue

        existing_item = routes_by_slug.get(route["slug"])
        if existing_item:
            # Existing GPX profiles remain the source of truth; only add missing data.
            if "descent_m" in item:
                existing_item["descent_m"] = item["descent_m"]
                existing_item["evidence"] = item["evidence"]
            if "segment_distance_m" in item:
                existing_item["segment_distance_m"] = item["segment_distance_m"]
                existing_item["segment_distance_evidence"] = item[
                    "segment_distance_evidence"
                ]
        else:
            document["routes"].append(item)
            routes_by_slug[route["slug"]] = item
        new_estimates.append(item)

    document["schema_version"] = "route-metrics-2"
    estimated_descent_slugs = {
        item["slug"] for item in new_estimates if "descent_m" in item
    }
    unresolved_descent = sorted(
        route["slug"]
        for route in snapshot
        if route["descent_m"] is None
        and route["slug"] not in estimated_descent_slugs
    )
    document["unresolved"] = unresolved_descent
    document["estimate_summary"] = {
        "descent_estimates": sum("descent_m" in item for item in new_estimates),
        "segment_distance_profiles": sum(
            "segment_distance_m" in item for item in new_estimates
        ),
        "low_confidence_descent_slugs": [
            item["slug"]
            for item in new_estimates
            if item.get("evidence", {}).get("confidence") == "low"
        ],
        "generation_method": "scripts/estimate-missing-route-metrics.py",
        "calibration": {
            "descent": DESCENT_CALIBRATION,
            "segment_distance": DISTANCE_CALIBRATION,
        },
    }
    return document, new_estimates, errors


def render_preserving_existing_routes(original_text, document):
    """Keep checked-in GPX evidence byte-for-byte where it did not change."""
    match = re.search(r'"routes"\s*:\s*\[', original_text)
    if not match:
        raise ValueError("fixture has no routes array")

    decoder = json.JSONDecoder()
    position = match.end()
    original_items = {}
    while True:
        while position < len(original_text) and original_text[position] in " \t\r\n,":
            position += 1
        if position >= len(original_text) or original_text[position] == "]":
            array_end = position
            break
        item, end = decoder.raw_decode(original_text, position)
        original_items[item["slug"]] = original_text[position:end]
        position = end

    rendered_items = []
    for item in document["routes"]:
        old_raw = original_items.get(item["slug"])
        old_item = decoder.decode(old_raw) if old_raw else None
        if old_item == item:
            rendered = "    " + old_raw
        else:
            rendered = json.dumps(item, ensure_ascii=False, indent=2)
            rendered = "\n".join(
                "    " + line for line in rendered.splitlines()
            )
        rendered_items.append(rendered)

    prefix = original_text[: match.end()]
    prefix = re.sub(
        r'("schema_version"\s*:\s*)"[^"]+"',
        r'\1"route-metrics-2"',
        prefix,
        count=1,
    )
    summary = json.dumps(document["estimate_summary"], ensure_ascii=False, indent=2)
    summary = summary.replace("\n", "\n  ")
    suffix = (
        "\n  ],\n  \"unresolved\": "
        + json.dumps(document["unresolved"], ensure_ascii=False)
        + ",\n  \"estimate_summary\": "
        + summary
        + "\n}\n"
    )
    return prefix + "\n" + ",\n".join(rendered_items) + suffix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("apps/api/fixtures/route_descent_v1.json"),
    )
    parser.add_argument("--output", type=Path, help="Write the generated fixture here")
    parser.add_argument("--report", action="store_true", help="Print a compact audit")
    args = parser.parse_args()
    document, estimates, errors = build_fixture(
        json.loads(args.snapshot.read_text()), args.fixture
    )
    rendered = render_preserving_existing_routes(
        args.fixture.read_text(), document
    )
    if args.output:
        args.output.write_text(rendered)
    if args.report:
        print(
            json.dumps(
                {
                    "new_estimates": len(estimates),
                    "descent_estimates": document["estimate_summary"][
                        "descent_estimates"
                    ],
                    "segment_distance_profiles": document["estimate_summary"][
                        "segment_distance_profiles"
                    ],
                    "unresolved": document["unresolved"],
                    "errors": errors,
                    "low_confidence_descent": [
                        item["slug"]
                        for item in estimates
                        if item.get("evidence", {}).get("confidence") == "low"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif not args.output:
        print(rendered, end="")


if __name__ == "__main__":
    main()
