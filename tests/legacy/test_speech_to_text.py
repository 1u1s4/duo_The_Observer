from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.legacy import speech_to_text


class FakeFFmpegStream:
    def __init__(self, target: Path) -> None:
        self.target = target

    def output(self, target: str) -> "FakeFFmpegStream":
        self.target = Path(target)
        return self

    def overwrite_output(self) -> "FakeFFmpegStream":
        return self

    def run(self) -> None:
        self.target.write_text("fake-mp3", encoding="utf-8")


class FakeFFmpegModule:
    @staticmethod
    def input(_: str) -> FakeFFmpegStream:
        return FakeFFmpegStream(Path("audio.mp3"))


class FakeMel:
    def to(self, _: str) -> "FakeMel":
        return self


class FakeWhisperModel:
    device = "cpu"

    @staticmethod
    def detect_language(_: Any) -> tuple[None, dict[str, float]]:
        return None, {"es": 0.9, "en": 0.1}


class FakeWhisperModule:
    @staticmethod
    def load_model(_: str) -> FakeWhisperModel:
        return FakeWhisperModel()

    @staticmethod
    def load_audio(_: str) -> str:
        return "audio"

    @staticmethod
    def pad_or_trim(audio: str) -> str:
        return audio

    @staticmethod
    def log_mel_spectrogram(_: str) -> FakeMel:
        return FakeMel()

    @staticmethod
    def DecodingOptions() -> object:  # noqa: N802
        return object()

    @staticmethod
    def decode(_: Any, __: Any, ___: Any) -> SimpleNamespace:
        return SimpleNamespace(text="transcripcion de prueba")


def test_ensure_ffmpeg_available_raises_without_binary(monkeypatch: Any) -> None:
    monkeypatch.setattr("scripts.legacy.speech_to_text.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError):
        speech_to_text.ensure_ffmpeg_available()


def test_run_pipeline_with_fake_modules(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr("scripts.legacy.speech_to_text.shutil.which", lambda _: "/usr/bin/ffmpeg")

    source_avi = tmp_path / "audio.avi"
    source_avi.write_text("fake-avi", encoding="utf-8")

    target_mp3 = tmp_path / "audio.mp3"
    target_text = tmp_path / "recognized.txt"

    result = speech_to_text.run_pipeline(
        source_avi=source_avi,
        target_mp3=target_mp3,
        output_text=target_text,
        ffmpeg_module=FakeFFmpegModule(),
        whisper_module=FakeWhisperModule(),
    )

    assert target_mp3.exists()
    assert target_text.read_text(encoding="utf-8") == "transcripcion de prueba"
    assert result.language == "es"
