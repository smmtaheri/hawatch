from types import SimpleNamespace

import pytest

from hawatch.common.time import (
    ROUTE_PACE_MODEL_VERSION,
    estimate_route_duration_minutes,
    paced_route_cumulative_minutes,
)
from hawatch.modules.routes.timing import route_mean_elevation_m


REFERENCE_ROUTES = {
    # Mean checkpoint-interpolated elevations; user-provided target hours.
    "tochal": (10.3, 2150, 0, 2830, (9.5, 6.5, 3.5)),
    "damavand": (9.5, 2584, 26, 4173, (14, 8.5, 3.75)),
    "eskelim": (8.8, 334, 57, 447, (4, 2.5, 1.125)),
    "azadkouh": (20.2, 2150, 365, 3427, (14, 8.5, 5.75)),
    "alamkuh": (8.6, 1550, 0, 3941, (11, 7, 3.5)),
}
PACE_LABELS = ("آرام", "متوسط", "سریع")


def test_route_pace_profiles_are_ordered_and_stay_within_calibration_error_budget():
    errors = []
    for distance_km, ascent_m, descent_m, mean_elevation_m, reference_hours in REFERENCE_ROUTES.values():
        actual_minutes = [
            estimate_route_duration_minutes(
                distance_km,
                ascent_m,
                descent_m,
                pace,
                mean_elevation_m=mean_elevation_m,
            )
            for pace in PACE_LABELS
        ]

        assert actual_minutes == sorted(actual_minutes, reverse=True)
        errors.extend(
            abs(actual - expected * 60)
            for actual, expected in zip(actual_minutes, reference_hours)
        )

    assert sum(errors) / len(errors) <= 40
    assert max(errors) <= 120


def test_route_pace_model_is_versioned_and_uses_descent_effort():
    flat = estimate_route_duration_minutes(10, 500, 0, "متوسط")
    with_descent = estimate_route_duration_minutes(10, 500, 800, "متوسط")

    assert ROUTE_PACE_MODEL_VERSION == "distance-ascent-altitude-fatigue-v3"
    assert with_descent > flat
    assert with_descent % 5 == 0


def test_route_pace_model_accounts_for_altitude_and_long_route_fatigue():
    low_altitude = estimate_route_duration_minutes(
        8.6, 1550, 0, "متوسط", mean_elevation_m=2500
    )
    high_altitude = estimate_route_duration_minutes(
        8.6, 1550, 0, "متوسط", mean_elevation_m=4000
    )
    short_flat = estimate_route_duration_minutes(10, 0, 0, "سریع")
    long_flat = estimate_route_duration_minutes(20, 0, 0, "سریع")

    assert high_altitude > low_altitude
    assert long_flat > short_flat * 2


def test_distance_fatigue_does_not_make_fast_pace_slower_than_medium_on_long_flat_route():
    medium = estimate_route_duration_minutes(27, 0, 0, "متوسط")
    fast = estimate_route_duration_minutes(27, 0, 0, "سریع")

    assert fast < medium


def test_mean_route_elevation_uses_segment_distance_weighting():
    route_points = [
        SimpleNamespace(sort_order=1, effective_elevation_m=1000, segment_distance_m=None),
        SimpleNamespace(sort_order=2, effective_elevation_m=3000, segment_distance_m=1000),
        SimpleNamespace(sort_order=3, effective_elevation_m=5000, segment_distance_m=3000),
    ]

    assert route_mean_elevation_m(route_points) == pytest.approx(3500)


def test_cumulative_landmark_time_scales_to_the_modeled_route_duration():
    total = estimate_route_duration_minutes(
        10.3,
        2150,
        0,
        "متوسط",
        mean_elevation_m=2830,
        fallback_medium_minutes=315,
    )
    halfway = paced_route_cumulative_minutes(
        157,
        315,
        "متوسط",
        distance_km=10.3,
        ascent_m=2150,
        descent_m=0,
        mean_elevation_m=2830,
    )

    assert halfway == round(total / 2 / 5) * 5
    assert paced_route_cumulative_minutes(
        315,
        315,
        "متوسط",
        distance_km=10.3,
        ascent_m=2150,
        descent_m=0,
        mean_elevation_m=2830,
    ) == total


def test_incomplete_geometry_uses_legacy_medium_duration_fallback():
    assert estimate_route_duration_minutes(
        None, 500, 0, "آرام", fallback_medium_minutes=120
    ) == 150
