# Paku 🌸

> Your tiny terminal companion.

---

## Phase 1 — Foundation

Paku is a Windows-first CLI tool written in Python.
It is designed to be packaged as a standalone `.exe` via PyInstaller.

---

## Quick Start

### 1. Install dependencies

```powershell
pip install -e .
```

### 2. Run Paku

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

---

## Project Structure

```
paku/
├── src/paku/
│   ├── __init__.py          # Version
│   ├── __main__.py          # python -m paku
│   ├── main.py
│   ├── cli.py               # Typer commands + interactive loop
│   ├── ui/
│   │   ├── terminal.py      # Screen renderers
│   │   ├── themes.py        #  Theme system  ← edit themes here
│   │   ├── mascot.py        #  Mascot loader ← add states here
│   │   └── animations.py    # Spinner / progress bar
│   ├── config/
│   │   └── settings.py      # %APPDATA%/Paku/config.json
│   └── data/
│
├── assets/
│   └── ascii/               # Drop your ASCII artwork here
│       ├── idle.txt
│       ├── happy.txt
│       ├── thinking.txt
│       ├── working.txt
│       ├── success.txt
│       └── error.txt
│
├── tests/
├── pyproject.toml
└── README.md
```

---

## Replacing the Mascot

Drop your finished ASCII `.txt` files into `assets/ascii/`.
The system reads them verbatim — spaces, indentation, and alignment are
preserved exactly. No reformatting, no trimming.

---

## Themes

Edit `src/paku/ui/themes.py` to add or modify themes.
Config is saved to `%APPDATA%\Paku\config.json`.

---

## Building the .exe (later)

```powershell
pip install pyinstaller
pyinstaller --onefile --name paku src/paku/__main__.py
```
