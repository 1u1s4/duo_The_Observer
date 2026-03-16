from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Sequence, TextIO

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
            f"ts={payload['ts']} event={payload['event']} message_id={payload.get('message_id')} "
            f"room_id={payload['room_id']} viewer_count={payload['viewer_count']} "
            f"user_id={user['user_id']} nickname={user['nickname']} unique_id={user['unique_id']} "
            f"comment={payload['comment']}"
        )
        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.close()


def build_comment_payload(
    event: Any,
    client: Any,
    *,
    viewer_count_hint: int | None = None,
) -> dict[str, Any]:
    # Priorizar user_info para evitar errores en algunas versiones donde event.user
    # puede fallar por diferencias de naming (nickName vs nick_name).
    user = _get_path(event, ("user_info",))
    if user is None:
        user = _get_path(event, ("user",))

    user_id = _first_non_empty_value(
        [
            _get_path(user, ("user_id",)),
            _get_path(user, ("id_str",)),
            _get_path(user, ("id",)),
            _get_path(event, ("user_id",)),
        ]
    )
    nickname = _first_non_empty_value(
        [
            _get_path(user, ("nickname",)),
            _get_path(user, ("display_id",)),
            _get_path(user, ("displayId",)),
            _get_path(user, ("nick_name",)),
            _get_path(user, ("nickName",)),
        ]
    )
    unique_id = _first_non_empty_value(
        [
            _get_path(user, ("unique_id",)),
            _get_path(user, ("display_id",)),
            _get_path(user, ("displayId",)),
            _get_path(user, ("uniqueId",)),
        ]
    )
    sec_uid = _first_non_empty_value(
        [
            _get_path(user, ("sec_uid",)),
            _get_path(user, ("secUid",)),
        ]
    )

    if user_id is None:
        user_id = sec_uid
    if unique_id is None:
        unique_id = _first_non_empty_value([nickname, sec_uid])
    if nickname is None:
        nickname = _first_non_empty_value([unique_id, sec_uid])

    following = _first_non_empty_value(
        [
            _get_path(user, ("info", "following")),
            _get_path(user, ("follow_info", "following_count")),
            _get_path(user, ("follow_info", "following")),
        ]
    )
    followers = _first_non_empty_value(
        [
            _get_path(user, ("info", "followers")),
            _get_path(user, ("follow_info", "follower_count")),
            _get_path(user, ("follow_info", "followers")),
        ]
    )
    follow_role = _first_non_empty_value(
        [
            _get_path(user, ("info", "follow_role")),
            _get_path(user, ("follow_info", "follow_status")),
        ]
    )

    viewer_count = _first_non_empty_value(
        [
            viewer_count_hint,
            _get_path(client, ("viewer_count",)),
            _get_path(client, ("room_info", "user_count")),
            _get_path(client, ("room_info", "viewer_count")),
            _get_path(event, ("viewer_count",)),
            _get_path(event, ("room_user_count",)),
            _get_path(event, ("total_user",)),
            _get_path(event, ("m_total",)),
            _get_path(event, ("m_popularity",)),
            _get_path(event, ("public_area_common", "room_user_count")),
            _get_path(event, ("public_area_message_common", "room_user_count")),
        ]
    )
    message_id = _first_non_empty_value(
        [
            _get_path(event, ("msg_id",)),
            _get_path(event, ("message_id",)),
            _get_path(event, ("log_id",)),
        ]
    )

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "comment",
        "message_id": message_id,
        "room_id": getattr(client, "room_id", None),
        "viewer_count": viewer_count,
        "comment": getattr(event, "comment", ""),
        "user": {
            "user_id": user_id,
            "nickname": nickname,
            "unique_id": unique_id,
            "sec_uid": sec_uid,
            "following": following,
            "followers": followers,
            "follow_role": follow_role,
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
    room_user_seq_event = events.get("RoomUserSeqEvent")

    known_user_ids: set[str] = set()
    known_message_ids: set[str] = set()
    latest_viewer_count = _extract_viewer_count(client)

    @client.on(connect_event)
    async def _on_connect(event: Any) -> None:
        room_id = getattr(event, "room_id", None) or getattr(client, "room_id", None)
        logger.info("Connected to Room ID: %s", room_id)

    @client.on(disconnect_event)
    async def _on_disconnect(_: Any) -> None:
        logger.info("Disconnected from room_id=%s", getattr(client, "room_id", None))

    if room_user_seq_event is not None:

        @client.on(room_user_seq_event)
        async def _on_room_user_seq(event: Any) -> None:
            nonlocal latest_viewer_count
            resolved = _extract_viewer_count(event)
            if resolved is not None:
                latest_viewer_count = resolved
                with suppress(Exception):
                    setattr(client, "viewer_count", resolved)

    async def _on_comment(event: Any) -> None:
        nonlocal latest_viewer_count
        payload = build_comment_payload(event, client, viewer_count_hint=latest_viewer_count)
        if payload["viewer_count"] is not None:
            latest_viewer_count = payload["viewer_count"]
        message_id = payload.get("message_id")
        if message_id is not None:
            message_key = str(message_id)
            if message_key in known_message_ids:
                return
            known_message_ids.add(message_key)

        user_data = payload["user"]

        dedupe_user = _first_non_empty_value([user_data.get("user_id"), user_data.get("sec_uid")])
        if dedupe_user is not None and str(dedupe_user) not in known_user_ids:
            known_user_ids.add(str(dedupe_user))
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

        display_user = _first_non_empty_value(
            [user_data.get("user_id"), user_data.get("unique_id"), user_data.get("sec_uid")]
        )
        logger.info("%s -> %s", display_user or "unknown", payload["comment"])
        logger.info("viewer_count: %s", payload["viewer_count"])

        if writer is not None:
            writer.write(payload)

    client.add_listener(comment_event, _on_comment)


def _get_path(container: Any, path: Sequence[str]) -> Any:
    current = container
    for key in path:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            try:
                current = getattr(current, key, None)
            except Exception:  # noqa: BLE001
                return None
    return current


def _first_non_empty_value(values: Iterable[Any]) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _extract_viewer_count(source: Any) -> int | None:
    raw = _first_non_empty_value(
        [
            _get_path(source, ("viewer_count",)),
            _get_path(source, ("room_user_count",)),
            _get_path(source, ("total_user",)),
            _get_path(source, ("m_total",)),
            _get_path(source, ("m_popularity",)),
            _get_path(source, ("public_area_common", "room_user_count")),
            _get_path(source, ("public_area_message_common", "room_user_count")),
            _get_path(source, ("room_info", "user_count")),
            _get_path(source, ("room_info", "viewer_count")),
        ]
    )
    if raw is None:
        return None

    with suppress(TypeError, ValueError):
        return int(raw)
    return None
