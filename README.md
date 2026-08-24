# Paku 🌸
<img width="794" height="235" alt="image" src="https://github.com/user-attachments/assets/03169184-a24b-45c9-a679-efa095e3a26a" />

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
[![License](https://img.shields.io/badge/license-GPLv3-blue)](LICENSE)

> Your tiny terminal companion.
## Table of Contents

- [Features](#features)
- [Phase 1 — Foundation](#phase-1--foundation)
- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Replacing the Mascot](#replacing-the-mascot)
- [Themes](#themes)
- [Building from Source](#building-from-source)
- [Roadmap](#roadmap)
- [Releases](#releases)
- [Author](#author)
- [License](#license)

## Features

### System & Workspace
<img width="1357" height="479" alt="image" src="https://github.com/user-attachments/assets/43d29241-7c66-4aa0-8426-e2db2d8e549d" />

- `paku doctor` — Run read-only environment and system diagnostics.
- `paku info` — Display system and environment overview.
- `paku workspace` — Analyze current workspace and Git repository status.

### Cleanup & Session

- `paku clean` — Scan and safely clean temporary build/cache files under CWD.
- `paku save` / `paku resume` — Capture a snapshot of the current workspace memory and notes, then view saved workspace session memory and previous notes.

### Security

- `paku scan` — Run lightweight system hygiene & protection checks.
- `paku autoruns` — Enumerate Windows & Linux auto-start locations (read-only).
- `paku debloat` — Scan for bloatware packages (read-only on Linux, removal on Windows).

### Customization

- `paku theme` — Browse and select a Paku colour theme.
- `paku settings` — Manage application preferences.

### Under the Hood

- **Zero-Blocking UI:** Smooth, concurrent animations that never choke your CPU.
- **Mixed OS Access:** Lightweight direct reads via `winreg` for Windows registry and desktop autostart / systemd / crontab on Linux, paired with targeted PowerShell calls on Windows or package manager checks on Linux.


## Phase 1 — Foundation

Paku is a CLI tool written in Python. It runs natively on both Windows and Linux across all commands (`scan`, `autoruns`, `debloat`, `doctor`, `info`, `workspace`, `clean`, `save`/`resume`).

It is packaged as standalone binaries (`paku-windows-x64.exe` and `paku-linux-x64`) via PyInstaller.

## Quick Start

### For Users

Download the latest standalone executable from the [Releases](#releases) page and run it directly (no Python installation needed):

- **Windows:** Download `paku-windows-x64.exe` and run it directly.
- **Linux:** Download `paku-linux-x64`, make it executable with `chmod +x paku-linux-x64`, and run it (`./paku-linux-x64`).

### For Developers

Install the package in editable mode:

```powershell
pip install -e .
```

> **Note:** If Windows/Linux throws a PATH warning and the `paku` command is not recognized, you can always run the app reliably using `python -m paku`.

Then run Paku:

```powershell
# Interactive interface
paku

# Or via Python module
python -m paku

# Version
paku --version

# Help
paku --help

# Theme selector
paku theme
```

## Requirements

- Python 3.11+ (if running from source)
- `typer>=0.12`
- `rich>=13`
- Windows 10/11 (64-bit) or Linux — supported natively across all commands.

> **Platform Compatibility Note:** All commands (`paku autoruns`, `paku scan`, `paku debloat`, `paku doctor`, `paku info`, `paku workspace`, `paku clean`, `paku save`/`resume`, `paku theme`, `paku settings`) run natively on both Linux and Windows via either prebuilt standalone binaries or from source.

## Project Structure

```text
paku/
├── src/paku/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py
│   ├── cli.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── data/
│   ├── features/
│   │   ├── __init__.py
│   │   ├── autoruns.py
│   │   ├── clean.py
│   │   ├── debloat.py
│   │   ├── doctor.py
│   │   ├── info.py
│   │   ├── resume.py
│   │   ├── scan.py
│   │   ├── settings.py
│   │   └── workspace.py
│   └── ui/
│       ├── __init__.py
│       ├── animations.py
│       ├── mascot.py
│       ├── terminal.py
│       └── themes.py
│   └── assets/
│       └── ascii/
│           ├── error.txt
│           ├── happy.txt
│           ├── idle.txt
│           ├── success.txt
│           ├── thinking.txt
│           └── working.txt
├── tests/
├── pyproject.toml
└── README.md
```

## Architecture

<img width="1132" height="1157" alt="Untitled-1" src="https://github.com/user-attachments/assets/3df90439-7679-4fb1-aca9-111d39da8815" />

## Replacing the Mascot

Drop your finished ASCII `.txt` files into `src/paku/assets/ascii/`. The system reads them verbatim, preserving spaces, indentation, and alignment exactly.

## Themes

Edit `src/paku/ui/themes.py` to add or modify themes. Config is saved to `%APPDATA%\Paku\config.json` on Windows or `~/.config/Paku/config.json` on Linux.

## Building from Source

To build a standalone executable on Windows or Linux using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm paku.spec
```

PyInstaller automatically adapts the binary output format for your operating system (`dist/paku.exe` on Windows or `dist/paku` on Linux). The spec file bundles `assets/` so mascot artwork remains included in the binary.

## Roadmap

- Cross-platform support: Full native Windows & Linux support achieved for diagnostic, autoruns, scan, and debloat enumeration features.
- Add richer package and startup-entry details while keeping destructive actions explicit.
- Improve automated test coverage for platform-specific behavior.

## Releases

Download packaged standalone executables (`paku-windows-x64.exe` and `paku-linux-x64`) from the project's [Releases](https://github.com/rymrimi777-rgb/paku-terminal-companion/releases) page.

## Author

Created by Rym.

## License

This project is licensed under the GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

## ⬇ Download

Get the latest version from the official Paku website:

👉 **[Download Paku](https://pakufixed.vercel.app/)**

For source code, release history, and development updates, see the
[GitHub repository](https://github.com/rymrimi777-rgb/paku-terminal-companion).

