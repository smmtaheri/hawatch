import json
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import RequestFactory

from hawatch.modules.catalog.seo_pages import _initial_forecast, _render


def test_html_uses_the_same_anonymous_cached_payload_as_the_week_api():
    payload = {"kind":"point","subject":{"slug":"sample"},"days":[],"cache_max_age_seconds":120}
    with patch("hawatch.api.v1.week_views.cached_week", return_value=((json.dumps(payload).encode(),'"etag"'),"HIT")) as cached:
        initial = _initial_forecast("point","sample")
    assert initial["payload"] == payload
    assert cached.call_args.args == ("point","sample",datetime.fromisoformat(initial["rendered_at"]).date())


def test_embedded_weather_is_script_safe_and_html_cache_cannot_keep_it_for_five_minutes(settings):
    settings.HAWATCH_QA_NOINDEX = False
    page = {"kind":"point","title":"آزمایش","headline":"آزمایش","canonical":"https://hawatch.ir/points/sample",
            "initial_forecast":{"payload":{"subject":{"name":"</script><script>bad()</script>"}},"rendered_at":"2026-10-18T12:00:00+03:30"}}
    local = datetime(2026,10,18,23,59,45,tzinfo=ZoneInfo("Asia/Tehran"))
    with patch("hawatch.modules.catalog.seo_pages.now_tehran",return_value=local):
        response = _render(RequestFactory().get("/points/sample"),page=page)
        query = _render(RequestFactory().get("/points/sample?date=2026-10-18"),page=page)
    html = response.content.decode()
    assert 'id="forecast-initial-data" type="application/json"' in html
    assert "<script>bad()" not in html
    assert "\\u003C/script\\u003E" in html
    script = html.split('id="forecast-initial-data" type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(script) == page["initial_forecast"]
    assert '": ' not in script
    assert ', ' not in script
    assert response["Cache-Control"] == "public, max-age=0, s-maxage=15, must-revalidate"
    assert query["Cache-Control"] == "no-cache"
    assert query["X-Robots-Tag"] == "noindex,follow"
