from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error, request

from .errors import ErrorTranscripcion
from .logging_terminal import TerminalColors, _colorize, log, log_separador
from .models import Segmento
from .text_utils import normalizar_espacios


def construir_prompt_postproceso(segmentos_batch: list[dict[str, Any]]) -> str:
    """Construye prompt estricto de postproceso LLM."""
    reglas = (
        "Debes devolver exclusivamente JSON valido. "
        "No uses markdown, no uses code fences y no agregues explicaciones. "
        "Recibiras una lista de segmentos con id, start, end y text. "
        "Debes devolver exactamente la misma cantidad de segmentos, en el mismo orden. "
        "No puedes cambiar id, start ni end. "
        "Solo puedes mejorar text. "
        "Conserva el idioma original. "
        "No traduzcas, no resumas, no inventes informacion. "
        "No agregues ni elimines segmentos. "
        "Puedes corregir ortografia, puntuacion, capitalizacion y espacios. "
        "Puedes quitar muletillas obvias solo si no alteran el sentido. "
        "Si un text mejorado quedara vacio, devuelve el text original."
    )
    payload = json.dumps(segmentos_batch, ensure_ascii=False)
    return f"{reglas}\n\nSegmentos:\n{payload}"


def resolver_api_key_llm(llm_api_key: str | None, llm_provider: str) -> str:
    """Resuelve API key desde argumento o entorno."""
    if llm_api_key:
        return llm_api_key

    provider = llm_provider.lower()
    if provider == "deepseek":
        for variable in ("DEEPSEEK_API_KEY", "DEEPSEEK_APIKEY", "OPENAI_API_KEY"):
            valor = os.environ.get(variable, "").strip()
            if valor:
                return valor
        raise ErrorTranscripcion(
            "No se encontró API key para DeepSeek. Usa --llm-api-key o DEEPSEEK_API_KEY."
        )

    raise ErrorTranscripcion(f"Provider LLM no soportado: {llm_provider}")


def resolver_endpoint_llm(llm_provider: str, llm_base_url: str | None) -> str:
    """Resuelve endpoint Chat Completions compatible con proveedor."""
    provider = llm_provider.lower()
    if provider != "deepseek":
        raise ErrorTranscripcion(f"Provider LLM no soportado: {llm_provider}")

    base_url = (llm_base_url or "https://api.deepseek.com/v1").strip().rstrip("/")
    if not base_url:
        raise ErrorTranscripcion("--llm-base-url no puede ser vacio cuando se usa LLM.")

    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def extraer_json_de_respuesta_llm(respuesta: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae y valida lista JSON de la respuesta del LLM."""
    choices = respuesta.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ErrorTranscripcion("La respuesta del LLM no contiene choices válidos.")

    primer_choice = choices[0]
    if not isinstance(primer_choice, dict):
        raise ErrorTranscripcion("La estructura de choices del LLM es inválida.")

    message = primer_choice.get("message")
    if not isinstance(message, dict):
        raise ErrorTranscripcion("La respuesta del LLM no incluye message válido.")

    contenido = message.get("content")
    if not isinstance(contenido, str):
        raise ErrorTranscripcion("El content del LLM no es texto válido.")

    texto = contenido.strip()
    if not texto:
        raise ErrorTranscripcion("El LLM devolvió un content vacío.")

    try:
        parseado = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ErrorTranscripcion(
            "La respuesta del LLM no es JSON válido en message.content."
        ) from exc

    if not isinstance(parseado, list):
        raise ErrorTranscripcion("El JSON del LLM debe ser una lista de segmentos.")

    salida: list[dict[str, Any]] = []
    for item in parseado:
        if not isinstance(item, dict):
            raise ErrorTranscripcion("Cada elemento devuelto por el LLM debe ser un objeto.")
        salida.append(item)
    return salida


def llamar_api_llm(
    endpoint: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout_segundos: float,
) -> list[dict[str, Any]]:
    """Llama a API de LLM y devuelve lista de segmentos JSON."""
    cuerpo = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un postprocesador estricto de transcripciones. "
                    "Siempre devuelves JSON valido y nada mas."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    data = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with request.urlopen(req, timeout=timeout_segundos) as respuesta:
            cuerpo_respuesta = respuesta.read().decode("utf-8")
    except error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise ErrorTranscripcion(f"HTTP {exc.code} al llamar LLM: {detalle}") from exc
    except error.URLError as exc:
        raise ErrorTranscripcion(f"Error de red al llamar LLM: {exc.reason}") from exc

    try:
        respuesta_json = json.loads(cuerpo_respuesta)
    except json.JSONDecodeError as exc:
        raise ErrorTranscripcion("La API LLM devolvió un JSON inválido.") from exc

    return extraer_json_de_respuesta_llm(respuesta_json)


def validar_respuesta_llm(
    originales: list[dict[str, Any]],
    respuesta_llm: list[dict[str, Any]],
) -> list[str]:
    """Valida inmutabilidad de estructura y retorna textos mejorados."""
    if len(originales) != len(respuesta_llm):
        raise ErrorTranscripcion(
            "Respuesta del LLM inválida: cambió la cantidad de segmentos."
        )

    textos_mejorados: list[str] = []

    for indice, (orig, nuevo) in enumerate(zip(originales, respuesta_llm), start=1):
        for clave in ("id", "start", "end", "text"):
            if clave not in nuevo:
                raise ErrorTranscripcion(
                    f"Respuesta del LLM inválida en item {indice}: falta '{clave}'."
                )

        if nuevo["id"] != orig["id"]:
            raise ErrorTranscripcion(
                f"Respuesta del LLM inválida en item {indice}: id modificado."
            )

        try:
            nuevo_start = float(nuevo["start"])
            nuevo_end = float(nuevo["end"])
        except (TypeError, ValueError) as exc:
            raise ErrorTranscripcion(
                f"Respuesta del LLM inválida en item {indice}: start/end no numéricos."
            ) from exc

        if abs(nuevo_start - float(orig["start"])) > 1e-6:
            raise ErrorTranscripcion(
                f"Respuesta del LLM inválida en item {indice}: start modificado."
            )
        if abs(nuevo_end - float(orig["end"])) > 1e-6:
            raise ErrorTranscripcion(
                f"Respuesta del LLM inválida en item {indice}: end modificado."
            )

        if not isinstance(nuevo["text"], str):
            raise ErrorTranscripcion(
                f"Respuesta del LLM inválida en item {indice}: text no es string."
            )

        textos_mejorados.append(normalizar_espacios(nuevo["text"]))

    return textos_mejorados


def aplicar_fallback_texto_vacio(texto_original: str, texto_mejorado: str) -> str:
    """Evita que un segmento quede vacío tras postproceso."""
    limpio = normalizar_espacios(texto_mejorado)
    if limpio:
        return limpio
    return texto_original


def truncar_texto_log(texto: str, limite: int = 140) -> str:
    """Trunca texto para logs manteniendo formato compacto."""
    compacto = normalizar_espacios(texto)
    if len(compacto) <= limite:
        return compacto
    return f"{compacto[: limite - 1]}…"


def imprimir_cambios_batch(
    batch_llm: list[dict[str, Any]],
    textos_mejorados: list[str],
) -> tuple[int, int]:
    """Imprime diff resumido por segmento de un batch."""
    cambios = 0
    sin_cambios = 0

    log("Cambios detectados por segmento en el batch:", nivel="info")
    for original, mejorado in zip(batch_llm, textos_mejorados):
        texto_original = str(original["text"])
        texto_mejorado = str(mejorado)
        segmento_id = int(original["id"])
        start = float(original["start"])
        end = float(original["end"])

        if texto_original == texto_mejorado:
            sin_cambios += 1
            log(
                f"  {_colorize('•', TerminalColors.CYAN)} {_colorize(f'seg#{segmento_id}', TerminalColors.DIM)} "
                f"[{start:.3f}-{end:.3f}] {_colorize('sin cambios', TerminalColors.DIM)} | "
                f"{truncar_texto_log(texto_original)}",
                nivel="info",
            )
            continue

        cambios += 1
        log(
            f"  {_colorize('•', TerminalColors.YELLOW)} {_colorize(f'seg#{segmento_id}', TerminalColors.YELLOW)} "
            f"[{start:.3f}-{end:.3f}]",
            nivel="warning",
        )
        log(f"      {_colorize('-', TerminalColors.ERROR)} {truncar_texto_log(texto_original)}")
        log(f"      {_colorize('+', TerminalColors.SUCCESS)} {truncar_texto_log(texto_mejorado)}")

    return cambios, sin_cambios


def postprocesar_segmentos_con_llm(
    segmentos: list[Segmento],
    registros_json: list[dict[str, Any]],
    llm_provider: str,
    llm_model: str,
    llm_api_key: str,
    llm_base_url: str | None,
    llm_batch_size: int,
    llm_timeout: float,
    llm_retries: int,
) -> tuple[list[Segmento], list[dict[str, Any]]]:
    """Ejecuta postproceso por batches con validación estricta y fallback."""
    if len(segmentos) != len(registros_json):
        raise ErrorTranscripcion(
            "Inconsistencia interna: cantidad de segmentos y JSON no coincide."
        )

    endpoint = resolver_endpoint_llm(llm_provider=llm_provider, llm_base_url=llm_base_url)

    segmentos_resultado = [Segmento(start=s.start, end=s.end, text=s.text) for s in segmentos]
    json_resultado = [dict(item) for item in registros_json]

    total = len(segmentos)
    total_batches = (total + llm_batch_size - 1) // llm_batch_size
    total_segmentos_cambiados = 0
    total_segmentos_sin_cambios = 0
    total_batches_ok = 0
    total_batches_fallback = 0
    total_reintentos = 0

    for batch_idx, inicio in enumerate(range(0, total, llm_batch_size), start=1):
        fin = min(inicio + llm_batch_size, total)
        log(f"Postprocesando batch {batch_idx}/{total_batches}...", nivel="progress")

        batch_llm: list[dict[str, Any]] = []
        for i in range(inicio, fin):
            batch_llm.append(
                {
                    "id": i,
                    "start": round(segmentos[i].start, 3),
                    "end": round(segmentos[i].end, 3),
                    "text": segmentos[i].text,
                }
            )

        prompt = construir_prompt_postproceso(batch_llm)

        respuesta_validada: list[str] | None = None
        for intento in range(1, llm_retries + 2):
            inicio_llamada = time.perf_counter()
            log(
                f"[LLM] Iniciando request | provider={llm_provider} model={llm_model} "
                f"batch={batch_idx}/{total_batches} intento={intento}/{llm_retries + 1}",
                nivel="info",
            )
            try:
                respuesta_cruda = llamar_api_llm(
                    endpoint=endpoint,
                    api_key=llm_api_key,
                    model=llm_model,
                    prompt=prompt,
                    timeout_segundos=llm_timeout,
                )
                log("Validando respuesta del LLM...", nivel="info")
                respuesta_validada = validar_respuesta_llm(
                    originales=batch_llm,
                    respuesta_llm=respuesta_cruda,
                )
                duracion = time.perf_counter() - inicio_llamada
                log(
                    f"[LLM] Request completada | batch={batch_idx}/{total_batches} "
                    f"intento={intento} | duración={duracion:.2f}s | estado=ok",
                    nivel="success",
                )
                log(f"Batch {batch_idx}/{total_batches} procesado correctamente", nivel="success")
                break
            except ErrorTranscripcion as exc:
                duracion = time.perf_counter() - inicio_llamada
                log(
                    f"[LLM] Request fallida | batch={batch_idx}/{total_batches} "
                    f"intento={intento} | duración={duracion:.2f}s | error={truncar_texto_log(str(exc), 60)}",
                    nivel="error",
                )
                if intento > llm_retries:
                    log(
                        f"Batch {batch_idx}/{total_batches} falló tras {llm_retries + 1} intento(s). "
                        "Se conservará el texto original del batch.",
                        nivel="warning",
                    )
                    respuesta_validada = None
                    break
                espera = min(2.0 * intento, 8.0)
                total_reintentos += 1
                log(
                    f"Reintentando batch {batch_idx}/{total_batches} en {espera:.1f}s... (intento {intento})",
                    nivel="warning",
                )
                time.sleep(espera)

        if respuesta_validada is None:
            total_batches_fallback += 1
            continue

        cambios_batch, sin_cambios_batch = imprimir_cambios_batch(
            batch_llm=batch_llm,
            textos_mejorados=respuesta_validada,
        )
        total_segmentos_cambiados += cambios_batch
        total_segmentos_sin_cambios += sin_cambios_batch
        total_batches_ok += 1

        for local_idx, i in enumerate(range(inicio, fin)):
            mejorado = aplicar_fallback_texto_vacio(
                texto_original=segmentos[i].text,
                texto_mejorado=respuesta_validada[local_idx],
            )
            segmentos_resultado[i] = Segmento(
                start=segmentos[i].start,
                end=segmentos[i].end,
                text=mejorado,
            )
            json_resultado[i]["text"] = mejorado

    log_separador()
    log("Resumen postproceso LLM:", nivel="info")
    log(
        f"  • Batches OK: {total_batches_ok} | Batches fallback: {total_batches_fallback} | "
        f"Reintentos: {total_reintentos}",
        nivel="info",
    )
    log(
        f"  • Segmentos cambiados: {total_segmentos_cambiados} | "
        f"Sin cambios: {total_segmentos_sin_cambios} | Total: {total}",
        nivel="info",
    )
    log_separador()

    return segmentos_resultado, json_resultado

