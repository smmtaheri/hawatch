import unittest
from pathlib import Path

from .publish_catalog import WorkflowError, build_parser, pending_timing_routes, remote_command, run_workflow


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

    def test_point_only_catalog_has_no_pending_routes(self):
        self.assertEqual(pending_timing_routes({"routes": {}}), [])

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

    def test_apply_cannot_bypass_provider_validation(self):
        repo = Path(__file__).resolve().parents[1]
        args = build_parser().parse_args(
            [
                "--catalog",
                str(repo / "apps/api/fixtures/catalog/hazar_v1.json"),
                "--host",
                "root@example.test",
                "--apply",
                "--skip-provider-validation",
            ]
        )

        with self.assertRaisesRegex(WorkflowError, "provider/DEM validation is required"):
            run_workflow(args)

    def test_apply_cannot_publish_unresolved_elevation(self):
        repo = Path(__file__).resolve().parents[1]
        args = build_parser().parse_args(
            [
                "--catalog",
                str(repo / "apps/api/fixtures/catalog/hazar_v1.json"),
                "--host",
                "root@example.test",
                "--apply",
                "--allow-unresolved-elevation",
            ]
        )

        with self.assertRaisesRegex(WorkflowError, "every imported point needs a validated elevation"):
            run_workflow(args)


if __name__ == "__main__":
    unittest.main()
