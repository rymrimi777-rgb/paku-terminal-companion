"""
Paku Debloat Feature
====================
Remove known Windows consumer bloatware UWP apps.
Current-user scope only, with curated whitelist.
"""

from __future__ import annotations

import sys
import json
import os
import re
import subprocess
from typing import List, Tuple, Set

from rich.console import Console
from rich.align import Align
from rich.text import Text

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel
from paku.ui.animations import spinner_task, dot_animation

console = Console(legacy_windows=False)

_PACKAGE_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


# Hardcoded whitelist of safe-to-remove UWP package family name substrings
# These are well-known non-essential consumer apps commonly included in debloat tools
_BLOAT_WHITELIST: Set[str] = {
    "CandyCrush",
    "XboxGameOverlay",
    "MixedReality.Portal",
    "3DViewer",
    "Microsoft.YourPhone",
    "BingWeather",
    "BingNews",
    "GetHelp",
    "Getstarted",
    "MicrosoftOfficeHub",
    "SkypeApp",
    "ZuneMusic",
    "ZuneVideo",
    "People",
    "Wallet",
    "Messaging",
    "Microsoft.Todos",
    "MicrosoftSolitaireCollection",
    "Microsoft.BingWeather",
    "Microsoft.BingNews",
    "Microsoft.BingSports",
    "Microsoft.BingFinance",
    "Microsoft.3DBuilder",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "Microsoft.Messaging",
    "Microsoft.MicrosoftOfficeHub",
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.People",
    "Microsoft.SkypeApp",
    "Microsoft.Wallet",
    "Microsoft.Windows.Photos",
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.YourPhone",
    "Microsoft.ZuneMusic",
    "Microsoft.ZuneVideo",
}


def _get_installed_packages() -> List[Tuple[str, str]]:
    """Get installed UWP packages matching the whitelist."""
    packages: List[Tuple[str, str]] = []  # (name, package_full_name)
    
    if sys.platform != "win32":
        return packages

    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-AppxPackage | Select Name,PackageFullName | ConvertTo-Json"
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=30)
        data = json.loads(out)
        
        if isinstance(data, list):
            for pkg in data:
                name = pkg.get("Name", "")
                full_name = pkg.get("PackageFullName", "")
                # Check if any whitelist substring matches the package name
                if any(protected_term in name for protected_term in ("Store", "Defender", "Security", "Shell")):
                    # Never remove protected system components, even if the whitelist changes later.
                    continue
                if any(whitelist_sub in name for whitelist_sub in _BLOAT_WHITELIST):
                    packages.append((name, full_name))
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, Exception):
        pass

    return packages


def _remove_package(package_full_name: str) -> Tuple[bool, str]:
    """Remove a single UWP package. Returns (success, message)."""
    if not _PACKAGE_FULL_NAME_RE.fullmatch(package_full_name):
        return (False, "Invalid package name")

    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "$package = [Environment]::GetEnvironmentVariable('PAKU_PACKAGE_FULL_NAME'); "
            "Remove-AppxPackage -Package $package",
        ]
        env = os.environ.copy()
        env["PAKU_PACKAGE_FULL_NAME"] = package_full_name
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30, env=env)
        return (True, "Removed successfully")
    except subprocess.TimeoutExpired:
        return (False, "Timeout during removal")
    except subprocess.CalledProcessError as e:
        return (False, f"Failed: {e.stderr.strip() if e.stderr else 'Unknown error'}")
    except Exception as e:
        return (False, f"Error: {str(e)}")


def render_debloat(theme: Theme, mascot_loader: MascotLoader, wait_for_enter: bool = True, animations_enabled: bool = True) -> None:
    """Render Debloat feature screen."""
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
    console.print(Align.center(build_header("P A K U   D E B L O A T", "不要アプリ削除  •  Remove Bloatware", theme)))
    console.print()
    console.print(Align.center(build_mascot_panel(mascot_loader.load("working"), theme)))
    console.print()

    if animations_enabled:
        spinner_task(console, "Scanning for bloatware packages...", duration=1.0, color=theme.primary, enabled=True)

    packages = _get_installed_packages()
    console.print(Align.center(build_mascot_panel(mascot_loader.load("happy" if not packages else "thinking"), theme)))
    console.print()

    if not packages:
        no_bloat = Text()
        no_bloat.append("  No whitelisted bloatware packages found.\n", style=theme.success)
        no_bloat.append("  Your system is clean!\n", style=theme.muted)
        console.print(Align.center(framed_section(no_bloat, "Scan Results", theme)))
        console.print()
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
        return

    # Interactive selection loop
    selected_indices: Set[int] = set()
    
    while True:
        console.clear()
        console.print()
        console.print(Align.center(build_header("P A K U   D E B L O A T", "不要アプリ削除  •  Remove Bloatware", theme)))
        console.print()

        # Show package list with checkboxes
        list_text = Text()
        list_text.append(f"  Found {len(packages)} bloatware package(s):\n\n", style=f"bold {theme.primary}")
        
        for i, (name, full_name) in enumerate(packages, 1):
            checkbox = "[x]" if i in selected_indices else "[ ]"
            list_text.append(f"  {checkbox}  {i:>2}  {name}\n", style=theme.text)
            list_text.append(f"      {full_name[:60]}...\n" if len(full_name) > 60 else f"      {full_name}\n", style=theme.muted)
        
        console.print(Align.center(framed_section(list_text, "Select Packages to Remove", theme)))
        console.print()
        
        # Instructions
        console.print(Align.center(
            styled_line(("Enter numbers to toggle (e.g., '1,3,5'), 'a' for all, or '0' to cancel.", theme.muted))
        ))
        console.print()

        try:
            choice = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            # Cancel
            console.print()
            console.print(Align.center(
                styled_line(("Cancelled. No packages removed.", theme.muted))
            ))
            console.print()
            break
        elif choice.lower() == "a":
            # Select all
            selected_indices = set(range(1, len(packages) + 1))
        elif choice:
            # Parse numbers
            try:
                parts = choice.replace(",", " ").split()
                for part in parts:
                    idx = int(part)
                    if 1 <= idx <= len(packages):
                        if idx in selected_indices:
                            selected_indices.remove(idx)
                        else:
                            selected_indices.add(idx)
            except ValueError:
                console.print(Align.center(
                    Text("Invalid input. Try again.", style=theme.error)
                ))
                console.print()
                input("  Press Enter to continue...")
                continue

        if selected_indices:
            # Show confirmation
            console.clear()
            console.print()
            console.print(Align.center(build_header("P A K U   D E B L O A T", "不要アプリ削除  •  Remove Bloatware", theme)))
            console.print()

            confirm_text = Text()
            confirm_text.append(f"  Remove {len(selected_indices)} package(s)?\n\n", style=f"bold {theme.warning}")
            
            for idx in sorted(selected_indices):
                name, full_name = packages[idx - 1]
                confirm_text.append(f"  • {name}\n", style=theme.text)
                confirm_text.append(f"    {full_name}\n", style=theme.muted)
            
            console.print(Align.center(framed_section(confirm_text, "Confirm Removal", theme)))
            console.print()
            console.print(Align.center(
                styled_line(("Confirm removal? [y/N]", theme.muted))
            ))
            console.print()

            try:
                confirm = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return

            if confirm == "y":
                # Remove packages
                console.clear()
                console.print()
                console.print(Align.center(build_header("P A K U   D E B L O A T", "不要アプリ削除  •  Remove Bloatware", theme)))
                console.print()

                results_text = Text()
                results_text.append(f"  Removing {len(selected_indices)} package(s)...\n\n", style=f"bold {theme.primary}")
                
                success_count = 0
                for idx in sorted(selected_indices):
                    name, full_name = packages[idx - 1]
                    success, msg = _remove_package(full_name)
                    if success:
                        results_text.append(f"  ✓  {name}\n", style=theme.success)
                        success_count += 1
                    else:
                        results_text.append(f"  ✗  {name}\n", style=theme.error)
                        results_text.append(f"      {msg}\n", style=theme.muted)

                final_state = "success" if success_count == len(selected_indices) else "thinking"
                console.print(Align.center(build_mascot_panel(mascot_loader.load(final_state), theme)))
                console.print()
                
                console.print(Align.center(framed_section(results_text, "Removal Results", theme)))
                console.print()
                console.print(Align.center(
                    styled_line((f"Removed {success_count}/{len(selected_indices)} package(s).", theme.success))
                ))
                console.print()
                console.print(Align.center(
                    styled_line(("Removed apps can be reinstalled from the Microsoft Store if needed.", theme.muted))
                ))
                console.print()
                break
            else:
                # Cancelled confirmation, go back to selection
                continue
        else:
            # No selection, ask to cancel
            console.print()
            console.print(Align.center(
                styled_line(("No packages selected. Press Enter to continue or '0' to cancel.", theme.muted))
            ))
            console.print()
            try:
                cont = input("  > ").strip()
                if cont == "0":
                    console.print()
                    console.print(Align.center(
                        styled_line(("Cancelled. No packages removed.", theme.muted))
                    ))
                    console.print()
                    break
            except (EOFError, KeyboardInterrupt):
                return

    if wait_for_enter:
        console.print(Align.center(
            styled_line(("Press Enter to return.", theme.muted))
        ))
        input()
