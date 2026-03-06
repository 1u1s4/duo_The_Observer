from __future__ import annotations

import pytest

from duo_observer.client import normalize_unique_id, resolve_unique_id


def test_normalize_unique_id_accepts_with_at_prefix() -> None:
    assert normalize_unique_id("@rtvenoticias") == "rtvenoticias"


def test_normalize_unique_id_strips_spaces() -> None:
    assert normalize_unique_id("  rtvenoticias  ") == "rtvenoticias"


def test_normalize_unique_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        normalize_unique_id("   ")


def test_resolve_unique_id_prefers_cli_user() -> None:
    assert resolve_unique_id("@cli_user", "env_user") == "cli_user"


def test_resolve_unique_id_falls_back_to_env() -> None:
    assert resolve_unique_id(None, "@env_user") == "env_user"
