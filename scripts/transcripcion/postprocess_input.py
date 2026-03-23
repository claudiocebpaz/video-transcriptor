from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ErrorTranscripcion
from .models import Segmento
from .text_utils import normalizar_espacios


def segmentos_desde_registros_json(
    registros_json: list[dict[str, Any]],
) -> list[Segmento]:
    """Convierte registros JSON validados en segmentos de dominio."""
    segmentos: list[Segmento] = []
    for indice, item in enumerate(registros_json, start=1):
        if not isinstance(item, dict):
            raise ErrorTranscripcion(
                f"JSON inválido en segmento {indice}: cada item debe ser objeto."
            )
        if "start" not in item or "end" not in item or "text" not in item:
            raise ErrorTranscripcion(
                f"JSON inválido en segmento {indice}: faltan start/end/text."
            )
        try:
            start = float(item["start"])
            end = float(item["end"])
        except (TypeError, ValueError) as exc:
            raise ErrorTranscripcion(
                f"JSON inválido en segmento {indice}: start/end no numéricos."
            ) from exc
        if end <= start:
            raise ErrorTranscripcion(
                f"JSON inválido en segmento {indice}: end debe ser mayor a start."
            )
        text = item["text"]
        if not isinstance(text, str):
            raise ErrorTranscripcion(
                f"JSON inválido en segmento {indice}: text debe ser string."
            )
        segmentos.append(Segmento(start=start, end=end, text=normalizar_espacios(text)))
    return segmentos


def leer_registros_json(path: Path) -> list[dict[str, Any]]:
    """Lee y valida estructura base de un JSON de segmentos."""
    if not path.exists() or not path.is_file():
        raise ErrorTranscripcion(f"No existe el JSON de entrada para postproceso: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorTranscripcion(f"El JSON de entrada es inválido: {path}") from exc

    if not isinstance(data, list):
        raise ErrorTranscripcion(f"El JSON de entrada debe ser una lista: {path}")

    salida: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ErrorTranscripcion(
                f"El JSON de entrada contiene elementos no-objeto: {path}"
            )
        salida.append(dict(item))
    return salida


def resolver_json_entrada_postprocess_only(prefijo: Path) -> Path:
    """Resuelve JSON de entrada priorizando *.raw.json sobre *.json."""
    raw_path = prefijo.with_suffix(".raw.json")
    final_path = prefijo.with_suffix(".json")

    if raw_path.exists() and raw_path.is_file():
        return raw_path
    if final_path.exists() and final_path.is_file():
        return final_path

    raise ErrorTranscripcion(
        "No se encontró JSON para --postprocess-only. "
        f"Buscado en {raw_path} y {final_path}."
    )

