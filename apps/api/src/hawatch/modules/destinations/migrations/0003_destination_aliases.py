from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("destinations", "0002_disable_auto_spatial_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="destination",
            name="aliases",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
