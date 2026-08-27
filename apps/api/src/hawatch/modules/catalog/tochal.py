"""Compatibility wrappers for the generic catalog loader."""

from hawatch.modules.catalog.catalog import DEFAULT_CATALOG_FILE, load_catalog_file, seed_catalog

TOCHAL_CATALOG_FILE = DEFAULT_CATALOG_FILE
TOCHAL_ROUTE_SLUGS = {
    "touchal-darband",
    "touchal-welanjak",
    "touchal-kalkchal",
    "touchal-ahar",
    "touchal-shahrestanak",
}


def load_tochal_catalog() -> dict:
    return load_catalog_file(TOCHAL_CATALOG_FILE)


def seed_tochal_catalog(*, catalog: dict | None = None) -> dict:
    return seed_catalog(catalog=catalog)
