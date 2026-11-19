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
