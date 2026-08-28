from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("forecasts", "0002_disable_auto_spatial_indexes")]

    operations = [
        migrations.CreateModel(
            name="ForecastDaily",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("forecast_date", models.DateField()),
                ("sunrise_at", models.DateTimeField(blank=True, null=True)),
                ("sunset_at", models.DateTimeField(blank=True, null=True)),
                ("generated_at", models.DateTimeField()),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("source", models.CharField(default="hawatch-demo", max_length=32)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
                ("provider", models.CharField(default="demo", max_length=32)),
                (
                    "weather_point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_forecasts",
                        to="forecasts.weatherpoint",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="forecastdaily",
            constraint=models.UniqueConstraint(
                fields=("weather_point", "forecast_date", "seed_version"),
                name="uniq_daily_point_date_seed",
            ),
        ),
        migrations.AddIndex(
            model_name="forecastdaily",
            index=models.Index(fields=["weather_point", "forecast_date"], name="daily_point_date_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastdaily",
            index=models.Index(fields=["generated_at"], name="daily_generated_idx"),
        ),
    ]

