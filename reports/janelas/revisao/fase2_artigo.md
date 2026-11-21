# V4 / Fase 2 — Artigo `rp_ii` revisado pelo parecer

Arquivo editado: `../entrega_parcial/rp_ii/main.tex` (cópia do original do colega guardada fora do repositório
só para esta comparação). Tabelas `tab_*.tex` e figuras `fig_*.png` geradas por `scripts/35_figuras_artigo_v2.py`
(modo padrão `ARTIGO=rp_ii`; `ARTIGO=entrega3` regenera a 3ª entrega como estava). Números do texto em
`reports/janelas/artigo/numeros_artigo.csv` (chaves `v4.*`, com a tabela de origem); o arquivo antigo foi
preservado como `numeros_artigo_entrega3.csv`. `21_valida_latex.py`: 0 problemas (18 `\cite` / 18 `\bibitem`,
9 `\ref` / 9 `\label`); o validador passou a aceitar `\bibitem[rótulo]{chave}`.

## Título novo
Crimes e Sinistros de Trânsito nas Horas em torno dos Jogos de Futebol na Cidade de São Paulo: **Variação por
Janela** e Ganho Preditivo

## Resumo novo
Jogos de futebol reúnem dezenas de milhares de pessoas em horários previsíveis. Investigamos se as horas em
torno dos jogos de Corinthians, Palmeiras, São Paulo FC e Santos têm mais crimes violentos, roubos, furtos e
sinistros de trânsito com vítima na cidade de São Paulo e se a agenda de jogos, conhecida na véspera, melhora a
previsão dessas ocorrências. A unidade de análise é a hora (17.520 horas de 2022 e 2023), com as janelas PRÉ,
DURANTE e PÓS em torno de 216 jogos na capital e 301 jogos fora dela, a partir dos boletins da SSP-SP, do
Infosiga SP e do INMET. Em GLMs de Poisson com efeitos fixos de hora × dia da semana e hora × mês, nenhuma
janela teve variação significativa na cidade toda depois da correção para múltiplos testes, nem nos crimes nem
nos sinistros. A variação se concentra no entorno de 3 km dos estádios: em relação ao resto da cidade, os
furtos foram 71% maiores durante e depois da partida, nos boletins presenciais e nos online; os roubos e os
crimes violentos foram 43% e 36% maiores depois do jogo, mas só nos boletins online; e os sinistros com vítima
foram 47% maiores nas duas horas antes do jogo. Na previsão feita na véspera, o XGBoost foi o melhor modelo para
crimes e o GLM para sinistros, ambos melhores que o baseline, e as variáveis de jogo reduziram a deviance só nas
horas de jogo (13,9% para furtos no entorno), sem melhorar a detecção de horas de pico.

## Trechos alterados, por seção

### Introdução
- "Não encontramos estudo que, para São Paulo, meça o efeito dos jogos hora a hora..." → "Para São Paulo,
  roubos e furtos já foram medidos hora a hora em torno de jogos de futebol [Masiero 2022]. Falta um estudo que
  inclua os sinistros de trânsito e os jogos dos clubes da cidade disputados fora da capital, compare o entorno
  dos estádios com o resto da cidade separando o canal de registro do boletim e avalie o ganho preditivo da
  agenda de jogos, com dados de 2022 e 2023." (**muda o sentido**: deixa de reivindicar ineditismo do grão horário.)
- "efeito/aumenta" → "variação/associação" (ex.: "também aumenta o risco no trânsito" → "também se associa a
  mais risco no trânsito"). Objetivos (i)–(iv) mantidos literalmente.

### Trabalhos correlatos
- 2.1, Ge et al.: "É o estudo mais próximo do nosso em local e em dados" → removido (o mais próximo passa a ser Masiero).
- 2.2: parágrafo novo de Masiero (2022), só com o que o resumo afirma (nove anos, distritos policiais, 430
  partidas, queda de roubos durante, deslocamento para antes, sem deslocamento espacial, incapacitação
  voluntária, crime local maior no entorno). Menção na síntese (2.4) e linha na Tabela 1 com o texto pedido.
- 2.3, Ristea et al. (2020): "modelos de densidade de kernel para prever a distribuição espacial" → United
  Center (Bulls e Blackhawks, basquete e hóquei), densidade de kernel localizada como atributo de regressão
  logística com regularização L2, avaliada pela AUC de curvas de vigilância. Tabela 1: Método "Regressão
  logística com atributos de densidade de kernel, com e sem redes sociais".
- Parágrafo final de posicionamento: começa por "A variação hora a hora de roubos e furtos em São Paulo já foi
  medida"; o item (iv) antigo (controle do perfil horário) sai, porque o próprio Masiero e o painel horário já
  fazem isso; entra (i) entorno contra resto por canal do BO.
- Linha de Card e Dahl mantida ("testa a heterogeneidade por resultado e clássico"): há resultado utilizável de clássico.

### Metodologia (reescrita)
- **Dados**: motivo da janela (fim = base de jogos; início exclui 2020–2021, jogos sem público ou com público
  restrito pela pandemia), definições de crimes violentos e de sinistros totais, BO único, funil (971.698 →
  641.697 → 536.766 → 50.071 nos discos; sinistros 90.829 → 90.737 → 90.311 → 8.686), falhas do INMET (649 horas
  sem chuva; 34 sem temperatura saem).
- **Jogos**: "As 137 partidas do Brasileiro e da Copa do Brasil vêm de uma base pública... sem a conversão... 52
  dessas partidas cairiam no dia seguinte e 108 teriam o indicador de jogo noturno errado" → os 137 são mandos
  dos três clubes da capital (130 na capital, 7 em Barueri e na Vila Belmiro); só "os horários estão no fuso do
  Reino Unido e foram convertidos". Fonte dos jogos fora da capital e do público.
- **Janelas**: ponto médio fechado à esquerda (às 21h30 a hora das 21h já é DURANTE), prioridade DURANTE > PÓS >
  PRÉ, exclusões numa regra só (finais da Copinha e do Brasileirão Feminino, 5 jogos do Brasil na Copa de 2022).
- **Modelo**: hora × mês no modelo principal, justificado pelo pôr do sol e pela concentração dos jogos.
- **Entorno**: "comparamos as janelas dos jogos daquele estádio com as dos outros" → GLM binomial da fração no
  disco contra o resto da cidade (diferença em diferenças), empilhado com efeitos fixos por estádio, raio 1/2/5 km.
- **Bloco preditivo**: hiperparâmetros em nota de rodapé; frase de disponibilidade ("código e dados agregados
  disponíveis com os autores", sem link, como decidido).

### Resultados
- 4.1 (**muda o sentido**): "Nos jogos na capital, os crimes violentos subiram 4,7% e os roubos 5,3% na janela
  PRÉ (p_BH = 0,041)... robusto no GLM, pareado inconclusivo" → "nenhuma janela teve variação que sobrevivesse à
  correção... crimes violentos 2,9% maiores no PRÉ (p = 0,043; p_BH = 0,205)... como os roubos fazem parte dos
  crimes violentos, os dois resultados não são confirmações independentes". DURANTE: GLM −1,6% e pareado −6,8%
  apresentados como estimativas que não concordam. Sinal novo e não robusto: PRÉ dos jogos fora da capital −3,1%.
- 4.2 "PRÉ da cidade toda: efeito pequeno e em parte sazonal" (narrativa) → "Robustez": Tabela 3 nova e um
  parágrafo só com resultados; tercil de público em uma frase (+6,3% no maior, p = 0,009).
- 4.3 (**muda o sentido**): modelo de diferença em diferenças; furtos DURANTE+PÓS como resultado principal
  (+71%), com subtipos (veículo +124%, transeunte +112%, outros +34%); "o que indica concentração do crime no
  entorno, e não aumento geral" → o desenho não separa crime gerado de deslocado [Kurland]; canal online com o
  argumento novo (geocodificação do endereço digitado); DRADE = 7 BOs (BO único, sem pontos de acúmulo; antes "10",
  sem origem em CSV); **sinistros no entorno PRÉ (+47%) deixam de ser "exploratório" e passam pela régua**;
  lesão corporal DURANTE (+138%) aparece como contradita pelo pareado.
- 4.4: saem a frase do P95 como subconjunto, o Jaccard e a coluna κ P95; nenhuma janela sobrevive à correção
  (PRÉ de crimes RR 1,29, p = 0,059; P95 1,62, p_BH = 0,053); frase da robustez com hora × mês no esperado.
- 4.5: baseline na Tabela 6, explicação da prevalência 0,075, frase da PR-AUC baixa por construção, clima da véspera.
- 4.6: Tabela 7 do modelo novo; a correção de 2,12 sai: os furtos sem hora não seguem a distribuição dos com
  hora (razão de chances 1,33 nos dias de jogo) e o fator empírico é 5,0 (excesso diário de 7,1 furtos por jogo
  contra 1,4 só com hora).

### Discussão e conclusão
- 1º parágrafo (**muda o sentido**): "Na cidade como um todo, o jogo não aumenta a violência: o PRÉ de crimes
  violentos é pequeno e, em boa parte, sazonalidade..." e "DURANTE o jogo os crimes tendem a cair, como em
  Manchester" → "as horas em torno dos jogos não têm mais crimes nem mais sinistros depois da correção"; objetivos
  respondidos de novo, separados por domínio ((i) sinistros agora com variação no PRÉ do entorno; (ii) nenhuma
  janela em nenhum domínio).
- "Na previsão, o XGBoost supera o Prophet" → "o XGBoost foi o melhor modelo para crimes e o GLM para
  sinistros, ambos comparados ao baseline".
- Parágrafo novo: convergência com Masiero (entorno e tamanho do jogo); DURANTE não sustenta a queda de São
  Paulo e Manchester; heterogeneidade (clássico PRÉ +11,5%, p_BH = 0,030; resultado do mandante sem associação
  em crimes violentos).
- Apagado o parágrafo do GLM diário e do fuso ("Os resultados também mostram por que a unidade horária...").
- Limitações: de seis para oito (violência doméstica; shows nos estádios), mais o deslocamento não separável e a
  maior proporção de furtos sem hora nos dias de jogo; recomendação de policiamento suavizada.

## Tabelas e origem dos números
| Tabela | Arquivo | Origem (reports/janelas/) |
|---|---|---|
| 1 literatura | inline no `main.tex` (texto, sem números nossos) | — |
| 2 variação por janela | `tab_janelas.tex` | `revisao/{crimes,sinistros}/tabelas/vereditos.csv` |
| 3 robustez (nova) | `tab_robustez.tex` | `revisao/crimes/tabelas/`: `modelo_principal_e_robustez`, `vereditos`, `placebo_permutacao`, `controles_pareados`, `entorno_modelo_principal`, `entorno_sem_hora_mes`, `entorno_placebo`, `entorno_pareado`, `entorno_raio` |
| 4 canal | `tab_canal.tex` | `revisao/crimes/tabelas/entorno_canal.csv` (marca = p_BH < 0,05 na coluna) |
| 5a/5b pico | `tab_pico.tex` | `revisao/{dom}/pico_sem_hm/tabelas/pico_*.csv` (definição mantida, dados da V4) |
| 6 preditivo | `tab_preditivo.tex` | `{dom}/tabelas/fase3_{desempenho,ablacao,pico}_*.csv` (bloco não refeito) |
| 7 risco | `tab_risco.tex` | `revisao/crimes/tabelas/entorno_tabela_risco.csv` × fator de `entorno_furtos_sem_hora.csv` |

Cada número das tabelas e do texto tem uma chave `v4.*` (ou `jogos.*`, `inmet.*`, `cfg.*`) em
`numeros_artigo.csv`. Conferência automática: todo número do texto fora da Tabela 1 e das citações de outros
estudos está no CSV (sobram só ":00" e "percentil 90", que são definições).

## Estimativa de páginas (calibrada pela compilação real da 3ª entrega, ~585–625 palavras por página)
| Seção | Palavras | Floats | Estimativa | Limite |
|---|---|---|---|---|
| Título e resumo | 272 | — | ~0,7 | 1 |
| Introdução | 823 | — | ~1,4 | 2 |
| Correlatos | 1.255 | Tab. 1 | ~3,0 | 4 |
| Metodologia | 1.119 | nota de rodapé | ~1,9–2,0 | 2 (no limite) |
| Resultados | 1.612 | 6 tabelas, 2 figuras | ~5,6–5,9 | 6 (no limite) |
| Discussão e conclusão | 532 | — | ~0,9 | 1 |

Sem LaTeX local: a contagem real depende da compilação.
