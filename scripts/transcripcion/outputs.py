from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Segmento


def formatear_timestamp_srt(segundos: float) -> str:
    """Convierte segundos en timestamp SRT HH:MM:SS,mmm."""
    total_ms = int(round(max(0.0, segundos) * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos_int, milisegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_int:02d},{milisegundos:03d}"


def escribir_txt(path: Path, segmentos: list[Segmento]) -> None:
    """Escribe transcripción plana con una línea por segmento."""
    contenido = "\n".join(s.text for s in segmentos).strip()
    path.write_text(contenido + "\n", encoding="utf-8")


def escribir_srt(path: Path, segmentos: list[Segmento]) -> None:
    """Escribe archivo SRT."""
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
    """Escribe salida JSON identada UTF-8."""
    with path.open("w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)

