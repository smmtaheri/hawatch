"""Independent staging runtime. Never connect this settings module to production."""
from .production import *  # noqa: F403

HAWATCH_NEW_DESIGN = True
HAWATCH_QA_NOINDEX = True
DEMO_DATA_ENABLED = False
HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY = False
SESSION_COOKIE_NAME = "hawatch_qa_site_session"
ADMIN_SESSION_COOKIE_NAME = "hawatch_qa_admin_session"
CSRF_COOKIE_NAME = "hawatch_qa_site_csrf"
ADMIN_CSRF_COOKIE_NAME = "hawatch_qa_admin_csrf"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
STAGE_ORIGIN = env("HAWATCH_STAGE_ORIGIN").rstrip("/")  # noqa: F405
SESSION_COOKIE_SECURE = STAGE_ORIGIN.startswith("https://")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = [STAGE_ORIGIN]
MIDDLEWARE = ["hawatch.common.qa_preview.NoIndexMiddleware", *MIDDLEWARE]  # noqa: F405

if DATABASES["default"]["NAME"] != "hawatch_stage" or DATABASES["default"]["HOST"] != "stage-postgres":
    raise RuntimeError("Stage requires its isolated stage-postgres/hawatch_stage database")
