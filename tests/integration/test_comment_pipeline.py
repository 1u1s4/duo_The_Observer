from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from duo_observer.handlers import JsonlEventWriter, register_event_handlers


class FakeConnectEvent:
    pass


class FakeCommentEvent:
    pass


class FakeDisconnectEvent:
    pass


class FakeClient:
    def __init__(self) -> None:
        self.room_id = "room-01"
        self.viewer_count = 12
        self._listeners: dict[type[Any], Any] = {}

    def on(self, event_type: type[Any]) -> Any:
        def decorator(handler: Any) -> Any:
            self._listeners[event_type] = handler
            return handler

        return decorator

    def add_listener(self, event_type: type[Any], callback: Any) -> None:
        self._listeners[event_type] = callback


async def _emit_comment(client: FakeClient) -> None:
    event = SimpleNamespace(
        comment="mensaje de prueba",
        user=SimpleNamespace(
            user_id="42",
            nickname="tester",
            unique_id="tester_uid",
            sec_uid="sec-uid",
            info=SimpleNamespace(following=10, followers=20, follow_role=0),
        ),
    )
    await client._listeners[FakeCommentEvent](event)


def test_comment_event_is_written_to_jsonl(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "duo_observer.handlers.load_event_types",
        lambda: {
            "ConnectEvent": FakeConnectEvent,
            "CommentEvent": FakeCommentEvent,
            "DisconnectEvent": FakeDisconnectEvent,
        },
    )

    output = tmp_path / "comments.jsonl"
    writer = JsonlEventWriter(output)
    client = FakeClient()
    logger = logging.getLogger("test.integration.comment_pipeline")

    register_event_handlers(client, logger, writer)
    asyncio.run(_emit_comment(client))
    writer.close()

    rows = [json.loads(row) for row in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["event"] == "comment"
    assert rows[0]["comment"] == "mensaje de prueba"
    assert rows[0]["room_id"] == "room-01"
