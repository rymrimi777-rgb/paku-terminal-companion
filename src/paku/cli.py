"""
Paku CLI — Command Definitions
================================
Defines all Typer commands, sub-apps, and interactive main loop.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.panel import Panel
from rich.rule import Rule
from rich import box

from paku import __version__
from paku.config.settings import (
    load_settings,
    save_settings,
    get_theme_name,
    set_theme,
    animations_enabled,
)
from paku.ui.themes import get_theme, THEMES, THEME_LIST
from paku.ui.mascot import MascotLoader
from paku.ui import terminal as ui
from paku.features import doctor, info, workspace, clean, resume, scan
from paku.features import settings as settings_feature
from paku.features import autoruns, debloat
from paku.features import selftest, system as system_feature, github as github_feature

# ─── Typer app ────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="paku",
    help="Paku - your tiny terminal companion.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
)

system_app = typer.Typer(
    name="system",
    help="Inspect and monitor system resources.  システム監視",
    add_completion=False,
    invoke_without_command=True,
)
app.add_typer(system_app)

github_app = typer.Typer(
    name="github",
    help="Manage and inspect GitHub projects.  GitHub連携",
    add_completion=False,
    invoke_without_command=True,
)
app.add_typer(github_app)

console = Console(legacy_windows=False)


# ─── Asset resolution ─────────────────────────────────────────────────────────

def _assets_dir() -> Path:
    """Resolve the assets directory for source, installed, and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "assets"


# ─── Core Subcommands ─────────────────────────────────────────────────────────

@app.command("doctor")
def doctor_command() -> None:
    """Run read-only environment and system diagnostics.  システム診断"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    doctor.render_doctor(th, mascot, _assets_dir(), wait_for_enter=False, animations_enabled=anim)


@app.command("info")
def info_command() -> None:
    """Display system and environment overview.  システム情報"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    info.render_info(th, mascot, wait_for_enter=False, animations_enabled=anim)


@app.command("workspace")
def workspace_command(
    path: Optional[Path] = typer.Argument(None, help="Target workspace path to inspect."),
    as_json: bool = typer.Option(False, "--json", help="Output results in JSON format."),
) -> None:
    """Analyze current workspace and Git repository status.  ワークスペース情報"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    workspace.render_workspace(
        th,
        mascot,
        target_dir=path,
        as_json=as_json,
        wait_for_enter=False,
        animations_enabled=anim,
    )


@app.command("clean")
def clean_command(
    path: Optional[Path] = typer.Argument(None, help="Target directory to clean (defaults to CWD)."),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation prompt and delete temporary files immediately.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Preview proposed changes and space savings without deleting anything.",
    ),
) -> None:
    """Scan and safely clean temporary build/cache files under CWD.  クリーン"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    clean.render_clean(
        th,
        mascot,
        target_dir=path,
        yes=yes,
        dry_run=dry_run,
        wait_for_enter=False,
        animations_enabled=anim,
    )


@app.command("save")
def save_command() -> None:
    """Capture a snapshot of the current workspace memory and notes.  コンテキスト保存"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    resume.render_save(th, mascot, wait_for_enter=False, animations_enabled=anim)


@app.command("resume")
def resume_command() -> None:
    """View saved workspace session memory and previous notes.  コンテキスト復元"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    resume.render_resume(th, mascot, wait_for_enter=False, animations_enabled=anim)


@app.command("scan")
def scan_command(
    path: Optional[Path] = typer.Argument(None, help="Target directory to scan (defaults to CWD)."),
    security: bool = typer.Option(
        False, "--security", "-s",
        help="Run comprehensive workspace security audit (secrets, git exposure, dependencies).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Output scan results in JSON format.",
    ),
) -> None:
    """Run lightweight system hygiene & security checks.  セキュリティ点検"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    code = scan.render_scan(
        th,
        mascot,
        security=security,
        target_dir=path,
        as_json=as_json,
        wait_for_enter=False,
        animations_enabled=anim,
    )
    if code != 0:
        raise typer.Exit(code=code)


@app.command("self-test")
@app.command("selftest", hidden=True)
def selftest_command(
    as_json: bool = typer.Option(
        False, "--json",
        help="Output self-test results in JSON format.",
    ),
) -> None:
    """Run automated self-tests and runtime verification.  自己診断"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    exit_code = selftest.render_self_test(th, mascot, as_json=as_json, wait_for_enter=False)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def _select_theme_interactive(settings: dict) -> str | None:
    """Core theme selection logic. Returns selected theme name or None if cancelled."""
    current = get_theme_name(settings)
    th = get_theme(current)

    console.clear()
    console.print()
    console.print(Align.center(ui.build_header("P A K U   T H E M E S", "テーマ選択", th)))
    console.print()

    theme_text = Text()
    for i, name in enumerate(THEME_LIST, 1):
        t = get_theme(name)
        theme_text.append(f"  [{i:>2}]  ", style=f"bold {th.accent}")
        theme_text.append(f"{t.display_name:<16}", style=t.primary)
        if name == current:
            theme_text.append("← active\n", style=th.muted)
        else:
            theme_text.append("\n", style=th.dim)

    console.print(Align.center(ui.framed_section(theme_text, "Select Palette", th)))
    console.print()
    console.print(Align.center(
        ui.styled_line(("Enter a number to switch, or press Enter to cancel.", th.muted))
    ))
    console.print()

    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice:
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(THEME_LIST):
            return THEME_LIST[idx]
    except ValueError:
        pass

    return None


@app.command("theme")
def theme_command() -> None:
    """Browse and select a Paku colour theme.  テーマを選択"""
    settings = load_settings()
    current = get_theme_name(settings)
    th = get_theme(current)

    new_theme = _select_theme_interactive(settings)

    if new_theme:
        settings = set_theme(settings, new_theme)
        nt = get_theme(new_theme)
        console.print()
        console.print(Align.center(
            ui.styled_line((f"✓  Theme set to {nt.display_name}!", f"bold {nt.primary}"), ("  完了！", nt.muted))
        ))
        console.print()
    else:
        console.print(Align.center(
            Text("Cancelled.", style=th.muted)
        ))


@app.command("settings")
def settings_command() -> None:
    """Manage application preferences.  設定"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)

    settings_feature.render_settings(
        th,
        mascot,
        theme_callback=theme_command,
        wait_for_enter=False,
        animations_enabled=anim,
    )


@app.command("autoruns")
def autoruns_command() -> None:
    """Enumerate auto-start locations (read-only).  自動起動"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    autoruns.render_autoruns(th, mascot, wait_for_enter=False, animations_enabled=anim)


@app.command("debloat")
def debloat_command() -> None:
    """Scan and remove bloatware apps (read-only on Linux).  不要アプリ削除"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    anim = animations_enabled(settings)
    debloat.render_debloat(th, mascot, wait_for_enter=False, animations_enabled=anim)


# ─── System Sub-app ───────────────────────────────────────────────────────────

@system_app.callback(invoke_without_command=True)
def system_main(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Output system metrics in JSON format."),
) -> None:
    """System resource inspection and monitoring.  システム監視"""
    if ctx.invoked_subcommand is None:
        settings = load_settings()
        th = get_theme(get_theme_name(settings))
        mascot = MascotLoader(_assets_dir())
        system_feature.render_system_overview(th, mascot, as_json=as_json, wait_for_enter=False)


@system_app.command("disk")
def system_disk(
    as_json: bool = typer.Option(False, "--json", help="Output disk metrics in JSON format."),
) -> None:
    """Inspect disk capacity and volume utilization.  ディスク使用状況"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    system_feature.render_system_disk(th, mascot, as_json=as_json, wait_for_enter=False)


@system_app.command("processes")
def system_processes(
    limit: int = typer.Option(15, "--limit", "-l", help="Number of processes to display."),
    sort: str = typer.Option("memory", "--sort", help="Sort processes by 'memory' or 'cpu'."),
    as_json: bool = typer.Option(False, "--json", help="Output processes in JSON format."),
) -> None:
    """List active processes and resource consumers.  プロセス一覧"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    system_feature.render_system_processes(
        th,
        mascot,
        limit=limit,
        sort_by=sort,
        as_json=as_json,
        wait_for_enter=False,
    )


@system_app.command("monitor")
def system_monitor(
    interval: float = typer.Option(2.0, "--interval", "-i", help="Refresh interval in seconds."),
) -> None:
    """Live interactive periodic system resource monitor.  リアルタイム監視"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    system_feature.render_system_monitor(th, mascot, interval=interval)


# ─── GitHub Sub-app ───────────────────────────────────────────────────────────

@github_app.callback(invoke_without_command=True)
def github_main(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Output GitHub status in JSON format."),
) -> None:
    """Manage and inspect GitHub projects.  GitHub連携"""
    if ctx.invoked_subcommand is None:
        settings = load_settings()
        th = get_theme(get_theme_name(settings))
        mascot = MascotLoader(_assets_dir())
        github_feature.render_github_status(th, mascot, as_json=as_json, wait_for_enter=False)


@github_app.command("status")
def github_status(
    as_json: bool = typer.Option(False, "--json", help="Output GitHub status in JSON format."),
) -> None:
    """Inspect GitHub authentication and repository link.  認証状態"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    github_feature.render_github_status(th, mascot, as_json=as_json, wait_for_enter=False)


@github_app.command("repos")
def github_repos(
    limit: int = typer.Option(15, "--limit", "-l", help="Maximum repositories to list."),
    as_json: bool = typer.Option(False, "--json", help="Output repositories in JSON format."),
) -> None:
    """List repositories accessible to the user.  リポジトリ一覧"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    code = github_feature.render_github_repos(th, mascot, limit=limit, as_json=as_json, wait_for_enter=False)
    if code != 0:
        raise typer.Exit(code=code)


@github_app.command("issues")
def github_issues(
    limit: int = typer.Option(15, "--limit", "-l", help="Maximum issues to list."),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target GitHub repo (owner/repo)."),
    as_json: bool = typer.Option(False, "--json", help="Output issues in JSON format."),
) -> None:
    """List open issues for current or specified repository.  課題一覧"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    code = github_feature.render_github_issues(th, mascot, limit=limit, repo=repo, as_json=as_json, wait_for_enter=False)
    if code != 0:
        raise typer.Exit(code=code)


@github_app.command("prs")
def github_prs(
    limit: int = typer.Option(15, "--limit", "-l", help="Maximum pull requests to list."),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target GitHub repo (owner/repo)."),
    as_json: bool = typer.Option(False, "--json", help="Output PRs in JSON format."),
) -> None:
    """List open pull requests for current or specified repository.  プルリクエスト"""
    settings = load_settings()
    th = get_theme(get_theme_name(settings))
    mascot = MascotLoader(_assets_dir())
    code = github_feature.render_github_prs(th, mascot, limit=limit, repo=repo, as_json=as_json, wait_for_enter=False)
    if code != 0:
        raise typer.Exit(code=code)


# ─── Main interactive loop ────────────────────────────────────────────────────

def _run_main_loop(settings: dict, mascot: MascotLoader) -> None:
    """Interactive menu loop."""
    assets = _assets_dir()

    while True:
        th = get_theme(get_theme_name(settings))
        anim = animations_enabled(settings)

        ui.render_main_screen(th, mascot, animations_enabled=anim)

        try:
            choice = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            resume.auto_save_on_exit()
            ui.render_exit(th)
            sys.exit(0)

        if choice == "1":
            doctor.render_doctor(th, mascot, assets, wait_for_enter=True, animations_enabled=anim)
        elif choice == "2":
            info.render_info(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "3":
            workspace.render_workspace(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "4":
            clean.render_clean(th, mascot, yes=False, wait_for_enter=True, animations_enabled=anim)
        elif choice == "5":
            resume.render_save(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "6":
            resume.render_resume(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "7":
            scan.render_scan(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "8":
            theme_command()
            settings = load_settings()
        elif choice == "9":
            settings_feature.render_settings(
                th, mascot, theme_callback=theme_command,
                wait_for_enter=True, animations_enabled=anim,
            )
            settings = load_settings()
        elif choice == "10":
            autoruns.render_autoruns(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "11":
            debloat.render_debloat(th, mascot, wait_for_enter=True, animations_enabled=anim)
        elif choice == "12":
            selftest.render_self_test(th, mascot, as_json=False, wait_for_enter=True)
        elif choice == "13":
            system_feature.render_system_overview(th, mascot, as_json=False, wait_for_enter=True)
        elif choice == "14":
            github_feature.render_github_status(th, mascot, as_json=False, wait_for_enter=True)
        elif choice == "15":
            ui.render_about(th)
        elif choice == "0":
            resume.auto_save_on_exit()
            ui.render_exit(th)
            sys.exit(0)
        else:
            pass


# ─── Root command (paku with no sub-command) ──────────────────────────────────

@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    """
    Paku — your tiny terminal companion.

    Run without arguments to open the interactive interface.
    """
    if ctx.invoked_subcommand is None:
        settings = load_settings()
        assets   = _assets_dir()
        mascot   = MascotLoader(assets)
        _run_main_loop(settings, mascot)
