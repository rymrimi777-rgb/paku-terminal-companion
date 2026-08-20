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
from contextlib import contextmanager
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


@contextmanager
def spinner_task(console: Console, message: str, duration: float = 1.0,
                 color: str = "cyan", enabled: bool = True):
    """
    Context manager that displays a spinner for at least `duration` seconds
    while running the wrapped block concurrently to avoid CPU bottlenecks.
    """
    if not enabled:
        console.print(f"  {message}", style=color)
        yield
        return

    start_time = time.time()
    with console.status(f"[{color}]  {message}[/]", spinner="dots", spinner_style=color):
        yield

    # Enforce minimum duration for UX aesthetics (Fake Loading)
    elapsed = time.time() - start_time
    if elapsed < duration:
        time.sleep(duration - elapsed)


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


@contextmanager
def dot_animation(console: Console, message: str, cycles: int = 3,
                  color: str = "cyan", enabled: bool = True):
    """
    Context manager for dot animation, guaranteeing minimum cycle time.
    """
    if not enabled:
        console.print(f"  {message}", style=color)
        yield
        return

    start_time = time.time()
    target_duration = cycles * 0.75
    with console.status(f"[{color}]  {message}...[/]", spinner="point", spinner_style=color):
        yield

    elapsed = time.time() - start_time
    if elapsed < target_duration:
        time.sleep(target_duration - elapsed)


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
