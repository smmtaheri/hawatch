"""Exercise real cookies, CSRF and Django sessions in one browser cookie jar."""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def browser(settings):
    settings.DEMO_AUTH_ALLOWED_PHONE = "989111111111"
    settings.DEMO_AUTH_FIXED_OTP = "2468"
    get_user_model().objects.create_superuser("isolation-admin", password="local-test-password")
    return APIClient(enforce_csrf_checks=True)


def site_login(client, token=None):
    if token is None:
        assert client.get("/api/v1/auth/csrf/").status_code == 200
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
    response = client.post("/api/v1/auth/login/", {"phone": "09111111111", "code": "2468"}, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    return response


def admin_login(client):
    response = client.get("/admin/login/")
    assert response.status_code == 200
    token = client.cookies[settings.ADMIN_CSRF_COOKIE_NAME].value
    response = client.post("/admin/login/", {"username": "isolation-admin", "password": "local-test-password", "csrfmiddlewaretoken": token, "next": "/admin/"})
    assert response.status_code == 302
    assert settings.ADMIN_SESSION_COOKIE_NAME in response.cookies
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert settings.CSRF_COOKIE_NAME not in response.cookies
    return response


def test_admin_login_does_not_log_in_site_or_rotate_its_csrf(browser):
    browser.get("/api/v1/auth/csrf/")
    site_token = browser.cookies[settings.CSRF_COOKIE_NAME].value
    response = admin_login(browser)
    assert response.cookies[settings.ADMIN_SESSION_COOKIE_NAME]["path"] == "/admin/"
    assert response.cookies[settings.ADMIN_SESSION_COOKIE_NAME]["httponly"]
    assert response.cookies[settings.ADMIN_CSRF_COOKIE_NAME]["path"] == "/admin/"
    assert browser.cookies[settings.CSRF_COOKIE_NAME].value == site_token
    assert browser.get("/admin/").status_code == 200
    assert browser.get("/api/v1/auth/me/").json() == {"authenticated": False}
    site_response = site_login(browser, site_token)
    assert site_response.cookies[settings.SESSION_COOKIE_NAME]["path"] == "/"
    assert browser.cookies[settings.SESSION_COOKIE_NAME].value != browser.cookies[settings.ADMIN_SESSION_COOKIE_NAME].value


def test_site_logout_invalidates_peer_session_but_leaves_admin_logged_in(browser):
    admin_login(browser)
    site_login(browser)
    peer = APIClient()
    peer.cookies[settings.SESSION_COOKIE_NAME] = browser.cookies[settings.SESSION_COOKIE_NAME].value
    assert peer.get("/api/v1/auth/me/").json()["authenticated"]
    token = browser.cookies[settings.CSRF_COOKIE_NAME].value
    response = browser.post("/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert response.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == 0
    assert settings.ADMIN_SESSION_COOKIE_NAME not in response.cookies
    assert browser.get("/api/v1/auth/me/").json() == {"authenticated": False}
    assert peer.get("/api/v1/auth/me/").json() == {"authenticated": False}
    assert browser.get("/admin/").status_code == 200


def test_site_login_and_admin_logout_leave_site_session_and_admin_form_token_independent(browser):
    admin_login(browser)
    admin_token = browser.cookies[settings.ADMIN_CSRF_COOKIE_NAME].value
    site_login(browser)
    assert browser.cookies[settings.ADMIN_CSRF_COOKIE_NAME].value == admin_token
    response = browser.post("/admin/logout/", {"csrfmiddlewaretoken": admin_token})
    assert response.status_code == 200
    assert response.cookies[settings.ADMIN_SESSION_COOKIE_NAME]["max-age"] == 0
    assert response.cookies[settings.ADMIN_SESSION_COOKIE_NAME]["path"] == "/admin/"
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert browser.get("/admin/").status_code == 302
    assert browser.get("/api/v1/auth/me/").json()["authenticated"]


def test_admin_never_falls_back_to_authenticated_site_cookie(browser):
    staff = get_user_model().objects.get(username="isolation-admin")
    browser.force_login(staff)
    assert browser.get("/api/v1/auth/me/").json()["authenticated"]
    assert browser.get("/admin/").status_code == 302


def test_legacy_shared_cookie_cannot_restore_site_or_admin_session(browser):
    browser.force_login(get_user_model().objects.get(username="isolation-admin"))
    browser.cookies["sessionid"] = browser.cookies[settings.SESSION_COOKIE_NAME].value
    del browser.cookies[settings.SESSION_COOKIE_NAME]
    assert browser.get("/api/v1/auth/me/").json() == {"authenticated": False}
    assert browser.get("/admin/").status_code == 302


def test_csrf_tokens_are_not_interchangeable(browser):
    admin_login(browser)
    site_login(browser)
    admin_token = browser.cookies[settings.ADMIN_CSRF_COOKIE_NAME].value
    site_token = browser.cookies[settings.CSRF_COOKIE_NAME].value
    assert browser.post("/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=admin_token).status_code == 403
    assert browser.post("/admin/logout/", {"csrfmiddlewaretoken": site_token}).status_code == 403
    assert browser.get("/api/v1/auth/me/").json()["authenticated"]
    assert browser.get("/admin/").status_code == 200
