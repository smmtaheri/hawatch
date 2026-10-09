import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "estimate_timings", Path(__file__).with_name("estimate-route-timings.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def example(*, gain=0, loss=0, indices=None, last_fraction=1.0):
    points = [
        {
            "lat": 35.0,
            "lon": 51.0 + i * 0.00011,
            "ele": 1000 + gain * i / 100,
            "time": None,
        }
        for i in range(101)
    ]
    points[-1]["lon"] = points[-2]["lon"] + 0.00011 * last_fraction
    profile = {
        "_profile": points,
        "_point_indices": indices or [0, 50, 100],
        "descent_m": loss,
        "chain": ["start", "middle", "target"],
        "evidence": {
            "catalog_source_urls": ["https://example.test/trail"],
            "source_url": None,
        },
    }
    route = {"slug": "sample", "distance_km": 1.0, "ascent_m": max(0, gain)}
    return profile, route


class TimingTests(unittest.TestCase):
    def test_timestamps_do_not_change_estimate(self):
        profile, route = example(gain=150)
        expected = module.estimate(profile, route)
        for point in profile["_profile"]:
            point["time"] = "a seventeen-hour stop or synthetic timestamp"
        self.assertEqual(expected, module.estimate(profile, route))
        self.assertFalse(expected["timing"]["evidence"]["timestamp_used"])

    def test_uphill_takes_longer_than_level_profile(self):
        level, route = example()
        uphill, uphill_route = example(gain=300)
        self.assertGreater(
            module.estimate(uphill, uphill_route)["one_way_minutes"],
            module.estimate(level, route)["one_way_minutes"],
        )

    def test_reduction_adds_to_independent_check(self):
        profile, route = example(gain=-200, loss=200)
        expected = module.estimate(profile, route)["timing"]["evidence"][
            "independent_check_minutes"
        ]
        profile["descent_m"] = 0
        without = module.estimate(profile, route)["timing"]["evidence"][
            "independent_check_minutes"
        ]
        self.assertGreater(expected, without)

    def test_close_landmarks_remain_strictly_ordered(self):
        profile, route = example(indices=[0, 99, 100])
        result = module.estimate(profile, route)
        minutes = list(result["timing"]["cumulative_minutes"].values())
        self.assertEqual(minutes[0], 0)
        self.assertLess(minutes[1], minutes[2])
        self.assertEqual(minutes[-1], result["one_way_minutes"])

    def test_final_partial_interval_is_retained_without_steep_grade_artifact(self):
        profile, route = example(gain=150, last_fraction=0.01)
        result = module.estimate(profile, route)
        self.assertGreater(result["one_way_minutes"], 0)

    def test_large_model_disagreement_requires_review(self):
        profile, route = example()
        route["ascent_m"] = 5000
        with self.assertRaisesRegex(ValueError, "disagreement"):
            module.estimate(profile, route)

    def test_incomplete_registered_metrics_rejected(self):
        profile, route = example()
        route["ascent_m"] = None
        with self.assertRaisesRegex(ValueError, "incomplete"):
            module.estimate(profile, route)


if __name__ == "__main__":
    unittest.main()
