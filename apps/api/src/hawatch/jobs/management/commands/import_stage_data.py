import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import connection, transaction
from django.core.management.color import no_style
from django.conf import settings
from django.apps import apps
from hawatch.api.v1.week_cache import invalidate_week_cache

ALLOWED = {"forecasts.weatherpoint", "routes.route", "routes.routepoint",
           "forecasts.forecastsnapshot", "forecasts.forecastpointresolution",
           "forecasts.forecastrecord", "forecasts.forecastdaily", "catalog.searchindexentry"}

class Command(BaseCommand):
    help = "Stream public catalog/weather into an empty isolated stage database"
    def handle(self, **options):
        if settings.DATABASES["default"]["NAME"] != "hawatch_stage":
            raise CommandError("Only hawatch_stage is allowed")
        if apps.get_model("forecasts.WeatherPoint").objects.exists():
            raise CommandError("Refusing to overwrite a populated stage catalog")
        try:
            header=json.loads(sys.stdin.readline())
        except (ValueError, TypeError) as error:
            raise CommandError("Empty or malformed stage snapshot") from error
        if header.get("stage_snapshot_version") != 1:
            raise CommandError("Unknown snapshot format")
        models, batch = set(), []
        model = None
        def flush():
            if not batch: return
            # Import trusted DB rows verbatim, including their original timestamps.
            # bulk_create normally rewrites auto_now/add; temporarily disable those
            # hooks only in this isolated import process, then restore on failure too.
            clocks=[(f,f.auto_now,f.auto_now_add) for f in model._meta.local_fields if hasattr(f,'auto_now')]
            try:
                for field,_,_ in clocks: field.auto_now=field.auto_now_add=False
                model.objects.bulk_create(batch,batch_size=500)
            finally:
                for field,auto,add in clocks: field.auto_now,field.auto_now_add=auto,add
            batch.clear()
        with transaction.atomic():
            for line in sys.stdin:
                if not line.strip(): continue
                for obj in serializers.deserialize("json", "["+line.strip()+"]"):
                    if obj.object._meta.label_lower not in ALLOWED:
                        raise CommandError("Unexpected model in staging snapshot")
                    incoming=type(obj.object)
                    if model is not incoming: flush(); model=incoming
                    models.add(model);batch.append(obj.object)
                    if len(batch)>=500: flush()
            flush()
            with connection.cursor() as cursor:
                for sql in connection.ops.sequence_reset_sql(no_style(),list(models)):
                    cursor.execute(sql)
            invalidate_week_cache()
        self.stdout.write("Imported public weather/catalog only; no accounts or secrets")
