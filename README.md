# Video Extractor

CLI en Python para transcribir videos con `ffmpeg` + `faster-whisper`, con salida en `TXT`, `SRT` y `JSON`.

> **Regla crítica:** este repositorio se trabaja en modo **Docker-only**. Para ejecutar el proyecto y sus validaciones, usá siempre los targets de [`Makefile`](Makefile).

---

## Tabla de contenidos

- [Descripción](#descripción)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Salida generada](#salida-generada)
- [Comandos oficiales](#comandos-oficiales)
- [Flujo recomendado de desarrollo](#flujo-recomendado-de-desarrollo)
- [Validación y calidad](#validación-y-calidad)
- [Solución de problemas](#solución-de-problemas)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## Descripción

El proyecto implementa el siguiente pipeline:

1. Resuelve el video de entrada (ruta explícita o autodetección en [`video_entrada/`](video_entrada)).
2. Extrae audio con `ffmpeg`.
3. Divide el audio en fragmentos.
4. Transcribe cada fragmento con `faster-whisper`.
5. (Opcional) Aplica postproceso con LLM sin modificar timestamps.
6. Exporta resultados en `TXT`, `SRT` y `JSON`.

Archivo principal: [`scripts/transcribir_video.py`](scripts/transcribir_video.py).

---

## Requisitos previos

| Requisito | Detalle |
| --- | --- |
| Docker | Instalado y con daemon activo |
| GNU Make | Disponible en el sistema |
| Video de entrada | Formatos: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm` |

### Restricciones operativas (Docker-only)

- No ejecutar el flujo de desarrollo con `python ...` en host.
- No instalar dependencias del proyecto con `pip` en host.
- Usar siempre [`Makefile`](Makefile) como entrypoint operativo.

---

## Instalación

### Opción recomendada

```bash
make install-dev
```

### Verificación básica

```bash
make help
```

---

## Configuración

1. Crear archivo local de entorno:

```bash
cp .env.example .env
```

2. Ajustar variables según necesidad:

| Variable | Descripción | Valor por defecto |
| --- | --- | --- |
| `WHISPER_MODEL` | Modelo de Whisper (`tiny`, `base`, `small`, `medium`, `large-v3`) | `small` |
| `LANGUAGE` | Idioma esperado (`es`, `en`) | `es` |
| `DEEPSEEK_MODEL` | Modelo para postproceso LLM | `deepseek-chat` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_APIKEY` | API key para postproceso LLM | vacío |
| `VIDEO` | Ruta de video para targets de `make` | vacío (autodetección) |

### Convenciones de rutas

- Entrada: [`video_entrada/`](video_entrada)
- Salida: [`salida/`](salida)
- Prefijo por defecto: `salida/transcripcion`

---

## Uso

### 1) Transcripción rápida (desarrollo)

```bash
make up
make dev VIDEO=./video_entrada/sample.mp4
```

Autodetección del primer video válido en [`video_entrada/`](video_entrada):

```bash
make up
make dev VIDEO=
```

### 2) Transcripción con modelo e idioma explícitos

```bash
make up
make transcribe VIDEO=./video_entrada/entrevista.mp4 WHISPER_MODEL=medium LANGUAGE=es
```

### 3) Postproceso LLM opcional

El postproceso LLM se aplica en una segunda pasada sobre texto/JSON. La transcripción base sigue siendo `faster-whisper`.

```bash
make up
make shell
python -m scripts.transcribir_video ./video_entrada/entrevista.mp4 \
  --postprocess-llm \
  --llm-provider deepseek \
  --llm-model deepseek-chat \
  --llm-batch-size 20 \
  --llm-timeout 60 \
  --llm-retries 2 \
  --keep-raw-json
```

Modo solo postproceso sobre JSON existente:

```bash
make up
make shell
python -m scripts.transcribir_video \
  --output-prefix salida/transcripcion \
  --postprocess-only \
  --postprocess-llm \
  --llm-provider deepseek \
  --llm-model deepseek-chat
```

---

## Salida generada

Con prefijo `salida/transcripcion`, se generan:

- [`salida/transcripcion.txt`](salida/transcripcion.txt): texto plano.
- [`salida/transcripcion.srt`](salida/transcripcion.srt): subtítulos.
- [`salida/transcripcion.json`](salida/transcripcion.json): segmentos estructurados.
- `salida/transcripcion.raw.json`: salida cruda opcional (con `--keep-raw-json`).

---

## Comandos oficiales

Todos definidos en [`Makefile`](Makefile):

| Comando | Propósito |
| --- | --- |
| `make help` | Muestra ayuda y variables |
| `make install-dev` | Setup inicial del entorno |
| `make up` | Construye la imagen Docker |
| `make rebuild` | Reconstruye sin caché |
| `make dev VIDEO=...` | Transcripción rápida |
| `make transcribe VIDEO=... WHISPER_MODEL=... LANGUAGE=...` | Transcripción configurable |
| `make format` | Formatea código con Ruff |
| `make lint` | Ejecuta lint con Ruff |
| `make typecheck` | Ejecuta typecheck con MyPy |
| `make check` | Lint + typecheck |
| `make unit-tests` | Ejecuta tests unitarios (`unittest`) |
| `make test` | `check` + `unit-tests` |
| `make shell` | Abre shell dentro del contenedor |
| `make status` | Lista contenedores de la imagen del proyecto |
| `make logs` | Sigue logs del contenedor nombrado |
| `make clean` | Limpia recursos Docker no usados |
| `make down` | Elimina la imagen del proyecto |

---

## Flujo recomendado de desarrollo

```bash
make up
make dev VIDEO=./video_entrada/sample.mp4
make check
```

Si necesitás validación automatizada adicional:

```bash
make up
make unit-tests
```

---

## Validación y calidad

### Validación manual mínima (MVP)

```bash
make up
make check
make dev VIDEO=./video_entrada/sample.mp4
```

### Validación automatizada disponible

- Test unitario principal: [`tests/test_resolver_video_entrada.py`](tests/test_resolver_video_entrada.py)
- Ejecución:

```bash
make up
make unit-tests
```

---

## Solución de problemas

### No existe `video_entrada/`

```bash
mkdir -p video_entrada
```

### No se detecta ningún video

- Verificá formato soportado.
- Pasá ruta explícita con `VIDEO=...`.

### Falla Docker o no existe la imagen

```bash
make up
make dev VIDEO=./video_entrada/sample.mp4
```

### El postproceso LLM no se activa

- Revisá `DEEPSEEK_API_KEY`/`DEEPSEEK_APIKEY` en `.env`.
- Verificá flags `--postprocess-llm` y `--llm-*`.

---

## Contribución

1. Crear rama (`feature/...` o `fix/...`).
2. Implementar cambios pequeños y acotados.
3. Ejecutar validaciones:

```bash
make up
make check
make test
```

4. Actualizar documentación impactada (incluido [`README.md`](README.md)).
5. Abrir Pull Request con contexto, alcance y evidencia de validación.

---

## Licencia

Distribuido bajo licencia MIT. Ver [`LICENSE`](LICENSE).
