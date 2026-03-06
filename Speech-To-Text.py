from __future__ import annotations

from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.legacy.speech_to_text import main


if __name__ == "__main__":
    warnings.warn(
        "Speech-To-Text.py esta deprecado. Usa scripts/legacy/speech_to_text.py.",
        DeprecationWarning,
    )
    raise SystemExit(main())
