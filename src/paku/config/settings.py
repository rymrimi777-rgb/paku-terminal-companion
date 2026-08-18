"""
Paku Settings & Configuration
==============================
Persists user preferences to %APPDATA%/Paku/config.json on Windows.
Falls back to ~/.paku/config.json on other platforms.

Schema (all fields optional — defaults are used for missing keys):
{
    "theme":              "cyan",
    "animations_enabled": true
}
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from paku.ui.themes import DEFAULT_THEME, THEME_LIST


# ─── Config directory resolution ─────────────────────────────────────────────

def _config_dir() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", Path.home())
        return Path(appdata) / "Paku"
    return Path.home() / ".paku"


CONFIG_DIR  = _config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"


# ─── Defaults ────────────────────────────────────────────────────────────────

_DEFAULTS: Dict[str, Any] = {
    "theme":              DEFAULT_THEME,
    "animations_enabled": True,
}


# ─── Public API ──────────────────────────────────────────────────────────────

def load_settings() -> Dict[str, Any]:
    """Return the merged settings dict (file values override defaults)."""
    if not CONFIG_FILE.exists():
        return dict(_DEFAULTS)
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**_DEFAULTS, **raw}
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist settings to disk, creating the directory if necessary."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_theme_name(settings: Dict[str, Any]) -> str:
    name = settings.get("theme", DEFAULT_THEME)
    return name if name in THEME_LIST else DEFAULT_THEME


def set_theme(settings: Dict[str, Any], theme_name: str) -> Dict[str, Any]:
    settings = dict(settings)
    settings["theme"] = theme_name
    save_settings(settings)
    return settings


def animations_enabled(settings: Dict[str, Any]) -> bool:
    return bool(settings.get("animations_enabled", True))
