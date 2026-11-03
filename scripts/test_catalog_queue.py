"""Offline regressions for queue accounting and publication transitions."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("catalog_queue", Path(__file__).with_name("catalog_queue.py"))
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


def entry(key, *, status="queued", site="havakouh", priority="P2", rank=100):
    row = {
        "id": key, "name": "مقصد نمونه", "region": "استان نمونه",
        "priority": priority, "rank": rank, "status": status,
        "note": "بررسی هویت مقصد نمونه",
        "sources": [{"site": site, "key": key, "label": "نمونه", "regions": [], "url": f"https://{site}.com/"}],
    }
    if status in queue.VERIFIED_STATUSES:
        row.update(hawatch_slugs=[key.lower()], verified_at="2026-01-01T00:00:00Z", match_basis="تطبیق صریح")
    return row


def ledger(*entries):
    return {
        "schema_version": 1,
        "production_snapshot": {"checked_at": "2026-01-01T00:00:00Z"},
        "sources": {
            site: {"url": f"https://{site}.com/", "inventory_keys": [ref["key"] for e in entries for ref in e["sources"] if ref["site"] == site], "excluded": []}
            for site in queue.SITES
        },
        "entries": list(entries),
    }


class CatalogQueueTests(unittest.TestCase):
    def test_source_aliases_count_once_and_inventory_is_lossless(self):
        first = entry("HK-A")
        first["sources"].append(dict(first["sources"][0], key="HK-ALIAS"))
        data = ledger(first, entry("HG-B", site="havagasht"))
        self.assertEqual(queue.validate(data), [])
        self.assertEqual(sum(queue.counts(data).values()), 2)
        self.assertEqual(sum(queue.counts(data, "havakouh").values()), 1)
        lost = deepcopy(data)
        lost["entries"][0]["sources"].pop()
        self.assertTrue(any("inventory coverage mismatch" in e for e in queue.validate(lost)))
        duplicated = deepcopy(data)
        duplicated["entries"].append(deepcopy(first))
        self.assertTrue(any("source item appears in two entries" in e for e in queue.validate(duplicated)))

    def test_foreign_inventory_is_preserved_but_not_selectable(self):
        data = ledger(entry("HK-A"))
        data["sources"]["havakouh"]["inventory_keys"].append("foreign")
        data["sources"]["havakouh"]["excluded"].append({"key": "foreign", "name": "خارج ایران", "reason": "دامنهٔ داخلی"})
        self.assertEqual(queue.validate(data), [])
        self.assertEqual([e["id"] for e in queue.next_entries(data, 10)], ["HK-A"])

    def test_next_is_stable_and_excludes_completed_and_current_work(self):
        data = ledger(
            entry("slow", rank=1), entry("review", status="needs_review", priority="P1", rank=1),
            entry("done", status="published", priority="P1", rank=2),
            entry("working", status="in_progress", priority="P1", rank=3),
            entry("second", site="havagasht", priority="P1", rank=20),
            entry("first", priority="P1", rank=10),
        )
        self.assertEqual([e["id"] for e in queue.next_entries(data, 2)], ["first", "second"])
        self.assertEqual([e["id"] for e in queue.next_entries(data, 10, "havakouh")], ["first", "slow"])
        # Calendar changes don't rewrite editorial rank or selection.
        later = deepcopy(data)
        later["production_snapshot"]["checked_at"] = "2040-12-31T23:59:59Z"
        self.assertEqual(queue.next_entries(data, 2), queue.next_entries(later, 2))

    def test_complete_requires_active_recent_live_evidence_and_keeps_history(self):
        row = entry("HK-A", status="in_progress")
        row["local_track_dir"] = "tracks/example/"
        data = ledger(row)
        snap = {"checked_at": "2026-01-02T00:00:00Z", "points": [{"slug": "canonical", "is_active": False, "seo_indexable": True}], "routes": []}
        before = deepcopy(data)
        with self.assertRaises(ValueError):
            queue.complete(data, "HK-A", "canonical", snap)
        self.assertEqual(data, before)
        snap["points"][0]["is_active"] = True
        snap["checked_at"] = "2025-01-02T00:00:00Z"
        with self.assertRaises(ValueError):
            queue.complete(data, "HK-A", "canonical", snap)
        snap["checked_at"] = "2026-01-02T00:00:00Z"
        snap["routes"] = [
            {"slug": "valid-route", "is_active": True, "target_weather_point__slug": "canonical"},
            {"slug": "inactive-route", "is_active": False, "target_weather_point__slug": "canonical"},
            {"slug": "other-route", "is_active": True, "target_weather_point__slug": "other"},
        ]
        queue.complete(data, "HK-A", "canonical", snap)
        self.assertEqual(queue.validate(data), [])
        self.assertEqual(data["entries"][0]["status"], "published")
        self.assertEqual(data["entries"][0]["route_slugs"], ["valid-route"])
        self.assertEqual(data["entries"][0]["history"][0]["local_track_dir"], "tracks/example/")
        self.assertEqual(queue.next_entries(data, 10), [])

    def test_noindex_point_is_not_misreported_as_independent_destination(self):
        data = ledger(entry("HK-A"))
        queue.complete(data, "HK-A", "support", {"checked_at": "2026-01-02T00:00:00Z", "points": [{"slug": "support", "is_active": True, "seo_indexable": False}]})
        self.assertEqual(data["entries"][0]["status"], "existing_point")
        self.assertEqual(queue.counts(data)["published"], 0)

    def test_two_source_entries_cannot_claim_same_published_entity(self):
        data = ledger(entry("first", status="published"), entry("second", status="published"))
        data["entries"][1]["hawatch_slugs"] = ["first"]
        self.assertTrue(any("merge its source references" in e for e in queue.validate(data)))

    def test_markdown_views_detect_manual_count_drift(self):
        data = ledger(entry("HK-A"), entry("HG-B", site="havagasht"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            queue.write_views(data, root)
            self.assertEqual(queue.write_views(data, root, check=True), [])
            path = root / "docs/catalog-queue.md"
            path.write_text(path.read_text() + "\nwrong manual count\n")
            self.assertEqual(queue.write_views(data, root, check=True), ["docs/catalog-queue.md"])


if __name__ == "__main__":
    unittest.main()
