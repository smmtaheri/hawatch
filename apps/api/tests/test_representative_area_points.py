"""Area destinations obey the same Point contract as every other destination."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.urls import Resolver404, resolve
from hawatch.modules.catalog import validation

CATALOG_DIR = Path(__file__).parents[1] / 'fixtures/catalog'


def test_area_pages_are_regular_points_and_third_entity_path_is_absent():
    for slug in ('dena', 'sahand', 'zardkuh', 'oshtorankuh', 'kabirkuh'):
        assert resolve(f'/points/{slug}').url_name == 'seo-point'
        with pytest.raises(Resolver404):
            resolve(f'/mountains/{slug}')


def test_representative_catalog_reuses_exact_named_summit_coordinates():
    catalog = json.loads((CATALOG_DIR / 'representative_area_points_20261106_v1.json').read_text())
    assert not validation.validate_catalog_document(catalog)
    assert catalog['routes'] == {}
    owners = {}
    for path in CATALOG_DIR.glob('*_v*.json'):
        if path.name != 'representative_area_points_20261106_v1.json':
            owners.update(json.loads(path.read_text()).get('weather_points', {}))
    for pair in catalog['reviewed_nearby_point_pairs']:
        area, summit = pair['slugs']
        row, source = catalog['weather_points'][area], owners[summit]
        assert row['kind'] == 'primary' and row['place_type'] == 'landmark'
        assert row['latitude'] == source['latitude'] and row['longitude'] == source['longitude']
        assert pair['relationship'] == 'area_representative'
        assert summit in catalog['shared_weather_points']


def test_colocation_exception_cannot_hide_ordinary_duplicate_summits(monkeypatch):
    monkeypatch.setattr(validation, '_colocated_area_representatives', lambda: frozenset({('dena', 'qash-mastan')}))
    area = SimpleNamespace(slug='dena', place_type='landmark', kind='primary')
    summit = SimpleNamespace(slug='qash-mastan', place_type='summit', kind='primary')
    assert validation._is_colocated_area_representative(area, summit)
    assert validation._is_colocated_area_representative(summit, area)
    area.place_type = 'summit'
    assert not validation._is_colocated_area_representative(area, summit)
    area.place_type, area.slug = 'landmark', 'undeclared-area'
    assert not validation._is_colocated_area_representative(area, summit)


def test_colocation_declaration_requires_existing_shared_representative():
    catalog = json.loads((CATALOG_DIR / 'representative_area_points_20261106_v1.json').read_text())
    catalog['shared_weather_points'].remove('qash-mastan')
    assert any(issue.code == 'area-representative' for issue in validation.validate_catalog_document(catalog))
