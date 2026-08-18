"""
Paku Doctor Feature
===================
Environment diagnostics (read-only checks).
"""

from __future__ import annotations

import os
import sys
import platform
import shutil
import json
import importlib.metadata
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader, MASCOT_STATES
from paku.ui.terminal import styled_line, framed_section, build_header
from paku.ui.animations import spinner_task
from paku.config.settings import CONFIG_DIR, CONFIG_FILE

console = Console(legacy_windows=False)


def run_diagnostics(assets_dir: Path) -> List[Tuple[str, str, str, str]]:
    """Run environment diagnostic checks."""
    results: List[Tuple[str, str, str, str]] = []

    # 1. Python version
    py_ver = sys.version.split()[0]
    if sys.version_info >= (3, 11):
        results.append(("pass", "Python Version", f"Python {py_ver}", "success"))
    else:
        results.append(("warn", "Python Version", f"Python {py_ver} (>=3.11 recommended)", "warning"))

    # 2. OS / platform info
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    results.append(("pass", "OS Platform", os_info, "success"))

    # 3. Terminal encoding
    enc = sys.stdout.encoding or "unknown"
    if enc.lower() in ("utf-8", "utf-8-sig"):
        results.append(("pass", "Terminal Encoding", enc.upper(), "success"))
    else:
        results.append(("warn", "Terminal Encoding", f"{enc} (UTF-8 recommended)", "warning"))

    # 4. Installed package versions
    try:
        rich_ver = importlib.metadata.version("rich")
        typer_ver = importlib.metadata.version("typer")
        results.append(("pass", "Dependencies", f"rich v{rich_ver}, typer v{typer_ver}", "success"))
    except Exception as e:
        results.append(("warn", "Dependencies", f"Error checking versions: {e}", "warning"))

    # 5. Mascot assets present
    ascii_dir = assets_dir / "ascii"
    missing_states = [state for state in MASCOT_STATES if not (ascii_dir / f"{state}.txt").exists()]
    if not missing_states:
        results.append(("pass", "Mascot Assets", f"All {len(MASCOT_STATES)} states found", "success"))
    else:
        results.append(("warn", "Mascot Assets", f"Missing states: {', '.join(missing_states)}", "warning"))

    # 6. Config directory check
    if CONFIG_DIR.exists():
        is_writable = os.access(CONFIG_DIR, os.W_OK)
        if is_writable:
            results.append(("pass", "Config Directory", f"Found & writable ({CONFIG_DIR})", "success"))
        else:
            results.append(("warn", "Config Directory", f"Found but read-only ({CONFIG_DIR})", "warning"))
    else:
        results.append(("warn", "Config Directory", f"Not created yet ({CONFIG_DIR})", "warning"))

    # 7. Config file valid JSON check
    if CONFIG_FILE.exists():
        try:
            json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            results.append(("pass", "Config File", "Valid JSON settings file", "success"))
        except Exception as e:
            results.append(("fail", "Config File", f"Invalid JSON: {e}", "error"))
    else:
        results.append(("pass", "Config File", "Not created yet (defaults in use)", "success"))

    # 8. Free disk space on config drive
    try:
        usage = shutil.disk_usage(CONFIG_DIR.anchor if CONFIG_DIR.anchor else ".")
        free_gb = usage.free / (1024 ** 3)
        results.append(("pass", "Disk Free Space", f"{free_gb:.2f} GB free", "success"))
    except Exception as e:
        results.append(("warn", "Disk Free Space", f"Could not determine ({e})", "warning"))

    # 9. Is paku on PATH?
    paku_path = shutil.which("paku")
    if paku_path:
        results.append(("pass", "Paku Executable", f"On PATH ({paku_path})", "success"))
    else:
        results.append(("warn", "Paku Executable", "Not found on PATH (run 'pip install -e .')", "warning"))

    return results


def render_doctor(theme: Theme, mascot_loader: MascotLoader, assets_dir: Path,
                  wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render the Doctor diagnostic screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   D O C T O R", "システム診断  •  System Diagnostics", theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Running diagnostics...", duration=0.8, color=theme.primary, enabled=True)

    diagnostics = run_diagnostics(assets_dir)
    n_ok = sum(1 for status, _, _, _ in diagnostics if status == "pass")
    n_warn = sum(1 for status, _, _, _ in diagnostics if status == "warn")
    n_fail = sum(1 for status, _, _, _ in diagnostics if status == "fail")

    table = Table(box=None, expand=True, show_header=False, pad_edge=False)
    table.add_column("Status", width=6, justify="center")
    table.add_column("Label", width=22)
    table.add_column("Detail")

    for status, label, detail, _ in diagnostics:
        if status == "pass":
            mark = Text("✓ OK", style=theme.success)
            lbl = Text(label, style=theme.text)
            det = Text(detail, style=theme.muted)
        elif status == "warn":
            mark = Text("! WARN", style=theme.warning)
            lbl = Text(label, style=theme.accent)
            det = Text(detail, style=theme.muted)
        else:
            mark = Text("✗ FAIL", style=theme.error)
            lbl = Text(label, style=f"bold {theme.error}")
            det = Text(detail, style=theme.text)
        table.add_row(mark, lbl, det)

    console.print(Align.center(framed_section(table, "Diagnostic Results", theme)))
    console.print()

    summary = Text()
    summary.append(f"{n_ok} ok", style=theme.success)
    summary.append("  ·  ", style=theme.dim)
    summary.append(f"{n_warn} warnings", style=theme.warning if n_warn > 0 else theme.dim)
    summary.append("  ·  ", style=theme.dim)
    summary.append(f"{n_fail} failed", style=theme.error if n_fail > 0 else theme.dim)

    console.print(Align.center(summary))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
