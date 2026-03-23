from __future__ import annotations

import re


def normalizar_espacios(texto: str) -> str:
    """Colapsa espacios consecutivos y recorta extremos."""
    return re.sub(r"\s+", " ", texto).strip()

