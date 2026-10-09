import io
import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.conf import settings
from hawatch.modules.forecasts.models import WeatherPoint

pytestmark=pytest.mark.django_db

def test_import_rejects_a_non_stage_database():
    with pytest.raises(CommandError,match='hawatch_stage'):
        call_command('import_stage_data')

def test_import_rejects_accounts_atomically_even_in_stage_settings():
    database=deepcopy(settings.DATABASES)
    database['default']['NAME']='hawatch_stage'
    source=io.StringIO(json.dumps({'stage_snapshot_version':1})+'\n'+json.dumps({'model':'auth.user','pk':100000,'fields':{'username':'must-not-import'}})+'\n')
    with override_settings(DATABASES=database),patch('sys.stdin',source):
        with pytest.raises(CommandError,match='Unexpected model'):
            call_command('import_stage_data')
    assert not WeatherPoint.objects.exists()
