"""
Paku Settings Feature
=====================
Interactive settings manager for application preferences.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from rich.console import Console
from rich.align import Align
from rich.text import Text

from paku.ui.themes import Theme, get_theme
from paku.ui.terminal import styled_line, framed_section, build_header
from paku.ui.animations import dot_animation
from paku.config.settings import (
    load_settings,
    save_settings,
    get_theme_name,
    animations_enabled as is_anim_enabled,
)

console = Console(legacy_windows=False)


def render_settings(
    theme: Theme,
    theme_callback: Optional[Callable[[], None]] = None,
    wait_for_enter: bool = True,
    animations_enabled: bool = True,
) -> None:
    """Render and manage interactive application settings."""
    current_settings = load_settings()

    if animations_enabled:
        console.clear()
        console.print()
        console.print(Align.center(build_header("P A K U   S E T T I N G S", "設定  •  Preferences", theme)))
        console.print()
        dot_animation(console, "Loading settings", cycles=1, color=theme.primary, enabled=True)

    feedback_msg: Optional[Text] = None

    while True:
        current_settings = load_settings()
        th_name = get_theme_name(current_settings)
        th = get_theme(th_name)
        anim_on = is_anim_enabled(current_settings)

        console.clear()
        console.print()
        console.print(Align.center(build_header("P A K U   S E T T I N G S", "設定  •  Preferences", th)))
        console.print()

        content = Text()

        # Item 1: Animations
        content.append("  1  ", style=f"bold {th.accent}")
        content.append(f"{'Animations':<18}", style=th.text)
        if anim_on:
            content.append("ON ", style=f"bold {th.success}")
        else:
            content.append("OFF", style=f"bold {th.error}")
        content.append("         アニメーション\n", style=th.muted)

        # Item 2: Theme
        content.append("  2  ", style=f"bold {th.accent}")
        content.append(f"{'Theme':<18}", style=th.text)
        content.append(f"{th.display_name:<11}", style=f"bold {th.highlight}")
        content.append("テーマ\n", style=th.muted)

        # Item 0: Back
        content.append("  0  ", style=f"bold {th.accent}")
        content.append(f"{'Back':<18}", style=th.text)
        content.append("戻る\n", style=th.muted)

        # Instructional Hint
        content.append("\n  ", style=th.dim)
        content.append("Enter a number to choose · ", style=th.muted)
        content.append("0", style=f"bold {th.accent}")
        content.append(" to go back\n", style=th.muted)
        content.append("  番号を入力してください\n", style=th.dim)

        console.print(Align.center(framed_section(content, "Application Preferences", th)))
        console.print()

        if feedback_msg:
            console.print(Align.center(feedback_msg))
            console.print()
            feedback_msg = None

        try:
            choice = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            new_anim = not anim_on
            current_settings["animations_enabled"] = new_anim
            save_settings(current_settings)
            status_str = "enabled" if new_anim else "disabled"
            status_st = th.success if new_anim else th.error
            feedback_msg = styled_line(
                ("✓  Animations ", f"bold {th.success}"),
                (status_str, f"bold {status_st}"),
                ("!  Changes saved.", th.muted),
            )
        elif choice == "2":
            if theme_callback:
                theme_callback()
                current_settings = load_settings()
                th = get_theme(get_theme_name(current_settings))
                feedback_msg = styled_line(
                    ("✓  Theme updated to ", f"bold {th.success}"),
                    (th.display_name, f"bold {th.primary}"),
                    ("!", th.muted),
                )
            else:
                feedback_msg = None
        elif choice in ("0", ""):
            break
        else:
            feedback_msg = styled_line(("Invalid choice.", th.error))
