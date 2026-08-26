import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        CreateExtension("postgis"),
        migrations.CreateModel(
            name="Destination",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("tile_name", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=128)),
                ("short_category", models.CharField(max_length=32)),
                ("category", models.CharField(max_length=128)),
                ("category_key", models.CharField(max_length=32)),
                ("region", models.CharField(max_length=64)),
                ("elevation_m", models.PositiveIntegerField()),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("image", models.CharField(max_length=255)),
                ("image_alt", models.CharField(max_length=255)),
                ("popular_order", models.PositiveSmallIntegerField(default=0)),
                ("climate", models.CharField(max_length=32)),
                ("is_popular", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
            ],
        ),
        migrations.AddIndex(
            model_name="destination",
            index=models.Index(fields=["is_popular", "popular_order"], name="destination_is_popu_idx"),
        ),
        migrations.AddIndex(
            model_name="destination",
            index=models.Index(fields=["is_active"], name="destination_is_acti_idx"),
        ),
        migrations.AddIndex(
            model_name="destination",
            index=django.contrib.postgres.indexes.GistIndex(fields=["location"], name="destination_location_gist"),
        ),
    ]
