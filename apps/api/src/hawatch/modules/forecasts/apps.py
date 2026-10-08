from django.apps import AppConfig


class ForecastsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hawatch.modules.forecasts"
    label = "forecasts"
    verbose_name = "Forecasts"

    def ready(self):
        from hawatch.api.v1.week_cache import register_signals
        register_signals()
