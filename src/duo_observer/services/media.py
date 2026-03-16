from __future__ import annotations

from importlib import import_module
from pathlib import Path
import shutil
from typing import Any


def ensure_ffmpeg_binary() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg no esta instalado o no esta en PATH. "
            "Instala ffmpeg para usar flujos legacy de audio/video."
        )


def extract_audio_to_mp3(
    source_media: Path,
    target_mp3: Path,
    ffmpeg_module: Any | None = None,
) -> None:
    ensure_ffmpeg_binary()

    if not source_media.exists():
        raise FileNotFoundError(f"No existe archivo fuente: {source_media}")

    try:
        ffmpeg_lib = ffmpeg_module or import_module("ffmpeg")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg-python no esta instalado. Instala dependencias con: pip install -e .[legacy]"
        ) from exc

    target_mp3.parent.mkdir(parents=True, exist_ok=True)

    stream = ffmpeg_lib.input(str(source_media)).output(str(target_mp3))
    if hasattr(stream, "overwrite_output"):
        stream = stream.overwrite_output()
    stream.run()
