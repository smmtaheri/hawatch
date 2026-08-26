from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "api").split(",")  # noqa: F405
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
