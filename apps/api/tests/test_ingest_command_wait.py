from types import SimpleNamespace
from unittest.mock import patch
import pytest
from django.core.management import call_command, CommandError
from hawatch.integrations.weather.ingest import IngestLockError

COMMAND='hawatch.jobs.management.commands.ingest_open_meteo'


def test_waits_for_existing_ingest_then_ingests_and_warms_once():
    snapshot=SimpleNamespace(pk=1,status='success',freshness='fresh',point_count=1,catalog_version='test',checksum='abc')
    with patch(f'{COMMAND}.OpenMeteoProvider'), patch(f'{COMMAND}.ingest_active_catalog', side_effect=[IngestLockError('busy'),snapshot]) as ingest, patch(f'{COMMAND}.time.monotonic',return_value=0), patch(f'{COMMAND}.time.sleep') as sleep, patch('django.core.management.call_command') as warm:
        call_command('ingest_open_meteo',wait_lock_seconds=10)
    assert ingest.call_count==2
    sleep.assert_called_once_with(5)
    warm.assert_called_once_with('warm_week_cache')


def test_busy_lock_times_out_without_fetching_twice():
    with patch(f'{COMMAND}.OpenMeteoProvider'), patch(f'{COMMAND}.ingest_active_catalog',side_effect=IngestLockError('busy')) as ingest, patch(f'{COMMAND}.time.monotonic',side_effect=[0,11]), patch(f'{COMMAND}.time.sleep') as sleep:
        with pytest.raises(CommandError,match='still running'):
            call_command('ingest_open_meteo',wait_lock_seconds=10)
    assert ingest.call_count==1
    sleep.assert_not_called()


def test_provider_errors_are_not_retried_or_hidden():
    with patch(f'{COMMAND}.OpenMeteoProvider'), patch(f'{COMMAND}.ingest_active_catalog',side_effect=RuntimeError('provider failed')) as ingest, patch(f'{COMMAND}.time.sleep') as sleep:
        with pytest.raises(RuntimeError,match='provider failed'):
            call_command('ingest_open_meteo',wait_lock_seconds=10)
    assert ingest.call_count==1
    sleep.assert_not_called()
