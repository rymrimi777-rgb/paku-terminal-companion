#!/usr/bin/env bash
set -e

echo "🌸 Paku Linux Installer"
echo "----------------------"

# 1. Check Python version (>= 3.11)
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    echo "Please install Python 3.11 or higher (e.g. via 'sudo apt install python3 python3-venv python3-pip')."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
    echo "❌ Error: Python 3.11+ is required. Found Python $PYTHON_VERSION."
    exit 1
fi

echo "✓ Found Python $PYTHON_VERSION"

# 2. Check for python3-venv module availability
if ! python3 -m venv --help &> /dev/null; then
    echo "❌ Error: python3-venv module is missing."
    echo "On Debian/Ubuntu systems, install it using:"
    echo "  sudo apt update && sudo apt install python3-venv python3-pip"
    exit 1
fi

# 3. Create virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "📦 Virtual environment $VENV_DIR already exists."
fi

# Activate virtual environment in subshell for installation
echo "⚡ Installing Paku in editable mode..."
"$VENV_DIR/bin/pip" install -e .

VENV_BIN="$(pwd)/$VENV_DIR/bin"

echo ""
echo "✨ Installation complete!"
echo ""
echo "To run Paku, activate your virtual environment:"
echo "  source .venv/bin/activate"
echo "  paku"
echo ""
echo "Or run directly:"
echo "  ./.venv/bin/paku"
echo ""

# 4. Check if scripts dir / venv bin path is in PATH
case ":$PATH:" in
  *":$VENV_BIN:"*)
    ;;
  *)
    if ! command -v paku &> /dev/null; then
        echo "⚠️  Note: 'paku' command is not currently in your system PATH."
        echo "If installing outside a venv (e.g. --user), add the scripts directory to your shell configuration:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "Add that line to your ~/.bashrc or ~/.zshrc and reload with 'source ~/.bashrc'."
    fi
    ;;
esac
