from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("destinations", "0004_destination_weather_point"),
    ]

    operations = [
        migrations.AlterField(
            model_name="destination",
            name="is_popular",
            field=models.BooleanField(default=False),
        ),
    ]
