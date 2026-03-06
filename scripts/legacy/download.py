from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import shutil
import sys
import warnings
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from duo_observer.client import TikTokLiveApiError, create_client, load_event_types, normalize_unique_id
from duo_observer.config import ObserverConfig
from duo_observer.services.live_probe import probe_live_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legacy TikTok live download")
    parser.add_argument("--user", help="Unique ID de TikTok. Si no se indica, usa TIKTOK_USER")
    parser.add_argument("--path", help="Ruta de salida .avi")
    parser.add_argument("--duration", type=int, default=60, help="Segundos. Usa 0 para indefinido")
    parser.add_argument("--quality", default=None, help="Calidad legacy")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    warnings.warn(
        "scripts/legacy/download.py es legacy y depende de APIs no garantizadas. "
        "Usa `observer watch` o `observer log` para flujo soportado oficialmente.",
        DeprecationWarning,
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = ObserverConfig.from_env()
        user = normalize_unique_id(args.user or config.tiktok_user or "")
        output_path = resolve_output_path(user, args.path, config)

        ensure_ffmpeg_available()

        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s")
        logger = logging.getLogger("legacy.download")

        client = create_client(user)
        download_method = getattr(client, "download", None)
        if not callable(download_method):
            raise TikTokLiveApiError(
                "TikTokLiveClient.download no existe en la version instalada. "
                "Este flujo legacy no esta soportado."
            )

        event_types = load_event_types()

        @client.on(event_types["ConnectEvent"])
        async def _on_connect(_: object) -> None:
            duration = None if args.duration == 0 else args.duration
            output_path.parent.mkdir(parents=True, exist_ok=True)
            download_method(path=str(output_path), duration=duration, quality=args.quality)
            logger.info("Descarga legacy iniciada en %s", output_path)

        is_live = asyncio.run(probe_live_status(client))
        if not is_live:
            logger.warning("%s no esta en vivo", user)
            return 3

        try:
            client.run()
        except KeyboardInterrupt:
            logger.info("Interrupcion por usuario")

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"legacy-download error: {exc}", file=sys.stderr)
        return 1


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg no esta instalado o no esta en PATH")


def resolve_output_path(unique_id: str, raw_path: str | None, config: ObserverConfig) -> Path:
    if raw_path:
        return Path(raw_path).expanduser().resolve()

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (config.output_dir / "legacy" / f"{unique_id}_{timestamp}.avi").expanduser().resolve()


if __name__ == "__main__":
    raise SystemExit(main())
