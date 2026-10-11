"""
Unit tests for Paku Security Audit (secret scanning, redaction, git exposure, dependencies).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from paku.features.security_audit import (
    redact_secret,
    scan_secrets,
    scan_git_exposure,
    scan_dependencies,
    run_full_security_audit,
    _is_sensitive_filename,
)


class TestSecurityAudit(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_redact_secret(self):
        self.assertEqual(redact_secret("short"), "***")
        self.assertEqual(redact_secret("AKIA1234567890ABCDEF"), "AKIA***CDEF")
        self.assertNotIn("1234567890AB", redact_secret("AKIA1234567890ABCDEF"))

    def test_sensitive_filenames(self):
        self.assertTrue(_is_sensitive_filename(".env"))
        self.assertTrue(_is_sensitive_filename(".env.production"))
        self.assertTrue(_is_sensitive_filename("id_rsa"))
        self.assertTrue(_is_sensitive_filename("cert.pem"))
        self.assertTrue(_is_sensitive_filename("secret.key"))
        self.assertFalse(_is_sensitive_filename("main.py"))
        self.assertFalse(_is_sensitive_filename("README.md"))

    def test_scan_secrets_detection_and_masking(self):
        # Create a file with test secrets in sandbox
        secret_file = self.dir / "test_config.py"
        test_aws = "AKIA" + "IOSFODNN7EXAMPLE"
        test_gh = "ghp_" + ("1234567890" * 3) + "123456"
        secret_file.write_text(
            f'AWS_KEY = "{test_aws}"\n'
            f'GH_TOKEN = "{test_gh}"\n',
            encoding="utf-8"
        )

        findings = scan_secrets(self.dir)
        self.assertGreaterEqual(len(findings), 2)

        titles = [f.title for f in findings]
        self.assertTrue(any("AWS Access Key" in t for t in titles))
        self.assertTrue(any("GitHub Personal Access Token" in t for t in titles))

        # Ensure raw secret is not in snippet
        for f in findings:
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE", f.snippet)
            self.assertNotIn("ghp_123456789012345678901234567890123456", f.snippet)
            self.assertIn("***", f.snippet)

    def test_scan_dependencies_manifest_detection(self):
        pyproj = self.dir / "pyproject.toml"
        pyproj.write_text('[project]\nname = "test"\n', encoding="utf-8")

        findings = scan_dependencies(self.dir)
        self.assertTrue(any("Python (pyproject.toml)" in f.title for f in findings))

    def test_full_security_audit_clean_run(self):
        report = run_full_security_audit(self.dir)
        self.assertIn("timestamp", report)
        self.assertIn("summary", report)
        self.assertIn("findings", report)
        self.assertTrue(report["clean"])
        self.assertEqual(report["summary"]["CRITICAL"], 0)
        self.assertEqual(report["summary"]["HIGH"], 0)


if __name__ == "__main__":
    unittest.main()
