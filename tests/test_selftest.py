"""
Unit tests for Paku Self-Test command and diagnostic verification.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from paku.features.selftest import (
    run_self_tests,
    _check_cli_registration,
    _check_config_lifecycle,
    _check_theme_integrity,
    _check_mascot_system,
    _check_filesystem_sandbox_cleanup,
    _check_platform_detection,
    _check_workspace_root_detection,
    _check_missing_tools_graceful_handling,
    _check_session_persistence,
)


class TestSelfTest(unittest.TestCase):

    def test_run_self_tests_comprehensive(self):
        report = run_self_tests()
        self.assertIn("timestamp", report)
        self.assertIn("platform", report)
        self.assertIn("summary", report)
        self.assertIn("checks", report)

        summary = report["summary"]
        self.assertGreater(summary["total"], 0)
        self.assertEqual(summary["failed"], 0, f"Self-test reported failures: {report['checks']}")
        self.assertTrue(report["all_passed"])
        self.assertGreaterEqual(summary["pass_rate_percent"], 90.0)

    def test_cli_registration_check(self):
        res = _check_cli_registration()
        self.assertEqual(res.status, "PASSED")
        self.assertIn("registered", res.message)

    def test_config_lifecycle_check(self):
        res = _check_config_lifecycle()
        self.assertEqual(res.status, "PASSED")

    def test_theme_integrity_check(self):
        res = _check_theme_integrity()
        self.assertEqual(res.status, "PASSED")

    def test_mascot_system_check(self):
        res = _check_mascot_system()
        self.assertEqual(res.status, "PASSED")

    def test_filesystem_sandbox_cleanup_check(self):
        res = _check_filesystem_sandbox_cleanup()
        self.assertEqual(res.status, "PASSED")

    def test_platform_detection_check(self):
        res = _check_platform_detection()
        self.assertIn(res.status, ("PASSED", "UNSUPPORTED"))

    def test_workspace_root_detection_check(self):
        res = _check_workspace_root_detection()
        self.assertEqual(res.status, "PASSED")

    def test_missing_tools_degradation_check(self):
        res = _check_missing_tools_graceful_handling()
        self.assertEqual(res.status, "PASSED")

    def test_session_persistence_check(self):
        res = _check_session_persistence()
        self.assertEqual(res.status, "PASSED")


if __name__ == "__main__":
    unittest.main()
