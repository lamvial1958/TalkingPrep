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
    # advérbios/pronomes genéricos comuns (italiano/português) que não carregam
    # imagética própria e por isso não devem virar "palavra-chave temática"
    "oggi", "ogni", "adesso", "sempre", "mai", "tutto", "tutti", "tutta",
    "tutte", "così", "molto", "meno", "bene", "male", "ecco", "qui", "qua",
    "prima", "poi", "cosa", "quindi", "allora", "então", "hoje", "cada",
    "agora", "sempre", "nunca", "tudo", "todos", "toda", "todas", "assim",
    "muito", "menos", "bem", "mal", "aqui", "ali", "antes", "depois",
}

# Rótulos de estrutura de composição (cabeçalhos de seção da letra, ex.: "STROFA 1
# (II TIPO)", "RITORNELLO", "PONTE") — não fazem parte do conteúdo poético e devem
# ser ignorados na extração de imagética, tanto a linha inteira quanto os termos.
_SECTION_LABEL_WORDS = {
    "strofa", "ritornello", "ponte", "finale", "coro", "verso", "refrao",
    "refrão", "bridge", "chorus", "outro", "intro", "precoro", "tipo", "misto",
    "estrofe", "estribilho", "introducao", "introdução",
}

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")
_HEADER_LINE_RE = re.compile(r"^[A-ZÀ-Ý0-9\s()/→\-]+$")


def _strip_section_headers(text: str) -> str:
    """Remove linhas que são cabeçalhos de estrutura (ex.: 'STROFA 1 (II TIPO)')."""
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and _HEADER_LINE_RE.match(stripped):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def load_lyrics(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return text or None


def extract_keywords(text: str, top_n: int = 6) -> list[str]:
    body_text = _strip_section_headers(text)
    words = [w.lower() for w in _WORD_RE.findall(body_text)]
    words = [
        w for w in words
        if len(w) > 3 and w not in _STOPWORDS and w not in _SECTION_LABEL_WORDS
    ]
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
