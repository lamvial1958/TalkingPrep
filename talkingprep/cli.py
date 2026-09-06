"""Interface de linha de comando e orquestração do pipeline (Seção 6 e 7)."""

from __future__ import annotations

import argparse
import shutil
import sys
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
from .errors import DiskSpaceError, ExternalToolError, InvalidAudioError, TalkingPrepError
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
    parser.add_argument("--audio", required=True, help="Caminho do arquivo .wav de entrada.")
    parser.add_argument(
        "--lyrics", required=True, help="Caminho do arquivo de texto (.txt/.md) com a letra."
    )
    parser.add_argument(
        "--title", default=None, help="Título da música. Default: nome do arquivo de áudio."
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
    return parser


def _slugify(name: str) -> str:
    keep = "-_ "
    cleaned = "".join(c if c.isalnum() or c in keep else "_" for c in name)
    return cleaned.strip().replace(" ", "_")


def run(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    audio_path = Path(args.audio)
    lyrics_path = Path(args.lyrics) if args.lyrics else None
    title = args.title or audio_path.stem
    silence_threshold = args.silence_threshold

    project_root = Path(__file__).resolve().parent.parent
    output_root = Path(args.output_dir) if args.output_dir else project_root / "output"

    try:
        check_ffmpeg_available()

        print(f"[1/6] Validando arquivo de áudio: {audio_path}")
        metadata = load_wav_metadata(audio_path)
        print(
            f"      Duração: {metadata.duration_sec:.2f}s | "
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
            print(f"      AVISO: {duration_warning}")

        short_duration_warning = None
        if is_duration_too_short_for_analysis(metadata.duration_sec):
            short_duration_warning = (
                f"A faixa tem apenas {metadata.duration_sec:.1f}s. A análise de energia "
                "pode não ter conteúdo suficiente para ser útil."
            )
            print(f"      AVISO: {short_duration_warning}")

        print("[2/6] Analisando energia do áudio (envelope RMS)...")
        envelope = compute_rms_envelope_db(audio_path)
        energy_segments = detect_low_energy_segments(envelope, threshold_db=silence_threshold)
        print(f"      {len(energy_segments)} trecho(s) de baixa energia detectado(s).")

        slug = _slugify(title) or "faixa"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_root / f"{slug}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        work_dir = output_dir / "_demucs_tmp"

        print("[3/6] Rodando separação vocal (Demucs, CPU)... isso pode levar alguns minutos.")
        vocals_path, no_vocals_path = run_demucs(audio_path, work_dir)

        print("[4/6] Cortando silêncio nas pontas e normalizando o volume...")
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

        print("[5/6] Gerando sugestão de prompt de avatar...")
        lyrics_text = load_lyrics(lyrics_path)
        lyrics_skipped = lyrics_text is None
        if lyrics_skipped:
            print("      AVISO: letra ausente ou vazia — etapa de sugestão temática pulada.")
        avatar_prompt = generate_avatar_prompt_suggestion(title, lyrics_text)

        print("[6/6] Montando ficha técnica...")
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
        )
        report_path = output_dir / f"{slug}_ficha_tecnica.md"
        report_path.write_text(report_text, encoding="utf-8")

    except InvalidAudioError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    except ExternalToolError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            f"\nERRO ao escrever arquivos de saída (verifique espaço em disco): {exc}",
            file=sys.stderr,
        )
        return 1
    except TalkingPrepError as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 60)
    print(f"Concluído: {title}")
    print(f"Duração: {metadata.duration_sec:.2f}s ({metadata.duration_sec / 60:.2f} min)")
    if duration_warning:
        print(f"Aviso: {duration_warning}")
    if short_duration_warning:
        print(f"Aviso: {short_duration_warning}")
    if lyrics_skipped:
        print("Aviso: sugestão de prompt de avatar gerada sem base na letra (arquivo ausente/vazio).")
    print(f"Pasta de saída: {output_dir}")
    print("=" * 60)

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
