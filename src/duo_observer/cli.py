from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Sequence

from duo_observer.client import (
    TikTokLiveApiError,
    TikTokLiveDependencyError,
    create_client,
    resolve_unique_id,
)
from duo_observer.config import ObserverConfig
from duo_observer.handlers import JsonlEventWriter, TextEventWriter, register_event_handlers
from duo_observer.services.live_probe import build_probe_result, probe_live_status

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_BAD_INPUT = 2
EXIT_NOT_LIVE = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observer", description="CLI para observar TikTok Live")
    parser.add_argument(
        "--version",
        action="version",
        version="duo-the-observer 0.2.0",
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


if __name__ == "__main__":
    raise SystemExit(main())
