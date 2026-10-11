"""
Unit tests for Paku Typer CLI commands.
"""

from __future__ import annotations

import unittest
from typer.testing import CliRunner
from paku.cli import app

runner = CliRunner()


class TestCliCommands(unittest.TestCase):

    def test_cli_help(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("doctor", result.output)
        self.assertIn("info", result.output)
        self.assertIn("workspace", result.output)
        self.assertIn("clean", result.output)
        self.assertIn("scan", result.output)
        self.assertIn("self-test", result.output)
        self.assertIn("system", result.output)
        self.assertIn("github", result.output)

    def test_cli_self_test_json(self):
        result = runner.invoke(app, ["self-test", "--json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"all_passed": true', result.output)

    def test_cli_clean_dry_run(self):
        result = runner.invoke(app, ["clean", "--dry-run"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("DRY RUN", result.output)

    def test_cli_scan_security(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = runner.invoke(app, ["scan", "--security", str(tmp_dir)])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Audit Summary", result.output)

    def test_cli_system_disk_json(self):
        result = runner.invoke(app, ["system", "disk", "--json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("mount", result.output)

    def test_cli_github_status_json(self):
        result = runner.invoke(app, ["github", "status", "--json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("is_authenticated", result.output)


if __name__ == "__main__":
    unittest.main()
