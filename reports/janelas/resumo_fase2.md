# V2 / Fase 2 — Resumo comparativo: crimes × sinistros

Cada domínio foi analisado em modelos, famílias de BH, definição de pico e conclusão próprios (`reports/janelas/crimes/relatorio_fase2_crimes.md`, `reports/janelas/sinistros/relatorio_fase2_sinistros.md`). Aqui só lado a lado, sem juntar.

## CRIMES — `crimes_violentos` (principal)

| janela | var_pct | IC95_lo | IC95_hi | p | p_BH_dominio | p_placebo | veredito |
|---|---|---|---|---|---|---|---|
| capital PRÉ | 4.722 | 1.016 | 1.079 | 0.003 | 0.041 | 0.000 | robusto no GLM, pareado inconclusivo |
| capital DURANTE | -2.060 | 0.949 | 1.010 | 0.191 | 0.412 | 0.428 | sem evidência |
| capital PÓS | 2.674 | 1.000 | 1.054 | 0.048 | 0.223 | 0.036 | sinal não robusto |
| fora da capital PRÉ | -1.503 | 0.958 | 1.012 | 0.278 | 0.519 | 0.192 | sem evidência |
| fora da capital DURANTE | -2.540 | 0.943 | 1.007 | 0.127 | 0.374 | 0.108 | sem evidência |
| fora da capital PÓS | -0.155 | 0.973 | 1.024 | 0.906 | 0.939 | 0.666 | sem evidência |

Todos os desfechos do domínio:

| desfecho | janela | var_pct | p | p_BH_dominio | p_placebo | veredito |
|---|---|---|---|---|---|---|
| crimes_violentos | capital PRÉ | 4.722 | 0.003 | 0.041 | 0.000 | robusto no GLM, pareado inconclusivo |
| crimes_violentos | capital DURANTE | -2.060 | 0.191 | 0.412 | 0.428 | sem evidência |
| crimes_violentos | capital PÓS | 2.674 | 0.048 | 0.223 | 0.036 | sinal não robusto |
| crimes_violentos | fora da capital PRÉ | -1.503 | 0.278 | 0.519 | 0.192 | sem evidência |
| crimes_violentos | fora da capital DURANTE | -2.540 | 0.127 | 0.374 | 0.108 | sem evidência |
| crimes_violentos | fora da capital PÓS | -0.155 | 0.906 | 0.939 | 0.666 | sem evidência |
| lesao_corporal_dolosa | capital PRÉ | 2.470 | 0.344 | 0.520 | 0.296 | sem evidência |
| lesao_corporal_dolosa | capital DURANTE | -3.088 | 0.260 | 0.519 | 0.524 | sem evidência |
| lesao_corporal_dolosa | capital PÓS | 3.449 | 0.159 | 0.404 | 0.596 | sem evidência |
| lesao_corporal_dolosa | fora da capital PRÉ | -3.924 | 0.181 | 0.412 | 0.326 | sem evidência |
| lesao_corporal_dolosa | fora da capital DURANTE | -2.329 | 0.396 | 0.528 | 0.592 | sem evidência |
| lesao_corporal_dolosa | fora da capital PÓS | -1.834 | 0.469 | 0.571 | 0.562 | sem evidência |
| roubos_total | capital PRÉ | 5.282 | 0.003 | 0.041 | 0.000 | robusto no GLM, pareado inconclusivo |
| roubos_total | capital DURANTE | -1.752 | 0.307 | 0.520 | 0.614 | sem evidência |
| roubos_total | capital PÓS | 2.556 | 0.090 | 0.359 | 0.050 | sem evidência |
| roubos_total | fora da capital PRÉ | -1.064 | 0.520 | 0.606 | 0.228 | sem evidência |
| roubos_total | fora da capital DURANTE | -2.803 | 0.124 | 0.374 | 0.058 | sem evidência |
| roubos_total | fora da capital PÓS | 0.008 | 0.996 | 0.996 | 0.660 | sem evidência |
| furtos_total | capital PRÉ | 4.149 | 0.021 | 0.147 | 0.006 | sinal não robusto |
| furtos_total | capital DURANTE | 1.443 | 0.389 | 0.528 | 0.150 | sem evidência |
| furtos_total | capital PÓS | 4.112 | 0.035 | 0.195 | 0.012 | sinal não robusto |
| furtos_total | fora da capital PRÉ | 2.375 | 0.134 | 0.374 | 0.278 | sem evidência |
| furtos_total | fora da capital DURANTE | 1.098 | 0.543 | 0.609 | 0.024 | sem evidência |
| furtos_total | fora da capital PÓS | 0.413 | 0.830 | 0.894 | 0.580 | sem evidência |

## SINISTROS — `acidentes_com_vitima` (principal)

| janela | var_pct | IC95_lo | IC95_hi | p | p_BH_dominio | p_placebo | veredito |
|---|---|---|---|---|---|---|---|
| capital PRÉ | 1.482 | 0.963 | 1.070 | 0.585 | 0.723 | 0.436 | sem evidência |
| capital DURANTE | 2.913 | 0.966 | 1.097 | 0.376 | 0.692 | 0.272 | sem evidência |
| capital PÓS | 3.882 | 0.981 | 1.100 | 0.192 | 0.692 | 0.024 | sem evidência |
| fora da capital PRÉ | 2.634 | 0.973 | 1.083 | 0.343 | 0.692 | 0.042 | sem evidência |
| fora da capital DURANTE | 0.644 | 0.951 | 1.065 | 0.823 | 0.910 | 0.240 | sem evidência |
| fora da capital PÓS | 4.326 | 0.987 | 1.103 | 0.134 | 0.692 | 0.002 | sem evidência |

Todos os desfechos do domínio:

| desfecho | janela | var_pct | p | p_BH_dominio | p_placebo | veredito |
|---|---|---|---|---|---|---|
| acidentes_com_vitima | capital PRÉ | 1.482 | 0.585 | 0.723 | 0.436 | sem evidência |
| acidentes_com_vitima | capital DURANTE | 2.913 | 0.376 | 0.692 | 0.272 | sem evidência |
| acidentes_com_vitima | capital PÓS | 3.882 | 0.192 | 0.692 | 0.024 | sem evidência |
| acidentes_com_vitima | fora da capital PRÉ | 2.634 | 0.343 | 0.692 | 0.042 | sem evidência |
| acidentes_com_vitima | fora da capital DURANTE | 0.644 | 0.823 | 0.910 | 0.240 | sem evidência |
| acidentes_com_vitima | fora da capital PÓS | 4.326 | 0.134 | 0.692 | 0.002 | sem evidência |
| acidentes_total | capital PRÉ | 3.986 | 0.115 | 0.692 | 0.028 | sem evidência |
| acidentes_total | capital DURANTE | 2.561 | 0.409 | 0.692 | 0.176 | sem evidência |
| acidentes_total | capital PÓS | 2.845 | 0.331 | 0.692 | 0.086 | sem evidência |
| acidentes_total | fora da capital PRÉ | -0.055 | 0.983 | 0.986 | 0.476 | sem evidência |
| acidentes_total | fora da capital DURANTE | 1.864 | 0.494 | 0.692 | 0.214 | sem evidência |
| acidentes_total | fora da capital PÓS | 0.046 | 0.986 | 0.986 | 0.404 | sem evidência |
| atropelamentos | capital PRÉ | 4.354 | 0.442 | 0.692 | 0.232 | sem evidência |
| atropelamentos | capital DURANTE | -6.998 | 0.277 | 0.692 | 0.202 | sem evidência |
| atropelamentos | capital PÓS | 8.370 | 0.260 | 0.692 | 0.194 | sem evidência |
| atropelamentos | fora da capital PRÉ | -3.396 | 0.562 | 0.723 | 0.920 | sem evidência |
| atropelamentos | fora da capital DURANTE | -5.307 | 0.383 | 0.692 | 0.450 | sem evidência |
| atropelamentos | fora da capital PÓS | 9.599 | 0.229 | 0.692 | 0.598 | sem evidência |

---

# CRIMES: resposta direta e ressalvas

### Resposta direta

- **Jogos na capital (multidão perto do estádio)**, `crimes_violentos`: PRÉ +4.7% (p=0.003, p_BH=0.041, placebo p=0.000) → **robusto no GLM, pareado inconclusivo**; DURANTE -2.1% (p=0.191, p_BH=0.412, placebo p=0.428) → **sem evidência**; PÓS +2.7% (p=0.048, p_BH=0.223, placebo p=0.036) → **sinal não robusto**.
- **Jogos fora da capital (TV / bares)**, `crimes_violentos`: PRÉ -1.5% (p=0.278, p_BH=0.519, placebo p=0.192) → **sem evidência**; DURANTE -2.5% (p=0.127, p_BH=0.374, placebo p=0.108) → **sem evidência**; PÓS -0.2% (p=0.906, p_BH=0.939, placebo p=0.666) → **sem evidência**.
- Desfechos secundários com algum sinal: `roubos_total` capital PRÉ +5.3% (robusto no GLM, pareado inconclusivo, p_BH=0.041); `furtos_total` capital PRÉ +4.1% (sinal não robusto, p_BH=0.147); `furtos_total` capital PÓS +4.1% (sinal não robusto, p_BH=0.195).
- **Onde:** entorno de 3 km dos estádios (3 estádios agregados): durante +15.0% (p=0.035, p_BH=0.055); pos +31.0% (p=0.000, p_BH=0.000); pre +5.3% (p=0.439, p_BH=0.479); resto da cidade: pre +4.9% (p=0.002); durante -2.5% (p=0.115); pos +1.6% (p=0.227).
- **Picos (nível hora, P90 Pearson):** capital pre RR 1.31 (Fisher p=0.041); capital durante RR 1.15 (Fisher p=0.325); capital pos RR 1.20 (Fisher p=0.190); fora da capital pre RR 0.87 (Fisher p=0.421); fora da capital durante RR 0.99 (Fisher p=1.000); fora da capital pos RR 1.02 (Fisher p=0.874).
- Exploratório — horas tardias do event study (+4..+12 h) com p < 0,05: capital k=+12 IRR 1.058 (p=0.016, p_BH=0.263); fora da capital k=+10 IRR 1.048 (p=0.037, p_BH=0.347).
- **Controles pareados (DiD):** capital pre +1.2% (IC95 -3.1 a +5.0); capital durante -6.8% (IC95 -10.4 a -2.7); capital pos +1.2% (IC95 -3.1 a +5.5); fora da capital pre -3.6% (IC95 -7.4 a +0.2); fora da capital durante -0.7% (IC95 -4.2 a +3.0); fora da capital pos -2.4% (IC95 -6.6 a +1.6).

Regra do veredito (revista na Fase 2b): candidato = p_BH < 0,05 no modelo principal **e** placebo p < 0,05 **e** mesmo sinal com p < 0,10 na Binomial Negativa e no cluster por dia. Entre os candidatos: **efeito robusto** só se o desenho pareado **confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, pareado inconclusivo** se o pareado não confirma mas também não contradiz (IC95 do pareado contém a estimativa do GLM); **contradito pelo pareado** se o IC95 do pareado exclui a estimativa do GLM. **Sinal não robusto** = p < 0,05 sem ser candidato; **sem evidência** = p ≥ 0,05. Associação, não causalidade.

### Ressalvas que pesam na leitura

- **Pré-tendência (event study):** teste conjunto k=−6..−3 p=0.007 (capital) e p=0.084 (fora). Coeficientes da capital em −6..−3: k=-6 0.977, k=-5 0.949, k=-4 0.982, k=-3 1.039. Rejeição com sinais mistos: parte vem de uma hora isolada abaixo e de k=−3 já acima de 1 (subida começando ~3 h antes do jogo). Não é a pré-tendência monotônica que invalidaria o desenho, mas reduz a confiança de que o PRÉ seja só efeito do jogo.
- **Controles pareados vs GLM:** no desenho pareado (só jogos com ≥2 dias-controle livres; n=112) o PRÉ da capital dá +1.2% (IC95 -3.1 a +5.0). Não confirma o GLM (+4.7%, p_BH=0.041): o efeito PRÉ depende do estimador/amostra.
  - DURANTE no pareado: -6.8% (IC95 -10.4 a -2.7) — queda durante o jogo, como em Ivandić et al. (2024); no GLM a queda é menor e não significativa.
- **Placebo:** maior desvio do centro da distribuição placebo em relação a 0: capital 0.7%, fora_da_capital 1.3%. Distribuição centrada; placebo confiável.
- **Heterogeneidade com n pequeno** (< 20 horas, erro-padrão agrupado degenerado, **não interpretar**): fora_da_capital classico=True pre (16 h); fora_da_capital comp4=Outros pre (2 h); fora_da_capital comp4=Outros durante (2 h); fora_da_capital comp4=Outros pos (2 h).
- **Morumbi sem a semifinal e a final da Copa do Brasil 2023** (os 2 jogos que explicavam o sinal diário da Etapa 10), disco de 3 km: pre 1.26→1.24 (p=0.127); durante 1.58→1.54 (p=0.003); pos 1.64→1.41 (p=0.021). Tabela em `crimes/tabelas/espaco_sensibilidade_sem_2_jogos_copa_do_brasil.csv`.
- Contagens só com registros que têm hora (furtos: ~53% sem hora). Associação, não causalidade: não há variação exógena da agenda; o desenho controla calendário, clima e hora × dia da semana.


---

# SINISTROS: resposta direta e ressalvas

### Resposta direta

- **Jogos na capital (multidão perto do estádio)**, `acidentes_com_vitima`: PRÉ +1.5% (p=0.585, p_BH=0.723, placebo p=0.436) → **sem evidência**; DURANTE +2.9% (p=0.376, p_BH=0.692, placebo p=0.272) → **sem evidência**; PÓS +3.9% (p=0.192, p_BH=0.692, placebo p=0.024) → **sem evidência**.
- **Jogos fora da capital (TV / bares)**, `acidentes_com_vitima`: PRÉ +2.6% (p=0.343, p_BH=0.692, placebo p=0.042) → **sem evidência**; DURANTE +0.6% (p=0.823, p_BH=0.910, placebo p=0.240) → **sem evidência**; PÓS +4.3% (p=0.134, p_BH=0.692, placebo p=0.002) → **sem evidência**.
- Desfechos secundários: sem sinal (p ≥ 0,05 em todas as janelas).
- **Onde (exploratório):** entorno de 3 km dos estádios (3 estádios agregados): durante +17.9% (p=0.232, p_BH=0.418); pos +5.5% (p=0.730, p_BH=0.777); pre +46.3% (p=0.001, p_BH=0.004); resto da cidade: pre -0.2% (p=0.939); durante +2.7% (p=0.429); pos +4.4% (p=0.166).
- **Picos (nível hora, P90 Pearson):** capital pre RR 0.98 (Fisher p=1.000); capital durante RR 1.06 (Fisher p=0.682); capital pos RR 1.22 (Fisher p=0.141); fora da capital pre RR 1.12 (Fisher p=0.378); fora da capital durante RR 0.99 (Fisher p=1.000); fora da capital pos RR 1.13 (Fisher p=0.344).
- Exploratório — horas tardias do event study (+4..+12 h) com p < 0,05: fora da capital k=+11 IRR 1.082 (p=0.034, p_BH=0.692).
- **Controles pareados (DiD):** capital pre +2.3% (IC95 -4.8 a +10.6); capital durante +4.2% (IC95 -3.0 a +12.9); capital pos -2.4% (IC95 -12.4 a +6.7); fora da capital pre +4.6% (IC95 -3.1 a +11.7); fora da capital durante +2.8% (IC95 -5.4 a +10.5); fora da capital pos +5.7% (IC95 -3.0 a +15.1).

Regra do veredito (revista na Fase 2b): candidato = p_BH < 0,05 no modelo principal **e** placebo p < 0,05 **e** mesmo sinal com p < 0,10 na Binomial Negativa e no cluster por dia. Entre os candidatos: **efeito robusto** só se o desenho pareado **confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, pareado inconclusivo** se o pareado não confirma mas também não contradiz (IC95 do pareado contém a estimativa do GLM); **contradito pelo pareado** se o IC95 do pareado exclui a estimativa do GLM. **Sinal não robusto** = p < 0,05 sem ser candidato; **sem evidência** = p ≥ 0,05. Associação, não causalidade.

### Ressalvas que pesam na leitura

- **Pré-tendência (event study):** teste conjunto k=−6..−3 p=0.890 (capital) e p=0.210 (fora). Coeficientes da capital em −6..−3: k=-6 0.975, k=-5 0.985, k=-4 0.972, k=-3 1.014. Sem pré-tendência detectável.
- **Controles pareados vs GLM:** no desenho pareado (só jogos com ≥2 dias-controle livres; n=112) o PRÉ da capital dá +2.3% (IC95 -4.8 a +10.6). Consistente com o GLM, que também não acha efeito no PRÉ (+1.5%, p_BH=0.723).
- **Placebo:** maior desvio do centro da distribuição placebo em relação a 0: capital 1.1%, fora_da_capital 6.4%. Ainda há descentramento relevante em horas tardias — o p do placebo, sozinho, não é confiável aqui; vale o GLM.
- **Heterogeneidade com n pequeno** (< 20 horas, erro-padrão agrupado degenerado, **não interpretar**): fora_da_capital classico=True pre (16 h); fora_da_capital comp4=Outros pre (2 h); fora_da_capital comp4=Outros durante (2 h); fora_da_capital comp4=Outros pos (2 h).
- **Morumbi sem a semifinal e a final da Copa do Brasil 2023** (os 2 jogos que explicavam o sinal diário da Etapa 10), disco de 3 km: pre 1.27→1.31 (p=0.211); durante 1.09→1.07 (p=0.775); pos 1.08→1.05 (p=0.856). Tabela em `crimes/tabelas/espaco_sensibilidade_sem_2_jogos_copa_do_brasil.csv`.
- Contagens só com registros que têm hora (furtos: ~53% sem hora). Associação, não causalidade: não há variação exógena da agenda; o desenho controla calendário, clima e hora × dia da semana.



