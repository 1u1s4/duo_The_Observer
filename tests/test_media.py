from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from duo_observer.services.media import ensure_ffmpeg_binary, extract_audio_to_mp3


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


def test_ensure_ffmpeg_binary_raises_without_binary(monkeypatch: Any) -> None:
    monkeypatch.setattr("duo_observer.services.media.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError):
        ensure_ffmpeg_binary()


def test_extract_audio_to_mp3_with_fake_ffmpeg(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr("duo_observer.services.media.shutil.which", lambda _: "/usr/bin/ffmpeg")

    source_media = tmp_path / "capture.avi"
    source_media.write_text("fake-avi", encoding="utf-8")
    target_mp3 = tmp_path / "capture.mp3"

    extract_audio_to_mp3(source_media, target_mp3, ffmpeg_module=FakeFFmpegModule())

    assert target_mp3.read_text(encoding="utf-8") == "fake-mp3"


def test_extract_audio_to_mp3_requires_existing_source(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr("duo_observer.services.media.shutil.which", lambda _: "/usr/bin/ffmpeg")

    with pytest.raises(FileNotFoundError):
        extract_audio_to_mp3(tmp_path / "missing.avi", tmp_path / "capture.mp3")
