"""
Paku __main__.py
Allows: python -m paku
"""

import sys
import io

# Force UTF-8 on Windows so Japanese text and Unicode symbols render correctly.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from paku.cli import app

app()
