#!/usr/bin/env python3
"""Offline medium-pace ETA for pending, canonically matched hiking routes.

No database writes, provider requests, raw timestamp ETA or original GPX edits.
Uses the established Qaleh Roudkhan slope model, plus an explicit total-time
cross-check against registered distance/ascent and reviewed one-way reduction.
"""

import argparse
import copy
import importlib.util
import json
import math
from bisect import bisect_right
from pathlib import Path

from analyze_route_tracks import (
    haversine_m,
    moving_average,
    resample_elevations_by_distance,
)

_spec = importlib.util.spec_from_file_location(
    "route_reductions", Path(__file__).with_name("review-route-reductions.py")
)
_reductions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reductions)

# Local review choice, not a runtime speed change or inferred weather effect.
# The waterfall/cave trail has multiple short, steep woodland sections.
TERRAIN_FACTORS = {"shirabad-seven-waterfalls": 1.4}
DEFAULT_TERRAIN_FACTOR = 1.2
METHOD = "gpx-slope+distance-ascent-loss-check"
VERSION = "pending-eta-v1"


def ceil5(value):
    return int(math.ceil(value / 5) * 5)


def interpolate(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1
    return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])


def estimate(profile, route, *, terrain_factor=DEFAULT_TERRAIN_FACTOR):
    cut = profile["_profile"]
    indices = profile["_point_indices"]
    along = [0.0]
    for a, b in zip(cut, cut[1:]):
        along.append(
            along[-1] + haversine_m((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        )
    if along[-1] <= 0 or not 1 <= terrain_factor <= 2:
        raise ValueError("invalid profile distance/terrain factor")
    elevations = resample_elevations_by_distance(cut)
    distances = [i * 50.0 for i in range(len(elevations))]
    # Retain the final partial 50 m interval; never drop the target segment.
    if along[-1] > distances[-1] + 1e-6:
        distances.append(distances[-1] + 50.0)
        elevations.append(cut[-1]["ele"])
    elevations = moving_average(elevations)
    if distances[-1] > along[-1]:
        terminal = interpolate(distances, elevations, along[-1])
        distances[-1] = along[-1]
        elevations[-1] = terminal
    times = [0.0]
    for da, db, ea, eb in zip(distances, distances[1:], elevations, elevations[1:]):
        grade = (eb - ea) / (db - da)
        if abs(grade) > 1:
            raise ValueError("smoothed grade exceeds hiking-profile review limit")
        speed = min(4.0, 6 * math.exp(-3.5 * abs(grade + 0.05)))
        times.append(times[-1] + (db - da) / 1000 / speed * 60 * terrain_factor)
    distance_km = float(route["distance_km"])
    ascent = route["ascent_m"]
    loss = profile["descent_m"]
    if (
        not math.isfinite(distance_km)
        or distance_km <= 0
        or ascent is None
        or ascent < 0
    ):
        raise ValueError("registered distance/ascent incomplete")
    # Independent planning check: 4 km/h + 600 m/h ascent + 1200 m/h loss.
    # Loss adds effort; it must never be subtracted or treated as a return trip.
    reference = (distance_km * 15 + ascent / 10 + loss / 20) * terrain_factor
    raw_total = times[-1]
    bounded_total = max(reference * 0.85, min(reference * 1.35, raw_total))
    scale = bounded_total / raw_total
    if not 0.5 <= scale <= 2:
        raise ValueError(
            "model disagreement too large; inspect evidence instead of forcing ETA"
        )
    total = ceil5(bounded_total)
    cumulative = [0]
    for index in indices[1:-1]:
        value = int(
            math.floor(
                interpolate(distances, times, along[index]) * total / raw_total / 5
                + 0.5
            )
            * 5
        )
        cumulative.append(value)
    cumulative.append(total)
    # Preserve nearby real landmarks without adding 5 min per 50 m of trail.
    # Interior landmarks may use minute precision; the runtime pace rounding
    # remains unchanged. Reserve one minute for each remaining segment.
    for i in range(1, len(cumulative) - 1):
        cumulative[i] = min(
            total - (len(cumulative) - 1 - i), max(cumulative[i - 1] + 1, cumulative[i])
        )
    if any(b <= a for a, b in zip(cumulative, cumulative[1:])):
        raise ValueError("rounded landmarks cannot fit in total duration")
    sources = sorted(
        set(
            profile["evidence"]["catalog_source_urls"]
            + (
                [profile["evidence"]["source_url"]]
                if profile["evidence"]["source_url"]
                else []
            )
        )
    )
    prefix_url = profile["evidence"].get("reviewed_prefix", {}).get("source_url")
    if prefix_url:
        sources = sorted(set(sources) | {prefix_url})
    if not sources:
        raise ValueError("missing published source evidence")
    return {
        "slug": route["slug"],
        "one_way_minutes": total,
        "timing_status": "estimated",
        "timing": {
            "method": METHOD,
            "version": VERSION,
            "confidence": "low",
            "uncertainty_minutes": max(15, ceil5(total * 0.25)),
            "source_urls": sources,
            "cumulative_minutes": dict(zip(profile["chain"], cumulative)),
            "evidence": {
                **profile["evidence"],
                "timestamp_used": False,
                "terrain_factor": terrain_factor,
                "registered_distance_km": distance_km,
                "registered_ascent_m": ascent,
                "reviewed_reduction_m": loss,
                "raw_slope_minutes": round(raw_total, 2),
                "independent_check_minutes": round(reference, 2),
                "accepted_check_range": [0.85, 1.35],
                "scale_to_published_total": round(total / raw_total, 6),
                "model_profile_method": "50m-5sample+slope-speed-cap4",
                "landmark_distance_m": [round(along[i]) for i in indices],
            },
        },
    }


def review(root, registered):
    pending = [copy.deepcopy(r) for r in registered if r["timing_status"] == "pending"]
    for r in pending:
        if r["one_way_minutes"] is not None or any(
            p["cumulative_minutes"] is not None for p in r["points"]
        ):
            raise ValueError(
                "partially entered timing needs separate review: " + r["slug"]
            )
        r["descent_m"] = None  # Re-check the actual cut, even when reduction exists.
    reductions = _reductions.review(root, pending, include_profiles=True)
    rows = {r["slug"]: r for r in pending}
    accepted = []
    diagnostics = list(reductions["diagnostics"])
    for p in reductions["routes"]:
        try:
            accepted.append(
                estimate(
                    p,
                    rows[p["slug"]],
                    terrain_factor=TERRAIN_FACTORS.get(
                        p["slug"], DEFAULT_TERRAIN_FACTOR
                    ),
                )
            )
        except ValueError as error:
            diagnostics.append({"slug": p["slug"], "reason": str(error)})
    return {
        "routes": accepted,
        "unresolved": [
            r["slug"] for r in pending if r["slug"] not in {a["slug"] for a in accepted}
        ],
        "diagnostics": diagnostics,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--registered-routes", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            review(
                args.source_root.resolve(),
                json.loads(args.registered_routes.read_text()),
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
