from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0018_weatherpoint_seo_copy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="weatherpoint",
            name="elevation_m",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="forecastpointresolution",
            name="requested_elevation_m",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
