"""Public/cacheable week, planner parity, precipitation boundaries and sharing."""
from datetime import timedelta
from unittest.mock import patch
import pytest
from django.core.cache import cache
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient
from hawatch.common.time import now_tehran, localize_dt, paced_duration_minutes
from hawatch.modules.catalog.catalog import seed_catalog
from hawatch.modules.catalog.seed import ensure_forecasts
from hawatch.modules.forecasts.models import ForecastRecord, WeatherPoint
from hawatch.modules.routes.models import Route, SharedRoutePlan
from hawatch.api.v1.week_bundles import aggregate, build_week
from hawatch.api.v1.week_cache import invalidate_week_cache
from hawatch.integrations.weather.equipment import suggest_equipment

pytestmark=pytest.mark.django_db
@pytest.fixture
def week_seed(settings):
    cache.clear()
    seed_catalog(catalog_file='catalog/tochal_v1.json',prune=False,force_adopt=False)
    ensure_forecasts(settings.DEMO_SEED_VERSION,force=True)
    return now_tehran().date()

def test_public_week_is_shared_without_account_queries_or_cookies(week_seed):
    client=APIClient()
    url='/api/v1/points/tochal/forecast/week/'
    with CaptureQueriesContext(connection) as queries:
        first=client.get(url)
    assert first.status_code==200
    body=first.json()
    assert len(body['days'])==8 and body['range_end']==(week_seed+timedelta(days=7)).isoformat()
    assert body['intervals']['24'][0][0]['complete']
    assert body['intervals']['24'][0][0]['condition']
    assert 'private' in first['Cache-Control'] and 's-maxage=' not in first['Cache-Control']
    assert first['CDN-Cache-Control']=='no-store'
    assert 'Cookie' not in first['Vary'] and not first.cookies
    assert not any('accounts_' in q['sql'] or 'auth_' in q['sql'] for q in queries)
    with CaptureQueriesContext(connection) as warm_queries:
        second=client.get(url)
    assert second.content==first.content and second['X-Hawatch-Cache']=='HIT'
    assert len(warm_queries)==0
    assert client.get(url,HTTP_IF_NONE_MATCH=first['ETag']).status_code==304
    assert client.get(url,{'date':week_seed.isoformat()}).status_code==400
    with patch('hawatch.api.v1.week_views.build_week',side_effect=RuntimeError('provider must never be used on hit')):
        assert APIClient().get(url).content==first.content

def test_cache_invalidation_follows_committed_data(week_seed,django_capture_on_commit_callbacks):
    client=APIClient();url='/api/v1/points/tochal/forecast/week/'
    old=client.get(url)
    with django_capture_on_commit_callbacks(execute=True):
        point=WeatherPoint.objects.get(slug='tochal');point.page_name='توچال آزمایشی';point.save()
    updated=client.get(url)
    assert updated['X-Hawatch-Cache']=='MISS' and updated['ETag']!=old['ETag']

def test_route_week_uses_existing_pace_rounding_and_midnight_matching(week_seed):
    body=build_week('route','tochal-darband',week_seed)
    assert all(row['condition'] for row in body['records'])
    route=Route.objects.get(slug='tochal-darband')
    points=list(route.points.all())
    assert len(body['plans'])==8*24*3
    assert len(body['records'])<len(body['plans'])*len(points)
    for speed,label in [('slow','آرام'),('medium','متوسط'),('fast','سریع')]:
        assert body['offsets'][speed]==[paced_duration_minutes(p.cumulative_minutes,label) for p in points]
        for day,hour in [(0,0),(0,23),(7,23)]:
            for i,index in enumerate(body['plans'][f'{day}:{speed}:{hour}']['records']):
                assert index is not None
                row=body['records'][index]
                target=localize_dt(week_seed+timedelta(days=day),hour)+timedelta(minutes=body['offsets'][speed][i])
                from datetime import datetime
                assert abs(datetime.fromisoformat(row['forecast_at'])-target)<=timedelta(minutes=90)
                assert ForecastRecord.objects.filter(weather_point=points[i].weather_point,forecast_at=datetime.fromisoformat(row['forecast_at'])).exists()

def test_precipitation_uses_preceding_hour_and_incomplete_is_not_zero(week_seed):
    point=WeatherPoint.objects.get(slug='tochal');start=localize_dt(week_seed,0)
    rows=list(ForecastRecord.objects.filter(weather_point=point,forecast_at__gte=start,forecast_at__lte=start+timedelta(hours=6)).order_by('forecast_at'))
    assert len(rows)==7
    for i,row in enumerate(rows):row.precipitation_mm=i;row.temperature_c=i;row.apparent_temperature_c=i;row.wind_speed_kmh=i;row.wind_gust_kmh=i*2
    six=aggregate(rows,start,6)
    assert six['rain']==21 and six['actual']==2.5 and six['min']==0 and six['max']==5
    assert six['wind']==5 and six['gust']==10
    assert aggregate(rows,start,1)['rain']==1
    assert aggregate(rows[:-1],start,6)['rain'] is None
    assert aggregate(rows[:-1],start,6)['complete'] is False

def test_equipment_explains_weather_and_never_infers_technical_terrain(week_seed):
    row=ForecastRecord.objects.filter(weather_point__slug='tochal').first()
    row.apparent_temperature_c=-15;row.wind_speed_kmh=40;row.wind_gust_kmh=70;row.precipitation_mm=2;row.snowfall_cm=1;row.uv_index=5
    items=suggest_equipment([row]);keys={i['id'] for i in items}
    assert {'hardshell','down-mittens','balaclava','goggles','uv-glasses'}<=keys
    assert not {'windstopper','poncho','boots','water','backpack','rope','ice-axe','crampons'} & keys
    assert all(i['reason'] and i['evidence'][0]['point']==row.weather_point_id for i in items)

def test_pending_and_missing_weather_never_invent_arrivals_or_readings(week_seed):
    route=Route.objects.get(slug='tochal-darband');route.timing_status='pending';route.save()
    body=build_week('route',route.slug,week_seed)
    assert body['timing_pending'] and all(not plan['records'] for plan in body['plans'].values())

@pytest.mark.parametrize('hour',[True,1.5,'01:30',24,-1])
def test_short_links_reject_non_hourly_starts(week_seed,hour):
    assert APIClient().post('/api/v1/shares/',{'route':'tochal-darband','date':week_seed.isoformat(),'start_hour':hour,'speed':'medium'},format='json').status_code==400

def test_short_link_retains_settings_but_past_date_redirects_to_today(week_seed):
    client=APIClient();created=client.post('/api/v1/shares/',{'route':'tochal-darband','date':week_seed.isoformat(),'start_hour':23,'speed':'slow'},format='json')
    assert created.status_code==201
    path=created.json()['path'];assert len(path)<20 and '?' not in path
    plan=SharedRoutePlan.objects.get(code=path.split('/')[-1]);assert 29<=(plan.expires_at-timezone.now()).days<=30
    assert client.get(path)['Location'].endswith('start_time=23%3A00&speed=slow')
    plan.date=week_seed-timedelta(days=14);plan.save()
    target=client.get(path)
    assert 'date='+week_seed.isoformat() in target['Location'] and 'past_program=1' in target['Location']
    assert target['Cache-Control']=='no-store'
    plan.expires_at=timezone.now()-timedelta(seconds=1);plan.save()
    assert client.get(path).status_code==404

def test_route_descent_applies_only_matching_canonical_chain(week_seed):
    from django.core.management import call_command
    call_command('apply_route_descent')
    route=Route.objects.get(slug='tochal-darband')
    assert route.descent_m is not None and route.descent_m>=0
    assert route.descent_evidence['source_sha256']
    payload=APIClient().get('/api/v1/routes/tochal-darband/forecast/week/').json()
    assert payload['subject']['descent_m']==route.descent_m
    distances=[p['distance_km'] for p in payload['points']]
    assert distances==[0,1.26,5.11,7.93,9.73,10.26]
    assert all(b>a for a,b in zip(distances,distances[1:]))
    # Existing complete profiles are curated data and must survive reapplication.
    points=list(route.points.order_by('sort_order'))
    for point in points[1:]:point.segment_distance_m=1234;point.save(update_fields=['segment_distance_m'])
    call_command('apply_route_descent')
    assert list(route.points.order_by('sort_order').values_list('segment_distance_m',flat=True))[1:]==[1234]*5
    assert Route.objects.get(slug='tochal-shahrestanak').descent_m is None


def test_cache_schema_isolates_payload_changes_but_ui_releases_share_cache(settings):
    from hawatch.api.v1.week_views import cached_week
    from django.test import override_settings
    import json
    cache.clear()
    legacy={"last_generated_at":None,"subject":{"slug":"tochal-darband"}}
    current={"last_generated_at":None,"subject":{"slug":"tochal-darband","descent_m":0}}
    today=now_tehran().date()
    with patch('hawatch.api.v1.week_views.WEEK_CACHE_SCHEMA','previous-schema'),patch('hawatch.api.v1.week_views.build_week',return_value=legacy):
        cached_week('route','tochal-darband',today)
    with override_settings(HAWATCH_ASSET_VERSION='new-worker'),patch('hawatch.api.v1.week_views.build_week',return_value=current) as build:
        (body,_),status=cached_week('route','tochal-darband',today)
        assert status=='MISS' and json.loads(body)['subject']['descent_m']==0
        assert cached_week('route','tochal-darband',today)[1]=='HIT'
        assert build.call_count==1
    with override_settings(HAWATCH_ASSET_VERSION='next-ui-release'),patch('hawatch.api.v1.week_views.build_week') as build:
        assert cached_week('route','tochal-darband',today)[1]=='HIT'
        build.assert_not_called()


def test_reapplying_unchanged_descent_preserves_weather_revision(week_seed,django_capture_on_commit_callbacks):
    from django.core.management import call_command
    from hawatch.api.v1.week_cache import revision
    with django_capture_on_commit_callbacks(execute=True):
        call_command('apply_route_descent')
    before=revision()
    with django_capture_on_commit_callbacks(execute=True):
        call_command('apply_route_descent')
    assert revision()==before
