"""
Unit tests for Paku Clean feature (safe junk scanning, path traversal guards, dry run).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from paku.features.clean import scan_junk, is_safe_target_path, _format_size, render_clean
from paku.ui.themes import get_theme
from paku.ui.mascot import MascotLoader


class TestCleanFeature(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.tmp.name).resolve()
        self.theme = get_theme("cyan")
        self.mascot = MascotLoader(self.sandbox)

    def tearDown(self):
        self.tmp.cleanup()

    def test_format_size(self):
        self.assertEqual(_format_size(500), "500 B")
        self.assertEqual(_format_size(2048), "2.0 KB")
        self.assertEqual(_format_size(2 * 1024 * 1024), "2.00 MB")

    def test_is_safe_target_path(self):
        inside = self.sandbox / "sub" / "file.txt"
        outside = self.sandbox.parent / "escape.txt"
        self.assertTrue(is_safe_target_path(inside, self.sandbox))
        self.assertFalse(is_safe_target_path(outside, self.sandbox))

    def test_scan_junk_detection(self):
        # Create safe junk
        pycache = self.sandbox / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.cpython-312.pyc").write_text("bytecode")

        pytest_cache = self.sandbox / ".pytest_cache"
        pytest_cache.mkdir()

        regular_file = self.sandbox / "main.py"
        regular_file.write_text("print('hello')")

        items = scan_junk(self.sandbox)
        item_paths = [p for p, _, _ in items]

        self.assertIn(pycache, item_paths)
        self.assertIn(pytest_cache, item_paths)
        self.assertNotIn(regular_file, item_paths)

    def test_dry_run_preserves_files(self):
        pycache = self.sandbox / "__pycache__"
        pycache.mkdir()
        test_file = pycache / "sample.pyc"
        test_file.write_text("data")

        # Run dry run
        render_clean(
            theme=self.theme,
            mascot_loader=self.mascot,
            target_dir=self.sandbox,
            yes=True,
            dry_run=True,
            wait_for_enter=False,
            animations_enabled=False,
        )

        # Confirm file still exists
        self.assertTrue(test_file.exists())
        self.assertTrue(pycache.exists())


if __name__ == "__main__":
    unittest.main()
