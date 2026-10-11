"""
Paku GitHub Integration Feature
===============================
Optional GitHub project management toolkit:
- GitHub CLI (gh) integration with GITHUB_TOKEN fallback
- Inspect authentication status and accessible repositories
- View open issues and pull requests
- Zero hardcoded tokens, zero mandatory network dependency for local commands
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel

console = Console(legacy_windows=False)


def _check_gh_cli() -> Tuple[bool, str, Optional[str]]:
    """Check if GitHub CLI (gh) is installed and authenticated."""
    gh_path = shutil.which("gh")
    if not gh_path:
        return False, "GitHub CLI ('gh') is not installed on PATH", None

    try:
        res = subprocess.run(
            [gh_path, "auth", "status"],
            capture_output=True, text=True, timeout=5
        )
        combined = (res.stdout or "") + (res.stderr or "")
        if res.returncode == 0 or "Logged in to" in combined:
            # Extract username if possible
            user = None
            for line in combined.splitlines():
                if "Logged in to" in line and "account" in line:
                    parts = line.split("account", 1)
                    if len(parts) > 1:
                        user = parts[1].strip().split()[0]
            return True, "GitHub CLI authenticated", user
        else:
            return False, "GitHub CLI is installed but not authenticated (run 'gh auth login')", None
    except (subprocess.TimeoutExpired, Exception) as exc:
        return False, f"Error checking GitHub CLI: {exc}", None


def _get_api_headers() -> Dict[str, str]:
    """Retrieve safe API headers using GITHUB_TOKEN if present."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Paku-Terminal-Companion",
    }
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def get_current_repo_nwo(cwd: Optional[Path] = None) -> Optional[str]:
    """Extract owner/repo slug from git origin remote URL."""
    root = cwd or Path.cwd()
    try:
        out = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=4
        ).strip()
        # Handle https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if "github.com" in out:
            cleaned = out.replace("git@github.com:", "").replace("https://github.com/", "")
            if cleaned.endswith(".git"):
                cleaned = cleaned[:-4]
            parts = cleaned.strip("/").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"
    except Exception:
        pass
    return None


def get_github_status() -> Dict[str, Any]:
    """Retrieve GitHub auth status and environment details."""
    gh_ok, gh_msg, gh_user = _check_gh_cli()
    has_token = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    current_repo = get_current_repo_nwo()

    auth_method = "GitHub CLI (gh)" if gh_ok else "GITHUB_TOKEN (env)" if has_token else "Unauthenticated"
    is_authenticated = gh_ok or has_token

    return {
        "is_authenticated": is_authenticated,
        "auth_method": auth_method,
        "username": gh_user or ("Token Authenticated" if has_token else "Anonymous"),
        "status_message": gh_msg if not gh_ok and not has_token else "Ready for authenticated queries",
        "current_repository": current_repo,
        "has_gh_cli": bool(shutil.which("gh")),
    }


def list_repositories(limit: int = 15) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Query repositories for current user."""
    gh_path = shutil.which("gh")
    if gh_path:
        try:
            cmd = ["gh", "repo", "list", "--limit", str(limit), "--json", "name,nameWithOwner,isPrivate,stargazerCount,updatedAt,url"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return True, data, "Success"
            else:
                err = res.stderr.strip() if res.stderr else "gh command failed"
                return False, [], err
        except Exception as exc:
            return False, [], str(exc)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        try:
            req = urllib.request.Request("https://api.github.com/user/repos?per_page=" + str(limit), headers=_get_api_headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                repos = []
                for r in data:
                    repos.append({
                        "name": r.get("name"),
                        "nameWithOwner": r.get("full_name"),
                        "isPrivate": r.get("private", False),
                        "stargazerCount": r.get("stargazers_count", 0),
                        "updatedAt": r.get("updated_at"),
                        "url": r.get("html_url"),
                    })
                return True, repos, "Success"
        except urllib.error.HTTPError as exc:
            return False, [], f"GitHub API error: {exc.code} {exc.reason}"
        except Exception as exc:
            return False, [], f"Network error: {exc}"

    return False, [], "No GitHub CLI or GITHUB_TOKEN available"


def list_issues(limit: int = 15, repo: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Query open issues for repository."""
    target_repo = repo or get_current_repo_nwo()
    gh_path = shutil.which("gh")

    if gh_path:
        try:
            cmd = ["gh", "issue", "list", "--limit", str(limit), "--json", "number,title,author,state,updatedAt,url"]
            if target_repo:
                cmd.extend(["-R", target_repo])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return True, data, "Success"
            else:
                return False, [], res.stderr.strip() if res.stderr else "gh command failed"
        except Exception as exc:
            return False, [], str(exc)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and target_repo:
        try:
            url = f"https://api.github.com/repos/{target_repo}/issues?state=open&per_page={limit}"
            req = urllib.request.Request(url, headers=_get_api_headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Filter out PRs (GitHub issues API includes PRs)
                issues = [
                    {
                        "number": i.get("number"),
                        "title": i.get("title"),
                        "author": {"login": i.get("user", {}).get("login", "unknown")},
                        "state": i.get("state"),
                        "updatedAt": i.get("updated_at"),
                        "url": i.get("html_url"),
                    }
                    for i in data if "pull_request" not in i
                ]
                return True, issues, "Success"
        except urllib.error.HTTPError as exc:
            return False, [], f"GitHub API error: {exc.code} {exc.reason}"
        except Exception as exc:
            return False, [], f"Network error: {exc}"

    if not target_repo:
        return False, [], "No target repository found (not inside a GitHub git repo or repo not specified)"
    return False, [], "Authentication required to query issues"


def list_prs(limit: int = 15, repo: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Query open pull requests for repository."""
    target_repo = repo or get_current_repo_nwo()
    gh_path = shutil.which("gh")

    if gh_path:
        try:
            cmd = ["gh", "pr", "list", "--limit", str(limit), "--json", "number,title,author,headRefName,state,updatedAt,url"]
            if target_repo:
                cmd.extend(["-R", target_repo])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return True, data, "Success"
            else:
                return False, [], res.stderr.strip() if res.stderr else "gh command failed"
        except Exception as exc:
            return False, [], str(exc)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and target_repo:
        try:
            url = f"https://api.github.com/repos/{target_repo}/pulls?state=open&per_page={limit}"
            req = urllib.request.Request(url, headers=_get_api_headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                prs = [
                    {
                        "number": p.get("number"),
                        "title": p.get("title"),
                        "author": {"login": p.get("user", {}).get("login", "unknown")},
                        "headRefName": p.get("head", {}).get("ref", "unknown"),
                        "state": p.get("state"),
                        "updatedAt": p.get("updated_at"),
                        "url": p.get("html_url"),
                    }
                    for p in data
                ]
                return True, prs, "Success"
        except urllib.error.HTTPError as exc:
            return False, [], f"GitHub API error: {exc.code} {exc.reason}"
        except Exception as exc:
            return False, [], f"Network error: {exc}"

    if not target_repo:
        return False, [], "No target repository found (not inside a GitHub git repo or repo not specified)"
    return False, [], "Authentication required to query pull requests"


# ─── Render Functions ────────────────────────────────────────────────────────

def render_github_status(
    theme: Theme,
    mascot_loader: MascotLoader,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render GitHub authentication and status screen."""
    status = get_github_status()
    if as_json:
        print(json.dumps(status, indent=2))
        return 0

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   G I T H U B", "GitHub連携  •  Authentication Status", theme)))
    console.print()

    mascot_state = "happy" if status["is_authenticated"] else "thinking"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(mascot_state), theme)))
    console.print()

    content = Text()
    content.append("  Auth Status       ", style=theme.accent)
    if status["is_authenticated"]:
        content.append("Connected\n", style=f"bold {theme.success}")
    else:
        content.append("Not Connected\n", style=f"bold {theme.warning}")

    content.append("  Auth Provider     ", style=theme.muted)
    content.append(f"{status['auth_method']}\n", style=theme.text)

    content.append("  Account / Identity", style=theme.muted)
    content.append(f"{status['username']}\n", style=theme.highlight)

    content.append("  Current Repo      ", style=theme.muted)
    repo_str = status["current_repository"] or "Not in a GitHub repository"
    content.append(f"{repo_str}\n\n", style=theme.secondary if status["current_repository"] else theme.dim)

    if not status["is_authenticated"]:
        content.append("  💡 Quick Setup:\n", style=f"bold {theme.primary}")
        content.append("     1. Install GitHub CLI: https://cli.github.com\n", style=theme.muted)
        content.append("     2. Run 'gh auth login' to authenticate safely\n", style=theme.muted)
        content.append("     Or set the GITHUB_TOKEN environment variable.\n", style=theme.dim)

    console.print(Align.center(framed_section(content, "GitHub Integration Status", theme)))
    console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_github_repos(
    theme: Theme,
    mascot_loader: MascotLoader,
    limit: int = 15,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render list of user repositories."""
    success, repos, msg = list_repositories(limit=limit)

    if as_json:
        print(json.dumps({"success": success, "repos": repos, "message": msg}, indent=2))
        return 0 if success else 1

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   G I T H U B   R E P O S", "リポジトリ一覧  •  Accessible Repositories", theme)))
    console.print()

    if not success:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("thinking"), theme)))
        console.print()
        console.print(Align.center(Text(f"! {msg}", style=theme.warning)))
        console.print()
        console.print(Align.center(
            styled_line(("Run 'gh auth login' or export GITHUB_TOKEN to view your repositories.", theme.muted))
        ))
        console.print()
        if wait_for_enter:
            console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
            input()
        return 1

    table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    table.add_column("Repository", style=theme.text)
    table.add_column("Visibility", width=12, justify="center")
    table.add_column("Stars", width=10, justify="right", style=theme.highlight)
    table.add_column("URL", style=theme.dim)

    for r in repos:
        vis = Text("Private", style=theme.warning) if r.get("isPrivate") else Text("Public", style=theme.success)
        table.add_row(
            r.get("nameWithOwner") or r.get("name", "unknown"),
            vis,
            str(r.get("stargazerCount", 0)),
            r.get("url", ""),
        )

    console.print(Align.center(framed_section(table, f"Repositories ({len(repos)})", theme)))
    console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_github_issues(
    theme: Theme,
    mascot_loader: MascotLoader,
    limit: int = 15,
    repo: Optional[str] = None,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render list of open issues."""
    target_repo = repo or get_current_repo_nwo()
    success, issues, msg = list_issues(limit=limit, repo=target_repo)

    if as_json:
        print(json.dumps({"success": success, "repo": target_repo, "issues": issues, "message": msg}, indent=2))
        return 0 if success else 1

    console.clear()
    console.print()
    subtitle = f"課題一覧  •  {target_repo or 'Open Issues'}"
    console.print(Align.center(build_header("P A K U   G I T H U B   I S S U E S", subtitle, theme)))
    console.print()

    if not success:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("thinking"), theme)))
        console.print()
        console.print(Align.center(Text(f"! {msg}", style=theme.warning)))
        console.print()
        if wait_for_enter:
            console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
            input()
        return 1

    if not issues:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("happy"), theme)))
        console.print()
        console.print(Align.center(
            styled_line(("✓  No open issues found for this repository!", theme.success))
        ))
    else:
        table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
        table.add_column("#", width=8, justify="right", style=theme.secondary)
        table.add_column("Title", style=theme.text)
        table.add_column("Author", width=18, style=theme.dim)

        for i in issues:
            author = i.get("author", {}).get("login", "unknown") if isinstance(i.get("author"), dict) else str(i.get("author"))
            table.add_row(
                f"#{i.get('number')}",
                i.get("title", ""),
                author,
            )

        console.print(Align.center(framed_section(table, f"Open Issues ({len(issues)})", theme)))

    console.print()
    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_github_prs(
    theme: Theme,
    mascot_loader: MascotLoader,
    limit: int = 15,
    repo: Optional[str] = None,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render list of open pull requests."""
    target_repo = repo or get_current_repo_nwo()
    success, prs, msg = list_prs(limit=limit, repo=target_repo)

    if as_json:
        print(json.dumps({"success": success, "repo": target_repo, "prs": prs, "message": msg}, indent=2))
        return 0 if success else 1

    console.clear()
    console.print()
    subtitle = f"プルリクエスト  •  {target_repo or 'Open Pull Requests'}"
    console.print(Align.center(build_header("P A K U   G I T H U B   P R S", subtitle, theme)))
    console.print()

    if not success:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("thinking"), theme)))
        console.print()
        console.print(Align.center(Text(f"! {msg}", style=theme.warning)))
        console.print()
        if wait_for_enter:
            console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
            input()
        return 1

    if not prs:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("happy"), theme)))
        console.print()
        console.print(Align.center(
            styled_line(("✓  No open pull requests found for this repository!", theme.success))
        ))
    else:
        table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
        table.add_column("#", width=8, justify="right", style=theme.secondary)
        table.add_column("Title", style=theme.text)
        table.add_column("Branch", width=20, style=theme.highlight)
        table.add_column("Author", width=16, style=theme.dim)

        for p in prs:
            author = p.get("author", {}).get("login", "unknown") if isinstance(p.get("author"), dict) else str(p.get("author"))
            table.add_row(
                f"#{p.get('number')}",
                p.get("title", ""),
                p.get("headRefName", ""),
                author,
            )

        console.print(Align.center(framed_section(table, f"Open Pull Requests ({len(prs)})", theme)))

    console.print()
    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0
