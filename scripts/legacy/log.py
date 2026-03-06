from __future__ import annotations

from pathlib import Path
import sys
import warnings
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from duo_observer.cli import main as observer_main


def main(argv: Sequence[str] | None = None) -> int:
    warnings.warn(
        "scripts/legacy/log.py es compatibilidad legacy. Usa `observer log`.",
        DeprecationWarning,
    )

    effective_argv = list(sys.argv[1:] if argv is None else argv)
    forwarded = ["log", *effective_argv]
    return observer_main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
