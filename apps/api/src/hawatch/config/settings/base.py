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

ANALYTICS_ATTRIBUTION_ENABLED = env_bool("ANALYTICS_ATTRIBUTION_ENABLED", True)
ANALYTICS_REPORT_TIMEOUT_MS = max(100, min(30000, int(env("ANALYTICS_REPORT_TIMEOUT_MS", "3000"))))

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
    # Historical migration namespace only; 0006 drops its legacy table.
    "hawatch.modules.destinations",
    "hawatch.modules.routes",
    "hawatch.modules.forecasts",
    "hawatch.modules.analytics",
    "hawatch.modules.accounts",
    "hawatch.jobs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "hawatch.common.sessions.AdminCookieIsolationMiddleware",
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
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
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

# Temporary allowlisted login is server-only. Never put its phone or code in
# frontend source, fixtures, or default settings.
DEMO_AUTH_ALLOWED_PHONE = os.environ.get("DEMO_AUTH_ALLOWED_PHONE", "")
DEMO_AUTH_FIXED_OTP = os.environ.get("DEMO_AUTH_FIXED_OTP", "")
AUTH_SESSION_AGE_SECONDS = int(os.environ.get("AUTH_SESSION_AGE_SECONDS", str(30 * 24 * 60 * 60)))
GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "").strip()
# Retire the old shared sessionid/csrftoken cookies; no implicit migration
# can distinguish a legacy admin login from an explicit site login.
SESSION_COOKIE_NAME = "hawatch_site_session"
CSRF_COOKIE_NAME = "hawatch_site_csrf"
ADMIN_SESSION_COOKIE_NAME = "hawatch_admin_session"
ADMIN_CSRF_COOKIE_NAME = "hawatch_admin_csrf"
SESSION_COOKIE_AGE = AUTH_SESSION_AGE_SECONDS
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

DEMO_DATA_ENABLED = env_bool("DEMO_DATA_ENABLED", True)
DEMO_SEED_VERSION = env("DEMO_SEED_VERSION", "hawatch-demo-v1")
HAWATCH_SCHEMA_VERSION = "1"
PUBLIC_SITE_ORIGIN = env("HAWATCH_PUBLIC_ORIGIN", "https://hawatch.ir").rstrip("/")
SITEMAP_ROOT = Path(env("HAWATCH_SITEMAP_ROOT", "/var/lib/hawatch-seo"))
SITEMAP_REFRESH_SECONDS = max(30, int(env("SITEMAP_REFRESH_SECONDS", "300")))
SITEMAP_QUERY_TIMEOUT_MS = max(100, int(env("SITEMAP_QUERY_TIMEOUT_MS", "5000")))
REDIS_URL = os.environ.get("REDIS_URL", "")
SHARED_HTTP_METRICS = env_bool("HAWATCH_SHARED_HTTP_METRICS", True)
HTTP_METRICS_REDIS_KEY = env("HAWATCH_HTTP_METRICS_KEY", "hawatch:http-metrics:v1")
# Proxies are operator-managed and encrypted in PostgreSQL.  The deploy script
# creates this key when absent; leaving it empty is safe until a proxy is active.
WEATHER_PROXY_ENCRYPTION_KEY = os.environ.get("WEATHER_PROXY_ENCRYPTION_KEY", "")
OPEN_METEO_BASE_URL = env("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_BATCH_SIZE = int(env("OPEN_METEO_BATCH_SIZE", "25"))
OPEN_METEO_FORECAST_DAYS = int(env("OPEN_METEO_FORECAST_DAYS", "10"))
OPEN_METEO_PAST_DAYS = int(env("OPEN_METEO_PAST_DAYS", "0"))
OPEN_METEO_RATE_LIMIT_ENABLED = env_bool("OPEN_METEO_RATE_LIMIT_ENABLED", True)
OPEN_METEO_RATE_LIMIT_REDIS_URL = env("OPEN_METEO_RATE_LIMIT_REDIS_URL", "")
OPEN_METEO_RATE_LIMIT_SCOPE = env("OPEN_METEO_RATE_LIMIT_SCOPE", "open-meteo")
OPEN_METEO_REQUEST_INTERVAL_SECONDS = float(env("OPEN_METEO_REQUEST_INTERVAL_SECONDS", "10"))
OPEN_METEO_CALLS_PER_MINUTE = float(env("OPEN_METEO_CALLS_PER_MINUTE", "300"))
OPEN_METEO_CALLS_PER_HOUR = float(env("OPEN_METEO_CALLS_PER_HOUR", "4500"))
OPEN_METEO_CALLS_PER_DAY = float(env("OPEN_METEO_CALLS_PER_DAY", "9000"))
FORECAST_STALE_AFTER_HOURS = int(env("FORECAST_STALE_AFTER_HOURS", "7"))
ANALYTICS_RATE_LIMIT_PER_MINUTE = int(env("ANALYTICS_RATE_LIMIT_PER_MINUTE", "60"))

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

# Public, revisioned week payloads only. Auth/session responses never use this cache.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL,
                       "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1}}} if REDIS_URL else {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "hawatch-week"}}

HAWATCH_ASSET_VERSION = env("HAWATCH_ASSET_VERSION", "")
HAWATCH_FRONTEND_ASSETS_ROOT = env("HAWATCH_FRONTEND_ASSETS_ROOT", "")

HAWATCH_PUBLIC_ASSET_VERSION = env("HAWATCH_PUBLIC_ASSET_VERSION", "") or HAWATCH_ASSET_VERSION
