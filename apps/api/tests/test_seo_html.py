from django.contrib.gis.geos import Point

from hawatch.modules.forecasts.models import WeatherPoint
from hawatch.modules.routes.models import Route


def test_home_has_semantic_initial_html_and_clean_canonical(api_client, seeded):
    response = api_client.get("/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "<title>هواچ | هوای نقطه، برنامهٔ مسیر</title>" in body
    assert 'name="description" content="هواچ؛ هوای نقاط و برنامهٔ مسیر."' in body
    assert 'rel="canonical" href="https://hawatch.ir/"' in body
    assert 'name="robots" content="index,follow"' in body
    assert "<h1>هوای مسیرت را ببین</h1>" in body
    assert 'src="/assets/hawatch.js"' in body
    assert response["X-Robots-Tag"] == "index,follow"


def test_point_html_is_catalog_driven_and_query_is_noindex(api_client, seeded):
    point = WeatherPoint.objects.create(
        slug="seo-test-ridge",
        name="یال آزمایشی",
        page_name="یال آزمایشی تهران",
        identity_summary="یک عارضهٔ مستقل برای کنترل رندر اولیهٔ هواچ.",
        category="یال کوهستانی",
        region="تهران",
        elevation_m=2500,
        location=Point(51.5, 35.8, srid=4326),
        seo_indexable=True,
        is_active=True,
    )

    response = api_client.get(f"/points/{point.slug}")

    assert response.status_code == 200
    body = response.content.decode()
    assert "<title>هوای یال آزمایشی تهران | هواچ</title>" in body
    assert 'name="description" content="پیش‌بینی هوا و وضعیت مسیر برای یال آزمایشی تهران در هواچ."' in body
    assert 'rel="canonical" href="https://hawatch.ir/points/seo-test-ridge"' in body
    assert 'name="robots" content="index,follow"' in body
    assert "<h1>یال آزمایشی تهران</h1>" in body
    assert "یک عارضهٔ مستقل برای کنترل رندر اولیهٔ هواچ." in body

    bot_response = api_client.get(f"/points/{point.slug}", HTTP_USER_AGENT="Googlebot")
    assert bot_response.status_code == 200
    assert bot_response.content == response.content

    query_response = api_client.get(f"/points/{point.slug}?date=2026-09-04&period=morning")
    query_body = query_response.content.decode()
    assert query_response.status_code == 200
    assert 'name="robots" content="noindex,follow"' in query_body
    assert 'rel="canonical" href="https://hawatch.ir/points/seo-test-ridge"' in query_body
    assert "?date=" not in query_body
    assert query_response["X-Robots-Tag"] == "noindex,follow"

    trailing_response = api_client.get(f"/points/{point.slug}/")
    assert trailing_response.status_code == 200
    assert 'rel="canonical" href="https://hawatch.ir/points/seo-test-ridge"' in trailing_response.content.decode()


def test_route_html_is_database_driven(api_client, seeded):
    route = Route.objects.create(
        slug="seo-test-route",
        title="مسیر آزمایشی تهران",
        subtitle="مسیر نمونه برای کنترل HTML اولیه.",
        trail_label="مسیر پیاده‌روی",
        origin="مبدأ آزمایشی",
        target_label="مقصد آزمایشی",
        region="تهران",
        distance_km="12.5",
        ascent_m=900,
        origin_location=Point(51.4, 35.7, srid=4326),
        is_active=True,
    )

    response = api_client.get(f"/routes/{route.slug}")

    assert response.status_code == 200
    body = response.content.decode()
    assert "<title>هوای مسیر آزمایشی تهران | هواچ</title>" in body
    assert 'rel="canonical" href="https://hawatch.ir/routes/seo-test-route"' in body
    assert '<h1>مسیر آزمایشی تهران</h1>' in body
    assert "مبدأ آزمایشی" in body
    assert "مقصد آزمایشی" in body
    assert "12.5 کیلومتر" in body


def test_invalid_public_slug_is_a_real_noindex_404(api_client, seeded):
    response = api_client.get("/points/not-a-real-point")

    assert response.status_code == 404
    body = response.content.decode()
    assert "<h1>نقطه پیدا نشد</h1>" in body
    assert 'name="robots" content="noindex,follow"' in body
    assert 'rel="canonical"' not in body
    assert response["X-Robots-Tag"] == "noindex,follow"
