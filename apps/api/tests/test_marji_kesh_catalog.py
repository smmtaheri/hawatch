import json
from pathlib import Path


def test_marji_kesh_route_has_report_based_timing():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/marji_kesh_v3.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))
    route = catalog["routes"]["southern_hezarchal"]

    assert route["timing_status"] == "estimated"
    assert route["one_way_minutes"] == 360
    assert route["timing"]["cumulative_minutes"] == {
        "alamkuh-tang-galu": 0,
        "alamkuh-hesarchal": 120,
        "marji-kesh": 360,
    }
    assert route["timing"]["confidence"] == "medium"
    assert route["timing"]["uncertainty_minutes"] == 90
    assert (
        "https://www.wikiloc.com/hiking-trails/qlh-lm-khwh-mrjykhsh-11-12-mrdd-1403-179557156"
        in route["timing"]["source_urls"]
    )
