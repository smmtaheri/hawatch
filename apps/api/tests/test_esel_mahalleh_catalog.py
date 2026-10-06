import json
from pathlib import Path

from hawatch.modules.catalog.validation import validate_catalog_document


CATALOGS = Path(__file__).parents[1] / "fixtures/catalog"


def test_esel_mahalleh_is_an_indexable_independent_village_shared_by_both_routes():
    daryasar = json.loads((CATALOGS / "daryasar_v2.json").read_text())
    sialan = json.loads((CATALOGS / "sialan_v2.json").read_text())
    assert not validate_catalog_document(daryasar)
    village = daryasar["weather_points"]["esel-mahalleh"]
    assert village["name"] == village["page_name"] == village["short_label"] == "روستای اِسِل‌محله"
    assert village["kind"] == village["importance"] == "primary"
    assert village["seo_indexable"] is True
    assert village["category_key"] == village["place_type"] == "village"
    assert "daryasar-esel-mahalleh" not in daryasar["weather_points"]
    assert "esel-mahalleh" in sialan["shared_weather_points"]
    assert "esel-mahalleh" not in sialan["weather_points"]
    for route in (daryasar["routes"]["esel_mahalleh_to_daryasar"], sialan["routes"]["esel_mahalleh_to_sialan"]):
        assert route["points"][0] == "esel-mahalleh"
        assert route["timing"]["cumulative_minutes"]["esel-mahalleh"] == 0
        assert "daryasar-esel-mahalleh" not in route["points"]
        assert "daryasar-esel-mahalleh" not in route["timing"]["cumulative_minutes"]
    assert daryasar["routes"]["esel_mahalleh_to_daryasar"]["slug"] == "daryasar-esel-mahalleh"
    heniz = sialan["weather_points"]["heniz"]
    assert heniz["seo_indexable"] is True
    assert heniz["kind"] == heniz["importance"] == "primary"
