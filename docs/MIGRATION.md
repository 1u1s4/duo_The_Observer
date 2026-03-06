# Migracion desde scripts originales

## Antes
El repo tenia scripts sueltos en raiz:
- `download.py`
- `log.py`
- `wacher.py`
- `Speech-To-Text.py`

Problemas detectados:
- Imports obsoletos (`TikTokLive.types.events`).
- Paths hardcodeados fuera del repo.
- Sin contrato de configuracion.
- Sin pruebas ni documentacion de arquitectura.

## Ahora
- La funcionalidad principal vive en `src/duo_observer/`.
- Se expone la CLI unificada `observer`.
- Se usa API actual `from TikTokLive.events import ...`.
- Se adopta estrategia best-effort: `is_live()` antes de conectar.
- Scripts heredados se movieron a `scripts/legacy/`.
- Los archivos de raiz quedaron como wrappers de compatibilidad con advertencia de deprecacion.

## Mapeo de comandos
- Antes: `python wacher.py` -> Ahora: `observer live-check --user <id>`
- Antes: `python log.py` -> Ahora: `observer log --user <id> --output ./output/logs/<archivo>.jsonl`
- Antes: `python download.py` -> Ahora: `observer legacy-download --user <id>` (solo legacy)
- Antes: `python Speech-To-Text.py` -> Ahora: `python scripts/legacy/speech_to_text.py --input audio.avi`

## Variables de entorno
Se estandariza `.env` con:
- `TIKTOK_USER`
- `OBSERVER_OUTPUT_DIR`
- `OBSERVER_LOG_LEVEL`
- `OBSERVER_CONNECT_TIMEOUT`
- `OBSERVER_RETRY_SECONDS`
