import json
from pathlib import Path


def test_kaman_kouh_has_independent_peak_and_shared_varangerud_routes():
    fixture = Path(__file__).parents[1] / "fixtures/catalog/kaman_kouh_v1.json"
    catalog = json.loads(fixture.read_text(encoding="utf-8"))

    assert catalog["primary_point"] == "kaman-kouh"
    summit = catalog["weather_points"]["kaman-kouh"]
    assert summit["name"] == "قلهٔ کمان‌کوه"
    assert summit["place_type"] == "summit"
    assert summit["seo_indexable"] is True
    assert catalog["shared_weather_points"] == [
        "azadkouh-varangerud-start",
        "azadkouh-shirkamar-intersection",
        "azadkouh-kamankouh-lake",
    ]

    direct = catalog["routes"]["varangerud_to_kaman_kouh"]
    assert direct["slug"] == "kaman-kouh-varangerud"
    assert direct["points"] == [
        "azadkouh-varangerud-start",
        "azadkouh-shirkamar-intersection",
        "kaman-kouh",
    ]
    assert direct["timing_status"] == "estimated"

    via_lake = catalog["routes"]["varangerud_to_kaman_kouh_via_lake"]
    assert via_lake["slug"] == "kaman-kouh-varangerud-yakhchal"
    assert via_lake["points"][-2:] == [
        "azadkouh-kamankouh-lake",
        "kaman-kouh",
    ]
    assert via_lake["timing_status"] == "pending"
