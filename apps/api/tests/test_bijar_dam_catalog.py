import json
from pathlib import Path


def test_bijar_reservoir_route_uses_the_named_feature_for_its_endpoint():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/bijar_dam_v2.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    points = catalog["weather_points"]
    route = catalog["routes"]["shah_shahidan_to_bijar_reservoir"]
    legacy_slug = "-".join(("bijar", "reservoir", "end"))

    assert legacy_slug not in points
    assert catalog["catalog_version"] == "hawatch-bijar-dam-catalog-v2"
    assert points["bijar-reservoir"]["name"] == "آبگیر سد بیجار"
    assert points["bijar-reservoir"]["page_name"] == "آبگیر سد بیجار"
    assert route["points"][-1] == "bijar-reservoir"
    assert route["target_label"] == "آبگیر سد بیجار"
    assert route["timing"]["cumulative_minutes"]["bijar-reservoir"] == 471
