# AGENTS.md - Video Extractor Project

## Project Overview

Proyecto Python para transcribir video con `ffmpeg` + `faster-whisper`.

- Extrae audio del video.
- Divide en chunks.
- Transcribe por segmentos.
- Exporta `TXT`, `SRT` y `JSON`.

**Archivo principal**: `transcribir_video.py`.

---

## 🚨 Docker obligatorio (regla crítica)

Este repositorio se opera en modo **Docker-only**.

### Prohibido en host

```bash
python transcribir_video.py <video>
pip install -r requirements.txt
ruff check transcribir_video.py
mypy transcribir_video.py
```

### Obligatorio (siempre en contenedor)

```bash
make up
make dev VIDEO=./sample.mp4
make lint
make format
make typecheck
```

### Secuencia requerida

```bash
make up
make <target>
```

Excepciones permitidas en host:

- Comandos `docker build` / `docker run` (solo cuando los encapsula `make`)
- Operaciones `git`
- Edición de archivos

---

## Commands (source of truth)

Usar [`Makefile`](Makefile) como entrypoint oficial.

### Setup

```bash
make install-dev
```

### Desarrollo

```bash
make dev VIDEO=./sample.mp4
make transcribe VIDEO=./sample.mp4 MODEL=small LANGUAGE=es
```

### Calidad

```bash
make format
make lint
make typecheck
make check
```

### Docker lifecycle

```bash
make up
make down
make logs
make shell
make status
```

---

## MVP-first

Construir solo lo mínimo necesario para validar el valor del CLI.

1. Máxima simplicidad.
2. Sin sobre-ingeniería.
3. Sin features “por si acaso”.
4. Sin automatizaciones innecesarias fuera del flujo principal.

---

## Code Style (Python)

- **Python**: 3.11+
- **Typing**: obligatorio en funciones/clases
- **I/O**: `pathlib.Path` y `encoding="utf-8"`
- **Errores de dominio**: mensajes en español
- **Subprocess**: `check=True`, `capture_output=True`, `text=True`

### Convenciones

| Elemento   | Convención       | Ejemplo                  |
| ---------- | ---------------- | ------------------------ |
| Funciones  | snake_case       | `extraer_audio_de_video` |
| Clases     | PascalCase       | `ErrorTranscripcion`     |
| Constantes | UPPER_SNAKE_CASE | `DEFAULT_CHUNK_SECONDS`  |
| Variables  | snake_case       | `audio_path`             |

---

## Testing Policy (MVP)

Validación manual obligatoria, ejecutada dentro del contenedor:

```bash
make check
make dev VIDEO=./sample.mp4
```

No crear tests automatizados salvo pedido explícito.

---

## Skills

- `docker-expert`: diseño de imagen Docker, seguridad, flujos Docker-only sin Compose.
- `python-pro`: typing estricto, calidad de código Python.

---

## Definition of Done

- Comandos funcionan vía Docker (`make help` + targets principales).
- Lint y typecheck pasan dentro de contenedor.
- Flujo de transcripción ejecuta sin depender de Python en host.
