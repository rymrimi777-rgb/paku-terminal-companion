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

from paku.ui.themes import Theme
from paku.ui.terminal import styled_line, framed_section, build_header
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


def _git_info(root: Path) -> Optional[Dict[str, str]]:
    """Fetch read-only git details via subprocess if root is a git repo."""
    if not (root / ".git").exists():
        return None

    info: Dict[str, str] = {}
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        info["branch"] = branch or "HEAD (detached)"

        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        modified_count = len(status.splitlines()) if status else 0
        info["uncommitted"] = str(modified_count)

        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
            info["remote"] = remote
        except Exception:
            info["remote"] = "none"

        return info
    except Exception:
        return None


def render_workspace(theme: Theme, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Workspace details screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   W O R K S P A C E", "ワークスペース情報  •  Workspace Analysis", theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Scanning workspace...", duration=0.6, color=theme.primary, enabled=True)

    cwd = Path.cwd()
    root, project_types = _detect_root(cwd)
    name = _extract_project_name(root)
    git_data = _git_info(root)

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
        panel_text.append("  Uncommitted     ", style=theme.muted)
        uncommitted_style = theme.warning if git_data["uncommitted"] != "0" else theme.success
        panel_text.append(f"{git_data['uncommitted']} file(s)\n", style=uncommitted_style)
        panel_text.append("  Origin Remote   ", style=theme.muted)
        panel_text.append(f"{git_data['remote']}\n", style=theme.dim)
    else:
        panel_text.append("\n  Git Status      ", style=theme.muted)
        panel_text.append("Not a Git repository\n", style=theme.dim)

    console.print(Align.center(framed_section(panel_text, "Workspace Overview", theme)))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
