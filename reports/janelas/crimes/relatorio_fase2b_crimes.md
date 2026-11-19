# V2 / Fase 2b — CRIMES: checagens de robustez

Gerado por `scripts/33b_robustez_janelas.py`. **O modelo principal da Fase 2 não muda**; aqui só se acrescentam robustezes. Domínio analisado isoladamente.

## 1. PRÉ da capital

### 1a/1b/1d. GLM com EF hora × mês, só com os jogos do pareado e PRÉ estendido

O pareado compara cada jogo com semanas próximas e por isso controla a mudança do perfil horário ao longo do ano (o pôr do sol muda mais de 1 h em SP; roubo é sensível à escuridão); o GLM principal só tinha hora × dia da semana + ano × mês. **1a** acrescenta EF hora do dia × mês (alternativa: × trimestre). **1b** reestima o GLM só com os 112 jogos que entraram no desenho pareado (as janelas e dias dos outros jogos da capital saem da amostra). **1d** PRÉ estendido = horas k = −3, −2, −1.

| desfecho | spec | janela | IRR | var_pct | IC95_lo | IC95_hi | p |
|---|---|---|---|---|---|---|---|
| crimes_violentos | principal | capital PRÉ | 1.047 | 4.722 | 1.016 | 1.079 | 0.003 |
| crimes_violentos | + EF hora×mês | capital PRÉ | 1.027 | 2.724 | 1.000 | 1.056 | 0.053 |
| crimes_violentos | + EF hora×trimestre | capital PRÉ | 1.036 | 3.564 | 1.006 | 1.066 | 0.017 |
| roubos_total | principal | capital PRÉ | 1.053 | 5.282 | 1.018 | 1.089 | 0.003 |
| roubos_total | + EF hora×mês | capital PRÉ | 1.029 | 2.874 | 0.999 | 1.060 | 0.060 |
| roubos_total | + EF hora×trimestre | capital PRÉ | 1.038 | 3.822 | 1.006 | 1.072 | 0.020 |
| crimes_violentos | PRÉ estendido (k=−3..−1) | capital PRÉ estendido (k=−3..−1) | 1.046 | 4.584 | 1.019 | 1.073 | 0.001 |
| crimes_violentos | PRÉ estendido + EF hora×mês | capital PRÉ estendido (k=−3..−1) | 1.029 | 2.928 | 1.005 | 1.054 | 0.017 |
| roubos_total | PRÉ estendido (k=−3..−1) | capital PRÉ estendido (k=−3..−1) | 1.049 | 4.851 | 1.019 | 1.079 | 0.001 |
| roubos_total | PRÉ estendido + EF hora×mês | capital PRÉ estendido (k=−3..−1) | 1.028 | 2.825 | 1.002 | 1.055 | 0.035 |
| crimes_violentos | só jogos do pareado | capital PRÉ | 1.041 | 4.138 | 1.005 | 1.079 | 0.026 |
| crimes_violentos | só jogos do pareado + EF hora×mês | capital PRÉ | 1.020 | 1.973 | 0.986 | 1.054 | 0.252 |
| roubos_total | só jogos do pareado | capital PRÉ | 1.045 | 4.504 | 1.004 | 1.087 | 0.030 |
| roubos_total | só jogos do pareado + EF hora×mês | capital PRÉ | 1.019 | 1.867 | 0.983 | 1.055 | 0.305 |

Todos os termos e desfechos, principal vs EF hora × mês / × trimestre:

| desfecho | termo | + EF hora×mês | + EF hora×trimestre | principal |
|---|---|---|---|---|
| crimes_violentos | C_durante | 0.984 (p=0.306) | 0.988 (p=0.436) | 0.979 (p=0.191) |
| crimes_violentos | C_fdj | 1.010 (p=0.213) | 1.008 (p=0.330) | 1.008 (p=0.328) |
| crimes_violentos | C_pos | 1.027 (p=0.052) | 1.026 (p=0.054) | 1.027 (p=0.048) |
| crimes_violentos | C_pre | 1.027 (p=0.053) | 1.036 (p=0.017) | 1.047 (p=0.003) |
| crimes_violentos | F_durante | 0.978 (p=0.169) | 0.981 (p=0.236) | 0.975 (p=0.127) |
| crimes_violentos | F_pos | 1.002 (p=0.874) | 1.005 (p=0.691) | 0.998 (p=0.906) |
| crimes_violentos | F_pre | 0.968 (p=0.012) | 0.975 (p=0.061) | 0.985 (p=0.278) |
| furtos_total | C_durante | 1.019 (p=0.231) | 1.021 (p=0.202) | 1.014 (p=0.389) |
| furtos_total | C_fdj | 1.020 (p=0.013) | 1.019 (p=0.014) | 1.019 (p=0.015) |
| furtos_total | C_pos | 1.048 (p=0.012) | 1.045 (p=0.021) | 1.041 (p=0.035) |
| furtos_total | C_pre | 1.032 (p=0.059) | 1.034 (p=0.043) | 1.041 (p=0.021) |
| furtos_total | F_durante | 1.014 (p=0.423) | 1.013 (p=0.464) | 1.011 (p=0.543) |
| furtos_total | F_pos | 1.013 (p=0.486) | 1.010 (p=0.617) | 1.004 (p=0.830) |
| furtos_total | F_pre | 1.012 (p=0.446) | 1.012 (p=0.415) | 1.024 (p=0.134) |
| lesao_corporal_dolosa | C_durante | 0.975 (p=0.365) | 0.975 (p=0.369) | 0.969 (p=0.260) |
| lesao_corporal_dolosa | C_fdj | 1.015 (p=0.315) | 1.014 (p=0.355) | 1.014 (p=0.353) |
| lesao_corporal_dolosa | C_pos | 1.035 (p=0.171) | 1.032 (p=0.194) | 1.034 (p=0.159) |
| lesao_corporal_dolosa | C_pre | 1.017 (p=0.517) | 1.022 (p=0.399) | 1.025 (p=0.344) |
| lesao_corporal_dolosa | F_durante | 0.978 (p=0.421) | 0.978 (p=0.412) | 0.977 (p=0.396) |
| lesao_corporal_dolosa | F_pos | 0.985 (p=0.569) | 0.984 (p=0.518) | 0.982 (p=0.469) |
| lesao_corporal_dolosa | F_pre | 0.960 (p=0.165) | 0.961 (p=0.188) | 0.961 (p=0.181) |
| roubos_total | C_durante | 0.987 (p=0.448) | 0.991 (p=0.603) | 0.982 (p=0.307) |
| roubos_total | C_fdj | 1.010 (p=0.308) | 1.007 (p=0.458) | 1.007 (p=0.451) |
| roubos_total | C_pos | 1.026 (p=0.080) | 1.026 (p=0.080) | 1.026 (p=0.090) |
| roubos_total | C_pre | 1.029 (p=0.060) | 1.038 (p=0.020) | 1.053 (p=0.003) |
| roubos_total | F_durante | 0.976 (p=0.166) | 0.980 (p=0.242) | 0.972 (p=0.124) |
| roubos_total | F_pos | 1.004 (p=0.799) | 1.008 (p=0.597) | 1.000 (p=0.996) |
| roubos_total | F_pre | 0.967 (p=0.029) | 0.976 (p=0.125) | 0.989 (p=0.520) |

**Leitura:**
- `crimes_violentos`: PRÉ +4.7% (p=0.003) no principal → +2.7% (p=0.053) com EF hora×mês e +3.6% (p=0.017) com hora×trimestre (58% do efeito original com hora×mês). Só os 112 jogos do pareado: +4.1% (p=0.026); + hora×mês: +2.0% (p=0.252). PRÉ estendido k=−3..−1: +4.6% (p=0.001); + hora×mês +2.9% (p=0.017).
- `roubos_total`: PRÉ +5.3% (p=0.003) no principal → +2.9% (p=0.060) com EF hora×mês e +3.8% (p=0.020) com hora×trimestre (54% do efeito original com hora×mês). Só os 112 jogos do pareado: +4.5% (p=0.030); + hora×mês: +1.9% (p=0.305). PRÉ estendido k=−3..−1: +4.9% (p=0.001); + hora×mês +2.8% (p=0.035).

### 1c. Dose-resposta do público com EF hora × mês (cidade toda)

| desfecho | spec | termo | IRR | IC95_lo | IC95_hi | p |
|---|---|---|---|---|---|---|
| crimes_violentos | log | C_pre__x_logpub | 1.078 | 0.976 | 1.192 | 0.140 |
| crimes_violentos | log | C_durante__x_logpub | 1.093 | 0.996 | 1.199 | 0.062 |
| crimes_violentos | log | C_pos__x_logpub | 1.109 | 1.029 | 1.196 | 0.007 |
| crimes_violentos | log | C_pre | 1.030 | 1.002 | 1.058 | 0.034 |
| crimes_violentos | log | C_durante | 0.987 | 0.957 | 1.017 | 0.388 |
| crimes_violentos | log | C_pos | 1.027 | 1.000 | 1.054 | 0.046 |
| roubos_total | log | C_pre__x_logpub | 1.078 | 0.969 | 1.199 | 0.166 |
| roubos_total | log | C_durante__x_logpub | 1.092 | 0.981 | 1.215 | 0.107 |
| roubos_total | log | C_pos__x_logpub | 1.137 | 1.048 | 1.234 | 0.002 |
| roubos_total | log | C_pre | 1.032 | 1.002 | 1.063 | 0.039 |
| roubos_total | log | C_durante | 0.991 | 0.958 | 1.024 | 0.578 |
| roubos_total | log | C_pos | 1.027 | 0.998 | 1.056 | 0.066 |
| crimes_violentos | tercis | C_pre__T1 | 1.006 | 0.960 | 1.054 | 0.805 |
| crimes_violentos | tercis | C_pre__T2 | 1.023 | 0.982 | 1.065 | 0.277 |
| crimes_violentos | tercis | C_pre__T3 | 1.062 | 1.014 | 1.112 | 0.011 |
| crimes_violentos | tercis | C_durante__T1 | 0.965 | 0.928 | 1.004 | 0.080 |
| crimes_violentos | tercis | C_durante__T2 | 0.994 | 0.945 | 1.046 | 0.826 |
| crimes_violentos | tercis | C_durante__T3 | 1.000 | 0.942 | 1.060 | 0.988 |
| crimes_violentos | tercis | C_pos__T1 | 1.004 | 0.959 | 1.050 | 0.869 |
| crimes_violentos | tercis | C_pos__T2 | 1.029 | 0.979 | 1.081 | 0.266 |
| crimes_violentos | tercis | C_pos__T3 | 1.050 | 1.007 | 1.095 | 0.024 |
| roubos_total | tercis | C_pre__T1 | 1.008 | 0.958 | 1.061 | 0.752 |
| roubos_total | tercis | C_pre__T2 | 1.029 | 0.986 | 1.075 | 0.193 |
| roubos_total | tercis | C_pre__T3 | 1.058 | 1.002 | 1.116 | 0.042 |
| roubos_total | tercis | C_durante__T1 | 0.973 | 0.931 | 1.016 | 0.217 |
| roubos_total | tercis | C_durante__T2 | 0.993 | 0.940 | 1.049 | 0.808 |
| roubos_total | tercis | C_durante__T3 | 1.004 | 0.939 | 1.074 | 0.906 |
| roubos_total | tercis | C_pos__T1 | 0.996 | 0.950 | 1.044 | 0.853 |
| roubos_total | tercis | C_pos__T2 | 1.026 | 0.971 | 1.084 | 0.370 |
| roubos_total | tercis | C_pos__T3 | 1.062 | 1.014 | 1.112 | 0.011 |

### 1e. Regra do veredito revista

Implementada em `33_analise_janelas.py` (vereditos da Fase 2 regenerados): entre os candidatos (p_BH < 0,05, placebo p < 0,05, NB e cluster por dia com o mesmo sinal), **efeito robusto** só se o pareado **confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, pareado inconclusivo** se o pareado não confirma mas não contradiz (IC95 do pareado contém a estimativa do GLM); **contradito pelo pareado** se o IC95 do pareado exclui a estimativa do GLM. Assim, nenhum efeito é chamado de robusto com o pareado contra.

| desfecho | janela | var_pct | p_BH_dominio | p_placebo | pareado_confirma | pareado_contradiz | veredito |
|---|---|---|---|---|---|---|---|
| crimes_violentos | capital PRÉ | 4.722 | 0.041 | 0.000 | False | False | robusto no GLM, pareado inconclusivo |
| crimes_violentos | capital PÓS | 2.674 | 0.223 | 0.036 | False | False | sinal não robusto |
| roubos_total | capital PRÉ | 5.282 | 0.041 | 0.000 | False | False | robusto no GLM, pareado inconclusivo |
| furtos_total | capital PRÉ | 4.149 | 0.147 | 0.006 | False | False | sinal não robusto |
| furtos_total | capital PÓS | 4.112 | 0.195 | 0.012 | False | False | sinal não robusto |

## 2. Entorno dos estádios

### 2a. BH na família espacial

Família = estádios × janelas × desfechos × (disco/bairros) = 72 testes; os 3 estádios agregados formam uma família à parte.

| desfecho | area | janela | IRR | IC95_lo | IC95_hi | p | p_BH_agregados |
|---|---|---|---|---|---|---|---|
| crimes_violentos | bairros | durante | 1.218 | 1.051 | 1.411 | 0.009 | 0.017 |
| crimes_violentos | bairros | pos | 1.365 | 1.143 | 1.629 | 0.001 | 0.001 |
| crimes_violentos | bairros | pre | 1.131 | 0.944 | 1.355 | 0.183 | 0.237 |
| furtos_total | bairros | durante | 2.168 | 1.860 | 2.527 | 0.000 | 0.000 |
| furtos_total | bairros | pos | 2.522 | 2.156 | 2.951 | 0.000 | 0.000 |
| furtos_total | bairros | pre | 1.793 | 1.497 | 2.148 | 0.000 | 0.000 |
| lesao_corporal_dolosa | bairros | durante | 1.456 | 1.070 | 1.981 | 0.017 | 0.029 |
| lesao_corporal_dolosa | bairros | pos | 0.650 | 0.416 | 1.014 | 0.058 | 0.087 |
| lesao_corporal_dolosa | bairros | pre | 1.048 | 0.707 | 1.552 | 0.817 | 0.817 |
| roubos_total | bairros | durante | 1.231 | 1.038 | 1.459 | 0.017 | 0.029 |
| roubos_total | bairros | pos | 1.544 | 1.288 | 1.850 | 0.000 | 0.000 |
| roubos_total | bairros | pre | 1.179 | 0.964 | 1.443 | 0.110 | 0.155 |
| crimes_violentos | disco | durante | 1.150 | 1.010 | 1.309 | 0.035 | 0.055 |
| crimes_violentos | disco | pos | 1.310 | 1.140 | 1.506 | 0.000 | 0.000 |
| crimes_violentos | disco | pre | 1.053 | 0.924 | 1.200 | 0.439 | 0.479 |
| furtos_total | disco | durante | 1.657 | 1.469 | 1.868 | 0.000 | 0.000 |
| furtos_total | disco | pos | 1.847 | 1.601 | 2.132 | 0.000 | 0.000 |
| furtos_total | disco | pre | 1.318 | 1.149 | 1.511 | 0.000 | 0.000 |
| lesao_corporal_dolosa | disco | durante | 2.044 | 1.493 | 2.798 | 0.000 | 0.000 |
| lesao_corporal_dolosa | disco | pos | 0.742 | 0.477 | 1.156 | 0.188 | 0.237 |
| lesao_corporal_dolosa | disco | pre | 1.102 | 0.729 | 1.667 | 0.644 | 0.672 |
| roubos_total | disco | durante | 1.082 | 0.941 | 1.245 | 0.270 | 0.324 |
| roubos_total | disco | pos | 1.386 | 1.204 | 1.596 | 0.000 | 0.000 |
| roubos_total | disco | pre | 1.057 | 0.922 | 1.211 | 0.427 | 0.479 |

Termos por estádio que sobrevivem ao BH da família espacial:

| estadio | area | desfecho | janela | IRR | p | p_BH_familia_espacial |
|---|---|---|---|---|---|---|
| Neo Quimica Arena | disco | lesao_corporal_dolosa | durante | 1.853 | 0.014 | 0.035 |
| Neo Quimica Arena | disco | roubos_total | pos | 1.430 | 0.004 | 0.012 |
| Neo Quimica Arena | disco | furtos_total | pre | 1.551 | 0.004 | 0.011 |
| Neo Quimica Arena | disco | furtos_total | durante | 1.941 | 0.000 | 0.000 |
| Neo Quimica Arena | disco | furtos_total | pos | 2.078 | 0.000 | 0.000 |
| Neo Quimica Arena | bairros | furtos_total | pre | 1.641 | 0.001 | 0.004 |
| Neo Quimica Arena | bairros | furtos_total | durante | 2.080 | 0.000 | 0.000 |
| Neo Quimica Arena | bairros | furtos_total | pos | 2.305 | 0.000 | 0.000 |
| Allianz Parque | disco | furtos_total | durante | 1.280 | 0.013 | 0.034 |
| Allianz Parque | disco | furtos_total | pos | 1.449 | 0.000 | 0.002 |
| Allianz Parque | bairros | furtos_total | pre | 1.622 | 0.001 | 0.003 |
| Allianz Parque | bairros | furtos_total | durante | 1.722 | 0.000 | 0.000 |
| Allianz Parque | bairros | furtos_total | pos | 1.900 | 0.000 | 0.000 |
| Morumbi | disco | crimes_violentos | durante | 1.580 | 0.001 | 0.005 |
| Morumbi | disco | crimes_violentos | pos | 1.640 | 0.005 | 0.014 |
| Morumbi | disco | lesao_corporal_dolosa | durante | 3.336 | 0.000 | 0.002 |
| Morumbi | disco | roubos_total | durante | 1.488 | 0.008 | 0.023 |
| Morumbi | disco | roubos_total | pos | 1.713 | 0.002 | 0.007 |
| Morumbi | disco | furtos_total | pre | 1.554 | 0.001 | 0.005 |
| Morumbi | disco | furtos_total | durante | 1.952 | 0.000 | 0.000 |
| Morumbi | disco | furtos_total | pos | 2.871 | 0.000 | 0.000 |
| Morumbi | bairros | crimes_violentos | durante | 1.778 | 0.003 | 0.010 |
| Morumbi | bairros | crimes_violentos | pos | 1.901 | 0.001 | 0.004 |
| Morumbi | bairros | roubos_total | durante | 1.810 | 0.003 | 0.010 |
| Morumbi | bairros | roubos_total | pos | 2.137 | 0.000 | 0.000 |
| Morumbi | bairros | furtos_total | pre | 2.753 | 0.000 | 0.000 |
| Morumbi | bairros | furtos_total | durante | 3.289 | 0.000 | 0.000 |
| Morumbi | bairros | furtos_total | pos | 5.616 | 0.000 | 0.000 |

### 2b. Por estádio e tipo, com o resto da cidade na mesma janela

`IRR_resto` = resto da cidade (fora dos 3 discos) nas janelas **dos jogos daquele estádio**, mesmo modelo. Deslocamento = entorno sobe enquanto o resto da cidade fica igual ou cai.

| desfecho | estadio | janela | IRR_disco | p_disco | p_BH_familia_espacial_disco | IRR_bairros | p_bairros | IRR_resto | p_resto |
|---|---|---|---|---|---|---|---|---|---|
| crimes_violentos | Allianz Parque | pre | 1.039 | 0.683 | 0.806 | 1.246 | 0.162 | 1.048 | 0.055 |
| crimes_violentos | Allianz Parque | durante | 1.041 | 0.704 | 0.813 | 1.298 | 0.041 | 0.985 | 0.591 |
| crimes_violentos | Allianz Parque | pos | 1.214 | 0.056 | 0.101 | 1.340 | 0.050 | 0.987 | 0.595 |
| crimes_violentos | Morumbi | pre | 1.257 | 0.095 | 0.163 | 1.369 | 0.038 | 1.051 | 0.047 |
| crimes_violentos | Morumbi | durante | 1.580 | 0.001 | 0.005 | 1.778 | 0.003 | 0.990 | 0.705 |
| crimes_violentos | Morumbi | pos | 1.640 | 0.005 | 0.014 | 1.901 | 0.001 | 1.012 | 0.573 |
| crimes_violentos | Neo Quimica Arena | pre | 0.916 | 0.511 | 0.652 | 0.785 | 0.160 | 1.045 | 0.047 |
| crimes_violentos | Neo Quimica Arena | durante | 1.065 | 0.550 | 0.678 | 1.040 | 0.711 | 0.951 | 0.065 |
| crimes_violentos | Neo Quimica Arena | pos | 1.314 | 0.024 | 0.056 | 1.171 | 0.257 | 1.047 | 0.041 |
| furtos_total | Allianz Parque | pre | 1.140 | 0.171 | 0.252 | 1.622 | 0.001 | 1.046 | 0.111 |
| furtos_total | Allianz Parque | durante | 1.280 | 0.013 | 0.034 | 1.722 | 0.000 | 1.005 | 0.858 |
| furtos_total | Allianz Parque | pos | 1.449 | 0.000 | 0.002 | 1.900 | 0.000 | 0.987 | 0.667 |
| furtos_total | Morumbi | pre | 1.554 | 0.001 | 0.005 | 2.753 | 0.000 | 0.982 | 0.556 |
| furtos_total | Morumbi | durante | 1.952 | 0.000 | 0.000 | 3.289 | 0.000 | 0.989 | 0.637 |
| furtos_total | Morumbi | pos | 2.871 | 0.000 | 0.000 | 5.616 | 0.000 | 1.018 | 0.542 |
| furtos_total | Neo Quimica Arena | pre | 1.551 | 0.004 | 0.011 | 1.641 | 0.001 | 1.059 | 0.025 |
| furtos_total | Neo Quimica Arena | durante | 1.941 | 0.000 | 0.000 | 2.080 | 0.000 | 0.991 | 0.762 |
| furtos_total | Neo Quimica Arena | pos | 2.078 | 0.000 | 0.000 | 2.305 | 0.000 | 1.001 | 0.984 |
| lesao_corporal_dolosa | Allianz Parque | pre | 0.968 | 0.922 | 0.977 | 1.010 | 0.983 | 1.000 | 0.998 |
| lesao_corporal_dolosa | Allianz Parque | durante | 1.680 | 0.051 | 0.095 | 1.912 | 0.041 | 0.977 | 0.634 |
| lesao_corporal_dolosa | Allianz Parque | pos | 0.777 | 0.463 | 0.606 | 1.014 | 0.976 | 0.997 | 0.937 |
| lesao_corporal_dolosa | Morumbi | pre | 1.800 | 0.192 | 0.276 | 1.092 | 0.870 | 0.997 | 0.929 |
| lesao_corporal_dolosa | Morumbi | durante | 3.336 | 0.000 | 0.002 | 1.652 | 0.161 | 0.943 | 0.181 |
| lesao_corporal_dolosa | Morumbi | pos | 0.695 | 0.516 | 0.652 | 0.534 | 0.297 | 1.016 | 0.699 |
| lesao_corporal_dolosa | Neo Quimica Arena | pre | 0.953 | 0.888 | 0.954 | 1.049 | 0.845 | 1.037 | 0.378 |
| lesao_corporal_dolosa | Neo Quimica Arena | durante | 1.853 | 0.014 | 0.035 | 1.238 | 0.309 | 0.932 | 0.123 |
| lesao_corporal_dolosa | Neo Quimica Arena | pos | 0.726 | 0.368 | 0.491 | 0.561 | 0.049 | 1.086 | 0.075 |
| roubos_total | Allianz Parque | pre | 1.053 | 0.597 | 0.716 | 1.292 | 0.129 | 1.062 | 0.021 |
| roubos_total | Allianz Parque | durante | 0.998 | 0.983 | 0.983 | 1.247 | 0.091 | 0.986 | 0.648 |
| roubos_total | Allianz Parque | pos | 1.260 | 0.024 | 0.056 | 1.402 | 0.026 | 0.986 | 0.599 |
| roubos_total | Morumbi | pre | 1.229 | 0.148 | 0.237 | 1.429 | 0.027 | 1.062 | 0.035 |
| roubos_total | Morumbi | durante | 1.488 | 0.008 | 0.023 | 1.810 | 0.003 | 1.002 | 0.959 |
| roubos_total | Morumbi | pos | 1.713 | 0.002 | 0.007 | 2.137 | 0.000 | 1.012 | 0.606 |
| roubos_total | Neo Quimica Arena | pre | 0.920 | 0.555 | 0.678 | 0.705 | 0.112 | 1.048 | 0.056 |
| roubos_total | Neo Quimica Arena | durante | 0.971 | 0.813 | 0.915 | 0.995 | 0.975 | 0.956 | 0.119 |
| roubos_total | Neo Quimica Arena | pos | 1.430 | 0.004 | 0.012 | 1.393 | 0.024 | 1.039 | 0.100 |

Na janela DURANTE, 8 de 12 combinações estádio × desfecho têm entorno acima de 1 e resto da cidade abaixo de 1 (padrão de deslocamento).

### 2c. Furtos e roubos do entorno por DESCR_CONDUTA (exploratório)

Registros com hora no disco de 3 km (sem células de empilhamento). O = observado nas janelas dos jogos do próprio estádio; E = taxa das horas sem jogo no mesmo estádio, mesma hora × dia da semana. Descritivo (sem EF de mês nem de clima): serve para ver **que tipo** de ocorrência sobe, não para medir o tamanho do efeito.

| janela | natureza | conduta | O | E | O/E | IC95_lo | IC95_hi | parcela_do_excesso_positivo |
|---|---|---|---|---|---|---|---|---|
| DURANTE+PÓS | furto | (NULO) | 25 | 1.43 | 17.47 | 11.30 | 25.78 | 0.09 |
| DURANTE+PÓS | furto | DEMAIS (agrupadas) | 22 | 19.53 | 1.13 | 0.71 | 1.71 | 0.01 |
| DURANTE+PÓS | furto | ESTABELECIMENTO COMERCIAL | 11 | 9.54 | 1.15 | 0.58 | 2.06 | 0.01 |
| DURANTE+PÓS | furto | INTERIOR DE VEICULO | 42 | 32.53 | 1.29 | 0.93 | 1.75 | 0.04 |
| DURANTE+PÓS | furto | INTERIOR ESTABELECIMENTO | 12 | 12.15 | 0.99 | 0.51 | 1.73 | 0.00 |
| DURANTE+PÓS | furto | OUTROS | 177 | 126.59 | 1.40 | 1.20 | 1.62 | 0.19 |
| DURANTE+PÓS | furto | TRANSEUNTE | 78 | 29.15 | 2.68 | 2.12 | 3.34 | 0.19 |
| DURANTE+PÓS | furto | VEICULO | 228 | 100.36 | 2.27 | 1.99 | 2.59 | 0.48 |
| DURANTE+PÓS | roubo | (NULO) | 35 | 9.20 | 3.80 | 2.65 | 5.29 | 0.20 |
| DURANTE+PÓS | roubo | DEMAIS (agrupadas) | 2 | 4.42 | 0.45 | 0.05 | 1.63 | 0.00 |
| DURANTE+PÓS | roubo | ESTABELECIMENTO COMERCIAL | 10 | 7.60 | 1.32 | 0.63 | 2.42 | 0.02 |
| DURANTE+PÓS | roubo | INTERIOR DE VEICULO | 12 | 8.80 | 1.36 | 0.70 | 2.38 | 0.02 |
| DURANTE+PÓS | roubo | INTERIOR ESTABELECIMENTO | 8 | 6.66 | 1.20 | 0.52 | 2.37 | 0.01 |
| DURANTE+PÓS | roubo | OUTROS | 440 | 352.77 | 1.25 | 1.13 | 1.37 | 0.67 |
| DURANTE+PÓS | roubo | TRANSEUNTE | 89 | 77.89 | 1.14 | 0.92 | 1.41 | 0.08 |
| DURANTE+PÓS | roubo | VEICULO | 60 | 62.37 | 0.96 | 0.73 | 1.24 | 0.00 |
| PRÉ | furto | (NULO) | 5 | 1.67 | 2.99 | 0.97 | 6.97 | 0.04 |
| PRÉ | furto | DEMAIS (agrupadas) | 18 | 11.80 | 1.53 | 0.90 | 2.41 | 0.08 |
| PRÉ | furto | ESTABELECIMENTO COMERCIAL | 8 | 9.57 | 0.84 | 0.36 | 1.65 | 0.00 |
| PRÉ | furto | INTERIOR DE VEICULO | 30 | 26.81 | 1.12 | 0.75 | 1.60 | 0.04 |
| PRÉ | furto | INTERIOR ESTABELECIMENTO | 8 | 9.42 | 0.85 | 0.37 | 1.67 | 0.00 |
| PRÉ | furto | OUTROS | 83 | 85.17 | 0.97 | 0.78 | 1.21 | 0.00 |
| PRÉ | furto | TRANSEUNTE | 45 | 19.83 | 2.27 | 1.65 | 3.04 | 0.30 |
| PRÉ | furto | VEICULO | 105 | 60.31 | 1.74 | 1.42 | 2.11 | 0.54 |
| PRÉ | roubo | (NULO) | 16 | 4.81 | 3.33 | 1.90 | 5.40 | 0.59 |
| PRÉ | roubo | DEMAIS (agrupadas) | 3 | 1.75 | 1.72 | 0.35 | 5.02 | 0.07 |
| PRÉ | roubo | ESTABELECIMENTO COMERCIAL | 4 | 3.90 | 1.03 | 0.28 | 2.63 | 0.01 |
| PRÉ | roubo | INTERIOR DE VEICULO | 3 | 6.64 | 0.45 | 0.09 | 1.32 | 0.00 |
| PRÉ | roubo | INTERIOR ESTABELECIMENTO | 1 | 1.41 | 0.71 | 0.02 | 3.95 | 0.00 |
| PRÉ | roubo | OUTROS | 181 | 174.56 | 1.04 | 0.89 | 1.20 | 0.34 |
| PRÉ | roubo | TRANSEUNTE | 33 | 38.23 | 0.86 | 0.59 | 1.21 | 0.00 |
| PRÉ | roubo | VEICULO | 25 | 26.90 | 0.93 | 0.60 | 1.37 | 0.00 |

**Leitura:**
- furto DURANTE+PÓS: maior parcela do excesso em `VEICULO` (48%; O/E 2.27).
- roubo DURANTE+PÓS: maior parcela do excesso em `OUTROS` (67%; O/E 1.25).
- furto PRÉ: maior parcela do excesso em `VEICULO` (54%; O/E 1.74).
- roubo PRÉ: maior parcela do excesso em `(NULO)` (59%; O/E 3.33).

### 2d. Leituras alternativas que não dá para testar com estes dados

- **Mais policiamento → mais registro.** Em dia de jogo há operação policial reforçada no entorno do estádio. Parte do aumento pode ser de registro (mais flagrantes, BOs feitos ali mesmo), não de ocorrência. Sem dado de efetivo/operação por hora, não é possível separar.
- **Mais gente → mais contagem, não necessariamente mais risco.** O entorno recebe dezenas de milhares de pessoas a mais nas janelas do jogo; a contagem sobe com a população presente mesmo que o risco por pessoa não mude. Kurland, Johnson e Tilley (2014), em Wembley, discutem exatamente essa diferença entre atração/geração de crime e o tamanho da população exposta — sem um denominador da população presente por hora, a taxa por pessoa não é estimável aqui.
- **Indício a favor da leitura do registro (item 2c):** nos BOs do entorno, os registros **sem `DESCR_CONDUTA`** sobem muito mais que os demais nas janelas DURANTE+PÓS (furto O/E 17.5, 25 vs 1.4 esperados; roubo O/E 3.8) — padrão compatível com BOs registrados na operação do próprio estádio, com preenchimento diferente. Não prova o canal, mas mostra que parte do excesso tem assinatura de registro, não só de ocorrência.
- As duas leituras não anulam o resultado (há mais ocorrências registradas no entorno durante e depois do jogo), mas impedem ler o IRR como aumento de risco individual.

## 3. Exploratórios (com p_BH; sem destaque no texto principal)

Horas tardias do event study (+4..+12 h) com p < 0,05 — BH na família do event study do domínio (todos os k × categorias × desfechos):

| desfecho | categoria | k | IRR | p | p_BH_familia_event_study |
|---|---|---|---|---|---|
| crimes_violentos | capital | 12.000 | 1.058 | 0.016 | 0.263 |
| crimes_violentos | fora_da_capital | 10.000 | 1.048 | 0.037 | 0.347 |
| lesao_corporal_dolosa | fora_da_capital | 8.000 | 1.134 | 0.019 | 0.263 |
| roubos_total | capital | 12.000 | 1.077 | 0.005 | 0.249 |
| roubos_total | fora_da_capital | 10.000 | 1.056 | 0.043 | 0.347 |
| furtos_total | capital | 10.000 | 1.045 | 0.043 | 0.347 |
