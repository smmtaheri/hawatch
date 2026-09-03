"""Compatibility wrappers for the generic catalog loader."""

from hawatch.modules.catalog.catalog import (
    DEFAULT_CATALOG_FILE,
    bootstrap_live_catalog_if_empty,
    load_catalog_file,
    seed_catalog,
)

TOCHAL_CATALOG_FILE = DEFAULT_CATALOG_FILE
TOCHAL_ROUTE_SLUGS = {
    "tochal-darband",
    "tochal-velenjak",
    "tochal-kolakchal",
    "tochal-ahar",
    "tochal-shahrestanak",
}


def load_tochal_catalog() -> dict:
    return load_catalog_file(TOCHAL_CATALOG_FILE)


def seed_tochal_catalog(*, catalog: dict | None = None, prune: bool = False, force_adopt: bool = False) -> dict:
    return seed_catalog(catalog=catalog, prune=prune, force_adopt=force_adopt)


def bootstrap_tochal_catalog_if_empty() -> dict | None:
    return bootstrap_live_catalog_if_empty(catalog_file=TOCHAL_CATALOG_FILE)
