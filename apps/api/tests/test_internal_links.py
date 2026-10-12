from django.contrib.gis.geos import Point

import pytest

from hawatch.modules.catalog.internal_links import (
    related_public_similar_destinations,
    similar_destinations_title,
)
from hawatch.modules.forecasts.models import WeatherPoint


def _destination(
    slug: str,
    *,
    latitude: float,
    longitude: float,
    category_key: str,
    place_type: str,
    catalog_version: str = "",
) -> WeatherPoint:
    return WeatherPoint.objects.create(
        slug=slug,
        name=slug,
        page_name=slug,
        short_label=slug,
        place_type=place_type,
        category_key=category_key,
        importance="primary",
        name_status="established",
        source_urls=["https://example.test/point"],
        kind=WeatherPoint.Kind.PRIMARY,
        location=Point(longitude, latitude, srid=4326),
        elevation_m=1500,
        catalog_version=catalog_version,
        data_mode="live",
        seo_indexable=True,
        is_active=True,
    )


@pytest.mark.django_db
def test_point_only_destination_falls_back_to_place_type_even_with_category():
    target = _destination(
        "kalut-target",
        latitude=30.8,
        longitude=57.8,
        category_key="kalut",
        place_type="desert",
    )
    alternative = _destination(
        "desert-alternative",
        latitude=31.0,
        longitude=57.9,
        category_key="desert",
        place_type="desert",
    )

    assert [item.slug for item in related_public_similar_destinations(target)] == [alternative.slug]
    assert similar_destinations_title(target) == "مقصدهای مشابه"


@pytest.mark.django_db
def test_unique_destination_category_uses_same_catalog_cluster():
    target = _destination(
        "coastal-beach",
        latitude=37.7,
        longitude=49.1,
        category_key="beach",
        place_type="beach",
        catalog_version="coastal-cluster-v1",
    )
    nearby_forest = _destination(
        "coastal-forest",
        latitude=37.71,
        longitude=49.11,
        category_key="forest",
        place_type="forest",
        catalog_version="coastal-cluster-v1",
    )
    unrelated_forest = _destination(
        "distant-forest",
        latitude=36.0,
        longitude=51.0,
        category_key="forest",
        place_type="forest",
        catalog_version="other-cluster-v1",
    )

    related = related_public_similar_destinations(target)
    assert [item.slug for item in related] == [nearby_forest.slug]
    assert unrelated_forest.slug not in [item.slug for item in related]


@pytest.mark.django_db
def test_exact_category_is_ranked_before_type_and_catalog_fallbacks():
    target = _destination(
        "target-spring",
        latitude=36.0,
        longitude=53.8,
        category_key="spring",
        place_type="spring",
        catalog_version="spring-cluster-v1",
    )
    same_cluster = _destination(
        "cluster-lake",
        latitude=36.01,
        longitude=53.81,
        category_key="lake",
        place_type="lake",
        catalog_version="spring-cluster-v1",
    )
    same_type = _destination(
        "other-spring",
        latitude=36.02,
        longitude=53.82,
        category_key="hot_spring",
        place_type="spring",
    )
    same_category = _destination(
        "same-category-spring",
        latitude=36.03,
        longitude=53.83,
        category_key="spring",
        place_type="water",
    )

    assert [item.slug for item in related_public_similar_destinations(target)] == [
        same_category.slug,
        same_cluster.slug,
        same_type.slug,
    ]
