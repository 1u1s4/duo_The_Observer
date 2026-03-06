from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Any

import pytest

from duo_observer.client import TikTokLiveDependencyError, create_client, load_event_types

pytestmark = pytest.mark.live


def _dns_available() -> bool:
    try:
        socket.gethostbyname("www.tiktok.com")
        return True
    except OSError:
        return False


@pytest.mark.asyncio
async def test_rtvenoticias_smoke_best_effort() -> None:
    if not _dns_available():
        pytest.skip("Sin conectividad DNS para www.tiktok.com")

    try:
        client = create_client("rtvenoticias")
        event_types = load_event_types()
    except TikTokLiveDependencyError as exc:
        pytest.skip(f"TikTokLive no instalado: {exc}")

    connected = asyncio.Event()

    @client.on(event_types["ConnectEvent"])
    async def _on_connect(_: Any) -> None:
        connected.set()

    try:
        is_live = await client.is_live()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"No fue posible consultar is_live(): {exc}")

    if not is_live:
        pytest.skip("@rtvenoticias no esta en vivo en este momento")

    connect_task = asyncio.create_task(client.connect())
    try:
        await asyncio.wait_for(connected.wait(), timeout=25)
    finally:
        with contextlib.suppress(Exception):
            await client.disconnect()

        if not connect_task.done():
            connect_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await connect_task
