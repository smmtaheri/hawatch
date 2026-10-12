import unittest
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "route_metrics", Path(__file__).with_name("estimate-missing-route-metrics.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EstimateMissingRouteMetricsTests(unittest.TestCase):
    def test_descent_uses_ascent_and_net_elevation(self):
        route = {
            "slug": "test-route",
            "ascent_m": 1000,
            "timing_source_urls": [],
            "points": [
                {"elevation_m": 1000},
                {"elevation_m": 1500},
                {"elevation_m": 1800},
            ],
        }
        descent, evidence = module.estimate_descent(route)
        self.assertEqual(descent, 200)
        self.assertEqual(evidence["confidence"], "medium")
        self.assertFalse(evidence["lower_bound_estimate"])

    def test_descent_never_violates_checkpoint_drop_lower_bound(self):
        route = {
            "slug": "test-route",
            "ascent_m": 100,
            "timing_source_urls": [],
            "points": [
                {"elevation_m": 1000},
                {"elevation_m": 1200},
                {"elevation_m": 1150},
            ],
        }
        descent, evidence = module.estimate_descent(route)
        self.assertEqual(descent, 50)
        self.assertEqual(evidence["confidence"], "low")
        self.assertTrue(evidence["lower_bound_estimate"])

    def test_segment_distance_preserves_known_values_and_route_total(self):
        route = {
            "slug": "test-route",
            "distance_km": 10.0,
            "points": [
                {
                    "slug": "origin",
                    "latitude": 35.0,
                    "longitude": 51.0,
                    "segment_distance_m": None,
                },
                {
                    "slug": "midpoint",
                    "latitude": 35.05,
                    "longitude": 51.0,
                    "segment_distance_m": 2000,
                },
                {
                    "slug": "target",
                    "latitude": 35.10,
                    "longitude": 51.0,
                    "segment_distance_m": None,
                },
            ],
        }
        distances, evidence = module.estimate_segment_distances(route)
        self.assertEqual(distances, [0, 2000, 8000])
        self.assertEqual(sum(distances[1:]), 10000)
        self.assertEqual(evidence["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
