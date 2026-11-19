# V2 / Fase 3 — CRIMES: bloco preditivo

Gerado por `scripts/34_preditivo_janelas.py`. Previsão feita na véspera (até 23h59 do dia anterior); só variáveis conhecidas nesse momento (calendário, agenda de jogos, público **histórico** do mandante, clima como previsão perfeita e variante com clima defasado 24 h, histórico do desfecho com defasagem ≥ 24 h). Walk-forward 12 folds mensais de 2023, janela expansiva desde 2022-01, tudo reajustado só no treino. Hiperparâmetros fixos e rasos (Etapa 17). Prophet só na escala cidade (no entorno as contagens são esparsas e o Prophet, gaussiano em log1p, não é adequado). GLM de previsão = spec da Fase 2 com mês do ano + tendência no lugar de ano × mês (o mês de teste não existe no treino).

## Resposta direta: saber que haverá jogo melhora a previsão hora a hora?

- **cidade — `crimes_violentos`:** XGBoost / todas as horas: deviance +0.4% → não muda; MAE -0.000 → não muda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +3.9% → **ajuda**; MAE +0.118 → ajuda; XGBoost clima lag24 / todas as horas: deviance +1.3% → **ajuda**; MAE +0.024 → não muda; XGBoost clima lag24 / horas PRÉ/DURANTE/PÓS na capital: deviance +5.6% → **ajuda**; MAE +0.176 → ajuda; GLM / todas as horas: deviance +0.6% → **ajuda**; MAE +0.015 → ajuda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance -0.3% → não muda; MAE -0.036 → não muda; Prophet / todas as horas: deviance -0.0% → não muda; MAE -0.000 → não muda; Prophet / horas PRÉ/DURANTE/PÓS na capital: deviance +1.9% → **ajuda**; MAE +0.056 → ajuda.
- **entorno — `crimes_violentos`:** XGBoost / todas as horas: deviance +0.2% → não muda; MAE +0.001 → não muda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +4.6% → **ajuda**; MAE -0.010 → não muda; GLM / todas as horas: deviance +0.4% → **ajuda**; MAE +0.001 → ajuda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance +2.4% → não muda; MAE -0.010 → não muda.
- **entorno — `roubos_total`:** XGBoost / todas as horas: deviance +0.2% → não muda; MAE +0.001 → não muda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +3.8% → **ajuda**; MAE -0.009 → não muda; GLM / todas as horas: deviance +0.3% → não muda; MAE +0.001 → ajuda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance +2.8% → não muda; MAE -0.010 → não muda.
- **entorno — `furtos_total`:** XGBoost / todas as horas: deviance +0.9% → **ajuda**; MAE +0.003 → ajuda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +13.9% → **ajuda**; MAE +0.002 → não muda; GLM / todas as horas: deviance +0.5% → **ajuda**; MAE +0.002 → ajuda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance +8.7% → **ajuda**; MAE -0.026 → piora.

(ganho = métrica sem as variáveis de jogo − com; > 0 = jogo ajuda; "ajuda"/"piora" só quando o IC95 por bootstrap em blocos de semana exclui 0 — IC completos nas tabelas de ablação. `XGBoost clima lag24` = variante conservadora com o clima da véspera no lugar da previsão perfeita.)

**Notas de leitura:**
- **Baseline com deviance muito alta no entorno:** a média das 4 semanas anteriores é 0 em muitas horas de contagem baixa; quando ocorre 1 registro, a deviance de Poisson explode (μ≈0). Compare o baseline pelo MAE, que é próximo dos outros modelos.
- **Deviance × MAE:** a deviance pesa mais os erros em horas de contagem alta/inesperada; o MAE pesa todos igualmente. Quando o jogo melhora a deviance mas não o MAE, o ganho está em capturar as horas de excesso (cauda), não em acertar melhor a hora típica.
- **Classificação de pico / hora de risco:** compare PR-AUC com a prevalência (linha `prevalencia_teste`): PR-AUC de um classificador aleatório = prevalência.

## Cidade — `crimes_violentos`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| XGBoost | com_jogo | 1.6428 | 4.3698 | 8666 | 2.0932 | 5.8253 |
| XGBoost | sem_jogo | 1.6489 | 4.3696 | 8666 | 2.1778 | 5.9435 |
| XGBoost clima lag24 | com_jogo | 1.6742 | 4.4065 | 8666 | 2.2139 | 6.0208 |
| XGBoost clima lag24 | sem_jogo | 1.6957 | 4.4307 | 8666 | 2.3453 | 6.1969 |
| Prophet | sem_jogo | 1.8240 | 4.5503 | 8666 | 2.3697 | 6.1290 |
| Prophet | com_jogo | 1.8243 | 4.5504 | 8666 | 2.3248 | 6.0726 |
| GLM | com_jogo | 1.8453 | 4.7541 | 8666 | 2.3969 | 6.4368 |
| GLM | sem_jogo | 1.8560 | 4.7686 | 8666 | 2.3908 | 6.4012 |
| baseline | sem_jogo | 1.9264 | 4.7468 | 8666 | 2.4427 | 6.3649 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 8666 | 1.8560 | 1.8453 | 0.0107 | 0.0014 | 0.0224 | 0.5757 | 4.7686 | 4.7541 | 0.0146 | 0.0003 | 0.0320 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 642 | 2.3908 | 2.3969 | -0.0061 | -0.0475 | 0.0415 | -0.2543 | 6.4012 | 6.4368 | -0.0356 | -0.1091 | 0.0333 |
| GLM | horas de jogo fora da capital | 716 | 2.0481 | 1.9982 | 0.0499 | 0.0011 | 0.1158 | 2.4377 | 5.8326 | 5.7578 | 0.0747 | -0.0107 | 0.1825 |
| XGBoost | todas as horas | 8666 | 1.6489 | 1.6428 | 0.0061 | -0.0068 | 0.0197 | 0.3703 | 4.3696 | 4.3698 | -0.0003 | -0.0194 | 0.0178 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 642 | 2.1778 | 2.0932 | 0.0846 | 0.0165 | 0.1536 | 3.8854 | 5.9435 | 5.8253 | 0.1182 | 0.0165 | 0.2086 |
| XGBoost | horas de jogo fora da capital | 716 | 1.8107 | 1.7992 | 0.0115 | -0.0410 | 0.0691 | 0.6336 | 5.4215 | 5.3891 | 0.0324 | -0.0721 | 0.1312 |
| XGBoost clima lag24 | todas as horas | 8666 | 1.6957 | 1.6742 | 0.0216 | 0.0048 | 0.0415 | 1.2710 | 4.4307 | 4.4065 | 0.0242 | -0.0004 | 0.0523 |
| XGBoost clima lag24 | horas PRÉ/DURANTE/PÓS na capital | 642 | 2.3453 | 2.2139 | 0.1314 | 0.0676 | 0.2028 | 5.6014 | 6.1969 | 6.0208 | 0.1761 | 0.0632 | 0.2989 |
| XGBoost clima lag24 | horas de jogo fora da capital | 716 | 1.9361 | 1.8586 | 0.0775 | -0.0003 | 0.1470 | 4.0031 | 5.6396 | 5.5027 | 0.1369 | 0.0094 | 0.2597 |
| Prophet | todas as horas | 8666 | 1.8240 | 1.8243 | -0.0003 | -0.0062 | 0.0058 | -0.0157 | 4.5503 | 4.5504 | -0.0002 | -0.0085 | 0.0083 |
| Prophet | horas PRÉ/DURANTE/PÓS na capital | 642 | 2.3697 | 2.3248 | 0.0450 | 0.0116 | 0.0785 | 1.8973 | 6.1290 | 6.0726 | 0.0564 | 0.0000 | 0.1072 |
| Prophet | horas de jogo fora da capital | 716 | 2.0219 | 2.0634 | -0.0415 | -0.0853 | -0.0004 | -2.0522 | 5.6013 | 5.6406 | -0.0393 | -0.1164 | 0.0327 |

### Classificação de pico (P90 do resíduo de Pearson, definição da Fase 2)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost | sem_jogo | 0.147 | 0.122 | 0.216 | 0.075 |
| XGBoost | com_jogo | 0.144 | 0.110 | 0.188 | 0.075 |
| XGBoost clima lag24 | sem_jogo | 0.144 | 0.121 | 0.214 | 0.075 |
| XGBoost clima lag24 | com_jogo | 0.140 | 0.118 | 0.196 | 0.075 |
| baseline | sem_jogo | 0.108 | 0.080 | 0.108 | 0.075 |
| GLM | com_jogo | 0.093 | 0.120 | 0.090 | 0.075 |
| GLM | sem_jogo | 0.089 | 0.105 | 0.078 | 0.075 |
| Prophet | com_jogo | 0.084 | 0.043 | 0.084 | 0.075 |
| Prophet | sem_jogo | 0.083 | 0.042 | 0.071 | 0.075 |

### SHAP (ablação mostrou ganho) com auditoria de colinearidade

Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a variável pode estar fazendo papel de hora do dia (Etapa 18).

| variavel | shap_medio_abs | rank | rho_com_hora_do_dia | participacao_pct |
|---|---|---|---|---|
| fo_hora_rel | 0.006 | 13 | -0.044 | 1.189 |
| jg_publico_hist | 0.002 | 15 | 0.020 | 0.452 |
| jg_hora_rel | 0.002 | 16 | -0.028 | 0.342 |
| jg_classico | 0.001 | 17 | 0.020 | 0.209 |
| C_pre | 0.001 | 20 | 0.132 | 0.120 |
| jg_noturno | 0.001 | 21 | 0.016 | 0.117 |
| dia_de_jogo_f | 0.000 | 22 | 0.001 | 0.086 |
| fo_n_simult | 0.000 | 23 | 0.276 | 0.069 |
| jg_comp_Serie A | 0.000 | 24 | -0.001 | 0.059 |
| fo_time_Sao Paulo | 0.000 | 25 | 0.147 | 0.045 |
| C_fdj | 0.000 | 26 | -0.176 | 0.045 |
| jg_comp_Campeonato Paulista | 0.000 | 27 | 0.025 | 0.044 |
| jg_mand_Sao Paulo | 0.000 | 28 | 0.008 | 0.039 |
| jg_comp_Copa do Brasil | 0.000 | 29 | 0.020 | 0.028 |
| fo_time_Santos | 0.000 | 30 | 0.193 | 0.028 |

## Entorno — `crimes_violentos`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.9897 | 0.5478 | 25998 | 1.3517 | 0.8113 |
| XGBoost | sem_jogo | 0.9917 | 0.5489 | 25998 | 1.4163 | 0.8013 |
| GLM | com_jogo | 1.0191 | 0.5558 | 25998 | 1.3615 | 0.7994 |
| GLM | sem_jogo | 1.0232 | 0.5572 | 25998 | 1.3948 | 0.7894 |
| baseline | sem_jogo | 3.9069 | 0.5630 | 25998 | 5.1944 | 0.8333 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 25998 | 1.0232 | 1.0191 | 0.0041 | 0.0003 | 0.0089 | 0.4037 | 0.5572 | 0.5558 | 0.0014 | 0.0000 | 0.0031 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.3948 | 1.3615 | 0.0333 | -0.0066 | 0.0727 | 2.3868 | 0.7894 | 0.7994 | -0.0100 | -0.0238 | 0.0033 |
| GLM | horas de jogo fora da capital | 2148 | 1.1981 | 1.1942 | 0.0039 | -0.0099 | 0.0224 | 0.3275 | 0.7132 | 0.7057 | 0.0075 | 0.0019 | 0.0149 |
| XGBoost | todas as horas | 25998 | 0.9917 | 0.9897 | 0.0020 | -0.0004 | 0.0047 | 0.2010 | 0.5489 | 0.5478 | 0.0011 | -0.0001 | 0.0024 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.4163 | 1.3517 | 0.0646 | 0.0021 | 0.1333 | 4.5582 | 0.8013 | 0.8113 | -0.0100 | -0.0275 | 0.0044 |
| XGBoost | horas de jogo fora da capital | 2148 | 1.1794 | 1.1661 | 0.0133 | 0.0017 | 0.0248 | 1.1306 | 0.7086 | 0.7015 | 0.0072 | 0.0022 | 0.0122 |

### Classificação de hora de risco (P(Y ≥ obs | esperado calendário+clima) < 0,10)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.099 | 0.151 | 0.126 | 0.054 |
| XGBoost | sem_jogo | 0.098 | 0.153 | 0.127 | 0.054 |
| GLM | sem_jogo | 0.092 | 0.119 | 0.109 | 0.054 |
| GLM | com_jogo | 0.091 | 0.120 | 0.108 | 0.054 |
| baseline | sem_jogo | 0.067 | 0.071 | 0.072 | 0.054 |

### SHAP (ablação mostrou ganho) com auditoria de colinearidade

Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a variável pode estar fazendo papel de hora do dia (Etapa 18).

| variavel | shap_medio_abs | rank | rho_com_hora_do_dia | participacao_pct |
|---|---|---|---|---|
| fo_hora_rel | 0.018 | 10 | -0.037 | 1.841 |
| jg_hora_rel | 0.007 | 14 | -0.003 | 0.748 |
| dia_de_jogo_f | 0.003 | 19 | -0.023 | 0.342 |
| jg_publico_hist | 0.003 | 20 | 0.006 | 0.339 |
| C_fdj | 0.003 | 21 | -0.119 | 0.321 |
| fo_time_Palmeiras | 0.002 | 22 | 0.126 | 0.235 |
| C_pos | 0.001 | 23 | 0.069 | 0.157 |
| jg_noturno | 0.001 | 26 | 0.004 | 0.131 |
| C_durante | 0.001 | 27 | 0.092 | 0.103 |
| fo_time_Santos | 0.001 | 28 | 0.170 | 0.091 |
| fo_n_simult | 0.001 | 29 | 0.263 | 0.078 |
| jg_comp_Serie A | 0.001 | 30 | 0.006 | 0.072 |
| jg_mand_Sao Paulo | 0.001 | 31 | 0.007 | 0.067 |
| C_durante_outro | 0.001 | 32 | 0.140 | 0.063 |
| C_pre_outro | 0.001 | 33 | 0.093 | 0.063 |

## Entorno — `roubos_total`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.9389 | 0.5010 | 25998 | 1.3288 | 0.7675 |
| XGBoost | sem_jogo | 0.9406 | 0.5020 | 25998 | 1.3814 | 0.7583 |
| GLM | com_jogo | 0.9644 | 0.5074 | 25998 | 1.3425 | 0.7600 |
| GLM | sem_jogo | 0.9674 | 0.5086 | 25998 | 1.3811 | 0.7498 |
| baseline | sem_jogo | 3.9719 | 0.5111 | 25998 | 5.8286 | 0.7877 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 25998 | 0.9674 | 0.9644 | 0.0030 | -0.0002 | 0.0064 | 0.3114 | 0.5086 | 0.5074 | 0.0012 | 0.0000 | 0.0025 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.3811 | 1.3425 | 0.0386 | -0.0047 | 0.0863 | 2.7930 | 0.7498 | 0.7600 | -0.0102 | -0.0232 | 0.0036 |
| GLM | horas de jogo fora da capital | 2148 | 1.1687 | 1.1693 | -0.0006 | -0.0134 | 0.0162 | -0.0508 | 0.6713 | 0.6644 | 0.0069 | 0.0015 | 0.0138 |
| XGBoost | todas as horas | 25998 | 0.9406 | 0.9389 | 0.0016 | -0.0007 | 0.0041 | 0.1728 | 0.5020 | 0.5010 | 0.0010 | -0.0001 | 0.0024 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.3814 | 1.3288 | 0.0525 | 0.0011 | 0.1067 | 3.8040 | 0.7583 | 0.7675 | -0.0093 | -0.0224 | 0.0045 |
| XGBoost | horas de jogo fora da capital | 2148 | 1.1533 | 1.1483 | 0.0049 | -0.0052 | 0.0152 | 0.4282 | 0.6697 | 0.6652 | 0.0045 | -0.0009 | 0.0095 |

### Classificação de hora de risco (P(Y ≥ obs | esperado calendário+clima) < 0,10)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.111 | 0.159 | 0.134 | 0.052 |
| XGBoost | sem_jogo | 0.105 | 0.162 | 0.131 | 0.052 |
| GLM | com_jogo | 0.090 | 0.104 | 0.110 | 0.052 |
| GLM | sem_jogo | 0.084 | 0.088 | 0.093 | 0.052 |
| baseline | sem_jogo | 0.068 | 0.079 | 0.078 | 0.052 |

### SHAP (ablação mostrou ganho) com auditoria de colinearidade

Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a variável pode estar fazendo papel de hora do dia (Etapa 18).

| variavel | shap_medio_abs | rank | rho_com_hora_do_dia | participacao_pct |
|---|---|---|---|---|
| fo_hora_rel | 0.016 | 11 | -0.037 | 1.681 |
| jg_hora_rel | 0.006 | 16 | -0.003 | 0.662 |
| C_fdj | 0.003 | 19 | -0.119 | 0.337 |
| jg_publico_hist | 0.003 | 20 | 0.006 | 0.329 |
| fo_time_Palmeiras | 0.003 | 21 | 0.126 | 0.286 |
| C_pos | 0.003 | 22 | 0.069 | 0.269 |
| fo_time_Santos | 0.002 | 24 | 0.170 | 0.169 |
| fo_n_simult | 0.001 | 25 | 0.263 | 0.130 |
| dia_de_jogo_f | 0.001 | 26 | -0.023 | 0.117 |
| jg_mand_Sao Paulo | 0.001 | 27 | 0.007 | 0.098 |
| fo_time_Corinthians | 0.001 | 28 | 0.140 | 0.076 |
| C_durante | 0.001 | 30 | 0.092 | 0.059 |
| C_durante_outro | 0.001 | 31 | 0.140 | 0.059 |
| jg_comp_Copa do Brasil | 0.001 | 32 | 0.005 | 0.054 |
| jg_comp_Serie A | 0.001 | 33 | 0.006 | 0.052 |

## Entorno — `furtos_total`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.9336 | 0.5320 | 25998 | 1.2938 | 0.7292 |
| XGBoost | sem_jogo | 0.9418 | 0.5347 | 25998 | 1.5035 | 0.7309 |
| GLM | com_jogo | 0.9847 | 0.5483 | 25998 | 1.4297 | 0.7580 |
| GLM | sem_jogo | 0.9900 | 0.5503 | 25998 | 1.5664 | 0.7324 |
| baseline | sem_jogo | 3.6890 | 0.5557 | 25998 | 7.2448 | 0.7571 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 25998 | 0.9900 | 0.9847 | 0.0054 | 0.0026 | 0.0084 | 0.5431 | 0.5503 | 0.5483 | 0.0020 | 0.0012 | 0.0028 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.5664 | 1.4297 | 0.1367 | 0.0479 | 0.2443 | 8.7278 | 0.7324 | 0.7580 | -0.0256 | -0.0458 | -0.0048 |
| GLM | horas de jogo fora da capital | 2148 | 1.0411 | 1.0260 | 0.0151 | 0.0033 | 0.0292 | 1.4485 | 0.5842 | 0.5771 | 0.0071 | 0.0030 | 0.0113 |
| XGBoost | todas as horas | 25998 | 0.9418 | 0.9336 | 0.0082 | 0.0046 | 0.0129 | 0.8730 | 0.5347 | 0.5320 | 0.0027 | 0.0011 | 0.0044 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 636 | 1.5035 | 1.2938 | 0.2096 | 0.0913 | 0.3451 | 13.9426 | 0.7309 | 0.7292 | 0.0017 | -0.0179 | 0.0214 |
| XGBoost | horas de jogo fora da capital | 2148 | 0.9789 | 0.9606 | 0.0183 | 0.0028 | 0.0362 | 1.8678 | 0.5728 | 0.5664 | 0.0065 | 0.0000 | 0.0138 |

### Classificação de hora de risco (P(Y ≥ obs | esperado calendário+clima) < 0,10)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.125 | 0.179 | 0.160 | 0.052 |
| XGBoost | sem_jogo | 0.121 | 0.174 | 0.161 | 0.052 |
| GLM | com_jogo | 0.096 | 0.123 | 0.120 | 0.052 |
| GLM | sem_jogo | 0.094 | 0.120 | 0.111 | 0.052 |
| baseline | sem_jogo | 0.076 | 0.113 | 0.101 | 0.052 |

### SHAP (ablação mostrou ganho) com auditoria de colinearidade

Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a variável pode estar fazendo papel de hora do dia (Etapa 18).

| variavel | shap_medio_abs | rank | rho_com_hora_do_dia | participacao_pct |
|---|---|---|---|---|
| jg_hora_rel | 0.011 | 12 | -0.003 | 0.909 |
| jg_publico_hist | 0.006 | 14 | 0.006 | 0.509 |
| fo_hora_rel | 0.006 | 15 | -0.037 | 0.492 |
| dia_de_jogo_f | 0.005 | 18 | -0.023 | 0.411 |
| C_pos | 0.003 | 20 | 0.069 | 0.299 |
| jg_comp_Copa do Brasil | 0.003 | 22 | 0.005 | 0.238 |
| jg_comp_Serie A | 0.002 | 23 | 0.006 | 0.192 |
| fo_time_Sao Paulo | 0.002 | 24 | 0.157 | 0.191 |
| C_pre | 0.001 | 25 | 0.075 | 0.084 |
| C_pre_outro | 0.001 | 26 | 0.093 | 0.079 |
| jg_noturno | 0.001 | 27 | 0.004 | 0.073 |
| jg_classico | 0.001 | 28 | 0.005 | 0.071 |
| F_pos | 0.001 | 29 | 0.117 | 0.060 |
| fo_n_simult | 0.001 | 30 | 0.263 | 0.054 |
| C_fdj | 0.001 | 31 | -0.119 | 0.050 |

## Produto prático: risco esperado por estádio × janela (jogo típico)

Entorno de 3 km; esperado sem jogo = média observada na mesma hora × dia da semana em horas sem nenhum jogo dos 4 times; com jogo = × IRR da janela daquele estádio (modelo do entorno da Fase 2); excesso = ocorrências a mais nas 2 horas da janela; IC por simulação do coeficiente.

| desfecho | estadio | jogo_tipico | janela | esperado_sem_jogo_2h | esperado_com_jogo_2h | excesso_2h | excesso_IC95_lo | excesso_IC95_hi | IRR | p |
|---|---|---|---|---|---|---|---|---|---|---|
| crimes_violentos | Neo Quimica Arena | domingo 16h | pre | 0.70 | 0.64 | -0.06 | -0.20 | 0.13 | 0.92 | 0.51 |
| crimes_violentos | Neo Quimica Arena | domingo 16h | durante | 1.05 | 1.12 | 0.07 | -0.13 | 0.32 | 1.06 | 0.55 |
| crimes_violentos | Neo Quimica Arena | domingo 16h | pos | 1.10 | 1.44 | 0.34 | 0.03 | 0.73 | 1.31 | 0.02 |
| crimes_violentos | Neo Quimica Arena | quarta 21h30 | pre | 1.43 | 1.31 | -0.12 | -0.41 | 0.27 | 0.92 | 0.51 |
| crimes_violentos | Neo Quimica Arena | quarta 21h30 | durante | 1.76 | 1.87 | 0.11 | -0.23 | 0.54 | 1.06 | 0.55 |
| crimes_violentos | Neo Quimica Arena | quarta 21h30 | pos | 0.80 | 1.05 | 0.25 | 0.02 | 0.54 | 1.31 | 0.02 |
| crimes_violentos | Allianz Parque | domingo 16h | pre | 0.70 | 0.72 | 0.03 | -0.09 | 0.17 | 1.04 | 0.68 |
| crimes_violentos | Allianz Parque | domingo 16h | durante | 1.00 | 1.04 | 0.04 | -0.16 | 0.28 | 1.04 | 0.70 |
| crimes_violentos | Allianz Parque | domingo 16h | pos | 1.71 | 2.08 | 0.37 | 0.00 | 0.84 | 1.21 | 0.06 |
| crimes_violentos | Allianz Parque | quarta 21h30 | pre | 2.90 | 3.02 | 0.11 | -0.40 | 0.72 | 1.04 | 0.68 |
| crimes_violentos | Allianz Parque | quarta 21h30 | durante | 1.94 | 2.02 | 0.08 | -0.30 | 0.55 | 1.04 | 0.70 |
| crimes_violentos | Allianz Parque | quarta 21h30 | pos | 1.21 | 1.46 | 0.26 | -0.00 | 0.58 | 1.21 | 0.06 |
| crimes_violentos | Morumbi | domingo 16h | pre | 0.61 | 0.77 | 0.16 | -0.03 | 0.40 | 1.26 | 0.10 |
| crimes_violentos | Morumbi | domingo 16h | durante | 0.48 | 0.75 | 0.28 | 0.09 | 0.52 | 1.58 | 0.00 |
| crimes_violentos | Morumbi | domingo 16h | pos | 1.00 | 1.64 | 0.64 | 0.17 | 1.35 | 1.64 | 0.00 |
| crimes_violentos | Morumbi | quarta 21h30 | pre | 1.72 | 2.17 | 0.44 | -0.08 | 1.10 | 1.26 | 0.10 |
| crimes_violentos | Morumbi | quarta 21h30 | durante | 1.15 | 1.82 | 0.67 | 0.21 | 1.26 | 1.58 | 0.00 |
| crimes_violentos | Morumbi | quarta 21h30 | pos | 0.65 | 1.07 | 0.42 | 0.10 | 0.85 | 1.64 | 0.00 |
| roubos_total | Neo Quimica Arena | domingo 16h | pre | 0.61 | 0.56 | -0.05 | -0.18 | 0.14 | 0.92 | 0.56 |
| roubos_total | Neo Quimica Arena | domingo 16h | durante | 0.95 | 0.92 | -0.03 | -0.23 | 0.22 | 0.97 | 0.81 |
| roubos_total | Neo Quimica Arena | domingo 16h | pos | 0.76 | 1.09 | 0.33 | 0.09 | 0.63 | 1.43 | 0.00 |
| roubos_total | Neo Quimica Arena | quarta 21h30 | pre | 1.31 | 1.20 | -0.10 | -0.39 | 0.27 | 0.92 | 0.56 |
| roubos_total | Neo Quimica Arena | quarta 21h30 | durante | 1.58 | 1.53 | -0.05 | -0.38 | 0.38 | 0.97 | 0.81 |
| roubos_total | Neo Quimica Arena | quarta 21h30 | pos | 0.59 | 0.84 | 0.25 | 0.08 | 0.48 | 1.43 | 0.00 |
| roubos_total | Allianz Parque | domingo 16h | pre | 0.65 | 0.69 | 0.03 | -0.08 | 0.17 | 1.05 | 0.60 |
| roubos_total | Allianz Parque | domingo 16h | durante | 0.81 | 0.81 | -0.00 | -0.16 | 0.18 | 1.00 | 0.98 |
| roubos_total | Allianz Parque | domingo 16h | pos | 1.52 | 1.92 | 0.40 | 0.05 | 0.82 | 1.26 | 0.02 |
| roubos_total | Allianz Parque | quarta 21h30 | pre | 2.79 | 2.94 | 0.15 | -0.36 | 0.76 | 1.05 | 0.60 |
| roubos_total | Allianz Parque | quarta 21h30 | durante | 1.85 | 1.84 | -0.00 | -0.36 | 0.42 | 1.00 | 0.98 |
| roubos_total | Allianz Parque | quarta 21h30 | pos | 1.21 | 1.52 | 0.31 | 0.04 | 0.65 | 1.26 | 0.02 |
| roubos_total | Morumbi | domingo 16h | pre | 0.57 | 0.69 | 0.13 | -0.04 | 0.36 | 1.23 | 0.15 |
| roubos_total | Morumbi | domingo 16h | durante | 0.43 | 0.64 | 0.21 | 0.04 | 0.42 | 1.49 | 0.01 |
| roubos_total | Morumbi | domingo 16h | pos | 0.90 | 1.55 | 0.65 | 0.19 | 1.28 | 1.71 | 0.00 |
| roubos_total | Morumbi | quarta 21h30 | pre | 1.66 | 2.05 | 0.38 | -0.12 | 1.02 | 1.23 | 0.15 |
| roubos_total | Morumbi | quarta 21h30 | durante | 1.06 | 1.58 | 0.52 | 0.13 | 1.05 | 1.49 | 0.01 |
| roubos_total | Morumbi | quarta 21h30 | pos | 0.62 | 1.06 | 0.44 | 0.14 | 0.87 | 1.71 | 0.00 |
| furtos_total | Neo Quimica Arena | domingo 16h | pre | 0.74 | 1.15 | 0.41 | 0.12 | 0.80 | 1.55 | 0.00 |
| furtos_total | Neo Quimica Arena | domingo 16h | durante | 0.67 | 1.29 | 0.63 | 0.41 | 0.89 | 1.94 | 0.00 |
| furtos_total | Neo Quimica Arena | domingo 16h | pos | 0.95 | 1.98 | 1.03 | 0.61 | 1.55 | 2.08 | 0.00 |
| furtos_total | Neo Quimica Arena | quarta 21h30 | pre | 0.78 | 1.21 | 0.43 | 0.11 | 0.84 | 1.55 | 0.00 |
| furtos_total | Neo Quimica Arena | quarta 21h30 | durante | 0.70 | 1.35 | 0.66 | 0.41 | 0.94 | 1.94 | 0.00 |
| furtos_total | Neo Quimica Arena | quarta 21h30 | pos | 0.65 | 1.36 | 0.71 | 0.41 | 1.07 | 2.08 | 0.00 |
| furtos_total | Allianz Parque | domingo 16h | pre | 1.00 | 1.14 | 0.14 | -0.06 | 0.38 | 1.14 | 0.17 |
| furtos_total | Allianz Parque | domingo 16h | durante | 1.14 | 1.46 | 0.32 | 0.05 | 0.64 | 1.28 | 0.01 |
| furtos_total | Allianz Parque | domingo 16h | pos | 0.52 | 0.76 | 0.23 | 0.09 | 0.41 | 1.45 | 0.00 |
| furtos_total | Allianz Parque | quarta 21h30 | pre | 2.59 | 2.95 | 0.36 | -0.15 | 0.97 | 1.14 | 0.17 |
| furtos_total | Allianz Parque | quarta 21h30 | durante | 1.85 | 2.37 | 0.52 | 0.11 | 1.04 | 1.28 | 0.01 |
| furtos_total | Allianz Parque | quarta 21h30 | pos | 0.88 | 1.27 | 0.39 | 0.16 | 0.70 | 1.45 | 0.00 |
| furtos_total | Morumbi | domingo 16h | pre | 0.35 | 0.54 | 0.19 | 0.07 | 0.36 | 1.55 | 0.00 |
| furtos_total | Morumbi | domingo 16h | durante | 0.33 | 0.65 | 0.32 | 0.17 | 0.51 | 1.95 | 0.00 |
| furtos_total | Morumbi | domingo 16h | pos | 0.33 | 0.96 | 0.62 | 0.34 | 1.02 | 2.87 | 0.00 |
| furtos_total | Morumbi | quarta 21h30 | pre | 0.63 | 0.98 | 0.35 | 0.12 | 0.67 | 1.55 | 0.00 |
| furtos_total | Morumbi | quarta 21h30 | durante | 0.33 | 0.65 | 0.32 | 0.17 | 0.51 | 1.95 | 0.00 |
| furtos_total | Morumbi | quarta 21h30 | pos | 0.19 | 0.54 | 0.35 | 0.19 | 0.58 | 2.87 | 0.00 |
