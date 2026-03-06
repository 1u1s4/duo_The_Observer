from __future__ import annotations

from duo_observer.config import ObserverConfig


def test_config_from_env_defaults() -> None:
    cfg = ObserverConfig.from_env({})

    assert cfg.tiktok_user is None
    assert cfg.log_level == "INFO"
    assert cfg.connect_timeout == 15.0
    assert cfg.retry_seconds == 10.0


def test_config_from_env_values() -> None:
    cfg = ObserverConfig.from_env(
        {
            "TIKTOK_USER": "@rtvenoticias",
            "OBSERVER_OUTPUT_DIR": "./tmp-output",
            "OBSERVER_LOG_LEVEL": "debug",
            "OBSERVER_CONNECT_TIMEOUT": "22",
            "OBSERVER_RETRY_SECONDS": "5",
        }
    )

    assert cfg.tiktok_user == "@rtvenoticias"
    assert str(cfg.output_dir).endswith("tmp-output")
    assert cfg.log_level == "DEBUG"
    assert cfg.connect_timeout == 22.0
    assert cfg.retry_seconds == 5.0
