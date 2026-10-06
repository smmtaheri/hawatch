import json
from pathlib import Path

import pytest

from hawatch.api.v1.serializers import related_routes_for_weather_point
from hawatch.modules.catalog.seed import ensure_catalog
from hawatch.modules.catalog.validation import (
    validate_catalog_document,
    validate_database_catalog,
    validate_indexable_link_graph,
)
from hawatch.modules.forecasts.models import WeatherPoint


CATALOG_DIR = Path(__file__).parents[1] / "fixtures/catalog"


def test_catalog_aliases_identify_one_place_without_hiding_validation_warnings():
    for filename in ("dobarar_v1.json", "kandolus_village_v1.json"):
        catalog = json.loads((CATALOG_DIR / filename).read_text())
        assert not validate_catalog_document(catalog)

    # Ambiguous aliases are still detected; we corrected the data rather
    # than weakening the validator or silently dropping its warnings.
    catalog["weather_points"]["kojur-moss-waterfall"]["aliases"].append(
        "آبشار مسیر کجور به سیسنگان"
    )
    assert any(issue.code == "alias-collision" for issue in validate_catalog_document(catalog))


def test_chalon_pass_uses_named_waypoint_not_a_track_point_beside_the_summit():
    catalog = json.loads((CATALOG_DIR / "siah_kaman_v1.json").read_text())
    point = catalog["weather_points"]["siah-kaman-chalon-pass"]
    assert (point["latitude"], point["longitude"], point["elevation_m"]) == (
        36.382386, 50.988796, 4423
    )
    assert point["seo_indexable"] is False
    assert catalog["weather_points"]["chalon-peak"]["seo_indexable"] is True


@pytest.mark.django_db
def test_catalog_cleanup_preserves_route_chains_and_exposes_real_destination_links(api_client):
    ensure_catalog("hawatch-test-demo-v1")

    assert not validate_database_catalog(strict=True)
    assert not validate_indexable_link_graph()

    for point_slug, route_slug in (
        ("shahvars-east", "blades-rakhsh-to-shahvars"),
        ("sisangan-waterfall", "kojur-to-sisangan-waterfall"),
    ):
        point = WeatherPoint.objects.get(slug=point_slug)
        assert point.kind == WeatherPoint.Kind.PRIMARY
        assert point.importance == "primary" and point.seo_indexable
        page = api_client.get(f"/points/{point_slug}")
        assert page.status_code == 200
        assert page["X-Robots-Tag"] == "index,follow"
        assert f'href="/routes/{route_slug}"' in page.content.decode()
        assert f'href="/points/{point_slug}"' in api_client.get(f"/routes/{route_slug}").content.decode()
        assert route_slug in {row["slug"] for row in related_routes_for_weather_point(point)}

    response = api_client.get("/api/v1/seo/sitemap.xml")
    assert response.status_code == 200
    sitemap = response.content.decode()
    for slug in ("shahvars-east", "sisangan-waterfall"):
        assert f"https://hawatch.ir/points/{slug}</loc>" in sitemap
    for slug in (
        "doshakh-shelter", "shirabad-third-waterfall",
        "shirabad-fourth-waterfall", "shirabad-sixth-waterfall",
        "siah-kaman-chalon-pass", "kojur-moss-waterfall",
    ):
        assert WeatherPoint.objects.get(slug=slug).is_active
        assert f"https://hawatch.ir/points/{slug}</loc>" not in sitemap
        assert api_client.get(f"/points/{slug}")["X-Robots-Tag"] == "noindex,follow"

    # Curator exceptions never make genuinely duplicate coordinates valid.
    summit = WeatherPoint.objects.get(slug="doshakh-tehran")
    WeatherPoint.objects.filter(slug="doshakh-shelter").update(location=summit.location)
    assert any(issue.code == "near-duplicate-point" for issue in validate_database_catalog())
