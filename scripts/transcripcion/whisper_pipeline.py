from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Segmento
from .text_utils import normalizar_espacios


def transcribir_chunk(
    model: Any,
    chunk_path: Path,
    offset_segundos: float,
    language: str,
    beam_size: int,
    word_timestamps: bool,
) -> tuple[list[Segmento], list[dict[str, Any]]]:
    """Transcribe un chunk y retorna segmentos normalizados y JSON asociado."""
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

