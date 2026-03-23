#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


VIDEO_EXTS_PERMITIDAS = (".mp4", ".mkv", ".mov", ".avi", ".webm")


@dataclass
class Segmento:
    start: float
    end: float
    text: str


class ErrorTranscripcion(Exception):
    """Error controlado del flujo de transcripcion."""


def log(mensaje: str) -> None:
    print(mensaje, flush=True)


def normalizar_espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def ejecutar_comando(comando: list[str], descripcion: str) -> None:
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
    if shutil.which("ffmpeg") is None:
        raise ErrorTranscripcion("No se encontro ffmpeg en PATH.")
    if shutil.which("ffprobe") is None:
        raise ErrorTranscripcion(
            "No se encontro ffprobe en PATH (se usa para duraciones de chunks)."
        )


def verificar_archivo(path: Path) -> None:
    if not path.exists():
        raise ErrorTranscripcion(f"El archivo no existe: {path}")
    if not path.is_file():
        raise ErrorTranscripcion(f"La ruta no es un archivo valido: {path}")


def resolver_prefijo_salida(valor: str) -> Path:
    bruto = valor.strip()
    if not bruto:
        raise ErrorTranscripcion("El valor de --output-prefix no puede estar vacio.")

    candidato = Path(bruto)
    termina_en_sep = bruto.endswith(("/", "\\"))

    if (candidato.exists() and candidato.is_dir()) or termina_en_sep:
        candidato.mkdir(parents=True, exist_ok=True)
        return candidato / "transcripcion"

    candidato.parent.mkdir(parents=True, exist_ok=True)
    return candidato


def sanitizar_nombre(nombre: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre).strip("._")
    return limpio or "video"


def resolver_video_entrada(video_arg: Path | None, raiz: Path) -> Path:
    if video_arg is not None:
        return video_arg

    candidatos = sorted(
        [
            p
            for p in raiz.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTS_PERMITIDAS
        ],
        key=lambda p: p.name.lower(),
    )

    if not candidatos:
        formatos = ", ".join(VIDEO_EXTS_PERMITIDAS)
        raise ErrorTranscripcion(
            "No se encontró un video en la raíz del proyecto para transcribir. "
            f"Formatos buscados: {formatos}. "
            "Indicá el archivo manualmente, por ejemplo: "
            "python transcribir_video.py ./mi_video.mp4"
        )

    elegido = candidatos[0]
    if len(candidatos) == 1:
        log(f"Video detectado automáticamente: {elegido.name}")
    else:
        lista = ", ".join(p.name for p in candidatos)
        log(
            "Se detectaron múltiples videos en la raíz "
            f"({lista}). Se usará {elegido.name} por orden alfabético."
        )
    return elegido


@contextmanager
def directorio_trabajo(keep_temp: bool) -> Iterator[Path]:
    if keep_temp:
        ruta = Path(tempfile.mkdtemp(prefix="transcribir_video_"))
        try:
            yield ruta
        finally:
            pass
    else:
        with tempfile.TemporaryDirectory(prefix="transcribir_video_") as td:
            yield Path(td)


def extraer_audio_de_video(
    video_path: Path,
    audio_path: Path,
    audio_bitrate: str,
    audio_sample_rate: int,
) -> Path:
    # M4A (AAC) ofrece buena compatibilidad y un tamanio estable para videos largos.
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

    # Se recalculan offsets con duracion real de cada chunk para timestamps globales precisos.
    offsets: list[tuple[Path, float]] = []
    acumulado = 0.0
    for chunk in sorted(chunks):
        offsets.append((chunk, acumulado))
        acumulado += obtener_duracion_segundos(chunk)

    return offsets


def formatear_timestamp_srt(segundos: float) -> str:
    total_ms = int(round(max(0.0, segundos) * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos_int, milisegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_int:02d},{milisegundos:03d}"


def transcribir_chunk(
    model: Any,
    chunk_path: Path,
    offset_segundos: float,
    language: str,
    beam_size: int,
    word_timestamps: bool,
) -> tuple[list[Segmento], list[dict[str, Any]]]:
    kwargs: dict[str, Any] = {
        "vad_filter": True,
        "beam_size": beam_size,
        "word_timestamps": word_timestamps,
    }
    if language.lower() != "auto":
        kwargs["language"] = language

    segmentos_fw, _info = model.transcribe(str(chunk_path), **kwargs)

    segmentos: list[Segmento] = []
    registros_json: list[dict[str, Any]] = []

    for segmento in segmentos_fw:
        texto = normalizar_espacios(getattr(segmento, "text", ""))
        if not texto:
            continue

        inicio = offset_segundos + float(getattr(segmento, "start", 0.0))
        fin = offset_segundos + float(getattr(segmento, "end", 0.0))
        if fin <= inicio:
            continue

        item = Segmento(start=inicio, end=fin, text=texto)
        segmentos.append(item)

        registro: dict[str, Any] = {
            "start": round(item.start, 3),
            "end": round(item.end, 3),
            "text": item.text,
        }

        if word_timestamps:
            palabras_json: list[dict[str, Any]] = []
            for palabra in getattr(segmento, "words", None) or []:
                palabra_txt = normalizar_espacios(getattr(palabra, "word", ""))
                if not palabra_txt:
                    continue
                w_start = offset_segundos + float(getattr(palabra, "start", 0.0))
                w_end = offset_segundos + float(getattr(palabra, "end", 0.0))
                if w_end <= w_start:
                    continue
                palabras_json.append(
                    {
                        "start": round(w_start, 3),
                        "end": round(w_end, 3),
                        "word": palabra_txt,
                    }
                )
            if palabras_json:
                registro["words"] = palabras_json

        registros_json.append(registro)

    return segmentos, registros_json


def escribir_txt(path: Path, segmentos: list[Segmento]) -> None:
    contenido = "\n".join(s.text for s in segmentos).strip()
    path.write_text(contenido + "\n", encoding="utf-8")


def escribir_srt(path: Path, segmentos: list[Segmento]) -> None:
    lineas: list[str] = []
    for i, seg in enumerate(segmentos, start=1):
        inicio = formatear_timestamp_srt(seg.start)
        fin = formatear_timestamp_srt(seg.end)
        lineas.append(str(i))
        lineas.append(f"{inicio} --> {fin}")
        lineas.append(seg.text)
        lineas.append("")
    path.write_text("\n".join(lineas), encoding="utf-8")


def escribir_json(path: Path, datos: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe un video completo con ffmpeg + faster-whisper."
    )
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        default=None,
        help=(
            "Ruta al archivo de video. Si se omite, se busca automáticamente en "
            "la raíz del proyecto (mp4/mkv/mov/avi/webm)."
        ),
    )
    parser.add_argument(
        "--model", default="small", help="Modelo de faster-whisper (default: small)."
    )
    parser.add_argument(
        "--language",
        default="es",
        help="Idioma (ej: es, en) o 'auto' para deteccion automatica (default: es).",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Dispositivo de inferencia.",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="Tipo de computo de faster-whisper (default: int8).",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=600,
        help="Duracion de cada chunk en segundos (default: 600).",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size para transcripcion (default: 5).",
    )
    parser.add_argument(
        "--output-prefix",
        default="transcripcion",
        help="Prefijo de salida o carpeta (default: transcripcion).",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Conservar archivos temporales (audio y chunks).",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="Bitrate de audio temporal extraido (default: 128k).",
    )
    parser.add_argument(
        "--audio-sample-rate",
        type=int,
        default=16000,
        help="Sample rate del audio temporal para ASR (default: 16000).",
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Incluir timestamps por palabra en el JSON.",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Procesar solo los primeros N chunks (util para pruebas).",
    )
    return parser.parse_args()


def main() -> int:
    args = parsear_args()

    if args.chunk_seconds <= 0:
        raise ErrorTranscripcion("--chunk-seconds debe ser mayor a 0.")
    if args.beam_size <= 0:
        raise ErrorTranscripcion("--beam-size debe ser mayor a 0.")
    if args.audio_sample_rate <= 0:
        raise ErrorTranscripcion("--audio-sample-rate debe ser mayor a 0.")
    if args.max_chunks is not None and args.max_chunks <= 0:
        raise ErrorTranscripcion("--max-chunks debe ser mayor a 0 cuando se usa.")

    video_path = resolver_video_entrada(args.video, Path.cwd())

    verificar_ffmpeg()
    verificar_archivo(video_path)

    prefijo = resolver_prefijo_salida(args.output_prefix)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ErrorTranscripcion(
            "No se pudo importar faster_whisper. Instala con: pip install faster-whisper"
        ) from exc

    nombre_base = sanitizar_nombre(video_path.stem)

    with directorio_trabajo(args.keep_temp) as workdir:
        if args.keep_temp:
            log(f"Temporales en: {workdir}")

        audio_path = workdir / f"{nombre_base}_audio.m4a"
        chunks_dir = workdir / f"{nombre_base}_chunks"

        log("Extrayendo audio del video...")
        extraer_audio_de_video(
            video_path=video_path,
            audio_path=audio_path,
            audio_bitrate=args.audio_bitrate,
            audio_sample_rate=args.audio_sample_rate,
        )

        log("Dividiendo audio en chunks...")
        chunks_con_offset = dividir_audio(
            audio_path=audio_path,
            chunks_dir=chunks_dir,
            chunk_seconds=args.chunk_seconds,
        )

        if args.max_chunks is not None:
            chunks_con_offset = chunks_con_offset[: args.max_chunks]

        if not chunks_con_offset:
            raise ErrorTranscripcion(
                "No hay chunks para transcribir luego de aplicar filtros."
            )

        log(f"Chunks generados: {len(chunks_con_offset)}")
        log("Cargando modelo...")
        model = WhisperModel(
            args.model,
            device=args.device,
            compute_type=args.compute_type,
        )

        segmentos_totales: list[Segmento] = []
        json_segmentos: list[dict[str, Any]] = []

        for i, (chunk_path, offset) in enumerate(chunks_con_offset, start=1):
            log(f"Transcribiendo {chunk_path.name} ({i}/{len(chunks_con_offset)})...")
            segmentos_chunk, json_chunk = transcribir_chunk(
                model=model,
                chunk_path=chunk_path,
                offset_segundos=offset,
                language=args.language,
                beam_size=args.beam_size,
                word_timestamps=args.word_timestamps,
            )
            segmentos_totales.extend(segmentos_chunk)
            json_segmentos.extend(json_chunk)

    if not segmentos_totales:
        raise ErrorTranscripcion(
            "No se obtuvo texto transcripto. Proba con otro --model o --language auto."
        )

    txt_path = prefijo.with_suffix(".txt")
    srt_path = prefijo.with_suffix(".srt")
    json_path = prefijo.with_suffix(".json")

    log("Escribiendo salidas...")
    escribir_txt(txt_path, segmentos_totales)
    escribir_srt(srt_path, segmentos_totales)
    escribir_json(json_path, json_segmentos)

    log("Listo.")
    log(f"TXT:  {txt_path}")
    log(f"SRT:  {srt_path}")
    log(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130)
    except ErrorTranscripcion as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
