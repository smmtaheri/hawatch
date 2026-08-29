from django.db import migrations, models


def mark_existing_fixture_rows(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    WeatherPoint.objects.filter(data_mode="live").exclude(slug__startswith="dest:").update(
        fixture_managed=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0011_search_aliases"),
    ]

    operations = [
        migrations.AddField(
            model_name="weatherpoint",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="ingest_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="fixture_managed",
            field=models.BooleanField(
                default=False,
                help_text="True when created/updated from a JSON catalog import; prune only removes fixture_managed rows.",
            ),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=models.Index(fields=["is_active", "ingest_enabled"], name="weatherpoint_ingest_idx"),
        ),
        migrations.RunPython(mark_existing_fixture_rows, migrations.RunPython.noop),
    ]
