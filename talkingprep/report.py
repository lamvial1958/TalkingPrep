"""Geração da ficha técnica final em Markdown (Seção 6, item 6)."""

from __future__ import annotations

from datetime import datetime

from .audio_analysis import AudioMetadata
from .config import (
    DEFAULT_SILENCE_THRESHOLD_DB,
    SINGING_MANUAL_LIMIT_MIN,
    SINGING_PRACTICAL_LIMIT_MIN,
    TALKING_PHOTOS_RULES,
)
from .recommendation import Recommendation


def _format_segments(segments: list[tuple[float, float]]) -> str:
    if not segments:
        return "Nenhum trecho de baixa energia detectado."
    lines = []
    for start, end in segments:
        lines.append(f"- {start:.1f}s – {end:.1f}s (duração: {end - start:.1f}s)")
    return "\n".join(lines)


def _format_rules_table() -> str:
    header = "| Categoria | Engine | Qualidade | Limite de duração por clipe |"
    sep = "|---|---|---|---|"
    rows = [header, sep]
    for rule in TALKING_PHOTOS_RULES:
        limite = f"Até {rule['limite_duracao_min']:.1f} min".replace(".0", "")
        rows.append(
            f"| {rule['categoria']} | {rule['engine']} | {rule['qualidade']} | {limite} |"
        )
    table = "\n".join(rows)

    nota_singing = next(
        (r["nota"] for r in TALKING_PHOTOS_RULES if r["categoria"] == "Singing Video" and "nota" in r),
        None,
    )
    if nota_singing:
        table += f"\n\n> **Nota sobre Singing Video:** {nota_singing}"
    return table


def build_report(
    *,
    title: str,
    metadata: AudioMetadata,
    energy_segments: list[tuple[float, float]],
    silence_threshold_db: float,
    recommendation: Recommendation,
    avatar_prompt: str,
    duration_warning: str | None,
    short_duration_warning: str | None,
    lyrics_skipped: bool,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# Ficha Técnica — {title}",
        "",
        f"**Data de processamento:** {now}",
        "",
        "## Metadados técnicos do áudio original",
        "",
        f"- Duração: {metadata.duration_sec:.2f} segundos ({metadata.duration_sec / 60:.2f} min)",
        f"- Taxa de amostragem: {metadata.sample_rate} Hz",
        f"- Canais: {metadata.channels}",
        f"- Profundidade de bits: {metadata.bit_depth} bits",
        "",
    ]

    if duration_warning:
        lines += [f"> ⚠️ **Aviso de duração:** {duration_warning}", ""]
    if short_duration_warning:
        lines += [f"> ⚠️ **Aviso de faixa curta:** {short_duration_warning}", ""]

    lines += [
        "## Análise de energia (RMS, janelas de 1s)",
        "",
        f"Limiar de silêncio/baixa energia utilizado: {silence_threshold_db:.1f} dBFS.",
        "",
        "Trechos sinalizados como candidatos a silêncio/introdução instrumental/pausa "
        "(apenas informativo — nenhum corte automático foi aplicado no meio da faixa):",
        "",
        _format_segments(energy_segments),
        "",
        "## Regras de referência — Talking Photos AI",
        "",
        _format_rules_table(),
        "",
        "## Recomendação de configuração",
        "",
        f"**Principal:** {recommendation.principal}",
        "",
    ]

    if recommendation.alternativas:
        lines.append("**Alternativas:**")
        for alt in recommendation.alternativas:
            lines.append(f"- {alt}")
        lines.append("")

    if recommendation.avisos:
        for aviso in recommendation.avisos:
            lines.append(f"> ⚠️ {aviso}")
        lines.append("")

    lines += [
        "## Sugestão de prompt de avatar",
        "",
    ]
    if lyrics_skipped:
        lines.append("> ⚠️ Etapa de leitura da letra foi pulada (arquivo ausente ou vazio).")
        lines.append("")
    lines.append(avatar_prompt)
    lines += [
        "",
        "## Checklist manual — passos restantes no Talking Photos",
        "",
        "- [ ] Fazer upload do áudio vocal isolado (`*_vocal_isolado.wav`) no Talking Photos.",
        "- [ ] Escolher o modo indicado na seção 'Recomendação de configuração' acima.",
        "- [ ] Gerar ou fazer upload do avatar/imagem, usando a sugestão de prompt acima.",
        "- [ ] Conferir o enquadramento (close-up, fundo neutro) antes de renderizar.",
        "- [ ] Rodar a geração do vídeo (Singing Video) no Talking Photos.",
        "- [ ] Se a faixa exceder "
        f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} min, usar o módulo 'Mix Videos' para unir segmentos.",
        "",
    ]

    return "\n".join(lines)
