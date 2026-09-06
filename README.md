# TalkingPrep

Ferramenta de linha de comando (CLI) local que automatiza tudo que antecede o upload de uma
faixa musical no [Talking Photos AI](https://talkingphotos.ai) para geração de vídeos de
avatar cantando ("Singing Video"): separação vocal, limpeza/normalização do áudio,
análise técnica, e geração de uma ficha técnica com a configuração recomendada e sugestão
de prompt de avatar.

**O que esta ferramenta NÃO faz:** gerar vídeo, avatar ou imagem, nem se integrar
automaticamente com o Talking Photos (a plataforma não oferece API pública — o upload e a
geração continuam sendo feitos manualmente por você). Não há servidor, API, processo em
background ou agendador — é um comando que você roda sob demanda, e que termina sozinho.

---

## Instalação

### 1. Pré-requisitos de sistema

- **Python 3.10+**
- **ffmpeg** instalado e disponível no PATH do sistema (usado para corte de silêncio nas
  pontas e normalização de loudness).

  - **Windows:** `winget install ffmpeg` (ou baixe em https://ffmpeg.org/download.html e
    adicione ao PATH).
  - **macOS:** `brew install ffmpeg`

  Verifique com:
  ```
  ffmpeg -version
  ```

### 2. Ambiente Python

Crie e ative um ambiente virtual, depois instale as dependências:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

A separação vocal é feita pelo [Demucs](https://github.com/facebookresearch/demucs)
(modelo `htdemucs`), 100% em CPU — não é necessária GPU.

> **Importante — conexão com a internet na primeira execução:** na primeira vez que você
> rodar o TalkingPrep, o Demucs baixa automaticamente o modelo `htdemucs` (~80 MB) da
> internet. É necessário estar conectado nesse momento. Nas execuções seguintes, o modelo
> fica em cache local e a ferramenta funciona normalmente offline.

---

## Uso

```bash
python talkingprep.py --audio "Gocce_di_Noi.wav" --lyrics "letra.txt" --title "Gocce di Noi"
```

### Argumentos

| Argumento | Obrigatório | Descrição |
|---|---|---|
| `--audio` | Sim | Caminho do arquivo `.wav` de entrada (voz + instrumentos misturados). |
| `--lyrics` | Sim | Caminho do arquivo de texto (`.txt`/`.md`) com a letra da música. |
| `--title` | Não | Título da música. Default: nome do arquivo de áudio (sem extensão). |
| `--output-dir` | Não | Pasta de destino. Default: `output/` no diretório do projeto. |
| `--silence-threshold` | Não | Limiar em dB para detecção de silêncio/baixa energia. Default: `-40`. |

### Exemplo

```bash
python talkingprep.py \
  --audio "musicas/Gocce_di_Noi.wav" \
  --lyrics "letras/Gocce_di_Noi.txt" \
  --title "Gocce di Noi"
```

Ao final, o terminal imprime um resumo com a duração da faixa, avisos relevantes (ex.:
faixa muito longa ou muito curta) e o caminho da pasta de saída gerada.

---

## Estrutura da pasta de saída

Cada execução cria uma pasta própria em `output/<titulo>_<timestamp>/`, contendo:

```
output/
└── Gocce_di_Noi_20260906_130044/
    ├── Gocce_di_Noi_vocal_isolado.wav   # stem vocal, cortado nas pontas e normalizado
    ├── Gocce_di_Noi_instrumental.wav    # stem instrumental (referência)
    ├── Gocce_di_Noi_original.wav        # cópia do áudio original (referência)
    └── Gocce_di_Noi_ficha_tecnica.md    # ficha técnica completa
```

A **ficha técnica** (`*_ficha_tecnica.md`) contém:

- Nome da música e data de processamento.
- Metadados técnicos do áudio original (duração, taxa de amostragem, canais, bits).
- Resultado da análise de energia (trechos de baixa energia sinalizados, apenas informativo).
- Tabela de referência das regras do Talking Photos AI e a recomendação de
  categoria/engine/qualidade para a faixa processada.
- Sugestão de prompt de avatar (baseada na letra fornecida, com as diretrizes
  anti-"dancinha" da plataforma).
- Checklist manual dos passos que você ainda precisa fazer no Talking Photos.

---

## Regras de negócio do Talking Photos AI

Codificadas em `talkingprep/config.py` como tabela de referência:

| Categoria | Engine | Qualidade | Limite de duração por clipe |
|---|---|---|---|
| Human Video (Close-up) | 3.5 | Alta | Até 1 minuto |
| Human Video (Padrão) | 3.5 | Alta | Até 1 minuto |
| Human Video (Legada) | 3.0 | Padrão | Até 5 minutos |
| Fantasy/Animal | 3.5 | Alta | Até 1 minuto |
| Fantasy/Animal | 3.0 | Padrão | Até 5 minutos |
| Singing Video | 3.0 / 3.5 | Alta/Padrão | Até 3,5 minutos (manual) |

> **Nota:** o manual oficial documenta 3,5 minutos como limite da categoria Singing Video,
> mas o uso real e recorrente da plataforma confirma que o modo **"Singing normal"**
> (qualidade Padrão, engine 3.0) permite faixas de **até 5 minutos**, com tempo médio de
> processamento de ~15 minutos. O TalkingPrep usa 5 minutos como limite de referência
> prático nas recomendações e avisos; o valor do manual é mantido apenas como referência
> histórica/secundária na ficha técnica.

---

## Tratamento de erros e casos-limite

- **Arquivo de áudio ausente, corrompido ou não-WAV:** erro claro no terminal, execução
  interrompida com código de saída 1.
- **Faixa muito curta (< 5s):** aviso de que a análise de energia pode não ser útil;
  execução continua normalmente.
- **Faixa acima de 5 minutos:** aviso sugerindo segmentar a faixa e usar o módulo
  "Mix Videos" do Talking Photos; execução continua normalmente.
- **Letra ausente ou vazia:** a sugestão de prompt de avatar é gerada apenas com as
  diretrizes técnicas fixas (sem tema extraído da letra); a execução não é abortada.
- **ffmpeg não encontrado no PATH:** erro claro antes de iniciar o processamento.
- **Falha do Demucs (ex.: sem internet no primeiro uso):** erro claro reproduzindo a saída
  do Demucs e lembrando da necessidade de internet na primeira execução.
- **Falta de espaço em disco / falha de escrita:** erro claro, sem travamento silencioso.

---

## Estrutura do código

```
talkingprep.py              # ponto de entrada (python talkingprep.py ...)
talkingprep/
├── cli.py                  # argparse + orquestração do pipeline
├── config.py               # tabela de regras do Talking Photos AI
├── audio_analysis.py       # metadados WAV, envelope RMS, detecção de silêncio
├── audio_processing.py     # Demucs, corte de silêncio e normalização (ffmpeg)
├── lyrics.py                # leitura da letra e sugestão de prompt de avatar
├── recommendation.py       # lógica de recomendação de categoria/engine/qualidade
├── report.py                # geração da ficha técnica em Markdown
└── errors.py                 # exceções do pipeline
```

---

## Licença

Uso pessoal do autor do projeto.
