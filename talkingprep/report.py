"""Geração da ficha técnica final em texto simples (Seção 6, item 6; Seção 11)."""

from __future__ import annotations

from datetime import datetime

from .audio_analysis import AudioMetadata
from .config import (
    SINGING_PRACTICAL_LIMIT_MIN,
    TALKING_PHOTOS_RULES,
)
from .recommendation import Recommendation

_BAR = "=" * 70
_SEP = "-" * 70


def _format_segments(segments: list[tuple[float, float]]) -> str:
    if not segments:
        return "Nenhum trecho de baixa energia detectado."
    lines = []
    for start, end in segments:
        lines.append(f"  - {start:.1f}s a {end:.1f}s (duração: {end - start:.1f}s)")
    return "\n".join(lines)


def _format_rules_table() -> str:
    col_cat, col_eng, col_qual, col_lim = 26, 12, 14, 22
    header = (
        f"{'Categoria':<{col_cat}}{'Engine':<{col_eng}}"
        f"{'Qualidade':<{col_qual}}{'Limite por clipe':<{col_lim}}"
    )
    rows = [header, "-" * len(header)]
    for rule in TALKING_PHOTOS_RULES:
        limite = f"Até {rule['limite_duracao_min']:.1f} min".replace(".0", "")
        rows.append(
            f"{rule['categoria']:<{col_cat}}{rule['engine']:<{col_eng}}"
            f"{rule['qualidade']:<{col_qual}}{limite:<{col_lim}}"
        )
    table = "\n".join(rows)

    nota_singing = next(
        (r["nota"] for r in TALKING_PHOTOS_RULES if r["categoria"] == "Singing Video" and "nota" in r),
        None,
    )
    if nota_singing:
        table += f"\n\nNOTA sobre Singing Video: {nota_singing}"
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
    vocal_filename: str,
    duet_note: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        _BAR,
        f"FICHA TÉCNICA -- {title}",
        _BAR,
        "",
        f"Data de processamento: {now}",
        "",
    ]

    if duet_note:
        lines += [duet_note, ""]

    lines += [
        _SEP,
        "METADADOS TÉCNICOS DO ÁUDIO ORIGINAL",
        _SEP,
        "",
        f"- Duração: {metadata.duration_sec:.2f} segundos ({metadata.duration_sec / 60:.2f} min)",
        f"- Taxa de amostragem: {metadata.sample_rate} Hz",
        f"- Canais: {metadata.channels}",
        f"- Profundidade de bits: {metadata.bit_depth} bits",
        "",
    ]

    if duration_warning:
        lines += [f"AVISO DE DURAÇÃO: {duration_warning}", ""]
    if short_duration_warning:
        lines += [f"AVISO DE FAIXA CURTA: {short_duration_warning}", ""]

    lines += [
        _SEP,
        "ANÁLISE DE ENERGIA (RMS, JANELAS DE 1 SEGUNDO)",
        _SEP,
        "",
        f"Limiar de silêncio/baixa energia utilizado: {silence_threshold_db:.1f} dBFS.",
        "",
        "Trechos sinalizados como candidatos a silêncio/introdução instrumental/pausa",
        "(apenas informativo -- nenhum corte automático foi aplicado no meio da faixa):",
        "",
        _format_segments(energy_segments),
        "",
        _SEP,
        "REGRAS DE REFERÊNCIA -- TALKING PHOTOS AI",
        _SEP,
        "",
        _format_rules_table(),
        "",
        _SEP,
        "RECOMENDAÇÃO DE CONFIGURAÇÃO",
        _SEP,
        "",
        f"Principal: {recommendation.principal}",
        "",
    ]

    if recommendation.alternativas:
        lines.append("Alternativas:")
        for alt in recommendation.alternativas:
            lines.append(f"  - {alt}")
        lines.append("")

    if recommendation.avisos:
        for aviso in recommendation.avisos:
            lines.append(f"AVISO: {aviso}")
        lines.append("")

    lines += [
        _SEP,
        "SUGESTÃO DE PROMPT DE AVATAR",
        _SEP,
        "",
    ]
    if lyrics_skipped:
        lines.append("AVISO: etapa de leitura da letra foi pulada (arquivo ausente ou vazio).")
        lines.append("")
    lines.append(avatar_prompt)
    lines += [
        "",
        _SEP,
        "CHECKLIST MANUAL -- PASSOS RESTANTES NO TALKING PHOTOS",
        _SEP,
        "",
        "Siga os passos abaixo, na ordem, dentro do site/aplicativo do Talking Photos AI:",
        "",
        f"1. Faça login no Talking Photos AI e inicie a criação de um novo vídeo.",
        f"2. Quando for pedido o áudio, envie (faça upload d)o arquivo "
        f"'{vocal_filename}', que está nesta mesma pasta de saída. Não envie o "
        f"áudio original nem o instrumental -- apenas este arquivo, que já é a voz "
        f"isolada, cortada nas pontas e com volume normalizado.",
        "3. Selecione a categoria 'Singing Video' (às vezes chamada de 'Singing' ou "
        "'Cantar', dependendo da versão da interface -- não temos certeza do nome "
        "exato do botão nesta versão, mas é a opção destinada a vídeos de música/canto).",
        f"4. Escolha o modo indicado na seção 'RECOMENDAÇÃO DE CONFIGURAÇÃO' acima "
        f"(engine e qualidade). Se houver mais de uma alternativa listada, escolha "
        f"a que melhor equilibra qualidade e duração para o seu caso.",
        "5. Envie ou gere a imagem do avatar, usando a sugestão de prompt da seção "
        "'SUGESTÃO DE PROMPT DE AVATAR' acima, no campo de geração/upload de imagem "
        "do Talking Photos.",
        "6. Antes de confirmar a geração, confira visualmente que o enquadramento "
        "está em close-up (rosto), com fundo neutro, olhando para a câmera -- evite "
        "imagens com ombros ou braços muito visíveis.",
        "7. Confirme e inicie a geração do vídeo (render). O tempo médio de "
        "processamento do modo Singing/Padrão é de aproximadamente 15 minutos para "
        "faixas de até 5 minutos.",
        "8. Ao terminar, baixe o vídeo gerado e confira o resultado antes de "
        "considerar a tarefa concluída.",
        "",
        "Se a faixa exceder "
        f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} minutos, ela precisa ser dividida em "
        "partes menores antes deste processo. Neste caso, gere um vídeo separado "
        "para cada parte e depois use o módulo 'Mix Videos' do próprio Talking "
        "Photos para uni-los na ordem correta.",
        "",
    ]

    return "\n".join(lines)
