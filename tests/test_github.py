"""
Unit tests for Paku GitHub Integration.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from paku.features.github import (
    get_github_status,
    get_current_repo_nwo,
    list_repositories,
    list_issues,
    list_prs,
    render_github_status,
)
from paku.ui.themes import get_theme
from paku.ui.mascot import MascotLoader


class TestGitHubIntegration(unittest.TestCase):

    def test_get_current_repo_nwo_parses(self):
        # Paku repo itself has origin remote pointing to rymrimi777-rgb/paku-terminal-companion
        repo = get_current_repo_nwo(Path.cwd())
        if repo:
            self.assertIn("/", repo)
            self.assertEqual(repo, "rymrimi777-rgb/paku-terminal-companion")

    def test_github_status_no_crash(self):
        status = get_github_status()
        self.assertIn("is_authenticated", status)
        self.assertIn("auth_method", status)
        self.assertIn("status_message", status)
        self.assertIn("username", status)

    @patch("shutil.which", return_value=None)
    @patch.dict("os.environ", {}, clear=True)
    def test_unauthenticated_state_graceful_handling(self, mock_which):
        status = get_github_status()
        self.assertFalse(status["is_authenticated"])
        self.assertEqual(status["auth_method"], "Unauthenticated")

        ok_repos, repos, msg_repos = list_repositories(limit=5)
        self.assertFalse(ok_repos)
        self.assertIn("available", msg_repos.lower())

        ok_issues, issues, msg_issues = list_issues(limit=5, repo="owner/repo")
        self.assertFalse(ok_issues)

        ok_prs, prs, msg_prs = list_prs(limit=5, repo="owner/repo")
        self.assertFalse(ok_prs)

    def test_render_github_status_display(self):
        theme = get_theme("cyan")
        mascot = MascotLoader(Path.cwd())
        code = render_github_status(theme, mascot, as_json=True, wait_for_enter=False)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
