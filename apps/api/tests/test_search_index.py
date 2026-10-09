import pytest


@pytest.mark.django_db(transaction=True)
def test_catalog_publish_invalidates_the_redis_search_payload(seeded):
    from django.core.cache import cache

    from hawatch.modules.catalog.search import rebuild_search_index
    from hawatch.modules.catalog.search_payload import SEARCH_INDEX_CACHE_KEY, search_index_payload
    from hawatch.modules.forecasts.models import WeatherPoint

    cache.delete(SEARCH_INDEX_CACHE_KEY)
    before = search_index_payload()
    WeatherPoint.objects.filter(slug="tochal").update(page_name="قلهٔ توچال تازه")
    rebuild_search_index()
    after = search_index_payload()

    assert after["revision"] != before["revision"]
    assert any(point["label"] == "قلهٔ توچال تازه" for point in after["points"])


@pytest.mark.django_db
def test_search_index_is_compact_public_and_edge_cacheable(api_client, seeded):
    response = api_client.get("/api/v1/catalog/search-index/")

    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    assert response["ETag"]
    payload = response.json()
    assert payload["revision"]
    assert any(point["slug"] == "tochal" for point in payload["points"])
    assert any(route["slug"] == "tochal-darband" for route in payload["routes"])
    assert set(payload["points"][0]) == {
        "slug", "label", "terms", "hint", "href", "category_key", "place_type", "primary",
    }

    not_modified = api_client.get(
        "/api/v1/catalog/search-index/",
        HTTP_IF_NONE_MATCH=response["ETag"],
    )
    assert not_modified.status_code == 304
    assert not_modified["ETag"] == response["ETag"]
