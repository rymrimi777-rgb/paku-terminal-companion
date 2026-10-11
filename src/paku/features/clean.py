"""
Paku Clean Feature
==================
Safely scans and removes temporary / junk files recursively under CWD.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel
from paku.ui.animations import spinner_task, progress_bar

console = Console(legacy_windows=False)

# Strict safe-list
SAFE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SAFE_FILES = {"*.pyc", "*.pyo", ".DS_Store", "Thumbs.db"}


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable units."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def _get_item_size(path: Path) -> int:
    """Calculate file size or recursive directory size."""
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    elif path.is_dir():
        total = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except OSError:
            pass
        return total
    return 0


def is_safe_target_path(candidate: Path, base_dir: Path) -> bool:
    """Verify that candidate is strictly within base_dir and not escaping."""
    try:
        cand_resolved = candidate.resolve()
        base_resolved = base_dir.resolve()
        return cand_resolved.is_relative_to(base_resolved)
    except (ValueError, OSError):
        return False


def scan_junk(start_dir: Path) -> List[Tuple[Path, int, str]]:
    """Recursively scan start_dir for safe-listed junk files and directories."""
    results: List[Tuple[Path, int, str]] = []
    base_resolved = start_dir.resolve()

    def _walk(curr: Path) -> None:
        try:
            entries = list(curr.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            # Reject symlinks to prevent directory traversal and symlink hijacking
            if entry.is_symlink():
                continue

            name = entry.name
            if name == ".git":
                continue

            # Verify that the entry is strictly within start_dir
            if not is_safe_target_path(entry, base_resolved):
                continue

            if entry.is_dir():
                if name in SAFE_DIRS:
                    sz = _get_item_size(entry)
                    results.append((entry, sz, "directory"))
                else:
                    _walk(entry)
            elif entry.is_file():
                is_match = False
                if name in SAFE_FILES:
                    is_match = True
                else:
                    for pattern in SAFE_FILES:
                        if pattern.startswith("*.") and name.endswith(pattern[1:]):
                            is_match = True
                            break
                if is_match:
                    sz = _get_item_size(entry)
                    results.append((entry, sz, "file"))

    _walk(start_dir)
    return results


def render_clean(
    theme: Theme,
    mascot_loader: MascotLoader,
    target_dir: Optional[Path] = None,
    yes: bool = False,
    dry_run: bool = False,
    wait_for_enter: bool = True,
    animations_enabled: bool = True,
) -> None:
    """Render Clean screen, scan directory, confirm, and remove junk items safely."""
    console.clear()
    console.print()
    subtitle = "クリーン  •  Dry Run Preview" if dry_run else "クリーン  •  Clean Temporary Files"
    console.print(Align.center(build_header("P A K U   C L E A N", subtitle, theme)))
    console.print()

    target = (target_dir or Path.cwd()).resolve()

    if not target.exists() or not target.is_dir():
        console.print(Align.center(build_mascot_panel(mascot_loader.load("error"), theme)))
        console.print()
        console.print(Align.center(
            Text(f"Error: Target path '{target}' does not exist or is not a directory.", style=theme.error)
        ))
        console.print()
        if wait_for_enter:
            console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
            input()
        return

    with spinner_task(console, f"Scanning {target.name} for junk files...", duration=0.6, color=theme.primary, enabled=animations_enabled):
        items = scan_junk(target)

    console.print(Align.center(build_mascot_panel(mascot_loader.load("happy" if not items else "thinking"), theme)))
    console.print()

    if not items:
        content = Text()
        content.append(f"  ✓  No temporary or junk files found in {target.name}.\n", style=f"bold {theme.success}")
        content.append("  きれい！  Workspace is completely clean.", style=theme.muted)
        console.print(Align.center(framed_section(content, "Scan Results", theme)))
        console.print()
        if wait_for_enter:
            console.print(Align.center(
                styled_line(("Press Enter to return.", theme.muted))
            ))
            input()
        return

    total_bytes = sum(sz for _, sz, _ in items)

    table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    table.add_column("Type", width=10, style=theme.accent)
    table.add_column("Path", style=theme.text)
    table.add_column("Reclaimable", width=12, justify="right", style=theme.highlight)

    for item_path, sz, item_type in items:
        try:
            rel_path = item_path.relative_to(target)
        except ValueError:
            rel_path = item_path
        table.add_row(f"[{item_type}]", str(rel_path), _format_size(sz))

    card_title = "Dry Run: Proposed Deletions" if dry_run else "Junk Files Detected"
    console.print(Align.center(framed_section(table, card_title, theme)))
    console.print()

    summary_text = Text()
    summary_text.append(f"Target: {target}\n", style=theme.muted)
    summary_text.append(f"Found {len(items)} item(s)  ·  Reclaimable space: ", style=theme.text)
    summary_text.append(_format_size(total_bytes), style=f"bold {theme.primary}")
    console.print(Align.center(summary_text))
    console.print()

    if dry_run:
        console.print(Align.center(
            styled_line(("[DRY RUN] Preview only. No files were deleted.", f"bold {theme.warning}"))
        ))
        console.print()
        if wait_for_enter:
            console.print(Align.center(
                styled_line(("Press Enter to return.", theme.muted))
            ))
            input()
        return

    confirmed = yes
    if not yes:
        console.print(Align.center(
            styled_line(("Delete these items? [y/N] ", f"bold {theme.warning}"))
        ))
        console.print()
        try:
            answer = input("  > ").strip().lower()
            confirmed = answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            confirmed = False

    if not confirmed:
        console.print(Align.center(build_mascot_panel(mascot_loader.load("idle"), theme)))
        console.print()
        console.print()
        console.print(Align.center(
            styled_line(("Operation cancelled. No files were deleted.", theme.muted))
        ))
        console.print()
        if wait_for_enter:
            console.print(Align.center(
                styled_line(("Press Enter to return.", theme.muted))
            ))
            input()
        return

    # Delete confirmed items safely
    removed_count = 0
    freed_bytes = 0
    failures: List[Tuple[Path, str]] = []

    if animations_enabled:
        progress_bar(console, "Removing items", steps=len(items), color=theme.primary, enabled=True)

    for item_path, sz, item_type in items:
        # Re-verify path safety immediately before removal
        if not is_safe_target_path(item_path, target) or item_path.is_symlink():
            failures.append((item_path, "Rejected unsafe path or symlink"))
            continue

        try:
            if item_path.is_dir():
                shutil.rmtree(item_path)
            elif item_path.is_file():
                item_path.unlink()
            removed_count += 1
            freed_bytes += sz
        except Exception as e:
            failures.append((item_path, str(e)))

    final_state = "thinking" if failures else "success"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(final_state), theme)))
    console.print()

    console.print()
    if removed_count > 0:
        res_text = Text()
        res_text.append("✓  Successfully cleaned ", style=theme.success)
        res_text.append(f"{removed_count} item(s)", style=f"bold {theme.primary}")
        res_text.append(f" ({_format_size(freed_bytes)} freed)!", style=theme.success)
        console.print(Align.center(res_text))
        console.print(Align.center(
            styled_line(("完了！  Workspace tidy.", theme.muted))
        ))

    if failures:
        console.print()
        console.print(Align.center(
            Text(f"Failed to remove {len(failures)} item(s):", style=theme.error)
        ))
        for fail_path, err in failures:
            console.print(Align.center(
                styled_line((f"  ✗ {fail_path.name}: {err}", theme.muted))
            ))

    console.print()
    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
