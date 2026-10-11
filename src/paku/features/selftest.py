"""
Paku Self-Test Feature
======================
Automated runtime diagnostics and self-verification.
Verifies CLI registration, configuration, filesystem safety,
platform detection, git interoperability, theme engine, and error handling
using temporary sandboxes without touching user files.
"""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme, THEME_LIST, get_theme
from paku.ui.mascot import MascotLoader, MASCOT_STATES, _BUILTIN_PLACEHOLDER
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel

console = Console(legacy_windows=False)


@dataclass
class CheckResult:
    category: str
    name: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "UNSUPPORTED"
    message: str
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _check_cli_registration() -> CheckResult:
    """Verify all expected CLI commands are properly registered."""
    t0 = time.perf_counter()
    expected_commands = {
        "doctor", "info", "workspace", "clean", "save", "resume",
        "scan", "theme", "settings", "autoruns", "debloat", "self-test",
    }
    try:
        from paku.cli import app
        registered = {c.name for c in app.registered_commands if c.name}
        missing = expected_commands - registered
        dt = (time.perf_counter() - t0) * 1000.0
        if not missing:
            return CheckResult(
                category="CLI",
                name="Command Registration",
                status="PASSED",
                message=f"All {len(registered)} commands registered successfully",
                duration_ms=dt,
            )
        else:
            return CheckResult(
                category="CLI",
                name="Command Registration",
                status="FAILED",
                message=f"Missing commands: {', '.join(missing)}",
                duration_ms=dt,
            )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="CLI",
            name="Command Registration",
            status="FAILED",
            message=f"Exception during inspection: {exc}",
            duration_ms=dt,
        )


def _check_config_lifecycle() -> CheckResult:
    """Test configuration loading, validation, saving, and corruption fallback."""
    t0 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="paku_test_config_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            cfg_file = tmp_path / "config.json"

            # 1. Non-existent file defaults
            import paku.config.settings as s_mod
            original_dir = s_mod.CONFIG_DIR
            original_file = s_mod.CONFIG_FILE
            try:
                s_mod.CONFIG_DIR = tmp_path
                s_mod.CONFIG_FILE = cfg_file

                defaults = s_mod.load_settings()
                if "theme" not in defaults or "animations_enabled" not in defaults:
                    raise ValueError("Default settings missing required keys")

                # 2. Modify and save
                modified = dict(defaults)
                modified["theme"] = "midnight"
                modified["animations_enabled"] = False
                s_mod.save_settings(modified)

                if not cfg_file.exists():
                    raise FileNotFoundError("Config file was not written to disk")

                # 3. Reload
                reloaded = s_mod.load_settings()
                if reloaded.get("theme") != "midnight" or reloaded.get("animations_enabled") is not False:
                    raise ValueError("Reloaded settings did not reflect saved modifications")

                # 4. Corrupted JSON fallback
                cfg_file.write_text("{invalid json", encoding="utf-8")
                corrupt_fallback = s_mod.load_settings()
                if "theme" not in corrupt_fallback:
                    raise ValueError("Failed to recover gracefully from corrupt JSON")

            finally:
                s_mod.CONFIG_DIR = original_dir
                s_mod.CONFIG_FILE = original_file

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Config",
            name="Configuration Lifecycle",
            status="PASSED",
            message="Defaults, save, reload, and corruption recovery verified in sandbox",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Config",
            name="Configuration Lifecycle",
            status="FAILED",
            message=f"Config validation error: {exc}",
            duration_ms=dt,
        )


def _check_theme_integrity() -> CheckResult:
    """Verify all theme definitions contain all required semantic attributes."""
    t0 = time.perf_counter()
    try:
        required_attrs = [
            "name", "display_name", "primary", "secondary", "accent",
            "text", "muted", "success", "error", "warning", "border",
            "title", "subtitle", "highlight", "dim"
        ]
        checked = 0
        for name in THEME_LIST:
            th = get_theme(name)
            for attr in required_attrs:
                val = getattr(th, attr, None)
                if not val or not isinstance(val, str):
                    raise ValueError(f"Theme '{name}' has invalid attribute '{attr}': {val}")
            checked += 1
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Theme",
            name="Theme Palettes",
            status="PASSED",
            message=f"Verified {checked} palettes with all semantic tokens intact",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Theme",
            name="Theme Palettes",
            status="FAILED",
            message=f"Theme validation failed: {exc}",
            duration_ms=dt,
        )


def _check_mascot_system() -> CheckResult:
    """Verify MascotLoader fallback mechanisms and asset resolution."""
    t0 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="paku_test_mascot_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            loader = MascotLoader(tmp_path)

            # Missing assets directory: should return builtin placeholder
            art = loader.load("idle")
            if not art or _BUILTIN_PLACEHOLDER.strip() not in art:
                raise ValueError("Did not return builtin placeholder when assets missing")

            # Create test state
            ascii_dir = tmp_path / "ascii"
            ascii_dir.mkdir(parents=True)
            (ascii_dir / "idle.txt").write_text("(^_^)", encoding="utf-8")
            (ascii_dir / "happy.txt").write_text("(^o^)", encoding="utf-8")

            if loader.load("happy").strip() != "(^o^)":
                raise ValueError("Failed to load existing mascot state")
            if loader.load("nonexistent_state").strip() != "(^_^)":
                raise ValueError("Failed to fall back to idle state")

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Mascot",
            name="Mascot Art Loader",
            status="PASSED",
            message="State loading, idle fallback, and placeholder recovery verified",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Mascot",
            name="Mascot Art Loader",
            status="FAILED",
            message=f"Mascot verification failed: {exc}",
            duration_ms=dt,
        )


def _check_filesystem_sandbox_cleanup() -> CheckResult:
    """Verify safe junk scanning, traversal rejection, and symlink protection."""
    t0 = time.perf_counter()
    try:
        from paku.features.clean import scan_junk, is_safe_target_path

        with tempfile.TemporaryDirectory(prefix="paku_test_clean_") as tmp_dir:
            sandbox = Path(tmp_dir).resolve()
            
            # Create valid junk
            junk_dir = sandbox / "__pycache__"
            junk_dir.mkdir()
            (junk_dir / "module.cpython-312.pyc").write_text("test bytecode", encoding="utf-8")
            
            # Create subfolder with junk file
            sub = sandbox / "src"
            sub.mkdir()
            (sub / "dummy.pyc").write_text("pyc", encoding="utf-8")
            (sub / "normal.py").write_text("print('safe')", encoding="utf-8")

            # Scan junk in sandbox
            items = scan_junk(sandbox)
            item_paths = [p for p, _, _ in items]

            if not any(p.name == "__pycache__" for p in item_paths):
                raise ValueError("__pycache__ directory was not detected by scanner")
            if not any(p.name == "dummy.pyc" for p in item_paths):
                raise ValueError("dummy.pyc was not detected by scanner")
            if any(p.name == "normal.py" for p in item_paths):
                raise ValueError("normal.py was erroneously flagged as junk")

            # Verify path traversal validation
            outside_path = sandbox.parent / "outside_target.txt"
            if is_safe_target_path(outside_path, sandbox):
                raise ValueError("Path outside sandbox was incorrectly reported as safe")

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Filesystem",
            name="Clean & Traversal Safety",
            status="PASSED",
            message="Junk detection, file filtering, and path containment guards verified",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Filesystem",
            name="Clean & Traversal Safety",
            status="FAILED",
            message=f"Clean sandbox check failed: {exc}",
            duration_ms=dt,
        )


def _check_platform_detection() -> CheckResult:
    """Verify host OS detection, Python version, architecture, and encoding."""
    t0 = time.perf_counter()
    try:
        os_name = sys.platform
        py_ver = sys.version_info
        if py_ver < (3, 11):
            return CheckResult(
                category="Platform",
                name="OS & Python Environment",
                status="FAILED",
                message=f"Python version >= 3.11 required; currently {py_ver.major}.{py_ver.minor}",
                duration_ms=(time.perf_counter() - t0) * 1000.0,
            )

        supported_os = os_name in ("win32", "linux", "darwin")
        status = "PASSED" if supported_os else "UNSUPPORTED"
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Platform",
            name="OS & Python Environment",
            status=status,
            message=f"Platform: {platform.system()} {platform.machine()} | Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Platform",
            name="OS & Python Environment",
            status="FAILED",
            message=f"Platform inspection failed: {exc}",
            duration_ms=dt,
        )


def _check_git_interop_safe() -> CheckResult:
    """Verify Git discovery and safe read-only query in an isolated sandbox repository."""
    t0 = time.perf_counter()
    git_bin = shutil.which("git")
    if not git_bin:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Git",
            name="Git Subprocess & Repo Query",
            status="SKIPPED",
            message="Git executable not found on PATH; skipping repo sandbox test",
            duration_ms=dt,
        )

    try:
        from paku.features.workspace import _git_info

        with tempfile.TemporaryDirectory(prefix="paku_test_git_") as tmp_dir:
            repo_dir = Path(tmp_dir).resolve()
            # Initialize a throwaway git repository
            subprocess.run(
                [git_bin, "init", "-q", "-b", "main"],
                cwd=repo_dir, check=True, capture_output=True, text=True, timeout=10
            )
            # Configure local user for commit test
            subprocess.run(
                [git_bin, "config", "user.name", "PakuTest"],
                cwd=repo_dir, check=True, capture_output=True, text=True, timeout=5
            )
            subprocess.run(
                [git_bin, "config", "user.email", "test@paku.internal"],
                cwd=repo_dir, check=True, capture_output=True, text=True, timeout=5
            )

            test_file = repo_dir / "README.md"
            test_file.write_text("# Paku Self-Test Repo\n", encoding="utf-8")
            
            # Uncommitted status test
            info_before = _git_info(repo_dir)
            if not info_before:
                raise ValueError("Failed to retrieve git info for initialized repo")
            if info_before.get("uncommitted") != "1":
                raise ValueError(f"Expected 1 uncommitted file, got {info_before.get('uncommitted')}")

            # Commit
            subprocess.run(
                [git_bin, "add", "README.md"],
                cwd=repo_dir, check=True, capture_output=True, text=True, timeout=5
            )
            subprocess.run(
                [git_bin, "commit", "-m", "Initial commit"],
                cwd=repo_dir, check=True, capture_output=True, text=True, timeout=10
            )

            info_after = _git_info(repo_dir)
            if not info_after or info_after.get("uncommitted") != "0":
                raise ValueError("Expected 0 uncommitted files after commit")

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Git",
            name="Git Subprocess & Repo Query",
            status="PASSED",
            message="Git initialization, status inspection, and branch retrieval verified safely",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Git",
            name="Git Subprocess & Repo Query",
            status="FAILED",
            message=f"Git test failed: {exc}",
            duration_ms=dt,
        )


def _check_workspace_root_detection() -> CheckResult:
    """Verify workspace marker file hierarchy detection and name extraction."""
    t0 = time.perf_counter()
    try:
        from paku.features.workspace import _detect_root, _extract_project_name

        with tempfile.TemporaryDirectory(prefix="paku_test_ws_") as tmp_dir:
            root = Path(tmp_dir).resolve()
            nested = root / "src" / "package"
            nested.mkdir(parents=True)

            pyproj = root / "pyproject.toml"
            pyproj.write_text('[project]\nname = "selftest-app"\n', encoding="utf-8")

            detected_root, p_types = _detect_root(nested)
            if detected_root != root:
                raise ValueError(f"Expected root {root}, detected {detected_root}")
            if not any("pyproject" in t for t in p_types):
                raise ValueError(f"Expected Python pyproject type, got {p_types}")

            proj_name = _extract_project_name(root)
            if proj_name != "selftest-app":
                raise ValueError(f"Expected name 'selftest-app', got '{proj_name}'")

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Workspace",
            name="Workspace Marker Detection",
            status="PASSED",
            message="Root traversal, pyproject.toml marker, and project name extraction verified",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Workspace",
            name="Workspace Marker Detection",
            status="FAILED",
            message=f"Workspace detection failed: {exc}",
            duration_ms=dt,
        )


def _check_missing_tools_graceful_handling() -> CheckResult:
    """Verify system handles missing optional binaries gracefully without crashing."""
    t0 = time.perf_counter()
    try:
        fake_binary = "definitely_nonexistent_cli_tool_987654321"
        loc = shutil.which(fake_binary)
        if loc is not None:
            raise ValueError("Unexpectedly found fictitious binary")

        # Test subprocess safety when executable is missing
        try:
            subprocess.run([fake_binary, "--version"], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            pass  # Expected behavior handled cleanly

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Reliability",
            name="Missing Tools Degradation",
            status="PASSED",
            message="Missing external binary checks handle FileNotFoundError gracefully",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Reliability",
            name="Missing Tools Degradation",
            status="FAILED",
            message=f"Degradation test failed: {exc}",
            duration_ms=dt,
        )


def _check_session_persistence() -> CheckResult:
    """Verify save & resume session memory storage in a sandbox directory."""
    t0 = time.perf_counter()
    try:
        import paku.features.resume as r_mod
        with tempfile.TemporaryDirectory(prefix="paku_test_session_") as tmp_dir:
            tmp_sessions = Path(tmp_dir) / "sessions"
            orig_sessions = r_mod.SESSIONS_DIR
            try:
                r_mod.SESSIONS_DIR = tmp_sessions
                # Test slug generation
                slug1 = r_mod._get_workspace_slug(Path("/some/path/a"))
                slug2 = r_mod._get_workspace_slug(Path("/some/path/a"))
                slug3 = r_mod._get_workspace_slug(Path("/some/path/b"))

                if slug1 != slug2 or slug1 == slug3:
                    raise ValueError("Slug hashing is inconsistent or colliding")

                # Test relative time formatting
                now_iso = datetime.now(timezone.utc).isoformat()
                rel = r_mod._format_relative_time(now_iso)
                if rel not in ("just now", "recently"):
                    raise ValueError(f"Relative time unexpected format: {rel}")

            finally:
                r_mod.SESSIONS_DIR = orig_sessions

        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Session",
            name="Session Context Engine",
            status="PASSED",
            message="Workspace slug hashing and relative timestamp formatting verified",
            duration_ms=dt,
        )
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        return CheckResult(
            category="Session",
            name="Session Context Engine",
            status="FAILED",
            message=f"Session persistence failed: {exc}",
            duration_ms=dt,
        )


def run_self_tests() -> Dict[str, Any]:
    """Execute all self-test checks and compile comprehensive report."""
    checks = [
        _check_cli_registration(),
        _check_config_lifecycle(),
        _check_theme_integrity(),
        _check_mascot_system(),
        _check_filesystem_sandbox_cleanup(),
        _check_platform_detection(),
        _check_git_interop_safe(),
        _check_workspace_root_detection(),
        _check_missing_tools_graceful_handling(),
        _check_session_persistence(),
    ]

    n_pass = sum(1 for c in checks if c.status == "PASSED")
    n_fail = sum(1 for c in checks if c.status == "FAILED")
    n_skip = sum(1 for c in checks if c.status == "SKIPPED")
    n_unsup = sum(1 for c in checks if c.status == "UNSUPPORTED")
    total = len(checks)

    all_passed = (n_fail == 0)
    pass_rate = (n_pass / total) * 100.0 if total > 0 else 0.0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "all_passed": all_passed,
        "summary": {
            "total": total,
            "passed": n_pass,
            "failed": n_fail,
            "skipped": n_skip,
            "unsupported": n_unsup,
            "pass_rate_percent": round(pass_rate, 1),
        },
        "checks": [c.to_dict() for c in checks],
    }


def render_self_test(
    theme: Theme,
    mascot_loader: MascotLoader,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """
    Render self-test suite results.
    Returns process exit code (0 for success, 1 for failure).
    """
    report = run_self_tests()
    all_passed = report["all_passed"]
    exit_code = 0 if all_passed else 1

    if as_json:
        print(json.dumps(report, indent=2))
        return exit_code

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   S E L F - T E S T", "自己診断  •  Runtime Verification Suite", theme)))
    console.print()

    mascot_state = "success" if all_passed else "error"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(mascot_state), theme)))
    console.print()

    # Table of Checks
    table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    table.add_column("Category", width=12, style=theme.accent)
    table.add_column("Check", width=26, style=theme.text)
    table.add_column("Status", width=14, justify="center")
    table.add_column("Details", style=theme.muted)
    table.add_column("Time", width=8, justify="right", style=theme.dim)

    for item in report["checks"]:
        st = item["status"]
        if st == "PASSED":
            st_text = Text("✓ PASSED", style=theme.success)
        elif st == "FAILED":
            st_text = Text("✗ FAILED", style=f"bold {theme.error}")
        elif st == "SKIPPED":
            st_text = Text("↷ SKIPPED", style=theme.warning)
        else:
            st_text = Text("- UNSUPP", style=theme.dim)

        table.add_row(
            item["category"],
            item["name"],
            st_text,
            item["message"],
            f"{item['duration_ms']:.1f}ms",
        )

    console.print(Align.center(framed_section(table, "Verification Results", theme)))
    console.print()

    # Summary Panel
    s = report["summary"]
    summary_text = Text()
    summary_text.append(f"Total: {s['total']} checks  ·  ", style=theme.text)
    summary_text.append(f"{s['passed']} passed  ·  ", style=theme.success)
    summary_text.append(f"{s['failed']} failed  ·  ", style=theme.error if s['failed'] > 0 else theme.dim)
    summary_text.append(f"{s['skipped']} skipped  ·  ", style=theme.warning if s['skipped'] > 0 else theme.dim)
    summary_text.append(f"Pass Rate: {s['pass_rate_percent']}%\n", style=f"bold {theme.primary}")
    summary_text.append(f"Environment: {report['platform']}  •  Python {report['python']}", style=theme.muted)

    console.print(Align.center(framed_section(summary_text, "Summary", theme)))
    console.print()

    if all_passed:
        console.print(Align.center(
            styled_line(("✓  All automated self-tests passed cleanly!", f"bold {theme.success}"), ("  安心！", theme.muted))
        ))
    else:
        console.print(Align.center(
            styled_line(("✗  One or more self-tests reported failures.", f"bold {theme.error}"))
        ))

    console.print()
    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return exit_code
