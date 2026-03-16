from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from duo_observer.handlers import JsonlEventWriter, build_comment_payload, register_event_handlers


class FakeConnectEvent:
    pass


class FakeCommentEvent:
    pass


class FakeDisconnectEvent:
    pass


class FakeRoomUserSeqEvent:
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


async def _emit_room_seq(client: FakeClient, event: Any) -> None:
    callback = client._listeners[FakeRoomUserSeqEvent]
    await callback(event)


def test_register_event_handlers_uses_event_types(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "duo_observer.handlers.load_event_types",
        lambda: {
            "ConnectEvent": FakeConnectEvent,
            "CommentEvent": FakeCommentEvent,
            "DisconnectEvent": FakeDisconnectEvent,
            "RoomUserSeqEvent": FakeRoomUserSeqEvent,
        },
    )

    client = FakeClient()
    writer = JsonlEventWriter(tmp_path / "events.jsonl")
    logger = logging.getLogger("test.handlers")

    register_event_handlers(client, logger, writer)

    assert FakeConnectEvent in client._decorated
    assert FakeDisconnectEvent in client._decorated
    assert FakeRoomUserSeqEvent in client._decorated
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


def test_build_comment_payload_fallbacks_for_user_info_and_viewers() -> None:
    client = SimpleNamespace(room_id="abc", viewer_count=None)
    event = SimpleNamespace(
        comment="mensaje",
        room_user_count=321,
        user_info=SimpleNamespace(
            id_str="7788",
            display_id="usuario_demo",
            secUid="SEC-XYZ",
            follow_info=SimpleNamespace(following_count=11, follower_count=22, follow_status=1),
        ),
    )

    payload = build_comment_payload(event, client)

    assert payload["viewer_count"] == 321
    assert payload["user"]["user_id"] == "7788"
    assert payload["user"]["unique_id"] == "usuario_demo"
    assert payload["user"]["sec_uid"] == "SEC-XYZ"


def test_build_comment_payload_uses_secuid_when_id_is_missing() -> None:
    client = SimpleNamespace(room_id="abc", viewer_count=None)
    event = SimpleNamespace(
        comment="mensaje",
        user_info=SimpleNamespace(secUid="SEC-ONLY"),
    )

    payload = build_comment_payload(event, client)

    assert payload["user"]["user_id"] == "SEC-ONLY"
    assert payload["user"]["nickname"] == "SEC-ONLY"
    assert payload["user"]["unique_id"] == "SEC-ONLY"


def test_register_event_handlers_deduplicates_by_message_id(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "duo_observer.handlers.load_event_types",
        lambda: {
            "ConnectEvent": FakeConnectEvent,
            "CommentEvent": FakeCommentEvent,
            "DisconnectEvent": FakeDisconnectEvent,
            "RoomUserSeqEvent": FakeRoomUserSeqEvent,
        },
    )

    client = FakeClient()
    writer = JsonlEventWriter(tmp_path / "events.jsonl")
    logger = logging.getLogger("test.handlers.dedupe")
    register_event_handlers(client, logger, writer)

    event = SimpleNamespace(
        msg_id="msg-1",
        comment="hola",
        user=SimpleNamespace(user_id="u1", nickname="nick", unique_id="uniq", sec_uid="sec"),
    )

    asyncio.run(_emit_comment(client, event))
    asyncio.run(_emit_comment(client, event))
    writer.close()

    rows = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_register_event_handlers_uses_room_user_seq_for_viewer_count(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "duo_observer.handlers.load_event_types",
        lambda: {
            "ConnectEvent": FakeConnectEvent,
            "CommentEvent": FakeCommentEvent,
            "DisconnectEvent": FakeDisconnectEvent,
            "RoomUserSeqEvent": FakeRoomUserSeqEvent,
        },
    )

    client = FakeClient()
    client.viewer_count = None
    writer = JsonlEventWriter(tmp_path / "events.jsonl")
    logger = logging.getLogger("test.handlers.viewer_count")
    register_event_handlers(client, logger, writer)

    room_seq_event = SimpleNamespace(total_user=4321)
    asyncio.run(_emit_room_seq(client, room_seq_event))

    comment_event = SimpleNamespace(
        comment="hola",
        user=SimpleNamespace(user_id="u1", nickname="nick", unique_id="uniq", sec_uid="sec"),
    )
    asyncio.run(_emit_comment(client, comment_event))
    writer.close()

    row = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["viewer_count"] == 4321
