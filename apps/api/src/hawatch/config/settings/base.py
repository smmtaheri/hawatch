import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[4]
SRC_DIR = BASE_DIR / "src"
FIXTURES_DIR = BASE_DIR / "fixtures"


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-local-placeholder")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [item.strip() for item in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if item.strip()]

TIME_ZONE = env("HAWATCH_TIMEZONE", "Asia/Tehran")
LANGUAGE_CODE = "fa"
USE_I18N = True
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.postgres",
    "rest_framework",
    "corsheaders",
    "hawatch.modules.catalog",
    "hawatch.modules.destinations",
    "hawatch.modules.routes",
    "hawatch.modules.forecasts",
    "hawatch.jobs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "hawatch.common.observability.RequestMetricsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hawatch.config.urls"
WSGI_APPLICATION = "hawatch.config.wsgi.application"
ASGI_APPLICATION = "hawatch.config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("POSTGRES_DB", "hawatch"),
        "USER": env("POSTGRES_USER", "hawatch"),
        "PASSWORD": env("POSTGRES_PASSWORD", "hawatch"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 10},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "hawatch.common.errors.api_exception_handler",
}

CORS_ALLOWED_ORIGINS = [
    item.strip()
    for item in env(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]
CORS_ALLOW_CREDENTIALS = False

DEMO_DATA_ENABLED = env_bool("DEMO_DATA_ENABLED", True)
DEMO_SEED_VERSION = env("DEMO_SEED_VERSION", "hawatch-demo-v1")
HAWATCH_SCHEMA_VERSION = "1"
REDIS_URL = os.environ.get("REDIS_URL", "")
WEATHER_PROXY_URL = os.environ.get("WEATHER_PROXY_URL", "")
OPEN_METEO_BASE_URL = env("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_BATCH_SIZE = int(env("OPEN_METEO_BATCH_SIZE", "100"))
OPEN_METEO_FORECAST_DAYS = int(env("OPEN_METEO_FORECAST_DAYS", "7"))
OPEN_METEO_PAST_DAYS = int(env("OPEN_METEO_PAST_DAYS", "0"))
FORECAST_STALE_AFTER_HOURS = int(env("FORECAST_STALE_AFTER_HOURS", "7"))

# Observability is intentionally configured through environment variables. The
# actual token/password values are supplied by Compose secrets or a local .env.
OBSERVABILITY_SERVICE_NAME = env("HAWATCH_SERVICE_NAME", "hawatch-api")
OBSERVABILITY_ENVIRONMENT = env("HAWATCH_ENVIRONMENT", "local")
HAWATCH_LOG_DIR = Path(env("HAWATCH_LOG_DIR", "/var/log/hawatch"))
HAWATCH_LOG_FILE = env("HAWATCH_LOG_FILE", str(HAWATCH_LOG_DIR / "api.jsonl"))
HAWATCH_RETENTION_DAYS = int(env("HAWATCH_RETENTION_DAYS", "7"))
METRICS_REQUIRE_AUTH = env_bool("METRICS_REQUIRE_AUTH", True)
METRICS_TOKEN_FILE = env("HAWATCH_METRICS_TOKEN_FILE", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "hawatch_json": {
            "()": "hawatch.common.observability.JsonFormatter",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "hawatch_json",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
        "file_json": {
            "class": "hawatch.common.observability.SafeTimedRotatingFileHandler",
            "formatter": "hawatch_json",
            "level": "INFO",
            "filename": HAWATCH_LOG_FILE,
            "when": "midnight",
            "interval": 1,
            "backupCount": 6,
            "encoding": "utf-8",
            "utc": True,
        },
    },
    "loggers": {
        "hawatch": {
            "handlers": ["console_json", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": ["console_json", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console_json", "file_json"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console_json", "file_json"],
        "level": "INFO",
    },
}

SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
