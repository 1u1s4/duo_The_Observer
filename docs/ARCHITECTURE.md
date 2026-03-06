# Arquitectura

## Objetivo
`duo_The_Observer` provee una CLI para observar TikTok Live usando `TikTokLive`, con un flujo principal soportado y un flujo legacy aislado.

## Estructura
- `src/duo_observer/config.py`: contrato de configuracion por variables de entorno.
- `src/duo_observer/client.py`: integracion con `TikTokLiveClient`, carga de eventos y normalizacion de `unique_id`.
- `src/duo_observer/handlers.py`: handlers de eventos (`ConnectEvent`, `CommentEvent`, `DisconnectEvent`) y salidas estructuradas (`jsonl`/texto).
- `src/duo_observer/services/live_probe.py`: verificacion `is_live()` y utilidades de sonda.
- `src/duo_observer/cli.py`: comandos `watch`, `log`, `live-check`, `legacy-download`.
- `scripts/legacy/*`: scripts heredados compatibles pero no recomendados.

## Flujo principal
1. Resolver `unique_id` desde CLI o `TIKTOK_USER`.
2. Crear cliente `TikTokLiveClient` con API actual (`TikTokLive.events`).
3. Ejecutar `is_live()` para comportamiento best-effort.
4. Si la cuenta esta en vivo, registrar listeners y ejecutar `client.run()`.
5. Persistir comentarios opcionalmente en formato `jsonl` o texto estructurado.

## Flujo legacy
- `legacy-download` y `speech_to_text` quedan fuera del camino principal.
- Requieren prerequisitos extras (`ffmpeg`, `whisper`) y no tienen garantias de compatibilidad con futuras versiones de `TikTokLive`.

## Manejo de errores
- Dependencia faltante (`TikTokLive`) -> error explicito de instalacion.
- API faltante (`download`) -> error controlado con mensaje de migracion.
- Cuenta no en vivo -> salida controlada con codigo `3`.
