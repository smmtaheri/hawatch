"""Cache headers for public, non-personalized catalog and page responses."""

PUBLIC_CATALOG_CACHE_CONTROL = (
    "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
)


def mark_public_catalog_response(response):
    """Allow short browser caching and five-minute shared-edge caching."""

    response["Cache-Control"] = PUBLIC_CATALOG_CACHE_CONTROL
    return response
