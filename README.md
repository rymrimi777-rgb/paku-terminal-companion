# Paku 🌸
<img width="794" height="235" alt="image" src="https://github.com/user-attachments/assets/03169184-a24b-45c9-a679-efa095e3a26a" />

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-brightgreen)
![Version](https://img.shields.io/badge/version-2.0.0-blue)
[![License](https://img.shields.io/badge/license-GPLv3-blue)](LICENSE)

> Cross-Platform Developer Assistant, Security Toolkit & Project Manager.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
  - [Reliability & Diagnostics](#reliability--diagnostics)
  - [Security Toolkit](#security-toolkit)
  - [System Monitoring](#system-monitoring)
  - [Workspace & Git Management](#workspace--git-management)
  - [GitHub Project Integration](#github-project-integration)
  - [Safe Cleanup & Session Memory](#safe-cleanup--session-memory)
  - [Theme Customization](#theme-customization)
- [Quick Start](#quick-start)
  - [Standalone Binaries (No Python Needed)](#standalone-binaries-no-python-needed)
  - [Developer Installation (From Source)](#developer-installation-from-source)
- [CLI Reference](#cli-reference)
- [Cross-Platform Architecture](#cross-platform-architecture)
- [Building from Source](#building-from-source)
- [Automated Testing & CI](#automated-testing--ci)
- [License](#license)

---

## Overview

**Paku Terminal Companion 2.0** is an open-source, lightweight, cross-platform terminal assistant engineered for Windows and Linux. It pairs high-speed native system inspections with developer workflows: workspace git tracking, secret leakage prevention, dependency CVE checking, system resource monitoring, and optional GitHub CLI integration — all wrapped in an aesthetic, responsive terminal UI.

---

## Key Features

### Reliability & Diagnostics

- `paku self-test` — Runs an automated runtime verification suite testing CLI command registration, sandboxed configuration lifecycle, filesystem safety, Git interop, platform detection, theme integrity, and graceful error degradation. Outputs machine-readable results via `--json`.
- `paku doctor` — Read-only environment and dependency diagnostics (Python runtime, encoding, PATH registration, storage availability).
- `paku info` — System architecture, core counts, RAM capacity, and platform specifications overview.

### Security Toolkit

- `paku scan` — System hygiene and protection check (Windows Defender status, double-extension malware detection, startup entries, listening network ports).
- `paku scan --security` — Comprehensive workspace security audit:
  - **Secret Detection**: Scans source code for hardcoded AWS keys, GitHub PATs, Slack tokens, Stripe keys, private cryptographic keys, and high-entropy tokens. All detected values are automatically redacted.
  - **Git Exposure Checks**: Verifies that sensitive files (`.env`, `*.key`, `id_rsa`) are not tracked by Git index, validates `.gitignore` rules, and detects embedded plaintext credentials in remote URLs.
  - **Dependency Auditing**: Identifies manifests (`pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`) and integrates with `pip-audit` / `npm audit` when installed. Reports clearly when offline or when audit tools are uninstalled.
- `paku autoruns` — Enumerate auto-start locations (Windows Registry Run/RunOnce, Startup Folders, Scheduled Tasks, Automatic Services; Linux Desktop Autostart, systemd services, crontab `@reboot` jobs).
- `paku debloat` — Scan for consumer bloatware packages (read-only listing on Linux; user-confirmed removal on Windows).

### System Monitoring

- `paku system` — Interactive hardware resource dashboard displaying CPU utilization, multi-core breakdown, physical memory consumption, disk mounts, top memory-consuming processes, and diagnostic threshold warnings (>85% CPU/RAM).
- `paku system disk` — Storage partition table with used, free, total capacity, and visual utilization bars.
- `paku system processes` — Inspect top processes by memory (RSS) or CPU consumption without terminating processes.
- `paku system monitor` — Live periodic terminal monitor with customizable refresh interval (`--interval`) and safe exit via `Ctrl+C`.

### Workspace & Git Management

- `paku workspace` — In-depth local workspace inspection: project type markers, exact Git status (staged, unstaged, untracked counts), upstream tracking branch, recent commit history (last 5 commits), and repository health checks.

### GitHub Project Integration

- `paku github status` — Check GitHub CLI (`gh`) authentication state or `GITHUB_TOKEN` environment variable.
- `paku github repos` — List accessible repositories with stars, visibility, and URLs.
- `paku github issues` — List open issues for current or target repository.
- `paku github prs` — List open pull requests for current or target repository.

### Safe Cleanup & Session Memory

- `paku clean` — Recursively cleans safe-listed temporary junk (`__pycache__`, `.pytest_cache`, `*.pyc`).
  - Strict path traversal guards prevent escaping the target root directory.
  - Symlink protection: never traverses or deletes symlinked files outside scope.
  - `paku clean --dry-run` (`-n`) — Preview proposed deletions and calculate reclaimable space without modifying files.
- `paku save` / `paku resume` — Per-workspace context snapshot memory. Capture notes and Git state before closing, resume where you left off.

### Theme Customization

- `paku theme` — Switch palettes dynamically (`cyan`, `sakura`, `lavender`, `midnight`, `monochrome`).
- `paku settings` — Toggle animations and persist preferences to `%APPDATA%\Paku\config.json` (Windows) or `~/.paku/config.json` (Linux).

---

## Quick Start

### Standalone Binaries (No Python Needed)

Download the precompiled single-file executable from GitHub Releases:

- **Windows x64:** Download `paku-windows-x64.exe` and run:
  ```powershell
  .\paku-windows-x64.exe
  ```
- **Linux x64:** Download `paku-linux-x64`, make executable, and run:
  ```bash
  chmod +x paku-linux-x64
  ./paku-linux-x64
  ```

### Developer Installation (From Source)

Requires Python 3.11+.

```bash
# Clone the repository
git clone https://github.com/rymrimi777-rgb/paku-terminal-companion.git
cd paku-terminal-companion

# Install in editable mode
pip install -e .

# Run Paku
paku
# or via module:
python -m paku
```

---

## CLI Reference

| Command | Options | Description |
| :--- | :--- | :--- |
| `paku` | | Open interactive menu with mascot and options |
| `paku self-test` | `--json` | Run automated self-test verification suite |
| `paku doctor` | | Run system and runtime environment diagnostics |
| `paku info` | | Display OS, CPU, RAM, and terminal overview |
| `paku workspace [PATH]` | `--json` | Inspect workspace project type and Git status |
| `paku clean [PATH]` | `-y`, `--yes`<br>`-n`, `--dry-run` | Clean temporary files (or preview deletions) |
| `paku scan [PATH]` | `-s`, `--security`<br>`--json` | Hygiene scan or full workspace security audit |
| `paku system` | `--json` | Display CPU, RAM, disk, and process dashboard |
| `paku system disk` | `--json` | Display disk storage volumes and free space |
| `paku system processes`| `--limit <N>`<br>`--sort <mem\|cpu>` | Display top active processes |
| `paku system monitor` | `--interval <SEC>` | Live continuous resource monitor (Ctrl+C to exit) |
| `paku github status` | `--json` | Inspect GitHub CLI authentication and repository |
| `paku github repos` | `--limit <N>`<br>`--json` | List accessible GitHub repositories |
| `paku github issues` | `--repo <ORG/REPO>`<br>`--limit <N>` | List open repository issues |
| `paku github prs` | `--repo <ORG/REPO>`<br>`--limit <N>` | List open repository pull requests |
| `paku autoruns` | | Enumerate autostart registry, cron, and services |
| `paku debloat` | | Scan for bloatware apps (read-only on Linux) |
| `paku save` | | Capture snapshot of workspace notes and git state |
| `paku resume` | | Display previous workspace notes and session history |
| `paku theme` | | Switch color palette |
| `paku settings` | | Configure animations and application preferences |

---

## Cross-Platform Architecture

- **Path Handling**: Strict use of Python's standard `pathlib.Path` with `.resolve()` and `.is_relative_to()` to prevent directory traversal and handle forward/backward slashes.
- **Zero-Dependency Core**: System monitoring, secret detection, and git interactions utilize Python standard library modules (`ctypes`, `shutil`, `urllib.request`, `re`, `subprocess`, `os`). If `psutil` is installed, Paku automatically leverages it for accelerated monitoring.
- **Subprocess Safety**: Command arguments are passed as explicit lists without shell expansion (`shell=False`), preventing command injection.
- **Graceful Tool Degradation**: Optional tools (`gh`, `pip-audit`, `systemctl`, `crontab`, `winreg`) are detected at runtime and handled with clear informational messages when unavailable.

---

## Building from Source

To build standalone single-file executables:

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm paku.spec
```

The output binary is written to `dist/paku.exe` (Windows) or `dist/paku` (Linux).

---

## Automated Testing & CI

Run the unit and integration test suite:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions workflows (`build-check.yml` and `release.yml`) execute test suites on both Windows and Linux matrix runners and run smoke tests directly against the compiled executables (`--help`, `self-test`, `clean --dry-run`, `system disk`).

---

## License

This project is licensed under the GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.
