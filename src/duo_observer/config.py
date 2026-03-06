from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CONNECT_TIMEOUT = 15.0
DEFAULT_RETRY_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class ObserverConfig:
    tiktok_user: str | None = None
    output_dir: Path = DEFAULT_OUTPUT_DIR
    log_level: str = DEFAULT_LOG_LEVEL
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    retry_seconds: float = DEFAULT_RETRY_SECONDS

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "ObserverConfig":
        data = dict(os.environ if environ is None else environ)

        return cls(
            tiktok_user=_none_if_empty(data.get("TIKTOK_USER")),
            output_dir=Path(data.get("OBSERVER_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)).expanduser(),
            log_level=data.get("OBSERVER_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
            connect_timeout=_parse_float(
                data.get("OBSERVER_CONNECT_TIMEOUT"),
                DEFAULT_CONNECT_TIMEOUT,
                "OBSERVER_CONNECT_TIMEOUT",
                allow_zero=False,
            ),
            retry_seconds=_parse_float(
                data.get("OBSERVER_RETRY_SECONDS"),
                DEFAULT_RETRY_SECONDS,
                "OBSERVER_RETRY_SECONDS",
                allow_zero=True,
            ),
        )


def _none_if_empty(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped if stripped else None


def _parse_float(
    raw_value: str | None,
    default: float,
    field_name: str,
    *,
    allow_zero: bool,
) -> float:
    if raw_value in (None, ""):
        return default

    try:
        parsed = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{field_name} debe ser numerico: {raw_value!r}") from exc

    minimum = 0.0 if allow_zero else 0.000001
    if parsed < minimum or (not allow_zero and parsed == 0.0):
        comparator = "mayor o igual a 0" if allow_zero else "mayor a 0"
        raise ValueError(f"{field_name} debe ser {comparator}: {raw_value!r}")

    return parsed
