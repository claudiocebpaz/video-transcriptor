from __future__ import annotations

import os
from pathlib import Path

from .logging_terminal import log


def parsear_linea_env(linea: str) -> tuple[str, str] | None:
    """Parsea una línea de archivo .env en formato clave=valor."""
    cruda = linea.strip()
    if not cruda or cruda.startswith("#"):
        return None

    if cruda.startswith("export "):
        cruda = cruda[len("export ") :].strip()

    if "=" not in cruda:
        return None

    clave, valor = cruda.split("=", 1)
    clave_limpia = clave.strip()
    if not clave_limpia:
        return None

    valor_limpio = valor.strip()
    if len(valor_limpio) >= 2 and (
        (valor_limpio.startswith('"') and valor_limpio.endswith('"'))
        or (valor_limpio.startswith("'") and valor_limpio.endswith("'"))
    ):
        valor_limpio = valor_limpio[1:-1]

    return clave_limpia, valor_limpio


def cargar_env_desde_archivo(path_env: Path, override: bool = False) -> int:
    """Carga variables de entorno desde archivo .env."""
    if not path_env.exists() or not path_env.is_file():
        return 0

    cargadas = 0
    for linea in path_env.read_text(encoding="utf-8").splitlines():
        parseada = parsear_linea_env(linea)
        if parseada is None:
            continue
        clave, valor = parseada
        if not override and clave in os.environ:
            continue
        os.environ[clave] = valor
        cargadas += 1
    return cargadas


def resolver_archivos_env() -> list[Path]:
    """Resuelve los archivos .env candidatos a cargar."""
    raiz_proyecto = Path(__file__).resolve().parent.parent.parent
    desde_script = raiz_proyecto / ".env"
    desde_cwd = Path.cwd() / ".env"

    candidatos: list[Path] = []
    for candidato in (desde_script, desde_cwd):
        if candidato not in candidatos:
            candidatos.append(candidato)
    return candidatos


def cargar_env_robusto() -> None:
    """Carga configuración .env priorizando no sobrescribir entorno existente."""
    archivos = resolver_archivos_env()
    for archivo in archivos:
        cargadas = cargar_env_desde_archivo(archivo, override=False)
        if archivo.exists():
            log(
                f"Configuración .env detectada | archivo={archivo} variables_cargadas={cargadas}",
                nivel="info",
            )


def detectar_variable_api_key_configurada(llm_provider: str) -> str | None:
    """Detecta variable de API key disponible para el proveedor LLM."""
    provider = llm_provider.lower()
    if provider != "deepseek":
        return None

    for variable in ("DEEPSEEK_API_KEY", "DEEPSEEK_APIKEY", "OPENAI_API_KEY"):
        if os.environ.get(variable, "").strip():
            return variable
    return None

