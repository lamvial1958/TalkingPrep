"""Tabela de referência das regras de negócio do Talking Photos AI (Seção 5 do CLAUDE.md)."""

# Limite prático confirmado pelo usuário para o modo "Singing normal" (qualidade Padrão,
# engine 3.0), por uso real e recorrente da plataforma. Substitui o valor documentado
# no manual oficial (3,5 min) para fins de recomendação e avisos de duração.
SINGING_PRACTICAL_LIMIT_MIN = 5.0

# Valor documentado no manual oficial do Talking Photos AI para a categoria Singing Video.
# Mantido apenas como referência histórica/secundária, pois diverge da prática observada.
SINGING_MANUAL_LIMIT_MIN = 3.5

TALKING_PHOTOS_RULES = [
    {
        "categoria": "Human Video (Close-up)",
        "engine": "3.5",
        "qualidade": "Alta",
        "limite_duracao_min": 1.0,
    },
    {
        "categoria": "Human Video (Padrão)",
        "engine": "3.5",
        "qualidade": "Alta",
        "limite_duracao_min": 1.0,
    },
    {
        "categoria": "Human Video (Legada)",
        "engine": "3.0",
        "qualidade": "Padrão",
        "limite_duracao_min": 5.0,
    },
    {
        "categoria": "Fantasy/Animal (Alta)",
        "engine": "3.5",
        "qualidade": "Alta",
        "limite_duracao_min": 1.0,
    },
    {
        "categoria": "Fantasy/Animal (Padrão)",
        "engine": "3.0",
        "qualidade": "Padrão",
        "limite_duracao_min": 5.0,
    },
    {
        "categoria": "Singing Video",
        "engine": "3.0 / 3.5",
        "qualidade": "Alta/Padrão",
        "limite_duracao_min": SINGING_MANUAL_LIMIT_MIN,
        "nota": (
            f"Manual oficial documenta {SINGING_MANUAL_LIMIT_MIN} min como limite desta "
            f"categoria. Uso real e recorrente da plataforma pelo usuário confirma que o "
            f"modo 'Singing normal' (qualidade Padrão, engine 3.0) permite faixas de até "
            f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} min, com tempo médio de processamento de "
            f"~15 minutos. Use {SINGING_PRACTICAL_LIMIT_MIN:.0f} min como limite de "
            f"referência prático; o valor do manual é mantido apenas como referência "
            f"histórica/secundária."
        ),
    },
]

# Diretrizes anti-"dancinha" para sugestão de prompt de avatar/imagem (Seção 5).
ANTI_DANCINHA_PROMPT_TAGS = (
    "front view, still pose, studio portrait, looking directly at camera, "
    "neutral background"
)

ANTI_DANCINHA_GUIDELINES = [
    (
        "Enquadrar em close-up (rosto), evitando ombros/braços visíveis — mais corpo "
        "visível aumenta a movimentação física indesejada durante a animação."
    ),
    (
        "Quando a duração da faixa permitir (até 1 minuto), preferir o modo "
        "'Singing / Close-up High Quality (v3.5)', que foca a animação em "
        "micro-movimentos faciais."
    ),
]

# Limiar padrão (dBFS) para detecção de trechos de silêncio/baixa energia.
DEFAULT_SILENCE_THRESHOLD_DB = -40.0

# Duração mínima (segundos) abaixo da qual a análise de energia é considerada pouco útil.
MIN_USEFUL_DURATION_SEC = 5.0
