# Projeto: Predição de picos de violência/acidentes em dias de jogo — São Paulo

## Contexto
Artigo acadêmico (USP) em LaTeX, template SBC. **Coautoria corrigida em 2026-09-04**:
os autores reais, confirmados em `docs/main (1).tex` (e-mail do 1º autor bate com o
e-mail do usuário) são Gilberto Serafim Dias de Araújo, Leonardo de Cico e Pedro
Henrique de Almeida — os nomes "Gustavo Santos El Dib, Rafael Tolentino Limberte,
Flavio Augusto Faustino de Carvalho" citados em versões anteriores deste arquivo
estavam desatualizados/incorretos; não usar mais. Objetivo: sistema de ciência de
dados comparando XGBoost e Prophet para prever picos de crime/acidentes em dias de
jogo dos clubes de futebol de São Paulo capital. O roteiro completo do projeto
(27 seções, regras de rigor metodológico) está em `docs/briefing_original.md` — leia
antes de continuar qualquer etapa. Regras inegociáveis do briefing: nunca inventar
dados/URLs, nunca usar random split em série temporal, sempre comparar com baseline,
diferenciar correlação de causalidade, declarar limitação em vez de fabricar solução.

## Artigo final em LaTeX (§25 — ver `docs/`)
- `docs/rpII_predicao_acidentes.tex`: artigo completo (template SBC), integra
  `docs/main (1).tex` (proposta original — Introdução/Trabalhos Relacionados
  adaptados de tempo futuro para estudo concluído) e `docs/metodologia.tex`
  (Seção 3, já escrita por trabalho anterior, incluída via `\input{metodologia}`)
  com Resultados/Discussão/Conclusão/Limitações/Trabalhos Futuros NOVOS, escritos
  a partir dos números reais das Etapas 1–24 (nunca inventados). **Compilado de
  verdade pelo usuário (2026-09-04)**: 10 páginas com referências — mas o próprio
  usuário recontou e viu que o CONTEÚDO (excluindo resumo/abstract/referências)
  ocupava só ~8,3 das 10 páginas, sobrando margem real. **Conteúdo restaurado no
  mesmo dia** (2ª rodada, depois do 1º corte ter sido conservador demais): tabela
  GLM voltou a ter as 11 linhas de desfecho (não só 4), tabela DiD por anel
  (Neo Química/Allianz/Morumbi) restaurada na análise espacial, tabelas completas
  de comparação de modelos (regressão e classificação, todos os candidatos, não
  só o vencedor) restauradas em Resultados, as 2 figuras que tinham sido cortadas
  (MAE por fold, beeswarm SHAP) voltaram, "Interpretabilidade e cenários" separado
  de volta em 2 subseções, Discussão ganhou um 3º parágrafo (implicação prática +
  achado colateral de Fisher), e a Metodologia ganhou de volta a lista de fontes
  de dados em itemize. Validado com `scripts/21_valida_latex.py`: 0 erros
  estruturais. **Ainda não recompilado pelo usuário após esta 2ª rodada** —
  próximo passo é recompilar e conferir se ainda cabe em 8–10 páginas de
  conteúdo.
- `docs/rpII_predicao_acidentes_relatorio_completo.tex`: **versão estendida sem
  limite de páginas** (mesmo template, mesmas referências), a pedido do usuário —
  não corta nada, inclui todas as tabelas completas (GLM com os 11 desfechos, DiD
  por anel, PSM com balanço, comparação completa de baselines/modelos regressão E
  classificação, tuning de hiperparâmetros, SHAP por grupo nos 3 modelos, cenários
  com decomposição), seção "Dados" dedicada (as 109 colunas do
  `features_dia_sp.csv` por grupo), sumário (`\tableofcontents`) e as 5 figuras
  (as 3 do artigo curto + MAE por fold + beeswarm SHAP). Serve de material de
  referência/apoio, não é para submissão em formato SBC.
- **Referências bibliográficas completas (2026-09-04)**: os 2 `\bibitem`
  incompletos (Soliani et al. 2024, da Silva et al. 2025) foram preenchidos com
  os dados exatos fornecidos pelo usuário (Soliani, R.D. et al., *Multimodal
  Transportation* 3(4), 100173; da Silva, J.P. et al., *Computers, Environment
  and Urban Systems* 121, 102306) — pendência de verificação fechada, nos 2
  arquivos `.tex`.
- `docs/figuras/`: 5 figuras geradas por `scripts/20_figura_artigo.py` — 3 copiadas
  de relatórios já publicados (MAE por fold, matriz de confusão, beeswarm SHAP) e
  2 novas (diagrama do pipeline; participação líquida vs bruta do futebol no SHAP,
  a figura mais importante do artigo).
- Compilação: requer que `docs/` seja a raiz do projeto LaTeX (usa
  `\input{metodologia}` e `\includegraphics{figuras/...}`, ambos caminhos
  relativos a `docs/`). **`scripts/21_valida_latex.py <arquivo.tex>`** faz
  checagem de sintaxe sem precisar de `pdflatex` (chaves balanceadas, nº de
  colunas de cada tabela, todo `\cite`/`\ref` resolvendo a `\bibitem`/`\label`,
  nenhum `%` cru fora de comentário) — rodar contra os 2 arquivos acima depois
  de qualquer edição futura neles, já que não há LaTeX local neste ambiente.

## V2: análise por janelas de horário (em andamento desde 2026-11-15)
A professora considerou o grão DIA ruim e pediu a análise por janelas em torno de
cada jogo (PRÉ 2h antes / DURANTE início..+2h / PÓS +2h..+4h / FORA), com crimes
e sinistros **sempre separados** (cálculo, pico, BH, tabelas, conclusão). Roteiro:
`docs/prompt_v2_janelas.md` (Fases 1–3, checkpoint ao fim de cada fase; não
commitar; não editar os `.tex` até o usuário aprovar os resultados).
- **Fase 1 concluída e APROVADA pelo usuário (2026-11-16)**: scripts
  `30` → `31a` → `31` → `32` → `data/silver/{crime,acidentes}_eventos_sp.csv.gz`,
  `data/bronze/jogos_complementares.csv`, `jogos_fora_capital.csv`,
  `data/silver/jogos_sp_horario.csv`, `jogos_fora_capital_horario.csv`,
  `data/gold/fato_hora_sp.csv` (17.520 horas × 72, dicionário em
  `fato_hora_sp_dicionario.csv`), relatório `reports/janelas/fase1_base_horaria.md`.
  Rodar com `py -3.14` (o `python` padrão desta máquina não tem pandas). `31a` usa os
  snapshots em `data/bronze/wikipedia/`; `--baixar` só busca os que faltam.
- **4 times monitorados (decisão do usuário, 2026-11-15 — substitui "Santos fica de fora")**:
  Corinthians, Palmeiras, São Paulo e **Santos** (páginas *2022/2023 Santos FC season*).
- **Duas categorias de jogo, colunas separadas e NÃO exclusivas (decidido — não redecidir)**:
  - `janela` (pre/durante/pos/fora_dia_jogo/dia_sem_jogo): jogos dos 4 times **em estádio da
    capital** — 216 jogos (130 da base original + 85 Paulistão/Libertadores/Sul-Americana/
    Recopa + 1 Série A ausente da base; inclui Santos × Ferroviária no Canindé, único mando do
    Santos na capital). Efeito da multidão perto do estádio.
  - `janela_fora_capital` (pre/durante/pos/nenhum): jogos dos 4 times **fora da capital** —
    301 jogos (fora de casa dos 3 clubes, Santos na Vila e fora, os 7 mandos em Barueri/Vila
    Belmiro, exterior, Supercopa). Efeito de assistir pela TV/bares. Com
    `n_jogos_fora_simultaneos`, `times_fora_capital`, `fora_capital_rmsp` (RMSP, ex. Barueri).
    Horário convertido para Brasília com o fuso da própria página; validado 200/200 contra o
    BR-Football e 40/40 contra páginas de edição (5 erros da Wikipédia corrigidos com 3ª fonte).
  - Controle = `hora_sem_jogo` (nenhuma janela dos 4 times nem dia de jogo na capital).
  - Fonte: páginas de temporada (Wikipédia en, permalink `oldid`); 137/137 horários originais
    idênticos à Wikipédia após a correção do fuso.
- **Público (decidido)**: integrado só para os jogos da `janela` (capital), público TOTAL da
  Wikipédia; ausente = NaN, nunca zero; status `ok`/`capacidade_restrita` (COVID 23/01–09/03/
  2022, teto 70%, por regra com fonte)/`portoes_fechados` (1: Corinthians × Vasco 29/07/2023,
  público 0 real). Amostra de 20 em 2ª fonte: 18 achados, 17 idênticos, 1 a 0,6%. Fora da
  capital o público do estádio não entra na análise.
- **Plano da Fase 2 (pedido do usuário, não redecidir)**: modelo principal com dummies de
  `janela` E `janela_fora_capital` juntas, controle = hora sem nenhum jogo dos 4 times; os dois
  efeitos reportados à parte, sempre separado crimes × sinistros; heterogeneidade por time nas
  duas categorias (incluindo Santos); público como dose-resposta SÓ na `janela` (interação com
  log(público) + tercis; cidade toda e entorno do estádio); robustez: (a) só `janela` (sem
  jogos fora da capital) e (b) só base original (`janela_base_original`). **Fase 3: público
  real não é conhecido antes do jogo — só pode entrar como média histórica do mandante.**
- **Eventos de grande público sem os 4 times (decidido pelo usuário)**: finais do Brasileirão
  Feminino (24/09/2022 14h, 10/09/2023 16h, Neo Química) e da Copinha sub-20 (25/01/2022 10h
  Allianz, 25/01/2023 15h30 Canindé) — nem tratamento nem controle: horas PRÉ/DURANTE/PÓS com
  `excluir_evento_grande_publico=True` (24 h) fora da amostra principal; robustez com elas de volta.
- **Fase 2 também faz event study (−6..+12) para `janela_fora_capital`** (pedido do usuário:
  efeito de TV pode aparecer ~10 h depois, Ivandić et al. 2024). Estrutura confirmada: as duas
  categorias juntas no modelo = os dois tipos de jogo; crimes e sinistros em modelos separados,
  um modelo por desfecho, BH por domínio.
- **GLM diário (spec Etapa 7) com calendário completo**: `furtos_total` RR 1,040 e
  `crimes_totais` RR 1,029 sobrevivem ao BH do domínio crime (p_BH 0,024) — o "nulo" do
  trabalho diário era em parte diluição por dias de Paulistão/Libertadores marcados como sem
  jogo. É checagem, não estimativa; a Fase 2 decide.
- **BUG DO FUSO no pipeline diário (supera dados do trabalho antigo)**: `time` e
  `date` do `BR-Football-Dataset.csv` estão no horário/data do Reino Unido. Afeta
  `02_limpeza.py`/`fato_dia_sp.csv` e tudo que deriva dele: 52/137 jogos no dia
  errado, `jogo_noturno` errado em 108/137, os "11 dias com 2 jogos" eram artefato
  (são 0). Correção só na base V2 (`31_jogos_horarios.py`: `tz_localize('Europe/London')`
  → `tz_convert('America/Sao_Paulo')`). Checagem: o GLM diário da Etapa 7 com datas
  corrigidas mantém o nulo (0/11 após BH por domínio; `acidentes_fatais` RR 1,164,
  p=0,025 sem correção, p_BH=0,124). As Etapas 7–24 e o artigo NÃO foram refeitos;
  qualquer número que dependa de `jogo_noturno` ou da data exata do jogo no trabalho
  diário deve ser lido com essa ressalva.
- Decisões da Fase 1: grão 1h (crime tem 33% no minuto :00); janela pelo ponto médio
  hh:30 em linha do tempo contínua; `hora_relativa` ∈ [−6, 12]; FORA dividido em
  `fora_dia_jogo`/`dia_sem_jogo`; horários com segundos ≠ 00 (3 jogos, incl.
  `01:24:28`) arredondados a 30 min com flag (os 3 batem com a Wikipédia).
- Qualidade da hora: crime 33,9% sem hora (furtos 52,8%, roubos 8,1%, lesão 8,6%);
  sinistro 0,1%. **Seleção**: com o calendário completo, nenhuma após BH (lesão p bruto
  0,026, OR 1,08); com a base original havia (lesão OR 1,16, `crimes_violentos` OR 1,06).
  Por cautela, a Fase 2 reporta junto o total diário desses 2 tipos.
- **Fase 2 concluída (2026-11-16), aprovada pelo usuário (2026-11-19)** — `scripts/33_analise_janelas.py` (~13 min;
  `REUSA=1` refaz só placebo + relatórios a partir das tabelas salvas) → `reports/janelas/crimes/`,
  `reports/janelas/sinistros/`, `reports/janelas/resumo_fase2.md`. Resultados (não re-descobrir):
  - **Crimes, cidade toda:** capital PRÉ `crimes_violentos` +4,7% e `roubos_total` +5,3% (p_BH 0,041,
    placebo e NB/cluster-dia ok → "efeito robusto" pela regra do script), PÓS +2,7% (não robusto),
    DURANTE −2,1% ns. Ressalvas: pré-tendência rejeitada (p=0,007, sinais mistos, k=−3 já +3,9%) e o
    desenho pareado NÃO confirma o PRÉ (+1,2% ns) mas mostra queda DURANTE (−6,8%, IC exclui 0). O PRÉ é
    da cidade toda (resto +4,9%), não do entorno; cresce com o público (tercis +1,7/+4,5/+9,1%).
  - **Crimes, entorno de 3 km dos estádios:** DURANTE +15% (p=0,035), PÓS +31% (p<0,001); Morumbi
    +58%/+64%, sobrevive sem pile-up e sem os 2 jogos da Copa do Brasil 2023 (+54%/+41%) — o grão
    horário revela o que o diário (Etapa 10) diluía.
  - **Crimes fora da capital (TV):** nulo; indício isolado em +10 h no event study (p=0,037, sem correção).
  - **Sinistros:** nulo na cidade toda nas duas categorias, pareado e dose nulos, sem pré-tendência;
    só o entorno de 3 km no PRÉ (+46%, p=0,001, base ~0,1/hora por estádio).
  - **Placebo corrigido durante a fase** (base ajustada só nas horas sem jogo da categoria; candidatos em
    toda a amostra). Em sinistros ainda há até 6% de descentramento nas horas tardias → vale o GLM.
  - **Pico:** crimes nível hora, estável (prevalência fora da amostra 8,1% média), mais frequente só no
    PRÉ da capital (RR 1,31, p=0,041); sinistros nível hora (2 h não melhora), prevalência fora da
    amostra 12,9% média (tendência de 2023 não extrapolada), sem diferença por janela.
- **Fase 2b concluída (2026-11-16), aprovada pelo usuário (2026-11-19)** — `scripts/33b_robustez_janelas.py` (~7 min;
  `REUSA=1` só relatórios) → `reports/janelas/*/relatorio_fase2b_*.md`, `resumo_fase2b.md`.
  - **Regra do veredito (decidida):** "efeito robusto" só se o pareado CONFIRMA; senão "robusto no GLM,
    pareado inconclusivo" ou "contradito pelo pareado". PRÉ de crimes = "robusto no GLM, pareado inconclusivo".
  - **PRÉ de crimes é ~45% sazonalidade do perfil horário** (EF hora×mês: +4,7%→+2,7%, p=0,053); não é
    diferença de amostra (112 jogos do pareado sem hora×mês: +4,1%); com os dois: +2,0% ns ≈ pareado.
    Resíduo pequeno no PRÉ estendido k=−3..−1 com hora×mês: +2,9% (p=0,017). Dose por público persiste.
  - **Entorno dos estádios é o resultado mais forte e sobrevive ao BH espacial:** crimes violentos PÓS
    +31%, furtos +66–85% DURANTE/PÓS, roubos PÓS +39% (p_BH<0,001); deslocamento (entorno sobe, resto da
    cidade ~igual DURANTE). Excesso de furto = veículo e transeunte; BOs sem `DESCR_CONDUTA` sobem 17×
    (indício de canal de registro). Leituras alternativas não testáveis: policiamento → registro;
    população presente (Kurland, Johnson e Tilley 2014).
  - Exploratórios: horas tardias do event study não sobrevivem ao BH (p_BH 0,25–0,35); sinistros entorno
    PRÉ +46% (p_BH 0,004, base ~0,1/h).
  - Atenção técnica: EF hora×mês/trimestre SÓ como interações (`_interacoes_hora` no 33); dummies cheias
    dão posto incompleto e MemoryError no LAPACK. Rodar com `PYTHONIOENCODING=utf-8` (console cp1252).
- **Fase 3 concluída (2026-11-17), aprovada pelo usuário (2026-11-19)** — `34a_canal_registro.py` (~3 min) e
  `34_preditivo_janelas.py` (~16 min; `REUSA=1` só relatórios; `N_FOLDS=1` teste rápido;
  `SEM_PROPHET=1`). Resultados (não re-descobrir):
  - **Canal de registro:** DRADE só 10 BOs (não há canal do estádio). Furtos no entorno sobem nos BOs
    presenciais E online (robusto); **crimes violentos/roubos PÓS no entorno vêm só do BO online** (local
    declarado pela vítima) — ressalva forte para esse resultado.
  - **Preditivo (crimes):** XGBoost é o melhor modelo; Prophet e GLM piores (comparação do título:
    XGBoost > Prophet). Saber que haverá jogo **não melhora a previsão no geral**, mas **melhora nas horas
    de jogo** (cidade −3,9% deviance/−0,12 MAE; entorno furtos −13,9%); em crimes violentos/roubos do
    entorno o ganho é só de deviance (cauda), MAE igual. Pico/hora de risco: sem ganho de PR-AUC.
  - **Preditivo (sinistros):** jogo não ajuda (entorno GLM até piora). GLM é o melhor na cidade.
  - SHAP: variáveis de jogo ≤ 1,2% do total, não colineares com a hora (|rho| ≤ 0,28).
  - Produto: tabela de risco estádio × janela (`fase3_tabela_risco_estadio_janela.csv`): excesso < 1
    ocorrência por janela de 2 h; maiores: Morumbi crimes violentos DURANTE, furtos na Neo Química.
- **Artigo da 3ª entrega escrito (2026-11-17), aprovado pelo usuário (2026-11-19)**; ajustes da V3
  (objetivos, subseção de pico, preparação da compilação) em 2026-11-19, compilação real pendente — pasta nova
  `../entrega_parcial/entrega3/` (cópia da entrega2; a entrega2 e os `.tex` de `docs/` NÃO foram tocados).
  Figuras e tabelas `tab_*.tex` geradas por `scripts/35_figuras_artigo_v2.py` (não editar à mão; números
  rastreáveis em `reports/janelas/artigo/numeros_artigo.csv`). Objetivo oficial mantido literal; objetivos
  específicos reescritos para a V2. `docs/defesa_metodologia.md` = perguntas/respostas para a apresentação.
  Validar com `21_valida_latex.py` (o aviso de `\cite` sem `\bibitem` é falso positivo: usa BibTeX).

## V3: fechamento da 3ª entrega (2026-11-19)
- **Entregável atual = `../entrega_parcial/entrega3/main.tex`** (artigo da V2, por janelas de horário),
  aprovado pelo usuário em 2026-11-19 junto com as Fases 2, 2b e 3. O artigo diário de setembro
  (`docs/rpII_predicao_acidentes*.tex`) e a `entrega2/` ficam como histórico — não editar.
- Ajustes da V3 no `main.tex`: objetivo geral e 4 objetivos específicos reescritos para a V2 (hora, 4 times,
  jogos na capital e fora; (ii) novo = pico mais frequente nas janelas), delimitação da introdução e fim do
  1º parágrafo da Discussão respondendo os 4 objetivos separadamente para crimes e sinistros; subseção
  nova "Horas de pico" (`sec:res_pico`) + frase de validação no parágrafo "Pico" da Metodologia.
- `tab_pico.tex` gerada por `tab_pico()` no `35_figuras_artigo_v2.py` (chamada depois de `numeros_extras()`
  para não mudar a ordem dos números antigos); números novos com prefixo `pico_tab.` em `numeros_artigo.csv`
  (940 linhas; as 481 antigas idênticas no valor formatado). O 35 calcula o BH das 6 janelas por domínio
  sobre os p de Fisher já publicados (transformação, não reestimação): PRÉ de crimes p=0,041 → p_BH 0,244.
- Com matplotlib/pandas novos (SSD novo) o 35 gera PNGs com diferença só de renderização; as figuras
  aprovadas foram restauradas. Se rodar o 35 de novo, restaurar `fig_*.png` ou aceitar a diferença visual.
- Compilação: `sbc-template.sty` copiado para `entrega3/`; **`sbc.bst` não existe no projeto nem em
  `entrega_parcial/`** — o usuário vai pegar no template do SBC. `21_valida_latex.py` precisa de caminho
  absoluto (ou relativo à raiz do projeto); único "erro" = falso positivo do `\cite` (BibTeX).
- Título mantém "Dias de Jogos" (não mudar sem o usuário; sugestão registrada no resumo da sessão V3).

## Status do trabalho DIÁRIO antigo (histórico; o atual é a V2/V3 acima): Etapas 1–20, 23 e 24 concluídas e revisadas, incl. auditoria pooled/fold_macro do ROC-AUC e PR-AUC e auditoria de colinearidade com calendário no SHAP (checkpoint 2026-09-04). Todas as pendências abertas fechadas nesse mesmo checkpoint: auditoria completa do grupo futebol (0,0% líquido nos 3 modelos), robustez do SHAP a hiperparâmetro raso vs produção (confirmada), e discrepância PSM/IPTW da Etapa 20 (resolvida — era violação de positividade). §21/22 satisfeitos por `README.md`. **§25 (relatório final) compilado de verdade pelo usuário e dentro do alvo de páginas do SBC** (`docs/rpII_predicao_acidentes.tex`, 10 páginas c/ referências); referências bibliográficas completas; também existe uma versão estendida sem limite de páginas (`docs/rpII_predicao_acidentes_relatorio_completo.tex`). Falta só revisão final dos coautores. Roteiro completo (§1–25) coberto pela primeira vez neste checkpoint.
## Nota: numeração das "Etapas" deste projeto = numeração das Seções do próprio `docs/briefing_original.md` (Etapa 6 = §6 EDA, ..., Etapa 14 = §14 Modelos ML). Daqui pra frente: §15 séries temporais/validação, §16 métricas, §17 otimização, §18 interpretabilidade/SHAP, §19 cenários, §20 causalidade, §21+ código/pipeline/resultados/visualizações/relatório final.
- Etapa 6 (EDA): `scripts/03_eda.py` → `reports/eda/`
- Etapa 7 (jogo vs não-jogo): `scripts/04_analise_jogo_vs_naojogo.py` → `reports/etapa7/`
- Etapa 8 (análise estatística): `scripts/05_analise_estatistica.py` → `reports/etapa8/`
- Etapa 9 (defasagem D-2..D+2): `scripts/06_analise_defasagem.py` → `reports/etapa9/`
- Etapa 10 (espacial): `scripts/07_analise_espacial.py` → `reports/etapa10/`
- Etapa 11 (definição de pico): `scripts/08_definicao_pico.py` → `reports/etapa11/` + `data/gold/pico_dia_sp.csv`
- Etapa 12 (feature engineering): `scripts/09_feature_engineering.py` → `reports/etapa12/` + `data/gold/features_dia_sp.csv`
- Etapa 13 (baselines): `scripts/10_baselines.py` → `reports/etapa13/`
- Etapa 14 (modelos ML): `scripts/11_modelos.py` → `reports/etapa14/`
- Etapa 15 (validação temporal walk-forward): `scripts/12_validacao_temporal.py` → `reports/etapa15/`
- Etapa 16 (métricas — consolidação formal): `scripts/13_metricas_consolidadas.py` → `reports/etapa16/`
- Etapa 17 (otimização de hiperparâmetros): `scripts/14_otimizacao_hiperparametros.py` → `reports/etapa17/`
- Etapa 18 (interpretabilidade SHAP): `scripts/15_interpretabilidade_shap.py` → `reports/etapa18/`
- Etapa 19 (análise de cenários): `scripts/16_analise_cenarios.py` → `reports/etapa19/`
- Etapa 20 (causalidade formal): `scripts/17_analise_causalidade.py` → `reports/etapa20/`
- Etapa 23 (resultados esperados — 12 perguntas do briefing): `scripts/18_resultados_finais.py` → `reports/etapa23/`
- Etapa 24 (visualizações finais — galeria dos 15 itens): `scripts/19_visualizacoes_finais.py` → `reports/etapa24/`
- `README.md` (raiz do projeto): arquitetura, diagrama do pipeline (§21/22), como rodar — documento para humanos, complementa este `CLAUDE.md`
- Registro por etapa em `docs/Changelog.md` (o que foi feito / decisões / saídas)

## Convenção de defasagem D-1/D0/D+1 — RESOLVIDA e auditada (2026-09-04)
Convenção única do projeto = a do gold (`02_limpeza.py`), relativa ao **dia do
desfecho**, não ao dia do jogo:
- `jogo_d_menos_k[dia] = tem_jogo_sp[dia-k]` = "houve jogo há k dias" → efeito
  **POSTERIOR / rescaldo** (k dias depois do jogo).
- `jogo_d_mais_k[dia]  = tem_jogo_sp[dia+k]` = "há jogo daqui a k dias" → efeito
  **ANTECIPATÓRIO / véspera** (k dias antes do jogo).
- `jogo_d0` = jogo no mesmo dia.

Auditoria de `06_analise_defasagem.py` confirmada: a Seção 1 (defasagens
distribuídas) já calculava certo, só o rótulo do relatório estava trocado —
corrigido para usar os nomes das colunas do gold diretamente (autoexplicativo,
sem "D+1"/"D-1" ambíguo). A Seção 4 (Kruskal-Wallis por janela) usava a
convenção **oposta à Seção 1 dentro do mesmo script** — bug real, não só rótulo;
corrigido, `KW_H`/`KW_p` inalterados. Toda a prosa revisada. Etapa 12 e Seção 9
do artigo usam esta convenção: "antecipatório" = `jogo_d_mais_*`, "posterior" =
`jogo_d_menos_*`.

## Achado central das Etapas 7–10 (não re-descobrir)
A associação bruta entre dia de jogo e desfechos (lesão corporal +15%, acidentes +6%,
acidentes fatais +39%) **desaparece após controlar dia da semana e mês**: GLM Poisson
ajustado sem efeito significativo (Etapa 7); correlação parcial de todos os 44 pares
driver×desfecho cai a ~0 (Etapa 8); nenhuma das 30 defasagens `jogo_d_menos_2`..
`jogo_d_mais_2` é significativa após BH (Etapa 9) — sem efeito antecipatório nem
posterior. Kruskal-Wallis: `dia_semana` ε²≈0,16–0,41 vs `numero_jogos_sp` ε²≈0,01.
Único resíduo: acidentes fatais em `jogo_d0` ~+15% (p≈0,06, não robusto).

**Etapa 10 (espacial) — investigada e explicada, não só descartada**: o RR ~3
aparente no Morumbi se decompôs em 3 mecanismos concretos, todos verificados: (1)
concentrado em 2 datas (final + semifinal da Copa do Brasil 2023, não dia de jogo
comum), (2) ~60% de "pile-up" de geocodificação no ponto do próprio estádio (BOs
online geocodificados ao endereço declarado, não ao local real), (3) 75%+ é furto
simples, não crime violento. Reportar como observação investigada, não como achado
espacial robusto — é uma história melhor pro artigo do que simplesmente omitir ou
aceitar o RR bruto.

Conclusão geral: efeito de calendário, não do jogo. Sem causalidade.

**Implicação para o resto do projeto**: quatro métodos independentes (Etapas 7, 8,
9, 10) convergem no mesmo nulo. É provável que `tem_jogo_sp`/`classico`/
`numero_jogos_sp` tenham importância baixa no SHAP (Etapa 18) e que as respostas às
perguntas da Seção 23 do briefing (clássico/noturno/público influenciam?) sejam
"não, controlado por calendário" — isso é um resultado científico legítimo, não uma
falha do pipeline. Preparar a Discussão do artigo em torno disso desde já.

## Arquitetura de dados (bronze → silver → gold)
- `data/bronze/`: cópias brutas das fontes, sem transformação
- `data/silver/`: uma tabela diária por fonte, já harmonizada e filtrada para SP capital
- `data/gold/fato_dia_sp.csv`: dataset analítico final — **1 linha = 1 dia**, SP capital,
  2022-01-01 a 2023-12-31 (730 dias), 69 colunas. Chave primária: `data`.
- `data/gold/pico_dia_sp.csv`: flags de pico (Etapa 11) — chave `data`, 40 colunas.
  `02_limpeza.py` faz merge disso nos placeholders `pico_*` do fato quando o arquivo existe.
- Scripts: `scripts/01_ingestao.py` (bronze) e `scripts/02_limpeza.py` (silver+gold).
  Rodar nessa ordem; `01_ingestao.py` usa cache (não reconverte se o CSV já existe).

## Fontes de dados usadas
| Fonte | Arquivo bronze | Cobertura | Observação |
|---|---|---|---|
| SPDadosCriminais (SSP-SP) | `crime_2022_*.csv`, `crime_2023_*.csv` | 2022–2023, estado todo | Filtrado por `CD_IBGE==3550308`; grão real é BO×rubrica, não BO único (ver `bos_unicos` vs `crimes_totais`) |
| BR-Football-Dataset | `BR-Football-Dataset.csv` | 2014–2023 | Só Série A/B/C + Copa do Brasil. Paulistão e Libertadores **não** estão nesta base |
| INMET (estação A701 Mirante) | `inmet_2022.csv`, `inmet_2023.csv` | 2022–2023, horário | Fuso UTC→Brasília (-3h fixo, sem DST) |
| Infosiga SP (Detran-SP) | `sinistros_2022.csv`, `sinistros_2023.csv` | 2022–2023, estado todo | Endpoint ZIP oficial dá "não autorizado" via download automatizado; usuário baixou manualmente os anuais `sinistros_AAAA.csv`. Encoding latin-1, separador `;` |
| Feriados/calendário escolar | calculado em `02_limpeza.py` | 2022–2023 | Feriados via algoritmo de Páscoa (sem depender de API); calendário escolar SME transcrito manualmente das resoluções oficiais |

## Decisões metodológicas já tomadas (não redecidir sem motivo)
- **Filtro geográfico**: sempre `CD_IBGE == 3550308`, nunca o campo texto da cidade (tem variantes de espaço em branco).
- **Futebol em SP capital**: no trabalho DIÁRIO antigo, mandante ∈ {Corinthians, Palmeiras, Sao Paulo} (Santos fora como mandante). **Superado na V2 (2026-11-15)**: 4 times monitorados incluindo o Santos, jogos na capital em `janela` e fora dela em `janela_fora_capital` (ver seção V2).
- **Clássico**: mandante E visitante ∈ {Corinthians, Palmeiras, Sao Paulo, Santos}.
- **Colunas de futebol em dia sem jogo**: ficam nulas, não zero (`tem_jogo_sp=False` é o flag; o resto é NaN).
- **Público dos jogos**: no trabalho DIÁRIO antigo, não enriquecido (hook `clean_football(kaggle_publico_path=...)` nunca usado). **Superado na V2 (2026-11-15)**: público dos 216 jogos na capital vindo das páginas de temporada da Wikipédia (ver seção V2).
- **Paulistão**: no trabalho DIÁRIO antigo, fora do pipeline. **Superado na V2 (2026-11-15)**: Paulistão, Libertadores, Sul-Americana e Recopa integrados via `31a_jogos_complementares.py` (páginas de temporada dos clubes na Wikipédia, `fonte_jogo` = permalink `oldid`).
- **Testes não-paramétricos como default** (Etapa 6→7): normalidade rejeitada em quase todas as contagens → Mann-Whitney/Kruskal-Wallis primários, t/ANOVA secundários.
- **Ajuste por GLM Poisson + erros HC1** (não Binomial Negativa): mais simples de defender, consistente para a média mesmo sob sobredispersão. NB citado como alternativa não executada.
- **BH aplicado por família de teste**, não globalmente (Etapa 8): zero-order, parcial A, parcial B, proporções e KW corrigidos separadamente.
- **Análise espacial usa BAIRRO como unidade primária** (não lat/long bruto) por causa do erro de coordenada; anel de distância (2,5/7,5–15 km) tratado como robustez secundária, não headline, pelo mesmo motivo.
- **Definição de pico = resíduo dessazonalizado** (`obs − OLS(obs ~ t + C(dia_semana) + C(mes) + feriado)`), não a contagem crua — evita que "pico" vire sinônimo de "fim de semana". P90 do resíduo é o método principal; P95/z-score/média móvel(28d causal) são robustez.

## Limitações conhecidas (documentar no relatório, não esconder)
- Janela de sobreposição das 3 fontes principais é curta: só 730 dias (2022–2023) — vai pesar no split temporal da Seção 15 do roteiro.
- **Censura no fim da série**: 2023-12-30 e 2023-12-31 têm contagens de crime e acidente anormalmente baixas (defasagem de registro — não é queda real). Já excluídas das análises desde a Etapa 7 e das flags de pico (NaN). Excluir também do treino/teste na Etapa 15.
- **Lacuna Infosiga (Etapa 6)**: 2022-01-17 (`acidentes_total`=7) e 2023-08-07 (=24) — fluxo `tipo_registro=NOTIFICACAO` não entrou nesses dias. Já excluídas desde a Etapa 7. Tratar como missing, não zero.
- 27/11/2023: dia sem nenhuma leitura do INMET (falha de estação).
- 25/08 a 11/09/2023: sensor de precipitação do INMET fora do ar. Reduz a amostra do modelo de controle B da Etapa 8 pra n≈713.
- `latitude`/`longitude` do crime: ~20% das linhas SP-capital têm coord nula/zero/fora do município. BAIRRO (99,6% preenchido) é a unidade primária para qualquer análise espacial. **Pile-up de geocodificação**: BOs online geocodificados ao endereço declarado — no Morumbi, ~60% do "excesso" de dia de jogo cai em 2 coordenadas do próprio estádio (investigado na Etapa 10, ver acima). Acidente (Infosiga) tem coord 99,5% válida, não sofre desse problema na mesma escala.
- **Outlier 2022-06-19** (`furtos_total`=2633 vs mediana ~780): registro em lote. **Tratado na Etapa 12** (não na 11): contagens de crime do dia → NaN em `features_dia_sp.csv` (missing, não zero/removido silenciosamente); lags interpolam só o buraco de 1 dia; linha fora do treino/teste; flag `dia_artefato_lote=1`. `pico_dia_sp.csv` (Etapa 11) **não foi regenerado** — continua com o dia cru (pico `Alto`) porque define a *metodologia*; `features_dia_sp.csv` recalcula os alvos já tratados e é o que a Etapa 13+ deve usar. Sensibilidade (rodar também sem o tratamento) fica para a Etapa 14.

## Definição de pico (Etapa 11 — decidida, não redecidir sem motivo)
- **Alvo = resíduo dessazonalizado**, não a contagem crua (R² do calendário: 0,16–0,60
  conforme o desfecho). Os testes P90/P95 provisórios da Etapa 8 ficam substituídos por isto.
- **Método principal = P90 do resíduo** (~73 dias-pico/728, ~10%). P95, z>2 e média
  móvel (28d, causal) ficam como variantes de robustez — a Etapa 14 reporta as 3.
- **Alvos recomendados**: `crimes_violentos` e `acidentes_com_vitima`. Flags de todos os
  6 desfechos e `nivel_risco` (Baixo/Médio/Alto = `<P75 / P75–P90 / >P90` do resíduo de
  `crimes_violentos` **apenas** — não combina crime+acidente num único índice) em
  `data/gold/pico_dia_sp.csv` (chave `data`, 40 colunas). Se a Etapa 12 quiser um
  desfecho de classificação que combine os dois domínios, isso ainda não existe e
  precisaria ser definido explicitamente, não assumido.
- **Run order**: `02 → 08 → 02`. `pico_dia_sp.csv` não é regenerado pela Etapa 12 (ver
  Limitações acima) — fica como referência da metodologia com a série crua.
- **Ressalva p/ Etapa 15**: limiar P90 e ajuste de calendário usam a série inteira; num
  walk-forward estrito, reestimar só no treino de cada fold. A variante média móvel já
  é causal.
- **Fisher exato no achado colateral (adendo 2026-09-04, não reabrir)**: 5/12 dias-pico
  de consenso de `crimes_violentos` são dia de jogo (OR 3,51, p=0,041). NÃO é achado:
  sem o artefato de 2022-06-19 p=0,103; Bonferroni ×6 p≈0,24; ainda é parte proxy de
  fim de semana; e contradiz as Etapas 7–9 (que testaram isso com potência completa).
  `acidentes_com_vitima`: 0/11, p=0,227. Documentado no relatório da Etapa 11 §3.

## Feature engineering (Etapa 12 — decidida, não redecidir sem motivo)
- **`data/gold/features_dia_sp.csv`** (730×109): 1 linha = 1 dia, 95 features + 10 alvos
  (`y_count_*`, `y_resid_*`, `y_pico_p90_*`, `y_pico_p95_*`, `y_nivel_*` para
  `crimes_violentos` e `acidentes_com_vitima`) + 4 flags/chave. Gerado por
  `scripts/09_feature_engineering.py`. **É este arquivo que a Etapa 13+ deve usar**,
  não `fato_dia_sp.csv` nem `pico_dia_sp.csv` diretamente.
- **4 grupos**: temporal (26, todas conhecidas em avanço), futebol (20 — fixtures de D0
  conhecidas em avanço; resultado/gols do jogo EXCLUÍDOS por leakage, só entram
  defasados; `publico`/`taxa_ocupacao` bloqueadas, 100% NaN), clima (11 — D0 assume
  previsão perfeita + variante `_lag1` conservadora), histórica (38 — lags
  1/2/3/7/14/28/364 e rolling 7/14/28 do desfecho, todos `shift>=1`, auditado
  automaticamente, 0 falhas).
- **Outlier 2022-06-19 resolvido aqui** (ver Limitações). **`sazonal_esperado_*` e
  `*_resid_*`** dependem de ajuste de calendário na série inteira → mesma ressalva da
  Etapa 15 já registrada, marcada explicitamente no dicionário de features
  (`leakage_ok='ver ressalva E15'`).
- **Sanidade confirmada**: |ρ Spearman| máximo de qualquer feature de futebol com o
  resíduo-alvo = 0,018 (`crimes_violentos`) e 0,055 (`acidentes_com_vitima`) — as
  features líderes são histórico do próprio desfecho e clima. Consistente com
  Etapas 7–10; prévia do SHAP (Etapa 18).

## Baselines (Etapa 13 — decididos, não redecidir sem motivo)
- **Split fixo**: treino < 2023-10-01, teste ≥ 2023-10-01 (90 dias), sem embaralhar.
- **Alvo de pico REDEFINIDO aqui** (não é o `y_pico_p90_*` do `features_dia_sp.csv`):
  calendário + limiar P90 reajustados **só no treino**, aplicados ao teste — primeira
  aplicação real da ressalva "reajustar por fold" repetida desde a Etapa 8.
- **Achado importante**: nesse corte, prevalência de pico no teste saiu de 3,3%
  (`crimes_violentos`) a 34,4% (`acidentes_com_vitima`) — a tendência linear do
  modelo de calendário, extrapolada 3 meses à frente, sobre-prevê um desfecho e
  subestima o outro. **Não é bug**; é a prova, com números do projeto, de que um
  corte único é frágil aqui → reforça a necessidade de walk-forward na Etapa 15.
  Consequência prática: métricas de classificação para `crimes_violentos` neste
  corte (n=3 positivos no teste) são ilustrativas, não conclusivas.
- **Scoreboard a bater na Etapa 14**: regressão — média móvel 7d (MAE 51,3
  `crimes_violentos` / 11,8 `acidentes_com_vitima`) venceu média histórica e
  mesmo-dia-semana-anterior. Classificação — `logreg_balanced` bateu classe
  majoritária e a heurística `dia_semana_risco` em Recall/F1 para
  `acidentes_com_vitima` (0,74/0,55); `crimes_violentos` inconclusivo neste corte.
- Considerar, na Etapa 14/15, suavizar/remover a tendência linear do modelo de
  calendário ou reajustá-la com mais frequência.

## Modelos de ML (Etapa 14 — decidida, não redecidir sem motivo)
- **Mesmo split e mesmo alvo redefinido da Etapa 13** (comparação direta com o
  scoreboard). Testados: Decision Tree, Random Forest, HistGradientBoosting
  (bônus), XGBoost, LightGBM (classificação + regressão Poisson), Logistic
  Regression (classificação). `sample_weight` balanceado; hiperparâmetros rasos
  e não otimizados de propósito (Regra 6).
- **Vencedor por métrica não é sempre óbvio**: em `acidentes_com_vitima`,
  `random_forest` vence por PR-AUC (0,532) mas só marca 2/90 dias como pico no
  limiar 0,5 (Recall 0,065); `logreg_balanced` da Etapa 13 tem Recall 0,742/F1
  0,548 com PR-AUC menor. **Não declarar um vencedor único sem dizer qual
  critério** — para um sistema de alerta, Recall no ponto de operação importa.
  `crimes_violentos` classificação segue inconclusiva (3 positivos no teste,
  herdado da Etapa 13).
- **Importância de features = `total_gain`, nunca `gain` médio isolado**
  (infla features binárias raras — `classico_d_menos_1` parecia #1 em
  `acidentes_com_vitima` por `gain`, mas usada em só 2 splits; cai pro rank #37
  por `total_gain`. Mesmo cuidado já aplicado ao RR do Morumbi na Etapa 10).
  Times líderes reais: histórico do próprio desfecho + clima, 0 features de
  futebol no top 15 por `total_gain` nos dois desfechos — reconfirma Etapas 7–10.
- **Sensibilidade ao outlier 2022-06-19 rodada** (XGBoost, `crimes_violentos`):
  diferença moderada (MAE 39,2→43,1 sem o tratamento), não muda a conclusão
  qualitativa. Pendência da Etapa 12 encerrada.

## Validação temporal (Etapa 15 — decidida, não redecidir sem motivo)
- **12 folds mensais walk-forward, janela expansiva** ancorada em 2022-01-01,
  cobrindo 2023 inteiro em teste. Calendário/resíduo/limiar P90/`sazonal_esperado`
  reajustados **só no treino de cada fold** — toda ressalva "ver ressalva E15"
  desde a Etapa 8 está resolvida.
- **Prophet introduzido aqui** (log1p/expm1, primeira aparição do 2º algoritmo do
  título do projeto). Comparado a XGBoost nos mesmos folds: **XGBoost venceu em
  MAE pooled nos dois desfechos** (34,8 vs 42,2 em `crimes_violentos`; 10,3 vs
  11,0 em `acidentes_com_vitima`); Prophet prejudicado por só 1-2 anos de
  histórico para sazonalidade anual (aviso do próprio Prophet).
- **Achado metodológico (não reabrir sem reler `reports/etapa15/` §2)**: pooled
  ROC-AUC de `logreg_balanced`/`crimes_violentos` deu 0,266 (pior que aleatório)
  — investigado: é artefato de empilhar scores de 12 modelos com calibração de
  probabilidade incompatível entre folds (folds com poucos positivos têm score
  médio muito diferente), não o modelo piorando. Corrigido calculando
  `*_fold_macro` (AUC dentro de cada fold, depois média) ao lado de `*_pooled`;
  valor corrigido = 0,494 (~aleatório). **Ao reportar AUC de qualquer walk-forward
  daqui pra frente, usar `fold_macro`, não `pooled`, quando houver poucos
  positivos por fold.**
- **RESOLVIDO (2026-09-04)**: a correção `pooled`→`fold_macro` estava calculada
  para PR-AUC (`pr_auc_fold_macro` já existia na tabela), mas o aviso automático
  de divergência só checava ROC-AUC — PR-AUC podia estar tão ou mais distorcido
  sem sinalização. Confirmado com números reais: `random_forest`/`crimes_violentos`
  diverge Δ=0,259 em PR-AUC (`pooled`=0,089 vs `fold_macro`=0,348) — maior que
  qualquer divergência de ROC-AUC, e não estava sendo avisado. Corrigido:
  `secao_classificacao` agora audita PR-AUC divergente com o mesmo limiar (>0,15),
  separadamente do ROC-AUC. Relatório regenerado; adendo em `docs/Changelog.md`.
- **`crimes_violentos` deixa de ser inconclusivo**: ~360 dias de teste pooled
  (vs 90/3-positivos da Etapa 13) dão base estatística genuína pela primeira vez.

## Métricas (Etapa 16 — decidida, não redecidir sem motivo)
- **Não treina nada novo**: consolida os CSVs já publicados nas Etapas 13/14
  (split único) e 15 (pooled walk-forward) num scoreboard único por
  alvo × tarefa, audita a cobertura contra a lista do briefing §16 e produz a
  única peça que faltava — **matriz de confusão** (exigida em §16 e §24 item
  12, nunca gerada antes).
- **MAPE justificado como apropriado, SMAPE declarado como desnecessário**:
  mínimo observado de `y_count_crimes_violentos`/`y_count_acidentes_com_vitima`
  é 340/31 em 730 dias, 0 dias com contagem zero — MAPE não explode nem fica
  instável aqui, então SMAPE não acrescenta informação (Regra 10: declarar a
  decisão, não calcular por calcular).
- **Matriz de confusão reconstruída algebricamente** a partir dos totais
  pooled já publicados na Etapa 15 (`n_teste_total`, `n_pico_total`,
  `accuracy`, `recall` → TP/FP/FN/TN), **não recalculada do zero** (os arrays
  de predição por fold não foram persistidos em disco na Etapa 15). Validada:
  precision/F1 recalculados da matriz batem com os valores publicados em
  todas as 10 linhas (base × modelo) — decomposição exata, não aproximação.
- **Modelo recomendado para a Etapa 17/18** (critério: pooled walk-forward
  como evidência principal; PR-AUC fold_macro como ranking primário em
  classificação, nunca Accuracy — Regra 8):
  * Regressão: **XGBoost Poisson** vence nos dois alvos (MAE 34,8
    `crimes_violentos` / 10,3 `acidentes_com_vitima`), mas `acidentes_com_vitima`
    tem vantagem estreita sobre `random_forest`/`media_movel_7d` e R² baixo
    (0,28) — melhor disponível, não preditor forte.
  * Classificação `acidentes_com_vitima`: **`logreg_balanced`** vence sem
    ambiguidade (melhor PR-AUC fold_macro E melhor Recall/F1 ao mesmo tempo,
    diferente do split único da Etapa 13/14 onde os critérios discordavam).
  * Classificação `crimes_violentos`: **sem vencedor defensável** — melhor
    PR-AUC (`random_forest`, 0,348) tem Recall 0,05 (inútil); melhor Recall
    (`dia_semana_risco`, 0,50) tem PR-AUC baixo (0,115). Nenhum classificador
    chega a um ponto de operação usável. **Fica sem candidato recomendado
    para tuning na Etapa 17** até reavaliar se otimização muda essa conclusão.
    Convergente com o nulo das Etapas 7–10.

## Otimização de hiperparâmetros (Etapa 17 — decidida, não redecidir sem motivo)
- **Nested walk-forward, não um único CV**: nível externo = os mesmos 12 folds
  mensais da Etapa 15 (métrica pooled comparável número-a-número); nível
  interno = `TimeSeriesSplit` (sem embaralhar) dentro do treino de cada fold
  externo, via `RandomizedSearchCV`, para escolher hiperparâmetros sem que a
  escolha veja o próprio teste daquele fold — a métrica pooled reportada é
  uma estimativa honesta de generalização (Regra 7), diferente de rodar a
  busca 1x sobre tudo e reportar o próprio score da busca.
- **Hiperparâmetros de produção calculados à parte** (busca sobre todo o
  histórico, ainda com `TimeSeriesSplit`) — é este conjunto, não os
  hiperparâmetros rasos da Etapa 14/15 nem a média dos hiperparâmetros por
  fold, que a **Etapa 18 (SHAP) deve usar** para treinar o modelo final.
  Tabela em `reports/etapa17/tabelas/hiperparametros_producao.csv`.
- **Resultado central: tuning não trouxe ganho real, e isso é o achado, não
  uma falha do script.** Com ~350–700 linhas de treino por fold e poucos
  positivos em classificação, a busca interna tem pouco dado para
  diferenciar hiperparâmetros de forma estável:
  * Regressão `crimes_violentos`: MAE pooled **piorou levemente** (34,8 →
    35,1; R² 0,481→0,462) com o tuning.
  * Regressão `acidentes_com_vitima`: ganho marginal (<3%, MAE 10,32→10,28).
  * Classificação `acidentes_com_vitima` (`logreg_balanced`): Recall melhorou
    (0,576→0,674) mas PR-AUC fold_macro **piorou** (0,476→0,417) mesmo com a
    busca otimizando explicitamente para `average_precision` — trade-off
    real, não bug; hiperparâmetros por fold variam muito (`C` de 0,001 a 74),
    sinal de que a busca interna está reagindo a ruído. Nenhum dos dois
    (baseline vs tunado) domina o outro nos dois critérios ao mesmo tempo —
    documentado como tal, sem escolher um vencedor artificial.
- **`crimes_violentos` (classificação) permanece sem candidato**, decisão da
  Etapa 16 mantida — tuning não foi tentado porque o problema é falta de
  sinal nas features, não hiperparâmetro; não reabrir sem novidade do SHAP.

## Interpretabilidade SHAP (Etapa 18 — decidida, não redecidir sem motivo)
- **Modelos explicados = os "de produção" da Etapa 17**, treinados 1x sobre
  todo o histórico e explicados IN-SAMPLE (a generalização já foi validada
  nas Etapas 15/17 — o objetivo aqui é explicar o modelo final, não
  reavaliar desempenho). `TreeExplainer` para os 2 XGBoost Poisson
  (regressão); `shap.Explainer` (linear) para `logreg_balanced`
  (classificação, só `acidentes_com_vitima` — `crimes_violentos` continua
  sem modelo recomendado, decisão da Etapa 16 não reaberta).
- **Confirma o nulo das Etapas 7–14 nos dois modelos de regressão**: grupo
  `futebol` = 2,2% do SHAP total em `crimes_violentos` (0 features de
  futebol no top 15) e 18,7% em `acidentes_com_vitima` — **mas essa segunda
  fatia é quase toda artefato, ver achado abaixo**.
- **Achado investigado (mesmo padrão de rigor das Etapas 10/14/15/17):
  `dias_desde_jogo`/`dias_ate_jogo` (grupo futebol) apareciam com SHAP alto
  (rank #2 em regressão E em classificação de `acidentes_com_vitima`), mas
  são fortemente colineares com sazonalidade** (correlação com `mes` de
  -0,44/-0,21; `dias_desde_jogo` médio = 80–96 dias em jan-mar sem jogos de
  SP-capital na base vs ~2 dias na temporada) **e têm correlação
  praticamente nula e não-significativa com o alvo já desazonalizado**
  (`y_resid`: rho=-0,055 p=0,14; `y_pico`: rho=-0,003 p=0,94). Auditoria
  automática (`audita_colinearidade` no script) confirma: o SHAP credita
  "época do ano", não "efeito do jogo" — **consistente com o nulo das
  Etapas 7–12, não uma contradição dele**. **Atualizado no adendo de
  2026-09-04** (auditoria completa, ver seção de pendências fechadas
  abaixo): depois de descontar o artefato, `futebol` líquido = **0,0% nos
  3 modelos** (2 regressão + 1 classificação) — os ~26% de
  `acidentes_com_vitima` classificação citados originalmente como "limite
  superior" eram um artefato de a auditoria só cobrir o top-20 SHAP
  global; com todas as 18 features de futebol testadas, as 18 são
  artefato.
- **Perguntas do briefing §18 respondidas com números** (não qualitativo):
  número de jogos, clássico e horário do jogo — todos com SHAP
  desprezível/rank baixo nos 2 modelos de regressão; público —
  **não testável** (feature 100% NaN, nunca entrou no modelo, mesma
  pendência desde a Etapa 12); chuva explica mais que futebol em
  `acidentes_com_vitima` **depois de descontar o artefato de calendário**;
  dia da semana domina futebol líquido em regressão nos 2 alvos.

## Pendências do checkpoint pós-Etapa 18 — FECHADAS (2026-09-04, adendo)
- **Auditoria de colinearidade completa no grupo futebol de `acidentes_com_vitima`**:
  `audita_colinearidade` reescrita para testar TODAS as features (não só o top-20
  SHAP global — bug corrigido junto: `tabela_grupo` também tinha um bug real, o
  `.fillna()` da coluna `soma_sem_artefato` caía de volta no valor bruto quando um
  grupo inteiro ficava 100% flagado, escondendo justamente o caso mais importante).
  **Resultado, não mais limite superior**: 18/18 features de futebol marcadas como
  artefato de colinearidade nos 3 modelos (2 regressão + 1 classificação) —
  `futebol líquido = 0,0%` nos três, substituindo o "~26%/33% limite superior"
  citado nas Etapas 18/19.
- **Sensibilidade do SHAP ao hiperparâmetro de produção confirmada**: reexplicados
  os 3 modelos com os hiperparâmetros rasos da Etapa 14/15 (não os da busca da
  Etapa 17). Participação bruta do futebol varia até 5,7 p.p. entre raso e
  produção, mas a participação líquida (pós-auditoria) é 0,0% em ambos os
  hiperparâmetros nos 3 modelos — "futebol ≈ nulo" não é um artefato da busca de
  hiperparâmetros.
- Detalhes em `scripts/15_interpretabilidade_shap.py` (seções 3.2 e 5 do
  relatório) e no adendo correspondente do `docs/Changelog.md`.

## Análise de cenários (Etapa 19 — decidida, não redecidir sem motivo)
- **Adaptação necessária**: os cenários A-D do briefing especificam público
  ("20 mil pessoas" etc.) — `publico`/`taxa_ocupacao` são 100% ausentes
  (pendência desde a Etapa 12) e nunca entraram em nenhum modelo; cenários
  simulados só nas dimensões realmente modeladas (dia da semana, tipo de
  jogo, horário, clima), com a limitação declarada explicitamente (Regra 10).
- **Método = dia real, não linha sintética**: cada cenário usa uma linha REAL
  do dataset que já satisfaz a descrição (escolhida deterministicamente —
  mediana por data entre candidatos elegíveis, evita cherry-picking), exceto
  o cenário D, que reusa a linha do B com uma única perturbação controlada
  (chuva = mediana dos dias de chuva observados, 4,1mm). Evita Regra 1/2
  (inventar dados/resultado): todo feature vem de um dia que aconteceu de
  verdade.
- **Decomposição SHAP exata do delta cenário-vs-baseline, por grupo de
  features**: usa a aditividade do SHAP (predição = base + Σshap) para
  quantificar exatamente quanto da diferença de risco vem do grupo
  `futebol` vs de outras diferenças incidentais entre os 2 dias reais
  (clima do dia, histórico recente). **Cuidado de escala descoberto e
  corrigido durante a implementação**: SHAP do XGBoost Poisson é aditivo no
  LOG da taxa (`output_margin=True`), não na contagem (`predict()` aplica
  `exp()`, não-linear); SHAP da LogReg é aditivo no log-odds
  (`decision_function`), não na probabilidade (`predict_proba()` aplica
  sigmoid). A primeira versão do script comparava a soma dos SHAP com o
  delta em escala de contagem/probabilidade e a checagem de aditividade
  falhava (ex. delta previsto 16,34 vs soma SHAP 0,033) — não é um bug de
  cálculo, é comparação na escala errada; corrigido usando margem/log-odds
  em toda a seção de decomposição.
- **Resultado central**: no vs baseline, `futebol` contribui pouco para o
  delta total nas 2 regressões na maioria das comparações (ex. 0,3–27% do
  "tamanho" do delta, às vezes com sinal oposto ao delta total) — reforça
  o nulo das Etapas 7–18. Exceção parcial: na classificação de
  `acidentes_com_vitima` (cenário B vs baseline), futebol responde por
  ~33% do delta desse par de dias especifico (medida bruta, sem auditoria
  de colinearidade — não é a mesma quantidade que a participação global do
  grupo futebol no SHAP, que a Etapa 18 fechou em 0,0% líquido após o
  adendo de 2026-09-04; os dois números não são contraditórios, só medem
  coisas diferentes — um é o delta de 2 dias reais específicos, o outro é
  a média sobre todos os dias).
- **Achado didático sobre a ressalva de causalidade**: o cenário com maior
  P(pico) previsto para `acidentes_com_vitima` é "domingo + jogo comum"
  (0,855), não o clássico (0,539) nem o jogo noturno de meio de semana
  (0,627) — ilustra concretamente por que comparar cenários sem decompor
  por SHAP pode levar a uma leitura errada (o dia-âncora escolhido para
  "jogo comum" tinha outras características que pesam mais que o tipo de
  jogo em si).

## Análise de causalidade formal (Etapa 20 — decidida, não redecidir sem motivo)
- **Cobre os 5 métodos do briefing §20**: regressão com controles/event
  study/DiD já feitos nas Etapas 7–10 (não repetidos); **2 métodos novos
  adicionados aqui**: Propensity Score (matching 1:1 + IPTW) e uma
  adaptação de Interrupted Time Series.
- **PSM**: escore de propensão via logística em
  dia_semana/mês/feriado/férias/trend; pareamento 1:1 sem reposição
  (caliper 0,2·DP do logit(ps)); balanço checado por SMD antes/depois
  (20/22 covariáveis desbalanceadas → 6-7/22 depois). ATE pareado
  (estimativa primária): `crimes_violentos` +1,5% (ns, p=0,32);
  `acidentes_com_vitima` +0,7% (ns, p=0,83) — ambos nulos, convergente
  com Etapas 7–9.
- **Violação de positividade descoberta, documentada e confirmada**:
  jan-fev não têm NENHUM dia de jogo de SP-capital na base (0% de
  tratamento) — viola o pré-requisito de sobreposição do PSM. Isso não
  invalida o pareamento (que só usa a região com sobreposição real), mas
  **explicava uma discrepância real encontrada**: o IPTW (que repondera a
  base inteira, incluindo jan-mar) deu RR=1,038 significativo (p=0,017) em
  `acidentes_com_vitima`, enquanto o pareamento não achou nada (p=0,83).
  **Confirmado (2026-09-04, adendo)**: rodando o IPTW restrito à mesma
  região de sobreposição do pareamento (exclui jan-fev), o efeito some
  (RR=1,006, p=0,723) — quase idêntico ao pareamento. Discrepância
  resolvida: era reintrodução do confundidor sazonal via os meses sem
  jogo, não um efeito causal real. Pareamento seguiu como estimativa
  primária.
- **ITS adaptado**: janela de ±21 dias ao redor da final da Copa do Brasil
  2023 (2023-09-24) tem 8 outros jogos dentro dela — contamina uma
  regressão segmentada clássica. Adaptado para z-score do resíduo do
  evento vs distribuição de outros jogos comuns: `crimes_violentos` z=1,22
  (percentil 93), `acidentes_com_vitima` z=-1,83 (percentil 3) — **ambos
  dentro da faixa típica de um dia de jogo comum**, nem o evento mais
  extremo do dataset deixou marca detectável na série agregada de SP
  capital.
- **Limitações estruturais documentadas** (§20 exige): sem variação
  exógena da agenda de jogos, Paulistão/Libertadores fora da base,
  público não observado, fatores de confusão temporais não modelados —
  frase do briefing citada literalmente: associação (já fraca/nula),
  não causalidade.

## Resultados esperados (Etapa 23 — decidida, não redecidir sem motivo)
- **Não recalcula nada**: responde as 12 perguntas objetivas do briefing §23
  lendo diretamente os CSVs já publicados nas Etapas 6–20 (mesma filosofia
  de consolidação da Etapa 16), cada resposta citando a etapa de origem —
  serve de esqueleto pronto para as seções Resultados/Discussão/Conclusão
  do relatório final (§25).
- **Síntese de 1 frase por pergunta** (ver `reports/etapa23/relatorio_resultados_finais.md`
  para os números completos): (1) associação bruta fraca some após ajuste,
  sem causalidade; (2) idem para acidentes, `acidentes_fatais` é o resíduo
  mais próximo de significância do projeto (RR=1,146, p=0,063, não-BH);
  (3) clássico não representa risco maior (SHAP líquido=0); (4) noturno
  idem para os 2 alvos principais; (5) público não testável; (6) nenhuma
  defasagem D-2..D+2 significativa, sem período de risco identificável;
  (7) histórico do desfecho + calendário + clima explicam os picos, não
  futebol; (8) XGBoost Poisson (regressão) e `logreg_balanced`
  (classificação, só `acidentes_com_vitima`); (9) Recall 0,576–0,674 só
  para `acidentes_com_vitima`, nenhum ponto de operação útil para
  `crimes_violentos`; (10) previsão D0 válida (walk-forward), horizonte
  >1 dia nunca testado; (11) MAE 34,8/10,3, MAPE 7,1%/12,7%; (12) lista
  consolidada de limitações (público, Paulistão/Libertadores,
  causalidade, `crimes_violentos` sem classificador, janela de 730 dias).

## Visualizações finais (Etapa 24 — decidida, não redecidir sem motivo)
- **Não recalcula nada**: 13 dos 15 itens do briefing §24 já existiam como
  figuras publicadas (EDA, Etapas 7, 13, 14, 16, 18) — `scripts/19_visualizacoes_finais.py`
  só gera os 2 que faltavam (item 6 clássico vs comum, item 7 diurno vs
  noturno — a Etapa 7 só tinha publicado tabela pra esses recortes, nunca
  virou figura) e monta um índice (`reports/etapa24/galeria_visualizacoes.md`)
  linkando os 15, citando a etapa de origem de cada um.
- **Item 8 (heatmap dia da semana × horário) adaptado para dia da semana ×
  mês**: a unidade de análise do projeto é 1 dia (Etapa 4), sem
  granularidade horária para crime/acidente — já resolvido na EDA (Etapa
  6), declarado como adaptação explícita, não substituição silenciosa.
- Figuras novas em estilo violino (mesmo estilo da Etapa 7), mesmo filtro/
  exclusão de dias censurados já decidido lá — confirma visualmente o nulo
  já testado estatisticamente (sobreposição quase total das distribuições).

## `README.md` (§21/22 — código e pipeline, documentado, não redecidido)
- Criado documento para humanos na raiz do projeto (complementa este
  `CLAUDE.md`, que é para assistência de IA): arquitetura de dados
  (bronze→silver→gold), diagrama Mermaid do pipeline completo (19
  scripts), instruções de como rodar, estrutura de diretórios, fontes de
  dados, achado central. `scripts/` já estava organizado 1 script por
  etapa desde o início do projeto — não precisou reorganização, só
  documentação formal do que já existia (briefing §21/22 não pedem código
  novo, só organização/diagrama).

## Próximos passos (atualizado 2026-11-19)
1. Usuário: copiar `sbc.bst` do template do SBC para `../entrega_parcial/entrega3/` e compilar
   `main.tex` (pdflatex → bibtex → pdflatex ×2); conferir limites de página da 2ª entrega (título+resumo 1;
   introdução 2; correlatos 4; metodologia 2; resultados 6; discussão+conclusão 1). Se estourar, enxugar
   texto (nunca fonte/margem).
2. Decidir o título (hoje ainda diz "Dias de Jogos").
3. Versionar (usuário roda os comandos): `.gitignore` criado; `git rm --cached` dos 12 brutos rastreados.
4. Depois de qualquer edição: `py -3.14 scripts/21_valida_latex.py <caminho absoluto do .tex>`.
5. (Histórico) `docs/rpII_predicao_acidentes*.tex` = artigo diário de setembro, não é mais o entregável.

## Pendências que bloqueiam partes do roteiro
Valem para o trabalho DIÁRIO antigo (Etapas 7–24, `fato_dia_sp.csv`); **as duas foram
superadas na V2 (2026-11-15)**, ver seção "V2: análise por janelas de horário".
- ~~**Público dos jogos**: `publico`/`taxa_ocupacao` 100% NaN~~ — **superado na V2**: público
  total dos 216 jogos na capital integrado a partir das páginas de temporada da Wikipédia
  (`jogo_publico`, `jogo_publico_status` em `fato_hora_sp.csv`; amostra conferida em 2ª fonte).
  No trabalho diário antigo continua NaN (não foi retroalimentado).
- ~~**Paulistão e Libertadores** fora da base de futebol~~ — **superado na V2**: Paulistão,
  Libertadores, Sul-Americana e Recopa integrados (`data/bronze/jogos_complementares.csv`).
  A ressalva continua valendo para os números do trabalho diário antigo (Etapas 7–24), que
  usaram só Série A + Copa do Brasil — e o GLM diário com o calendário completo já mostra
  que isso atenuava efeitos (furtos +4,0%, p_BH 0,024).

## Como rodar
```bash
cd scripts
python3 01_ingestao.py   # materializa bronze/ (usa cache se já existir); ~6 min do zero (streama 2 xlsx de ~200MB)
python3 02_limpeza.py    # gera silver/ e data/gold/fato_dia_sp.csv (730 linhas × 69 colunas)
python3 03_eda.py        # Etapa 6: gera reports/eda/eda_report.md + figures/ + tabelas/
python3 04_analise_jogo_vs_naojogo.py   # Etapa 7 → reports/etapa7/
python3 05_analise_estatistica.py       # Etapa 8 → reports/etapa8/
python3 06_analise_defasagem.py         # Etapa 9 → reports/etapa9/
python3 07_analise_espacial.py          # Etapa 10 → reports/etapa10/ (relê o bronze de crime, ~1 min)
python3 08_definicao_pico.py            # Etapa 11 → reports/etapa11/ + data/gold/pico_dia_sp.csv
python3 02_limpeza.py                   # de novo: mescla pico_dia_sp.csv nos placeholders pico_* do fato
python3 09_feature_engineering.py       # Etapa 12 → reports/etapa12/ + data/gold/features_dia_sp.csv (~5s)
python3 10_baselines.py                 # Etapa 13 → reports/etapa13/ (~5s)
python3 11_modelos.py                   # Etapa 14 → reports/etapa14/ (~30s; requer xgboost, lightgbm)
python3 12_validacao_temporal.py        # Etapa 15 → reports/etapa15/ (~2min; requer prophet)
python3 13_metricas_consolidadas.py     # Etapa 16 → reports/etapa16/ (~5s; só lê CSVs já publicados)
python3 14_otimizacao_hiperparametros.py  # Etapa 17 → reports/etapa17/ (~1-2min; RandomizedSearchCV nested)
python3 15_interpretabilidade_shap.py   # Etapa 18 → reports/etapa18/ (~30s; requer shap)
python3 16_analise_cenarios.py          # Etapa 19 → reports/etapa19/ (~30s; requer shap)
python3 17_analise_causalidade.py       # Etapa 20 → reports/etapa20/ (~10s)
python3 18_resultados_finais.py         # Etapa 23 → reports/etapa23/ (~5s; só lê CSVs já publicados)
```
No Windows o interpretador é `python` (não `python3`). Dependências extras além do
briefing: `openpyxl` (usado por `01_ingestao.py`), `xgboost` e `lightgbm` (usados por
`11_modelos.py`), `prophet` (usado por `12_validacao_temporal.py`), `shap` (usado por
`15_interpretabilidade_shap.py`). Instalar com
`pip install openpyxl xgboost lightgbm prophet shap`.

## Ambiente e caminhos (SSD novo, 2026-11-19)
- Projeto: `C:\Users\seraf\Documents\Development\códigos\RpII_predi-o_acidentes`; artigo atual:
  `C:\Users\seraf\Documents\Development\códigos\entrega_parcial\entrega3\` (FORA do repositório git).
- O SSD novo veio sem Python e sem Git. Instalados em 2026-11-19 (com autorização do usuário) via winget:
  Python 3.14.10 (escopo de usuário, com o launcher `py`) e Git 2.56.0. Pacotes instalados no 3.14:
  `numpy`, `pandas` (3.1), `matplotlib` (+ dependências) — só o que o 35 importa; o 21 usa só a stdlib.
  **Não instalados**: statsmodels, scikit-learn, xgboost, prophet, shap, openpyxl (scripts 01–34 não rodam
  sem eles; não é preciso rodá-los de novo). Se o PATH do terminal não achar `py`/`git`, abrir um terminal novo.

## Controle de versão (atualizado 2026-11-19)
`origin` = `https://github.com/Gibaoo/RpII_predi-o_acidentes.git`. Há **6 commits**, o último em
2026-09-05 ("Artigo"); `git branch -vv` mostra `origin/main: gone` (sem fetch neste SSD — estado do remoto
não conferido). **Nada da V2/V3 está versionado** (scripts 30–35, `reports/janelas/`, `data/gold/fato_hora_sp.csv`,
silver de eventos; `CLAUDE.md` e `Changelog.md` modificados). `.gitignore` criado em 2026-11-19 (bronze,
uploads, `__pycache__`, `*.pyc`, auxiliares de LaTeX). **12 arquivos brutos estão rastreados desde o 1º
commit** (`data/bronze/` e `uploads/`: BR-Football, INMET, sinistros 2022/2023, o maior 51,6 MB) — o
`.gitignore` não os remove; proposto `git rm -r --cached data/bronze uploads` (não executado). Nenhum arquivo
novo passa de 100 MB (maior: `data/silver/crime_eventos_sp.csv.gz`, 25,5 MB, nível de evento com
`bo_key`/lat/lon — decidir se entra). `gh` CLI não instalado. O usuário versiona manualmente — **não
commitar/dar push por conta própria**. Se for ajudar com isso no futuro, atenção:
`data/bronze/` (991 MB) e `uploads/` (503 MB) são microdados brutos SSP-SP/Detran-SP,
incluem arquivos >100MB (limite do GitHub) e não devem ir pro repo — usar
`.gitignore` e manter só código/`docs/`/`reports/`/`CLAUDE.md`/`data/silver`+`data/gold`
(pequenos, agregados, sem microdado; juntos ~3MB).
