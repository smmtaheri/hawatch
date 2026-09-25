from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0021_route_seo_copy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="routepoint",
            name="elevation_m",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
