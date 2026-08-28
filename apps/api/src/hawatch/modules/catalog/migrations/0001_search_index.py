from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("destinations", "0003_destination_aliases"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchIndexEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("destination", "destination"), ("point", "point")],
                        max_length=16,
                    ),
                ),
                (
                    "match_kind",
                    models.CharField(
                        choices=[("name", "name"), ("alias", "alias")],
                        default="name",
                        max_length=8,
                    ),
                ),
                ("normalized_term", models.CharField(max_length=160)),
                ("display_label", models.CharField(max_length=120)),
                ("display_hint", models.CharField(blank=True, default="", max_length=160)),
                ("destination_slug", models.CharField(blank=True, default="", max_length=80)),
                ("weather_point_slug", models.CharField(blank=True, default="", max_length=96)),
                ("rank", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["normalized_term", "rank"], name="search_term_rank_idx"),
                    models.Index(fields=["kind", "weather_point_slug"], name="search_kind_point_idx"),
                    models.Index(fields=["kind", "destination_slug"], name="search_kind_dest_idx"),
                ],
            },
        ),
    ]
