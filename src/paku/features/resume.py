"""
Paku Resume & Context Capture Feature
=====================================
Per-workspace session memory aid for dev context.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.panel import Panel

from paku.ui.themes import Theme
from paku.ui.terminal import styled_line, framed_section, build_header
from paku.ui.animations import spinner_task
from paku.config.settings import CONFIG_DIR
from paku.features.workspace import _detect_root, _git_info, _extract_project_name

console = Console(legacy_windows=False)

SESSIONS_DIR = CONFIG_DIR / "sessions"
_SESSION_SAVED_IN_THIS_RUN = False


def _get_workspace_slug(root: Path) -> str:
    """Generate stable SHA1 hash slug for workspace root path."""
    clean_path = str(root.resolve()).lower().strip()
    return hashlib.sha1(clean_path.encode("utf-8")).hexdigest()[:12]


def _get_session_file(root: Path) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _get_workspace_slug(root)
    return SESSIONS_DIR / f"{slug}.json"


def _format_relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to human-friendly relative time."""
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        else:
            days = seconds // 86400
            return f"{days}d ago"
    except Exception:
        return "recently"


def save_current_session(note: Optional[str] = None, prompt_user: bool = False) -> None:
    """Capture current workspace state and write to session history."""
    global _SESSION_SAVED_IN_THIS_RUN

    root, _ = _detect_root(Path.cwd())
    git_data = _git_info(root)

    user_note = note
    if prompt_user:
        console.print()
        console.print(Align.center(
            styled_line(("What are you working on? ", "bold bright_white"), ("(optional, Enter to skip)", "bright_black"))
        ))
        console.print()
        try:
            inp = input("  > ").strip()
            user_note = inp if inp else None
        except (EOFError, KeyboardInterrupt):
            user_note = None

    session_file = _get_session_file(root)
    history: List[Dict[str, Any]] = []

    if session_file.exists():
        try:
            history = json.loads(session_file.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(root),
        "git_branch": git_data["branch"] if git_data else None,
        "uncommitted_count": int(git_data["uncommitted"]) if git_data and git_data["uncommitted"].isdigit() else None,
        "note": user_note,
    }

    history.insert(0, entry)
    history = history[:5]  # Keep last 5 entries

    session_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    _SESSION_SAVED_IN_THIS_RUN = True


def auto_save_on_exit() -> None:
    """Silently capture session on exit if not manually saved during run."""
    global _SESSION_SAVED_IN_THIS_RUN
    if not _SESSION_SAVED_IN_THIS_RUN:
        try:
            save_current_session(note=None, prompt_user=False)
        except Exception:
            pass


def render_save(theme: Theme, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Save Context screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   S A V E", "コンテキスト保存  •  Save Workspace Memory", theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Capturing workspace context...", duration=0.6, color=theme.primary, enabled=True)

    save_current_session(prompt_user=True)

    console.print()
    console.print(Align.center(
        styled_line(("✓  Context saved successfully!", f"bold {theme.success}"), ("  完了！", theme.muted))
    ))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()


def render_resume(theme: Theme, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Resume Context screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   R E S U M E", "コンテキスト復元  •  Workspace Memory", theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Loading workspace memory...", duration=0.6, color=theme.primary, enabled=True)

    cwd = Path.cwd()
    root, _ = _detect_root(cwd)
    proj_name = _extract_project_name(root)
    session_file = _get_session_file(root)

    history: List[Dict[str, Any]] = []
    if session_file.exists():
        try:
            history = json.loads(session_file.read_text(encoding="utf-8"))
        except Exception:
            history = []

    if not history:
        content = Text()
        content.append(f"  No saved sessions found for ", style=theme.text)
        content.append(f"{proj_name}\n", style=theme.highlight)
        content.append(f"  Path: {root}\n\n", style=theme.muted)
        content.append("  💡 Tip: Run 'paku save' before closing to capture your notes!", style=theme.accent)
        console.print(Align.center(framed_section(content, "Workspace Context", theme)))
    else:
        latest = history[0]
        rel_time = _format_relative_time(latest.get("timestamp", ""))

        main_text = Text()
        main_text.append(f"  Project Name     ", style=f"bold {theme.accent}")
        main_text.append(f"{proj_name}\n", style=theme.highlight)
        main_text.append(f"  Workspace Root   ", style=f"bold {theme.accent}")
        main_text.append(f"{latest.get('workspace_root', str(root))}\n", style=theme.text)

        branch = latest.get("git_branch")
        if branch:
            main_text.append(f"  Git Branch       ", style=f"bold {theme.accent}")
            main_text.append(f"{branch}\n", style=theme.secondary)

        uncommitted = latest.get("uncommitted_count")
        if uncommitted is not None:
            main_text.append(f"  Uncommitted      ", style=f"bold {theme.accent}")
            st = theme.warning if uncommitted > 0 else theme.success
            main_text.append(f"{uncommitted} file(s)\n", style=st)

        main_text.append(f"  Last Saved       ", style=f"bold {theme.accent}")
        main_text.append(f"{rel_time}\n", style=theme.muted)

        note = latest.get("note")
        if note:
            main_text.append(f"\n  Note: ", style=f"bold {theme.primary}")
            main_text.append(f"\"{note}\"", style=f"bold {theme.text}")

        console.print(Align.center(framed_section(main_text, "Latest Active Session", theme)))

        if len(history) > 1:
            console.print()
            hist_text = Text()
            for idx, item in enumerate(history[1:], 1):
                t_str = _format_relative_time(item.get("timestamp", ""))
                b_str = item.get("git_branch") or "no-git"
                u_cnt = item.get("uncommitted_count")
                u_str = f"{u_cnt} uncommitted" if u_cnt is not None else ""
                n_str = f" • \"{item.get('note')}\"" if item.get("note") else ""

                hist_text.append(f"  [{idx}]  ", style=f"bold {theme.accent}")
                hist_text.append(f"{t_str:<10} ", style=theme.muted)
                hist_text.append(f"({b_str}) ", style=theme.secondary)
                if u_str:
                    hist_text.append(f"{u_str} ", style=theme.dim)
                if n_str:
                    hist_text.append(f"{n_str}", style=theme.text)
                hist_text.append("\n")

            console.print(Align.center(framed_section(hist_text, "Previous Sessions", theme)))

    console.print()
    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
