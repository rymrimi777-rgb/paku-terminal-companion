"""
Paku Mascot System
==================
Loads ASCII artwork from assets/ascii/<state>.txt files.

Usage:
    mascot = MascotLoader(assets_dir)
    art    = mascot.load("idle")

Rules:
- Preserves every space, newline, indent, and character exactly.
- Falls back to idle.txt if a state file is missing.
- Never trims, wraps, or reformats the artwork.
"""

from pathlib import Path
from typing import Optional


# States that Paku recognises
MASCOT_STATES = ("idle", "happy", "thinking", "working", "success", "error")


class MascotLoader:
    """Loads mascot ASCII art from the assets/ascii directory."""

    def __init__(self, assets_dir: Path) -> None:
        self.ascii_dir = assets_dir / "ascii"

    def load(self, state: str = "idle") -> str:
        """
        Load the ASCII art for the given state.

        If the requested file does not exist, falls back to 'idle'.
        If 'idle' is also missing, returns a minimal built-in placeholder.
        """
        target = self._path_for(state)
        if not target.exists() and state != "idle":
            target = self._path_for("idle")

        if target.exists():
            return target.read_text(encoding="utf-8")

        # Absolute last-resort built-in placeholder
        return _BUILTIN_PLACEHOLDER

    def _path_for(self, state: str) -> Path:
        return self.ascii_dir / f"{state}.txt"

    def state_exists(self, state: str) -> bool:
        return self._path_for(state).exists()


# ─── Built-in Placeholder ────────────────────────────────────────────────────
# Used ONLY if no ASCII files are present at all.
# Replace with your own artwork by dropping files into assets/ascii/

_BUILTIN_PLACEHOLDER = r"""
    ╭──────────────╮
    │  (  ◕ ‿ ◕  ) │
    │   \  Paku  / │
    │    ‾‾‾‾‾‾   │
    ╰──────────────╯
"""
