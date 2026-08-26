from django.apps import AppConfig


class ForecastsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hawatch.modules.forecasts"
    label = "forecasts"
    verbose_name = "Forecasts"
