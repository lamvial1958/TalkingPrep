# TalkingPrep — Especificação do Projeto

## Para o Claude Code

Este arquivo é a especificação completa do projeto. Leia-o integralmente antes de escrever qualquer código. O objetivo é construir uma ferramenta de linha de comando (CLI) local, não um serviço em nuvem, não uma API, não um processo residente. É executada sob demanda pelo usuário.

**Princípio transversal, obrigatório em todo o projeto:** o usuário é iniciante na parte técnica/operacional deste fluxo. Toda ação manual que ele precisar executar fora da automação — qualquer passo dentro do Talking Photos, qualquer escolha de arquivo, qualquer decisão que dependa dele — deve ser descrita pela ficha técnica de saída de forma explícita, sequencial e sem pressupor conhecimento prévio. Isso vale para TODA saída de texto do TalkingPrep (fichas técnicas individuais, ficha de dueto, mensagens de aviso no terminal, README), não apenas para o checklist de dueto da Seção 11, onde esse padrão já foi aplicado como referência de nível de detalhe esperado. Nenhuma instrução deve dizer apenas "configure conforme necessário" ou equivalente vago — cada passo deve dizer exatamente onde clicar/o que selecionar/o que digitar, na medida em que a informação for conhecida (baseada no manual do Talking Photos já fornecido). Onde a especificação exata de uma tela da plataforma não for conhecida com certeza, o texto deve dizer isso abertamente, em vez de inventar um passo de interface não verificado.

**Formato de arquivo, obrigatório em todo o projeto:** toda e qualquer instrução gerada para o usuário em forma de arquivo (ficha técnica, ficha de dueto, ou qualquer outro documento de saída) deve ser salva em `.txt`, nunca em `.md`. Isso vale mesmo quando o conteúdo é estruturado em seções/checklists — usar formatação em texto simples (ex.: títulos em maiúsculas ou sublinhados com `---`, listas com `-` ou números, sem sintaxe Markdown como `#`, `**`, `` ` ``) em vez de sintaxe Markdown, já que o arquivo não será renderizado como Markdown.

---

## 1. Propósito do Projeto

O usuário produz músicas autorais, de qualquer gênero, e usa a plataforma comercial **Talking Photos AI** (assinatura paga, já ativa) para gerar vídeos de avatar cantando essas músicas ("Singing Video"). O gargalo do fluxo atual é manual: preparar o áudio (a faixa exportada do Suno vem com voz + instrumentos misturados) e decidir a configuração correta na plataforma a cada nova música.

**TalkingPrep automatiza tudo que antecede o upload no Talking Photos** — nunca a geração do vídeo em si. O Talking Photos continua sendo a ferramenta de renderização final, por decisão deliberada (é especializada, rápida — ~15 min para até 5 min de vídeo em qualidade "Singing normal" — e o usuário já paga por ela). Não construir, sob nenhuma circunstância, um substituto de geração de vídeo/avatar dentro deste projeto.

---

## 2. Escopo

### Dentro do escopo
- Separação vocal automática (isolar voz do instrumental).
- Limpeza e normalização do áudio vocal isolado.
- Análise técnica do áudio (duração, taxa de amostragem, canais, detecção de trechos de silêncio/baixa energia).
- Geração de uma ficha técnica de recomendação de configuração para o Talking Photos, com base nas regras documentadas na Seção 5.
- Geração de sugestões de prompt de avatar/imagem, com base na letra da música fornecida.
- Organização de todos os arquivos de saída em uma pasta única, pronta para o usuário abrir e usar.

### Fora do escopo (não implementar)
- Qualquer geração de vídeo, avatar ou imagem.
- Qualquer integração via API com o Talking Photos (a plataforma não oferece API pública conhecida; a interação é manual, feita pelo usuário).
- Servidor web, API REST, processo em background, agendador (cron/daemon) ou qualquer forma de execução contínua.
- Upload automático de arquivos para qualquer serviço externo.
- Clonagem de voz, geração de TTS, ou qualquer forma de criação de áudio a partir de texto.

---

## 3. Arquitetura

- **Tipo:** CLI Python, executado localmente via terminal.
- **Modelo de execução:** sob demanda. O usuário roda o comando toda vez que tiver uma nova faixa. Nenhum processo deve continuar rodando após a conclusão do comando.
- **Persistência de estado:** nenhuma exigida entre execuções. Cada execução é independente. Não criar banco de dados.
- **Plataforma-alvo:** ambiente local do usuário (a especificar pelo Claude Code as dependências de sistema operacional; assumir Windows ou macOS como alvo principal, já que é onde o usuário provavelmente vai rodar isso — perguntar ao usuário se não houver certeza).
- **Interface gráfica local (adendo):** o usuário confirmou querer um ponto de entrada mais amigável do que digitar o comando no terminal — um ícone no desktop e uma tela de resultados legível. Isso é permitido desde que não mude a natureza do projeto: continua sendo um programa local, sob demanda, sem servidor, sem API, sem processo residente. A janela é aberta pelo usuário, roda o mesmo pipeline por baixo, mostra o resultado, e fecha — nada continua rodando em segundo plano depois que a janela é fechada.

---

## 4. Stack Técnica

- **Linguagem:** Python 3.10+
- **Separação vocal:** biblioteca `demucs` (modelo `htdemucs`, modo `--two-stems=vocals`). Validado como funcional em ambiente CPU-only (sem GPU), com desempenho aproximado de 1,2x o tempo real de áudio (uma faixa de 3 minutos leva ~3-4 minutos para processar). Não assumir GPU disponível; a ferramenta deve funcionar 100% em CPU.
- **Manipulação/análise de áudio:** `numpy` + módulo `wave` da biblioteca padrão (já validado) para leitura de metadados e cálculo de envelope RMS. Usar `ffmpeg` (via `subprocess` ou biblioteca `pydub`) para corte de silêncio nas pontas e normalização de loudness (padrão sugerido: normalização de pico ou LUFS, o que for mais simples de implementar de forma confiável).
- **Interface:** CLI com biblioteca `argparse` (evitar dependências pesadas de CLI framework, não é necessário).
- **Interface gráfica opcional:** `tkinter` (biblioteca padrão do Python, sem dependência extra) para uma janela local simples com seletor de arquivos e tela de resultado, acessível via ícone no desktop. É uma camada fina sobre o mesmo pipeline da CLI — não substitui a CLI, que continua funcionando normalmente. Nenhum framework web, servidor local ou processo residente.

---

## 5. Regras de Negócio — Talking Photos AI

Estas regras vêm do manual oficial da plataforma e devem ser codificadas como uma tabela de referência interna (dicionário/config, não hardcoded espalhado pelo código):

| Categoria | Engine | Qualidade | Limite de duração por clipe |
|---|---|---|---|
| Human Video (Close-up) | 3.5 | Alta | Até 1 minuto |
| Human Video (Padrão) | 3.5 | Alta | Até 1 minuto |
| Human Video (Legada) | 3.0 | Padrão | Até 5 minutos |
| Fantasy/Animal | 3.5 | Alta | Até 1 minuto |
| Fantasy/Animal | 3.0 | Padrão | Até 5 minutos |
| Singing Video | 3.0 / 3.5 | Alta/Padrão | Até 3,5 minutos |

**Correção confirmada pelo usuário (substitui o valor do manual para esta regra):** o manual documenta 3,5 minutos como limite da categoria Singing Video, mas o usuário confirmou, por uso real e recorrente da plataforma, que o modo **"Singing normal"** (qualidade Padrão, engine 3.0) permite faixas de **até 5 minutos**, com tempo médio de processamento de ~15 minutos. Use **5 minutos** como limite de referência para o modo Singing/Padrão na lógica de recomendação e nos avisos de duração, não os 3,5 minutos do manual. Mantenha o valor do manual (3,5 min) documentado apenas como referência histórica/secundária na ficha técnica, com nota indicando que a prática observada diverge do documento oficial. Não é necessário tratar isso mais como ambiguidade em aberto.

**Diretrizes anti-"dancinha" (para as sugestões de prompt de avatar):**
- Incluir no prompt de imagem: `front view, still pose, studio portrait, looking directly at camera, neutral background`.
- Recomendar enquadramento em close-up (rosto), evitando ombros/braços visíveis, pois mais corpo visível aumenta movimentação física indesejada.
- Recomendar o modo "Singing / Close-up High Quality (v3.5)" quando a duração permitir, por focar a animação em micro-movimentos faciais.

**Diretriz de limpeza de áudio para lip-sync:**
- A IA sincroniza os lábios com base no espectro de frequência do áudio. Áudio com instrumentos na mesma faixa de frequência da voz humana causa erros de sincronização.
- Por isso a separação vocal (Demucs) é etapa obrigatória do pipeline, não opcional.

---

## 6. Pipeline Funcional (passo a passo)

1. **Entrada:** o usuário fornece um arquivo `.wav` e um arquivo de texto (`.txt` ou `.md`) com a letra da música. Opcionalmente, um título da música (se não fornecido, usar o nome do arquivo de áudio sem extensão).

2. **Validação de entrada:**
   - Confirmar que o arquivo de áudio existe e é um `.wav` válido e legível.
   - Extrair metadados: duração, taxa de amostragem, canais, profundidade de bits.
   - Se a duração ultrapassar 5 minutos (limite prático confirmado pelo usuário para o modo Singing normal), emitir aviso claro na saída (não bloquear a execução) informando que pode ser necessário segmentar a faixa e usar o módulo "Mix Videos" do Talking Photos posteriormente.

3. **Análise de energia do áudio:**
   - Calcular envelope RMS em janelas de 1 segundo (método já validado nesta conversa).
   - Identificar e listar trechos com nível abaixo de um limiar (sugestão inicial: -40 dB) como candidatos a silêncio/introdução instrumental/pausa.
   - Essa informação entra na ficha técnica como alerta informativo, não como ação automática de corte (o corte de silêncio nas pontas, sim, pode ser automático — ver item 4; cortes no meio da faixa não devem ser automáticos, pois podem remover partes musicais intencionais).

4. **Processamento de áudio:**
   - Rodar Demucs (`--two-stems=vocals`, modelo `htdemucs`) sobre o arquivo de entrada.
   - Do resultado, pegar o stem `vocals.wav`.
   - Cortar silêncio nas pontas (início/fim) do stem vocal isolado — apenas nas pontas, nunca no meio.
   - Normalizar o volume do stem vocal (padronizar loudness de saída, para consistência entre faixas diferentes).
   - Salvar o resultado final como `<nome_da_faixa>_vocal_isolado.wav`.

5. **Geração de sugestões de prompt de avatar:**
   - Ler o arquivo de letra fornecido.
   - Gerar um bloco de texto com sugestão de prompt de imagem/avatar, combinando: (a) tema/imagética extraída da letra (ex.: chuva, mãos, intimidade — no caso da faixa de teste "Gocce di Noi"), com (b) as diretrizes técnicas fixas anti-"dancinha" da Seção 5.
   - Este passo pode ser um template simples preenchido com palavras-chave extraídas da letra (não é necessário machine learning; extração por palavras-chave ou até input manual do usuário sobre "tema visual desejado" é aceitável — decidir a abordagem mais simples e confiável).

6. **Geração da ficha técnica final** (arquivo `.txt`, texto simples, sem sintaxe Markdown, dentro da pasta de saída), contendo:
   - Nome da música, data de processamento.
   - Metadados técnicos do áudio original.
   - Resultado da análise de energia (trechos sinalizados).
   - Recomendação de categoria/engine/qualidade, com a ressalva de ambiguidade da Seção 5 explicitada.
   - Sugestão de prompt de avatar.
   - Checklist manual dos passos que o usuário ainda precisa fazer no Talking Photos (upload do áudio vocal isolado, escolha do modo, geração/upload do avatar, render).

7. **Empacotamento de saída:**
   - Criar uma pasta por execução, nomeada `<nome_da_faixa>_<timestamp>` ou similar.
   - Dentro dela: o áudio vocal isolado, a ficha técnica, e opcionalmente o instrumental isolado (`no_vocals.wav`) e o áudio original, para referência.

---

## 7. Interface de Linha de Comando (exemplo esperado)

```
python talkingprep.py --audio "Gocce_di_Noi.wav" --lyrics "letra.txt" --title "Gocce di Noi"
```

Argumentos:
- `--audio` (obrigatório): caminho do arquivo `.wav`.
- `--lyrics` (obrigatório): caminho do arquivo de texto com a letra.
- `--title` (opcional): título da música. Default: nome do arquivo de áudio.
- `--output-dir` (opcional): pasta de destino. Default: pasta `output/` no diretório do projeto.
- `--silence-threshold` (opcional): limiar em dB para detecção de silêncio. Default: -40.

Ao final da execução, imprimir no terminal um resumo claro: duração da faixa, avisos relevantes, caminho da pasta de saída gerada.

---

## 8. Tratamento de Erros e Casos-Limite

- Arquivo de áudio corrompido ou formato não suportado (não-WAV): erro claro, não travar silenciosamente.
- Faixa muito curta (ex.: menos de 5 segundos): avisar que pode não haver conteúdo suficiente para análise de energia útil.
- Demucs sem conexão à internet no primeiro uso (o modelo é baixado na primeira execução): avisar isso claramente ao usuário na documentação do projeto (README), já que requer internet ao menos uma vez.
- Falta de espaço em disco: capturar erro de escrita e informar mensagem clara, não travar sem explicação.
- Letra vazia ou arquivo de letra ausente: seguir em frente sem a sugestão de prompt de avatar, avisando que essa etapa foi pulada, em vez de abortar todo o processo.

---

## 9. Critérios de Aceitação (Definition of Done)

- [ ] Rodar o comando com a faixa `Gocce_di_Noi.wav` (fornecida como caso de teste real) e a letra correspondente produz uma pasta de saída completa e correta.
- [ ] O áudio vocal isolado gerado está audivelmente livre (ou majoritariamente livre) de instrumentos.
- [ ] A ficha técnica reflete corretamente a duração real da faixa e aplica a tabela de regras da Seção 5 sem inventar informação não documentada.
- [ ] A ferramenta funciona sem GPU.
- [ ] Nenhum processo permanece em execução após o comando terminar.
- [ ] README do projeto explica claramente: instalação (dependências, incluindo `ffmpeg` como dependência de sistema), uso, e a ressalva de que o download do modelo Demucs exige internet na primeira execução.
- [ ] Rodar o comando em modo `--duet` com duas faixas de teste produz duas pastas de saída corretas, detecta corretamente divergência de duração entre elas (testar com faixas de duração propositalmente diferentes), e gera a `ficha_dueto.md` com o checklist completo e compreensível.
- [ ] Toda instrução dirigida ao usuário em qualquer saída do TalkingPrep (ficha técnica, ficha de dueto, mensagens de terminal, README) é sequencial, explícita, e não usa formulações vagas como "configure conforme necessário" — conforme o Princípio Transversal descrito na abertura deste documento.

---

## 10. Fora de Discussão

Não sugerir, em nenhuma iteração futura deste projeto, a construção de um pipeline de geração de vídeo/avatar como substituto do Talking Photos, a menos que o usuário explicitamente reabra essa discussão. Essa decisão já foi tomada e justificada (qualidade e velocidade da ferramenta comercial superam qualquer alternativa open-source viável nas condições de hardware disponíveis).

---

## 11. Modo Dueto (Duet Mode)

### Pré-requisito de entrada

O usuário deve fornecer DUAS faixas de áudio já separadas por cantor, seguindo o Passo 1 do fluxo de dueto documentado no manual do Talking Photos: Áudio A (voz do Cantor 1, com silêncio nos trechos do Cantor 2) e Áudio B (voz do Cantor 2, com silêncio nos trechos do Cantor 1). Essa separação por cantor é responsabilidade do usuário na etapa de composição/geração musical, e não deve ser tentada automaticamente pelo TalkingPrep.

Fora de escopo, explicitamente: qualquer tentativa de detectar automaticamente "quem está cantando quando" dentro de uma única faixa mista de dois cantores. Não implementar, nem como experimento.

### Interface de linha de comando

Adicionar um modo dueto ativado por flag, com os seguintes argumentos:
- `--duet` (ativa o modo)
- `--audio-a` (obrigatório em modo dueto)
- `--audio-b` (obrigatório em modo dueto)
- `--lyrics-a` (opcional)
- `--lyrics-b` (opcional)
- `--title` (opcional, nome do dueto)

### Pipeline em modo dueto

Rodar o pipeline padrão (separação vocal via Demucs, limpeza, normalização, análise de energia) de forma independente para a Faixa A e a Faixa B, gerando uma pasta de saída para cada, dentro de uma pasta pai única do dueto.

Validação obrigatória: comparar a duração das duas faixas processadas. Se divergirem, emitir aviso destacado na ficha técnica, pois isso compromete a sincronização entre os dois vídeos na montagem final.

### Ficha técnica específica de dueto

Gerar, além das duas fichas técnicas individuais, um arquivo adicional (`ficha_dueto.txt`, texto simples, sem sintaxe Markdown) com um checklist manual, passo a passo, redigido em linguagem direta e sem pressupor conhecimento técnico prévio do usuário, cobrindo:

1. Renderizar o vídeo do Cantor A no Talking Photos usando a Imagem A + o áudio vocal isolado da Faixa A (respeitando o limite prático de 5 minutos por render).
2. Renderizar o vídeo do Cantor B no Talking Photos usando a Imagem B + o áudio vocal isolado da Faixa B.
3. Escolher UM dos dois métodos de montagem final e explicar as duas opções com clareza:
   - **(a) Telas Alternadas:** importar os dois vídeos no módulo "Mix Videos" do próprio Talking Photos e alternar a sequência entre Cantor A e Cantor B conforme a estrutura da música.
   - **(b) Composição Lado a Lado:** importar os dois vídeos em um editor externo (CapCut, Premiere ou DaVinci Resolve) e dividir a tela; quando um cantor estiver em silêncio na própria faixa, o avatar dele permanecerá de boca fechada automaticamente, enquanto o outro canta do lado oposto do quadro.

Esse checklist deve ser o mais explícito possível: o usuário não deve precisar deduzir nenhum passo por conta própria — ver o Princípio Transversal na abertura deste documento, que rege o nível de detalhe exigido em toda saída de texto do TalkingPrep, não apenas neste checklist.
