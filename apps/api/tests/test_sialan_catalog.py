import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOG = Path(__file__).parents[1] / "fixtures/catalog/sialan_v2.json"


def test_heniz_is_an_independent_destination_and_summit_is_not_route_specific():
    catalog = json.loads(CATALOG.read_text())
    assert not validate_catalog_document(catalog)
    village = catalog["weather_points"]["heniz"]
    assert village["name"] == village["page_name"] == "روستای هنیز"
    assert village["kind"] == village["importance"] == "primary"
    assert village["seo_indexable"] is True
    assert village["category_key"] == village["place_type"] == "village"
    assert catalog["weather_points"]["sialan"]["page_name"] == "قلهٔ سیالان"
    assert "مرز قزوین و مازندران" in catalog["point"]["region"]
    assert "sialan-heniz-trailhead" not in catalog["weather_points"]


def test_southern_route_reuses_pass_and_summit_with_stop_free_outbound_timing():
    catalog = json.loads(CATALOG.read_text())
    route = catalog["routes"]["heniz_to_sialan"]
    assert route["slug"] == "sialan-heniz"
    assert route["points"] == ["heniz", "sialan-south-shelter", "sialan-pass", "sialan"]
    assert catalog["weather_points"]["sialan-south-shelter"]["place_type"] == "shelter"
    assert route["distance_km"] == 14  # outbound, not full roundtrip or raw GPS spikes
    assert route["ascent_m"] == 2080
    assert route["timing_status"] == "estimated"
    assert route["one_way_minutes"] == 450
    assert route["timing"]["uncertainty_minutes"] == 90
    minutes = [route["timing"]["cumulative_minutes"][slug] for slug in route["points"]]
    assert minutes == [0, 255, 390, 450]
    assert "GPS outliers indices1026-1027" in route["internal_note"]
    assert catalog["routes"]["esel_mahalleh_to_sialan"]["one_way_minutes"] == 690
    assert catalog["weather_points"]["sialan-pass"]["latitude"] == 36.518718
