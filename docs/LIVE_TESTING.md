# Pruebas live con `@rtvenoticias`

## Enfoque
La prueba live se implementa como **best-effort**:
1. Consultar `is_live()`.
2. Si no esta en vivo, marcar `skip` informativo.
3. Si esta en vivo, conectar una ventana corta y validar `ConnectEvent`.

## Requisitos
- Dependencias instaladas (`TikTokLive`, `pytest`, `pytest-asyncio`).
- Conectividad real a TikTok (`www.tiktok.com` resolviendo DNS).

## Ejecutar smoke test
```bash
python -m pytest -m live -q
```

## Ejecutar via CLI
```bash
observer live-check --user rtvenoticias
```

## Criterio esperado
- Exit code `0`: usuario en vivo.
- Exit code `3`: usuario offline (esperado en modo best-effort).
- Exit code `1`: error de red/dependencias.

## Nota de entorno
Si no hay conectividad DNS o salida a internet, la prueba live se omite/fracasa por entorno, no por logica del proyecto.
