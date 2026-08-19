"""
Paku Scan Feature
=================
Lightweight security & system hygiene check (read-only).
"""

from __future__ import annotations

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import List, Tuple

try:
    import winreg
except ImportError:
    winreg = None

from rich.console import Console
from rich.align import Align
from rich.text import Text

from paku.ui.themes import Theme
from paku.ui.terminal import styled_line, framed_section, build_header
from paku.ui.animations import dot_animation

console = Console(legacy_windows=False)


def _check_windows_defender() -> Tuple[str, str, str]:
    """Check Windows Defender real-time protection via PowerShell."""
    if sys.platform != "win32":
        return ("info", "Windows Defender", "N/A on this OS")

    try:
        cmd = ["powershell", "-NoProfile", "-Command", "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled | ConvertTo-Json"]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=30).strip()
        data = json.loads(out)
        realtime = data.get("RealTimeProtectionEnabled", False)
        av_enabled = data.get("AntivirusEnabled", False)

        if realtime and av_enabled:
            return ("pass", "Windows Defender", "Real-Time Protection Active & Enabled")
        elif av_enabled:
            return ("warn", "Windows Defender", "Antivirus Enabled (Real-Time Protection OFF)")
        else:
            return ("warn", "Windows Defender", "Protection Disabled or third-party AV active")
    except Exception:
        return ("warn", "Windows Defender", "Status unavailable (may require admin / third-party AV)")


def _scan_double_extensions() -> List[Path]:
    """Scan Desktop & Downloads for suspicious double extensions."""
    suspicious: List[Path] = []
    targets = [Path.home() / "Desktop", Path.home() / "Downloads"]
    doc_exts = {".pdf", ".doc", ".docx", ".jpg", ".png", ".txt", ".xlsx"}
    exec_exts = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".js"}

    for target in targets:
        if not target.exists():
            continue
        try:
            for item in target.iterdir():
                if item.is_file():
                    parts = item.name.lower().split(".")
                    if len(parts) >= 3:
                        ext2 = "." + parts[-2]
                        ext1 = "." + parts[-1]
                        if ext2 in doc_exts and ext1 in exec_exts:
                            suspicious.append(item)
        except OSError:
            pass
    return suspicious


def _read_startup_folder(startup_dir: Path) -> List[Tuple[str, str]]:
    """Read startup folder entries."""
    entries: List[Tuple[str, str]] = []
    if startup_dir.exists():
        for item in startup_dir.iterdir():
            if item.is_file():
                entries.append((item.name, str(item)))
    return entries


def _read_run_key(hive: int, key_path: str) -> List[Tuple[str, str]]:
    """Read a registry Run/RunOnce key."""
    entries: List[Tuple[str, str]] = []
    if winreg is None:
        return entries

    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
        idx = 0
        while True:
            try:
                val_name, val_data, _ = winreg.EnumValue(key, idx)
                entries.append((val_name, str(val_data)))
                idx += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except OSError:
        pass
    return entries


def _get_startup_entries() -> List[Tuple[str, str]]:
    """List startup items on Windows."""
    entries: List[Tuple[str, str]] = []
    if sys.platform != "win32" or winreg is None:
        return [("N/A", "Startup enumeration supported on Windows")]

    # 1. Startup folder (current user)
    appdata = os.environ.get("APPDATA")
    if appdata:
        startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        entries.extend(_read_startup_folder(startup_dir))

    # 2. Registry HKCU Run
    entries.extend(_read_run_key(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"))

    return entries


def _get_listening_ports() -> List[Tuple[str, str]]:
    """List local listening network ports."""
    ports: List[Tuple[str, str]] = []
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 4 and parts[0].upper() == "TCP" and "LISTENING" in line.upper():
                    local_addr = parts[1]
                    pid = parts[-1]
                    ports.append((local_addr, f"PID {pid}"))
        else:
            out = subprocess.check_output(["netstat", "-tuln"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if "LISTEN" in line:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        ports.append((parts[3], "Listening"))
    except Exception:
        pass
    return ports[:10]  # Show top 10


def render_scan(theme: Theme, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Scan Hygiene screen."""
    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   S C A N", "セキュリティ点検  •  System Hygiene Check", theme)))
    console.print()

    if animations_enabled:
        dot_animation(console, "Checking Defender status", cycles=1, color=theme.primary, enabled=True)

    defender_status, defender_label, defender_detail = _check_windows_defender()

    if animations_enabled:
        dot_animation(console, "Scanning Desktop & Downloads", cycles=1, color=theme.primary, enabled=True)

    suspicious_files = _scan_double_extensions()

    if animations_enabled:
        dot_animation(console, "Reading startup entries & listening ports", cycles=1, color=theme.primary, enabled=True)

    startup_entries = _get_startup_entries()
    listening_ports = _get_listening_ports()

    # Section 1: Antivirus & Protection
    def_text = Text()
    def_text.append(f"  {defender_label:<20}", style=f"bold {theme.accent}")
    if defender_status == "pass":
        def_text.append(" [Active] ", style=theme.success)
    elif defender_status == "warn":
        def_text.append(" [Warning] ", style=theme.warning)
    else:
        def_text.append(" [Info] ", style=theme.muted)
    def_text.append(f"{defender_detail}\n", style=theme.text)
    console.print(Align.center(framed_section(def_text, "1. Real-Time Protection", theme)))
    console.print()

    # Section 2: Suspicious Files
    file_text = Text()
    if not suspicious_files:
        file_text.append("  ✓  No suspicious double-extension files found on Desktop/Downloads.", style=theme.success)
    else:
        file_text.append(f"  !  Found {len(suspicious_files)} double-extension file(s):\n", style=theme.warning)
        for f in suspicious_files:
            file_text.append(f"     • {f.name}\n", style=theme.text)
            file_text.append(f"       ({f})\n", style=theme.muted)
    console.print(Align.center(framed_section(file_text, "2. Suspicious File Check", theme)))
    console.print()

    # Section 3: Startup Entries
    start_text = Text()
    if not startup_entries:
        start_text.append("  No user startup entries found.", style=theme.muted)
    else:
        for name, target in startup_entries[:8]:
            start_text.append(f"  • {name:<22}", style=theme.text)
            start_text.append(f"{target}\n", style=theme.muted)
        if len(startup_entries) > 8:
            start_text.append(f"    ...and {len(startup_entries) - 8} more entries", style=theme.dim)
    console.print(Align.center(framed_section(start_text, "3. Startup Programs & Registry", theme)))
    console.print()

    # Section 4: Local Listening Ports
    port_text = Text()
    if not listening_ports:
        port_text.append("  No active listening ports detected.", style=theme.muted)
    else:
        for addr, proc in listening_ports:
            port_text.append(f"  • {addr:<22}", style=theme.secondary)
            port_text.append(f"{proc}\n", style=theme.muted)
    console.print(Align.center(framed_section(port_text, "4. Local Listening Network Ports", theme)))
    console.print()

    # Disclaimer
    console.print(Align.center(
        styled_line(("⚠️  This is a basic hygiene check, not antivirus — for anything suspicious, run a full scan with Windows Defender.", theme.muted))
    ))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
