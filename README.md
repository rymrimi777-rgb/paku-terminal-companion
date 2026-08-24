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
- `paku autoruns` — Enumerate Windows auto-start locations (read-only).
- `paku debloat` — Remove known Windows bloatware UWP apps.

### Customization

- `paku theme` — Browse and select a Paku colour theme.
- `paku settings` — Manage application preferences.

### Under the Hood

- **Zero-Blocking UI:** Smooth, concurrent animations that never choke your CPU.
- **Mixed OS Access:** Lightweight direct reads via `winreg` for the registry, paired with targeted PowerShell calls (`Get-MpComputerStatus`, `Get-AppxPackage`, `Get-CimInstance`) for checks that need deeper Windows APIs.


## Phase 1 — Foundation

Paku is a CLI tool written in Python. It runs natively on both Windows and Linux, with Windows-specific features (scan, autoruns, debloat) showing a clear platform message on non-Windows systems.

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
- Windows 10 or Windows 11 (64-bit) — required for the Windows-specific features (`scan`, `autoruns`, `debloat`); other commands also run on Linux/macOS from source.

> **Platform Compatibility Note:** Windows 10/11 (64-bit) is required **only** for Windows-specific features (`paku scan`, `paku autoruns`, `paku debloat`). All other commands (`paku doctor`, `paku info`, `paku workspace`, `paku clean`, `paku save`/`resume`, `paku theme`, `paku settings`) run identically on Linux and Windows via either prebuilt standalone binaries or from source.

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

- Expand cross-platform diagnostics beyond the current Windows-first feature set.
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

