"""
Paku Terminal UI
================
Renders the main interface panels using Rich.
All colours are resolved through the active Theme — never hardcoded.
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.rule import Rule
from rich import box
from rich.console import RenderableType
import sys
import io

# Force UTF-8 so Japanese + Unicode chars render correctly on all Windows terminals.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from paku.ui.themes import Theme, get_theme
from paku.ui.mascot import MascotLoader


# ─── Console singleton ────────────────────────────────────────────────────────
console = Console(legacy_windows=False)


# ─── Reusable UI Helpers ─────────────────────────────────────────────────────

def styled_line(*parts: tuple[str, str]) -> Text:
    """Build a Text object from (segment, style) tuples."""
    line = Text()
    for segment, style in parts:
        line.append(segment, style=style)
    return line


def framed_section(content: RenderableType, title: str, theme: Theme, box_style=box.ROUNDED) -> Panel:
    """Wrap content in a consistent bordered card with a styled title."""
    return Panel(
        content,
        title=f"[bold {theme.primary}]{title}[/]" if title else None,
        title_align="left",
        border_style=theme.border,
        box=box_style,
        padding=(1, 2),
        width=76,
    )


def build_header(title: str, subtitle: str, theme: Theme) -> Text:
    """Build alternating-color header title."""
    header = Text()
    words = title.split()
    for i, word in enumerate(words):
        st = theme.primary if i % 2 == 0 else theme.secondary
        header.append(word + " ", style=f"bold {st}")
    header.append(f"\n{subtitle}", style=theme.muted)
    return header


# ─── Japanese flavour text ───────────────────────────────────────────────────

WELCOME_PHRASES = [
    ("ようこそ、Pakuへ ♡", "Welcome to Paku"),
    ("おかえりなさい ♡", "Welcome back"),
    ("がんばって！", "You can do it!"),
]

MENU_ITEMS = [
    ("1",  "Doctor",          "システム診断"),
    ("2",  "System Info",     "システム情報"),
    ("3",  "Workspace",       "ワークスペース"),
    ("4",  "Clean",           "クリーン"),
    ("5",  "Save Context",    "コンテキスト保存"),
    ("6",  "Resume Context",  "コンテキスト復元"),
    ("7",  "Scan Hygiene",    "セキュリティ点検"),
    ("8",  "Themes",          "テーマ"),
    ("9",  "Settings",        "設定"),
    ("10", "Autoruns",        "自動起動"),
    ("11", "Debloat",         "不要アプリ削除"),
    ("12", "About",           "について"),
    ("0",  "Exit",            "終了"),
]


# ─── Helper builders ─────────────────────────────────────────────────────────

def build_title(theme: Theme) -> Text:
    """Big spaced-out PAKU title."""
    title = Text()
    title.append("P ", style=theme.primary)
    title.append("A ", style=theme.secondary)
    title.append("K ", style=theme.primary)
    title.append("U",  style=theme.secondary)
    return title


def build_mascot_panel(mascot_art: str, theme: Theme) -> Panel:
    """Wrap ASCII art in a styled panel, preserving every character."""
    art_text = Text(mascot_art, style=theme.primary, no_wrap=True, overflow="fold")
    return Panel(
        Align.center(art_text),
        border_style=theme.border,
        box=box.SIMPLE,
        padding=(0, 2),
    )


def build_menu(theme: Theme) -> Text:
    """Render the numbered menu with instructional hint."""
    menu = Text()
    for key, label, jp in MENU_ITEMS:
        menu.append(f"  {key:>2}  ", style=f"bold {theme.accent}")
        menu.append(f"{label:<18}", style=theme.text)
        menu.append(f"{jp}\n",      style=theme.muted)
    
    menu.append("\n  ", style=theme.dim)
    menu.append("Enter a number to choose · ", style=theme.muted)
    menu.append("0", style=f"bold {theme.accent}")
    menu.append(" to exit\n", style=theme.muted)
    menu.append("  番号を入力してください\n", style=theme.dim)
    return menu


# ─── Main screen ─────────────────────────────────────────────────────────────

def render_main_screen(theme: Theme, mascot_loader: MascotLoader,
                        animations_enabled: bool = True) -> None:
    """Draw the full Paku welcome screen."""
    console.clear()

    # ── Title Banner Panel ─────────────────────────────────────────────────
    console.print()
    title_content = Text()
    title_content.append("P A K U\n", style=f"bold {theme.primary}")
    title_content.append("Your tiny terminal companion.", style=theme.muted)

    console.print(Align.center(
        Panel(
            Align.center(title_content),
            border_style=theme.border,
            box=box.ROUNDED,
            width=76,
        )
    ))

    # ── Mascot ─────────────────────────────────────────────────────────────
    mascot_art = mascot_loader.load("idle")
    console.print(Align.center(
        Text(mascot_art, style=theme.primary, no_wrap=True, overflow="fold")
    ))

    # ── Welcome phrase ──────────────────────────────────────────────────────
    jp_phrase, en_phrase = WELCOME_PHRASES[0]
    console.print(Align.center(
        Text(f"{jp_phrase}", style=f"bold {theme.secondary}")
    ))
    console.print(Align.center(
        Text(f"{en_phrase}", style=theme.muted)
    ))
    console.print()

    # ── Menu Card ──────────────────────────────────────────────────────────
    console.print(Align.center(
        Panel(
            Align.center(build_menu(theme)),
            title=f"[bold {theme.primary}]Main Menu[/]",
            border_style=theme.border,
            box=box.ROUNDED,
            width=76,
        )
    ))
    console.print()


def render_coming_soon(feature: str, theme: Theme) -> None:
    """Placeholder screen for unimplemented features."""
    console.clear()
    console.print()
    content = Text()
    content.append(f"  [ {feature} ]\n\n", style=f"bold {theme.primary}")
    content.append("  Coming in the next phase.\n", style=theme.muted)
    content.append("  次のフェーズで実装します。", style=theme.dim)

    console.print(Align.center(framed_section(content, "Feature Status", theme)))
    console.print()
    console.print(Align.center(
        styled_line(("Press Enter to return.", theme.muted))
    ))
    input()


def render_about(theme: Theme) -> None:
    """About / credits screen."""
    from paku import __version__
    console.clear()
    console.print()
    about = Text()
    about.append("P A K U\n",             style=f"bold {theme.primary}")
    about.append(f"v{__version__}\n\n",   style=theme.secondary)
    about.append("Your tiny terminal companion.\n", style=theme.text)
    about.append("小さなターミナルの友達。\n\n",       style=theme.muted)
    about.append("Built with Python · Rich · Typer\n", style=theme.dim)

    console.print(Align.center(framed_section(Align.center(about), "About Paku", theme)))
    console.print()
    console.print(Align.center(
        styled_line(("Press Enter to return.", theme.muted))
    ))
    input()


def render_exit(theme: Theme) -> None:
    """Goodbye screen."""
    console.print()
    console.print(Align.center(
        Text("またね ♡  See you next time!", style=f"bold {theme.primary}")
    ))
    console.print()
