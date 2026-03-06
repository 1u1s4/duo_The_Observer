# duo_The_Observer

CLI para observar TikTok Live con `TikTokLive`, con flujo principal alineado a la API actual y utilidades legacy aisladas.

## Estado del proyecto
- Flujo principal soportado: `watch`, `log`, `live-check`.
- Flujo legacy aislado: `legacy-download`, `speech_to_text`.
- Compatibilidad de scripts antiguos mantenida mediante wrappers deprecados.

## Requisitos
- Python `>=3.10` (recomendado: Python `3.12` para baseline operativa).
- `TikTokLive` para comandos principales.
- `ffmpeg` + `openai-whisper` para utilidades legacy de audio/video.

## Instalacion
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e .[dev]
```

Opcional (legacy):
```bash
pip install -e .[legacy]
```

## Configuracion
Copia `.env.example` y ajusta variables:
- `TIKTOK_USER`
- `OBSERVER_OUTPUT_DIR`
- `OBSERVER_LOG_LEVEL`
- `OBSERVER_CONNECT_TIMEOUT`
- `OBSERVER_RETRY_SECONDS`

## Uso de la CLI
### Ver estado live
```bash
observer live-check --user rtvenoticias
```

### Observar eventos en consola
```bash
observer watch --user rtvenoticias
```

### Guardar eventos estructurados
```bash
observer log --user rtvenoticias --output ./output/logs/rtve.jsonl --format jsonl
```

### Descarga legacy (no recomendada)
```bash
observer legacy-download --user rtvenoticias --path ./output/legacy/rtve.avi --duration 60
```

## Formatos de salida
`observer log` soporta:
- `jsonl`: una linea JSON por evento (recomendado para pipelines).
- `text`: lineas estructuradas tipo `key=value`.

## Estructura
- `src/duo_observer/`: implementacion principal.
- `scripts/legacy/`: scripts heredados, con prerequisitos adicionales.
- `docs/`: arquitectura, migracion y pruebas live.
- `tests/`: unitarias, integracion, legacy y smoke live.

## Pruebas y calidad
```bash
python -m pytest -q
python -m pytest -m live -q
ruff check .
```

## Documentacion adicional
- [Arquitectura](docs/ARCHITECTURE.md)
- [Migracion](docs/MIGRATION.md)
- [Live testing](docs/LIVE_TESTING.md)

## Troubleshooting
- `TikTokLive no esta instalado`: ejecuta `pip install -e .`.
- `ffmpeg no esta instalado`: instala `ffmpeg` y valida con `ffmpeg -version`.
- Smoke test live falla por red: verifica DNS/salida a `www.tiktok.com`.
- `legacy-download` falla por API: la funcionalidad depende de metodos no garantizados por versiones recientes.
