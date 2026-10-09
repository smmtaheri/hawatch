from io import StringIO

import pytest
from rest_framework.test import APIClient
from django.core.management import call_command

from hawatch.common.time import paced_duration_minutes
from hawatch.modules.catalog.sync import load_packaged_catalogs
from hawatch.modules.routes.models import Route
from hawatch.modules.routes.timing import route_timing_complete

EXPECTED = {
    "afjeh-hoyej-person": 210,
    "andar-person-rizan": 345,
    "afjeh-hoyej-rizan": 265,
    "afjeh-saka-atash-kuh": 320,
    "barg-jahan-person": 250,
    "chin-kalagh-sarbazark": 450,
    "garmabdar-pirzan-mehrchal": 280,
    "gol-zard-north-polour": 235,
    "gol-zard-south-mobarakabad": 250,
    "imameh-mehrchal": 310,
    "hio-aseman-kuh": 250,
    "ira-fil-zamin": 265,
    "ira-siah-palas": 310,
    "javard-siah-palas": 215,
    "kaman-kouh-varangerud-yakhchal": 435,
    "lasak-gorge-mishineh-marg": 315,
    "lavasan-bozorg-fil-zamin": 225,
    "rendan-village-waterfall": 65,
    "shirabad-seven-waterfalls": 95,
    "sofeh-park-to-summit": 100,
}
BLOCKED = {
    "sanboran-gahar",
}


def test_packaged_timings_have_traceable_estimates_and_consistent_cumulatives():
    desired = load_packaged_catalogs()
    for slug, total in EXPECTED.items():
        row = desired.route_rows[slug]
        timing = row["timing"]
        assert row["timing_status"] == "estimated"
        assert row["one_way_minutes"] == total
        cumulatives = [timing["cumulative_minutes"][point] for point in row["points"]]
        assert cumulatives[0] == 0 and cumulatives[-1] == total
        assert all(b > a for a, b in zip(cumulatives, cumulatives[1:]))
        assert timing["source_urls"] and timing["uncertainty_minutes"] >= 15
        assert timing["evidence"]["timestamp_used"] is False
        assert timing["evidence"]["source_sha256"]
    for slug in BLOCKED:
        assert desired.route_rows[slug]["timing_status"] == "pending"
        assert desired.route_rows[slug].get("one_way_minutes") is None


@pytest.mark.django_db
def test_deploy_catalog_sync_completes_existing_pending_routes_and_preserves_paces():
    call_command("sync_catalog", "--apply", stdout=StringIO())
    Route.objects.filter(slug__in=EXPECTED).update(
        timing_status="pending", one_way_minutes=None
    )
    for route in Route.objects.filter(slug__in=EXPECTED):
        route.points.update(
            timing_status="pending", cumulative_minutes=None, segment_minutes=None
        )
    call_command("sync_catalog", "--apply", stdout=StringIO())
    for slug, total in EXPECTED.items():
        route = Route.objects.get(slug=slug)
        assert route.one_way_minutes == total
        assert route_timing_complete(
            timing_status=route.timing_status,
            one_way_minutes=total,
            points=route.points.all(),
        )
    for slug in BLOCKED:
        assert Route.objects.get(slug=slug).timing_status == "pending"
    client = APIClient()
    for pace in ("متوسط", "آرام", "سریع"):
        result = client.get(
            "/api/v1/routes/rendan-village-waterfall/forecast/",
            {"start_time": "06:00", "speed": pace},
        ).json()
        assert result["timing_pending"] is False
        assert result["points"][-1]["arrival_minutes"] == 360 + paced_duration_minutes(
            65, pace
        )
    repeated = StringIO()
    call_command("sync_catalog", "--apply", stdout=repeated)
    assert "updated=0" in repeated.getvalue()
