# duo_The_Observer

CLI para observar TikTok Live con `TikTokLive`.

## Requisitos
- Python `>=3.10` (recomendado: Python `3.12`).
- `TikTokLive` para comandos principales.

## Instalacion
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e .[dev]
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

## Formatos de salida
`observer log` soporta:
- `jsonl`: una linea JSON por evento (recomendado para pipelines).
- `text`: lineas estructuradas tipo `key=value`.

## Estructura
- `src/duo_observer/`: implementacion principal.
- `docs/`: arquitectura y documentacion.
- `tests/`: unitarias, integracion y smoke live.

## Pruebas y calidad
```bash
python -m pytest -q
python -m pytest -m live -q
ruff check .
```

## Documentacion adicional
- [Arquitectura](docs/ARCHITECTURE.md)

## Troubleshooting
- `TikTokLive no esta instalado`: ejecuta `pip install -e .`.
- Smoke test live falla por red: verifica DNS/salida a `www.tiktok.com`.
