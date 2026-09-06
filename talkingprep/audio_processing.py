"""Separação vocal (Demucs) e pós-processamento de áudio via ffmpeg (Seção 6, item 4)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .errors import ExternalToolError


def check_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise ExternalToolError(
            "ffmpeg não foi encontrado no PATH do sistema. Instale-o antes de continuar "
            "(veja o README para instruções)."
        )


def run_demucs(input_wav: Path, work_dir: Path, model: str = "htdemucs") -> tuple[Path, Path]:
    """Roda o Demucs (--two-stems=vocals) sobre o arquivo de entrada.

    Retorna (caminho_vocals.wav, caminho_no_vocals.wav). Roda 100% em CPU.
    Na primeira execução, o Demucs baixa o modelo da internet automaticamente.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=vocals",
        "-n",
        model,
        "-d",
        "cpu",
        "-o",
        str(work_dir),
        str(input_wav),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ExternalToolError(
            "Demucs não está instalado no ambiente Python atual. "
            "Rode 'pip install -r requirements.txt' antes de usar o TalkingPrep."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ExternalToolError(
            f"Falha ao executar o Demucs (código {exc.returncode}).\n"
            f"Saída de erro:\n{exc.stderr}\n"
            "Se esta for a primeira execução, verifique sua conexão com a internet "
            "(o modelo precisa ser baixado)."
        ) from exc

    stem_dir = work_dir / model / input_wav.stem
    vocals_path = stem_dir / "vocals.wav"
    no_vocals_path = stem_dir / "no_vocals.wav"

    if not vocals_path.exists() or not no_vocals_path.exists():
        raise ExternalToolError(
            f"Demucs terminou mas os arquivos esperados não foram encontrados em {stem_dir}."
        )

    return vocals_path, no_vocals_path


def _run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ExternalToolError(
            "ffmpeg não foi encontrado no PATH do sistema. Instale-o antes de continuar."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ExternalToolError(f"Falha ao executar ffmpeg:\n{exc.stderr}") from exc


def trim_silence_edges(input_wav: Path, output_wav: Path, threshold_db: float) -> None:
    """Corta silêncio apenas nas pontas (início/fim), nunca no meio da faixa."""
    silence_filter = (
        f"silenceremove=start_periods=1:start_threshold={threshold_db}dB:start_silence=0.1,"
        f"areverse,"
        f"silenceremove=start_periods=1:start_threshold={threshold_db}dB:start_silence=0.1,"
        f"areverse"
    )
    _run_ffmpeg(["-i", str(input_wav), "-af", silence_filter, str(output_wav)])


def normalize_loudness(input_wav: Path, output_wav: Path) -> None:
    """Normaliza o loudness do áudio (EBU R128 / loudnorm, passagem única)."""
    _run_ffmpeg(["-i", str(input_wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", str(output_wav)])
