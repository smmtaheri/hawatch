import json
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "fixtures" / "catalog" / "filband_v1.json"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_filband_catalog_exposes_village_peaks_and_adjacent_villages():
    catalog = load_catalog()
    points = catalog["weather_points"]

    assert catalog["primary_point"] == "filband-village"
    assert {"filband-village", "sangchal-village", "sheikh-musa-village", "hesin-bon", "espeh-rez"} <= set(points)
    assert all(points[slug]["kind"] == "primary" for slug in points)
    assert all(points[slug]["seo_indexable"] for slug in points)


def test_filband_catalog_has_two_distinct_routes_and_reuses_existing_alimestan_points():
    catalog = load_catalog()
    routes = catalog["routes"]

    first = routes["filband-hesin-bon-espeh-rez"]
    second = routes["filband-alimestan-ridge"]
    assert first["points"] == ["filband-village", "hesin-bon", "espeh-rez"]
    assert second["points"] == ["filband-village", "imamzadeh-qasem", "alimestan-village"]
    assert catalog["shared_weather_points"] == ["imamzadeh-qasem", "alimestan-village"]
    assert first["timing_status"] == "estimated"
    assert second["timing_status"] == "estimated"
    assert first["evidence_tracks"] == ["tracks/filband/filband-hesin-bon-espeh-rez-2023.gpx"]
    assert second["evidence_tracks"] == ["tracks/filband/filband-to-elimastan-ridge-2013.gpx"]
