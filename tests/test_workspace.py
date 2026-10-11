"""
Unit tests for Paku Workspace analysis.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from paku.features.workspace import _detect_root, _extract_project_name, _git_info, render_workspace
from paku.ui.themes import get_theme
from paku.ui.mascot import MascotLoader


class TestWorkspaceFeature(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name).resolve()
        self.theme = get_theme("sakura")
        self.mascot = MascotLoader(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detect_root_and_project_name(self):
        pyproj = self.dir / "pyproject.toml"
        pyproj.write_text('[project]\nname = "test-workspace-pkg"\n', encoding="utf-8")

        sub = self.dir / "src" / "pkg"
        sub.mkdir(parents=True)

        root, ptypes = _detect_root(sub)
        self.assertEqual(root, self.dir)
        self.assertTrue(any("pyproject" in t for t in ptypes))

        name = _extract_project_name(self.dir)
        self.assertEqual(name, "test-workspace-pkg")

    def test_git_info_non_repo_returns_none(self):
        info = _git_info(self.dir)
        self.assertIsNone(info)

    def test_render_workspace_json(self):
        code = render_workspace(
            theme=self.theme,
            mascot_loader=self.mascot,
            target_dir=self.dir,
            as_json=True,
            wait_for_enter=False,
            animations_enabled=False,
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
