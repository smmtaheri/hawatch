"""Offline tests for origin/target-aware GPX analysis cuts."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "route_analyzer", Path(__file__).with_name("analyze_route_tracks.py")
)
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)


class RouteSegmentCutTests(unittest.TestCase):
    def setUp(self):
        self.points = [
            {"lat": 35.0 + index * 0.001, "lon": 51.0, "ele": 1000 + index * 50, "time": None}
            for index in range(5)
        ]

    def test_forward_cut_excludes_recorded_access_before_origin(self):
        segment, meta = analyzer.cut_route_segment(
            self.points,
            target=(35.004, 51.0),
            origin=(35.001, 51.0),
            direction="forward",
        )
        self.assertEqual(len(segment), 4)
        self.assertEqual(segment[0]["lat"], 35.001)
        self.assertEqual(segment[-1]["lat"], 35.004)
        self.assertEqual(meta["origin_index"], 1)
        self.assertFalse(meta["reversed_for_analysis"])

    def test_reverse_cut_returns_origin_to_target_order(self):
        segment, meta = analyzer.cut_route_segment(
            self.points,
            target=(35.0, 51.0),
            origin=(35.004, 51.0),
            direction="reverse",
        )
        self.assertEqual(segment[0]["lat"], 35.004)
        self.assertEqual(segment[-1]["lat"], 35.0)
        self.assertEqual(meta["origin_index"], 4)
        self.assertTrue(meta["reversed_for_analysis"])

    def test_reverse_requires_an_explicit_origin(self):
        with self.assertRaisesRegex(ValueError, "requires a manifest route_origin"):
            analyzer.cut_route_segment(
                self.points,
                target=(35.004, 51.0),
                origin=None,
                direction="reverse",
            )


if __name__ == "__main__":
    unittest.main()
