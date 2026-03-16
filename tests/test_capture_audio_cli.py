from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any

from duo_observer.cli import EXIT_OK, build_parser, run_capture_audio
from duo_observer.config import ObserverConfig


class FakeConnectEvent:
    pass


class FakeCaptureClient:
    def __init__(self) -> None:
        self._listeners: dict[type[Any], Any] = {}
        self.download_calls: list[dict[str, Any]] = []
        self.disconnected = False

    def on(self, event_type: type[Any]) -> Any:
        def decorator(handler: Any) -> Any:
            self._listeners[event_type] = handler
            return handler

        return decorator

    def download(self, path: str, duration: int | None, quality: str | None) -> None:
        self.download_calls.append({"path": path, "duration": duration, "quality": quality})
        Path(path).write_text("fake-avi", encoding="utf-8")

    async def disconnect(self) -> None:
        self.disconnected = True

    def run(self) -> None:
        asyncio.run(self._listeners[FakeConnectEvent](object()))


def test_build_parser_accepts_capture_audio_command() -> None:
    parser = build_parser()

    args = parser.parse_args(["capture-audio", "--user", "rtvenoticias"])

    assert args.command == "capture-audio"
    assert args.duration == 60
    assert args.keep_video is False


def test_run_capture_audio_extracts_mp3_and_removes_temp_video(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client = FakeCaptureClient()
    extracted: dict[str, Path] = {}

    monkeypatch.setattr("duo_observer.cli._ensure_ffmpeg_binary", lambda: None)
    monkeypatch.setattr("duo_observer.cli.create_client", lambda _: client)
    monkeypatch.setattr("duo_observer.cli.load_event_types", lambda: {"ConnectEvent": FakeConnectEvent})
    monkeypatch.setattr("duo_observer.cli._check_live", lambda *_: True)

    def fake_extract_audio_to_mp3(source_media: Path, target_mp3: Path) -> None:
        extracted["source"] = source_media
        extracted["target"] = target_mp3
        target_mp3.write_text("fake-mp3", encoding="utf-8")

    monkeypatch.setattr("duo_observer.cli.extract_audio_to_mp3", fake_extract_audio_to_mp3)

    args = argparse.Namespace(
        user="rtvenoticias",
        audio_path=str(tmp_path / "captured.mp3"),
        video_path=None,
        duration=30,
        quality="sd",
        keep_video=False,
    )

    exit_code = run_capture_audio(
        args,
        ObserverConfig(output_dir=tmp_path),
        logging.getLogger("test.capture_audio.remove_temp"),
    )

    assert exit_code == EXIT_OK
    assert extracted["target"] == tmp_path / "captured.mp3"
    assert extracted["target"].read_text(encoding="utf-8") == "fake-mp3"
    assert extracted["source"].suffix == ".avi"
    assert not extracted["source"].exists()
    assert client.download_calls == [
        {
            "path": str(extracted["source"]),
            "duration": 30,
            "quality": "sd",
        }
    ]
    assert client.disconnected is True


def test_run_capture_audio_keeps_temp_video_when_requested(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client = FakeCaptureClient()
    video_path = tmp_path / "raw" / "capture.avi"
    audio_path = tmp_path / "audio" / "capture.mp3"

    monkeypatch.setattr("duo_observer.cli._ensure_ffmpeg_binary", lambda: None)
    monkeypatch.setattr("duo_observer.cli.create_client", lambda _: client)
    monkeypatch.setattr("duo_observer.cli.load_event_types", lambda: {"ConnectEvent": FakeConnectEvent})
    monkeypatch.setattr("duo_observer.cli._check_live", lambda *_: True)
    monkeypatch.setattr(
        "duo_observer.cli.extract_audio_to_mp3",
        lambda source_media, target_mp3: target_mp3.write_text(source_media.name, encoding="utf-8"),
    )

    args = argparse.Namespace(
        user="rtvenoticias",
        audio_path=str(audio_path),
        video_path=str(video_path),
        duration=5,
        quality=None,
        keep_video=True,
    )

    exit_code = run_capture_audio(
        args,
        ObserverConfig(output_dir=tmp_path),
        logging.getLogger("test.capture_audio.keep_temp"),
    )

    assert exit_code == EXIT_OK
    assert audio_path.read_text(encoding="utf-8") == "capture.avi"
    assert video_path.exists()
