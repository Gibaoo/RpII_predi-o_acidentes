# Etapa 23 -- Resultados esperados (12 perguntas do briefing)

_Gerado por `scripts/18_resultados_finais.py` em 2026-09-04. Consolida CSVs já publicados nas Etapas 6-20 -- nenhum modelo treinado ou teste estatístico recalculado aqui; cada resposta cita a etapa de origem.

> Regra 5 aplicada em cada resposta: distinção explícita entre correlação, associação (ajustada), predição (de modelo) e causalidade -- nunca usado "efeito de X" quando o que foi medido foi associação ou predição.

## 1. Existe associação entre jogos de futebol e violência?

**Bruta, sim (parcialmente); ajustada por calendário, não.**

Comparação bruta dia-com-jogo vs dia-sem-jogo (Etapa 7):

| variavel | media_com jogo | media_sem jogo | dif_pct_media | MannWhitney_p | MW_p_BH | signif_BH_5pct |
| --- | --- | --- | --- | --- | --- | --- |
| crimes_violentos | 517.690 | 517.977 | -0.055 | 0.775 | 0.775 | não |
| lesao_corporal_dolosa | 100.548 | 87.480 | 14.938 | 0.000 | 0.000 | sim |

Mesmas variáveis, GLM Poisson ajustado por dia da semana + mês + feriado (Etapa 7):

| variavel | rate_ratio_jogo | IC95_lo | IC95_hi | p_value | signif_BH_5pct |
| --- | --- | --- | --- | --- | --- |
| crimes_violentos | 1.009 | 0.988 | 1.031 | 0.399 | não |
| lesao_corporal_dolosa | 1.015 | 0.975 | 1.057 | 0.462 | não |

Correlação parcial (Etapa 8): 0 dos 44 pares driver×desfecho significativos após controlar calendário (0/44 no modelo A). PSM (Etapa 20): ATE pareado `crimes_violentos` = +1,5% (ns, Wilcoxon p=0,32).

**Leitura**: `lesao_corporal_dolosa` mostra diferença bruta grande e significativa (+14,9%, p<0,001), mas some completamente após ajuste (RR ajustado ~1,0, ns). `crimes_violentos` nunca foi significativo, nem bruto. **Associação bruta fraca existe para alguns desfechos específicos; não sobrevive a controle por calendário; nenhuma evidência de causalidade em nenhum dos 5 métodos usados (Etapas 7-9, 20).**

## 2. Existe associação entre jogos e acidentes?

Comparação bruta (Etapa 7):

| variavel | media_com jogo | media_sem jogo | dif_pct_media | MannWhitney_p | signif_BH_5pct |
| --- | --- | --- | --- | --- | --- |
| acidentes_total | 131.357 | 123.518 | 6.346 | 0.000 | sim |
| acidentes_com_vitima | 83.952 | 80.283 | 4.570 | 0.013 | sim |
| acidentes_fatais | 3.095 | 2.232 | 38.696 | 0.000 | sim |

GLM Poisson ajustado (Etapa 7), família acidente:

| variavel | rate_ratio_jogo | IC95_lo | IC95_hi | p_value | signif_BH_5pct |
| --- | --- | --- | --- | --- | --- |
| acidentes_total | 1.002 | 0.972 | 1.033 | 0.902 | não |
| acidentes_com_vitima | 1.015 | 0.985 | 1.046 | 0.333 | não |
| atropelamentos | 1.035 | 0.968 | 1.106 | 0.315 | não |
| colisoes | 1.010 | 0.976 | 1.046 | 0.556 | não |
| acidentes_fatais | 1.146 | 0.993 | 1.323 | 0.063 | não |

PSM (Etapa 20, `acidentes_com_vitima`): ATE pareado = +0,7% (Wilcoxon p=0,83, ns); IPTW irrestrito RR=1.038 (p=0.017, chegou a ser significativo) mas **investigado e resolvido**: IPTW restrito à região de sobreposição RR=1.006 (p=0.723, ns) -- era violação de positividade (jan-fev sem jogo na base), não efeito real.

**Leitura**: `acidentes_fatais` tem o maior resíduo do projeto inteiro (RR bruto +38,7%, RR ajustado 1,146, p=0,063 -- não significativo após BH, mas o mais próximo de significância entre todos os desfechos testados nas Etapas 7-20). Mesmo esse resíduo não é robusto (não sobrevive à correção de múltiplas comparações). **Nenhuma evidência causal robusta de jogo → acidente, em nenhum dos 6 métodos usados no projeto (Etapas 7, 8, 9, 10, 18, 20).**

## 3. Clássicos apresentam maior risco?

Clássico vs jogo comum (Etapa 7, bruto):

| variavel | n_classico | n_comum | media_classico | media_comum | dif_% | MW_p |
| --- | --- | --- | --- | --- | --- | --- |
| crimes_totais | 23 | 103 | 1,386.652 | 1,330.738 | 4.202 | 0.387 |
| crimes_violentos | 23 | 103 | 518.130 | 517.592 | 0.104 | 0.942 |
| lesao_corporal_dolosa | 23 | 103 | 97.304 | 101.272 | -3.918 | 0.570 |
| acidentes_total | 23 | 103 | 136.478 | 130.214 | 4.811 | 0.276 |
| acidentes_com_vitima | 23 | 103 | 88.739 | 82.883 | 7.065 | 0.064 |

SHAP da feature `classico` nos 3 modelos de produção (Etapa 18):

| modelo | rank_shap | mean_abs_shap | artefato_colinearidade |
| --- | --- | --- | --- |
| crimes_violentos (regressão) | 42 | 0.0001 | sim |
| acidentes_com_vitima (regressão) | 49 | 0.0000 | sim |
| acidentes_com_vitima (classificação) | 34 | 0.1073 | sim |

Cenário B (domingo+clássico) vs A (domingo+jogo comum), Etapa 19: P(pico) previsto `acidentes_com_vitima` foi **menor** no clássico (0,539) do que no jogo comum (0,855) -- diferença explicada por características incidentais do dia-âncora escolhido, não pelo tipo de jogo (ver decomposição SHAP da Etapa 19).

**Leitura**: nenhuma diferença bruta é significativa após BH; a única quase-significância bruta (`acidentes_com_vitima` +7,1%, p=0,064) não sobrevive a correção. SHAP confirma: `classico` marcado como artefato de colinearidade com calendário nos 3 modelos, contribuição líquida = 0. **Sem evidência de que clássicos representem risco maior.**

## 4. Jogos noturnos apresentam maior risco?

Noturno vs diurno (Etapa 7, bruto):

| variavel | n_noturno | n_diurno | media_noturno | media_diurno | dif_% | MW_p |
| --- | --- | --- | --- | --- | --- | --- |
| crimes_totais | 72 | 54 | 1,353.556 | 1,324.130 | 2.222 | 0.664 |
| crimes_violentos | 72 | 54 | 519.847 | 514.815 | 0.978 | 0.771 |
| lesao_corporal_dolosa | 72 | 54 | 107.236 | 91.630 | 17.032 | 0.000 |
| acidentes_total | 72 | 54 | 133.639 | 128.315 | 4.149 | 0.081 |
| acidentes_com_vitima | 72 | 54 | 84.472 | 83.259 | 1.457 | 0.557 |

`lesao_corporal_dolosa` é a única variável com diferença bruta grande e significativa mesmo após BH (+17,0%, MW p=0,0003) -- mas é uma comparação SÓ dentro dos dias de jogo (72 noturnos vs 54 diurnos), sem controle de dia da semana/mês (jogos noturnos podem concentrar-se em dias diferentes dos diurnos); `crimes_violentos` (+0,98%) e `acidentes_com_vitima` (+1,46%) não são significativos.

SHAP da feature `jogo_noturno` (Etapa 18):

| modelo | rank_shap | mean_abs_shap | artefato_colinearidade |
| --- | --- | --- | --- |
| crimes_violentos (regressão) | 67 | 0.0000 | sim |
| acidentes_com_vitima (regressão) | 63 | 0.0000 | sim |
| acidentes_com_vitima (classificação) | 50 | 0.0320 | sim |

**Leitura**: o único sinal bruto real (`lesao_corporal_dolosa`) é para um desfecho fora dos 2 alvos principais do projeto e não controla calendário; nos 2 alvos principais (`crimes_violentos`, `acidentes_com_vitima`) não há diferença significativa em nenhuma leitura, bruta ou SHAP. **Sem evidência robusta de que jogos noturnos representem risco maior para os alvos principais.**

## 5. O público influencia?

**Não testável com os dados disponíveis** (Regra 10 -- declarar a limitação, não fabricar um proxy). `publico`/`taxa_ocupacao` são 100% ausentes (a fonte Kaggle `adaoduque/campeonato-brasileiro-de-futebol` nunca foi baixada, pendência aberta desde a Etapa 12) e por isso nunca entraram no conjunto de features de nenhum modelo das Etapas 13-20. Declarado explicitamente em cada etapa onde a pergunta reaparece (7, 12, 18, 19, 20) em vez de inventar um proxy (ex. mandante/visitante como proxy de público teria introduzido uma suposição não verificável). Fica como recomendação de trabalho futuro (§25) caso a base seja baixada.

## 6. Qual é o período de maior risco: antes, durante ou depois do jogo?

Modelo de defasagens distribuídas D-2..D+2 (Etapa 9, GLM Poisson HC1):

| desfecho | defasagem | rate_ratio | p_value | signif_BH_5pct |
| --- | --- | --- | --- | --- |
| crimes_violentos | jogo_d_menos_2 | 1.002 | 0.852 | não |
| crimes_violentos | jogo_d_menos_1 | 0.996 | 0.713 | não |
| crimes_violentos | jogo_d0 | 1.008 | 0.493 | não |
| crimes_violentos | jogo_d_mais_1 | 1.005 | 0.623 | não |
| crimes_violentos | jogo_d_mais_2 | 1.010 | 0.339 | não |
| acidentes_com_vitima | jogo_d_menos_2 | 1.011 | 0.513 | não |
| acidentes_com_vitima | jogo_d_menos_1 | 1.003 | 0.849 | não |
| acidentes_com_vitima | jogo_d0 | 1.014 | 0.372 | não |
| acidentes_com_vitima | jogo_d_mais_1 | 1.004 | 0.806 | não |
| acidentes_com_vitima | jogo_d_mais_2 | 1.014 | 0.384 | não |
| acidentes_fatais | jogo_d_menos_2 | 1.043 | 0.577 | não |
| acidentes_fatais | jogo_d_menos_1 | 0.992 | 0.913 | não |
| acidentes_fatais | jogo_d0 | 1.148 | 0.059 | não |
| acidentes_fatais | jogo_d_mais_1 | 1.071 | 0.362 | não |
| acidentes_fatais | jogo_d_mais_2 | 1.107 | 0.179 | não |

Event study D-1 (véspera) / D0 (dia do jogo) / D+1 (dia seguinte), resíduo dessazonalizado (Etapa 9):

| desfecho | janela_gold | media_residuo | t_p_vs_0 | p_BH |
| --- | --- | --- | --- | --- |
| crimes_violentos | jogo_d_mais_1 (vespera) | 0.929 | 0.823 | 0.913 |
| crimes_violentos | jogo_d0 (dia do jogo) | 2.915 | 0.559 | 0.913 |
| crimes_violentos | jogo_d_menos_1 (dia seguinte) | -0.973 | 0.814 | 0.913 |
| acidentes_com_vitima | jogo_d_mais_1 (vespera) | 0.263 | 0.817 | 0.913 |
| acidentes_com_vitima | jogo_d0 (dia do jogo) | 0.657 | 0.473 | 0.913 |
| acidentes_com_vitima | jogo_d_menos_1 (dia seguinte) | 0.122 | 0.913 | 0.913 |

**Leitura**: nenhuma das 30 defasagens D-2..D+2 (6 desfechos × 5 defasagens) é significativa após BH; o event study também não encontra desvio significativo em nenhum offset -7..+7. O único resíduo em qualquer análise de janela temporal do projeto inteiro é `acidentes_fatais` em D0 (mesmo dia), RR=1,146, p=0,063 sem BH -- não robusto. **Não há período (antes, durante ou depois) com risco significativamente elevado; se houvesse algum, seria D0 (mesmo dia do jogo), não antes nem depois — mas mesmo esse sinal não passa em correção de múltiplas comparações.**

## 7. Quais variáveis mais explicam os picos?

**crimes_violentos (regressão)** (SHAP por grupo, Etapa 18):

| grupo | soma_mean_abs_shap | pct_% | soma_sem_artefato |
| --- | --- | --- | --- |
| historica | 0.07 | 42.52 | 0.07 |
| temporal | 0.06 | 37.80 | 0.06 |
| clima | 0.03 | 17.50 | 0.02 |
| futebol | 0.00 | 2.18 | 0.00 |

**acidentes_com_vitima (regressão)** (SHAP por grupo, Etapa 18):

| grupo | soma_mean_abs_shap | pct_% | soma_sem_artefato |
| --- | --- | --- | --- |
| temporal | 0.05 | 37.22 | 0.05 |
| historica | 0.05 | 33.83 | 0.03 |
| futebol | 0.03 | 18.71 | 0.00 |
| clima | 0.01 | 10.24 | 0.01 |

**acidentes_com_vitima (classificação)** (SHAP por grupo, Etapa 18):

| grupo | soma_mean_abs_shap | pct_% | soma_sem_artefato |
| --- | --- | --- | --- |
| temporal | 3.88 | 30.58 | 3.88 |
| futebol | 3.37 | 26.62 | 0.00 |
| historica | 3.16 | 24.96 | 1.14 |
| clima | 2.26 | 17.84 | 2.03 |

**Leitura**: histórico do próprio desfecho (lags/médias móveis) e variáveis de calendário/sazonalidade dominam nos 2 modelos de regressão; clima explica mais que futebol em `acidentes_com_vitima` depois de descontar o artefato de colinearidade (Etapa 18). `futebol` líquido = 0,0% nos 3 modelos após auditoria completa (adendo 2026-09-04) -- **os picos são explicados por padrão histórico do próprio desfecho, calendário e clima, não por jogos de futebol.**

## 8. Qual modelo apresentou melhor desempenho?

Regressão -- XGBoost Poisson, pooled walk-forward (Etapa 15/16/17; tuning da Etapa 17 não trouxe ganho, valores = baseline não-tunado):

| base | MAE_baseline | RMSE_baseline | R2_baseline | MAPE_baseline_% |
| --- | --- | --- | --- | --- |
| crimes_violentos | 34.84 | 44.87 | 0.48 | 7.09 |
| acidentes_com_vitima | 10.32 | 13.08 | 0.28 | 12.69 |

Classificação -- `logreg_balanced`, só `acidentes_com_vitima` (pooled walk-forward, Etapa 15/16):

| base | accuracy_baseline | precision_baseline | recall_baseline | f1_baseline | pr_auc_baseline |
| --- | --- | --- | --- | --- | --- |
| acidentes_com_vitima | 0.663 | 0.390 | 0.576 | 0.465 | 0.476 |

**`crimes_violentos` (classificação) continua sem modelo recomendado** -- decisão da Etapa 16, nunca revertida: nenhum classificador testado (Etapas 14, 15, 17) chega a um ponto de operação com Recall e PR-AUC úteis ao mesmo tempo.

**Leitura**: XGBoost Poisson venceu baselines e Prophet nos 2 alvos de regressão (Etapa 15); `logreg_balanced` venceu por Recall/F1 E PR-AUC ao mesmo tempo em `acidentes_com_vitima` classificação (Etapa 16) -- vencedor sem ambiguidade de critério, ao contrário do split único da Etapa 13/14.

## 9. Qual é o Recall para identificação de picos?

Recall pooled walk-forward por modelo (Etapa 15/16):

| base | modelo | recall | precision | f1 | pr_auc |
| --- | --- | --- | --- | --- | --- |
| acidentes_com_vitima | logreg_balanced | 0.576 | 0.390 | 0.465 | 0.476 |
| acidentes_com_vitima | dia_semana_risco | 0.457 | 0.228 | 0.304 | 0.291 |
| acidentes_com_vitima | random_forest | 0.120 | 0.647 | 0.202 | 0.400 |
| acidentes_com_vitima | xgboost | 0.087 | 0.308 | 0.136 | 0.394 |
| acidentes_com_vitima | classe_majoritaria | 0.000 | 0.000 | 0.000 |  |
| crimes_violentos | dia_semana_risco | 0.500 | 0.057 | 0.102 | 0.115 |
| crimes_violentos | logreg_balanced | 0.100 | 0.020 | 0.033 | 0.228 |
| crimes_violentos | random_forest | 0.050 | 0.333 | 0.087 | 0.348 |
| crimes_violentos | classe_majoritaria | 0.000 | 0.000 | 0.000 |  |
| crimes_violentos | xgboost | 0.000 | 0.000 | 0.000 | 0.201 |

**Leitura**: `acidentes_com_vitima` -- Recall 0,576 com `logreg_balanced` (0,674 com hiperparâmetro tunado da Etapa 17, mas à custa de PR-AUC menor). `crimes_violentos` -- nenhum modelo combina Recall e PR-AUC úteis: `random_forest` tem a melhor PR-AUC (0,348) mas Recall=0,05 (praticamente não detecta pico); `dia_semana_risco` (heurística de calendário) tem o melhor Recall (0,50) mas PR-AUC baixo (0,115). **Recall utilizável só existe para `acidentes_com_vitima`; para `crimes_violentos`, nenhum classificador testado atinge um ponto de operação prático.**

## 10. É possível prever um pico com antecedência?

**Sim, com D0 (mesmo dia), para `acidentes_com_vitima`; não de forma útil para `crimes_violentos`.** Todas as features do modelo são conhecidas ANTES do desfecho do dia (fixtures de futebol, calendário, histórico defasado ≥1 dia, previsão de clima) -- verificado por auditoria automática de leakage na Etapa 12 (0 falhas) -- e a validação walk-forward (Etapas 15/17) confirma que a previsão generaliza para meses nunca vistos no treino, não é ajuste ao próprio passado.

**Limitação declarada (não testada no projeto)**: o horizonte de previsão testado é sempre D0 (o dia em si, com informação disponível até o dia anterior) -- o projeto não testou previsão com 2+ dias de antecedência (ex. prever terça-feira usando só dados até domingo). Fica como recomendação explícita de trabalho futuro (§25), não uma capacidade já demonstrada.

## 11. Qual é a margem de erro da previsão?

| base | MAE_baseline | RMSE_baseline | MAPE_baseline_% | R2_baseline |
| --- | --- | --- | --- | --- |
| crimes_violentos | 34.84 | 44.87 | 7.09 | 0.48 |
| acidentes_com_vitima | 10.32 | 13.08 | 12.69 | 0.28 |

**Leitura**: para `crimes_violentos`, o modelo erra em média ±34,8 crimes/dia (MAPE 7,1%) sobre uma contagem diária que varia de 340 a bem mais -- R²=0,48 (o modelo explica ~48% da variância diária). Para `acidentes_com_vitima`, erro médio ±10,3/dia (MAPE 12,7%), R²=0,28 (bem menos variância explicada -- "melhor disponível, não preditor forte", conforme já registrado na Etapa 16). Números pooled sobre ~360 dias de teste walk-forward (Etapa 15), não um único corte.

## 12. Quais são as limitações do estudo?

| categoria | limitação |
| --- | --- |
| Cobertura de futebol | Paulistão e Libertadores fora da base (BR-Football-Dataset só cobre Série A/B/C + Copa do Brasil) -- dias de jogo dessas competições aparecem como `tem_jogo_sp=0`, atenuando qualquer efeito real e potencialmente inflando o peso do calendário |
| Público | `publico`/`taxa_ocupacao` 100% ausentes -- pergunta 5 (§23) não testável, feature nunca usada em nenhum modelo |
| Janela temporal | Só 730 dias (2022-2023) de sobreposição das 3 fontes principais -- limita a validação temporal (Etapa 15) e a sazonalidade anual do Prophet |
| Censura/lacunas de registro | 2023-12-30/31 (defasagem de registro), 2022-01-17 e 2023-08-07 (falha Infosiga), 27/11/2023 (falha INMET), 25/08-11/09/2023 (sensor de precipitação fora do ar) -- todas excluídas/tratadas como missing, nunca como zero |
| Outlier de registro | 2022-06-19 (`furtos_total`=2633, registro em lote) -- tratado como missing na Etapa 12; sensibilidade rodada na Etapa 14 (MAE muda de 39,2 para 43,1, não muda conclusão qualitativa) |
| Geolocalização | ~20% das coordenadas de crime nulas/zero/fora do município; pile-up de geocodificação no Morumbi investigado e explicado (Etapa 10), não é achado espacial robusto |
| Causalidade | Sem variação exógena da agenda de jogos (decidida por CBF/clubes, não aleatória) -- nenhum dos 5 métodos causais do briefing (regressão com controles, event study, DiD, PSM, ITS adaptado) permite afirmar causalidade, só associação (Etapa 20) |
| Classificação de `crimes_violentos` | Nenhum classificador testado (Etapas 14, 15, 17) atinge Recall e PR-AUC úteis ao mesmo tempo -- sem modelo recomendado para esse alvo |
| Horizonte de previsão | Só testado D0 (mesmo dia); previsão com 2+ dias de antecedência não avaliada |
| Fatores de confusão não observados | Mudanças de política de segurança, operações policiais pontuais, greves, eventos não-futebolísticos coincidentes -- não há como descartar toda coincidência residual com 730 dias de dados (Etapa 20) |

Lista consolidada a partir de `CLAUDE.md` ("Limitações conhecidas") e da seção 4 do relatório da Etapa 20 -- nenhuma limitação nova introduzida aqui, só reunida num único lugar para a seção Limitações do relatório final (§25).

## Síntese em uma frase por pergunta

- 1. Associação bruta fraca com futebol para alguns desfechos; some após ajuste por calendário; sem causalidade.
- 2. Idem para acidentes; `acidentes_fatais` é o resíduo mais próximo de significância do projeto, ainda não robusto.
- 3. Não -- diferenças brutas não significativas após BH; SHAP confirma `classico` como artefato de calendário nos 3 modelos.
- 4. Não para os 2 alvos principais -- único sinal bruto significativo (`lesao_corporal_dolosa`) é fora do escopo principal e sem controle de calendário.
- 5. Não testável -- feature 100% ausente, nunca modelada.
- 6. Nenhum período (D-2..D+2) é significativo após BH; se houvesse, seria D0, não antes/depois.
- 7. Histórico do próprio desfecho, calendário e clima -- futebol líquido = 0,0% do SHAP nos 3 modelos.
- 8. XGBoost Poisson (regressão, 2 alvos); `logreg_balanced` (classificação, só `acidentes_com_vitima`).
- 9. 0,576-0,674 para `acidentes_com_vitima`; nenhum ponto de operação útil para `crimes_violentos`.
- 10. Sim, D0, para `acidentes_com_vitima`, validado walk-forward; horizonte >1 dia não testado.
- 11. MAE 34,8 (crimes_violentos, MAPE 7,1%) / 10,3 (acidentes_com_vitima, MAPE 12,7%), pooled walk-forward.
- 12. Público ausente, Paulistão/Libertadores fora da base, janela curta, sem causalidade, `crimes_violentos` sem classificador utilizável.
