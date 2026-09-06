"""Validação de entrada e análise técnica de áudio (Seção 6, itens 2 e 3 do CLAUDE.md)."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import DEFAULT_SILENCE_THRESHOLD_DB, MIN_USEFUL_DURATION_SEC
from .errors import InvalidAudioError


@dataclass
class AudioMetadata:
    duration_sec: float
    sample_rate: int
    channels: int
    bit_depth: int


def load_wav_metadata(path: Path) -> AudioMetadata:
    """Valida que o arquivo é um WAV legível e extrai seus metadados básicos."""
    if not path.exists():
        raise InvalidAudioError(f"Arquivo de áudio não encontrado: {path}")
    if path.suffix.lower() != ".wav":
        raise InvalidAudioError(
            f"Formato não suportado: '{path.suffix}'. Apenas arquivos .wav são aceitos."
        )
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
    except (wave.Error, EOFError) as exc:
        raise InvalidAudioError(
            f"Arquivo de áudio corrompido ou não é um WAV válido: {path} ({exc})"
        ) from exc

    if rate <= 0:
        raise InvalidAudioError(f"Arquivo de áudio com taxa de amostragem inválida: {path}")

    duration_sec = frames / float(rate)
    return AudioMetadata(
        duration_sec=duration_sec,
        sample_rate=rate,
        channels=channels,
        bit_depth=sampwidth * 8,
    )


def _read_samples_mono(path: Path) -> tuple[np.ndarray, int]:
    """Lê o WAV inteiro e retorna amostras normalizadas em [-1, 1], já convertidas a mono."""
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth)
    if dtype is None:
        raise InvalidAudioError(f"Profundidade de bits não suportada ({sampwidth * 8} bits): {path}")

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    max_val = float(2 ** (sampwidth * 8 - 1))
    samples /= max_val

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples, rate


def compute_rms_envelope_db(path: Path, window_sec: float = 1.0) -> list[tuple[float, float]]:
    """Calcula o envelope RMS em janelas de `window_sec`, em dBFS.

    Retorna uma lista de (tempo_inicial_seg, nivel_db).
    """
    samples, rate = _read_samples_mono(path)
    window_size = max(1, int(round(window_sec * rate)))
    n_windows = int(np.ceil(len(samples) / window_size)) if len(samples) else 0

    envelope: list[tuple[float, float]] = []
    for i in range(n_windows):
        start = i * window_size
        end = min(start + window_size, len(samples))
        chunk = samples[start:end]
        rms = float(np.sqrt(np.mean(np.square(chunk)))) if len(chunk) else 0.0
        db = 20 * np.log10(rms) if rms > 1e-9 else -120.0
        envelope.append((start / rate, db))

    return envelope


def detect_low_energy_segments(
    envelope: list[tuple[float, float]],
    threshold_db: float = DEFAULT_SILENCE_THRESHOLD_DB,
    window_sec: float = 1.0,
) -> list[tuple[float, float]]:
    """Identifica e mescla trechos contíguos abaixo do limiar de energia.

    Retorna lista de (inicio_seg, fim_seg). Uso apenas informativo — não altera o áudio.
    """
    segments: list[tuple[float, float]] = []
    current_start: float | None = None

    for t, db in envelope:
        if db < threshold_db:
            if current_start is None:
                current_start = t
        else:
            if current_start is not None:
                segments.append((current_start, t))
                current_start = None

    if current_start is not None:
        segments.append((current_start, envelope[-1][0] + window_sec if envelope else current_start))

    return segments


def is_duration_too_short_for_analysis(duration_sec: float) -> bool:
    return duration_sec < MIN_USEFUL_DURATION_SEC
