import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0004_catalog_metadata")]

    operations = [
        migrations.AlterField(
            model_name="weatherpoint",
            name="route_point",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="legacy_weather_point",
                to="routes.routepoint",
            ),
        )
    ]

