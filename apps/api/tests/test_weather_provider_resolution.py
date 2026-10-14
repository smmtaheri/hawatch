from __future__ import annotations

from math import cos, pi, radians

import pytest

from hawatch.integrations.weather.normalize import (
    provider_resolution_distance_km,
    provider_resolution_is_acceptable,
)


@pytest.mark.parametrize(("distance_km", "expected"), [(5.2, True), (5.26, False)])
def test_provider_resolution_accepts_only_the_narrow_over_five_km_allowance(distance_km, expected):
    latitude = 30.907806
    requested_longitude = 51.480139
    longitude_delta = distance_km / (6371.0088 * cos(radians(latitude))) * 180 / pi
    provider_point = {
        "latitude": latitude,
        "longitude": requested_longitude + longitude_delta,
    }

    measured = provider_resolution_distance_km(
        provider_point,
        requested_latitude=latitude,
        requested_longitude=requested_longitude,
    )

    assert measured == pytest.approx(distance_km)
    assert provider_resolution_is_acceptable(
        provider_point,
        requested_latitude=latitude,
        requested_longitude=requested_longitude,
    ) is expected
