from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo
import zlib
import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from hawatch.api.v1.week_interest import fixed_points, payload_ttl, touch_page, warm_targets
from hawatch.api.v1.week_views import cached_week
from hawatch.api.v1.week_cache import invalidate_week_cache, revision
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.routes.models import WeekCacheInterest, Route

pytestmark = pytest.mark.django_db

@pytest.fixture
def catalog():
    cache.clear()
    seed_catalog(catalog_file='catalog/tochal_v1.json', prune=False, force_adopt=False)


def test_fixed_selection_has_100_unique_public_catalog_slugs():
    selected = fixed_points()
    assert len(selected) == len(set(selected)) == 100


def test_last_visit_renews_to_48_hours_without_adding_days(catalog):
    now = timezone.now()
    with patch('hawatch.api.v1.week_interest.timezone.now', return_value=now):
        touch_page('point', 'tochal')
    later = now + timedelta(hours=3)
    with patch('hawatch.api.v1.week_interest.timezone.now', return_value=later):
        touch_page('point', 'tochal')
    assert WeekCacheInterest.objects.get().expires_at == later + timedelta(hours=48)
    with patch('hawatch.api.v1.week_interest.timezone.now', return_value=now):
        touch_page('point', 'tochal')
    assert WeekCacheInterest.objects.get().expires_at == later + timedelta(hours=48)


def test_fixed_points_use_the_first_related_route_and_recent_pages_expire(catalog):
    touch_page('point', 'tochal-sarband-square')
    with patch('hawatch.api.v1.week_interest.fixed_points', return_value=['tochal']):
        targets = warm_targets()
    first = Route.objects.filter(is_active=True, points__weather_point__slug='tochal').order_by('sort_order','slug').first()
    assert targets == [('point','tochal'), ('route',first.slug), ('point','tochal-sarband-square')]
    WeekCacheInterest.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    with patch('hawatch.api.v1.week_interest.fixed_points', return_value=['tochal']):
        assert ('point','tochal-sarband-square') not in warm_targets()
    assert not WeekCacheInterest.objects.exists()


def test_visit_endpoint_validates_page_without_fetching_weather(catalog):
    client = APIClient()
    with patch('hawatch.api.v1.week_views.build_week', side_effect=AssertionError('no weather build')):
        assert client.post('/api/v1/points/tochal/forecast/visit/').status_code == 204
        assert client.post('/api/v1/points/missing/forecast/visit/').status_code == 404
    assert WeekCacheInterest.objects.count() == 1


def test_warming_does_not_renew_visits_and_survives_one_failure(catalog):
    touch_page('route','tochal-darband')
    expiry = WeekCacheInterest.objects.get().expires_at
    with patch('hawatch.api.v1.week_interest.fixed_points', return_value=['tochal']), patch('hawatch.jobs.management.commands.warm_week_cache.cached_week', side_effect=[RuntimeError('one failed page'), (b'{}','HIT'), (b'{}','HIT')]) as build:
        call_command('warm_week_cache')
    assert build.call_count >= 2
    assert WeekCacheInterest.objects.get().expires_at == expiry


@pytest.mark.parametrize('schedule,expected', [('00:00,06:00,12:00,18:00',5*3600), ('00:00,03:00,06:00,09:00,12:00,15:00,18:00,21:00',2*3600)])
def test_payload_expiration_tracks_ingest_schedule(monkeypatch,schedule,expected):
    monkeypatch.setenv('HAWATCH_INGEST_SCHEDULE',schedule)
    with patch('hawatch.api.v1.week_interest.now_tehran', return_value=datetime(2026,10,9,1,tzinfo=ZoneInfo('Asia/Tehran'))):
        assert payload_ttl() == expected


def test_compressed_redis_payload_and_new_data_revision(catalog,settings,django_capture_on_commit_callbacks):
    settings.HAWATCH_ASSET_VERSION='cache-flow-test'
    today=timezone.localdate()
    payload={'last_generated_at':'2026-10-09T01:00:00+03:30','text':'x'*20000}
    with patch('hawatch.api.v1.week_views.build_week',return_value=payload) as build:
        cold,status=cached_week('point','tochal',today)
        assert status=='MISS'
        key=f'week-3:cache-flow-test:{revision()}:point:tochal:{today}'
        packed=cache.get(key)
        assert len(packed[0])<len(cold[0])/10 and zlib.decompress(packed[0])==cold[0]
        assert cached_week('point','tochal',today)==(cold,'HIT')
        with django_capture_on_commit_callbacks(execute=True):invalidate_week_cache()
        assert cached_week('point','tochal',today)[1]=='MISS'
        assert build.call_count==2
        assert not WeekCacheInterest.objects.exists()
