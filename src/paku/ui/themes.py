"""
Paku Theme System
=================
Centralized color/style configuration.
All UI components reference semantic names (primary, secondary, etc.)
and never use raw color values directly.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Theme:
    name: str
    display_name: str
    primary: str
    secondary: str
    accent: str
    text: str
    muted: str
    success: str
    error: str
    warning: str
    border: str
    title: str
    subtitle: str
    highlight: str
    dim: str


# ─── Theme Definitions ────────────────────────────────────────────────────────

THEMES: Dict[str, Theme] = {
    "cyan": Theme(
        name="cyan",
        display_name="Cyan",
        primary="bright_cyan",
        secondary="cyan",
        accent="bright_white",
        text="white",
        muted="bright_black",        # gray
        success="bright_green",
        error="bright_red",
        warning="bright_yellow",
        border="cyan",
        title="bold bright_cyan",
        subtitle="cyan",
        highlight="bold bright_white",
        dim="bright_black",
    ),
    "sakura": Theme(
        name="sakura",
        display_name="Sakura",
        primary="bright_magenta",
        secondary="magenta",
        accent="bright_white",
        text="white",
        muted="bright_black",
        success="bright_green",
        error="bright_red",
        warning="bright_yellow",
        border="magenta",
        title="bold bright_magenta",
        subtitle="magenta",
        highlight="bold bright_white",
        dim="bright_black",
    ),
    "lavender": Theme(
        name="lavender",
        display_name="Lavender",
        primary="bright_blue",
        secondary="blue",
        accent="bright_white",
        text="white",
        muted="bright_black",
        success="bright_green",
        error="bright_red",
        warning="bright_yellow",
        border="blue",
        title="bold bright_blue",
        subtitle="blue",
        highlight="bold bright_white",
        dim="bright_black",
    ),
    "midnight": Theme(
        name="midnight",
        display_name="Midnight",
        primary="bright_blue",
        secondary="cyan",
        accent="bright_cyan",
        text="bright_white",
        muted="bright_black",
        success="bright_green",
        error="bright_red",
        warning="bright_yellow",
        border="bright_blue",
        title="bold bright_blue",
        subtitle="cyan",
        highlight="bold bright_cyan",
        dim="bright_black",
    ),
    "monochrome": Theme(
        name="monochrome",
        display_name="Monochrome",
        primary="bright_white",
        secondary="white",
        accent="bright_white",
        text="white",
        muted="bright_black",
        success="bright_white",
        error="white",
        warning="white",
        border="white",
        title="bold bright_white",
        subtitle="white",
        highlight="bold bright_white",
        dim="bright_black",
    ),
}

THEME_LIST = list(THEMES.keys())
DEFAULT_THEME = "cyan"


def get_theme(name: str) -> Theme:
    """Return a Theme by name, falling back to the default if unknown."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])
