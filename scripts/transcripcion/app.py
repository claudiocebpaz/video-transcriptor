from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import parsear_args, validar_args
from .env_config import cargar_env_robusto, detectar_variable_api_key_configurada
from .errors import ErrorTranscripcion
from .filesystem import (
    resolver_prefijo_salida,
    resolver_video_entrada,
    sanitizar_nombre,
    verificar_archivo,
)
from .llm_postprocess import postprocesar_segmentos_con_llm, resolver_api_key_llm
from .logging_terminal import TerminalColors, log, log_key_value, log_separador, log_titulo
from .media_pipeline import (
    directorio_trabajo,
    dividir_audio,
    extraer_audio_de_video,
    verificar_ffmpeg,
)
from .models import Segmento
from .outputs import escribir_json, escribir_srt, escribir_txt
from .postprocess_input import (
    leer_registros_json,
    resolver_json_entrada_postprocess_only,
    segmentos_desde_registros_json,
)
from .whisper_pipeline import transcribir_chunk


def run() -> int:
    """Ejecuta flujo completo de transcripción y exportación."""
    cargar_env_robusto()
    args = parsear_args()
    validar_args(args)

    if args.postprocess_only:
        args.postprocess_llm = True
    else:
        if not args.no_llm:
            api_key_disponible = detectar_variable_api_key_configurada(args.llm_provider)
            if api_key_disponible:
                args.postprocess_llm = True
                log(
                    f"Auto-detección LLM | se activa postproceso porque hay configuración en {api_key_disponible}",
                    nivel="success",
                )

    if args.postprocess_llm:
        variable_detectada = detectar_variable_api_key_configurada(args.llm_provider)
        origen_api_key = (
            "argumento --llm-api-key" if args.llm_api_key else "variables de entorno"
        )
        log(
            f"Modo LLM: ACTIVADO | provider={args.llm_provider} model={args.llm_model} "
            f"postprocess_only={args.postprocess_only} api_key={origen_api_key}",
            nivel="success",
        )
        if not args.llm_api_key:
            log(
                f"Detección API key por entorno | variable={variable_detectada or 'NO_ENCONTRADA'}",
                nivel="info",
            )
    else:
        variable_detectada = detectar_variable_api_key_configurada(args.llm_provider)
        if variable_detectada:
            log(
                f"Modo LLM: DESACTIVADO | se detectó configuración de DeepSeek "
                f"en {variable_detectada}, pero falta activar --postprocess-llm",
                nivel="warning",
            )
        else:
            log(
                "Modo LLM: DESACTIVADO | se usará solo transcripción ASR con faster-whisper",
                nivel="info",
            )

    prefijo = resolver_prefijo_salida(args.output_prefix)

    segmentos_totales: list[Segmento]
    json_segmentos: list[dict[str, Any]]

    if args.postprocess_only:
        entrada_json = resolver_json_entrada_postprocess_only(prefijo)
        log(f"Cargando segmentos desde JSON existente: {entrada_json}", nivel="info")
        json_segmentos = leer_registros_json(entrada_json)
        segmentos_totales = segmentos_desde_registros_json(json_segmentos)
    else:
        video_path = resolver_video_entrada(args.video, Path.cwd())

        verificar_ffmpeg()
        verificar_archivo(video_path)

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ErrorTranscripcion(
                "No se pudo importar faster_whisper. Instala con: pip install faster-whisper"
            ) from exc

        nombre_base = sanitizar_nombre(video_path.stem)

        with directorio_trabajo(args.keep_temp) as workdir:
            if args.keep_temp:
                log(f"Temporales en: {workdir}", nivel="info")

            audio_path = workdir / f"{nombre_base}_audio.m4a"
            chunks_dir = workdir / f"{nombre_base}_chunks"

            log("Extrayendo audio del video...", nivel="progress")
            extraer_audio_de_video(
                video_path=video_path,
                audio_path=audio_path,
                audio_bitrate=args.audio_bitrate,
                audio_sample_rate=args.audio_sample_rate,
            )

            log("Dividiendo audio en chunks...", nivel="progress")
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

            log(f"Chunks generados: {len(chunks_con_offset)}", nivel="success")
            log("Cargando modelo Whisper...", nivel="progress")
            model = WhisperModel(
                args.model,
                device=args.device,
                compute_type=args.compute_type,
            )

            segmentos_totales = []
            json_segmentos = []

            log_titulo("Transcripción de Chunks")
            log(f"Procesando {len(chunks_con_offset)} chunks con modelo {args.model}...")
            log_separador()

            for i, (chunk_path, offset) in enumerate(chunks_con_offset, start=1):
                log(
                    f"[{i}/{len(chunks_con_offset)}] Transcribiendo {chunk_path.name}...",
                    nivel="progress",
                )
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
    raw_json_path = prefijo.with_suffix(".raw.json")

    if args.postprocess_llm:
        if args.keep_raw_json:
            log("Guardando JSON bruto previo al postproceso...", nivel="info")
            escribir_json(raw_json_path, json_segmentos)

        api_key = resolver_api_key_llm(args.llm_api_key, args.llm_provider)

        log("Iniciando postproceso LLM opcional...", nivel="progress")
        segmentos_totales, json_segmentos = postprocesar_segmentos_con_llm(
            segmentos=segmentos_totales,
            registros_json=json_segmentos,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            llm_api_key=api_key,
            llm_base_url=args.llm_base_url,
            llm_batch_size=args.llm_batch_size,
            llm_timeout=args.llm_timeout,
            llm_retries=args.llm_retries,
        )

    log("Escribiendo salidas...", nivel="info")
    escribir_txt(txt_path, segmentos_totales)
    escribir_srt(srt_path, segmentos_totales)
    escribir_json(json_path, json_segmentos)

    log_titulo("Transcripción Completada")
    log_key_value("TXT", str(txt_path), TerminalColors.GREEN)
    log_key_value("SRT", str(srt_path), TerminalColors.GREEN)
    log_key_value("JSON", str(json_path), TerminalColors.GREEN)
    log_key_value("Segmentos", str(len(segmentos_totales)), TerminalColors.CYAN)
    if args.postprocess_llm and args.keep_raw_json:
        log_key_value("RAW", str(raw_json_path), TerminalColors.YELLOW)
    log_separador()
    log("¡Listo! La transcripción ha finalizado correctamente.", nivel="success")

    return 0

