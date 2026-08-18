"""
Paku System Info Feature
========================
Displays system & environment details in a styled panel.
"""

from __future__ import annotations

import os
import sys
import platform
import getpass
import shutil
import subprocess
import ctypes
from pathlib import Path

from rich.console import Console
from rich.align import Align
from rich.text import Text

from paku import __version__
from paku.ui.themes import Theme
from paku.ui.terminal import styled_line, framed_section, build_header
from paku.ui.animations import spinner_task
from paku.config.settings import CONFIG_FILE

console = Console(legacy_windows=False)


def _get_total_ram() -> str:
    """Best-effort RAM calculation without third-party dependencies."""
    system = platform.system()
    try:
        if system == "Windows":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                gb = stat.ullTotalPhys / (1024 ** 3)
                return f"{gb:.1f} GB"
        elif system == "Linux":
            meminfo = Path("/proc/meminfo")
            if meminfo.exists():
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        kb = int(parts[1])
                        gb = kb / (1024 ** 2)
                        return f"{gb:.1f} GB"
        elif system == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            gb = int(out) / (1024 ** 3)
            return f"{gb:.1f} GB"
    except Exception:
        pass
    return "unknown"


def render_info(theme: Theme, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render System Information screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   I N F O", "システム情報  •  System Overview", theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Gathering system info...", duration=0.6, color=theme.primary, enabled=True)

    term_size = shutil.get_terminal_size()
    total_ram = _get_total_ram()

    info_pairs = [
        ("Paku Version", f"v{__version__}", theme.highlight),
        ("OS User",     getpass.getuser(), theme.secondary),
        ("Hostname",    platform.node(), theme.text),
        ("OS Platform", f"{platform.system()} {platform.release()}", theme.text),
        ("Architecture", platform.machine(), theme.text),
        ("Python Version", sys.version.split()[0], theme.accent),
        ("CPU Cores",   str(os.cpu_count() or "unknown"), theme.text),
        ("Total RAM",   total_ram, theme.highlight),
        ("Terminal Size", f"{term_size.columns} × {term_size.lines}", theme.muted),
        ("Working Dir", str(Path.cwd()), theme.muted),
        ("Config File", str(CONFIG_FILE), theme.muted),
    ]

    panel_text = Text()
    for label, val, val_style in info_pairs:
        panel_text.append(f"  {label:<16}", style=theme.muted)
        panel_text.append(f"{val}\n", style=val_style)

    console.print(Align.center(framed_section(panel_text, "System Specifications", theme)))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
