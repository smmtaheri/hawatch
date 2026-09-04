from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "api").split(",")  # noqa: F405
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Bump the static URL prefix when gateway/CDN caches contain stale assets.
# This keeps an old cached MIME type from masking the current admin styles.
STATIC_URL = "/static-v2/"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://hawatch.ir,https://www.hawatch.ir",
    ).split(",")
    if origin.strip()
]
# The public HTTPS endpoint is terminated by the CDN before reaching the
# gateway. Nginx preserves that forwarded scheme for Django.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
