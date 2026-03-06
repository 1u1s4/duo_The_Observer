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
        self.room_id = "1234"
        self.viewer_count = 99
        self._decorated: list[type[Any]] = []
        self._listeners: dict[type[Any], Any] = {}

    def on(self, event_type: type[Any]) -> Any:
        self._decorated.append(event_type)

        def decorator(handler: Any) -> Any:
            self._listeners[event_type] = handler
            return handler

        return decorator

    def add_listener(self, event_type: type[Any], callback: Any) -> None:
        self._listeners[event_type] = callback


async def _emit_comment(client: FakeClient, event: Any) -> None:
    callback = client._listeners[FakeCommentEvent]
    await callback(event)


def test_register_event_handlers_uses_event_types(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "duo_observer.handlers.load_event_types",
        lambda: {
            "ConnectEvent": FakeConnectEvent,
            "CommentEvent": FakeCommentEvent,
            "DisconnectEvent": FakeDisconnectEvent,
        },
    )

    client = FakeClient()
    writer = JsonlEventWriter(tmp_path / "events.jsonl")
    logger = logging.getLogger("test.handlers")

    register_event_handlers(client, logger, writer)

    assert FakeConnectEvent in client._decorated
    assert FakeDisconnectEvent in client._decorated
    assert FakeCommentEvent in client._listeners

    event = SimpleNamespace(
        comment="hola",
        user=SimpleNamespace(
            user_id="u1",
            nickname="nick",
            unique_id="uniq",
            sec_uid="sec",
            info=SimpleNamespace(following=1, followers=2, follow_role=0),
        ),
    )
    asyncio.run(_emit_comment(client, event))
    writer.close()

    payload = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert payload["comment"] == "hola"
    assert payload["user"]["user_id"] == "u1"
