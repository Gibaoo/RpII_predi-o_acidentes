# Changelog

Registro cronológico das etapas do projeto. Cada entrada descreve **o que foi
feito**, **quais decisões foram tomadas e por quê** e **qual arquivo/resultado
foi produzido**. Datas no formato AAAA-MM-DD.

---

## 2026-09-03 — Reprodução do pipeline (Etapas 1–5) + correções

### O que foi feito
- Rodado o pipeline do zero (`data/` estava vazio, sem cache bronze):
  `01_ingestao.py` → `02_limpeza.py`.
- `01_ingestao.py`: convertidos os 4 semestres de `SPDadosCriminais_20{22,23}.xlsx`
  (2.440.033 linhas) para CSV via streaming openpyxl; cópias de futebol, INMET e
  Infosiga para `data/bronze/`.
- `02_limpeza.py`: geradas as 5 tabelas silver e o dataset gold.

### Decisões tomadas e por quê
- **Corrigido bug de nome de arquivo** em `01_ingestao.py::ingest_weather()`: o
  script procurava `INMET_..._SAO_PAULO_-_MIRANTE_...CSV` (underscores) mas os
  arquivos reais em `uploads/` usam espaços (`SAO PAULO - MIRANTE`). Sem a
  correção o pipeline não roda. Ajustado para o nome real.
- **`openpyxl` adicionado como dependência** (não estava instalado). É import
  direto de `01_ingestao.py`; documentado no `CLAUDE.md`.
- **Interpretador**: neste ambiente Windows é `python`, não `python3` — anotado
  no `CLAUDE.md` para reprodutibilidade.
- Nenhuma decisão metodológica nova: as regras das Etapas 1–5 (filtro `CD_IBGE`,
  mandantes SP-capital, colunas de futebol nulas em dia sem jogo, janela
  2022–2023) foram mantidas como já estavam.

### Resultado produzido
- `data/bronze/` (9 arquivos), `data/silver/` (5 tabelas).
- **`data/gold/fato_dia_sp.csv` = (730, 69)**, 2022-01-01 a 2023-12-31, 0 datas
  duplicadas, 0 dias sem registro de crime/acidente. Confere com a spec do
  `CLAUDE.md`.

---

## 2026-09-03 — Etapa 6: Análise Exploratória de Dados (EDA)

### O que foi feito
- Criado `scripts/03_eda.py` cobrindo os 4 blocos do roteiro §6: qualidade,
  estatística descritiva, distribuições e séries temporais. Nada é modelado.
- Confirmadas as lacunas conhecidas do INMET; identificados concretamente os dias
  anômalos nos extremos das contagens.

### Decisões tomadas e por quê
- **Escopo restrito a EDA descritiva**: testes de hipótese formais ficam para a
  Etapa 7; definição de "pico" para a Etapa 11. Evita antecipar decisão sem a
  análise que a fundamenta.
- **`tabulate` não usado**: helper `df_to_md` próprio para gerar tabelas markdown
  sem adicionar dependência.
- **Testes não-paramétricos serão o default na Etapa 7**: `normaltest` rejeita
  normalidade em quase todas as contagens (assimetria/curtose altas) → decisão de
  usar Mann-Whitney/Kruskal-Wallis adiante.
- **Nova limitação documentada** (não estava no `CLAUDE.md`): 2022-01-17
  (`acidentes_total`=7) e 2023-08-07 (=24) são segundas comuns sem feriado com
  `frac_com_vitima`≈1,0 (típico ≈0,65) — o fluxo `tipo_registro=NOTIFICACAO` da
  Infosiga não entrou nesses dias. É lacuna de registro da fonte, não queda real;
  tratar como missing, não zero. Adicionado ao `CLAUDE.md`.
- **Outlier 2022-06-19** (`furtos_total`=2633 vs mediana ~780): sinalizado como
  provável registro em lote, **não removido agora** — decisão de remoção fica
  para a Etapa 12 para não deixar 1 artefato dominar a definição de pico.
- **Censura de fim de série** (2023-12-30/31) confirmada como os 2 menores dias de
  `crimes_totais` sem feriado; pesa mais em crime que em acidente. Exclusão
  efetiva fica para a Etapa 15 (split).

### Resultado produzido
- `scripts/03_eda.py`
- `reports/eda/eda_report.md` (relatório completo)
- `reports/eda/figures/` — 13 figuras (séries temporais, histogramas, heatmaps
  dia×mês, ACF, correlação Pearson/Spearman)
- `reports/eda/tabelas/` — 9 CSVs (descritiva, missing, correlações, extremos,
  distribuição temporal mensal, média por dia da semana)
- `CLAUDE.md` atualizado: status "Etapas 1–6 concluídas", nova limitação Infosiga,
  próximos passos revisados.

---

## 2026-09-03 — Etapa 7: comparação dia com jogo vs dia sem jogo

### O que foi feito
- Criado `scripts/04_analise_jogo_vs_naojogo.py`.
- Comparação **bruta** com jogo vs sem jogo para 11 desfechos (6 de crime, 5 de
  acidente): média, mediana, diferença absoluta e %, IC 95% bootstrap (10 000
  reamostragens, semente 20260903), Mann-Whitney U (primário), t de Welch
  (secundário), effect sizes (Cliff's delta = r rank-biserial, Hedges' g),
  correção de Benjamini-Hochberg.
- Comparação **estratificada por dia da semana**.
- Associação **ajustada**: GLM Poisson com erros-padrão robustos HC1, controlando
  `C(dia_semana) + feriado + C(mes)`; reportado rate ratio `exp(coef)` com IC 95%.
- Recortes dentro dos dias de jogo: clássico vs comum; noturno vs diurno.
- Prévia D-1 / D0 / D+1 (Kruskal-Wallis) — a defasagem completa é a Etapa 9.

### Decisões tomadas e por quê
- **Mann-Whitney como teste primário** (t de Welch só secundário): a EDA rejeitou
  normalidade em quase todas as contagens.
- **Exclusão de dias com registro defeituoso** antes de testar: crime remove
  2023-12-30/31; acidente remove esses 2 + 2022-01-17 e 2023-08-07. São lacunas
  de registro identificadas na Etapa 6, não dias reais baixos — mantê-las
  enviesaria a comparação. 4 dias de 730, perda de potência desprezível.
- **Ajuste por Poisson/HC1 em vez de Binomial Negativa**: Poisson com EP robusto
  é consistente para o modelo da média mesmo sob sobredispersão, e é mais simples
  de defender; NB fica como alternativa (muda largura do IC, não a direção).
- **Controlar `C(mes)`** além de dia da semana: a temporada de futebol (abr-nov)
  não cobre o verão (dez-mar), que tem menos acidentes — sem esse controle o
  "efeito jogo" absorve efeito de calendário.
- **Benjamini-Hochberg** sobre os p-values: 11 desfechos testados; sem correção
  haveria inflação de falso-positivo.
- **Alto vs baixo público NÃO foi feito**: `publico` é 100% ausente. Declarado
  como pendente, sem proxy inventado (Regra 10).
- **Outlier 2022-06-19 mantido**: infla a sobredispersão de crimes_totais/
  furtos_total; teste de sensibilidade sem ele foi remetido à Etapa 12 (mesma
  decisão da EDA), para não misturar limpeza com análise aqui.
- **Síntese reescrita para refletir o resultado real**: as diferenças brutas
  (lesão corporal +15%, acidentes +6%, acidentes fatais +39%) **não sobrevivem ao
  ajuste** (todos p_BH > 0,5; maior resíduo = acidentes fatais RR 1,15, p=0,06
  sem BH). Conclusão honesta: associação fraca, majoritariamente explicada por
  dia da semana e mês; **não** se afirma causalidade (Regra 5).

### Resultado produzido
- `scripts/04_analise_jogo_vs_naojogo.py`
- `reports/etapa7/relatorio_jogo_vs_naojogo.md`
- `reports/etapa7/figures/` — 3 figuras (distribuição por grupo em crime e
  acidente; forest plot da associação ajustada)
- `reports/etapa7/tabelas/` — 13 CSVs (bruto, estratificado por dia da semana ×4,
  GLM ajustado, jogos por dia da semana, recortes clássico/noturno, prévia de
  lag ×4)
- Principais números: dia de jogo bruto → `lesao_corporal_dolosa` +14,9%
  (MW p_BH<0,001), `acidentes_total` +6,3% (p_BH=0,001), `acidentes_fatais`
  +38,7% (p_BH<0,001), `roubos_total` −3,3% (p_BH=0,03); **ajustado → nada
  significativo após BH** (acidentes_fatais RR 1,15, IC95 0,99–1,32).

---

## 2026-09-03 — Etapa 8: análise estatística

### O que foi feito
- Criado `scripts/05_analise_estatistica.py`.
- **Correlação zero-order** (Pearson + Spearman) driver × desfecho, com IC de
  Fisher, p-value e Benjamini-Hochberg — 44 pares (11 desfechos × 4 drivers:
  `tem_jogo_sp`, `numero_jogos_sp`, `classico`, `jogo_noturno`).
- **Correlação parcial** (Spearman): residualização OLS de desfecho e driver
  sobre os controles, correlação dos resíduos. Modelo A controla
  `C(dia_semana) + C(mes) + feriado`; modelo B adiciona `temp_media +
  precipitacao_total + umidade_media`.
- **Teste de proporções**: P(dia > P90 / P95) em jogo vs sem jogo — z de duas
  proporções + qui-quadrado + Fisher; RR, RD, OR com IC 95%.
- **Kruskal-Wallis + ANOVA** para fatores multi-nível (`dia_semana`,
  `numero_jogos_sp` 0/1/2, janela D-1/D0/D+1) com ε²/η² e post-hoc
  Mann-Whitney par a par com BH.
- Cada bloco declara H0, H1, estatística, p, effect size e interpretação
  (exigência do briefing §8).

### Decisões tomadas e por quê
- **Correlação parcial por resíduos de OLS** (não `pingouin`, não instalado):
  para a versão Spearman, residualizam-se as *ranks* de x e y — partial
  correlation baseada em posto, robusta a não-normalidade, mantendo só as
  bibliotecas do briefing.
- **Dois modelos de controle (A e B)** em vez de um: separar o efeito de
  calendário do efeito de clima; B roda no subconjunto com clima observado
  (n≈713) e reporta n_B.
- **Limiar de "dia alto" P90/P95 marcado como PROVISÓRIO**: a definição formal
  de pico é a Etapa 11; aqui é só um teste de proporções ilustrativo, sem
  controle de dia da semana — declarado explicitamente no relatório.
- **Post-hoc de `dia_semana` movido só para CSV** (21 pares × 7 desfechos =
  ruído no relatório); no markdown ficam só os fatores ligados a futebol.
- **BH aplicado dentro de cada família de testes** (zero-order, parcial A,
  parcial B, proporções, KW) — não um BH global, que misturaria hipóteses de
  natureza diferente.
- **Síntese escrita de forma conclusiva** (não "verificar quais permanecem"):
  o resultado é inequívoco e deve ser reportado como tal.

### Resultado produzido
- `scripts/05_analise_estatistica.py`
- `reports/etapa8/relatorio_analise_estatistica.md`
- `reports/etapa8/figures/` — 3 figuras (atenuação zero-order→parcial para
  `tem_jogo_sp` e `numero_jogos_sp`; barras de proporção P90 jogo vs sem jogo)
- `reports/etapa8/tabelas/` — 5 CSVs (zero-order, parcial, proporções,
  Kruskal/ANOVA, post-hoc completo)
- **Resultado central:** dos 44 pares, 8 são significativos na correlação
  simples (|rho| 0,11–0,19) e **0 sobrevivem ao controle de calendário**
  (todos p_BH > 0,8). `lesao_corporal_dolosa`×`tem_jogo_sp`: rho 0,19 → 0,03;
  `acidentes_fatais`: 0,17 → 0,06; `acidentes_total`: 0,13 → 0,01. Kruskal-Wallis:
  `dia_semana` ε² = 0,16–0,41 (grande) vs `numero_jogos_sp` ε² = 0,006–0,015
  (desprezível). Conclusão: associação bruta jogo×desfecho é explicada por
  calendário; dados não sustentam efeito do jogo em si; sem causalidade (Regra 5).

---

## 2026-09-03 — Etapa 9: análise de defasagem temporal (D-2..D+2)

### O que foi feito
- Criado `scripts/06_analise_defasagem.py`.
- **Modelo de defasagens distribuídas** (inferência principal): GLM Poisson
  `y ~ jogo[D-2]+jogo[D-1]+jogo[D0]+jogo[D+1]+jogo[D+2] + C(dia_semana) +
  C(mes) + feriado`, HC1 — rate ratio por defasagem, IC 95%, BH sobre 6
  desfechos × 5 defasagens.
- **Correlação cruzada (CCF)** −14..+14 sobre séries **dessazonalizadas**
  (resíduo de OLS ~ `C(dia_semana)+C(mes)+feriado`) do indicador de jogo e do
  desfecho, com banda ±1,96/√n.
- **Event study**: média do resíduo dessazonalizado nos offsets −7..+7 em torno
  de cada jogo, para todos os jogos e para jogos "isolados" (sem outro jogo em
  ±3 d); teste t vs 0 em D-1/D0/D+1.
- **Kruskal-Wallis nos resíduos** por janela (D-2..D+2 vs baseline sem jogo em
  ±2 d) com ε².

### Decisões tomadas e por quê
- **Convenção de sinal** (⚠️ a descrição desta linha estava ERRADA na versão
  original desta entrada — ver correção de 2026-09-04 abaixo). O que a seção 1
  do código realmente calcula: coluna rotulada "D-1" = `tem_jogo_sp.shift(1)` =
  "houve jogo ontem" = **igual a `jogo_d_menos_1` do gold**; "D+1" =
  `shift(-1)` = "há jogo amanhã" = `jogo_d_mais_1` do gold. Ou seja, a seção 1
  já estava na convenção do gold; o texto (H0, cabeçalho, síntese) e a seção 4
  é que descreviam/rotulavam ao contrário.
- **Lags construídos na série diária completa (730 d) antes das exclusões**: os
  4 dias excluídos continuam existindo como linhas para o `shift` cruzar as
  bordas corretamente; só saem da amostra de estimação.
- **Dessazonalização antes da CCF**: uma CCF crua entre jogo e desfecho só
  mostraria a estrutura semanal comum às duas séries (lição das Etapas 7–8).
  Residualizar em `C(dia_semana)+C(mes)+feriado` isola o que sobra.
- **Inferência firme = seção 1 (modelo distribuído), CCF e event study como
  exploratórios**: a CCF sobre resíduos ainda tem autocorrelação residual que
  infla a banda; pré-branqueamento ARIMA completo foi citado como refinamento,
  não executado (a seção 1 não depende disso).
- **Jogos "isolados" no event study**: janelas de ±7 d se sobrepõem quando há
  jogos em dias próximos; o subconjunto isolado dá a leitura limpa.
- **Síntese conclusiva** (não condicional): com os resultados em mão, o texto
  afirma o achado.

### Resultado produzido
- `scripts/06_analise_defasagem.py`
- `reports/etapa9/relatorio_defasagem.md`
- `reports/etapa9/figures/` — 4 figuras (forest de rate ratio por defasagem para
  crime e acidente; CCF 6 painéis; event study 6 painéis)
- `reports/etapa9/tabelas/` — 4 CSVs (defasagens distribuídas, resumo CCF, event
  study D-1/D0/D+1, KW por janela)
- **Resultado central:** nenhuma das 30 estimativas de defasagem é significativa
  após BH (todas p_BH ≥ 0,97). Maior efeito: `acidentes_fatais` em **D0**
  RR 1,15 (IC95 0,99–1,33; p=0,06 sem BH) — mesmo sinal marginal das Etapas 7–8,
  não robusto. CCF em lag 0 dentro da banda para todos; event study plano
  (todos offsets p_BH=0,91); KW por janela ε² ≤ 0,006. **Não há efeito
  antecipatório nem posterior do jogo após controle de calendário.** Convergência
  total com Etapas 7–8; sem causalidade.

---

## 2026-09-04 — Correção da convenção D-1/D+1 na Etapa 9 (antes da Etapa 10)

### O que foi feito
- Auditado `06_analise_defasagem.py` linha a linha (script de verificação
  empírica): confirmado qual `shift()` alimenta cada rótulo do relatório e
  comparado com as colunas `jogo_d_menos_1`/`jogo_d_mais_1` do gold.
- Padronizada **toda** a Etapa 9 na convenção do gold; relatório regenerado.

### O que estava errado (e o que não estava)
- **Seção 1 (`secao_dlag`) — o cálculo já estava certo.** A coluna rotulada
  "D-1" era `tem_jogo_sp.shift(1)` = `jogo_d_menos_1` do gold ("houve jogo
  ontem" → efeito **posterior/rescaldo**); "D+1" era `shift(-1)` =
  `jogo_d_mais_1` ("há jogo amanhã" → efeito **antecipatório/véspera**).
  Os números do modelo **não mudaram** — só os rótulos.
- **Prosa contradizia o próprio código**: o texto de H0
  ("jogo[D+1] = houve jogo ONTEM; jogo[D-1] = há jogo AMANHÃ"), a nota de
  convenção no cabeçalho ("D+1 = dia seguinte ao jogo") e a síntese
  ("antecipatório (D-1/D-2), posterior (D+1/D+2)") estavam com os sentidos
  trocados em relação ao que a seção 1 calcula.
- **Seção 4 (`secao_kw_residuo`) tinha bug real de convenção**: rotulava
  `janela[p-1]` (véspera) como "D-1" e `janela[p+1]` (dia seguinte) como "D+1"
  — convenção de event-study padrão, **oposta** à da seção 1 e do gold. Dentro
  do mesmo relatório, "D-1" significava dias diferentes na seção 1 e na 4.
- A descrição no `CLAUDE.md` ("Etapa 9 usa `shift(1)` rotulado como 'D+1'") e a
  entrada de Changelog da Etapa 9 estavam ambas imprecisas quanto ao `shift`.

### Decisões tomadas e por quê
- **Convenção única no projeto = a do gold**, relativa ao dia do desfecho:
  `jogo_d_menos_k` = houve jogo há k dias (posterior); `jogo_d_mais_k` = há
  jogo daqui a k dias (antecipatório); `jogo_d0` = mesmo dia.
- **Rótulos passaram a ser os próprios nomes das colunas do gold**
  (`jogo_d_menos_2 .. jogo_d_mais_2`) em vez de "D±k" — elimina a ambiguidade
  de "D+1" ser lido como "depois do jogo" ou "jogo no dia +1".
- **Seção 4 reordenada preservando a prioridade de colisão original** (janela
  mais próxima de um jogo prevalece): `KW_H`/`KW_p` voltaram idênticos aos da
  versão anterior; só o conteúdo das colunas `res_*` trocou de lugar (era o
  efeito pretendido).
- **CCF e event study mantêm seu eixo próprio** (lag / offset relativo ao
  jogo), com uma linha de ponte explícita: lag k>0 ↔ `jogo_d_menos_k`,
  k<0 ↔ `jogo_d_mais_|k|`.

### Resultado produzido
- `scripts/06_analise_defasagem.py` reescrito nos rótulos e na prosa.
- `reports/etapa9/relatorio_defasagem.md` regenerado; `reports/etapa9/tabelas/`
  agora com `event_study_vizinhos.csv` (nome antigo `event_study_d1d0.csv`
  removido).
- **Conclusão substantiva inalterada**: nenhuma defasagem significativa após BH;
  único resíduo `acidentes_fatais` em `jogo_d0` RR 1,15 (p=0,06). Inverter um
  rótulo não inverte um nulo — mas agora o relatório pode ser citado no artigo
  sem risco de escrever "antes/durante/depois" ao contrário.
- `CLAUDE.md`: seção ⚠️ marcada como resolvida.

---

## 2026-09-04 — Etapa 10: análise espacial

### O que foi feito
- Criado `scripts/07_analise_espacial.py` (volta ao bronze: crime com campo
  BAIRRO + lat/long; acidente com lat/long da Infosiga).
- **Concentração** (seção 1): volume de crime por bairro, hexbin de densidade
  crime/acidente, % de ocorrências a X km dos estádios.
- **Análise principal — bairro do estádio vs resto** (seção 2): para cada
  estádio, bairros que concentram ≥10% dos pontos de crime a ≤1,5 km (coord só
  para rotular); GLM Poisson empilhado com interação `estadio_bairro:jogo`,
  controles `C(dia_semana)+C(mes)+feriado`, HC1, BH sobre 3 estádios. Rodado com
  todos os jogos e sem 2 datas de alavancagem.
- **Robustez secundária — DiD por anel** (seção 3): ≤2,5 km vs 7,5–15 km,
  Poisson com offset de área, HC1; crime e acidente; com/sem as 2 datas; +
  diagnóstico de empilhamento de coordenada para RR de anel > 1,1.
- **Verificação do sinal do Morumbi** (seção 4): (a) substituir lat/long por
  bairro; (b) artefato de geocodificação (pile-up em 2 coords, delegacia,
  natureza); figura crime-por-jogo.

### Decisões tomadas e por quê
- **Unidade primária do crime = BAIRRO, não lat/long**: ~20% das coordenadas de
  crime são nulas/zero/fora do município (erro já documentado no CLAUDE.md);
  BAIRRO está em 99,6% das linhas. Lat/long do crime só para rotular bairros e
  checar artefato. Acidente não tem bairro e tem coord 99,5% válida → usa anel.
- **DiD por anel fino = robustez secundária, não resultado principal**:
  granularidade de coordenada não é confiável para crime; a unidade primária
  (bairro) tem precedência.
- **Verificação obrigatória antes de reportar RR por proximidade** (pedido do
  usuário): como Etapas 7–9 já deram nulo em nível de cidade, um efeito espacial
  concentrado grande precisa passar por (a) bairro em vez de coord e (b) artefato
  de geocodificação. Se não sustentar → descritivo + limitação (Regra 10),
  **não** reportar como achado.
- **Rodar tudo com e sem 2023-09-24 e 2023-08-16**: são a final e a semifinal da
  Copa do Brasil 2023 no Morumbi (~68 mil pagantes cada) e dominam qualquer
  ajuste como pontos de alavancagem.
- **Coordenadas dos estádios**: aproximadas, de domínio público (Wikipedia),
  usadas só para rotular/robustez — declarado como limitação.

### Resultado produzido
- `scripts/07_analise_espacial.py`
- `reports/etapa10/relatorio_espacial.md`
- `reports/etapa10/figures/` — 3 figuras (hexbin densidade; forest DiD por anel;
  crime no bairro Morumbi por jogo)
- `reports/etapa10/tabelas/` — 4 CSVs (top bairros, % por anel, DiD bairro, DiD
  anel)
- **Resultado central:** sem efeito espacial robusto de dia de jogo.
  * Concentração: crime/acidente no centro e corredores viários, não nos estádios.
  * Bairro (principal): Neo Química RR 0,91 (ns, abaixo de 1), Allianz RR 1,01,
    Morumbi RR 2,39 com todas as datas → **1,17 (IC inclui 1) sem as 2 finais**.
  * Anel (secundário): Morumbi RR 2,66 → 1,24 (p=0,08) sem as 2 datas; Allianz
    crime RR 1,17 (p≈0,02) persiste, mas **sem pile-up de coordenada e sem
    aparecer no nível de bairro** → tratado como ruído do método por anel.
  * Morumbi: o RR ~3 é 2 datas (final + semi da Copa do Brasil), ~60% pile-up de
    geocodificação em 2 coords do estádio, 75%+ `FURTO - OUTROS`, zero em
    violento/roubo. Nos outros 46 jogos, crime no Morumbi = baseline.
  * **Decisão: não é achado espacial** — é registro de furto associado a 2
    eventos excepcionais. Descrito + limitação (Regra 10). Convergente com
    Etapas 7–9.

---

## 2026-09-04 — Etapa 11: definição de "pico"

### O que foi feito
- Criado `scripts/08_definicao_pico.py`.
- **Seção 1**: mostra por que a contagem crua não serve — P90 de `crimes_totais`
  cru: 25% dos dias de sexta são "pico", 1% dos de segunda; R² do modelo de
  calendário (`t + C(dia_semana) + C(mes) + feriado`) vai de 0,16
  (`acidentes_fatais`) a 0,60 (`lesao_corporal_dolosa`).
- **Seção 2**: 3 métodos sobre o **resíduo dessazonalizado**, comparados em 6
  desfechos — percentil (P90/P95), z-score (z>2, z>1,5, z>2 robusto com MAD),
  média móvel (resíduo > mm_28d + 2·sd_28d, janela causal deslocada 1 dia).
- **Seção 3**: concordância (Jaccard) entre métodos + inspeção dos dias-pico de
  consenso (P90 ∩ z>2 ∩ média móvel) para `crimes_violentos` e
  `acidentes_com_vitima`.
- **Seção 4**: série do resíduo com os dias-pico marcados por método.
- **Seção 5**: recomendação + materialização em `data/gold/pico_dia_sp.csv`.
- Patch em `02_limpeza.py`: os placeholders `pico_crime_p90` / `pico_crime_zscore`
  / `pico_acidente_p90` / `nivel_risco` agora recebem merge de `pico_dia_sp.csv`
  se ele existir (senão NaN + aviso). Ordem: `02 → 08 → 02` (opcional).

### Decisões tomadas e por quê
- **Pico sobre o resíduo dessazonalizado, não a contagem crua**: Etapas 6–10
  mostraram sazonalidade semanal/mensal forte; "pico cru" ≈ "é fim de semana" e
  um classificador acertaria só aprendendo o dia da semana (os testes P90/P95 da
  Etapa 8 foram marcados como provisórios exatamente por isso).
- **Método principal = percentil P90 do resíduo**: percentil não assume
  normalidade (o z-score assume, e a EDA rejeitou); z>2 no resíduo dá <5% de
  positivos (cauda direita mais pesada que a normal) — pouco para o split. P90 dá
  ~73 dias-pico/728 (~10%), suficiente para a validação temporal da Etapa 15;
  P95 daria ~36. z>2 e média móvel ficam como variantes de robustez (Etapa 14
  reporta as 3).
- **Alvos recomendados = `crimes_violentos` e `acidentes_com_vitima`** (os "picos
  de violência/acidentes" do título); `crimes_totais`/`acidentes_total`/
  `acidentes_fatais`/`lesao_corporal_dolosa` ficam como secundários — flags de
  todos vão no CSV.
- **`nivel_risco` (3 níveis)**: `< P75` = Baixo, `P75–P90` = Médio, `> P90` = Alto,
  sobre o resíduo de `crimes_violentos` (546/109/73 dias; 2 NaN nos dias excluídos).
- **Média móvel deliberadamente causal** (`shift(1)` + janela para trás): além de
  definição, serve como feature na Etapa 12 sem data leakage.
- **Ressalva para a Etapa 15**: limiar e ajuste de calendário aqui usam a série
  inteira; num walk-forward estrito devem ser reestimados só no treino de cada
  fold. A versão média móvel já é causal e não tem esse problema — anotado.
- **2022-06-19 mantido como pico** (é pico por todos os métodos, inclusive em
  `crimes_violentos`); é o artefato de registro em lote — remoção/winsorização
  fica para a Etapa 12, conforme já decidido.
- **`pico_dia_sp.csv` como artefato standalone** em vez de gravar direto no
  `fato_dia_sp.csv`: evita fragilidade de ordem de execução; o merge no fato é
  opcional e feito pelo `02` de forma graciosa.

### Resultado produzido
- `scripts/08_definicao_pico.py`; `scripts/02_limpeza.py` (patch do merge)
- `data/gold/pico_dia_sp.csv` — 730 × 40 (flags `pico_<alvo>_<metodo>` boolean com
  NaN nos dias excluídos, `nivel_risco`, resíduos dos 2 alvos principais)
- `reports/etapa11/relatorio_definicao_pico.md`
- `reports/etapa11/figures/` — 2 figuras (série do resíduo + picos, para
  `crimes_violentos` e `acidentes_com_vitima`)
- `reports/etapa11/tabelas/` — 3 CSVs (n picos por método, picos de consenso ×2)
- **Achado colateral:** dos 12 picos de consenso de `crimes_violentos`, 5 são dia
  de jogo (42%); dos 11 de `acidentes_com_vitima`, 0 — nenhum padrão de futebol
  nos dias-pico, consistente com Etapas 7–10.

---

## 2026-09-04 — Etapa 11 (adendo): teste de Fisher no achado colateral

### O que foi feito
- A pedido, teste de **Fisher exato** sobre "dias-pico de consenso × dia de jogo",
  adicionado a `secao_concordancia` de `08_definicao_pico.py` (roda para
  `crimes_violentos` e `acidentes_com_vitima`). Tabela 2×2 sobre os dias
  elegíveis, OR, p bilateral e unilateral, + análises de robustez.
- Novas tabelas: `reports/etapa11/tabelas/fisher_pico_x_jogo_{crimes_violentos,
  acidentes_com_vitima}.csv`.

### Resultado registrado (no relatório, seção 3)
- **`crimes_violentos`**: 5/12 picos de consenso são dia de jogo vs 17,3% de
  taxa-base. Fisher exato **OR = 3,51, p (bilateral) = 0,041 — significativo a 5%**.
  Registrado como tal, com as ressalvas:
  * sem o artefato de 2022-06-19 (1 dos 5): **p = 0,103, deixa de ser significativo**;
  * pós-hoc (definição "consenso dos 3" é uma de várias); Bonferroni ×6 desfechos
    → p ≈ 0,24 (ns);
  * a residualização tira a média de dia-da-semana/mês, não toda a estrutura de
    fim de semana → "dia de jogo" ainda é em parte proxy de fim de semana;
  * n mínimo (5 na célula crítica), IC do OR de <1 a >10;
  * **Etapas 7–9 testaram `crimes_violentos` × jogo com n completo (126 vs 602),
    controles e defasagens → todas nulas.** Uma associação pós-hoc em 12 dias não
    reverte isso.
  * Uso no artigo: associação exploratória que não sobrevive à remoção do artefato
    nem à correção de múltiplas comparações e é inconsistente com as análises
    primárias.
- **`acidentes_com_vitima`**: 0/11, OR = 0, p = 0,227 — não significativo.

### Decisão
- Achado **não** promovido a resultado; a conclusão geral do projeto (efeito de
  calendário, não do jogo; sem causalidade) permanece. O teste fica documentado
  para transparência e para a seção de Discussão do artigo.
- `data/gold/pico_dia_sp.csv` e `fato_dia_sp.csv` **inalterados** (só o relatório
  da Etapa 11 mudou).

---

## 2026-09-04 — Etapa 12: feature engineering

### O que foi feito
- Criado `scripts/09_feature_engineering.py` → `data/gold/features_dia_sp.csv`
  (730 linhas × 109 colunas: 95 features + 10 alvos + 4 flags/chave).
- **4 grupos de features**: temporal (26 — one-hot/cíclico de dia da semana,
  calendário escolar/feriados, tendência linear), futebol (20 — fixtures de D0,
  `jogo_d_menos_2..jogo_d_mais_2`, dias até/desde jogo, interações explícitas;
  `publico`/`taxa_ocupacao` mantidas como colunas 100% NaN), clima (11 — D0
  assumindo previsão perfeita + variante `_lag1` conservadora), histórica (38 —
  lags 1/2/3/7/14/28/364, rolling mean/std 7/14/28, resíduo defasado, contagem de
  picos recentes, valor esperado pelo calendário).
- **Alvos recalculados nesta etapa** (não herdados cegamente da Etapa 11):
  `y_count_*`, `y_resid_*`, `y_pico_p90_*`, `y_pico_p95_*`, `y_nivel_*` para
  `crimes_violentos` e `acidentes_com_vitima`.
- **Auditoria de leakage automatizada**: checa que nenhum lag coincide com o alvo
  do mesmo dia e que `rollmean` correlaciona mais com o alvo defasado do que com
  o do próprio dia — 0 falhas.
- **Correlação de sanidade** (Spearman) feature × resíduo-alvo, com figura dos
  top 15 por desfecho.

### Decisões tomadas e por quê
- **Setup de previsão explicitado**: fixtures de futebol de D0 são conhecidas
  com antecedência → features legítimas; resultado/gols do jogo de D0 só são
  conhecidos depois → excluídos (só entram defasados via
  `jogo_d_menos_k`/`classico_d_menos_k`); clima de D0 assume previsão perfeita
  (prática padrão na literatura clima×crime) com uma variante `_lag1`
  conservadora ao lado, para o modelo poder ser comparado nas duas hipóteses.
- **Todo lag/rolling usa `shift >= 1`**, verificado por auditoria automática, não
  só por inspeção visual.
- **Outlier de 2022-06-19 (decisão adiada da Etapa 6/8/11, resolvida aqui)**:
  contagens de crime do dia → NaN (tratado como *missing*, igual às lacunas já
  conhecidas — não removido silenciosamente, não zerado, não substituído por um
  valor inventado). A linha sai do treino/teste de crime; para os lags,
  interpola-se linearmente só o buraco de 1 dia (não deixa o artefato vazar
  para 2022-06-20 em diante). Flag `dia_artefato_lote=1` preservada. Sensibilidade
  (rodar também sem esse tratamento) fica marcada para a Etapa 14.
- **`y_*` recalculados aqui e não herdados de `pico_dia_sp.csv`**: a Etapa 11
  não tratava o outlier de 2022-06-19; recalcular garante que o alvo de
  classificação já reflita a decisão desta etapa (a Etapa 11 permanece válida
  como o documento que define e testa a *metodologia* de definição de pico).
- **`sazonal_esperado_*` e `*_resid_*` marcados `leakage_ok='ver ressalva E15'`**:
  dependem de um ajuste de calendário na série inteira — mesma ressalva já
  registrada nas Etapas 8/9/11, propagada aqui de forma explícita no dicionário
  de features, não escondida.
- **`features_dia_sp.csv` como artefato separado** (não sobrescreve `fato_dia_sp.csv`
  nem `pico_dia_sp.csv`) — mantém a mesma disciplina de não fragilizar a ordem de
  execução já usada na Etapa 11.

### Resultado produzido
- `scripts/09_feature_engineering.py`
- `data/gold/features_dia_sp.csv` (730 × 109)
- `reports/etapa12/relatorio_features.md`
- `reports/etapa12/figures/` — 2 figuras (top-15 correlação × alvo, por desfecho)
- `reports/etapa12/tabelas/` — 5 CSVs (dicionário de features, auditoria de
  leakage, missingness, correlação feature×alvo ×2)
- **Achado de sanidade**: nos dois alvos, as features líderes em correlação são
  do próprio histórico do desfecho (`_resid_lag1`, `_lag1`, `_rollmean*`) e de
  clima; a maior correlação de qualquer feature de futebol é |ρ|=0,018
  (`crimes_violentos`) e 0,055 (`acidentes_com_vitima`) — consistente com o nulo
  das Etapas 7–10 e prévia do que o SHAP (Etapa 18) deve confirmar.

---

## 2026-09-04 — Etapa 13: baselines

### O que foi feito
- Criado `scripts/10_baselines.py` → `reports/etapa13/`.
- **Split temporal fixo**: treino < 2023-10-01, teste ≥ 2023-10-01 (90 dias),
  sem embaralhar (Regra 7).
- **Baselines de regressão** (alvo = `y_count_<base>`, contagem crua): média
  histórica (constante do treino), média móvel 7d/28d (reaproveita as colunas
  causais da Etapa 12), mesmo dia da semana anterior (`lag7`). MAE/RMSE/R²/MAPE.
- **Baselines de classificação** (alvo = pico, **redefinido nesta etapa**):
  classe majoritária, heurística `dia_semana_risco` (dias da semana com taxa de
  pico acima da média NO TREINO), Logistic Regression (com e sem
  `class_weight='balanced'`). Accuracy/Precision/Recall/F1/ROC-AUC/PR-AUC +
  matriz de confusão + curvas ROC/PR.
- **Correção de vazamento**: diferente do `y_pico_p90_<base>` da Etapa 12 (ajuste
  de calendário na série inteira), aqui o modelo de calendário e o limiar P90 são
  **reajustados só no treino** e aplicados ao teste — primeira aplicação real da
  ressalva repetida desde a Etapa 8.

### Achado (não previsto, investigado a fundo em vez de reportado cru)
- A prevalência de pico no teste saiu de 3,3% (`crimes_violentos`) a 34,4%
  (`acidentes_com_vitima`), longe dos ~10% nominais. Investigado (seção 1.1): o
  termo de **tendência linear** do modelo de calendário, ajustado só até
  set/2023, extrapola mal 3 meses à frente — sobre-prevê `crimes_violentos`
  (558,5 previsto vs 510,1 real → resíduo médio -48 → quase ninguém passa do
  limiar) e subestima `acidentes_com_vitima` (77,9 vs 85,6 → resíduo +7,7 →
  muitos passam do limiar). Não é bug; é evidência concreta (não só teórica) de
  por que um único corte temporal é frágil aqui — motiva a validação
  walk-forward da Etapa 15 com números do próprio projeto.

### Decisões tomadas e por quê
- **Corte fixo em 2023-10-01** (não % do dataset): mais transparente/reproduzível
  que um corte por fração; dá ~90 dias de teste, um trimestre "realista" a prever.
- **Baselines de regressão reaproveitam features já causais da Etapa 12**
  (`rollmean7/28`, `lag7`) em vez de recalcular — são por definição preditores
  válidos para o dia seguinte, sem necessidade de "treinar".
- **`dia_semana_risco` como baseline extra** (além dos exigidos pelo briefing):
  operacionaliza "o calendário sozinho já entrega quanto?", ligando direto ao
  achado das Etapas 6-11.
- **Leitura por desfecho, não agregada**, na síntese: com `crimes_violentos`
  tendo só 3 positivos no teste, qualquer métrica de classificação para esse
  desfecho é ilustrativa, não conclusiva — dito explicitamente para não deixar
  um número instável parecer definitivo.

### Resultado produzido
- `scripts/10_baselines.py`
- `reports/etapa13/relatorio_baselines.md`
- `reports/etapa13/figures/` — 3 figuras (previsto-vs-real do calendário
  extrapolado; baselines de regressão; ROC/PR do LogReg)
- `reports/etapa13/tabelas/` — 2 CSVs (baselines de regressão e de classificação)
- **Scoreboard que a Etapa 14 precisa bater**: regressão — média móvel 7d venceu
  os outros baselines nos dois desfechos (MAE 51,3 / 11,8). Classificação —
  `logreg_balanced` bateu classe majoritária e `dia_semana_risco` em Recall/F1
  para `acidentes_com_vitima` (0,74/0,55); `crimes_violentos` não é conclusivo
  neste corte (n=3 positivos).

---

## 2026-09-04 — Etapa 14: modelos de Machine Learning

### O que foi feito
- Criado `scripts/11_modelos.py` → `reports/etapa14/`.
- **Mesmo split e mesma redefinição de alvo (calendário+P90 reajustados só no
  treino) da Etapa 13**, para comparação direta com o scoreboard de baselines.
- **Classificação** (pico): Decision Tree, Random Forest, HistGradientBoosting
  (bônus, NaN nativo), XGBoost, LightGBM, + Logistic Regression (repetida da
  Etapa 13) — tabela combinada baselines+modelos, ordenada por PR-AUC, com
  `sample_weight` balanceado em todos.
- **Regressão** (contagem): Decision Tree, Random Forest, HistGradientBoosting
  (`loss='poisson'`), XGBoost (`count:poisson`), LightGBM (`poisson`) — objetivo
  Poisson nos 3 modelos de boosting/HGB por ser dado de contagem (briefing §14).
- **Importância de features** (prévia — SHAP formal é a Etapa 18): por
  `total_gain`, não `gain` médio.
- **Sensibilidade ao outlier de 2022-06-19** (pendência da Etapa 12): XGBoost em
  `crimes_violentos`, com e sem o tratamento.

### Achados investigados antes de reportar (mesmo padrão de rigor da Etapa 10)
- **Importância por `gain` médio apontava `classico_d_menos_1` como feature #1
  em `acidentes_com_vitima`** — investigado como o RR do Morumbi na Etapa 10:
  é usada em só 2 de ~600 splits (`weight`=2) e cai para o rank #37 por
  `total_gain` (a medida agregada honesta). É o mesmo sinal fraco de clássico
  com amostra pequena (n=20/636 treino) já visto e não confirmado nas
  Etapas 7–9 — **não é achado novo**. Corrigido: `total_gain` virou a métrica
  principal do relatório, com auditoria automática comparando `gain` vs
  `total_gain`/`weight` para qualquer feature suspeita.
- **PR-AUC e F1@0.5 discordam do "melhor modelo"** em `acidentes_com_vitima`:
  `random_forest` vence por PR-AUC (0,532) mas no limiar 0,5 só marca 2 de 90
  dias como pico (Recall=0,065); `logreg_balanced` (Etapa 13) tem PR-AUC menor
  (0,436) mas Recall 0,742/F1 0,548. Reportado explicitamente em vez de
  declarar `random_forest` vencedor sem qualificação — para um sistema de
  alerta de pico, Recall no ponto de operação importa mais que ranking
  abstrato.

### Decisões tomadas e por quê
- **Features = mesmo conjunto leakage-safe da Etapa 13 + `lag364`**: a Etapa 13
  excluiu `lag364` só por causa da imputação do LogReg; árvores/boosting toleram
  bem uma coluna 49,9% NaN.
- **NaN nativo em HistGB/XGBoost/LightGBM, imputação por mediana (treino) só em
  árvore/RF/LogReg**: evita perder informação nos modelos que suportam NaN
  nativamente.
- **Hiperparâmetros rasos, sem busca** (Regra 6: não usar complexidade só por
  ser sofisticada): profundidade ≤6, ~300 árvores no máximo, adequado a ~640
  linhas de treino.
- **Herda o problema de n pequeno da Etapa 13** para `crimes_violentos`
  (3 positivos no teste): documentado de novo aqui, com a matriz de confusão do
  "melhor" modelo mostrada explicitamente para não deixar a métrica sozinha
  esconder que 26 falsos positivos foram necessários para acertar 1 verdadeiro.

### Resultado produzido
- `scripts/11_modelos.py`
- `reports/etapa14/relatorio_modelos.md`
- `reports/etapa14/figures/` — 4 figuras (ROC/PR de todos os classificadores;
  melhor regressor vs real; importância `total_gain` ×2 desfechos)
- `reports/etapa14/tabelas/` — 3 CSVs (classificação completa, regressão
  completa, sensibilidade ao outlier)
- **Scoreboard**: regressão — XGBoost/LightGBM Poisson bateram os baselines nos
  dois desfechos (MAE 39,2 vs 51,3 em `crimes_violentos`; 11,8 empatado com
  média móvel em `acidentes_com_vitima`). Classificação — `crimes_violentos`
  inconclusivo (n=3); `acidentes_com_vitima` sem vencedor único (depende do
  critério: PR-AUC vs Recall/F1, ver acima). Sensibilidade ao outlier:
  diferença moderada (MAE 39,2→43,1), não muda a conclusão qualitativa.

---

## 2026-09-04 — Etapa 15: validação temporal (walk-forward)

### O que foi feito
- Criado `scripts/12_validacao_temporal.py` → `reports/etapa15/`.
- **12 folds mensais walk-forward, janela de treino expansiva** ancorada em
  2022-01-01, cobrindo 2023 inteiro em teste (cada dia testado exatamente uma
  vez, treino sempre estritamente antes do teste — Regra 7).
- **Em cada fold**: modelo de calendário, resíduo, limiar P90 (alvo de pico) e
  `sazonal_esperado` reajustados **só no treino daquele fold** — resolve a
  última ressalva "ver ressalva E15" pendente desde a Etapa 8.
- **Modelos** (escopo menor que a Etapa 14 de propósito — validar
  estabilidade, não repetir o comparativo completo): baselines + Random Forest
  + XGBoost (classificação e regressão Poisson) + **Prophet** (regressão,
  log1p — primeira aparição no projeto do 2º algoritmo do título "XGBoost vs
  Prophet"; natural aqui porque validação temporal é o território do Prophet).
- Métricas agregadas **pooled** (previsões de todos os folds empilhadas,
  ~360 dias de teste) e **por fold** (tabela de diagnóstico com R² do
  calendário, limiar P90, prevalência de pico, média real vs prevista).

### Achado metodológico investigado antes de reportar (mesmo padrão de rigor
das Etapas 10/14)
- `roc_auc_pooled` do `logreg_balanced` em `crimes_violentos` deu **0,266**
  (pior que aleatório). Investigado por fold: fold de jan/2023 (0 picos reais)
  tinha score médio 0,93; fold de fev/2023 (13 picos reais, o mês mais
  anômalo) tinha score médio 0,03 — **12 modelos treinados do zero têm
  calibrações de probabilidade incompatíveis**, e empilhar os scores crus
  mistura essas escalas, distorcendo o ranking agregado. **Não é o modelo
  piorando a previsão.** Corrigido: adicionada métrica `*_fold_macro` (AUC
  calculada DENTRO de cada fold, depois média entre folds) ao lado da
  `*_pooled`; `logreg_balanced` corrigido sobe para AUC 0,494 (~aleatório, não
  "pior que aleatório"). Auditoria automática sinaliza qualquer modelo cuja
  `pooled` e `fold_macro` divirjam >0,15.

### Decisões tomadas e por quê
- **Folds mensais (não trimestrais como a Etapa 13)**: dá 12 pontos de
  validação em vez de 1, cobrindo o ano inteiro; contrapartida é poucos
  positivos por fold (0-13), que é justamente o que gerou o achado acima —
  decisão de manter granularidade mensal e tratar o problema de agregação
  explicitamente, em vez de aumentar a janela do fold e perder cobertura.
- **Janela expansiva, não deslizante**: maximiza o uso dos dados (só 730 dias
  no total); mesma lógica do exemplo do briefing (Train 2018-2023, Val 2024).
- **Prophet com log1p(y)**: Prophet assume erros gaussianos; log1p/expm1 é a
  adaptação padrão para dado de contagem, evita previsão negativa.
- **Escopo de modelos reduzido vs Etapa 14**: 24 folds×base já são ~150+
  ajustes de modelo; repetir os 11 modelos da Etapa 14 nesse volume por pouco
  ganho adicional — Random Forest + XGBoost + Prophet cobrem o essencial para
  validar estabilidade sem inflar o tempo de execução.

### Resultado produzido
- `scripts/12_validacao_temporal.py`
- `reports/etapa15/relatorio_validacao_temporal.md`
- `reports/etapa15/figures/` — 3 figuras (prevalência de pico por fold ×2
  desfechos; MAE por fold para os 3 modelos de regressão principais)
- `reports/etapa15/tabelas/` — 4 CSVs (diagnóstico por fold ×2, classificação
  pooled, regressão pooled)
- **Resultado central**: walk-forward confirma que a instabilidade da Etapa 13
  era real (prevalência de pico por fold ainda oscila mês a mês — ex.
  `acidentes_com_vitima` janeiro/2023 = 80,6%), mas o pooled de 12 folds dá
  leitura muito mais confiável. Regressão: XGBoost Poisson bate os baselines e
  o Prophet nos dois desfechos (MAE 34,8 vs 42,2 do Prophet em
  `crimes_violentos`; 10,3 vs 11,0 em `acidentes_com_vitima`) — mas Prophet
  sofre com só ~1-2 anos de histórico para sazonalidade anual (aviso do
  próprio Prophet nos logs). Classificação: `crimes_violentos` deixa de ser
  inconclusivo (~360 dias pooled vs 90/3-positivos da Etapa 13);
  `acidentes_com_vitima` com `logreg_balanced` mantém o melhor equilíbrio
  Recall/F1 (0,576/0,465) como já indicado na Etapa 14.

---

## 2026-09-04 — Diretório de trabalho migrado para repo git + controle de versão adiado

### O que foi feito
- O diretório de trabalho da sessão mudou de `projeto-futebol-sp` para
  `RpII_predi-o_acidentes` (mesma cópia do projeto, estado idêntico — Etapas
  1–13 concluídas no momento da troca). O novo diretório já tinha `git init`
  feito e `origin` configurado para `https://github.com/Gibaoo/RpII_predi-o_acidentes.git`.
- A sessão recebeu um comando estruturado para criar um PR ("Create PR"). Antes
  de agir, verificado o estado real do repositório:
  - `git status`: branch `main`, **0 commits**, todos os arquivos untracked.
  - `git ls-remote --heads origin`: vazio — o repositório remoto também não tem
    nenhum branch ainda.
  - `gh` CLI: **não instalado** nesta máquina (checado no PATH e nos diretórios
    de instalação comuns do Windows).
  - Tamanho do diretório: **1,5 GB**, dominado por `data/bronze/` (991 MB) e
    `uploads/` (503 MB) — microdados brutos SSP-SP/Detran-SP, incluindo
    arquivos de 190–226 MB (acima do limite de 100 MB do GitHub por arquivo).

### Decisão tomada e por quê
- **Nada foi commitado, dado push ou aberto como PR.** Motivos: (1) sem `gh`
  CLI, `gh pr create` não roda de qualquer forma; (2) com o remoto vazio, não
  há branch-base pra comparar — um PR real não é estruturalmente possível
  nesse primeiro commit; (3) commitar `data/bronze/`+`uploads/` sem crivo
  redistribuiria ~1,5 GB de microdado governamental bruto via GitHub, além de
  falhar no push pelos arquivos >100 MB — decisão de conteúdo do repositório
  não é algo pra tomar sozinho.
- Apresentadas as opções ao usuário (gitignorar dados brutos vs commitar tudo
  mesmo assim; push direto em `main` vs branch separada sem push). **O usuário
  escolheu fazer o versionamento manualmente** para as duas perguntas — sessão
  não prosseguiu com nenhuma ação de git.

### Resultado
- Nenhum arquivo alterado nesta frente. `CLAUDE.md` ganhou uma seção "Controle
  de versão" registrando o estado (repo vazio, sem `gh`, decisão do usuário de
  versionar manualmente, e o alerta sobre `data/bronze/`/`uploads/` para quem
  for ajudar com isso depois).

---

## 2026-09-04 — Etapa 15 (adendo): correção pooled→fold_macro estendida ao PR-AUC

### O que foi feito
- A pedido, verificado se a correção pooled→fold_macro da Etapa 15 (ver adendo
  acima) tinha sido aplicada ao PR-AUC, não só ao ROC-AUC.
- **Achado**: `pr_auc_fold_macro` já estava sendo **calculado** (mesma lógica de
  `fold_pr_auc` por fold + média), mas o aviso automático de divergência em
  `secao_classificacao` só comparava `roc_auc_pooled` vs `roc_auc_fold_macro` —
  o PR-AUC tinha a métrica certa na tabela, mas nenhuma auditoria checava se
  `pr_auc_pooled` também estava distorcido.
- Conferido nos números já publicados: em `crimes_violentos`, `random_forest`
  tem `pr_auc_pooled`=0,089 vs `pr_auc_fold_macro`=0,348 (Δ=0,259) — divergência
  **maior** que a do ROC-AUC que já estava sinalizada (Δ=0,102, abaixo do
  limiar) — e não estava sendo avisada. Confirma a mesma vulnerabilidade de
  pooling (calibração/prevalência instável entre folds com poucos positivos),
  agora no PR-AUC.

### Correção aplicada
- `scripts/12_validacao_temporal.py::secao_classificacao`: adicionado um
  segundo bloco de auditoria, paralelo ao do ROC-AUC, comparando
  `pr_auc_pooled` vs `pr_auc_fold_macro` (mesmo limiar >0,15) e emitindo um
  aviso próprio quando divergem.
- Script reexecutado; `reports/etapa15/relatorio_validacao_temporal.md`
  regenerado com o novo aviso.

### Resultado
- **`crimes_violentos`**: novo aviso captura `random_forest` e
  `logreg_balanced` (Δ 0,259 e 0,191) — `random_forest` não tinha sido pego
  pelo aviso de ROC-AUC. `xgboost` fica no limite (Δ=0,142, abaixo do limiar,
  não sinalizado) e `dia_semana_risco` não diverge no PR-AUC (Δ=0,056).
- **`acidentes_com_vitima`**: nenhum modelo diverge >0,15 em PR-AUC (máximo
  Δ=0,092, `xgboost`) — nenhum aviso novo aqui, consistente com esse desfecho
  ter 11/12 folds com as 2 classes (bem mais estável que `crimes_violentos`,
  que só tem 6/12).
- Conclusão do relatório já orientava usar `fold_macro`; a correção só
  fortalece essa orientação com um sinal explícito por modelo, em vez de
  depender só da leitura manual da tabela.

---

## 2026-09-04 — Etapa 16: métricas (consolidação formal)

### O que foi feito
- Criado `scripts/13_metricas_consolidadas.py` → `reports/etapa16/`. **Não
  treina nenhum modelo novo**: lê os CSVs já publicados nas Etapas 13
  (baselines, split único), 14 (modelos ML, mesmo split único) e 15 (pooled
  walk-forward + fold_macro).
- **Auditoria de cobertura contra o briefing §16**: todas as métricas de
  regressão (MAE, RMSE, R², MAPE) e classificação (Accuracy, Precision,
  Recall, F1, ROC-AUC, PR-AUC) já estavam sendo calculadas desde a Etapa 13 —
  única lacuna real era **matriz de confusão** (exigida em §16 e §24 item 12),
  nunca produzida em nenhuma etapa anterior.
- **Matriz de confusão** para os modelos pooled walk-forward (Etapa 15),
  **reconstruída algebricamente** a partir dos totais já publicados
  (`n_teste_total`, `n_pico_total`, `accuracy`, `recall` → TP/FP/FN/TN), já
  que os arrays de predição por fold não tinham sido persistidos em disco na
  Etapa 15. Validada linha a linha: precision/F1 recalculados da matriz batem
  com os valores originais em todas as 10 combinações base×modelo (não é uma
  estimativa aproximada — é decomposição exata de contagens inteiras de
  dias).
- **Scoreboard único** por alvo × tarefa, juntando as 3 fontes (Etapa 13/14
  split único + Etapa 15 pooled), com o pooled walk-forward tratado como
  evidência principal (mais dias de teste, sem a fragilidade do corte único
  documentada na Etapa 13).
- **Declaração formal do modelo recomendado** por alvo × tarefa, a valer
  para a Etapa 17 (tuning) e 18 (SHAP).

### Decisões tomadas e por quê
- **MAPE mantido, SMAPE não calculado**: checado o mínimo observado de
  `y_count_crimes_violentos` (340) e `y_count_acidentes_com_vitima` (31) em
  730 dias, 0 dias com contagem zero em qualquer um dos dois — MAPE não
  explode nem fica instável aqui, então SMAPE (que só se justifica quando há
  valores reais perto de zero) não acrescentaria informação. Decisão
  declarada explicitamente em vez de calcular SMAPE só para "cumprir tabela"
  (Regra 10).
- **Reconstrução algébrica da matriz de confusão em vez de retreinar os 12
  folds da Etapa 15 de novo**: os totais pooled (accuracy/recall/n_teste/
  n_pico) já são exatos; decompor em TP/FP/FN/TN é aritmética determinística,
  não uma nova estimativa. Verificado contra retreinar do zero: mais barato
  (~5s vs ~2min) e sem risco de divergência de seed/versão de biblioteca.
  Auditoria automática confirma consistência antes de publicar (Regra 2: não
  inventar resultado).
- **Critério de recomendação = PR-AUC fold_macro para ranking, nunca
  Accuracy** (Regra 8), com Recall/F1 citados ao lado — mesmo cuidado já
  aplicado na Etapa 14 para não deixar uma métrica agregada esconder que um
  modelo é inútil operacionalmente.
- **`crimes_violentos` deliberadamente deixado sem modelo recomendado para
  classificação**: melhor PR-AUC (`random_forest`, 0,348) tem Recall 0,05
  (praticamente não detecta pico); melhor Recall (`dia_semana_risco`, 0,50)
  tem PR-AUC baixo (0,115) e é só o baseline de calendário. Forçar um
  "vencedor" aqui esconderia que nenhum classificador testado chega a um
  ponto de operação útil — reportado como limitação (Regra 10), não como
  resultado positivo. Consistente com o nulo de futebol×desfecho já
  encontrado nas Etapas 7–10 (pouco sinal além do calendário para o
  classificador aprender).

### Resultado produzido
- `scripts/13_metricas_consolidadas.py`
- `reports/etapa16/relatorio_metricas.md`
- `reports/etapa16/figures/` — 2 figuras (matriz de confusão pooled ×2 bases,
  3 modelos em destaque: `random_forest`/`dia_semana_risco` para
  `crimes_violentos`, `logreg_balanced` para `acidentes_com_vitima`)
- `reports/etapa16/tabelas/` — 3 CSVs (`scoreboard_regressao.csv`,
  `scoreboard_classificacao.csv`, `matriz_confusao_pooled.csv`)
- **Modelos recomendados para a Etapa 17**: regressão — XGBoost Poisson nos
  dois alvos (MAE pooled 34,8 / 10,3); classificação — `logreg_balanced` só
  para `acidentes_com_vitima` (vence em PR-AUC fold_macro E Recall/F1 ao
  mesmo tempo, sem ambiguidade de critério); `crimes_violentos` sem
  candidato — ver decisão acima.
- `CLAUDE.md` atualizado: status "Etapas 1–16 concluídas", seção "Métricas
  (Etapa 16)" com a decisão de MAPE/SMAPE e a recomendação de modelo,
  "Próximos passos" renumerado a partir da Etapa 17.

---

## 2026-09-04 — Etapa 17: otimização de hiperparâmetros

### O que foi feito
- Criado `scripts/14_otimizacao_hiperparametros.py` → `reports/etapa17/`.
- **Escopo herdado da Etapa 16, não redecidido**: regressão — XGBoost
  Poisson nos 2 alvos (`crimes_violentos`, `acidentes_com_vitima`);
  classificação — `logreg_balanced` só em `acidentes_com_vitima`
  (`crimes_violentos` ficou sem candidato na Etapa 16 e não foi retunado
  aqui).
- **Nested walk-forward temporal** (Regra 7, em 2 níveis): nível externo =
  os mesmos 12 folds mensais walk-forward da Etapa 15 (janela expansiva
  ancorada em 2022-01-01), para que o MAE/PR-AUC pooled resultante seja
  comparável número-a-número com a Etapa 15/16; nível interno =
  `sklearn.model_selection.TimeSeriesSplit` (sem embaralhar) dentro do
  treino de CADA fold externo, alimentando `RandomizedSearchCV` — a escolha
  de hiperparâmetros para prever o mês de teste do fold N nunca usa dados de
  fold ≥ N.
- **Hiperparâmetros de produção calculados à parte**: uma busca adicional
  usando todo o histórico disponível (ainda `TimeSeriesSplit`, sem
  embaralhar), fora da métrica pooled reportada — é este conjunto fixo,
  não os hiperparâmetros rasos da Etapa 14/15 nem uma média por fold, que
  fica marcado para a Etapa 18 (SHAP) usar no modelo final.
- Calendário/resíduo/limiar de pico do alvo de classificação reajustados só
  no treino de cada fold externo, mesma disciplina da Etapa 15.

### Achado central (investigado antes de reportar, mesmo padrão de rigor das Etapas 10/14/15)
- **Tuning não trouxe ganho real em nenhum dos 3 pares alvo×tarefa testados
  — e isso é o achado, não uma falha do script**:
  * `crimes_violentos` (regressão): MAE pooled **piorou levemente** com o
    tuning (34,84 → 35,12; R² 0,481 → 0,462).
  * `acidentes_com_vitima` (regressão): ganho marginal, <3% (MAE 10,32 →
    10,28).
  * `acidentes_com_vitima` (classificação, `logreg_balanced`): Recall
    melhorou (0,576 → 0,674) mas PR-AUC fold_macro **piorou** (0,476 →
    0,417) — mesmo com a busca interna otimizando explicitamente para
    `average_precision` em cada fold. Trade-off real: nenhum dos dois
    modelos (baseline não-tunado vs tunado) domina o outro nos dois
    critérios ao mesmo tempo.
- **Diagnóstico, não só constatação**: a tabela de hiperparâmetros por fold
  mostra grande variação fold a fold (ex.: `C` do LogReg variando de 0,001 a
  74 entre os 12 folds) — sinal de que, com ~350–700 linhas de treino por
  fold (e poucos positivos em classificação), a busca interna reage a
  ruído em vez de convergir para um padrão estável. Não é bug de
  implementação (verificado: R² e demais métricas tunadas caem junto com o
  MAE em `crimes_violentos`, consistente com um modelo genuinamente pior,
  não com um erro de cálculo).

### Decisões tomadas e por quê
- **Nested CV (não CV único sobre tudo)**: rodar `RandomizedSearchCV` uma
  vez sobre toda a série e reportar o próprio score da busca inflaria a
  métrica (a busca "veria" o que está tentando prever). O desenho de 2
  níveis mantém a métrica pooled honesta e comparável à Etapa 15, ao custo
  de rodar a busca 12x (uma por fold externo).
- **`TimeSeriesSplit` como CV interno, não `KFold`**: preserva a Regra 7
  também dentro da busca — nenhum hiperparâmetro é escolhido usando dados
  futuros em relação ao que está sendo validado, nem no nível externo nem
  no interno.
- **`error_score=np.nan` no `RandomizedSearchCV`**: alguns splits internos
  muito curtos (early folds) podem ter 0 casos de uma classe; em vez de
  travar a busca inteira, essas combinações de hiperparâmetro ficam com
  score `NaN` nesse split e são naturalmente despriorizadas pelo ranking
  médio, sem inventar um valor.
- **Hiperparâmetros de produção separados da métrica pooled**: usar a busca
  sobre todo o histórico tanto para reportar desempenho quanto para gerar o
  modelo final misturaria estimativa de generalização com o modelo de
  produção (a busca "de produção" já viu todos os dados, então seu próprio
  score não pode ser usado como estimativa honesta) — por isso os dois são
  mantidos e rotulados como coisas diferentes.
- **`crimes_violentos` (classificação) não retunado**: a Etapa 16 já
  concluiu que nenhum classificador chega a um ponto de operação útil para
  esse alvo — o problema é falta de sinal nas features (convergente com o
  nulo das Etapas 7–10), não hiperparâmetro subótimo; gastar uma busca de
  hiperparâmetros nesse alvo não mudaria essa conclusão e foi descartado
  explicitamente em vez de rodado "só para completar a tabela".
- **Síntese não esconde o resultado negativo**: o texto do relatório evita
  chamar uma piora de "ganho marginal" — quando o MAE/PR-AUC tunado é pior
  que o baseline, isso é dito explicitamente (Regra 2: não inventar
  resultado), com a hipótese metodológica (poucos dados por fold) declarada
  ao lado, não como desculpa, mas como explicação verificável.

### Resultado produzido
- `scripts/14_otimizacao_hiperparametros.py`
- `reports/etapa17/relatorio_otimizacao.md`
- `reports/etapa17/figures/` — 2 figuras (MAE tunado vs baseline ×2 alvos;
  métricas de classificação tunado vs baseline para `acidentes_com_vitima`)
- `reports/etapa17/tabelas/` — 6 CSVs (hiperparâmetros por fold ×3
  regressão/classificação, comparação pooled ×2, hiperparâmetros de
  produção)
- **Conclusão prática**: os modelos "de produção" recomendados para a
  Etapa 18 continuam sendo XGBoost Poisson (regressão, os 2 alvos) e
  `logreg_balanced` (classificação, só `acidentes_com_vitima`) — a Etapa 16
  não muda —, mas agora com hiperparâmetros explicitamente buscados (não
  os valores rasos herdados da Etapa 14) e com a ressalva documentada de
  que, neste volume de dados, tuning tem retorno pequeno ou nulo.
- `CLAUDE.md` atualizado: status "Etapas 1–17 concluídas", nova seção
  "Otimização de hiperparâmetros (Etapa 17)", "Próximos passos"
  renumerado a partir da Etapa 18.

---

## 2026-09-04 — Etapa 18: interpretabilidade formal com SHAP

### O que foi feito
- Criado `scripts/15_interpretabilidade_shap.py` → `reports/etapa18/`.
  Instalado `shap` (nova dependência, adicionada ao `CLAUDE.md`).
- **Modelos explicados = os "de produção" da Etapa 17**, treinados aqui uma
  vez sobre todo o histórico disponível e explicados IN-SAMPLE — a
  generalização já foi validada nas Etapas 15/17 (pooled walk-forward); o
  objetivo aqui é explicar o que o modelo final aprendeu, não reavaliar
  desempenho: `shap.TreeExplainer` para XGBoost Poisson (regressão, os 2
  alvos) e `shap.Explainer` (linear) para `logreg_balanced` (classificação,
  só `acidentes_com_vitima` — `crimes_violentos` segue sem modelo
  recomendado, decisão da Etapa 16 não reaberta).
- Para cada modelo: beeswarm SHAP, gráfico de barras top-15 colorido por
  grupo de features (temporal/futebol/clima/histórica), tabela de
  importância por grupo, comparação SHAP vs `total_gain` do mesmo modelo
  (regressão).
- **Auditoria automática de colinearidade com calendário** (função
  `audita_colinearidade`): para cada feature com SHAP alto (top 20),
  correlaciona (Spearman) com o alvo JÁ desazonalizado (`y_resid_<base>` na
  regressão, o próprio `y_pico` na classificação — ambos já têm
  mês/dia-da-semana/feriado removidos por construção). Feature com SHAP
  alto e correlação próxima de zero/não-significativa com esse alvo é
  marcada como provável artefato de colinearidade com calendário.
- Respondidas com números (não qualitativo) as 6 perguntas do briefing §18
  sobre futebol/clima/dia-da-semana.

### Achado investigado (mesmo padrão de rigor das Etapas 10/14/15/17)
- **`dias_desde_jogo`/`dias_ate_jogo` apareciam com SHAP muito alto**
  (rank #2 tanto na regressão quanto na classificação de
  `acidentes_com_vitima`; grupo `futebol` bruto = 18,7%/26,6% do SHAP
  total) — à primeira vista, pareceria contradizer o nulo das Etapas 7–12.
  **Investigado antes de reportar**: essas 2 features (contagem contínua de
  dias até/desde o jogo mais próximo) são fortemente colineares com
  sazonalidade — correlação Spearman com `mes` de -0,44/-0,21;
  `dias_desde_jogo` médio = 80,6–96,3 dias em jan-mar (sem jogos de
  SP-capital na base nesse período) vs ~2 dias na temporada (mai-nov). Mas
  a correlação dessas mesmas features com o alvo **já desazonalizado** é
  praticamente nula e não-significativa: `y_resid_acidentes_com_vitima`
  rho=-0,055 (p=0,136); `y_pico_acidentes_com_vitima` rho=-0,003 (p=0,938,
  classificação) — confirmado também para `dias_ate_jogo`
  (rho=-0,014/p=0,71) e para `n_jogos_janela7`, `jogo_d_menos_1`,
  `jogo_serie_a`, `tem_jogo_sp` (todos p>0,24 contra o resíduo). Conclusão:
  **o modelo aprendeu "época do ano" (proxy quase perfeito via
  `dias_desde_jogo`), não "efeito do jogo"** — consistente com o nulo das
  Etapas 7–12, não uma contradição dele. Depois de descontar as features
  confirmadas como artefato, `futebol` líquido cai para 0,1–4% em regressão
  (`soma_sem_artefato` nas tabelas `shap_grupo_*.csv`); em classificação de
  `acidentes_com_vitima` ainda sobra ~26%, mas é soma de muitas features
  individualmente pequenas não auditadas uma a uma — documentado como
  limite superior, não confirmação de efeito.
- **Cuidado metodológico ao construir a auditoria**: a flag de "artefato"
  só é aplicada a features de fora do grupo `temporal` — um feature de
  calendário (ex. `sin_dow`) ter correlação baixa com um alvo já
  residualizado NO PRÓPRIO calendário é esperado por construção
  (quase-tautológico), não evidência de artefato; aplicar a mesma regra a
  features temporais gerava falsos positivos sem sentido nas primeiras
  versões do script, corrigido antes de publicar.

### Decisões tomadas e por quê
- **SHAP calculado in-sample sobre o modelo de produção, não em um novo
  split**: a Etapa 18 é sobre EXPLICAR o modelo final, não sobre validar
  generalização de novo (já feito nas Etapas 15/17) — documentado
  explicitamente para não confundir o leitor sobre o propósito da métrica
  aqui.
- **`TreeExplainer` para XGBoost (exato, rápido) e `shap.Explainer` linear
  para LogReg** (com `shap.maskers.Independent` usando TODA a base de
  fundo, não a subamostra default de 100, para reprodutibilidade exata) —
  escolha padrão de biblioteca para cada família de modelo, sem
  aproximações desnecessárias.
- **Auditoria de colinearidade construída como checagem automática, não só
  texto**: seguindo o padrão já estabelecido nas Etapas 10 (RR do Morumbi),
  14 (`total_gain` vs `gain`), 15 (pooled vs `fold_macro`) e 17
  (instabilidade de hiperparâmetro) — toda vez que uma métrica agregada dá
  um resultado que poderia ser mal-interpretado como "achado", o projeto
  audita a causa raiz antes de publicar, não relata o número bruto sozinho.
- **Pergunta "público influencia?" respondida como limitação, não
  computada**: `publico`/`taxa_ocupacao` são 100% NaN desde a Etapa 12 e
  nunca entraram no conjunto de features de nenhum modelo — não há SHAP a
  reportar (Regra 10, não fabricar proxy).

### Resultado produzido
- `scripts/15_interpretabilidade_shap.py`
- `reports/etapa18/relatorio_shap.md`
- `reports/etapa18/figures/` — 6 figuras (beeswarm + barras top-15 por
  grupo, para os 2 modelos de regressão e o 1 de classificação)
- `reports/etapa18/tabelas/` — 6 CSVs (`shap_importancia_*` com colunas de
  auditoria de colinearidade, `shap_grupo_*` com `soma_sem_artefato`)
- **Resultado central**: SHAP confirma o nulo de futebol em
  `crimes_violentos` (2,2% do peso, 0 features no top 15) e, depois de
  descontar o artefato de colinearidade com calendário, também em
  `acidentes_com_vitima` regressão (18,7%→0,1% líquido); histórico do
  próprio desfecho e clima/temporal seguem como os grupos que realmente
  explicam a previsão nos dois modelos de regressão. Classificação de
  `acidentes_com_vitima` fica com uma fração de futebol líquida maior
  (~26%) mas não totalmente auditada — marcado como limite superior, a
  investigar mais na Etapa 20 (causalidade) se necessário.
- `CLAUDE.md` atualizado: status "Etapas 1–18 concluídas", nova seção
  "Interpretabilidade SHAP (Etapa 18)" com o achado de colinearidade,
  "Próximos passos" renumerado a partir da Etapa 19, `shap` adicionado às
  dependências.

---

## 2026-09-04 — Etapa 19: análise de cenários

### O que foi feito
- Criado `scripts/16_analise_cenarios.py` → `reports/etapa19/`. Usa os
  modelos de produção da Etapa 17 (mesmos hiperparâmetros, treinados 1x
  sobre todo o histórico, igual à Etapa 18).
- **Cenários adaptados do exemplo do briefing §19** (A: domingo + jogo
  comum; B: domingo + clássico; C: quarta-feira + jogo noturno; D: domingo
  + clássico + chuva), mais 2 baselines pareados por dia da semana/época do
  ano (domingo sem jogo, quarta sem jogo) para servir de referência de
  comparação.
- **Adaptação necessária**: os cenários do briefing especificam público
  ("20 mil pessoas" etc.) — `publico`/`taxa_ocupacao` são 100% ausentes
  desde a Etapa 12 e nunca entraram em nenhum modelo; declarado como
  limitação explícita (Regra 10), sem proxy inventado. Cenários simulados
  só nas dimensões que os modelos realmente usam.
- **Método de construção**: cada cenário (A, B, C e os 2 baselines) usa uma
  linha REAL do dataset — um dia histórico que já satisfaz a descrição,
  escolhido deterministicamente (mediana por data entre os candidatos
  elegíveis, para não cherry-picker uma data favorável). O cenário D reusa
  a mesma linha real do B com uma única perturbação controlada
  (`precipitacao_total` → mediana dos dias de chuva observados, 4,1mm),
  isolando o efeito do clima com o resto do dia mantido idêntico.
- Para cada cenário: previsão de contagem (2 alvos, XGBoost Poisson) e
  probabilidade de pico (`acidentes_com_vitima`, `logreg_balanced`) — mais
  uma **decomposição SHAP exata** da diferença entre cada cenário e seu
  baseline pareado, por grupo de features (temporal/futebol/clima/
  histórica), usando a aditividade do SHAP (predição = base_value + soma
  dos SHAP values).

### Problema descoberto e corrigido durante a implementação
- A primeira versão comparava a soma dos deltas SHAP com a diferença de
  predição na escala de **contagem** (regressão) e **probabilidade**
  (classificação) — a checagem de aditividade falhava sistematicamente
  (ex.: diferença prevista de 16,34 na contagem vs soma SHAP de apenas
  0,033). Investigado antes de publicar: não era um bug de cálculo, era
  comparação na escala errada. SHAP é aditivo na escala em que o modelo
  soma internamente (árvores/coeficientes) — para XGBoost com
  `objective="count:poisson"` isso é o **log da taxa** (`predict(...,
  output_margin=True)`, que é exatamente `log(predict())`, verificado
  numericamente); para a Logistic Regression é o **log-odds**
  (`decision_function`), não a probabilidade (`predict_proba` aplica
  sigmoid, não-linear). Corrigido usando margem/log-odds em toda a seção
  de decomposição, com o "confere" da checagem de aditividade agora exato
  em todas as comparações.

### Achados
- **`futebol` contribui pouco para a maioria dos deltas cenário-vs-baseline
  nas 2 regressões** (0,3% a 27% do "tamanho" do delta, medido em
  |delta_shap|; às vezes com sinal oposto ao delta total) — reforça o nulo
  já estabelecido nas Etapas 7–18: a diferença de risco entre um dia de
  jogo e seu baseline pareado vem majoritariamente de outras diferenças
  incidentais entre os 2 dias reais (clima do dia, histórico recente), não
  do jogo em si.
- **Exceção parcial**: na classificação de `acidentes_com_vitima` (cenário
  B — clássico — vs baseline), o grupo `futebol` responde por ~33% do
  delta em log-odds — a maior participação entre todas as comparações
  testadas, mas ainda minoritária. Consistente com o achado da Etapa 18 de
  que essa é a combinação alvo/tarefa com a fração de futebol menos
  totalmente auditada (o "limite superior" de ~26% documentado lá).
- **Achado didático sobre a ressalva de causalidade**: o cenário com maior
  P(pico) previsto para `acidentes_com_vitima` é "domingo + jogo comum"
  (0,855) — não o clássico (0,539) nem o jogo noturno de meio de semana
  (0,627), que intuitivamente pareceriam mais arriscados. Isso não
  significa que jogo comum é mais perigoso que clássico; significa que o
  dia-âncora real escolhido para esse cenário tinha outras características
  (histórico recente, clima) que pesam mais no modelo do que o tipo de
  jogo — exatamente o tipo de leitura equivocada que a decomposição por
  grupo existe para prevenir.

### Decisões tomadas e por quê
- **Cenários construídos com dias reais, não linhas sintéticas**: fabricar
  uma linha com 71 features do zero exigiria inventar valores de histórico/
  clima sem base (Regra 1/2); usar um dia real que já satisfaz a descrição
  do cenário elimina esse risco — toda feature vem de algo que realmente
  aconteceu, exceto a única perturbação controlada do cenário D.
- **Seleção determinística do dia-âncora (mediana por data)**: evita a
  aparência (e o risco real) de escolher a dia favorável a um resultado
  desejado entre vários candidatos elegíveis.
- **Baselines pareados por dia da semana e época do ano** (não um único
  baseline geral): isola melhor a comparação "mesmo perfil de calendário,
  com/sem jogo" — ainda que dias reais diferentes sempre tragam alguma
  diferença incidental (daí a decomposição SHAP para quantificar isso, não
  assumir que a diferença toda é "efeito do jogo").
- **Decomposição por grupo em vez de citar só a predição final**: essencial
  para não repetir o erro que a Etapa 18 já identificou (SHAP alto podendo
  vir de colinearidade com calendário, não de sinal de futebol) — aqui
  aplicado ao delta entre 2 cenários específicos, não à importância global.

### Resultado produzido
- `scripts/16_analise_cenarios.py`
- `reports/etapa19/relatorio_cenarios.md`
- `reports/etapa19/figures/` — 1 figura (contagem prevista ×2 alvos +
  P(pico) `acidentes_com_vitima`, todos os 6 cenários lado a lado)
- `reports/etapa19/tabelas/` — 3 CSVs (`predicoes_cenarios.csv`,
  `decomposicao_shap_cenarios.csv`, `resumo_participacao_futebol.csv`)
- `CLAUDE.md` atualizado: status "Etapas 1–19 concluídas", nova seção
  "Análise de cenários (Etapa 19)", "Próximos passos" renumerado a partir
  da Etapa 20.

---

## 2026-09-04 — Etapa 20: análise de causalidade formal

### O que foi feito
- Criado `scripts/17_analise_causalidade.py` → `reports/etapa20/`.
- **Mapeamento formal dos 5 métodos do briefing §20** contra o que o
  projeto já tinha feito: regressão com controles (Etapas 7-9), event
  study (Etapa 9) e Difference-in-Differences (Etapa 10) — não repetidos.
  **2 métodos novos adicionados nesta etapa**:
  1. **Propensity Score** — escore de propensão via regressão logística
     (`tem_jogo_sp ~ dia_semana + mês + feriado + férias_escolares +
     trend`), pareamento 1:1 sem reposição (vizinho mais próximo no logit
     do escore, caliper 0,2·DP, regra de Austin 2011), balanço de
     covariáveis checado por SMD antes/depois, ATE pareado com bootstrap
     pareado + Wilcoxon, e IPTW (pesos estabilizados truncados p1/p99,
     GLM Poisson HC1) como robustez.
  2. **Interrupted Time Series (adaptado)** — em torno da final da Copa do
     Brasil 2023 (2023-09-24, maior público da base, ~68 mil pagantes),
     citywide (diferente da Etapa 10, que só olhou o bairro do Morumbi).

### Problemas descobertos e investigados antes de publicar (mesmo padrão de rigor das Etapas 10/14/15/17/18/19)
- **Violação de positividade**: verificado ANTES de rodar o matching que
  janeiro e fevereiro não têm NENHUM dia de jogo de SP-capital em toda a
  base (0% de tratamento nesses meses) — viola o pré-requisito de
  sobreposição (overlap) do PSM. Quantificado: ~25% dos dias têm escore de
  propensão extremo (<0,05 ou >0,95).
- **Discrepância real entre pareamento e IPTW em `acidentes_com_vitima`**:
  o ATE pareado não achou efeito (Wilcoxon p=0,825, +0,7%), mas o IPTW
  achou um RR pequeno e estatisticamente significativo (1,038, p=0,017).
  Investigado em vez de reportado cru: a causa provável é exatamente a
  violação de positividade acima -- o pareamento só compara dentro da
  região com sobreposição real (meses com jogo), enquanto o IPTW repondera
  a base inteira, incluindo jan-mar (só controles, propensão ~0), o que
  reintroduz parte do confundidor sazonal que o desenho deveria eliminar.
  **Reportado como discrepância não resolvida**, não escondida atrás de um
  "converge tudo para o nulo" -- o pareamento foi adotado como estimativa
  primária (mais robusto à falta de suporte comum) e o IPTW mantido como
  resultado em aberto.
- **Janela de ITS contaminada**: verificado que a janela de ±21 dias ao
  redor da final da Copa do Brasil tem 8 OUTROS jogos dentro dela --
  inviabiliza uma regressão segmentada clássica (misturaria o evento
  extremo com o efeito rotineiro de jogo já nulo nas Etapas 7-9).
  Adaptado para uma comparação de distribuição (z-score do resíduo do
  evento vs. resíduo de outros jogos comuns) em vez de fabricar uma janela
  "limpa" que não existe nos dados (Regra 10).
- **Bug de escala corrigido durante a implementação**: a primeira versão
  reportava "%_vs_controle" também para o alvo `resíduo desazonalizado`
  (média ~0 por construção) -- produzia percentuais sem sentido (ex.
  -151%). Corrigido: `%` só é reportado para a contagem crua (denominador
  positivo e interpretável); para o resíduo, reporta-se só o ATE em
  unidades absolutas.

### Achados
- **PSM (estimativa primária) confirma o nulo nos 2 alvos**:
  `crimes_violentos` ATE +1,5% (IC95 -5,67 a 22,39, Wilcoxon p=0,32);
  `acidentes_com_vitima` ATE +0,7% (IC95 -2,91 a 4,19, Wilcoxon p=0,83).
- **Evento extremo (final da Copa do Brasil) não deixa marca detectável na
  série agregada de SP capital**: `crimes_violentos` z=1,22 (percentil
  93), `acidentes_com_vitima` z=-1,83 (percentil 3) -- ambos dentro da
  faixa típica de um dia de jogo comum (|z|<2). Nem o evento de maior
  público do dataset (~68 mil pagantes) produz um sinal citywide fora do
  esperado para um jogo qualquer.
- **6º e 7º métodos independentes convergindo no nulo já estabelecido**
  (regressão com controles, event study, DiD, colinearidade SHAP,
  decomposição de cenários, e agora PSM + evento extremo) -- com a única
  exceção sendo o IPTW em `acidentes_com_vitima`, documentada como
  discrepância metodológica em aberto, não como achado causal novo.

### Decisões tomadas e por quê
- **PSM em vez de repetir DiD/regressão**: balanceia por DESENHO (matching/
  pesos) em vez de por especificação de modelo -- evidência estruturalmente
  diferente da já produzida nas Etapas 7-9, exigida pelo briefing como
  metodologia própria, não uma repetição do que já existia.
- **Pareamento como estimativa primária, IPTW como robustez**: quando os 2
  discordam e há violação de positividade documentada, o pareamento (que
  naturalmente restringe a comparação à região de sobreposição real) é
  metodologicamente mais defensável que reponderar regiões sem dados de
  tratamento -- decisão declarada explicitamente, não silenciosa.
- **GLM Poisson (não WLS-Gaussiano) para o IPTW**: mesma convenção já
  fixada nas Etapas 7-9 para dado de contagem: Poisson + erros HC1, agora
  ponderado pelo peso IPTW via `var_weights`.
- **Adaptação do ITS declarada, não escondida**: melhor reportar a
  limitação real (janela contaminada) e usar um método mais simples e
  honesto (comparação de distribuição) do que apresentar uma regressão
  segmentada que pareceria rigorosa mas estaria medindo uma mistura de
  efeitos (Regra 10).

### Resultado produzido
- `scripts/17_analise_causalidade.py`
- `reports/etapa20/relatorio_causalidade.md`
- `reports/etapa20/figures/` — 2 figuras (balanço de covariáveis SMD
  antes/depois do pareamento, ×2 alvos)
- `reports/etapa20/tabelas/` — 6 CSVs (balanço de covariáveis ×2, ATE
  pareado ×2, resumo PSM, evento extremo Copa do Brasil)
- `CLAUDE.md` atualizado: status "Etapas 1–20 concluídas", nova seção
  "Análise de causalidade formal (Etapa 20)" com a violação de
  positividade e a discrepância PSM/IPTW, "Próximos passos" apontando para
  a Etapa 21 (consolidação/relatório final).

---

## 2026-09-04 — Adendo: fecha as 2 pendências do checkpoint pós-Etapa 18

### O que foi feito
A pedido, antes de iniciar a Etapa 21, fechadas as 2 pendências registradas
no checkpoint pós-Etapa 18 (`CLAUDE.md`), que ainda estavam abertas depois
das Etapas 19 e 20.

**1. Auditoria de colinearidade completa no grupo futebol de
`acidentes_com_vitima`** — `scripts/15_interpretabilidade_shap.py`:
- `audita_colinearidade` reescrita para testar **todas** as features de
  cada modelo contra o alvo já desazonalizado, não só o top-20 SHAP
  *global* (a versão anterior nunca testava features de futebol de
  rank>20, como `classico`, `classico_d_menos_1`, `jogo_x_noturno` — que
  tinham SHAP não-desprezível em `acidentes_com_vitima` classificação).
- Nova seção 3.2 no relatório (`## 3.2 Auditoria completa do grupo
  futebol`) lista as 18 features de futebol de cada um dos 3 modelos com
  correlação, p-valor e flag de artefato.
- **Bug real encontrado e corrigido durante a implementação**: a coluna
  `soma_sem_artefato` de `tabela_grupo` usava
  `out["grupo"].map(liq).fillna(out["soma_mean_abs_shap"])` — quando um
  grupo inteiro fica 100% marcado como artefato, o `groupby()` de `liq`
  descarta esse grupo (sem nenhuma linha sobrevivente), o `.map()` dá NaN,
  e o `.fillna()` **reintroduzia o valor BRUTO inteiro** em vez de 0 —
  exatamente o cenário mais importante (grupo inteiramente artefato)
  escondido por um fallback errado. Descoberto porque a nova auditoria
  completa passou a marcar 18/18 features de futebol como artefato pela
  primeira vez, expondo o bug (antes, sempre sobrava alguma feature de
  rank>20 não testada, mascarando o problema). Corrigido: `.fillna(0.0)`.
- **Resultado, agora fechado (não mais "limite superior")**: nos 3 modelos
  (`crimes_violentos` regressão, `acidentes_com_vitima` regressão e
  classificação), **18/18 features de futebol são marcadas como artefato
  de colinearidade com calendário** — `futebol líquido = 0,0%` do SHAP
  total nos três. Substitui o "~26% (classificação)/33% (Etapa 19, cenário
  B)" citado como limite superior nas Etapas 18/19.

**2. Sensibilidade do SHAP ao hiperparâmetro de produção** — mesmo script,
nova seção 5:
- Reexplicados os 3 modelos com os **hiperparâmetros rasos e
  não-otimizados da Etapa 14/15** (`n_estimators=300, max_depth=3,
  learning_rate=0,05, subsample=0,8, colsample_bytree=0,8` para XGBoost;
  `C=1,0, penalty='l2'` para a LogReg — os defaults nunca especificados na
  Etapa 15), em vez dos hiperparâmetros de produção da Etapa 17.
- **Resultado**: participação bruta do grupo futebol varia até 5,7 pontos
  percentuais entre hiperparâmetro raso e de produção (ex.
  `acidentes_com_vitima` classificação: 26,6% produção vs 24,3% raso), mas
  a participação **líquida** (pós-auditoria da pendência 1) é **0,0% nos
  dois hiperparâmetros, nos 3 modelos** — a conclusão "futebol ≈ nulo" não
  é um artefato da busca de hiperparâmetros da Etapa 17.

### Decisões tomadas e por quê
- **Flag de artefato só para features fora do grupo `temporal`, mantida**:
  já decidido na Etapa 18 original — testar colinearidade de uma feature
  de calendário contra um alvo já ajustado pelo próprio calendário seria
  quase tautológico.
- **Robustez roda com `gera_figuras=False`**: a checagem de hiperparâmetro
  raso é só numérica (comparação de %), não precisa de 6 figuras extras
  poluindo o relatório — `roda_regressao`/`roda_classificacao` ganharam
  parâmetros `sufixo` e `gera_figuras` para reuso sem sobrescrever os
  arquivos de produção.
- **Bug do `.fillna()` corrigido na função geral (`tabela_grupo`), não só
  para o caso do futebol**: a mesma correção vale para qualquer grupo que
  algum dia fique 100% marcado como artefato — mais robusto que um
  patch específico.

### Resultado produzido
- `scripts/15_interpretabilidade_shap.py` (reescrito: `audita_colinearidade`,
  `tabela_grupo`, `roda_regressao`/`roda_classificacao` com `sufixo`/
  `gera_figuras`, novas seções 3.2 e 5, `HP_RASOS`)
- `reports/etapa18/relatorio_shap.md` regenerado (agora com 6 seções: 1-2
  modelos, 3 sanidade, 3.1 achado investigado, 3.2 auditoria completa, 4
  perguntas do briefing, 5 robustez de hiperparâmetro, 6 síntese)
- `reports/etapa18/tabelas/` — 13 CSVs (6 novos: 3 `shap_importancia_*_hp_rasos.csv`
  + 3 `shap_grupo_*_hp_rasos.csv`, mais `robustez_hp_rasos_vs_producao.csv`)
- `CLAUDE.md`: seção de pendências marcada como **FECHADA**, com os números
  resolvidos.

---

## 2026-09-04 — Adendo: IPTW restrito confirma a discrepância PSM/IPTW da Etapa 20

### O que foi feito
A pedido, adicionado a `scripts/17_analise_causalidade.py` (seção 2) um
terceiro IPTW, restrito à mesma região de sobreposição que o pareamento
usa (exclui jan-fev, os meses sem nenhum dia de jogo de SP-capital na
base — violação de positividade já documentada na Etapa 20) — confirmação
direta da hipótese de que a discrepância PSM/IPTW em `acidentes_com_vitima`
vinha da falta de sobreposição, não de um efeito causal real.

### Resultado
- **Confirmado**: restringindo o IPTW à região de sobreposição, o efeito
  em `acidentes_com_vitima` some (RR=1,006, IC95 0,975–1,037, p=0,723) —
  quase idêntico ao pareamento (ATE +0,7%, p=0,825) e muito diferente do
  IPTW irrestrito original (RR=1,038, p=0,017). A discrepância está
  **resolvida**: era reintrodução do confundidor sazonal via os dias de
  jan-fev (só controles, propensão ~0) entrando na média ponderada do
  IPTW irrestrito, não evidência de efeito causal.
- `crimes_violentos` (que já não tinha discrepância) confere como esperado:
  IPTW restrito (RR=1,007, p=0,623) próximo do IPTW irrestrito (RR=1,006,
  p=0,665) e do pareamento (p=0,322) — sem surpresa, incluído por simetria.
- Texto do relatório (seções 2, 4 e 5) atualizado para declarar a
  discrepância como resolvida em vez de "em aberto"; a síntese e o
  blockquote da Regra 5/§20 agora refletem isso dinamicamente (gerados a
  partir do resultado, não hardcoded).

### Decisões tomadas e por quê
- **Reusa o mesmo `ps` (escore de propensão) já estimado no sample
  completo**, só restringindo as LINHAS ao subconjunto com sobreposição,
  em vez de reajustar a regressão logística do zero nesse subconjunto —
  mantém a comparação com o pareamento (que também usa o mesmo `ps`)
  apples-to-apples; a estabilização do peso (`p_treat`) é recalculada
  dentro do subconjunto, como exige a definição de IPTW estabilizado.
- **`crimes_violentos` incluído mesmo sem discrepância**: mantém o código
  simétrico entre os 2 alvos e serve como checagem de sanidade (o IPTW
  restrito não deveria alterar muito uma estimativa que já não discordava).

### Resultado produzido
- `scripts/17_analise_causalidade.py` (nova lógica de IPTW restrito dentro
  de `secao_psm`, textos de discrepância/síntese reescritos para serem
  dinâmicos)
- `reports/etapa20/relatorio_causalidade.md` regenerado
- `reports/etapa20/tabelas/resumo_psm.csv` com as novas colunas
  `iptw_rr_restrito`/`iptw_p_restrito`
- `CLAUDE.md`: seção "Análise de causalidade formal (Etapa 20)" atualizada
  — discrepância marcada como confirmada/resolvida, pendência removida,
  "Próximos passos" ajustado.

---

## 2026-09-04 — Etapa 23: resultados esperados (12 perguntas do briefing)

### O que foi feito
- Criado `scripts/18_resultados_finais.py` → `reports/etapa23/`. **Não
  treina nada novo, não recalcula nenhum teste estatístico** — lê
  diretamente os CSVs já publicados nas Etapas 6, 7, 8, 9, 10, 16, 17, 18
  e 20 e monta a resposta às 12 perguntas objetivas do briefing §23, cada
  uma citando a etapa de origem (mesma filosofia de consolidação da
  Etapa 16).
- Cada resposta segue a Regra 5 explicitamente: nunca usa "efeito de X"
  quando o que foi medido é associação ajustada ou predição de modelo, não
  causalidade.

### Resultado
As 12 respostas (números completos em
`reports/etapa23/relatorio_resultados_finais.md`):
1. Associação bruta fraca com futebol para alguns desfechos (ex.
   `lesao_corporal_dolosa` +14,9%, p<0,001); some completamente após
   ajuste por calendário (RR~1,0, ns); 0/44 pares significativos na
   correlação parcial (Etapa 8); PSM `crimes_violentos` ATE ns (Etapa 20).
2. Mesmo padrão para acidentes; `acidentes_fatais` é o resíduo mais
   próximo de significância do projeto inteiro (RR ajustado 1,146,
   p=0,063, não sobrevive a BH).
3. Clássicos não representam risco maior — diferenças brutas não
   significativas após BH; SHAP confirma `classico` como artefato de
   colinearidade com calendário nos 3 modelos de produção (contribuição
   líquida = 0).
4. Jogos noturnos idem para os 2 alvos principais do projeto (o único
   sinal bruto significativo, `lesao_corporal_dolosa` +17,0%, é fora do
   escopo principal e sem controle de calendário).
5. Público não testável (feature 100% ausente, nunca modelada).
6. Nenhuma das 30 defasagens D-2..D+2 é significativa após BH; sem
   período de maior risco identificável antes/durante/depois do jogo.
7. Histórico do próprio desfecho + calendário + clima explicam os picos;
   futebol líquido = 0,0% do SHAP nos 3 modelos (adendo Etapa 18).
8. XGBoost Poisson (regressão, 2 alvos, MAE 34,8/10,3); `logreg_balanced`
   (classificação, só `acidentes_com_vitima`) — `crimes_violentos`
   classificação continua sem modelo recomendado.
9. Recall 0,576 (0,674 tunado) para `acidentes_com_vitima`; nenhum ponto
   de operação útil para `crimes_violentos` (melhor PR-AUC tem Recall
   0,05; melhor Recall tem PR-AUC baixo).
10. Sim, D0 (mesmo dia), validado walk-forward; horizonte de previsão >1
    dia nunca testado no projeto — declarado como limitação, não capacidade
    demonstrada.
11. MAE 34,8 (`crimes_violentos`, MAPE 7,1%, R²=0,48) / 10,3
    (`acidentes_com_vitima`, MAPE 12,7%, R²=0,28), pooled walk-forward
    (~360 dias de teste).
12. Lista consolidada de 10 categorias de limitação (público ausente,
    Paulistão/Libertadores fora da base, janela de 730 dias, censura/
    lacunas de registro, outlier tratado, geolocalização, sem causalidade,
    `crimes_violentos` sem classificador, horizonte de previsão, fatores
    de confusão não observados) — reunidas de `CLAUDE.md` e da Etapa 20,
    nenhuma limitação nova.

### Decisões tomadas e por quê
- **Consolidação pura, sem recomputar**: todas as 12 respostas foram lidas
  de CSVs de etapas já publicadas e auditadas; evita divergência entre o
  número citado aqui e o número já revisado na etapa original.
- **Cada resposta cita a etapa de origem explicitamente**: facilita
  auditoria e vira a base direta das seções Resultados/Discussão/Conclusão
  do relatório final (§25), sem precisar re-derivar nada na hora de
  escrever o artigo.

### Resultado produzido
- `scripts/18_resultados_finais.py`
- `reports/etapa23/relatorio_resultados_finais.md`
- `CLAUDE.md` atualizado: status "Etapas 1–20 + 23 concluídas", nova seção
  "Resultados esperados (Etapa 23)", "Próximos passos" reorganizado em
  §21/22 (documentação de código/pipeline), §24 (galeria de visualizações)
  e §25 (relatório acadêmico final em LaTeX/SBC — maior peça restante,
  escopo a alinhar com o usuário).

---

## 2026-09-04 — Etapa 24 (visualizações finais) + README.md (§21/22)

### O que foi feito
- Criado `scripts/19_visualizacoes_finais.py` → `reports/etapa24/`. **Não
  recalcula nenhuma estatística**: levantados os 15 itens exigidos pelo
  briefing §24 contra as figuras já publicadas nas etapas anteriores — 13
  já existiam (EDA, Etapas 7, 13, 14, 16, 18); só 2 nunca tinham virado
  figura (item 6, clássico vs jogo comum, e item 7, jogo diurno vs
  noturno — a Etapa 7 só tinha publicado tabela para esses 2 recortes).
  Geradas as 2 figuras que faltavam (violino, mesmo estilo e mesmo
  filtro/exclusão de dias censurados já usados na Etapa 7) e montado um
  índice (`reports/etapa24/galeria_visualizacoes.md`) linkando os 15
  itens, cada um citando a etapa de origem.
- Criado `README.md` na raiz do projeto (documento para humanos,
  complementa o `CLAUDE.md` interno): contexto do projeto, achado central
  em 1 parágrafo, diagrama Mermaid do pipeline completo (19 scripts),
  instruções de como rodar em sequência, estrutura de diretórios, tabela
  de fontes de dados, status. Satisfaz briefing §21 (código organizado em
  módulos — já era verdade desde o início, 1 script por etapa) e §22
  (estrutura do pipeline — o diagrama).

### Decisões tomadas e por quê
- **Item 8 do briefing (heatmap dia da semana × horário) adaptado para
  dia da semana × mês, não ignorado**: a unidade de análise do projeto é
  1 dia (decidida na Etapa 4), sem granularidade horária para crime/
  acidente nas 3 fontes principais — a EDA (Etapa 6) já tinha resolvido
  isso com a granularidade temporal mais fina disponível de forma
  consistente. Declarado como adaptação explícita no índice da galeria,
  não uma omissão silenciosa (Regra 10).
- **Figuras novas reusam a mesma exclusão de dias censurados/lacuna de
  registro da Etapa 7** (`EXCL_CRIME`/`EXCL_ACID`), copiada literalmente,
  não redecidida — evita qualquer risco de as 2 novas figuras mostrarem
  uma amostra ligeiramente diferente da que gerou os números já
  publicados nas tabelas `recorte_classico.csv`/`recorte_jogo_noturno.csv`.
- **Nenhum teste estatístico novo nas 2 figuras**: os p-valores/effect
  sizes de clássico e noturno já estão nas tabelas da Etapa 7 — as
  figuras só visualizam o que já foi testado, não reabrem a análise.
- **`README.md` como documento separado do `CLAUDE.md`**: `CLAUDE.md` é
  contexto operacional para assistência de IA (decisões metodológicas
  detalhadas, convenções, pendências); um leitor humano (revisor,
  coautor, o próprio usuário revisitando o projeto depois) precisa de um
  documento mais enxuto e navegável — não duplicado, o `README` referencia
  o `CLAUDE.md`/`Changelog.md` para detalhe em vez de repetir conteúdo.

### Resultado produzido
- `scripts/19_visualizacoes_finais.py`
- `reports/etapa24/figures/` — 2 figuras novas (`00_classico_vs_comum.png`,
  `01_noturno_vs_diurno.png`)
- `reports/etapa24/galeria_visualizacoes.md` — índice dos 15 itens do
  briefing §24
- `README.md` (raiz do projeto)
- `CLAUDE.md` atualizado: status "Etapas 1–20, 23 e 24 concluídas", novas
  seções "Visualizações finais (Etapa 24)" e "`README.md` (§21/22)",
  "Próximos passos" reduzido a só §25 (relatório acadêmico final).

---

## 2026-09-04 — Etapa 25: rascunho do relatório acadêmico final (LaTeX/SBC)

### O que foi feito
- O usuário informou que já existe um projeto Overleaf com os coautores,
  com dois arquivos em `docs/`: `main (1).tex` (proposta original do
  projeto, em tom de trabalho futuro, com cronograma) e `metodologia.tex`
  (Seção 3 já escrita, cobrindo o pipeline real executado). Pediu um novo
  arquivo, `docs/rpII_predicao_acidentes.tex`, usando o mesmo template
  (`sbc-template.sty`, também em `docs/`).
- **Descoberta corrigida**: os autores reais (confirmados pelo e-mail do
  1º autor em `main (1).tex`, que bate com o e-mail do usuário) são
  Gilberto Serafim Dias de Araújo, Leonardo de Cico e Pedro Henrique de
  Almeida — diferentes dos nomes que constavam em versões anteriores deste
  `CLAUDE.md` ("Gustavo Santos El Dib, Rafael Tolentino Limberte, Flavio
  Augusto Faustino de Carvalho"), que estavam desatualizados/incorretos.
  Corrigido no `CLAUDE.md`.
- Criado `docs/rpII_predicao_acidentes.tex`, artigo completo no template
  SBC, montado a partir de 3 fontes:
  1. **Introdução e Trabalhos Relacionados**: adaptados de `main (1).tex`
     (a proposta original), removendo o tom de trabalho futuro
     (``propõe-se'', cronograma) e reformulando como estudo concluído,
     mantendo a fundamentação teórica (Teoria da Atividade Rotineira) e a
     revisão de literatura (Kurland 2014, Ristea 2018/2020), com um novo
     parágrafo final de posicionamento que credita o bloco de causalidade
     formal (Etapa 20) como além da ambição original da proposta.
  2. **Metodologia**: `metodologia.tex` reaproveitado quase verbatim via
     `\input{metodologia}` (já escrito por trabalho anterior e alinhado com
     o pipeline real).
  3. **Resultados, Discussão, Conclusão, Limitações e Trabalhos Futuros**:
     escritos do zero a partir dos números reais das Etapas 6–24 (nenhum
     número inventado) — GLM ajustado (Etapa 7), correlação parcial
     (Etapa 8), defasagens (Etapa 9), DiD espacial e artefato do Morumbi
     (Etapa 10), PSM/IPTW/ITS (Etapa 20), desempenho de regressão e
     classificação pooled walk-forward (Etapas 15–17), SHAP e auditoria de
     colinearidade (Etapa 18), cenários (Etapa 19).
- Criado `scripts/20_figura_artigo.py` → `docs/figuras/` (5 figuras): 2
  novas (diagrama do pipeline de 4 etapas, citado em `metodologia.tex`;
  gráfico de participação bruta vs líquida do grupo futebol no SHAP nos 3
  modelos — a figura central do artigo) e 3 copiadas de relatórios já
  publicados (MAE por fold da Etapa 15, matriz de confusão da Etapa 16,
  beeswarm SHAP da Etapa 18) sem recálculo.
- Adicionadas 5 referências bibliográficas novas (Austin 2011 para PSM,
  Benjamini--Hochberg 1995, Chen \& Guestrin 2016 para XGBoost, Taylor \&
  Letham 2018 para Prophet, Lundberg \& Lee 2017 para SHAP), com `\cite`
  inseridos nos pontos de `metodologia.tex` e do novo texto onde essas
  técnicas são mencionadas mas não tinham citação formal.

### Decisões tomadas e por quê
- **Não inventar dados bibliográficos**: `metodologia.tex` já citava, em
  prosa, ``Soliani et al. (2024)'' e ``da Silva et al. (2025)'' sem
  `\cite`/`\bibitem` e sem prenomes ou dados de volume/página completos
  (só título, periódico e ano, no comentário de cabeçalho do arquivo).
  Em vez de inventar iniciais de autores ou números de volume/página
  (Regra 1/2/3 do briefing -- nunca inventar dados/fontes), os `\bibitem`
  foram criados só com a informação real disponível, com uma nota
  explícita `[Nota dos autores: ... conferir antes da submissão]` pedindo
  aos coautores para completar os dados antes de submeter.
- **Revisão manual completa de sintaxe LaTeX, sem compilar**: o ambiente
  não tem `pdflatex`/`xelatex` instalado. Conferido manualmente: chaves
  balanceadas (154/154 e 65/65), todo `\%` escapado corretamente (nenhum
  `%` cru que cortaria uma linha como comentário), todo `\begin`/`\end`
  pareado, todo `\cite{}` resolve a um `\bibitem{}` e vice-versa (11 chaves
  em cada lado, conferido por grep), todo `\ref{}` resolve a um `\label{}`
  já existente. Declarado explicitamente como não-testado por compilação
  real -- não uma alegação de certeza que não pode ser sustentada.
- **Introdução/Trabalhos Relacionados adaptados, não reescritos do zero**:
  o texto de `main (1).tex` já tinha qualidade e fundamentação teórica
  adequadas; a mudança foi de enquadramento temporal (proposta → estudo
  concluído), preservando citações e estrutura já aprovadas pelos
  coautores na versão anterior.
- **Only 5 figuras no artigo** (não uma por etapa): o limite de 8-10
  páginas do template SBC não comporta uma galeria completa -- priorizadas
  as figuras mais diretamente ligadas às alegações centrais do texto
  (desempenho preditivo, classificação, e a figura do achado central sobre
  futebol vs artefato de calendário).

### Resultado produzido
- `docs/rpII_predicao_acidentes.tex`
- `docs/metodologia.tex` (editado: adicionados `\cite` e a figura do
  pipeline que já era referenciada mas não existia)
- `scripts/20_figura_artigo.py`
- `docs/figuras/` — 5 PNGs (`pipeline.png`, `futebol_liquido.png`,
  `mae_por_fold.png`, `matriz_confusao_acidentes.png`,
  `shap_beeswarm_acidentes.png`)
- `CLAUDE.md` atualizado: coautoria corrigida, nova seção "Artigo final em
  LaTeX (§25)", status marcando o roteiro completo (§1–25) coberto pela
  primeira vez, "Próximos passos" apontando para revisão dos coautores e
  compilação real.

---

## 2026-09-04 — Adendo: revisão pós-compilação real + relatório técnico completo

### O que foi feito
O usuário aplicou correções diretamente em `docs/metodologia.tex`
(`\mathbb{E}\to\mathrm{E}`, `\cite{}` adicionados para as 6 referências que
só apareciam como `\bibitem` sem nunca serem citadas no texto) e compilou o
artigo de verdade (Overleaf/LaTeX local, template aproximado): 16 páginas,
acima do alvo de 8–10 do SBC.

**1. Reinserida a Figura~\ref{fig:pipeline}** em `metodologia.tex`, que o
usuário tinha removido temporariamente (com um comentário `% TODO`) porque
a referência ficava indefinida -- o arquivo `docs/figuras/pipeline.png` já
existia (gerado na Etapa 25 anterior por `scripts/20_figura_artigo.py`),
só faltava o bloco `\begin{figure}...\label{fig:pipeline}...\end{figure}`.

**2. Corte de conteúdo para caber em 8–10 páginas**: `metodologia.tex`
reescrito de forma mais direta (~1000 palavras, ante ~1300) sem remover
nenhuma afirmação substantiva -- só prosa redundante e repetição de
citações. Em `rpII_predicao_acidentes.tex`: as seções de Resultados
mescladas (5 subseções viraram 4), 2 das 4 figuras removidas
(`mae_por_fold`, `shap_beeswarm` -- mantidas `matriz_confusao` e
`futebol_liquido`, que carregam informação não repetida em texto), Tabela 1
reduzida de 5 para 4 colunas (removida a coluna de IC 95%, mantida em
texto).

**3. Bibliografia completada com dados exatos**: o usuário forneceu os
dados bibliográficos completos de Soliani et al. (2024) e da Silva et al.
(2025) (autores completos, volume, número, página/artigo). Os 2 `\bibitem`
que tinham nota `[Nota dos autores: conferir antes da submissão]` foram
atualizados com os dados reais, sem nenhum dado inventado.

**4. Compilação real confirmada pelo usuário**: com a bibliografia
completa, o artigo compilou em **10 páginas incluindo referências** --
dentro do alvo do SBC. O usuário reportou ~19 linhas de espaço sobrando na
página 10 antes das referências; usado para restaurar 2 trechos cortados
com mais força: a decomposição dos 3 mecanismos do achado do Morumbi na
Discussão (antes reduzida a "duas datas extremas e de geocodificação") e a
nota metodológica sobre coordenadas de crime inválidas nas Limitações. A
coluna de IC 95% da Tabela 1 também foi restaurada (não custa linhas, só
largura).

**5. Criado `docs/rpII_predicao_acidentes_relatorio_completo.tex`** -- a
pedido do usuário, uma versão sem limite de páginas, "escrevendo tudo que
seria relevante". Reusa o mesmo template e as mesmas 11 referências, mas
sem nenhum corte: seção "Dados" dedicada (as 109 colunas do
`features_dia_sp.csv` por grupo, com tabela de estatísticas descritivas
dos 2 alvos), Metodologia sem cortes, Resultados em 7 subseções com 12
tabelas completas (GLM com os 11 desfechos, DiD por anel nos 3 estádios,
PSM com balanço de covariáveis, comparação completa de baselines/modelos
em regressão E classificação, tuning de hiperparâmetros, SHAP por grupo
nos 3 modelos, cenários com decomposição completa), as 5 figuras (as 3 do
artigo curto + MAE por fold + beeswarm), sumário (`\tableofcontents`), e
Conclusão respondendo as 12 perguntas do roteiro uma a uma.

**6. Criado `scripts/21_valida_latex.py`** -- ferramenta permanente de
checagem de sintaxe LaTeX sem precisar de `pdflatex` (não disponível neste
ambiente): resolve `\input{}`, verifica chaves balanceadas, número de
colunas de cada linha de tabela contra a especificação do `tabular`, todo
`\cite`/`\ref` resolvendo a `\bibitem`/`\label` e vice-versa, e nenhum `%`
cru fora de linha de comentário. Rodada contra os 2 arquivos `.tex` --
0 problemas em ambos (um `\ref{sec:modelos}` quebrado foi encontrado e
corrigido para `\ref{sec:validacao}` durante essa checagem).

### Decisões tomadas e por quê
- **Cortes de conteúdo, não de rigor**: toda remoção em `metodologia.tex`/
  `rpII_predicao_acidentes.tex` foi de prosa redundante, repetição de
  citação ou detalhe secundário (ex.: 1 coluna de tabela) -- nenhuma
  afirmação, número ou resultado foi removido. Onde havia dúvida sobre
  quanto cortar, preferiu-se cortar menos e confirmar com o usuário depois
  de uma compilação real, em vez de arriscar remover conteúdo relevante
  baseado só em estimativa de página sem `pdflatex` local.
- **Bibliografia nunca inventada**: mesmo sob pressão de espaço/tempo, os 2
  `\bibitem` incompletos ficaram sinalizados como pendência (Regra 1/2/3)
  até o usuário fornecer os dados reais -- nunca preenchidos com
  prenomes/volume/página adivinhados.
- **Relatório completo como documento separado, não substituindo o
  artigo SBC**: mantém o artigo dentro do formato de submissão (8–10
  páginas) intacto, e cria um documento de referência técnica completo à
  parte, sem comprometer nenhum dos dois objetivos (submissão vs.
  documentação exaustiva).
- **Script de validação salvo em `scripts/`, não deixado só no scratchpad
  da sessão**: scratchpads são efêmeros; uma ferramenta que substitui (em
  parte) a ausência de `pdflatex` neste ambiente precisa persistir para
  qualquer edição futura nesses arquivos.

### Resultado produzido
- `docs/metodologia.tex` (figura do pipeline reinserida, texto condensado)
- `docs/rpII_predicao_acidentes.tex` (Resultados condensados, 2 figuras
  removidas, bibliografia completa, pequena expansão calibrada de ~19
  linhas) -- **compilado com sucesso pelo usuário, 10 páginas com
  referências**
- `docs/rpII_predicao_acidentes_relatorio_completo.tex` (novo, sem limite
  de páginas)
- `scripts/21_valida_latex.py` (novo)
- `CLAUDE.md` atualizado: seção "Artigo final em LaTeX (§25)" reescrita
  com o resultado da compilação real, os 2 arquivos `.tex` e a ferramenta
  de validação; "Próximos passos" reduzido a revisão final dos coautores.

## Adendo (2026-09-05): restauração de conteúdo pós-compilação real (2ª rodada)

### Contexto
O usuário recompilou `docs/rpII_predicao_acidentes.tex` de verdade (Overleaf)
e contou manualmente: 10 páginas totais com referências, mas o CONTEÚDO
(Introdução até Trabalhos Futuros, excluindo resumo/abstract/referências)
ocupava só ~8,3 páginas — sobrava margem real (~2 páginas), contradizendo a
suposição anterior de que o corte da rodada 1 já tinha atingido o limite.
O corte anterior (feito sem `pdflatex` local, só por estimativa) havia sido
mais conservador do que o necessário.

### O que foi restaurado (todos os números vêm de CSVs já publicados nas
Etapas 8/10/14/15/17/18/19 — nada recalculado ou inventado)
- **Tabela GLM (`tab:glm`, §4.1)**: voltou a ter as 11 linhas de desfecho
  (crimes totais, violentos, roubos, furtos, lesão corporal, homicídios,
  sinistros totais/com vítima/atropelamento/colisão/fatais), não só as 4
  citadas no texto. Colunas trocadas de (Bruto%, RR, IC, p) para
  (RR, IC, p, p_BH) — o p_BH deixa explícito que nenhum resíduo sobrevive
  à correção mesmo antes de olhar o IC.
- **Achado colateral de Fisher exato** (5/12 dias-pico de crimes violentos
  em dia de jogo, OR=3,51, some sob 3 ajustes triviais) devolvido ao corpo
  do texto — tinha sido cortado na rodada 1.
- **Tabela DiD por anel de distância (`tab:did-anel`, §4.2)**: devolvida,
  mostrando os 3 estádios lado a lado (Neo Química Arena RR≈0,95 ns;
  Allianz Parque RR≈1,17-1,18 persistente mas sem pile-up; Morumbi
  2,66→1,24 ao remover as 2 datas de alavancagem) — sem essa tabela o texto
  só mencionava o Morumbi, perdendo o contraste com os outros 2 estádios.
- **Tabelas completas de comparação de modelos (§4.3)**: regressão
  (`tab:regressao`, 7 candidatos por alvo: baselines + Prophet + Random
  Forest + XGBoost Poisson) e classificação (`tab:classificacao`, 4-5
  candidatos por alvo) — a rodada 1 tinha reduzido cada uma ao único
  vencedor, perdendo a evidência de "venceu contra o quê".
- **2 figuras devolvidas**: `mae_por_fold.png` (estabilidade da vantagem do
  XGBoost ao longo dos 12 folds, não só a média pooled) e
  `shap_beeswarm_acidentes.png` (visualização direta da distribuição de
  SHAP por atributo). Total voltou a 4 figuras (de um máximo de 5; o
  diagrama do pipeline mora na Metodologia via `\input`).
- **"Interpretabilidade e cenários" separado de volta em 2 subseções**
  (`Interpretabilidade (SHAP)` e `Análise de cenários`), como estava antes
  do corte.
- **Discussão ganhou um 3º parágrafo**: implicação prática para alocação de
  efetivo policial/fiscalização (não sustentada por dados de futebol) e
  reflexão sobre o achado de Fisher como exemplo de por que testes
  isolados sem checagem de robustez não devem embasar política pública.
- **`docs/metodologia.tex`**: "Fontes de dados" voltou a ser uma lista
  (`itemize`) com detalhe por fonte (grão do BO, encoding do Infosiga,
  definição de clássico, fuso do INMET, feriados por algoritmo de Páscoa)
  em vez do parágrafo corrido condensado da rodada 1; parágrafo de
  atributos ganhou as contagens exatas por grupo (95 atributos, 26/20/11/38
  por grupo temporal/futebol/clima/histórico).

### Validação
`python scripts/21_valida_latex.py docs/rpII_predicao_acidentes.tex` → 0
erros estruturais (271=271 chaves, 4 tabelas com nº de colunas correto,
11 `\cite`/11 `\bibitem` e 9 `\ref`/9 `\label` todos resolvendo, 0 `%` cru).
Compilação real (`pdflatex`) ainda pendente — usuário precisa recompilar e
confirmar se o conteúdo agora preenche melhor as 8–10 páginas do SBC sem
estourar.

### Resultado produzido
- `docs/metodologia.tex` (fontes de dados em itemize, contagem de
  atributos por grupo)
- `docs/rpII_predicao_acidentes.tex` (tabela GLM completa, tabela DiD por
  anel, tabelas de regressão/classificação completas, 2 figuras
  restauradas, subseções separadas, Discussão com 3º parágrafo)
- `CLAUDE.md` atualizado (seção "Artigo final em LaTeX" com o novo status
  de compilação pendente de reconfirmação)

---

# V2: análise por janelas de horário

## V2 / Fase 1 (2026-11-15): base horária

### Contexto
A professora pediu para refazer a análise no grão de janelas de horário em torno de
cada jogo (PRÉ = 2h antes, DURANTE = início..+2h, PÓS = +2h..+4h, FORA), com crimes
e sinistros validados separadamente. Roteiro em `docs/prompt_v2_janelas.md`.

### O que foi feito
- `scripts/30_eventos_horarios.py` (rascunho anterior revisado e executado pela 1ª
  vez): bronze → `data/silver/crime_eventos_sp.csv.gz` (974.737 linhas BO×natureza)
  e `acidentes_eventos_sp.csv.gz` (90.829 sinistros), timestamp local e `tem_hora`;
  tabela de qualidade da hora por tipo e por arquivo. Correções sobre o rascunho:
  aceita o artefato Excel `1900-01-01 HH:MM:SS` como hora válida (36 registros
  recuperados); datas no campo hora (`2000-06-01 00:00:00`, 20 registros) = sem hora;
  `CATEGORIAS_VIOLENTAS` importada de `02_limpeza.py` (não copiada); conferência com
  o silver diário.
- `scripts/31_jogos_horarios.py`: 1 registro por jogo com `inicio_br` (fuso
  corrigido), flags clássico/noturno/fim de semana/competição/feriado, estádio
  habitual assumido (coordenadas da Etapa 10) + checagem do GLM diário da Etapa 7
  com as datas corrigidas.
- `scripts/32_base_horaria.py`: `data/gold/fato_hora_sp.csv` (17.520 × 58) +
  dicionário `fato_hora_sp_dicionario.csv`; janelas pela regra do ponto médio
  (hh:30) na linha do tempo contínua; teste de seleção dos registros sem hora;
  relatório `reports/janelas/fase1_base_horaria.md`.

### Bug do pipeline diário encontrado e corrigido (na base nova)
- `BR-Football-Dataset.csv`: `time` está no horário do Reino Unido (GMT/BST) e
  `date` é a data UK. `02_limpeza.py` usava ambos como se fossem de Brasília.
- Consequências: **52/137 jogos (38%) estavam no dia seguinte**; `jogo_noturno`
  (hora UK ≥ 19) **errado em 108/137 jogos**; os **11 "dias com 2 jogos"** citados
  desde a Etapa 1 eram todos artefato (0 dias com 2 jogos após a correção; 126 → 137
  dias de jogo).
- `01:24:28` = São Paulo × Flamengo, Copa do Brasil 2022 (21:24:28 em Brasília). Três
  jogos de SP capital (e 4% da base inteira) têm segundos ≠ 00, padrão de carimbo de
  coleta → arredondados a 30 min, flag `horario_aproximado`.
- **Checagem do GLM diário (Etapa 7) com datas corrigidas: o nulo se mantém** — 0/11
  desfechos significativos após BH por domínio. `acidentes_fatais` fica um pouco mais
  forte (RR 1,164, p = 0,025 sem correção; p_BH = 0,124). `fato_dia_sp.csv` e as
  Etapas 7–24 **não foram refeitas** (só checagem, como pedido).

### Achados de qualidade
- Crimes: 33,9% sem hora (furtos 52,8%; roubos 8,1%; lesão dolosa 8,6%;
  `crimes_violentos` 8,6%), estável nos 4 arquivos; 32,9% no minuto :00 e 53,1% em
  :00/:30 → grão de 1 hora. 00:00 não é placeholder (hora 0 não incha vs 23h/1h).
- Sinistros: 0,10% sem hora, sem arredondamento relevante (2,5% no :00).
- Lote de furtos de 2022-06-19: 83% sem hora → cai quase todo em `sem_hora_furtos_total`.
- **Teste de seleção** (GLM binomial diário com calendário, BH por domínio): em dia de
  jogo a proporção sem hora é um pouco maior em `lesao_corporal_dolosa` (OR 1,16;
  ~8,5% → ~9,8%) e `crimes_violentos` (OR 1,06; +0,5 p.p.) — limitação pequena, viés
  para baixo de ~1,4%/0,5% na contagem horária em dia de jogo. Roubos, furtos e os 3
  tipos de sinistro: sem seleção.

### Decisões
- Janela por ponto médio da hora; `hora_relativa` = ⌊(hh:30 − início)/1h⌋ ∈ [−6, 12];
  prioridade DURANTE > PÓS > PRÉ (não usada: 0 sobreposições).
- FORA dividido em `fora_dia_jogo` / `dia_sem_jogo` pela data de Brasília; 726 horas
  `dia_sem_jogo` estão a +4..+12h de um jogo da noite anterior (o event study isola).
- Exclusões como flags por domínio (`excluir_crime`, `excluir_sinistro`), linhas mantidas.
- Clima NaN fica NaN (chuva 3,7% das horas, temperatura 1,2%).

### Resultado produzido
- `scripts/30_eventos_horarios.py`, `31_jogos_horarios.py`, `32_base_horaria.py`
- `data/silver/{crime,acidentes}_eventos_sp.csv.gz`, `jogos_sp_horario.csv`, `qualidade_hora.csv`
- `data/gold/fato_hora_sp.csv`, `fato_hora_sp_dicionario.csv`
- `reports/janelas/fase1_base_horaria.md`, `reports/janelas/fase1/{tabelas,figuras}/`

## V2 / Fase 1 — adendo (2026-11-15): calendário completo de jogos

### Contexto
Usuário aprovou o item opcional do prompt V2 (completar o calendário antes da Fase 2),
ampliado para Paulistão, Libertadores, Sul-Americana **e Recopa**, com fonte verificável,
horário de Brasília confirmado, estádio real e exclusão de mandos fora da capital —
conferindo isso também nos 137 jogos da base original.

### O que foi feito
- **`scripts/31a_jogos_complementares.py`** (novo): baixa (API da Wikipédia, com espera e
  retry por limite de taxa) e lê snapshots de 19 páginas em `data/bronze/wikipedia/`
  (+ `manifesto.json` com revid/timestamp). Fonte primária = páginas de temporada de cada
  clube na Wikipédia em inglês (cada partida é um *football box* com data, horário com fuso
  explícito `{{UTZ|HH:MM|-3}}`, cidade, estádio, público, súmula). Páginas de edição
  (Libertadores, Sul-Americana, Recopa, Paulistão en/pt) = conferência cruzada — a página de
  edição do Paulistão na pt.wikipedia só tem tabela cruzada de placares na fase de grupos (sem
  data/hora/estádio), por isso não serve de primária. FPF não usada (desafio Cloudflare).
  Saídas: `data/bronze/jogos_complementares.csv` (86 jogos, `fonte_jogo` = permalink `oldid`),
  `data/bronze/jogos_base_conferencia_wikipedia.csv` (conferência dos 137).
- **`31_jogos_horarios.py`** integra os dois: calendário completo com `na_base_original`,
  `incluir_analise`, `motivo_exclusao`, estádio real (todos conferidos) e checagem do GLM
  diário com 3 versões (antigo / datas corrigidas / calendário completo).
- **`32_base_horaria.py`** regenerado: janelas pelo calendário completo (principal) +
  `janela_base_original`/`hora_relativa_base_original`/`dia_de_jogo_base_original`
  (robustez da Fase 2) + `hora_jogo_fora_capital`; teste de seleção nas 2 versões;
  relatório ganhou a seção 1b. `fato_hora_sp.csv` agora 17.520 × 64.

### Resultados
- **85 jogos novos em SP capital**: Paulistão 48, Libertadores 20, Sul-Americana 15, Recopa 1,
  + 1 jogo de Série A ausente do BR-Football-Dataset (Palmeiras × Bragantino, 13/05/2023,
  conferido em 2ª fonte). Todos com horário em UTC−3 explícito (0 sem horário confirmado);
  33 conferidos em página de edição com 0 divergência de horário; data conferida com o link
  da súmula do ge (0 divergência). Final da Sul-Americana 2022 (Córdoba) excluída (campo neutro).
- **137/137 jogos originais com horário convertido idêntico ao da Wikipédia** — confirmação
  independente da correção do fuso.
- **7 dos 137 jogos originais eram mandos fora da capital** (6 na Arena Barueri, 1 na Vila
  Belmiro — shows no Allianz/Morumbi; 6 confirmados em 2ª fonte) → excluídos; suas horas
  PRÉ/DURANTE/PÓS ficam com flag `hora_jogo_fora_capital` (42 h) para sair da comparação.
- 3 jogos na capital em estádio não habitual (Palmeiras no Morumbi ×2; São Paulo × Água Santa
  no Allianz, Coldplay no Morumbi) → estádio real usado.
- **Calendário analisável: 215 jogos** (130 originais + 85). Jan–mar: horas de jogo
  6 → 288, dias de jogo 1 → 48 (a violação de positividade de jan–fev da Etapa 20 deixa de
  existir). **0 dias com 2 jogos** mesmo com 215 jogos.
- **GLM diário (spec Etapa 7) com calendário completo deixa de ser nulo total**:
  `furtos_total` RR 1,040 (p_BH 0,024) e `crimes_totais` RR 1,029 (p_BH 0,024), sobrevivendo ao
  BH do domínio crime; sinistros seguem nulos após BH. Checagem diária, não a estimativa do
  projeto — a Fase 2 testa com janelas/EF/placebo.
- **Teste de seleção** (sem hora × dia de jogo): com o calendário completo não há seleção
  após BH (lesão p bruto 0,026, OR 1,08, p_BH 0,10); com a base original havia
  (`lesao_corporal_dolosa`, `crimes_violentos`). Ambas as tabelas no relatório.
- Achado colateral não integrado: as páginas de temporada trazem o **público de todos os
  224 jogos em casa** (numérico) — resolveria a pendência de público desde a Etapa 12.

### Decisão para a Fase 2 (do usuário)
Análise principal = calendário completo (`janela`); robustez = só base original
(`janela_base_original`, os 130 jogos do BR-Football em SP capital já corrigidos).

## V2 / Fase 1 — adendo 2 (2026-11-15): Santos, jogos fora da capital e público

### Pedido do usuário
(1) Santos como 4º time monitorado; (2) duas categorias não exclusivas — `janela` (jogos dos
4 times na capital) e `janela_fora_capital` (jogos dos 4 times fora da capital, com
simultaneidade, times e flag RMSP), horário local convertido para Brasília pelo fuso da página;
(3) público integrado nos jogos da capital, NaN se ausente, portões fechados/restrito marcados,
amostra de ~20 em 2ª fonte; verificar jogos de grande público na capital sem os 4 times.

### O que foi feito
- `31a`: + páginas *2022/2023 Santos FC season* (data sem ano → ano da página; fuso
  `[[UTC-03:00]]`; "Arena Corinthians" → Neo Química Arena). Nova tabela única de todos os jogos
  oficiais dos 4 times, sem duplicata entre páginas (517: 216 na capital, 301 fora), com
  `inicio_br = hora_local + (−3 − offset)`. Saída nova `data/bronze/jogos_fora_capital.csv`.
  Validação do fuso fora da capital contra o BR-Football-Dataset (200/200) e páginas de edição
  CONMEBOL (40/40) depois de corrigir 5 horários em que a Wikipédia errou (3ª fonte em
  `horario_corrigido_fonte`). Público + `publico_status` a partir de `attendance`/`note`.
- `31`: público nos jogos da capital; regra COVID (teto 70% em 23/01–09/03/2022, fonte
  registrada) aplicada a todos os jogos do período; `data/silver/jogos_fora_capital_horario.csv`.
- `32`: colunas `janela_fora_capital`, `hora_relativa_fora_capital`, `n_jogos_fora_simultaneos`,
  `times_fora_capital`, `jogo_id_fora_capital`, `fora_capital_rmsp`, `hora_sem_jogo`,
  `jogo_publico`, `jogo_publico_status`; removido `hora_jogo_fora_capital`. 17.520 × 72.
  Relatório ganhou seções 1c–1f.
- `data/bronze/publico_conferencia_amostra.csv` (20 jogos, 2ª fonte) e
  `data/bronze/jogos_grande_publico_sem_times_monitorados.csv` (4 candidatos, não incluídos).

### Resultados
- Santos mandante na capital 1 vez (Santos × Ferroviária, 28/01/2023, Canindé) → `janela`
  passa a 216 jogos. Canindé sem coordenada no projeto (lat/lon NaN).
- `janela_fora_capital`: 301 jogos, 453/541/466 horas PRÉ/DURANTE/PÓS; até 4 jogos simultâneos;
  17 jogos na RMSP. Sobreposição com `janela` existe (ex. 39 horas DURANTE nas duas).
  Controle `hora_sem_jogo` = 11.520 horas.
- Público: 216/216 com valor; 201 ok, 14 capacidade restrita, 1 portões fechados (Corinthians ×
  Vasco, 29/07/2023, punição). Amostra: 18/20 encontrados, 17 idênticos, 1 com 0,6% de
  diferença; a Wikipédia usa público total (ESPN às vezes o pagante). FPF e fbref bloqueiam
  acesso automatizado (não contornado).
- Grande público sem os 4 times (time principal masculino): finais do Brasileirão Feminino
  2022 (41.070) e 2023 (42.566) na Neo Química e finais da Copinha sub-20 2022/2023 — aguardam
  decisão do usuário.
- GLM diário e teste de seleção praticamente inalterados com o jogo do Santos.

## V2 / Fase 1 — ajustes finais (2026-11-16)
- Eventos de grande público sem os 4 times (finais do Brasileirão Feminino 2022/2023 e da Copinha
  2022/2023): horário de início confirmado na imprensa (10h, 14h, 15h30, 16h); horas PRÉ/DURANTE/PÓS
  marcadas `excluir_evento_grande_publico` (24 h) — nem tratamento nem controle (decisão do usuário).
- `CLAUDE.md`: linhas antigas de público, Paulistão e as 2 pendências que bloqueavam o roteiro
  marcadas como superadas na V2.

## V2 / Fase 2 (2026-11-16): análise explicativa por janelas — `scripts/33_analise_janelas.py`

### O que foi feito (tudo separado para crimes e para sinistros; BH por domínio)
1. Descritivo (janela vs mesmas horas/dia da semana sem jogo; perfil horário; alinhado pela hora do jogo).
2. Modelo principal: GLM Poisson horário com as duas categorias juntas (C_pre/durante/pos + C_fdj e
   F_pre/durante/pos), EF hora×dia da semana + ano×mês + feriado/véspera/férias + chuva/temperatura,
   cluster por semana; controle = hora sem jogo dos 4 times. Robustezes: NB, cluster por dia, só janela,
   só base original, com as horas dos eventos de grande público, total diário (crimes).
3. Event study −6..+12 para as duas categorias (pedido do usuário) + teste de pré-tendência.
4. Placebo/permutação (1.000 sorteios, dois passos em forma fechada).
5. Heterogeneidade (clássico, noturno, fim de semana, competição, resultado só no PÓS, RMSP, por time
   incl. Santos) e dose-resposta do público (log e tercis; cidade toda e entorno de 3 km).
6. Espaço × tempo: disco de 3 km de cada estádio (crime sem células de pile-up + versão por bairros)
   vs resto da cidade; agregado por inverso da variância; sensibilidade do Morumbi sem os 2 jogos da
   Copa do Brasil 2023.
7. Controles pareados (mesmo dia da semana, ±4 semanas, sem jogo, sem feriado; DiD vs horas fora).
8. Pico horário (Pearson e cauda Poisson, P90/P95; sinistros também 2 h) + validação em 12 folds.

### Correção feita durante a fase (antes de qualquer conclusão)
A 1ª versão do placebo ajustava o modelo de base com as horas de jogo dentro e sorteava em ±6 semanas:
os EF hora×dia da semana absorviam parte do efeito (jogos concentrados em poucas células) e o pool de
candidatos ficava pequeno (mediana 2 por jogo fora da capital) → distribuição descentrada (até −10%) e p
artificialmente baixo até em janelas nulas no GLM. Corrigido: base ajustada só nas horas sem jogo da
categoria testada, candidatos em toda a amostra (mediana 48/31 por jogo). Crimes: placebo centrado
(desvio ≤ 1,3%); sinistros ainda com até 6% de descentramento em horas tardias (declarado; vale o GLM).

### Resultados
**Crimes:** cidade toda, capital PRÉ `crimes_violentos` +4,7% (p_BH 0,041; placebo p<0,001; NB e cluster
dia ok) e `roubos_total` +5,3% (p_BH 0,041) → "efeito robusto" pela regra; PÓS +2,7% (não robusto);
DURANTE −2,1% (ns). MAS: pré-tendência rejeitada (p=0,007, sinais mistos; k=−3 já +3,9%) e o desenho
pareado não confirma o PRÉ (+1,2%, IC −2,8 a +5,3) — mostra queda DURANTE (−6,8%, IC −10,8 a −3,0).
O PRÉ é da cidade toda (resto +4,9%, p=0,002), não do entorno. No entorno de 3 km dos estádios:
DURANTE +15% (p=0,035) e PÓS +31% (p<0,001); Morumbi +58%/+64%, sobrevive sem os 2 jogos da Copa do
Brasil (+54%/+41%) e sem pile-up. Dose: PRÉ cresce com o público (tercis +1,7%/+4,5%/+9,1%). Fora da
capital (TV): nulo em todas as janelas; event study com indício isolado em +10 h (IRR 1,048, p=0,037).
Pico P90 mais frequente só no PRÉ da capital (RR 1,31, Fisher p=0,041). Pico de crime estável
(prevalência fora da amostra 8,1% média).
**Sinistros:** nulo na cidade toda nas duas categorias (todos p_BH ≥ 0,69), sem pré-tendência, pareado
nulo, dose nula, picos sem diferença. Único sinal: entorno de 3 km no PRÉ +46% (p=0,001; Neo Química
+69%), base muito pequena (~0,1 sinistro com vítima/hora por estádio). Pico de sinistros com
prevalência fora da amostra acima de 10% (12,9% média; dezembro 21%) — tendência de alta de 2023 que
o EF ano×mês não extrapola; pico por 2 h não melhora → nível hora.

### Saídas
`reports/janelas/crimes/relatorio_fase2_crimes.md`, `reports/janelas/sinistros/relatorio_fase2_sinistros.md`,
`reports/janelas/resumo_fase2.md`, tabelas e figuras em `reports/janelas/{crimes,sinistros}/`.
`REUSA=1 python scripts/33_analise_janelas.py` refaz só placebo + relatórios a partir das tabelas.

## V2 / Fase 2b (2026-11-16): checagens de robustez — `scripts/33b_robustez_janelas.py`
Modelo principal da Fase 2 inalterado; só robustezes. Crimes e sinistros separados.

### Mudanças no `33_analise_janelas.py`
- **Regra do veredito revista (1e):** entre os candidatos (p_BH<0,05, placebo p<0,05, NB e cluster dia
  com mesmo sinal): "efeito robusto" só se o pareado **confirma**; "robusto no GLM, pareado
  inconclusivo" se não confirma nem contradiz; "contradito pelo pareado" se o IC95 do pareado exclui a
  estimativa do GLM. PRÉ de `crimes_violentos`/`roubos_total` passou a "robusto no GLM, pareado inconclusivo".
- Exploratórios (horas tardias do event study, entorno de sinistros) reportados com p_BH e sem destaque.
- EF hora × mês/trimestre construídos SÓ como interações (hora 1..23 × mês 2..12): com dummies cheias a
  matriz tinha posto incompleto e o LAPACK (gelsd) estourava memória.
- `controles_pareados` grava a lista dos jogos usados (`controles_pareados_jogos.csv`).

### Resultados
- **1a (EF hora × mês):** PRÉ `crimes_violentos` +4,7% → +2,7% (p=0,053); `roubos_total` +5,3% → +2,9%
  (p=0,060); hora × trimestre +3,6%/+3,8% (p≈0,02). ~45% do PRÉ era sazonalidade do perfil horário.
- **1b (só os 112 jogos do pareado):** +4,1% (p=0,026) sem hora×mês → não é diferença de amostra; com
  hora×mês +2,0% (p=0,25), perto do pareado (+1,2%). A discrepância GLM × pareado era sobretudo o controle
  de sazonalidade do perfil horário.
- **1c (dose com hora×mês):** gradiente por público persiste no PRÉ e PÓS (tercil alto PRÉ +6,2%, p=0,011;
  PÓS +5,0%, p=0,024; interação log(público) no PÓS 1,109, p=0,007).
- **1d (PRÉ estendido k=−3..−1):** +4,6% (p=0,001); com hora×mês +2,9% (p=0,017) — resíduo pequeno que
  resiste, compatível com deslocamento de torcedores.
- **2a (BH espacial):** crimes, 3 estádios agregados: `crimes_violentos` PÓS +31% (p_BH<0,001), DURANTE
  +15% (p_BH 0,055 disco / bairros +22%, p_BH 0,017); `furtos_total` +32%/+66%/+85% (PRÉ/DURANTE/PÓS,
  p_BH<0,001); `roubos_total` PÓS +39% (p_BH<0,001); lesão DURANTE +104% (p_BH<0,001). 28 termos por
  estádio sobrevivem ao BH (família de 72), concentrados em furtos (3 estádios) e no Morumbi.
- **2b (deslocamento):** DURANTE, 8/12 combinações estádio × desfecho com entorno >1 e resto da cidade <1;
  resto da cidade nas janelas dos jogos fica ~igual (0,95–1,02), exceto o PRÉ (+5%, cidade toda).
- **2c (DESCR_CONDUTA, exploratório):** excesso de furto no entorno = furto de veículo (O/E 2,3; ~metade do
  excesso) e de transeunte (O/E 2,7); roubo: "OUTROS" (O/E 1,25). BOs sem conduta preenchida sobem muito
  (furto O/E 17,5; roubo 3,8) — assinatura compatível com registro na operação do estádio.
- **2d:** leituras alternativas não testáveis escritas no relatório (policiamento → registro; mais gente →
  mais contagem sem mais risco por pessoa, Kurland, Johnson e Tilley 2014).
- **3 (exploratórios):** horas tardias +8..+12 com p<0,05 têm p_BH 0,25–0,35 (não sobrevivem); sinistros
  entorno PRÉ +46% (p_BH 0,004 na família dos agregados), base ~0,1/hora — exploratório.
- **Sinistros:** PRÉ nulo em todas as checagens (hora×mês, 112 jogos, estendido, dose).

### Saídas
`reports/janelas/{crimes,sinistros}/relatorio_fase2b_<dom>.md`, `tabelas/fase2b_*.csv`,
`reports/janelas/resumo_fase2b.md`. `REUSA=1 python scripts/33b_robustez_janelas.py` refaz só os relatórios.

## V2 / Fase 3 (2026-11-17): canal de registro + bloco preditivo

### Item 0 — canal de registro no entorno (`scripts/34a_canal_registro.py`)
- Lê o bronze (delegacia de registro, `DESCR_SUBTIPOLOCAL`, `DESCR_CONDUTA`) no disco de 3 km; conferência:
  contagens da versão original idênticas às do `33` (diferença 0).
- **DRADE: só 10 BOs** no entorno em 2022–2023 — não existe posto/canal do estádio. 64% dos registros do
  entorno são da Delegacia Eletrônica (BO online); 13% sem conduta.
- Modelo do entorno (Fase 2) reestimado sem cada canal, 3 estádios agregados:
  - **furtos** sobem nos dois canais (presencial PÓS 2,05; online PÓS 1,81) → robusto ao canal;
  - **crimes violentos e roubos no PÓS vêm só do BO online** (1,44 e 1,49; presencial 1,00 e 1,11 ns) —
    no BO online o local é declarado pela vítima (mesmo problema de localização da Etapa 10);
  - crimes violentos DURANTE some sem os BOs sem conduta (1,15 → 1,07 ns).

### Bloco preditivo (`scripts/34_preditivo_janelas.py`)
- Previsão na véspera; só variáveis conhecidas (calendário, agenda de jogos, público histórico do mandante,
  clima perfeito + variante com clima da véspera, histórico com defasagem ≥ 24 h). Cidade e entorno de 3 km
  (estádio como variável). Baseline (média hora × dia da semana 4 semanas), GLM Poisson (spec da Fase 2 com
  mês do ano + tendência), XGBoost Poisson (raso, fixo), Prophet (só cidade). Walk-forward 12 folds de 2023.
  Ablação com/sem variáveis de jogo, IC por bootstrap em blocos de semana.
- **Crimes:** melhor modelo = XGBoost (cidade: deviance 1,643 vs GLM 1,845, Prophet 1,824, baseline 1,926).
  Jogo **não muda a previsão no geral** (ganho ≤ 1%), mas **ajuda nas horas de jogo**: cidade XGBoost
  −3,9% de deviance e −0,12 de MAE nas janelas (com clima conservador −5,6%); entorno furtos XGBoost
  −13,9% / GLM −8,7% de deviance nas janelas; entorno crimes violentos/roubos −4,6%/−3,8% de deviance mas
  MAE igual (ganho só na cauda). Pico/hora de risco: variáveis de jogo **não** melhoram PR-AUC (diferenças
  ≤ 0,004; PR-AUC 0,10–0,15 vs prevalência 0,05–0,08).
- **Sinistros:** melhor modelo na cidade = GLM; jogo não ajuda (cidade ns; entorno GLM piora −4,5% nas
  janelas). Pico sem ganho.
- **SHAP** (rodado porque a ablação de crimes mostrou ganho): variáveis de jogo ≤ 1,2% do SHAP total,
  |rho| com a hora do dia ≤ 0,28 → não fazem papel de calendário, mas pesam pouco.
- **Tabela de risco** por estádio × janela (domingo 16h, quarta 21h30): excesso em 2 h de janela abaixo de
  1 ocorrência por janela; maiores excessos — Morumbi crimes violentos DURANTE +0,67 (IC 0,21–1,26) sobre
  base 1,15; furtos Neo Química DURANTE/PÓS +0,66/+0,71 sobre base ~0,7.
- Notas: deviance do baseline no entorno inflada por previsões zero (comparar pelo MAE).

### Saídas
`reports/janelas/crimes/relatorio_fase3_canal_registro.md`, `reports/janelas/{crimes,sinistros}/relatorio_fase3_preditivo_<dom>.md`,
`reports/janelas/resumo_fase3.md`, tabelas `fase3_*`. `REUSA=1` refaz só os relatórios.

## V2 — Artigo da 3ª entrega (2026-11-17)
- Base: `../entrega_parcial/entrega2/main.tex` e `referencias.bib` **copiados** (sem sobrescrever) para a
  pasta nova `../entrega_parcial/entrega3/`, onde o artigo foi reescrito com os resultados da V2.
- `scripts/35_figuras_artigo_v2.py` gera, só a partir de `reports/janelas/` e `data/`: `fig_event_study.png`,
  `fig_entorno.png`, as tabelas `tab_janelas/tab_pre/tab_canal/tab_preditivo/tab_risco.tex` (incluídas por
  `\input`) e `reports/janelas/artigo/numeros_artigo.csv` (481 números com a tabela de origem).
- `referencias.bib`: + Ivandić et al. (2024); DOIs em Montolio & Planells-Struse (2016) e Kurland et al. (2014).
- Seções: resumo novo; introdução nas 5 partes com o objetivo oficial **literal** e a delimitação explicando a
  hora e as 4 janelas (objetivos específicos (i)–(iii) reescritos para a V2); correlatos com Montolio,
  Ivandić e Kurland na tabela e no texto; metodologia em 2 páginas com a justificativa de cada escolha;
  resultados em 5 subseções (tabela por janela com veredito, event study, PRÉ e sazonalidade, entorno +
  canal de registro, preditivo, tabela de risco com coluna de furtos corrigida pela proporção com hora);
  discussão/conclusão substituindo "efeito de calendário, não do jogo".
- `docs/defesa_metodologia.md`: 34 perguntas prováveis com respostas curtas.
- Validação: `21_valida_latex.py` → chaves balanceadas, 5 tabelas com colunas corretas, 0 `%` cru; o
  "erro" de `\cite` sem `\bibitem` é do validador (o artigo usa BibTeX) — conferido à parte: todas as
  citações têm entrada no `.bib`, nenhum `\ref` sem `\label`. Compilação real pendente (sem LaTeX local).

---

# V3: fechamento da 3ª entrega (2026-11-19)

### Aprovação
- O usuário revisou os resumos e **aprovou os resultados das Fases 2, 2b e 3 e o artigo da 3ª entrega
  (2026-11-19)**. `CLAUDE.md`: "aguardando revisão" → "aprovada pelo usuário (2026-11-19)".

### Ambiente (SSD novo)
- A sessão anterior foi perdida na troca de SSD. A máquina nova não tinha Python nem Git: instalados via
  winget (com autorização) Python 3.14.10 + launcher `py` e Git 2.56.0; no 3.14, só `numpy`, `pandas`,
  `matplotlib` (o que o 35 importa; o 21 usa só a stdlib). Scripts 30–34 não rodados de novo.

### Objetivos (`entrega3/main.tex`)
- Objetivo geral trocado (era o da entrega 2: "dias", 3 mandantes) pelo texto do usuário: horas em torno dos
  jogos dos 4 times, na capital e fora, crimes violentos/roubos/furtos/sinistros com vítima, previsão horária
  e detecção de pico. Objetivos específicos passam a 4: (i) variação por janela (cidade e entorno para a
  capital; cidade para fora); (ii) **novo**: pico mais frequente nas janelas; (iii) ganho de erro da
  previsão; (iv) PR-AUC.
- Coerência: frase "Para que isso possa ser verificado..." (agora cita crimes e sinistros separados), parágrafo
  de delimitação (partes explicativa e preditiva, sem rótulos (i)/(ii) que colidiam com os objetivos) e fim
  do 1º parágrafo da Discussão, respondendo os 4 objetivos separadamente para crimes e sinistros. Resumo não
  contradizia nenhum objetivo — mantido. Título não alterado.

### Validação do pico (pedido da professora)
- Subseção nova "Horas de pico" em Resultados (crimes e sinistros em parágrafos separados): prevalência fora da
  amostra nos 12 folds contra 10% (crimes média 8,1%, faixa 3,6–19,9%; sinistros 12,9%, 7,5–21,1%, 9/12 folds
  acima de 10%), nível de agregação (sinistros: 2 h não melhora, desvio 4,4 vs 3,5 p.p.), concordância
  (κ P90×cauda 0,98/0,96; P95 ⊂ P90, Jaccard 0,50) e frequência por janela (crimes só PRÉ capital RR 1,31,
  Fisher p=0,041, **p_BH 0,244** nas 6 janelas; sinistros nada, maior RR 1,68 com P95 em 2 h, p=0,055).
- Metodologia, parágrafo "Pico": + frase da validação (esperado e limiar reestimados só no treino de cada
  fold mensal; prevalência no teste vs 10%; sinistros também em 2 h).
- `35_figuras_artigo_v2.py`: `bh()` e `tab_pico()` → `tab_pico.tex` (painéis (a) validação e (b) RR por
  janela; domínios em blocos separados, nunca somados) e 459 números novos (`pico_tab.*`) em
  `numeros_artigo.csv` (481 → 940). Conferência: 5 tabelas antigas idênticas byte a byte; as 481 linhas antigas
  idênticas em `chave`/`valor`/`fonte` (só `valor_bruto` difere na 16ª casa pela versão do pandas). PNGs com
  diferença de renderização (matplotlib novo) → figuras aprovadas restauradas do backup.

### Compilação
- `docs/sbc-template.sty` copiado para `entrega3/`. **`sbc.bst` não encontrado** no projeto nem em
  `entrega_parcial/` (usuário vai pegar no template do SBC).
- `21_valida_latex.py`: chaves balanceadas (417), 7 tabelas com colunas corretas, 0 `%` cru; único erro = falso
  positivo do `\cite` (as 17 chaves citadas existem no `referencias.bib`).

### Git
- `.gitignore` novo (bronze, uploads, `__pycache__`, `*.pyc`, auxiliares de LaTeX). 12 arquivos brutos já
  rastreados desde o 1º commit (maior 51,6 MB) → proposto `git rm -r --cached data/bronze uploads`, não executado.
  Nenhum arquivo do próximo commit passa de 100 MB (total ~44 MB). Nada commitado.

### Depois (mesmo dia)
- Remoto estava vazio: `main` recriado como commit único sem brutos; V2/V3 no PR #1, mergeado pelo usuário.
  Histórico original só na branch local `historico-setembro`. `*_eventos_sp.csv.gz` no `.gitignore`.
- `sbc.bst` extraído do template enviado pela professora; `.sty` do template idêntico ao do projeto.
- 1ª compilação real: 14 páginas, seções dentro dos limites. `\clearpage` antes da Discussão (Tabelas 6–7
  partiam a seção 5).
- Título trocado (decisão do usuário): "Crimes e Sinistros de Trânsito nas Horas em torno dos Jogos de
  Futebol na Cidade de São Paulo: Efeito por Janela e Ganho Preditivo".

# V3b: novos trabalhos correlatos (2026-11-19)
Só `entrega3/main.tex` e `referencias.bib`. Textos lidos na íntegra antes de escrever (Masiero: PDF de acesso
aberto da UNIGE; Recife: PDF da RBERU); Wood conferido no Crossref e na página da OUP (resumo).
- **Masiero (2022)**, JSE 23(8):1076–1095: 93 distritos policiais, 2006–2014, roubos e furtos por hora, 430
  jogos de Copa do Mundo/Confederações/Libertadores (73 em SP). Roubos −7,5% durante os jogos (incapacitação
  voluntária), antecipação para antes do jogo; **nos 3 distritos dos estádios roubos +28,3% e furtos +150%**,
  sem *deslocamento* espacial dos vizinhos. Atenção: o prompt dizia "sem efeito espacial no nível de distrito";
  o artigo encontra concentração local — o texto da Discussão segue o artigo. Entrou na 2.1, Tabela 1,
  lacuna da introdução, Síntese e Discussão.
- **Santos e Silveira Neto (2023)**, RBERU 17(2):237–261: painel horário 2011–2015, 743 jogos (341 casa, 402
  fora), binomial negativa com indicadores −7..+7 h; roubos e furtos na hora anterior, furtos durante, violência
  doméstica na 1ª hora depois; nulo para homicídio/lesão/entorpecentes; dose de público (+11,4% roubos e +30,3%
  furtos por 10 mil); conclusão: jogos fora de Recife não afetam (as figuras mostram reduções pontuais depois
  desses jogos). Entrou na 2.2, Tabela 1, Síntese e Discussão.
- **Wood, McInnes e Norton (2011)**, JCR 38(4):611–621, doi 10.1086/660164 (título registrado: "...Game-Day
  *Traffic* Fatalities"; o DOI 10.1086/659379 que circula é de outro artigo). 271 jogos decisivos/clássicos
  2001–2008, mais mortes no trânsito em jogos mais disputados, só onde há torcedores do vencedor. Entrou na 2.2
  com Redelmeier e na Tabela 1.
- Lacuna da introdução e Síntese reescritas: o efeito horário em SP já foi medido (Masiero); novo aqui = disco de
  3 km por estádio (vs distrito), jogos fora da capital como categoria com calendário doméstico, sinistros,
  ganho preditivo. Discussão: PRÉ vs Masiero/Recife (metade do PRÉ é hora×mês, controle que nenhum dos dois usa),
  disco vs distrito (unidade de área), TV nula vs queda de roubos de Masiero.
- `.bib`: `Ivandi{\'c}` corrigido; + `masiero2022sports`, `santos2023jogos`, `wood2011bad`. Card e Dahl enxugado.
- Validação: 21 ok (429 chaves, 7 tabelas), 20 citações todas no `.bib`, sem travessão nem "americano".
  Não compilado.

# V4: revisão pelo parecer (2026-11-20)
O artigo **`../entrega_parcial/rp_ii/main.tex`** (PDF `RP_II (1).pdf`) foi escrito por um colega fora deste
ambiente, a partir da entrega3 e sem o caminho diário, e **passou a ser a versão oficial do artigo**. Um parecer
externo revisou essa versão; o roteiro com os pontos aceitos está em `docs/prompt_v4_parecer.md`. A `entrega3/`,
a `entrega2/` e os `.tex` de `docs/` não foram tocados.

### Fase 1 (análises novas) — aprovada pelo usuário
- **Conferências:** o grão da contagem de crime era BO × natureza (+0,19% em crimes violentos; usuário decidiu
  deduplicar). Os 137 jogos da base original = 130 na capital + 7 mandos em Barueri/Vila Belmiro. Crimes violentos
  inclui roubos e lesão corporal dolosa. Tabelas do `rp_ii` eram transcrições à mão dos `tab_*.tex` (linhas de
  dados idênticas); `thebibliography` sem `.bib`; sem origem em CSV: "10 boletins da DRADE" e a coluna "Abs. corr."
  da Tabela 7. Janela: fim = BR-Football; início exclui 2020–2021 por COVID (resposta do usuário).
- **`scripts/36_revisao_parecer.py`** (novo; lê `fato_hora_sp.csv` e o silver de eventos, recalcula as contagens
  por BO único; cache do `DESCR_CONDUTA` em `data/silver/crime_conduta_eventos_sp.csv.gz`, fora do git) →
  `reports/janelas/revisao/`:
  - 1.1 modelo da cidade com EF hora × mês: nenhuma janela sobrevive ao BH (crimes PRÉ +2,9%, p_BH 0,205;
    sinistros nulos); DURANTE GLM −1,6% × pareado −6,8%.
  - 1.2 entorno por diferença em diferenças (GLM binomial disco × resto da cidade, IRLS-FWL conferido contra o
    statsmodels): furtos D+P +71%, roubos PÓS +43%, crimes violentos PÓS +36% ("efeito robusto"; roubos/violentos
    só no BO online); sinistros com vítima PRÉ +47% robusto; raio 1/2/3/5 km monotônico; fator empírico dos furtos
    sem hora 5,0 (substitui 2,12). Regra de parada (furtos no entorno) não acionada.
  - 1.3 5 jogos do Brasil na Copa de 2022 excluídos (30 h; Wikipédia, permalinks no script). O bloco preditivo
    não foi refeito: o teste é 2023 e não é afetado.
  - 1.4 pico com hora × mês no esperado: respostas ao objetivo (ii) não mudam após BH; definição mantida.
  - Correções durante a fase: pareado do entorno dos sinistros com correção de continuidade (+0,5; somas zero no
    bootstrap) e coeficiente por estádio sem nenhum evento na janela marcado como ausente (era IRR 0).
- Pacotes instalados no Python 3.14: `statsmodels`, `scipy`.

### Fase 2 (artigo) — aprovada pelo usuário
- `35_figuras_artigo_v2.py`: modo padrão `ARTIGO=rp_ii` com funções `*_v4` (tabelas 2–7, incluindo a Tabela 3
  nova de robustez, e as 2 figuras) gravadas no `rp_ii` e entrando por `\input`; `numeros_artigo.csv` com chaves
  `v4.*`; o arquivo antigo preservado como `numeros_artigo_entrega3.csv` (`ARTIGO=entrega3` regenera a 3ª entrega).
- `main.tex`: título "Variação por Janela"; resumo e discussão só com os resultados novos; linguagem de
  associação; Masiero (2022) citado e lacuna reescrita; Ristea et al. (2020) corrigido; Metodologia reescrita
  (definições, funil, ponto médio, exclusões, hora × mês, diferença em diferenças, hiperparâmetros, motivo da
  janela, disponibilidade do código com os autores); parágrafo do GLM diário/fuso apagado; limitações 6 → 8.
- `21_valida_latex.py` aceita `\bibitem[rótulo]{chave}`. Validação: 0 problemas. Não compilado (sem LaTeX local).
- Relatório da fase: `reports/janelas/revisao/fase2_artigo.md`.

### Fase 3 (documentação)
- `CLAUDE.md`: seção "V4: revisão pelo parecer", próximos passos. `.gitignore`: + cache de conduta. Nada commitado.
