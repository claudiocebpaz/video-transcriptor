from __future__ import annotations

import os
import sys
import time
from typing import Any


class TerminalColors:
    """Colores ANSI para salida terminal."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    INFO = "\033[96m"
    PROGRESS = "\033[94m"

    BG_DARK = "\033[48;5;236m"
    BG_SUCCESS = "\033[48;5;22m"
    BG_ERROR = "\033[48;5;52m"


def _es_terminal_soportada() -> bool:
    """Detecta si el terminal soporta colores ANSI."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    if term in ("dumb", ""):
        return False
    return True


_TERMINAL_SOPORTADA = _es_terminal_soportada()


def _colorize(texto: str, color: str) -> str:
    """Aplica color ANSI si el terminal lo soporta."""
    if not _TERMINAL_SOPORTADA:
        return texto
    return f"{color}{texto}{TerminalColors.RESET}"


def _bold(texto: str) -> str:
    """Aplica negrita si el terminal lo soporta."""
    if not _TERMINAL_SOPORTADA:
        return texto
    return f"{TerminalColors.BOLD}{texto}{TerminalColors.RESET}"


def log(mensaje: str, nivel: str = "info") -> None:
    """Imprime mensaje con formato y colores."""
    timestamp = time.strftime("%H:%M:%S")

    prefix = ""
    color = TerminalColors.WHITE

    if nivel == "success":
        prefix = "✅ "
        color = TerminalColors.SUCCESS
    elif nivel == "warning":
        prefix = "⚠️  "
        color = TerminalColors.WARNING
    elif nivel == "error":
        prefix = "❌ "
        color = TerminalColors.ERROR
    elif nivel == "progress":
        prefix = "⏳ "
        color = TerminalColors.PROGRESS
    elif nivel == "info":
        prefix = "ℹ️  "
        color = TerminalColors.INFO

    linea = f"[{timestamp}] {prefix}{mensaje}"
    print(_colorize(linea, color), flush=True)


def log_titulo(titulo: str) -> None:
    """Imprime un título formateado con separadores."""
    if not _TERMINAL_SOPORTADA:
        print(f"\n{'=' * 60}")
        print(f"  {titulo}")
        print(f"{'=' * 60}\n")
        return

    width = 60
    relleno = "─" * (width - len(titulo) - 2)
    print(
        f"\n{TerminalColors.CYAN}{TerminalColors.BOLD}┌{'─' * (width - 2)}┐{TerminalColors.RESET}"
    )
    print(
        f"{TerminalColors.CYAN}{TerminalColors.BOLD}│{TerminalColors.RESET} "
        f"{TerminalColors.BOLD}{titulo}{TerminalColors.RESET} "
        f"{TerminalColors.CYAN}{TerminalColors.BOLD}{relleno}│{TerminalColors.RESET}"
    )
    print(
        f"{TerminalColors.CYAN}{TerminalColors.BOLD}└{'─' * (width - 2)}┘{TerminalColors.RESET}\n"
    )


def log_separador() -> None:
    """Imprime un separador visual."""
    if not _TERMINAL_SOPORTADA:
        print("-" * 60)
        return
    print(f"{TerminalColors.DIM}{'─' * 60}{TerminalColors.RESET}")


def log_key_value(clave: str, valor: str, color_clave: str = TerminalColors.CYAN) -> None:
    """Imprime un par clave-valor formateado."""
    linea = f"  {_colorize(f'• {clave}:', color_clave)} {valor}"
    print(linea)


def log_bloque(titulo: str, lineas: list[str]) -> None:
    """Imprime un bloque de texto con título."""
    print()
    if _TERMINAL_SOPORTADA:
        print(f"{TerminalColors.BOLD}{titulo}:{TerminalColors.RESET}")
    else:
        print(f"{titulo}:")
    for linea in lineas:
        print(f"  {linea}")


class BarraProgreso:
    """Barra de progreso visual para la terminal."""

    def __init__(self, total: int, titulo: str = "Progreso", ancho: int = 40):
        self.total = total
        self.titulo = titulo
        self.ancho = ancho
        self.actual = 0
        self.inicio = time.perf_counter()
        self._ultima_linea_len = 0

    def actualizar(self, actual: int | None = None, mensaje: str = "") -> None:
        """Actualiza la barra de progreso."""
        if actual is not None:
            self.actual = actual
        else:
            self.actual += 1

        pct = min(100.0, (self.actual / self.total) * 100) if self.total > 0 else 100
        filled = int(self.ancho * self.actual / self.total) if self.total > 0 else self.ancho
        empty = self.ancho - filled

        elapsed = time.perf_counter() - self.inicio
        if self.actual > 0:
            eta = (elapsed / self.actual) * (self.total - self.actual)
            tiempo_str = f"ETA: {int(eta)}s"
        else:
            tiempo_str = "calculando..."

        if _TERMINAL_SOPORTADA:
            filled_bar = "█" * filled
            empty_bar = "░" * empty
            barra = (
                f"{TerminalColors.PROGRESS}{filled_bar}{TerminalColors.DIM}{empty_bar}"
                f"{TerminalColors.RESET}"
            )
            linea = (
                f"\r{self.titulo}: |{barra}| {pct:5.1f}% ({self.actual}/{self.total}) "
                f"{tiempo_str} {mensaje}"
            )
        else:
            pct_bar = "#" * filled
            linea = (
                f"\r{self.titulo}: [{pct_bar:<{self.ancho}}] {pct:.1f}% "
                f"({self.actual}/{self.total}) {tiempo_str}"
            )

        if self._ultima_linea_len:
            print(" " * self._ultima_linea_len, end="\r")
        print(linea, end="", flush=True)
        self._ultima_linea_len = len(linea)

    def finish(self, mensaje: str = "") -> None:
        """Finaliza la barra de progreso."""
        self.actual = self.total
        self.actualizar(mensaje=mensaje)
        print()

    def __enter__(self) -> "BarraProgreso":
        return self

    def __exit__(self, *args: Any) -> None:
        self.finish()


def formatear_duracion(segundos: float) -> str:
    """Formatea duración en formato legible."""
    if segundos < 60:
        return f"{segundos:.1f}s"
    if segundos < 3600:
        mins = int(segundos // 60)
        secs = int(segundos % 60)
        return f"{mins}m {secs}s"
    horas = int(segundos // 3600)
    mins = int((segundos % 3600) // 60)
    return f"{horas}h {mins}m"


def formatear_tamanio(bytes_size: int) -> str:
    """Formatea tamaño de archivo en formato legible."""
    size = float(bytes_size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

