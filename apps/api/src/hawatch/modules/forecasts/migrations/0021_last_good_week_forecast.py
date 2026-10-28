from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0020_weather_warning_inputs")]

    operations = [
        migrations.CreateModel(
            name="LastGoodWeekForecast",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("point", "point"), ("route", "route")], max_length=8)),
                ("slug", models.SlugField(max_length=96)),
                ("schema_version", models.CharField(default="week-2", max_length=16)),
                ("payload", models.BinaryField()),
                ("payload_sha256", models.CharField(max_length=64)),
                ("catalog_signature", models.CharField(max_length=64)),
                ("updated_at", models.DateTimeField()),
                ("source_label", models.CharField(blank=True, default="", max_length=160)),
                ("stored_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="lastgoodweekforecast",
            constraint=models.UniqueConstraint(fields=("kind", "slug"), name="uniq_last_good_week_subject"),
        ),
        migrations.AddIndex(
            model_name="lastgoodweekforecast",
            index=models.Index(fields=["updated_at"], name="lastgood_week_updated_idx"),
        ),
    ]
