from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import inspect
import json
import logging
from pathlib import Path
import sys
from typing import Sequence

from duo_observer.client import (
    TikTokLiveApiError,
    TikTokLiveDependencyError,
    create_client,
    load_event_types,
    resolve_unique_id,
)
from duo_observer.config import ObserverConfig
from duo_observer.handlers import JsonlEventWriter, TextEventWriter, register_event_handlers
from duo_observer.services.live_probe import build_probe_result, probe_live_status
from duo_observer.services.media import ensure_ffmpeg_binary, extract_audio_to_mp3

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_BAD_INPUT = 2
EXIT_NOT_LIVE = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observer", description="CLI para observar TikTok Live")
    parser.add_argument(
        "--version",
        action="version",
        version="duo-the-observer 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    watch_parser = subparsers.add_parser("watch", help="Conecta al live y muestra actividad")
    watch_parser.add_argument("--user", help="Unique ID de TikTok")

    log_parser = subparsers.add_parser("log", help="Conecta al live y persiste eventos")
    log_parser.add_argument("--user", help="Unique ID de TikTok")
    log_parser.add_argument("--output", help="Ruta de salida para logs")
    log_parser.add_argument(
        "--format",
        choices=("jsonl", "text"),
        default="jsonl",
        help="Formato de salida estructurada",
    )

    live_parser = subparsers.add_parser("live-check", help="Consulta si una cuenta esta en vivo")
    live_parser.add_argument("--user", help="Unique ID de TikTok")

    legacy_parser = subparsers.add_parser(
        "legacy-download",
        help="Descarga legacy no recomendada (depende de APIs no garantizadas)",
    )
    legacy_parser.add_argument("--user", help="Unique ID de TikTok")
    legacy_parser.add_argument("--path", help="Ruta de archivo de salida .avi")
    legacy_parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duracion en segundos. Usa 0 para indefinido",
    )
    legacy_parser.add_argument(
        "--quality",
        default=None,
        help="Calidad de descarga legacy segun soporte de TikTokLive",
    )

    audio_parser = subparsers.add_parser(
        "capture-audio",
        help="Captura audio MP3 del live usando flujo legacy",
    )
    audio_parser.add_argument("--user", help="Unique ID de TikTok")
    audio_parser.add_argument("--audio-path", help="Ruta de salida .mp3")
    audio_parser.add_argument("--video-path", help="Ruta temporal de captura .avi")
    audio_parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duracion en segundos. Usa 0 para indefinido",
    )
    audio_parser.add_argument(
        "--quality",
        default=None,
        help="Calidad de captura legacy segun soporte de TikTokLive",
    )
    audio_parser.add_argument(
        "--keep-video",
        action="store_true",
        help="Conserva el archivo temporal .avi despues de extraer audio",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = ObserverConfig.from_env()
    except ValueError as exc:
        print(f"Error de configuracion: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    setup_logging(config.log_level)
    logger = logging.getLogger("observer")

    try:
        if args.command == "watch":
            return run_watch(args, config, logger)
        if args.command == "log":
            return run_log(args, config, logger)
        if args.command == "live-check":
            return run_live_check(args, config, logger)
        if args.command == "legacy-download":
            return run_legacy_download(args, config, logger)
        if args.command == "capture-audio":
            return run_capture_audio(args, config, logger)
    except (TikTokLiveDependencyError, TikTokLiveApiError, ValueError, RuntimeError) as exc:
        logger.error("%s", exc)
        return EXIT_BAD_INPUT
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo no controlado: %s", exc)
        return EXIT_RUNTIME_ERROR

    logger.error("Comando no soportado: %s", args.command)
    return EXIT_BAD_INPUT


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def run_watch(args: argparse.Namespace, config: ObserverConfig, logger: logging.Logger) -> int:
    unique_id = resolve_unique_id(args.user, config.tiktok_user)
    client = create_client(unique_id)
    register_event_handlers(client, logger)

    if not _check_live(client, unique_id, logger):
        return EXIT_NOT_LIVE

    return _run_blocking_client(client, logger)


def run_log(args: argparse.Namespace, config: ObserverConfig, logger: logging.Logger) -> int:
    unique_id = resolve_unique_id(args.user, config.tiktok_user)
    client = create_client(unique_id)

    output_path = _resolve_log_output(unique_id, args.output, args.format, config)
    writer = JsonlEventWriter(output_path) if args.format == "jsonl" else TextEventWriter(output_path)
    logger.info("Guardando eventos en %s", output_path)

    try:
        register_event_handlers(client, logger, writer)

        if not _check_live(client, unique_id, logger):
            return EXIT_NOT_LIVE

        return _run_blocking_client(client, logger)
    finally:
        writer.close()


def run_live_check(args: argparse.Namespace, config: ObserverConfig, logger: logging.Logger) -> int:
    unique_id = resolve_unique_id(args.user, config.tiktok_user)
    client = create_client(unique_id)
    result = asyncio.run(build_probe_result(client, unique_id))

    payload = {
        "unique_id": unique_id,
        "is_live": result.is_live,
        "checked_at": result.checked_at.isoformat(),
        "error": result.error,
    }
    print(json.dumps(payload, ensure_ascii=True))

    if result.error:
        logger.error("No se pudo verificar live status: %s", result.error)
        return EXIT_RUNTIME_ERROR

    return EXIT_OK if result.is_live else EXIT_NOT_LIVE


def run_legacy_download(args: argparse.Namespace, config: ObserverConfig, logger: logging.Logger) -> int:
    unique_id = resolve_unique_id(args.user, config.tiktok_user)
    _ensure_ffmpeg_binary()

    client = create_client(unique_id)
    events = load_event_types()
    connect_event = events["ConnectEvent"]

    output_path = _resolve_legacy_output(unique_id, args.path, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.warning("Ejecutando flujo legacy-download (no recomendado para produccion)")
    _register_legacy_download_handler(
        client,
        connect_event,
        output_path,
        args.duration,
        args.quality,
        logger,
    )

    if not _check_live(client, unique_id, logger):
        return EXIT_NOT_LIVE

    return _run_blocking_client(client, logger)


def run_capture_audio(args: argparse.Namespace, config: ObserverConfig, logger: logging.Logger) -> int:
    unique_id = resolve_unique_id(args.user, config.tiktok_user)
    _ensure_ffmpeg_binary()

    client = create_client(unique_id)
    events = load_event_types()
    connect_event = events["ConnectEvent"]

    audio_path = _resolve_audio_output(unique_id, args.audio_path, config)
    video_path = _resolve_capture_video_output(
        unique_id,
        args.video_path,
        config,
        preferred_audio_path=audio_path,
    )
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.parent.mkdir(parents=True, exist_ok=True)

    logger.warning("Ejecutando capture-audio con flujo legacy de descarga")
    _register_legacy_download_handler(
        client,
        connect_event,
        video_path,
        args.duration,
        args.quality,
        logger,
        disconnect_when_done=args.duration != 0,
    )

    if not _check_live(client, unique_id, logger):
        return EXIT_NOT_LIVE

    exit_code = _run_blocking_client(client, logger)
    if exit_code != EXIT_OK:
        return exit_code

    if not video_path.exists():
        raise RuntimeError(
            f"No se genero captura temporal en {video_path}. "
            "Verifica soporte de TikTokLive.download en tu version instalada."
        )

    logger.info("Extrayendo audio desde %s hacia %s", video_path, audio_path)
    extract_audio_to_mp3(video_path, audio_path)
    logger.info("Audio guardado en %s", audio_path)

    if not args.keep_video:
        video_path.unlink(missing_ok=True)

    return EXIT_OK


def _check_live(client: object, unique_id: str, logger: logging.Logger) -> bool:
    try:
        is_live = asyncio.run(probe_live_status(client))
    except Exception as exc:  # noqa: BLE001
        logger.error("Error verificando estado live de %s: %s", unique_id, exc)
        raise

    if not is_live:
        logger.warning("%s no esta en vivo", unique_id)
        return False

    logger.info("%s esta en vivo. Iniciando conexion...", unique_id)
    return True


def _run_blocking_client(client: object, logger: logging.Logger) -> int:
    try:
        client.run()
    except KeyboardInterrupt:
        logger.info("Interrupcion por usuario")
        return EXIT_OK

    return EXIT_OK


def _resolve_log_output(
    unique_id: str,
    cli_output: str | None,
    fmt: str,
    config: ObserverConfig,
) -> Path:
    if cli_output:
        return Path(cli_output).expanduser().resolve()

    extension = "jsonl" if fmt == "jsonl" else "log"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (config.output_dir / "logs" / f"{unique_id}_{timestamp}.{extension}").expanduser().resolve()


def _resolve_legacy_output(
    unique_id: str,
    cli_path: str | None,
    config: ObserverConfig,
) -> Path:
    if cli_path:
        return Path(cli_path).expanduser().resolve()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (config.output_dir / "legacy" / f"{unique_id}_{timestamp}.avi").expanduser().resolve()


def _resolve_audio_output(
    unique_id: str,
    cli_path: str | None,
    config: ObserverConfig,
) -> Path:
    if cli_path:
        return Path(cli_path).expanduser().resolve()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (config.output_dir / "audio" / f"{unique_id}_{timestamp}.mp3").expanduser().resolve()


def _resolve_capture_video_output(
    unique_id: str,
    cli_path: str | None,
    config: ObserverConfig,
    *,
    preferred_audio_path: Path | None = None,
) -> Path:
    if cli_path:
        return Path(cli_path).expanduser().resolve()

    if preferred_audio_path is not None:
        return preferred_audio_path.with_suffix(".avi")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (config.output_dir / "legacy" / f"{unique_id}_{timestamp}.avi").expanduser().resolve()


def _register_legacy_download_handler(
    client: object,
    connect_event: type[object],
    output_path: Path,
    duration: int,
    quality: str | None,
    logger: logging.Logger,
    *,
    disconnect_when_done: bool = False,
) -> None:
    download_method = _require_download_method(client)

    @client.on(connect_event)
    async def _on_connect(_: object) -> None:
        capture_duration = None if duration == 0 else duration
        logger.info("Iniciando captura legacy en %s", output_path)
        result = download_method(path=str(output_path), duration=capture_duration, quality=quality)
        if inspect.isawaitable(result):
            await result
        logger.info("Captura legacy finalizada en %s", output_path)

        if disconnect_when_done and capture_duration is not None:
            await _disconnect_client(client)


def _require_download_method(client: object) -> object:
    download_method = getattr(client, "download", None)
    if callable(download_method):
        return download_method

    raise TikTokLiveApiError(
        "TikTokLiveClient.download no esta disponible en la version instalada. "
        "Usa observer watch/log para flujo soportado oficialmente."
    )


async def _disconnect_client(client: object) -> None:
    disconnect_method = getattr(client, "disconnect", None)
    if not callable(disconnect_method):
        return

    result = disconnect_method()
    if inspect.isawaitable(result):
        await result


def _ensure_ffmpeg_binary() -> None:
    ensure_ffmpeg_binary()


if __name__ == "__main__":
    raise SystemExit(main())
