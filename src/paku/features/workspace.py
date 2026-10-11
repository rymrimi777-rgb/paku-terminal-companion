"""
Paku Workspace Feature
======================
Detects project root, project type, package metadata, and Git status.
"""

from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel
from paku.ui.animations import spinner_task

console = Console(legacy_windows=False)

MARKERS: Dict[str, str] = {
    "pyproject.toml": "Python (pyproject)",
    "package.json":   "Node.js / JS",
    "Cargo.toml":     "Rust (Cargo)",
    "go.mod":         "Go",
    "requirements.txt": "Python (pip)",
    "setup.py":       "Python (setuptools)",
    "Gemfile":        "Ruby (Bundler)",
    "pom.xml":        "Java (Maven)",
    "build.gradle":   "Java / Kotlin (Gradle)",
    "composer.json":  "PHP (Composer)",
    "CMakeLists.txt": "C / C++ (CMake)",
}


def _detect_root(start_dir: Path) -> Tuple[Path, List[str]]:
    """Walk up from start_dir to find project root and detected types."""
    curr = start_dir.resolve()
    for _ in range(50):
        found_types = []
        if (curr / ".git").exists():
            found_types.append("Git Repository")
        for marker_file, label in MARKERS.items():
            if (curr / marker_file).exists():
                found_types.append(label)
        if found_types:
            return curr, found_types
        if curr.parent == curr:
            break
        curr = curr.parent
    return start_dir.resolve(), ["Generic Folder"]


def _extract_project_name(root: Path) -> str:
    """Extract project name from package.json or pyproject.toml if possible."""
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "name" in data:
                return str(data["name"])
        except Exception:
            pass

    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        try:
            for line in pyproj.read_text(encoding="utf-8").splitlines():
                line_s = line.strip()
                if line_s.startswith("name ="):
                    parts = line_s.split("=", 1)[1].strip().strip('"').strip("'")
                    if parts:
                        return parts
        except Exception:
            pass

    return root.name


def _git_info(root: Path) -> Optional[Dict[str, Any]]:
    """Fetch read-only git details via subprocess if root is a git repo."""
    if not (root / ".git").exists():
        return None

    info: Dict[str, Any] = {}
    try:
        # Branch
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        info["branch"] = branch or "HEAD (detached)"

        # Porcelain status
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        lines = status.splitlines() if status else []
        info["uncommitted"] = str(len(lines))

        # Staged vs Untracked
        staged_count = sum(1 for line in lines if len(line) >= 2 and line[0] in "MADRC")
        untracked_count = sum(1 for line in lines if line.startswith("??"))
        unstaged_count = sum(1 for line in lines if len(line) >= 2 and line[1] in "MD")

        info["staged"] = str(staged_count)
        info["unstaged"] = str(unstaged_count)
        info["untracked"] = str(untracked_count)

        # Remote URL
        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            info["remote"] = remote
        except Exception:
            info["remote"] = "none"

        # Upstream branch
        try:
            upstream = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            info["upstream"] = upstream
        except Exception:
            info["upstream"] = "none"

        # Recent commits (last 5)
        recent_commits: List[Tuple[str, str, str, str]] = []
        try:
            log_out = subprocess.check_output(
                ["git", "log", "-n", "5", "--format=%h|%an|%ar|%s"],
                cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if log_out:
                for line in log_out.splitlines():
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        recent_commits.append((parts[0], parts[1], parts[2], parts[3]))
        except Exception:
            pass
        info["recent_commits"] = recent_commits

        # Health checks
        health_notes: List[str] = []
        if info["branch"] == "HEAD (detached)":
            health_notes.append("Detached HEAD: commits made in this state may be lost.")
        if int(info["uncommitted"]) == 0:
            health_notes.append("Clean working tree.")
        else:
            health_notes.append(f"{info['uncommitted']} uncommitted file(s) ({staged_count} staged, {unstaged_count} unstaged, {untracked_count} untracked).")
        if info["upstream"] == "none" and info["remote"] != "none":
            health_notes.append("No upstream tracking branch configured for current branch.")
        info["health"] = health_notes

        return info
    except Exception:
        return None


def render_workspace(
    theme: Theme,
    mascot_loader: MascotLoader,
    target_dir: Optional[Path] = None,
    as_json: bool = False,
    wait_for_enter: bool = True,
    animations_enabled: bool = True,
) -> int:
    """Render Workspace details screen."""
    target = (target_dir or Path.cwd()).resolve()

    with spinner_task(console, "Scanning workspace...", duration=0.6, color=theme.primary, enabled=animations_enabled):
        root, project_types = _detect_root(target)
        name = _extract_project_name(root)
        git_data = _git_info(root)

    if as_json:
        report = {
            "name": name,
            "root": str(root),
            "project_types": project_types,
            "git": git_data,
        }
        print(json.dumps(report, indent=2))
        return 0

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   W O R K S P A C E", "ワークスペース情報  •  Workspace Analysis", theme)))
    console.print()

    mascot_state = "idle" if git_data is None else "thinking" if git_data["uncommitted"] != "0" else "happy"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(mascot_state), theme)))
    console.print()

    panel_text = Text()
    panel_text.append("  Project Name    ", style=theme.muted)
    panel_text.append(f"{name}\n", style=f"bold {theme.highlight}")
    panel_text.append("  Root Directory  ", style=theme.muted)
    panel_text.append(f"{root}\n", style=theme.text)
    panel_text.append("  Project Type    ", style=theme.muted)
    panel_text.append(f"{', '.join(project_types)}\n", style=theme.accent)

    if git_data:
        panel_text.append("\n  [Git Details]\n", style=f"bold {theme.primary}")
        panel_text.append("  Branch          ", style=theme.muted)
        panel_text.append(f"{git_data['branch']}\n", style=theme.secondary)
        panel_text.append("  Status          ", style=theme.muted)
        uncommitted_style = theme.warning if git_data["uncommitted"] != "0" else theme.success
        panel_text.append(
            f"{git_data['uncommitted']} total ({git_data['staged']} staged, {git_data['unstaged']} unstaged, {git_data['untracked']} untracked)\n",
            style=uncommitted_style,
        )
        panel_text.append("  Origin Remote   ", style=theme.muted)
        panel_text.append(f"{git_data['remote']}\n", style=theme.dim)
        if git_data.get("upstream") != "none":
            panel_text.append("  Upstream Branch ", style=theme.muted)
            panel_text.append(f"{git_data['upstream']}\n", style=theme.secondary)
    else:
        panel_text.append("\n  Git Status      ", style=theme.muted)
        panel_text.append("Not a Git repository\n", style=theme.dim)

    console.print(Align.center(framed_section(panel_text, "Workspace Overview", theme)))
    console.print()

    # Recent Commits Table if Git
    if git_data and git_data.get("recent_commits"):
        commit_table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
        commit_table.add_column("Commit", width=10, style=theme.highlight)
        commit_table.add_column("Author", width=18, style=theme.dim)
        commit_table.add_column("Date", width=14, style=theme.muted)
        commit_table.add_column("Message", style=theme.text)

        for chash, author, rel_date, subject in git_data["recent_commits"]:
            commit_table.add_row(chash, author, rel_date, subject)

        console.print(Align.center(framed_section(commit_table, "Recent Commit History", theme)))
        console.print()

    # Repo Health Notes
    if git_data and git_data.get("health"):
        health_text = Text()
        for note in git_data["health"]:
            health_text.append(f"  • {note}\n", style=theme.muted)
        console.print(Align.center(framed_section(health_text, "Repository Health", theme)))
        console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0

