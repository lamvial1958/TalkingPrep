"""Leitura da letra e geração de sugestão de prompt de avatar (Seção 6, item 5)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .config import ANTI_DANCINHA_GUIDELINES, ANTI_DANCINHA_PROMPT_TAGS

# Stopwords combinadas (português, italiano, inglês) — cobre os idiomas mais prováveis
# das letras do usuário sem precisar de detecção de idioma.
_STOPWORDS = {
    # português
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "uma", "para", "com",
    "não", "os", "as", "no", "na", "nos", "nas", "por", "mais", "como", "mas",
    "ao", "aos", "à", "às", "se", "eu", "tu", "ele", "ela", "nós", "vós", "eles",
    "elas", "meu", "minha", "teu", "tua", "seu", "sua", "é", "foi", "ser", "está",
    "são", "só", "já", "vai", "vou", "me", "te", "lhe", "nos", "essa", "esse",
    "isso", "aquele", "aquela", "quando", "onde", "porque", "sem", "sobre", "até",
    # italiano
    "di", "la", "il", "che", "e", "un", "una", "per", "con", "non", "gli", "le",
    "nel", "nella", "sono", "sei", "è", "ma", "come", "più", "mio", "mia", "tuo",
    "tua", "suo", "sua", "noi", "voi", "loro", "questo", "questa", "quello",
    "quella", "quando", "dove", "perché", "senza", "su", "anche", "ancora",
    # inglês
    "the", "a", "an", "of", "and", "to", "in", "is", "it", "you", "i", "on",
    "for", "with", "not", "are", "was", "were", "be", "this", "that", "my",
    "your", "his", "her", "their", "our", "we", "they", "he", "she", "so",
    "just", "but", "or", "as", "at", "by", "from", "all", "if", "when",
}

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")


def load_lyrics(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return text or None


def extract_keywords(text: str, top_n: int = 6) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    words = [w for w in words if len(w) > 3 and w not in _STOPWORDS]
    counts = Counter(words)
    return [word for word, _ in counts.most_common(top_n)]


def generate_avatar_prompt_suggestion(title: str, lyrics_text: str | None) -> str:
    lines = []

    if lyrics_text:
        keywords = extract_keywords(lyrics_text)
        if keywords:
            theme = ", ".join(keywords)
            lines.append(
                f"Imagética extraída da letra de '{title}': {theme}."
            )
            lines.append(
                f"Prompt de imagem sugerido: retrato de avatar evocando {theme}, "
                f"{ANTI_DANCINHA_PROMPT_TAGS}."
            )
        else:
            lines.append(
                f"Não foi possível extrair palavras-chave temáticas da letra fornecida. "
                f"Prompt de imagem sugerido (apenas diretrizes técnicas): "
                f"{ANTI_DANCINHA_PROMPT_TAGS}."
            )
    else:
        lines.append(
            "Etapa de sugestão temática pulada: nenhuma letra válida foi fornecida. "
            f"Prompt de imagem sugerido (apenas diretrizes técnicas): "
            f"{ANTI_DANCINHA_PROMPT_TAGS}."
        )

    lines.append("")
    lines.append("Diretrizes adicionais (anti-\"dancinha\"):")
    for guideline in ANTI_DANCINHA_GUIDELINES:
        lines.append(f"- {guideline}")

    return "\n".join(lines)
