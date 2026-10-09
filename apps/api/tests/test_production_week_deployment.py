from pathlib import Path


def test_production_week_deploy_enables_shared_cache_and_matching_asset_versions():
    root=Path(__file__).resolve().parents[3]
    compose=(root/'infra/compose/compose.yaml').read_text()
    script=(root/'scripts/deploy.sh').read_text()
    assert compose.count('REDIS_URL: redis://redis:6379/0')==2
    assert compose.count('OPEN_METEO_FORECAST_DAYS: ${OPEN_METEO_FORECAST_DAYS:-10}')==2
    assert 'VITE_ASSET_VERSION: ${HAWATCH_ASSET_VERSION:-local}' in compose
    assert compose.count('HAWATCH_ASSET_VERSION: ${HAWATCH_ASSET_VERSION:-local}')==2
    assert 'profiles: ["cache"]' not in compose
    assert '"--maxmemory", "128mb", "--maxmemory-policy", "allkeys-lru"' in compose
    assert 'set_env_value OPEN_METEO_FORECAST_DAYS 10' in script
    assert 'wait_for_healthy redis' in script
    assert 'exec -T api python manage.py apply_route_descent' in script
    assert script.index('sync_catalog --apply')<script.index('manage.py apply_route_descent')<script.index('manage.py warm_week_cache')
    assert 'ingest manage.py ingest_open_meteo --wait-lock-seconds 900' in script
    assert script.index("load_packaged_catalogs") < script.index("Starting the new release")
