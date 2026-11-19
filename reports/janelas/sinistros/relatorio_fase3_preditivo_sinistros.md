# V2 / Fase 3 — SINISTROS: bloco preditivo

Gerado por `scripts/34_preditivo_janelas.py`. Previsão feita na véspera (até 23h59 do dia anterior); só variáveis conhecidas nesse momento (calendário, agenda de jogos, público **histórico** do mandante, clima como previsão perfeita e variante com clima defasado 24 h, histórico do desfecho com defasagem ≥ 24 h). Walk-forward 12 folds mensais de 2023, janela expansiva desde 2022-01, tudo reajustado só no treino. Hiperparâmetros fixos e rasos (Etapa 17). Prophet só na escala cidade (no entorno as contagens são esparsas e o Prophet, gaussiano em log1p, não é adequado). GLM de previsão = spec da Fase 2 com mês do ano + tendência no lugar de ano × mês (o mês de teste não existe no treino).

## Resposta direta: saber que haverá jogo melhora a previsão hora a hora?

- **cidade — `acidentes_com_vitima`:** XGBoost / todas as horas: deviance +0.2% → não muda; MAE -0.001 → não muda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +1.0% → não muda; MAE +0.008 → não muda; XGBoost clima lag24 / todas as horas: deviance +0.5% → **ajuda**; MAE +0.002 → não muda; XGBoost clima lag24 / horas PRÉ/DURANTE/PÓS na capital: deviance +0.3% → não muda; MAE -0.003 → não muda; GLM / todas as horas: deviance +0.2% → não muda; MAE +0.001 → não muda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance +0.3% → não muda; MAE -0.004 → não muda; Prophet / todas as horas: deviance +0.1% → não muda; MAE +0.001 → não muda; Prophet / horas PRÉ/DURANTE/PÓS na capital: deviance +1.0% → **ajuda**; MAE +0.005 → não muda.
- **entorno — `acidentes_com_vitima`:** XGBoost / todas as horas: deviance -0.0% → não muda; MAE -0.001 → piora; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance -1.8% → não muda; MAE -0.017 → piora; GLM / todas as horas: deviance -0.4% → piora; MAE -0.001 → piora; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance -4.5% → piora; MAE -0.026 → piora.

(ganho = métrica sem as variáveis de jogo − com; > 0 = jogo ajuda; "ajuda"/"piora" só quando o IC95 por bootstrap em blocos de semana exclui 0 — IC completos nas tabelas de ablação. `XGBoost clima lag24` = variante conservadora com o clima da véspera no lugar da previsão perfeita.)

**Notas de leitura:**
- **Baseline com deviance muito alta no entorno:** a média das 4 semanas anteriores é 0 em muitas horas de contagem baixa; quando ocorre 1 registro, a deviance de Poisson explode (μ≈0). Compare o baseline pelo MAE, que é próximo dos outros modelos.
- **Deviance × MAE:** a deviance pesa mais os erros em horas de contagem alta/inesperada; o MAE pesa todos igualmente. Quando o jogo melhora a deviance mas não o MAE, o ganho está em capturar as horas de excesso (cauda), não em acertar melhor a hora típica.
- **Classificação de pico / hora de risco:** compare PR-AUC com a prevalência (linha `prevalencia_teste`): PR-AUC de um classificador aleatório = prevalência.

## Cidade — `acidentes_com_vitima`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| GLM | com_jogo | 1.2274 | 1.5239 | 8642 | 1.1976 | 1.6222 |
| GLM | sem_jogo | 1.2297 | 1.5246 | 8642 | 1.2011 | 1.6183 |
| XGBoost | com_jogo | 1.2600 | 1.5371 | 8642 | 1.2390 | 1.6504 |
| XGBoost | sem_jogo | 1.2630 | 1.5364 | 8642 | 1.2521 | 1.6583 |
| XGBoost clima lag24 | com_jogo | 1.2651 | 1.5369 | 8642 | 1.2349 | 1.6434 |
| XGBoost clima lag24 | sem_jogo | 1.2719 | 1.5386 | 8642 | 1.2381 | 1.6405 |
| Prophet | com_jogo | 1.3494 | 1.5600 | 8642 | 1.2526 | 1.6230 |
| Prophet | sem_jogo | 1.3511 | 1.5607 | 8642 | 1.2653 | 1.6283 |
| baseline | sem_jogo | 1.7794 | 1.6754 | 8642 | 1.5081 | 1.8510 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 8642 | 1.2297 | 1.2274 | 0.0024 | -0.0005 | 0.0055 | 0.1918 | 1.5246 | 1.5239 | 0.0008 | -0.0009 | 0.0027 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 642 | 1.2011 | 1.1976 | 0.0034 | -0.0114 | 0.0187 | 0.2841 | 1.6183 | 1.6222 | -0.0039 | -0.0147 | 0.0077 |
| GLM | horas de jogo fora da capital | 716 | 1.1907 | 1.1839 | 0.0067 | -0.0071 | 0.0221 | 0.5664 | 1.6098 | 1.6122 | -0.0024 | -0.0136 | 0.0096 |
| XGBoost | todas as horas | 8642 | 1.2630 | 1.2600 | 0.0030 | -0.0015 | 0.0076 | 0.2383 | 1.5364 | 1.5371 | -0.0007 | -0.0041 | 0.0027 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 642 | 1.2521 | 1.2390 | 0.0131 | -0.0109 | 0.0356 | 1.0456 | 1.6583 | 1.6504 | 0.0079 | -0.0095 | 0.0240 |
| XGBoost | horas de jogo fora da capital | 716 | 1.2323 | 1.2157 | 0.0166 | 0.0005 | 0.0353 | 1.3489 | 1.6249 | 1.6210 | 0.0038 | -0.0111 | 0.0197 |
| XGBoost clima lag24 | todas as horas | 8642 | 1.2719 | 1.2651 | 0.0068 | 0.0003 | 0.0135 | 0.5366 | 1.5386 | 1.5369 | 0.0018 | -0.0021 | 0.0058 |
| XGBoost clima lag24 | horas PRÉ/DURANTE/PÓS na capital | 642 | 1.2381 | 1.2349 | 0.0032 | -0.0195 | 0.0270 | 0.2565 | 1.6405 | 1.6434 | -0.0030 | -0.0183 | 0.0137 |
| XGBoost clima lag24 | horas de jogo fora da capital | 716 | 1.2464 | 1.2222 | 0.0241 | 0.0021 | 0.0459 | 1.9352 | 1.6295 | 1.6224 | 0.0071 | -0.0100 | 0.0233 |
| Prophet | todas as horas | 8642 | 1.3511 | 1.3494 | 0.0017 | -0.0006 | 0.0039 | 0.1244 | 1.5607 | 1.5600 | 0.0007 | -0.0005 | 0.0018 |
| Prophet | horas PRÉ/DURANTE/PÓS na capital | 642 | 1.2653 | 1.2526 | 0.0127 | 0.0020 | 0.0234 | 1.0020 | 1.6283 | 1.6230 | 0.0053 | -0.0017 | 0.0123 |
| Prophet | horas de jogo fora da capital | 716 | 1.2842 | 1.2750 | 0.0092 | -0.0003 | 0.0198 | 0.7141 | 1.6281 | 1.6252 | 0.0029 | -0.0041 | 0.0100 |

### Classificação de pico (P90 do resíduo de Pearson, definição da Fase 2)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost clima lag24 | sem_jogo | 0.168 | 0.142 | 0.192 | 0.119 |
| XGBoost clima lag24 | com_jogo | 0.168 | 0.141 | 0.189 | 0.119 |
| XGBoost | com_jogo | 0.167 | 0.153 | 0.181 | 0.119 |
| XGBoost | sem_jogo | 0.167 | 0.148 | 0.185 | 0.119 |
| GLM | com_jogo | 0.154 | 0.145 | 0.171 | 0.119 |
| GLM | sem_jogo | 0.152 | 0.124 | 0.158 | 0.119 |
| Prophet | com_jogo | 0.143 | 0.234 | 0.147 | 0.119 |
| Prophet | sem_jogo | 0.143 | 0.237 | 0.149 | 0.119 |
| baseline | sem_jogo | 0.141 | 0.164 | 0.147 | 0.119 |

### SHAP (ablação mostrou ganho) com auditoria de colinearidade

Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a variável pode estar fazendo papel de hora do dia (Etapa 18).

| variavel | shap_medio_abs | rank | rho_com_hora_do_dia | participacao_pct |
|---|---|---|---|---|
| fo_hora_rel | 0.006 | 14 | -0.032 | 1.002 |
| jg_hora_rel | 0.004 | 15 | -0.028 | 0.672 |
| jg_publico_hist | 0.003 | 16 | 0.020 | 0.487 |
| C_fdj | 0.003 | 17 | -0.199 | 0.413 |
| jg_mand_Corinthians | 0.001 | 18 | 0.020 | 0.232 |
| jg_mand_Sao Paulo | 0.001 | 19 | 0.015 | 0.197 |
| jg_comp_Serie A | 0.001 | 20 | 0.025 | 0.185 |
| F_durante | 0.001 | 22 | 0.205 | 0.152 |
| jg_classico | 0.001 | 23 | 0.019 | 0.140 |
| fo_time_Sao Paulo | 0.001 | 24 | 0.142 | 0.113 |
| jg_comp_CONMEBOL | 0.001 | 25 | 0.001 | 0.104 |
| dia_de_jogo_f | 0.001 | 26 | -0.018 | 0.102 |
| jg_noturno | 0.000 | 28 | 0.015 | 0.062 |
| jg_mand_Palmeiras | 0.000 | 29 | -0.005 | 0.059 |
| C_durante | 0.000 | 30 | 0.184 | 0.054 |

## Entorno — `acidentes_com_vitima`

### Desempenho (pooled nos 12 folds de teste)

| modelo | variante | deviance_media | MAE | n | deviance_janelas | MAE_janelas |
|---|---|---|---|---|---|---|
| XGBoost | sem_jogo | 0.4877 | 0.1869 | 25926 | 0.5833 | 0.2205 |
| XGBoost | com_jogo | 0.4880 | 0.1877 | 25926 | 0.5935 | 0.2372 |
| GLM | sem_jogo | 0.5312 | 0.2048 | 25926 | 0.6091 | 0.2413 |
| GLM | com_jogo | 0.5334 | 0.2059 | 25926 | 0.6368 | 0.2674 |
| baseline | sem_jogo | 2.7923 | 0.1916 | 25926 | 3.1695 | 0.2197 |

### Ablação (com × sem variáveis de jogo)

| modelo | subconjunto | n_horas | dev_sem_jogo | dev_com_jogo | ganho_dev | ganho_dev_IC_lo | ganho_dev_IC_hi | ganho_dev_pct | mae_sem_jogo | mae_com_jogo | ganho_mae | ganho_mae_IC_lo | ganho_mae_IC_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLM | todas as horas | 25926 | 0.5312 | 0.5334 | -0.0022 | -0.0032 | -0.0014 | -0.4149 | 0.2048 | 0.2059 | -0.0011 | -0.0022 | -0.0002 |
| GLM | horas PRÉ/DURANTE/PÓS na capital | 636 | 0.6091 | 0.6368 | -0.0276 | -0.0447 | -0.0122 | -4.5391 | 0.2413 | 0.2674 | -0.0261 | -0.0315 | -0.0216 |
| GLM | horas de jogo fora da capital | 2148 | 0.5376 | 0.5478 | -0.0102 | -0.0149 | -0.0045 | -1.9052 | 0.2169 | 0.2227 | -0.0058 | -0.0081 | -0.0035 |
| XGBoost | todas as horas | 25926 | 0.4877 | 0.4880 | -0.0002 | -0.0016 | 0.0010 | -0.0495 | 0.1869 | 0.1877 | -0.0008 | -0.0016 | -0.0001 |
| XGBoost | horas PRÉ/DURANTE/PÓS na capital | 636 | 0.5833 | 0.5935 | -0.0102 | -0.0287 | 0.0079 | -1.7519 | 0.2205 | 0.2372 | -0.0168 | -0.0217 | -0.0125 |
| XGBoost | horas de jogo fora da capital | 2148 | 0.5082 | 0.5140 | -0.0058 | -0.0115 | 0.0003 | -1.1489 | 0.1972 | 0.1966 | 0.0006 | -0.0018 | 0.0029 |

### Classificação de hora de risco (P(Y ≥ obs | esperado calendário+clima) < 0,10)

| modelo | variante | PR_AUC_fold_macro | recall_medio | precision_media | prevalencia_teste |
|---|---|---|---|---|---|
| XGBoost | com_jogo | 0.109 | 0.096 | 0.107 | 0.040 |
| XGBoost | sem_jogo | 0.105 | 0.099 | 0.121 | 0.040 |
| GLM | sem_jogo | 0.088 | 0.079 | 0.091 | 0.040 |
| GLM | com_jogo | 0.085 | 0.067 | 0.086 | 0.040 |
| baseline | sem_jogo | 0.061 | 0.226 | 0.084 | 0.040 |

## Produto prático: risco esperado por estádio × janela (jogo típico)

Entorno de 3 km; esperado sem jogo = média observada na mesma hora × dia da semana em horas sem nenhum jogo dos 4 times; com jogo = × IRR da janela daquele estádio (modelo do entorno da Fase 2); excesso = ocorrências a mais nas 2 horas da janela; IC por simulação do coeficiente.

| desfecho | estadio | jogo_tipico | janela | esperado_sem_jogo_2h | esperado_com_jogo_2h | excesso_2h | excesso_IC95_lo | excesso_IC95_hi | IRR | p |
|---|---|---|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | Neo Quimica Arena | domingo 16h | pre | 0.17 | 0.29 | 0.12 | 0.03 | 0.25 | 1.69 | 0.00 |
| acidentes_com_vitima | Neo Quimica Arena | domingo 16h | durante | 0.10 | 0.13 | 0.04 | -0.01 | 0.11 | 1.38 | 0.16 |
| acidentes_com_vitima | Neo Quimica Arena | domingo 16h | pos | 0.10 | 0.10 | 0.01 | -0.04 | 0.11 | 1.08 | 0.81 |
| acidentes_com_vitima | Neo Quimica Arena | quarta 21h30 | pre | 0.35 | 0.59 | 0.24 | 0.06 | 0.49 | 1.69 | 0.00 |
| acidentes_com_vitima | Neo Quimica Arena | quarta 21h30 | durante | 0.12 | 0.17 | 0.05 | -0.01 | 0.14 | 1.38 | 0.16 |
| acidentes_com_vitima | Neo Quimica Arena | quarta 21h30 | pos | 0.16 | 0.17 | 0.01 | -0.07 | 0.16 | 1.08 | 0.81 |
| acidentes_com_vitima | Allianz Parque | domingo 16h | pre | 0.30 | 0.42 | 0.12 | -0.03 | 0.34 | 1.38 | 0.12 |
| acidentes_com_vitima | Allianz Parque | domingo 16h | durante | 0.00 | 0.00 | 0.00 | -0.00 | 0.00 | 1.05 | 0.84 |
| acidentes_com_vitima | Allianz Parque | domingo 16h | pos | 0.14 | 0.15 | 0.00 | -0.05 | 0.10 | 1.02 | 0.94 |
| acidentes_com_vitima | Allianz Parque | quarta 21h30 | pre | 0.20 | 0.28 | 0.08 | -0.02 | 0.21 | 1.38 | 0.12 |
| acidentes_com_vitima | Allianz Parque | quarta 21h30 | durante | 0.12 | 0.13 | 0.01 | -0.04 | 0.10 | 1.05 | 0.84 |
| acidentes_com_vitima | Allianz Parque | quarta 21h30 | pos | 0.09 | 0.10 | 0.00 | -0.04 | 0.06 | 1.02 | 0.94 |
| acidentes_com_vitima | Morumbi | domingo 16h | pre | 0.13 | 0.17 | 0.04 | -0.02 | 0.12 | 1.27 | 0.28 |
| acidentes_com_vitima | Morumbi | domingo 16h | durante | 0.10 | 0.10 | 0.01 | -0.03 | 0.07 | 1.09 | 0.70 |
| acidentes_com_vitima | Morumbi | domingo 16h | pos | 0.19 | 0.21 | 0.01 | -0.07 | 0.14 | 1.08 | 0.76 |
| acidentes_com_vitima | Morumbi | quarta 21h30 | pre | 0.30 | 0.38 | 0.08 | -0.05 | 0.28 | 1.27 | 0.28 |
| acidentes_com_vitima | Morumbi | quarta 21h30 | durante | 0.12 | 0.13 | 0.01 | -0.04 | 0.09 | 1.09 | 0.70 |
| acidentes_com_vitima | Morumbi | quarta 21h30 | pos | 0.09 | 0.10 | 0.01 | -0.03 | 0.07 | 1.08 | 0.76 |
