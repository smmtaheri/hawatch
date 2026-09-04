from django.db import migrations, models

import hawatch.common.crypto


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0016_unify_point_profile"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeatherProxy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                (
                    "country_code",
                    models.CharField(
                        help_text="Two-letter ISO country code, for example CA or US.",
                        max_length=2,
                    ),
                ),
                (
                    "proxy_url",
                    hawatch.common.crypto.EncryptedTextField(
                        help_text="SOCKS5/SOCKS5H URI; encrypted at rest.",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_failure_at", models.DateTimeField(blank=True, null=True)),
                ("failure_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "pk"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["name", "country_code"],
                        name="uniq_weatherproxy_name_country",
                    ),
                ],
                "indexes": [
                    models.Index(
                        fields=["is_active", "sort_order"],
                        name="weatherproxy_active_order_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="WeatherProxyRotation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(default="weather", max_length=32, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "last_proxy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="rotation_cursors",
                        to="forecasts.weatherproxy",
                    ),
                ),
            ],
        ),
    ]
