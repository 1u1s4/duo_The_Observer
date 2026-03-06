from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for path in (SRC, ROOT):
    raw = str(path)
    if raw not in sys.path:
        sys.path.insert(0, raw)
