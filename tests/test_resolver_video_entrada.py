from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.transcribir_video import ErrorTranscripcion, resolver_video_entrada


class ResolverVideoEntradaTests(unittest.TestCase):
    def test_usa_archivo_explicito(self) -> None:
        with TemporaryDirectory() as td:
            raiz = Path(td)
            explicito = raiz / "manual.mp4"
            explicito.write_text("x", encoding="utf-8")

            resultado = resolver_video_entrada(explicito, raiz)

            self.assertEqual(resultado, explicito)

    def test_deteccion_automatica_exitosa(self) -> None:
        with TemporaryDirectory() as td:
            raiz = Path(td)
            carpeta_entrada = raiz / "video_entrada"
            carpeta_entrada.mkdir(parents=True, exist_ok=True)
            video = carpeta_entrada / "video_unico.webm"
            video.write_text("x", encoding="utf-8")

            resultado = resolver_video_entrada(None, raiz)

            self.assertEqual(resultado, video)

    def test_multiples_candidatos_prioriza_alfabetico(self) -> None:
        with TemporaryDirectory() as td:
            raiz = Path(td)
            carpeta_entrada = raiz / "video_entrada"
            carpeta_entrada.mkdir(parents=True, exist_ok=True)
            (carpeta_entrada / "zeta.mkv").write_text("x", encoding="utf-8")
            elegido = carpeta_entrada / "alfa.mp4"
            elegido.write_text("x", encoding="utf-8")
            (carpeta_entrada / "medio.mov").write_text("x", encoding="utf-8")

            resultado = resolver_video_entrada(None, raiz)

            self.assertEqual(resultado, elegido)

    def test_sin_videos_lanza_error_claro(self) -> None:
        with TemporaryDirectory() as td:
            raiz = Path(td)
            carpeta_entrada = raiz / "video_entrada"
            carpeta_entrada.mkdir(parents=True, exist_ok=True)
            (carpeta_entrada / "nota.txt").write_text("x", encoding="utf-8")

            with self.assertRaises(ErrorTranscripcion) as ctx:
                resolver_video_entrada(None, raiz)

            mensaje = str(ctx.exception)
            self.assertIn("No se encontró un video", mensaje)
            self.assertIn(
                "python scripts/transcribir_video.py ./video_entrada/mi_video.mp4",
                mensaje,
            )


if __name__ == "__main__":
    unittest.main()
