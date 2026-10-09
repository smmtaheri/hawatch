"""Offline regression checks; synthetic GPX, no server or private tracks needed."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "reductions", Path(__file__).with_name("review-route-reductions.py")
)
reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviewer)


class ReductionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / "tracks" / "hill"
        self.folder.mkdir(parents=True)
        catalog = self.root / "apps/api/fixtures/catalog"
        catalog.mkdir(parents=True)
        self.route = {
            "slug": "hill-walk",
            "points": ["origin", "middle", "target"],
            "evidence_tracks": ["tracks/hill/walk.gpx"],
        }
        (catalog / "hill.json").write_text(
            json.dumps({"point": {"slug": "hill"}, "routes": {"walk": self.route}})
        )
        self.registered = [
            {
                "slug": "hill-walk",
                "descent_m": None,
                "distance_km": "2.22",
                "timing_source_urls": [],
                "points": [
                    {"slug": slug, "latitude": 35 + i * 0.001, "longitude": 51}
                    for slug, i in zip(self.route["points"], [0, 10, 20])
                ],
            }
        ]
        self.track = {"route": "hill-walk", "file": "walk.gpx", "role": "primary"}
        self.elevations = [1000 + 20 * i for i in range(21)]

    def tearDown(self):
        self.temp.cleanup()

    def run_review(self, *, roundtrip=False):
        points = list(enumerate(self.elevations))
        if roundtrip:
            points += list(reversed(points[:-1]))
        gpx = '<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
        gpx += "".join(
            f'<trkpt lat="{35 + i * 0.001}" lon="51"><ele>{ele}</ele></trkpt>'
            for i, ele in points
        )
        gpx += "</trkseg></trk></gpx>"
        (self.folder / "walk.gpx").write_text(gpx)
        (self.folder / "manifest.json").write_text(json.dumps({"tracks": [self.track]}))
        return reviewer.review(self.root, self.registered)

    def test_return_descent_is_excluded_from_uphill_route(self):
        result = self.run_review(roundtrip=True)
        self.assertEqual(result["routes"][0]["descent_m"], 0)
        self.assertLess(result["routes"][0]["evidence"]["analysis_distance_km"], 2.3)

    def test_undulations_count_even_when_target_is_above_origin(self):
        self.elevations = [
            1000 + 40 * i
            if i <= 8
            else 1320 - 30 * (i - 8)
            if i <= 14
            else 1140 + 40 * (i - 14)
            for i in range(21)
        ]
        result = self.run_review(roundtrip=True)
        self.assertGreater(result["routes"][0]["descent_m"], 70)
        self.assertGreater(
            result["routes"][0]["evidence"]["analysis_ascent_m"],
            result["routes"][0]["descent_m"],
        )

    def test_explicit_reverse_section_preserves_registered_direction(self):
        self.registered[0]["points"] = list(reversed(self.registered[0]["points"]))
        self.track["route_sections"] = {
            "hill-walk": {"indices": [20, 10, 0], "direction": "reverse"}
        }
        result = self.run_review()
        self.assertEqual(result["routes"][0]["evidence"]["direction"], "reverse")
        self.assertGreater(result["routes"][0]["descent_m"], 300)

    def test_catalog_file_reference_works_without_route_slug(self):
        self.track.pop("route")
        result = self.run_review()
        self.assertEqual(len(result["routes"]), 1)

    def test_linked_reference_track_is_not_promoted_to_profile(self):
        self.track["role"] = "reference"
        self.assertEqual(self.run_review()["unresolved"], ["hill-walk"])

    def test_changed_source_hash_is_rejected(self):
        self.track["sha256"] = "0" * 64
        result = self.run_review()
        self.assertEqual(result["routes"], [])
        self.assertIn("source hash changed", result["diagnostics"][0]["reason"])

    def test_wrong_registered_origin_is_not_silently_replaced(self):
        self.registered[0]["points"][0]["latitude"] = 35.1
        self.assertEqual(self.run_review()["routes"], [])


if __name__ == "__main__":
    unittest.main()
