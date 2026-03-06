from __future__ import annotations

from importlib import import_module
from typing import Any


class TikTokLiveDependencyError(RuntimeError):
    """Raised when TikTokLive cannot be imported."""


class TikTokLiveApiError(RuntimeError):
    """Raised when expected TikTokLive API elements are not available."""


def normalize_unique_id(unique_id: str) -> str:
    cleaned = unique_id.strip()
    if not cleaned:
        raise ValueError("El unique_id no puede estar vacio")

    if cleaned.startswith("@"):
        cleaned = cleaned[1:]

    if not cleaned:
        raise ValueError("El unique_id no puede estar vacio")

    return cleaned


def resolve_unique_id(cli_user: str | None, env_user: str | None) -> str:
    selected = cli_user or env_user
    if not selected:
        raise ValueError("Debes indicar --user o definir TIKTOK_USER")
    return normalize_unique_id(selected)


def load_tiktoklive_client_class() -> type[Any]:
    try:
        module = import_module("TikTokLive")
    except ModuleNotFoundError as exc:
        raise TikTokLiveDependencyError(
            "TikTokLive no esta instalado. Instala dependencias con: pip install -e ."
        ) from exc

    client_class = getattr(module, "TikTokLiveClient", None)
    if client_class is None:
        raise TikTokLiveApiError("No se encontro TikTokLiveClient en el paquete TikTokLive")

    return client_class


def load_event_types() -> dict[str, type[Any]]:
    try:
        events_module = import_module("TikTokLive.events")
    except ModuleNotFoundError as exc:
        raise TikTokLiveDependencyError(
            "No se pudo importar TikTokLive.events. Verifica la version de TikTokLive"
        ) from exc

    required_names = ("ConnectEvent", "CommentEvent", "DisconnectEvent")
    event_types: dict[str, type[Any]] = {}
    for name in required_names:
        event_type = getattr(events_module, name, None)
        if event_type is None:
            raise TikTokLiveApiError(f"No se encontro {name} en TikTokLive.events")
        event_types[name] = event_type

    return event_types


def create_client(unique_id: str, **kwargs: Any) -> Any:
    client_class = load_tiktoklive_client_class()
    return client_class(unique_id=normalize_unique_id(unique_id), **kwargs)


async def is_user_live(client: Any) -> bool:
    return bool(await client.is_live())
