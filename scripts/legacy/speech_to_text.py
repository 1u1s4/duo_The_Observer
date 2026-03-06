from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import shutil
import sys
import warnings
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    language: str
    text: str


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg no esta instalado o no esta en PATH")


def convert_avi_to_mp3(
    source_avi: Path,
    target_mp3: Path,
    ffmpeg_module: Any | None = None,
) -> None:
    ensure_ffmpeg_available()

    if not source_avi.exists():
        raise FileNotFoundError(f"No existe archivo fuente: {source_avi}")

    ffmpeg_lib = ffmpeg_module or import_module("ffmpeg")

    stream = ffmpeg_lib.input(str(source_avi)).output(str(target_mp3))
    if hasattr(stream, "overwrite_output"):
        stream = stream.overwrite_output()
    stream.run()


def transcribe_mp3_to_text(
    source_mp3: Path,
    output_text: Path,
    model_name: str = "base",
    whisper_module: Any | None = None,
) -> TranscriptionResult:
    if not source_mp3.exists():
        raise FileNotFoundError(f"No existe archivo fuente: {source_mp3}")

    whisper_lib = whisper_module or import_module("whisper")

    model = whisper_lib.load_model(model_name)
    audio = whisper_lib.load_audio(str(source_mp3))
    audio = whisper_lib.pad_or_trim(audio)
    mel = whisper_lib.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)

    options = whisper_lib.DecodingOptions()
    result = whisper_lib.decode(model, mel, options)

    language = max(probs, key=probs.get)
    output_text.parent.mkdir(parents=True, exist_ok=True)
    output_text.write_text(result.text, encoding="utf-8")
    return TranscriptionResult(language=language, text=result.text)


def run_pipeline(
    source_avi: Path,
    target_mp3: Path,
    output_text: Path,
    model_name: str = "base",
    ffmpeg_module: Any | None = None,
    whisper_module: Any | None = None,
) -> TranscriptionResult:
    convert_avi_to_mp3(source_avi, target_mp3, ffmpeg_module=ffmpeg_module)
    return transcribe_mp3_to_text(
        target_mp3,
        output_text,
        model_name=model_name,
        whisper_module=whisper_module,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legacy AVI to text pipeline")
    parser.add_argument("--input", default="audio.avi", help="Archivo AVI de entrada")
    parser.add_argument("--mp3", default="audio.mp3", help="Archivo MP3 temporal")
    parser.add_argument("--output", default="recognized.txt", help="Archivo de texto de salida")
    parser.add_argument("--model", default="base", help="Modelo whisper")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    warnings.warn(
        "scripts/legacy/speech_to_text.py es legacy y depende de ffmpeg + whisper.",
        DeprecationWarning,
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    source_avi = Path(args.input).expanduser().resolve()
    target_mp3 = Path(args.mp3).expanduser().resolve()
    output_text = Path(args.output).expanduser().resolve()

    try:
        result = run_pipeline(source_avi, target_mp3, output_text, model_name=args.model)
    except Exception as exc:  # noqa: BLE001
        print(f"speech-to-text error: {exc}", file=sys.stderr)
        return 1

    print(f"Detected language: {result.language}")
    print(f"Saved transcription to: {output_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
