# V2 / Fase 2b — SINISTROS: checagens de robustez

Gerado por `scripts/33b_robustez_janelas.py`. **O modelo principal da Fase 2 não muda**; aqui só se acrescentam robustezes. Domínio analisado isoladamente.

## 1. PRÉ da capital

### 1a/1b/1d. GLM com EF hora × mês, só com os jogos do pareado e PRÉ estendido

O pareado compara cada jogo com semanas próximas e por isso controla a mudança do perfil horário ao longo do ano (o pôr do sol muda mais de 1 h em SP; roubo é sensível à escuridão); o GLM principal só tinha hora × dia da semana + ano × mês. **1a** acrescenta EF hora do dia × mês (alternativa: × trimestre). **1b** reestima o GLM só com os 112 jogos que entraram no desenho pareado (as janelas e dias dos outros jogos da capital saem da amostra). **1d** PRÉ estendido = horas k = −3, −2, −1.

| desfecho | spec | janela | IRR | var_pct | IC95_lo | IC95_hi | p |
|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | principal | capital PRÉ | 1.015 | 1.482 | 0.963 | 1.070 | 0.585 |
| acidentes_com_vitima | + EF hora×mês | capital PRÉ | 1.011 | 1.069 | 0.959 | 1.066 | 0.693 |
| acidentes_com_vitima | + EF hora×trimestre | capital PRÉ | 1.013 | 1.302 | 0.962 | 1.067 | 0.626 |
| acidentes_com_vitima | PRÉ estendido (k=−3..−1) | capital PRÉ estendido (k=−3..−1) | 1.013 | 1.282 | 0.971 | 1.057 | 0.557 |
| acidentes_com_vitima | PRÉ estendido + EF hora×mês | capital PRÉ estendido (k=−3..−1) | 1.005 | 0.492 | 0.963 | 1.048 | 0.820 |
| acidentes_com_vitima | só jogos do pareado | capital PRÉ | 1.000 | 0.041 | 0.936 | 1.069 | 0.990 |
| acidentes_com_vitima | só jogos do pareado + EF hora×mês | capital PRÉ | 0.995 | -0.533 | 0.930 | 1.064 | 0.877 |

Todos os termos e desfechos, principal vs EF hora × mês / × trimestre:

| desfecho | termo | + EF hora×mês | + EF hora×trimestre | principal |
|---|---|---|---|---|
| acidentes_com_vitima | C_durante | 1.036 (p=0.264) | 1.032 (p=0.319) | 1.029 (p=0.376) |
| acidentes_com_vitima | C_fdj | 1.017 (p=0.220) | 1.016 (p=0.237) | 1.015 (p=0.276) |
| acidentes_com_vitima | C_pos | 1.039 (p=0.208) | 1.033 (p=0.270) | 1.039 (p=0.192) |
| acidentes_com_vitima | C_pre | 1.011 (p=0.693) | 1.013 (p=0.626) | 1.015 (p=0.585) |
| acidentes_com_vitima | F_durante | 1.002 (p=0.937) | 1.003 (p=0.914) | 1.006 (p=0.823) |
| acidentes_com_vitima | F_pos | 1.034 (p=0.268) | 1.036 (p=0.229) | 1.043 (p=0.134) |
| acidentes_com_vitima | F_pre | 1.021 (p=0.459) | 1.021 (p=0.453) | 1.026 (p=0.343) |
| acidentes_total | C_durante | 1.035 (p=0.253) | 1.030 (p=0.330) | 1.026 (p=0.409) |
| acidentes_total | C_fdj | 1.011 (p=0.422) | 1.010 (p=0.462) | 1.010 (p=0.484) |
| acidentes_total | C_pos | 1.027 (p=0.377) | 1.024 (p=0.412) | 1.028 (p=0.331) |
| acidentes_total | C_pre | 1.038 (p=0.129) | 1.039 (p=0.128) | 1.040 (p=0.115) |
| acidentes_total | F_durante | 1.019 (p=0.492) | 1.022 (p=0.431) | 1.019 (p=0.494) |
| acidentes_total | F_pos | 0.995 (p=0.849) | 1.000 (p=0.993) | 1.000 (p=0.986) |
| acidentes_total | F_pre | 0.999 (p=0.964) | 0.996 (p=0.873) | 0.999 (p=0.983) |
| atropelamentos | C_durante | 0.965 (p=0.592) | 0.952 (p=0.463) | 0.930 (p=0.277) |
| atropelamentos | C_fdj | 1.006 (p=0.846) | 1.006 (p=0.852) | 1.012 (p=0.696) |
| atropelamentos | C_pos | 1.103 (p=0.167) | 1.088 (p=0.231) | 1.084 (p=0.260) |
| atropelamentos | C_pre | 1.048 (p=0.390) | 1.051 (p=0.359) | 1.044 (p=0.442) |
| atropelamentos | F_durante | 0.977 (p=0.708) | 0.976 (p=0.691) | 0.947 (p=0.383) |
| atropelamentos | F_pos | 1.097 (p=0.231) | 1.108 (p=0.183) | 1.096 (p=0.229) |
| atropelamentos | F_pre | 0.970 (p=0.628) | 0.975 (p=0.674) | 0.966 (p=0.562) |

**Leitura:**
- `acidentes_com_vitima`: PRÉ +1.5% (p=0.585) no principal → +1.1% (p=0.693) com EF hora×mês e +1.3% (p=0.626) com hora×trimestre (72% do efeito original com hora×mês). Só os 112 jogos do pareado: +0.0% (p=0.990); + hora×mês: -0.5% (p=0.877). PRÉ estendido k=−3..−1: +1.3% (p=0.557); + hora×mês +0.5% (p=0.820).

### 1c. Dose-resposta do público com EF hora × mês (cidade toda)

| desfecho | spec | termo | IRR | IC95_lo | IC95_hi | p |
|---|---|---|---|---|---|---|
| acidentes_com_vitima | log | C_pre__x_logpub | 1.025 | 0.875 | 1.200 | 0.759 |
| acidentes_com_vitima | log | C_durante__x_logpub | 0.930 | 0.772 | 1.121 | 0.449 |
| acidentes_com_vitima | log | C_pos__x_logpub | 1.042 | 0.850 | 1.279 | 0.691 |
| acidentes_com_vitima | log | C_pre | 1.012 | 0.960 | 1.067 | 0.646 |
| acidentes_com_vitima | log | C_durante | 1.036 | 0.973 | 1.102 | 0.268 |
| acidentes_com_vitima | log | C_pos | 1.037 | 0.976 | 1.102 | 0.238 |
| acidentes_com_vitima | tercis | C_pre__T1 | 1.004 | 0.927 | 1.087 | 0.925 |
| acidentes_com_vitima | tercis | C_pre__T2 | 0.992 | 0.900 | 1.093 | 0.869 |
| acidentes_com_vitima | tercis | C_pre__T3 | 1.046 | 0.960 | 1.140 | 0.304 |
| acidentes_com_vitima | tercis | C_durante__T1 | 1.091 | 0.988 | 1.204 | 0.086 |
| acidentes_com_vitima | tercis | C_durante__T2 | 1.010 | 0.923 | 1.105 | 0.825 |
| acidentes_com_vitima | tercis | C_durante__T3 | 1.006 | 0.924 | 1.096 | 0.888 |
| acidentes_com_vitima | tercis | C_pos__T1 | 1.055 | 0.942 | 1.181 | 0.358 |
| acidentes_com_vitima | tercis | C_pos__T2 | 1.036 | 0.921 | 1.165 | 0.555 |
| acidentes_com_vitima | tercis | C_pos__T3 | 1.026 | 0.944 | 1.114 | 0.549 |

### 1e. Regra do veredito revista

Implementada em `33_analise_janelas.py` (vereditos da Fase 2 regenerados): entre os candidatos (p_BH < 0,05, placebo p < 0,05, NB e cluster por dia com o mesmo sinal), **efeito robusto** só se o pareado **confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, pareado inconclusivo** se o pareado não confirma mas não contradiz (IC95 do pareado contém a estimativa do GLM); **contradito pelo pareado** se o IC95 do pareado exclui a estimativa do GLM. Assim, nenhum efeito é chamado de robusto com o pareado contra.

_Nenhum termo com p < 0,05 no domínio._

## 2. Entorno dos estádios

### 2a. BH na família espacial

Família = estádios × janelas × desfechos × (disco) = 27 testes; os 3 estádios agregados formam uma família à parte.

| desfecho | area | janela | IRR | IC95_lo | IC95_hi | p | p_BH_agregados |
|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | disco | durante | 1.179 | 0.900 | 1.545 | 0.232 | 0.418 |
| acidentes_com_vitima | disco | pos | 1.055 | 0.777 | 1.433 | 0.730 | 0.777 |
| acidentes_com_vitima | disco | pre | 1.463 | 1.161 | 1.843 | 0.001 | 0.004 |
| acidentes_total | disco | durante | 1.051 | 0.830 | 1.332 | 0.678 | 0.777 |
| acidentes_total | disco | pos | 0.962 | 0.738 | 1.254 | 0.777 | 0.777 |
| acidentes_total | disco | pre | 1.382 | 1.144 | 1.669 | 0.001 | 0.004 |
| atropelamentos | disco | durante | 0.791 | 0.391 | 1.600 | 0.514 | 0.771 |
| atropelamentos | disco | pos | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| atropelamentos | disco | pre | 1.601 | 0.958 | 2.675 | 0.072 | 0.163 |

Termos por estádio que sobrevivem ao BH da família espacial:

| estadio | area | desfecho | janela | IRR | p | p_BH_familia_espacial |
|---|---|---|---|---|---|---|
| Morumbi | disco | atropelamentos | pos | 0.000 | 0.000 | 0.000 |

### 2b. Por estádio e tipo, com o resto da cidade na mesma janela

`IRR_resto` = resto da cidade (fora dos 3 discos) nas janelas **dos jogos daquele estádio**, mesmo modelo. Deslocamento = entorno sobe enquanto o resto da cidade fica igual ou cai.

| desfecho | estadio | janela | IRR_disco | p_disco | p_BH_familia_espacial_disco | IRR_resto | p_resto |
|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | Allianz Parque | pre | 1.383 | 0.124 | 0.559 | 0.981 | 0.667 |
| acidentes_com_vitima | Allianz Parque | durante | 1.053 | 0.844 | 0.977 | 1.061 | 0.194 |
| acidentes_com_vitima | Allianz Parque | pos | 1.019 | 0.941 | 0.977 | 1.056 | 0.334 |
| acidentes_com_vitima | Morumbi | pre | 1.269 | 0.282 | 0.761 | 0.923 | 0.095 |
| acidentes_com_vitima | Morumbi | durante | 1.094 | 0.697 | 0.977 | 0.957 | 0.380 |
| acidentes_com_vitima | Morumbi | pos | 1.077 | 0.764 | 0.977 | 1.033 | 0.530 |
| acidentes_com_vitima | Neo Quimica Arena | pre | 1.689 | 0.005 | 0.064 | 1.088 | 0.035 |
| acidentes_com_vitima | Neo Quimica Arena | durante | 1.379 | 0.157 | 0.605 | 1.065 | 0.193 |
| acidentes_com_vitima | Neo Quimica Arena | pos | 1.084 | 0.812 | 0.977 | 1.041 | 0.441 |
| acidentes_total | Allianz Parque | pre | 1.368 | 0.051 | 0.273 | 1.040 | 0.326 |
| acidentes_total | Allianz Parque | durante | 1.029 | 0.886 | 0.977 | 1.086 | 0.052 |
| acidentes_total | Allianz Parque | pos | 0.999 | 0.998 | 0.998 | 1.076 | 0.128 |
| acidentes_total | Morumbi | pre | 1.240 | 0.270 | 0.761 | 0.966 | 0.437 |
| acidentes_total | Morumbi | durante | 1.154 | 0.494 | 0.953 | 0.976 | 0.628 |
| acidentes_total | Morumbi | pos | 0.884 | 0.582 | 0.977 | 1.001 | 0.990 |
| acidentes_total | Neo Quimica Arena | pre | 1.491 | 0.009 | 0.084 | 1.091 | 0.033 |
| acidentes_total | Neo Quimica Arena | durante | 0.975 | 0.906 | 0.977 | 1.045 | 0.329 |
| acidentes_total | Neo Quimica Arena | pos | 1.026 | 0.923 | 0.977 | 1.029 | 0.571 |
| atropelamentos | Allianz Parque | pre | 0.939 | 0.904 | 0.977 | 1.012 | 0.894 |
| atropelamentos | Allianz Parque | durante | 0.654 | 0.454 | 0.953 | 1.004 | 0.971 |
| atropelamentos | Allianz Parque | pos | 0.772 | 0.708 | 0.977 | 1.197 | 0.084 |
| atropelamentos | Morumbi | pre | 1.572 | 0.399 | 0.953 | 0.942 | 0.515 |
| atropelamentos | Morumbi | durante | 0.478 | 0.466 | 0.953 | 0.899 | 0.275 |
| atropelamentos | Morumbi | pos | 0.000 | 0.000 | 0.000 | 1.003 | 0.980 |
| atropelamentos | Neo Quimica Arena | pre | 2.121 | 0.042 | 0.273 | 1.103 | 0.240 |
| atropelamentos | Neo Quimica Arena | durante | 1.064 | 0.906 | 0.977 | 0.983 | 0.860 |
| atropelamentos | Neo Quimica Arena | pos | 1.845 | 0.192 | 0.648 | 1.079 | 0.546 |

Na janela DURANTE, 3 de 9 combinações estádio × desfecho têm entorno acima de 1 e resto da cidade abaixo de 1 (padrão de deslocamento).

### 2d. Leituras alternativas que não dá para testar com estes dados

- **Mais policiamento → mais registro.** Em dia de jogo há operação policial reforçada no entorno do estádio. Parte do aumento pode ser de registro (mais flagrantes, BOs feitos ali mesmo), não de ocorrência. Sem dado de efetivo/operação por hora, não é possível separar.
- **Mais gente → mais contagem, não necessariamente mais risco.** O entorno recebe dezenas de milhares de pessoas a mais nas janelas do jogo; a contagem sobe com a população presente mesmo que o risco por pessoa não mude. Kurland, Johnson e Tilley (2014), em Wembley, discutem exatamente essa diferença entre atração/geração de crime e o tamanho da população exposta — sem um denominador da população presente por hora, a taxa por pessoa não é estimável aqui.
- As duas leituras não anulam o resultado (há mais ocorrências registradas no entorno durante e depois do jogo), mas impedem ler o IRR como aumento de risco individual.

## 3. Exploratórios (com p_BH; sem destaque no texto principal)

Horas tardias do event study (+4..+12 h) com p < 0,05 — BH na família do event study do domínio (todos os k × categorias × desfechos):

| desfecho | categoria | k | IRR | p | p_BH_familia_event_study |
|---|---|---|---|---|---|
| acidentes_com_vitima | fora_da_capital | 11.000 | 1.082 | 0.034 | 0.692 |
| acidentes_total | fora_da_capital | 11.000 | 1.109 | 0.005 | 0.257 |
| atropelamentos | capital | 7.000 | 1.350 | 0.032 | 0.692 |
| atropelamentos | fora_da_capital | 11.000 | 1.361 | 0.004 | 0.257 |

PRÉ no entorno dos estádios (agregado) — exploratório:

| desfecho | area | IRR | p | p_BH_agregados |
|---|---|---|---|---|
| acidentes_com_vitima | disco | 1.463 | 0.001 | 0.004 |
| acidentes_total | disco | 1.382 | 0.001 | 0.004 |
| atropelamentos | disco | 1.601 | 0.072 | 0.163 |
