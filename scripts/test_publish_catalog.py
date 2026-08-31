import unittest

from .publish_catalog import pending_timing_routes, remote_command


class PublishCatalogTests(unittest.TestCase):
    def test_pending_timing_routes_is_explicit_and_ordered(self):
        catalog = {
            "routes": {
                "first": {"slug": "route-first", "timing_status": "estimated", "timing": {}},
                "second": {"slug": "route-second", "timing_status": "pending"},
                "third": {"slug": "route-third", "timing_status": "curated", "timing": {"method": "x"}},
            }
        }

        self.assertEqual(pending_timing_routes(catalog), ["route-first", "route-second"])

    def test_remote_command_uses_explicit_paths_and_no_directory_mutation(self):
        command = remote_command(
            host="root@example.test",
            remote_dir="/root/hawatch",
            env_file=".env",
            compose_file="infra/compose/compose.yaml",
            manage_args=["seed_catalog", "--stdin", "--check-only"],
        )

        self.assertEqual(command[:2], ["ssh", "root@example.test"])
        self.assertIn("--env-file /root/hawatch/.env", command[2])
        self.assertIn("-f /root/hawatch/infra/compose/compose.yaml", command[2])
        self.assertIn("seed_catalog --stdin --check-only", command[2])
        self.assertNotIn("cd ", command[2])


if __name__ == "__main__":
    unittest.main()
