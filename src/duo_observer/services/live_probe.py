from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class LiveProbeResult:
    unique_id: str
    is_live: bool
    checked_at: datetime
    error: str | None = None


async def probe_live_status(client: Any) -> bool:
    return bool(await client.is_live())


async def build_probe_result(client: Any, unique_id: str) -> LiveProbeResult:
    checked_at = datetime.now(timezone.utc)
    try:
        is_live = await probe_live_status(client)
    except Exception as exc:  # noqa: BLE001
        return LiveProbeResult(unique_id=unique_id, is_live=False, checked_at=checked_at, error=str(exc))

    return LiveProbeResult(unique_id=unique_id, is_live=is_live, checked_at=checked_at)


async def connect_for_window(client: Any, window_seconds: float) -> None:
    connect_task = asyncio.create_task(client.connect())

    try:
        await asyncio.sleep(window_seconds)
    finally:
        try:
            await client.disconnect()
        finally:
            if not connect_task.done():
                connect_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await connect_task
