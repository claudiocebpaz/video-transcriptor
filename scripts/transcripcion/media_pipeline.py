from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import ErrorTranscripcion


def ejecutar_comando(comando: list[str], descripcion: str) -> None:
    """Ejecuta comando externo y normaliza errores de proceso."""
    try:
        subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detalle = (exc.stderr or exc.stdout or "").strip()
        if not detalle:
            detalle = str(exc)
        raise ErrorTranscripcion(f"{descripcion} fallo:\n{detalle}") from exc


def verificar_ffmpeg() -> None:
    """Verifica disponibilidad de ffmpeg y ffprobe en PATH."""
    if shutil.which("ffmpeg") is None:
        raise ErrorTranscripcion("No se encontro ffmpeg en PATH.")
    if shutil.which("ffprobe") is None:
        raise ErrorTranscripcion(
            "No se encontro ffprobe en PATH (se usa para duraciones de chunks)."
        )


@contextmanager
def directorio_trabajo(keep_temp: bool) -> Iterator[Path]:
    """Provee directorio temporal persistente o efímero según configuración."""
    if keep_temp:
        ruta = Path(tempfile.mkdtemp(prefix="transcribir_video_"))
        yield ruta
    else:
        with tempfile.TemporaryDirectory(prefix="transcribir_video_") as td:
            yield Path(td)


def extraer_audio_de_video(
    video_path: Path,
    audio_path: Path,
    audio_bitrate: str,
    audio_sample_rate: int,
) -> Path:
    """Extrae audio mono AAC desde video usando ffmpeg."""
    comando = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(audio_sample_rate),
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        str(audio_path),
    ]
    ejecutar_comando(comando, "Extraccion de audio con ffmpeg")
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise ErrorTranscripcion("La extraccion de audio no genero un archivo valido.")
    return audio_path


def obtener_duracion_segundos(media_path: Path) -> float:
    """Obtiene duración en segundos usando ffprobe."""
    comando = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    try:
        resultado = subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detalle = (exc.stderr or exc.stdout or "").strip()
        raise ErrorTranscripcion(
            f"No se pudo obtener la duracion de {media_path}.\n{detalle}"
        ) from exc

    salida = (resultado.stdout or "").strip()
    try:
        duracion = float(salida)
    except ValueError as exc:
        raise ErrorTranscripcion(
            f"Duracion invalida reportada por ffprobe para {media_path}: {salida!r}"
        ) from exc

    if duracion <= 0:
        raise ErrorTranscripcion(f"Duracion no valida para {media_path}: {duracion}")
    return duracion


def dividir_audio(
    audio_path: Path,
    chunks_dir: Path,
    chunk_seconds: int,
) -> list[tuple[Path, float]]:
    """Divide audio en chunks y retorna rutas con offset absoluto."""
    if chunk_seconds <= 0:
        raise ErrorTranscripcion("--chunk-seconds debe ser mayor a 0.")

    chunks_dir.mkdir(parents=True, exist_ok=True)
    duracion_total = obtener_duracion_segundos(audio_path)

    chunks: list[Path] = []
    inicio = 0.0
    indice = 1

    while inicio < duracion_total:
        duracion_chunk = min(float(chunk_seconds), duracion_total - inicio)
        if duracion_chunk <= 0:
            break

        chunk_path = chunks_dir / f"chunk_{indice:04d}.m4a"
        comando = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{inicio:.3f}",
            "-i",
            str(audio_path),
            "-t",
            f"{duracion_chunk:.3f}",
            "-c",
            "copy",
            str(chunk_path),
        ]
        ejecutar_comando(comando, f"Generacion de chunk {chunk_path.name}")

        if chunk_path.exists() and chunk_path.stat().st_size > 0:
            chunks.append(chunk_path)

        inicio += duracion_chunk
        indice += 1

    if not chunks:
        raise ErrorTranscripcion("No se generaron chunks de audio.")

    offsets: list[tuple[Path, float]] = []
    acumulado = 0.0
    for chunk in sorted(chunks):
        offsets.append((chunk, acumulado))
        acumulado += obtener_duracion_segundos(chunk)

    return offsets

