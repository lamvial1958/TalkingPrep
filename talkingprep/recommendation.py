"""Lógica de recomendação de configuração para o Talking Photos AI (Seção 5 + 6)."""

from __future__ import annotations

from dataclasses import dataclass

from .config import SINGING_MANUAL_LIMIT_MIN, SINGING_PRACTICAL_LIMIT_MIN


@dataclass
class Recommendation:
    principal: str
    alternativas: list[str]
    avisos: list[str]


def recommend_configuration(duration_sec: float) -> Recommendation:
    duration_min = duration_sec / 60.0
    avisos: list[str] = []
    alternativas: list[str] = []

    if duration_min <= SINGING_PRACTICAL_LIMIT_MIN:
        principal = (
            "Singing / Normal (qualidade Padrão, engine 3.0) — "
            f"faixa de {duration_min:.2f} min está dentro do limite prático de "
            f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} min confirmado pelo usuário para este modo."
        )
        if duration_min <= 1.0:
            alternativas.append(
                "Singing / Close-up High Quality (v3.5) — duração compatível com o modo "
                "de alta qualidade (limite de 1 min); foca em micro-movimentos faciais."
            )
        elif duration_min <= SINGING_MANUAL_LIMIT_MIN:
            alternativas.append(
                "Singing / High Quality (v3.5) — duração compatível com o limite "
                f"documentado no manual oficial ({SINGING_MANUAL_LIMIT_MIN:.1f} min) "
                "para qualidade Alta."
            )
    else:
        principal = (
            f"Faixa de {duration_min:.2f} min excede o limite prático de "
            f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} min confirmado para o modo Singing/Padrão."
        )
        avisos.append(
            "Duração acima do limite prático (5 min). Considere segmentar a faixa em "
            "partes menores e usar o módulo 'Mix Videos' do Talking Photos para uni-las "
            "após a geração de cada segmento."
        )

    return Recommendation(principal=principal, alternativas=alternativas, avisos=avisos)
