from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Any
import warnings

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from duo_observer.client import create_client, normalize_unique_id
from duo_observer.services.live_probe import probe_live_status


async def _is_live(unique_id: str) -> bool:
    client = create_client(normalize_unique_id(unique_id))
    return await probe_live_status(client)


def on_connect(unique_id: str) -> bool:
    warnings.warn(
        "scripts/legacy/wacher.py es compatibilidad legacy. Usa `observer live-check`.",
        DeprecationWarning,
    )

    try:
        return bool(asyncio.run(_is_live(unique_id)))
    except Exception:  # noqa: BLE001
        return False


def main(argv: list[str] | None = None) -> int:
    unique_id = "edgar_toledo_g"
    if argv:
        unique_id = argv[0]

    print(on_connect(unique_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
