# V2 / Fase 3 — resumo do bloco preditivo

## CRIMES

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

## SINISTROS

## Resposta direta: saber que haverá jogo melhora a previsão hora a hora?

- **cidade — `acidentes_com_vitima`:** XGBoost / todas as horas: deviance +0.2% → não muda; MAE -0.001 → não muda; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance +1.0% → não muda; MAE +0.008 → não muda; XGBoost clima lag24 / todas as horas: deviance +0.5% → **ajuda**; MAE +0.002 → não muda; XGBoost clima lag24 / horas PRÉ/DURANTE/PÓS na capital: deviance +0.3% → não muda; MAE -0.003 → não muda; GLM / todas as horas: deviance +0.2% → não muda; MAE +0.001 → não muda; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance +0.3% → não muda; MAE -0.004 → não muda; Prophet / todas as horas: deviance +0.1% → não muda; MAE +0.001 → não muda; Prophet / horas PRÉ/DURANTE/PÓS na capital: deviance +1.0% → **ajuda**; MAE +0.005 → não muda.
- **entorno — `acidentes_com_vitima`:** XGBoost / todas as horas: deviance -0.0% → não muda; MAE -0.001 → piora; XGBoost / horas PRÉ/DURANTE/PÓS na capital: deviance -1.8% → não muda; MAE -0.017 → piora; GLM / todas as horas: deviance -0.4% → piora; MAE -0.001 → piora; GLM / horas PRÉ/DURANTE/PÓS na capital: deviance -4.5% → piora; MAE -0.026 → piora.

(ganho = métrica sem as variáveis de jogo − com; > 0 = jogo ajuda; "ajuda"/"piora" só quando o IC95 por bootstrap em blocos de semana exclui 0 — IC completos nas tabelas de ablação. `XGBoost clima lag24` = variante conservadora com o clima da véspera no lugar da previsão perfeita.)

**Notas de leitura:**
- **Baseline com deviance muito alta no entorno:** a média das 4 semanas anteriores é 0 em muitas horas de contagem baixa; quando ocorre 1 registro, a deviance de Poisson explode (μ≈0). Compare o baseline pelo MAE, que é próximo dos outros modelos.
- **Deviance × MAE:** a deviance pesa mais os erros em horas de contagem alta/inesperada; o MAE pesa todos igualmente. Quando o jogo melhora a deviance mas não o MAE, o ganho está em capturar as horas de excesso (cauda), não em acertar melhor a hora típica.
- **Classificação de pico / hora de risco:** compare PR-AUC com a prevalência (linha `prevalencia_teste`): PR-AUC de um classificador aleatório = prevalência.

