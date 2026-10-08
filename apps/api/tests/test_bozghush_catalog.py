import json
from pathlib import Path


def test_bozghush_is_a_distinct_peak_with_a_named_northern_ascent_route():
    catalog_dir = Path(__file__).parents[1] / "fixtures/catalog"
    catalog = json.loads((catalog_dir / "bozghush_v1.json").read_text(encoding="utf-8"))
    aq_dagh = json.loads((catalog_dir / "aq_dagh_khalkhal_v1.json").read_text(encoding="utf-8"))

    assert catalog["catalog_version"] == "hawatch-bozghush-v1"
    assert catalog["primary_point"] == "bozghush"
    peak = catalog["weather_points"]["bozghush"]
    assert peak["name"] == "قلهٔ بزقوش"
    assert peak["seo_indexable"] is True
    assert "قلهٔ آغ‌داغ" in peak["aliases"]

    # The existing Agh Dagh Khalkhal is a separate summit, not an alias/duplicate.
    khalkhal = aq_dagh["weather_points"]["aq-dagh-khalkhal"]
    assert khalkhal["latitude"] != peak["latitude"]
    assert abs(khalkhal["longitude"] - peak["longitude"]) > 0.5

    route = catalog["routes"]["bozghush-north"]
    assert route["points"] == [
        "bozghush-allah-haqq-trailhead",
        "bozghush-shelter",
        "bozghush",
    ]
    assert route["distance_km"] == 6.75
    assert route["ascent_m"] == 1270
    assert route["one_way_minutes"] == 280
    assert route["timing"]["cumulative_minutes"] == {
        "bozghush-allah-haqq-trailhead": 0,
        "bozghush-shelter": 160,
        "bozghush": 280,
    }

    for slug in ("bozghush-allah-haqq-trailhead", "bozghush-shelter"):
        assert catalog["weather_points"][slug]["seo_indexable"] is False
