from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Segmento:
    """Representa un segmento transcripto con tiempos absolutos."""

    start: float
    end: float
    text: str

