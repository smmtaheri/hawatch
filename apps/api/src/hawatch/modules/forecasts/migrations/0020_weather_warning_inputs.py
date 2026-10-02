from django.db import migrations, models


def mark_legacy_visibility(apps, schema_editor):
    # Old normalization substituted 10 km when missing. It is not possible to
    # distinguish those records without the provider archive: never assume it.
    Record = apps.get_model("forecasts", "ForecastRecord")
    Record.objects.using(schema_editor.connection.alias).all().update(fields_unavailable=["visibility_km"])


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0019_signed_weather_point_elevations")]
    operations = [
        migrations.AddField(model_name="forecastrecord", name="wmo_code",
                            field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="forecastrecord", name="relative_humidity_pct",
                            field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="forecastrecord", name="fields_unavailable",
                            field=models.JSONField(blank=True, default=list)),
        migrations.AlterField(model_name="forecastrecord", name="visibility_km",
                              field=models.DecimalField(decimal_places=2, max_digits=6)),
        migrations.RunPython(mark_legacy_visibility, migrations.RunPython.noop),
    ]
