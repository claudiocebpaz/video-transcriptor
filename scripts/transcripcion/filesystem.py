from __future__ import annotations

import re
from pathlib import Path

from .errors import ErrorTranscripcion
from .logging_terminal import log

VIDEO_EXTS_PERMITIDAS = (".mp4", ".mkv", ".mov", ".avi", ".webm")


def verificar_archivo(path: Path) -> None:
    """Verifica que la ruta exista y sea un archivo."""
    if not path.exists():
        raise ErrorTranscripcion(f"El archivo no existe: {path}")
    if not path.is_file():
        raise ErrorTranscripcion(f"La ruta no es un archivo valido: {path}")


def resolver_prefijo_salida(valor: str) -> Path:
    """Resuelve prefijo de salida permitiendo carpeta o prefijo completo."""
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
    """Normaliza nombre para uso en archivos temporales."""
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre).strip("._")
    return limpio or "video"


def resolver_video_entrada(video_arg: Path | None, raiz: Path) -> Path:
    """Resuelve video explícito o lo autodetecta desde video_entrada/."""
    if video_arg is not None:
        return video_arg

    carpeta_entrada = raiz / "video_entrada"
    if not carpeta_entrada.exists() or not carpeta_entrada.is_dir():
        raise ErrorTranscripcion(
            "No existe la carpeta de entrada 'video_entrada'. "
            "Creala en la raíz del proyecto o indicá un video manualmente."
        )

    candidatos = sorted(
        [
            p
            for p in carpeta_entrada.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTS_PERMITIDAS
        ],
        key=lambda p: p.name.lower(),
    )

    if not candidatos:
        formatos = ", ".join(VIDEO_EXTS_PERMITIDAS)
        raise ErrorTranscripcion(
            "No se encontró un video en 'video_entrada' para transcribir. "
            f"Formatos buscados: {formatos}. "
            "Indicá el archivo manualmente, por ejemplo: "
            "python scripts/transcribir_video.py ./video_entrada/mi_video.mp4"
        )

    elegido = candidatos[0]
    if len(candidatos) == 1:
        log(f"Video detectado automáticamente: {elegido.name}", nivel="info")
    else:
        lista = ", ".join(p.name for p in candidatos)
        log(
            f"Se detectaron múltiples videos en 'video_entrada' ({lista}). "
            f"Se usará {elegido.name} por orden alfabético.",
            nivel="warning",
        )
    return elegido

