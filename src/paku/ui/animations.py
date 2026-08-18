"""
Paku Animation System
=====================
Lightweight animations for the terminal.

Animations are:
- Fast and subtle
- Skippable / disableable
- Safe on all terminal types
"""

import time
import sys
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    SpinnerColumn,
)
from rich.live import Live
from rich.text import Text


def spinner_task(console: Console, message: str, duration: float = 1.5,
                 color: str = "cyan", enabled: bool = True) -> None:
    """
    Display a spinner for `duration` seconds with `message`.
    Falls back silently if animations are disabled.
    """
    if not enabled:
        console.print(f"  {message}", style=color)
        return

    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    with Live(console=console, refresh_per_second=12) as live:
        while time.time() < end_time:
            frame = frames[i % len(frames)]
            live.update(Text(f"  {frame}  {message}", style=color))
            time.sleep(0.08)
            i += 1


def progress_bar(console: Console, message: str, steps: int = 10,
                 color: str = "cyan", enabled: bool = True) -> None:
    """
    Display a simple progress bar that fills over `steps` ticks.
    """
    if not enabled:
        console.print(f"  ✓  {message}", style=color)
        return

    with Progress(
        TextColumn(f"  [bold {color}]{message}[/]"),
        BarColumn(bar_width=28, complete_style=color, finished_style=color),
        TextColumn(f"[{color}]{{task.percentage:>3.0f}}%[/]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=steps)
        for _ in range(steps):
            progress.advance(task)
            time.sleep(0.04)


def dot_animation(console: Console, message: str, cycles: int = 3,
                  color: str = "cyan", enabled: bool = True) -> None:
    """
    Classic "Checking..." → "Checking.." → "Checking..." dot animation.
    """
    if not enabled:
        console.print(f"  {message}", style=color)
        return

    states = [f"{message}.", f"{message}..", f"{message}..."]
    with Live(console=console, refresh_per_second=4) as live:
        for _ in range(cycles):
            for s in states:
                live.update(Text(f"  {s}", style=color))
                time.sleep(0.25)


def type_in(console: Console, text: str, color: str = "white",
            delay: float = 0.03, enabled: bool = True) -> None:
    """
    Typewriter effect for a single line of text.
    """
    if not enabled:
        console.print(text, style=color)
        return

    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()
