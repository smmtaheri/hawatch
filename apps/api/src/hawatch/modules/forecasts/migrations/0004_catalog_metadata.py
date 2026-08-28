from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0003_live_daily_forecasts")]

    operations = [
        migrations.AlterField(
            model_name="weatherpoint",
            name="kind",
            field=models.CharField(
                choices=[
                    ("destination", "destination"),
                    ("route_point", "route_point"),
                    ("shared", "shared"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="catalog_version",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="elevation_source",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="status",
            field=models.CharField(
                choices=[
                    ("approved", "approved"),
                    ("provisional", "provisional"),
                    ("unresolved_elevation", "unresolved_elevation"),
                ],
                default="approved",
                max_length=32,
            ),
        ),
    ]

