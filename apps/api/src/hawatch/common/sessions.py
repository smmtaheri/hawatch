"""Keep Django admin cookies separate from the public site's session/CSRF."""
from django.conf import settings


class AdminCookieIsolationMiddleware:
    """Adapt cookies around Django's unchanged session and CSRF middleware.

    Only the current request is adapted; global settings are never changed, so
    concurrent admin/API requests cannot switch each other's cookie namespace.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info != "/admin" and not request.path_info.startswith("/admin/"):
            return self.get_response(request)

        pairs = (
            (settings.SESSION_COOKIE_NAME, settings.ADMIN_SESSION_COOKIE_NAME),
            (settings.CSRF_COOKIE_NAME, settings.ADMIN_CSRF_COOKIE_NAME),
        )
        cookies = request.COOKIES.copy()
        for site_name, admin_name in pairs:
            if admin_name in cookies:
                cookies[site_name] = cookies[admin_name]
            else:
                # Never authenticate admin from the site's cookie as a fallback.
                cookies.pop(site_name, None)
        request.COOKIES = cookies

        response = self.get_response(request)
        for site_name, admin_name in pairs:
            if site_name not in response.cookies:
                continue
            cookie = response.cookies.pop(site_name)
            response.cookies[admin_name] = cookie.value
            response.cookies[admin_name].update(cookie)
            response.cookies[admin_name]["path"] = "/admin/"
        return response
