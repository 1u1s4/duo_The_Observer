from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, TextIO

from duo_observer.client import load_event_types


@dataclass(slots=True)
class JsonlEventWriter:
    path: Path
    _file: TextIO | None = None

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, payload: dict[str, Any]) -> None:
        if self._file is None:
            raise RuntimeError("El archivo de salida no fue inicializado")
        self._file.write(json.dumps(payload, ensure_ascii=True) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.close()


@dataclass(slots=True)
class TextEventWriter:
    path: Path
    _file: TextIO | None = None

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, payload: dict[str, Any]) -> None:
        if self._file is None:
            raise RuntimeError("El archivo de salida no fue inicializado")

        user = payload["user"]
        line = (
            f"ts={payload['ts']} event={payload['event']} room_id={payload['room_id']} "
            f"viewer_count={payload['viewer_count']} user_id={user['user_id']} "
            f"nickname={user['nickname']} unique_id={user['unique_id']} "
            f"comment={payload['comment']}"
        )
        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.close()


def build_comment_payload(event: Any, client: Any) -> dict[str, Any]:
    user = getattr(event, "user", None)
    info = getattr(user, "info", None)

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "comment",
        "room_id": getattr(client, "room_id", None),
        "viewer_count": getattr(client, "viewer_count", None),
        "comment": getattr(event, "comment", ""),
        "user": {
            "user_id": getattr(user, "user_id", None),
            "nickname": getattr(user, "nickname", None),
            "unique_id": getattr(user, "unique_id", None),
            "sec_uid": getattr(user, "sec_uid", None),
            "following": getattr(info, "following", None),
            "followers": getattr(info, "followers", None),
            "follow_role": getattr(info, "follow_role", None),
        },
    }


def register_event_handlers(
    client: Any,
    logger: logging.Logger,
    writer: JsonlEventWriter | TextEventWriter | None = None,
) -> None:
    events = load_event_types()
    connect_event = events["ConnectEvent"]
    comment_event = events["CommentEvent"]
    disconnect_event = events["DisconnectEvent"]

    known_user_ids: set[str] = set()

    @client.on(connect_event)
    async def _on_connect(event: Any) -> None:
        room_id = getattr(event, "room_id", None) or getattr(client, "room_id", None)
        logger.info("Connected to Room ID: %s", room_id)

    @client.on(disconnect_event)
    async def _on_disconnect(_: Any) -> None:
        logger.info("Disconnected from room_id=%s", getattr(client, "room_id", None))

    async def _on_comment(event: Any) -> None:
        payload = build_comment_payload(event, client)
        user_data = payload["user"]

        user_id = str(user_data.get("user_id"))
        if user_id not in known_user_ids:
            known_user_ids.add(user_id)
            logger.info(
                "user_data: %s | %s | %s | %s | %s | %s | %s",
                user_data.get("user_id"),
                user_data.get("nickname"),
                user_data.get("unique_id"),
                user_data.get("sec_uid"),
                user_data.get("following"),
                user_data.get("followers"),
                user_data.get("follow_role"),
            )

        logger.info("%s -> %s", user_data.get("user_id"), payload["comment"])
        logger.info("viewer_count: %s", payload["viewer_count"])

        if writer is not None:
            writer.write(payload)

    client.add_listener(comment_event, _on_comment)
