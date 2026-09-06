"""Interface de linha de comando e orquestração do pipeline (Seção 6, 7 e 11)."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .audio_analysis import (
    compute_rms_envelope_db,
    detect_low_energy_segments,
    is_duration_too_short_for_analysis,
    load_wav_metadata,
)
from .audio_processing import (
    check_ffmpeg_available,
    normalize_loudness,
    run_demucs,
    trim_silence_edges,
)
from .config import DEFAULT_SILENCE_THRESHOLD_DB, SINGING_PRACTICAL_LIMIT_MIN
from .duet_report import build_duet_report, check_duration_match
from .errors import TalkingPrepError
from .lyrics import generate_avatar_prompt_suggestion, load_lyrics
from .recommendation import recommend_configuration
from .report import build_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talkingprep.py",
        description=(
            "Prepara faixas de áudio (separação vocal, análise, ficha técnica) para "
            "geração de Singing Videos no Talking Photos AI."
        ),
    )
    parser.add_argument("--audio", default=None, help="Caminho do arquivo .wav de entrada.")
    parser.add_argument(
        "--lyrics", default=None, help="Caminho do arquivo de texto (.txt/.md) com a letra."
    )
    parser.add_argument(
        "--title", default=None, help="Título da música (ou do dueto). Default: nome do arquivo de áudio."
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Pasta de destino. Default: pasta 'output/' no diretório do projeto.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=DEFAULT_SILENCE_THRESHOLD_DB,
        help=f"Limiar em dB para detecção de silêncio. Default: {DEFAULT_SILENCE_THRESHOLD_DB}.",
    )
    parser.add_argument(
        "--duet",
        action="store_true",
        help="Ativa o Modo Dueto (Seção 11): processa duas faixas (--audio-a / --audio-b).",
    )
    parser.add_argument("--audio-a", default=None, help="[Modo Dueto] Caminho do áudio do Cantor A.")
    parser.add_argument("--audio-b", default=None, help="[Modo Dueto] Caminho do áudio do Cantor B.")
    parser.add_argument("--lyrics-a", default=None, help="[Modo Dueto] Letra do Cantor A (opcional).")
    parser.add_argument("--lyrics-b", default=None, help="[Modo Dueto] Letra do Cantor B (opcional).")
    return parser


def _slugify(name: str) -> str:
    keep = "-_ "
    cleaned = "".join(c if c.isalnum() or c in keep else "_" for c in name)
    return cleaned.strip().replace(" ", "_")


@dataclass
class TrackResult:
    title: str
    output_dir: Path
    final_vocal_path: Path
    metadata_duration_sec: float
    duration_warning: str | None
    short_duration_warning: str | None
    lyrics_skipped: bool


def process_track(
    *,
    audio_path: Path,
    lyrics_path: Path | None,
    title: str,
    output_dir: Path,
    silence_threshold: float,
    slug: str,
    log_prefix: str = "",
    duet_note: str | None = None,
) -> TrackResult:
    """Roda o pipeline padrão (Seção 6, itens 1 a 6) para uma única faixa de áudio."""
    print(f"{log_prefix}Validando arquivo de áudio: {audio_path}")
    metadata = load_wav_metadata(audio_path)
    print(
        f"{log_prefix}Duração: {metadata.duration_sec:.2f}s | "
        f"{metadata.sample_rate} Hz | {metadata.channels} canal(is) | "
        f"{metadata.bit_depth} bits"
    )

    duration_warning = None
    if metadata.duration_sec / 60.0 > SINGING_PRACTICAL_LIMIT_MIN:
        duration_warning = (
            f"A faixa tem {metadata.duration_sec / 60:.2f} min, acima do limite "
            f"prático de {SINGING_PRACTICAL_LIMIT_MIN:.0f} min para o modo Singing "
            "normal. Pode ser necessário segmentar a faixa e usar o módulo "
            "'Mix Videos' do Talking Photos posteriormente."
        )
        print(f"{log_prefix}AVISO: {duration_warning}")

    short_duration_warning = None
    if is_duration_too_short_for_analysis(metadata.duration_sec):
        short_duration_warning = (
            f"A faixa tem apenas {metadata.duration_sec:.1f}s. A análise de energia "
            "pode não ter conteúdo suficiente para ser útil."
        )
        print(f"{log_prefix}AVISO: {short_duration_warning}")

    print(f"{log_prefix}Analisando energia do áudio (envelope RMS)...")
    envelope = compute_rms_envelope_db(audio_path)
    energy_segments = detect_low_energy_segments(envelope, threshold_db=silence_threshold)
    print(f"{log_prefix}{len(energy_segments)} trecho(s) de baixa energia detectado(s).")

    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "_demucs_tmp"

    print(f"{log_prefix}Rodando separação vocal (Demucs, CPU)... isso pode levar alguns minutos.")
    vocals_path, no_vocals_path = run_demucs(audio_path, work_dir)

    print(f"{log_prefix}Cortando silêncio nas pontas e normalizando o volume...")
    trimmed_path = output_dir / f"{slug}_trimmed_temp.wav"
    trim_silence_edges(vocals_path, trimmed_path, threshold_db=silence_threshold)

    final_vocal_path = output_dir / f"{slug}_vocal_isolado.wav"
    normalize_loudness(trimmed_path, final_vocal_path)
    trimmed_path.unlink(missing_ok=True)

    no_vocals_final = output_dir / f"{slug}_instrumental.wav"
    shutil.copy2(no_vocals_path, no_vocals_final)

    original_copy = output_dir / f"{slug}_original.wav"
    shutil.copy2(audio_path, original_copy)

    shutil.rmtree(work_dir, ignore_errors=True)

    print(f"{log_prefix}Gerando sugestão de prompt de avatar...")
    lyrics_text = load_lyrics(lyrics_path)
    lyrics_skipped = lyrics_text is None
    if lyrics_skipped:
        print(f"{log_prefix}AVISO: letra ausente ou vazia -- etapa de sugestão temática pulada.")
    avatar_prompt = generate_avatar_prompt_suggestion(title, lyrics_text)

    print(f"{log_prefix}Montando ficha técnica...")
    recommendation = recommend_configuration(metadata.duration_sec)
    report_text = build_report(
        title=title,
        metadata=metadata,
        energy_segments=energy_segments,
        silence_threshold_db=silence_threshold,
        recommendation=recommendation,
        avatar_prompt=avatar_prompt,
        duration_warning=duration_warning,
        short_duration_warning=short_duration_warning,
        lyrics_skipped=lyrics_skipped,
        vocal_filename=final_vocal_path.name,
        duet_note=duet_note,
    )
    report_path = output_dir / f"{slug}_ficha_tecnica.txt"
    report_path.write_text(report_text, encoding="utf-8")

    return TrackResult(
        title=title,
        output_dir=output_dir,
        final_vocal_path=final_vocal_path,
        metadata_duration_sec=metadata.duration_sec,
        duration_warning=duration_warning,
        short_duration_warning=short_duration_warning,
        lyrics_skipped=lyrics_skipped,
    )


def _run_single(args: argparse.Namespace, output_root: Path) -> int:
    if not args.audio or not args.lyrics:
        print("\nERRO: --audio e --lyrics são obrigatórios fora do Modo Dueto.", file=sys.stderr)
        return 1

    audio_path = Path(args.audio)
    lyrics_path = Path(args.lyrics)
    title = args.title or audio_path.stem
    silence_threshold = args.silence_threshold

    try:
        check_ffmpeg_available()
        slug = _slugify(title) or "faixa"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_root / f"{slug}_{timestamp}"

        print("[1/6] Iniciando processamento...")
        result = process_track(
            audio_path=audio_path,
            lyrics_path=lyrics_path,
            title=title,
            output_dir=output_dir,
            silence_threshold=silence_threshold,
            slug=slug,
        )
    except TalkingPrepError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            f"\nERRO ao escrever arquivos de saída (verifique espaço em disco): {exc}",
            file=sys.stderr,
        )
        return 1

    print("\n" + "=" * 60)
    print(f"Concluído: {result.title}")
    print(
        f"Duração: {result.metadata_duration_sec:.2f}s "
        f"({result.metadata_duration_sec / 60:.2f} min)"
    )
    if result.duration_warning:
        print(f"Aviso: {result.duration_warning}")
    if result.short_duration_warning:
        print(f"Aviso: {result.short_duration_warning}")
    if result.lyrics_skipped:
        print("Aviso: sugestão de prompt de avatar gerada sem base na letra (arquivo ausente/vazio).")
    print(f"Pasta de saída: {result.output_dir}")
    print("=" * 60)
    return 0


def _run_duet(args: argparse.Namespace, output_root: Path) -> int:
    if not args.audio_a or not args.audio_b:
        print("\nERRO: --audio-a e --audio-b são obrigatórios em Modo Dueto (--duet).", file=sys.stderr)
        return 1

    audio_a_path = Path(args.audio_a)
    audio_b_path = Path(args.audio_b)
    lyrics_a_path = Path(args.lyrics_a) if args.lyrics_a else None
    lyrics_b_path = Path(args.lyrics_b) if args.lyrics_b else None
    title = args.title or "dueto"
    silence_threshold = args.silence_threshold

    try:
        check_ffmpeg_available()
        slug = _slugify(title) or "dueto"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parent_dir = output_root / f"{slug}_dueto_{timestamp}"
        dir_a = parent_dir / "faixa_a"
        dir_b = parent_dir / "faixa_b"

        print("[Dueto] Processando Faixa A (Cantor A)...")
        result_a = process_track(
            audio_path=audio_a_path,
            lyrics_path=lyrics_a_path,
            title=f"{title} -- Cantor A",
            output_dir=dir_a,
            silence_threshold=silence_threshold,
            slug=f"{slug}_a",
            log_prefix="  [A] ",
            duet_note=(
                "Esta faixa faz parte de um Modo Dueto. Veja o arquivo 'ficha_dueto.txt' "
                "na pasta pai para as instruções de montagem do vídeo final."
            ),
        )

        print("[Dueto] Processando Faixa B (Cantor B)...")
        result_b = process_track(
            audio_path=audio_b_path,
            lyrics_path=lyrics_b_path,
            title=f"{title} -- Cantor B",
            output_dir=dir_b,
            silence_threshold=silence_threshold,
            slug=f"{slug}_b",
            log_prefix="  [B] ",
            duet_note=(
                "Esta faixa faz parte de um Modo Dueto. Veja o arquivo 'ficha_dueto.txt' "
                "na pasta pai para as instruções de montagem do vídeo final."
            ),
        )

        print("[Dueto] Comparando durações e montando ficha de dueto...")
        duration_check = check_duration_match(
            duration_a_sec=load_wav_metadata_seconds(result_a.final_vocal_path),
            duration_b_sec=load_wav_metadata_seconds(result_b.final_vocal_path),
        )
        if duration_check.mismatched:
            print(
                f"  AVISO: durações divergem em {duration_check.diff_sec:.2f}s -- "
                "veja ficha_dueto.txt."
            )

        duet_report_text = build_duet_report(
            title=title,
            vocal_filename_a=result_a.final_vocal_path.name,
            vocal_filename_b=result_b.final_vocal_path.name,
            duration_check=duration_check,
        )
        (parent_dir / "ficha_dueto.txt").write_text(duet_report_text, encoding="utf-8")

    except TalkingPrepError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            f"\nERRO ao escrever arquivos de saída (verifique espaço em disco): {exc}",
            file=sys.stderr,
        )
        return 1

    print("\n" + "=" * 60)
    print(f"Concluído (Dueto): {title}")
    print(f"Duração Faixa A: {duration_check.duration_a_sec:.2f}s")
    print(f"Duração Faixa B: {duration_check.duration_b_sec:.2f}s")
    if duration_check.mismatched:
        print(f"AVISO: divergência de duração de {duration_check.diff_sec:.2f}s entre as faixas.")
    print(f"Pasta de saída: {parent_dir}")
    print("=" * 60)
    return 0


def load_wav_metadata_seconds(path: Path) -> float:
    return load_wav_metadata(path).duration_sec


def run(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    output_root = Path(args.output_dir) if args.output_dir else project_root / "output"

    if args.duet:
        return _run_duet(args, output_root)
    return _run_single(args, output_root)


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
