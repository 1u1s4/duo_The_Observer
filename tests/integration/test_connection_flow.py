from __future__ import annotations

import asyncio

from duo_observer.services.live_probe import connect_for_window


class FakeConnectionClient:
    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False

    async def connect(self) -> None:
        self.connected = True
        while not self.disconnected:
            await asyncio.sleep(0.01)

    async def disconnect(self) -> None:
        self.disconnected = True


def test_connect_disconnect_flow() -> None:
    client = FakeConnectionClient()
    asyncio.run(connect_for_window(client, 0.05))

    assert client.connected is True
    assert client.disconnected is True
