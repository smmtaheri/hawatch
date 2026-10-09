"""Run in the existing production image: SELECT-only JSONL, bounded memory."""
from django.apps import apps
from django.core import serializers
from django.db import connection, transaction
import sys
labels = ["forecasts.WeatherPoint", "routes.Route", "routes.RoutePoint",
          "forecasts.ForecastSnapshot", "forecasts.ForecastPointResolution",
          "forecasts.ForecastRecord", "forecasts.ForecastDaily", "catalog.SearchIndexEntry"]
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    sys.stdout.write('{"stage_snapshot_version":1}\n')
    for label in labels:
        model = apps.get_model(label)
        omitted = {"raw_response", "notes"} if label == "forecasts.ForecastSnapshot" else set()
        fields = [f.name for f in model._meta.fields if f.name not in omitted]
        rows = model.objects.order_by("pk").defer(*omitted)
        for row in rows.iterator(chunk_size=500):
            sys.stdout.write(serializers.serialize("json", [row], fields=fields)[1:-1] + "\n")
