from __future__ import annotations

import argparse
from pathlib import Path

from .errors import ErrorTranscripcion


def parsear_args() -> argparse.Namespace:
    """Define y parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Transcribe un video con ffmpeg + faster-whisper y postproceso LLM opcional."
    )
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        default=None,
        help=(
            "Ruta al archivo de video. Si se omite, se busca automáticamente en "
            "./video_entrada (mp4/mkv/mov/avi/webm)."
        ),
    )
    parser.add_argument(
        "--model", default="small", help="Modelo de faster-whisper (default: small)."
    )
    parser.add_argument(
        "--language",
        default="es",
        help="Idioma (ej: es, en) o 'auto' para detección automática (default: es).",
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
        help="Tipo de cómputo de faster-whisper (default: int8).",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=600,
        help="Duración de cada chunk en segundos (default: 600).",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size para transcripción (default: 5).",
    )
    parser.add_argument(
        "--output-prefix",
        default="salida/transcripcion",
        help="Prefijo de salida o carpeta (default: salida/transcripcion).",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Conservar archivos temporales (audio y chunks).",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="Bitrate de audio temporal extraído (default: 128k).",
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
        help="Procesar solo los primeros N chunks (útil para pruebas).",
    )

    parser.add_argument(
        "--postprocess-llm",
        action="store_true",
        help="Activar segunda pasada opcional de postprocesamiento con LLM.",
    )
    parser.add_argument(
        "--llm-provider",
        default="deepseek",
        help="Proveedor LLM (default: deepseek).",
    )
    parser.add_argument(
        "--llm-model",
        default="deepseek-chat",
        help="Modelo LLM para postproceso (default: deepseek-chat).",
    )
    parser.add_argument(
        "--llm-api-key",
        default=None,
        help="API key del proveedor LLM. Si se omite, se lee de variable de entorno.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=None,
        help="Base URL opcional para endpoints estilo OpenAI.",
    )
    parser.add_argument(
        "--llm-batch-size",
        type=int,
        default=20,
        help="Cantidad de segmentos enviados por request al LLM (default: 20).",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=60.0,
        help="Timeout de cada request LLM en segundos (default: 60).",
    )
    parser.add_argument(
        "--llm-retries",
        type=int,
        default=2,
        help="Reintentos por batch LLM ante error (default: 2).",
    )
    parser.add_argument(
        "--keep-raw-json",
        action="store_true",
        help="Guardar también el JSON bruto previo al postproceso como *.raw.json.",
    )
    parser.add_argument(
        "--postprocess-only",
        action="store_true",
        help="Ejecutar solo postproceso LLM usando JSON existente, sin transcribir audio.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Desactivar postprocesamiento con LLM aunque haya configuración disponible.",
    )

    return parser.parse_args()


def validar_args(args: argparse.Namespace) -> None:
    """Valida constraints numéricos de argumentos."""
    if args.chunk_seconds <= 0:
        raise ErrorTranscripcion("--chunk-seconds debe ser mayor a 0.")
    if args.beam_size <= 0:
        raise ErrorTranscripcion("--beam-size debe ser mayor a 0.")
    if args.audio_sample_rate <= 0:
        raise ErrorTranscripcion("--audio-sample-rate debe ser mayor a 0.")
    if args.max_chunks is not None and args.max_chunks <= 0:
        raise ErrorTranscripcion("--max-chunks debe ser mayor a 0 cuando se usa.")
    if args.llm_batch_size <= 0:
        raise ErrorTranscripcion("--llm-batch-size debe ser mayor a 0.")
    if args.llm_timeout <= 0:
        raise ErrorTranscripcion("--llm-timeout debe ser mayor a 0.")
    if args.llm_retries < 0:
        raise ErrorTranscripcion("--llm-retries no puede ser negativo.")

