"""Geração da ficha técnica específica de dueto, em texto simples (Seção 11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import DUET_DURATION_TOLERANCE_SEC, SINGING_PRACTICAL_LIMIT_MIN

_BAR = "=" * 70
_SEP = "-" * 70


@dataclass
class DuetDurationCheck:
    duration_a_sec: float
    duration_b_sec: float
    mismatched: bool
    diff_sec: float


def check_duration_match(
    duration_a_sec: float,
    duration_b_sec: float,
    tolerance_sec: float = DUET_DURATION_TOLERANCE_SEC,
) -> DuetDurationCheck:
    diff = abs(duration_a_sec - duration_b_sec)
    return DuetDurationCheck(
        duration_a_sec=duration_a_sec,
        duration_b_sec=duration_b_sec,
        mismatched=diff > tolerance_sec,
        diff_sec=diff,
    )


def build_duet_report(
    *,
    title: str,
    vocal_filename_a: str,
    vocal_filename_b: str,
    duration_check: DuetDurationCheck,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        _BAR,
        f"FICHA DE DUETO -- {title}",
        _BAR,
        "",
        f"Data de processamento: {now}",
        "",
        "Este arquivo explica, passo a passo, o que fazer no Talking Photos AI para",
        "montar o vídeo de dueto a partir das duas faixas processadas por este",
        "programa. Leia também a ficha técnica individual de cada faixa (dentro das",
        "subpastas 'faixa_a' e 'faixa_b'), que traz a recomendação de configuração e",
        "a sugestão de prompt de avatar específicas de cada cantor.",
        "",
        _SEP,
        "VERIFICAÇÃO DE DURAÇÃO ENTRE AS DUAS FAIXAS",
        _SEP,
        "",
        f"- Duração da Faixa A (processada): {duration_check.duration_a_sec:.2f} segundos "
        f"({duration_check.duration_a_sec / 60:.2f} min)",
        f"- Duração da Faixa B (processada): {duration_check.duration_b_sec:.2f} segundos "
        f"({duration_check.duration_b_sec / 60:.2f} min)",
        f"- Diferença entre as duas: {duration_check.diff_sec:.2f} segundos",
        "",
    ]

    if duration_check.mismatched:
        lines += [
            "AVISO IMPORTANTE -- AS DURAÇÕES NÃO BATEM:",
            f"As duas faixas processadas têm uma diferença de {duration_check.diff_sec:.2f} "
            "segundos entre si. Isso é maior do que o esperado e PODE fazer com que os",
            "dois vídeos gerados separadamente saiam dessincronizados na montagem final",
            "(um cantor terminando antes ou depois do outro).",
            "",
            "O que fazer antes de continuar:",
            "  1. Volte às faixas de áudio originais (Áudio A e Áudio B) e confira, ouvindo",
            "     as duas, se elas realmente começam e terminam nos mesmos momentos da",
            "     música.",
            "  2. Se uma das faixas tiver sido cortada, editada ou exportada com duração",
            "     diferente por engano, corrija-a e rode este programa novamente.",
            "  3. Se a diferença for pequena e esperada (por exemplo, um pequeno silêncio",
            "     extra no início de uma das faixas), você pode prosseguir, mas preste",
            "     atenção especial à sincronização ao assistir aos dois vídeos prontos,",
            "     antes de finalizar a montagem.",
            "",
        ]
    else:
        lines += [
            "As durações das duas faixas processadas estão dentro da tolerância esperada "
            f"({DUET_DURATION_TOLERANCE_SEC:.1f}s). Nenhuma ação adicional é necessária "
            "quanto a isso.",
            "",
        ]

    lines += [
        _SEP,
        "PASSO 1 -- RENDERIZAR O VÍDEO DO CANTOR A",
        _SEP,
        "",
        "1. No Talking Photos AI, inicie a criação de um novo vídeo.",
        f"2. Envie (faça upload d)o arquivo de áudio '{vocal_filename_a}', que está na",
        "   subpasta 'faixa_a' desta pasta de saída. Este já é o áudio vocal isolado,",
        "   cortado nas pontas e normalizado -- não use o áudio original nem o",
        "   instrumental.",
        "3. Envie ou gere a Imagem A (o avatar do Cantor A), usando a sugestão de",
        "   prompt que está na ficha técnica individual dentro de 'faixa_a'.",
        "4. Selecione a categoria 'Singing Video' e escolha o modo indicado na ficha",
        "   técnica da Faixa A (engine e qualidade).",
        f"5. Confirme que a duração da Faixa A está dentro do limite prático de "
        f"{SINGING_PRACTICAL_LIMIT_MIN:.0f} minutos por render. Se ultrapassar, "
        "divida a faixa em partes menores antes de continuar.",
        "6. Confirme e inicie a geração (render) do vídeo do Cantor A. Aguarde a",
        "   conclusão antes de seguir para o próximo passo.",
        "",
        _SEP,
        "PASSO 2 -- RENDERIZAR O VÍDEO DO CANTOR B",
        _SEP,
        "",
        "Repita exatamente o mesmo procedimento do Passo 1, mas usando os arquivos",
        "da Faixa B:",
        "",
        f"1. Envie o arquivo de áudio '{vocal_filename_b}', que está na subpasta",
        "   'faixa_b'.",
        "2. Envie ou gere a Imagem B (o avatar do Cantor B), usando a sugestão de",
        "   prompt da ficha técnica individual dentro de 'faixa_b'.",
        "3. Selecione a categoria 'Singing Video' e o modo indicado na ficha técnica",
        "   da Faixa B.",
        "4. Confirme e inicie a geração (render) do vídeo do Cantor B.",
        "",
        _SEP,
        "PASSO 3 -- ESCOLHER COMO MONTAR O VÍDEO FINAL DO DUETO",
        _SEP,
        "",
        "Depois de ter os dois vídeos prontos (o do Cantor A e o do Cantor B), você",
        "precisa escolher UM dos dois métodos abaixo para juntá-los em um único vídeo",
        "de dueto. Leia as duas opções antes de decidir.",
        "",
        "OPÇÃO (a) -- TELAS ALTERNADAS, dentro do próprio Talking Photos:",
        "  1. Abra o módulo 'Mix Videos' do Talking Photos AI (não temos certeza do",
        "     nome exato deste botão/menu na versão atual da interface, mas é o",
        "     módulo documentado no manual da plataforma para combinar vídeos).",
        "  2. Importe o vídeo do Cantor A e o vídeo do Cantor B para dentro deste",
        "     módulo.",
        "  3. Monte a sequência alternando entre o vídeo do Cantor A e o vídeo do",
        "     Cantor B, seguindo a estrutura da música -- por exemplo: Cantor A na",
        "     primeira estrofe, Cantor B no refrão, e assim por diante, de acordo com",
        "     quem está cantando em cada trecho.",
        "  4. Exporte o vídeo final combinado a partir do próprio Talking Photos.",
        "  Use esta opção se você quer uma edição simples, sem precisar de outro",
        "  programa, mostrando um cantor de cada vez na tela.",
        "",
        "OPÇÃO (b) -- COMPOSIÇÃO LADO A LADO, em um editor de vídeo externo:",
        "  1. Baixe os dois vídeos prontos (Cantor A e Cantor B) do Talking Photos.",
        "  2. Abra um editor de vídeo externo à sua escolha -- por exemplo CapCut,",
        "     Adobe Premiere ou DaVinci Resolve.",
        "  3. Crie um novo projeto e importe os dois vídeos.",
        "  4. Divida a tela em duas partes (lado a lado, ou uma em cima e outra",
        "     embaixo) e posicione um vídeo em cada metade.",
        "  5. Alinhe os dois vídeos no tempo, usando a mesma marca de início da",
        "     música nas duas faixas de áudio originais como referência.",
        "  6. Não é necessário editar manualmente quem aparece cantando em cada",
        "     momento: como cada áudio já tem silêncio nos trechos em que aquele",
        "     cantor não canta, o avatar correspondente ficará de boca fechada",
        "     automaticamente nesses momentos, enquanto o outro avatar canta do lado",
        "     oposto do quadro.",
        "  7. Exporte o vídeo final combinado a partir do editor externo.",
        "  Use esta opção se você quer os dois cantores visíveis ao mesmo tempo,",
        "  lado a lado, durante o vídeo inteiro.",
        "",
        "Se você não tiver certeza de qual opção escolher, a Opção (a) é mais simples",
        "e não exige instalar nenhum programa além do próprio Talking Photos; a",
        "Opção (b) dá mais controle visual, mas exige um editor de vídeo externo.",
        "",
    ]

    return "\n".join(lines)
