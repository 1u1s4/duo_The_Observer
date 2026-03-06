from __future__ import annotations

import asyncio

from duo_observer.services.live_probe import build_probe_result, probe_live_status


class FakeLiveClient:
    async def is_live(self) -> bool:
        return False


class FailingLiveClient:
    async def is_live(self) -> bool:
        raise RuntimeError("network error")


def test_probe_live_status_false() -> None:
    result = asyncio.run(probe_live_status(FakeLiveClient()))
    assert result is False


def test_build_probe_result_captures_error() -> None:
    result = asyncio.run(build_probe_result(FailingLiveClient(), "rtvenoticias"))

    assert result.unique_id == "rtvenoticias"
    assert result.is_live is False
    assert result.error is not None
