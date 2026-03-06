from __future__ import annotations

from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.legacy.download import main


if __name__ == "__main__":
    warnings.warn(
        "download.py esta deprecado. Usa `observer legacy-download`.",
        DeprecationWarning,
    )
    raise SystemExit(main())
