import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("destinations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Route",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("title", models.CharField(max_length=160)),
                ("subtitle", models.CharField(max_length=255)),
                ("trail_label", models.CharField(max_length=64)),
                ("origin", models.CharField(max_length=64)),
                ("destination_label", models.CharField(max_length=64)),
                ("region", models.CharField(max_length=64)),
                ("distance_km", models.DecimalField(decimal_places=1, max_digits=5)),
                ("ascent_m", models.PositiveIntegerField()),
                ("round_trip_minutes", models.PositiveIntegerField()),
                ("default_start_minutes", models.PositiveIntegerField()),
                ("featured", models.BooleanField(default=False)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("origin_location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
                (
                    "destination",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="routes",
                        to="destinations.destination",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RoutePoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80)),
                ("name", models.CharField(max_length=80)),
                ("elevation_m", models.PositiveIntegerField()),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("base_minutes", models.PositiveIntegerField()),
                ("sort_order", models.PositiveSmallIntegerField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("axis_x", models.PositiveSmallIntegerField(default=10)),
                ("axis_y", models.PositiveSmallIntegerField(default=50)),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
                (
                    "destination",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="route_points",
                        to="destinations.destination",
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="points",
                        to="routes.route",
                    ),
                ),
            ],
            options={"ordering": ["sort_order"]},
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(fields=["destination", "sort_order"], name="route_dest_sort_idx"),
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(fields=["featured"], name="route_featured_idx"),
        ),
        migrations.AddIndex(
            model_name="route",
            index=django.contrib.postgres.indexes.GistIndex(fields=["origin_location"], name="route_origin_gist"),
        ),
        migrations.AddConstraint(
            model_name="routepoint",
            constraint=models.UniqueConstraint(fields=("route", "sort_order"), name="uniq_route_point_order"),
        ),
        migrations.AddConstraint(
            model_name="routepoint",
            constraint=models.UniqueConstraint(fields=("route", "slug"), name="uniq_route_point_slug"),
        ),
        migrations.AddIndex(
            model_name="routepoint",
            index=models.Index(fields=["route", "sort_order"], name="routepoint_route_sort_idx"),
        ),
        migrations.AddIndex(
            model_name="routepoint",
            index=models.Index(fields=["slug"], name="routepoint_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="routepoint",
            index=models.Index(fields=["destination"], name="routepoint_dest_idx"),
        ),
        migrations.AddIndex(
            model_name="routepoint",
            index=django.contrib.postgres.indexes.GistIndex(fields=["location"], name="routepoint_location_gist"),
        ),
    ]
