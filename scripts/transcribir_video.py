#!/usr/bin/env python3
from __future__ import annotations

import sys
from scripts.transcripcion.app import run as _run

from scripts.transcripcion.cli import parsear_args
from scripts.transcripcion.env_config import (
    cargar_env_desde_archivo,
    cargar_env_robusto,
    detectar_variable_api_key_configurada,
    parsear_linea_env,
    resolver_archivos_env,
)
from scripts.transcripcion.errors import ErrorTranscripcion
from scripts.transcripcion.filesystem import (
    VIDEO_EXTS_PERMITIDAS,
    resolver_prefijo_salida,
    resolver_video_entrada,
    sanitizar_nombre,
    verificar_archivo,
)
from scripts.transcripcion.llm_postprocess import (
    aplicar_fallback_texto_vacio,
    construir_prompt_postproceso,
    extraer_json_de_respuesta_llm,
    imprimir_cambios_batch,
    llamar_api_llm,
    postprocesar_segmentos_con_llm,
    resolver_api_key_llm,
    resolver_endpoint_llm,
    truncar_texto_log,
    validar_respuesta_llm,
)
from scripts.transcripcion.logging_terminal import (
    BarraProgreso,
    TerminalColors,
    _bold,
    _colorize,
    _es_terminal_soportada,
    formatear_duracion,
    formatear_tamanio,
    log,
    log_bloque,
    log_key_value,
    log_separador,
    log_titulo,
)
from scripts.transcripcion.media_pipeline import (
    directorio_trabajo,
    dividir_audio,
    ejecutar_comando,
    extraer_audio_de_video,
    obtener_duracion_segundos,
    verificar_ffmpeg,
)
from scripts.transcripcion.models import Segmento
from scripts.transcripcion.outputs import (
    escribir_json,
    escribir_srt,
    escribir_txt,
    formatear_timestamp_srt,
)
from scripts.transcripcion.postprocess_input import (
    leer_registros_json,
    resolver_json_entrada_postprocess_only,
    segmentos_desde_registros_json,
)
from scripts.transcripcion.text_utils import normalizar_espacios
from scripts.transcripcion.whisper_pipeline import transcribir_chunk

__all__ = [
    "VIDEO_EXTS_PERMITIDAS",
    "BarraProgreso",
    "ErrorTranscripcion",
    "Segmento",
    "TerminalColors",
    "_bold",
    "_colorize",
    "_es_terminal_soportada",
    "aplicar_fallback_texto_vacio",
    "cargar_env_desde_archivo",
    "cargar_env_robusto",
    "construir_prompt_postproceso",
    "detectar_variable_api_key_configurada",
    "directorio_trabajo",
    "dividir_audio",
    "ejecutar_comando",
    "escribir_json",
    "escribir_srt",
    "escribir_txt",
    "extraer_audio_de_video",
    "extraer_json_de_respuesta_llm",
    "formatear_duracion",
    "formatear_tamanio",
    "formatear_timestamp_srt",
    "imprimir_cambios_batch",
    "leer_registros_json",
    "llamar_api_llm",
    "log",
    "log_bloque",
    "log_key_value",
    "log_separador",
    "log_titulo",
    "main",
    "normalizar_espacios",
    "obtener_duracion_segundos",
    "parsear_args",
    "parsear_linea_env",
    "postprocesar_segmentos_con_llm",
    "resolver_api_key_llm",
    "resolver_archivos_env",
    "resolver_endpoint_llm",
    "resolver_json_entrada_postprocess_only",
    "resolver_prefijo_salida",
    "resolver_video_entrada",
    "sanitizar_nombre",
    "segmentos_desde_registros_json",
    "transcribir_chunk",
    "truncar_texto_log",
    "validar_respuesta_llm",
    "verificar_archivo",
    "verificar_ffmpeg",
]


main = _run


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130)
    except ErrorTranscripcion as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
