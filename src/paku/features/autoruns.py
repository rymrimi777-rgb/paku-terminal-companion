"""
Paku Autoruns Feature
======================
Read-only enumeration of Windows auto-start locations.
Inspired by Sysinternals Autoruns.
"""

from __future__ import annotations

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None

from rich.console import Console
from rich.align import Align
from rich.text import Text

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel
from paku.ui.animations import spinner_task, dot_animation
from paku.features.scan import _read_startup_folder, _read_run_key

console = Console(legacy_windows=False)


def _get_registry_run_entries() -> List[Tuple[str, str, str]]:
    """Get all Run/RunOnce entries from HKCU and HKLM."""
    entries: List[Tuple[str, str, str]] = []  # (location, name, target)
    
    if sys.platform != "win32" or winreg is None:
        return entries

    # HKCU Run and RunOnce
    for key_name in ["Run", "RunOnce"]:
        path = rf"Software\Microsoft\Windows\CurrentVersion\{key_name}"
        for name, target in _read_run_key(winreg.HKEY_CURRENT_USER, path):
            entries.append((f"HKCU\\{key_name}", name, target))

    # HKLM Run and RunOnce
    for key_name in ["Run", "RunOnce"]:
        path = rf"Software\Microsoft\Windows\CurrentVersion\{key_name}"
        for name, target in _read_run_key(winreg.HKEY_LOCAL_MACHINE, path):
            entries.append((f"HKLM\\{key_name}", name, target))

    return entries


def _get_startup_folders() -> List[Tuple[str, str, str]]:
    """Get entries from current user and all-users startup folders."""
    entries: List[Tuple[str, str, str]] = []  # (location, name, target)
    
    if sys.platform != "win32":
        return entries

    # Current user startup folder
    appdata = os.environ.get("APPDATA")
    if appdata:
        startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for name, target in _read_startup_folder(startup_dir):
            entries.append(("Startup (User)", name, target))

    # All-users startup folder
    programdata = os.environ.get("ProgramData")
    if programdata:
        startup_dir = Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for name, target in _read_startup_folder(startup_dir):
            entries.append(("Startup (All Users)", name, target))

    return entries


def _get_logon_tasks() -> List[Tuple[str, str]]:
    """Get scheduled tasks with logon triggers."""
    tasks: List[Tuple[str, str]] = []  # (task name, program)
    
    if sys.platform != "win32":
        return tasks

    try:
        # Use CSV format for more reliable parsing
        cmd = ["schtasks", "/query", "/fo", "CSV", "/v"]
        out = subprocess.check_output(cmd, text=True, errors="replace", stderr=subprocess.DEVNULL, timeout=30)
        
        lines = out.splitlines()
        for line in lines:
            if "Logon" in line and "TaskName" not in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    task_name = parts[0].strip('"')
                    # Try to extract the program from the task
                    # This is simplified - full trigger parsing would be more complex
                    if task_name and not task_name.startswith("\\"):
                        tasks.append((task_name, "See Task Scheduler for details"))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
        pass

    return tasks


def _get_automatic_services() -> Optional[List[Tuple[str, str]]]:
    """Get services set to Automatic startup."""
    services: List[Tuple[str, str]] = []  # (display name, path)
    
    if sys.platform != "win32" or winreg is None:
        return services

    try:
        # Read directly from registry to avoid PowerShell overhead
        key_path = r"SYSTEM\CurrentControlSet\Services"
        services_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        
        idx = 0
        while True:
            try:
                svc_name = winreg.EnumKey(services_key, idx)
                idx += 1
                
                try:
                    svc_key = winreg.OpenKey(services_key, svc_name, 0, winreg.KEY_READ)
                    start_val, _ = winreg.QueryValueEx(svc_key, "Start")
                    
                    # Start == 2 signifies Automatic startup
                    if start_val == 2:
                        try:
                            display_name, _ = winreg.QueryValueEx(svc_key, "DisplayName")
                        except OSError:
                            display_name = svc_name
                            
                        try:
                            image_path, _ = winreg.QueryValueEx(svc_key, "ImagePath")
                        except OSError:
                            image_path = ""
                            
                        if image_path:
                            services.append((str(display_name), str(image_path)))
                    winreg.CloseKey(svc_key)
                except OSError:
                    continue
            except OSError:
                break
        winreg.CloseKey(services_key)
        
    except Exception as exc:
        print(f"Paku: could not query automatic services via Registry: {exc}", file=sys.stderr)
        return None

    return services


def render_autoruns(theme: Theme, mascot_loader: MascotLoader, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Autoruns enumeration screen."""
    if sys.platform != "win32":
        console.clear()
        console.print()
        console.print(Align.center(
            styled_line(("This feature is Windows-only.", theme.muted))
        ))
        console.print()
        if wait_for_enter:
            console.print(Align.center(
                styled_line(("Press Enter to return.", theme.muted))
            ))
            input()
        return

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   A U T O R U N S", "自動起動  •  Auto-Start Enumeration", theme)))
    console.print()
    console.print(Align.center(build_mascot_panel(mascot_loader.load("idle"), theme)))
    console.print()

    with spinner_task(console, "Enumerating auto-start entries...", duration=1.0, color=theme.primary, enabled=animations_enabled):
        # Collect all entries
        registry_entries = _get_registry_run_entries()
        startup_folders = _get_startup_folders()
        logon_tasks = _get_logon_tasks()
        auto_services = _get_automatic_services()

    total_count = len(registry_entries) + len(startup_folders) + len(logon_tasks) + len(auto_services or [])

    # Summary
    summary = Text()
    summary.append(f"  Found {total_count} auto-start entries across 4 categories\n", style=f"bold {theme.primary}")
    console.print(Align.center(framed_section(summary, "Summary", theme)))
    console.print()

    # Registry Run/RunOnce
    reg_text = Text()
    if not registry_entries:
        reg_text.append("  No registry Run/RunOnce entries found.\n", style=theme.muted)
    else:
        for location, name, target in registry_entries[:10]:
            reg_text.append(f"  [{location}]\n", style=theme.secondary)
            reg_text.append(f"    • {name}\n", style=theme.text)
            reg_text.append(f"      {target[:60]}...\n" if len(target) > 60 else f"      {target}\n", style=theme.muted)
        if len(registry_entries) > 10:
            reg_text.append(f"    ...and {len(registry_entries) - 10} more entries\n", style=theme.dim)
    console.print(Align.center(framed_section(reg_text, "1. Registry Run/RunOnce", theme)))
    console.print()

    # Startup Folders
    folder_text = Text()
    if not startup_folders:
        folder_text.append("  No startup folder entries found.\n", style=theme.muted)
    else:
        for location, name, target in startup_folders[:10]:
            folder_text.append(f"  [{location}]\n", style=theme.secondary)
            folder_text.append(f"    • {name}\n", style=theme.text)
            folder_text.append(f"      {target}\n", style=theme.muted)
        if len(startup_folders) > 10:
            folder_text.append(f"    ...and {len(startup_folders) - 10} more entries\n", style=theme.dim)
    console.print(Align.center(framed_section(folder_text, "2. Startup Folders", theme)))
    console.print()

    # Scheduled Tasks (Logon)
    task_text = Text()
    if not logon_tasks:
        task_text.append("  No logon-triggered scheduled tasks found.\n", style=theme.muted)
    else:
        for name, program in logon_tasks[:10]:
            task_text.append(f"  • {name}\n", style=theme.text)
            task_text.append(f"    {program}\n", style=theme.muted)
        if len(logon_tasks) > 10:
            task_text.append(f"    ...and {len(logon_tasks) - 10} more tasks\n", style=theme.dim)
    console.print(Align.center(framed_section(task_text, "3. Scheduled Tasks (Logon Trigger)", theme)))
    console.print()

    # Automatic Services
    svc_text = Text()
    if auto_services is None:
        svc_text.append("  Could not query services (see console for details).\n", style=theme.warning)
    elif not auto_services:
        svc_text.append("  No automatic startup services found.\n", style=theme.muted)
    else:
        for display_name, path in auto_services[:10]:
            svc_text.append(f"  • {display_name}\n", style=theme.text)
            svc_text.append(f"    {path[:60]}...\n" if len(path) > 60 else f"    {path}\n", style=theme.muted)
        if len(auto_services) > 10:
            svc_text.append(f"    ...and {len(auto_services) - 10} more services\n", style=theme.dim)
    console.print(Align.center(framed_section(svc_text, "4. Automatic Startup Services", theme)))
    console.print()

    # Disclaimer
    console.print(Align.center(
        styled_line(("To disable an entry, use Task Scheduler, Services, or msconfig — Paku doesn't modify these yet.", theme.muted))
    ))
    console.print()

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
