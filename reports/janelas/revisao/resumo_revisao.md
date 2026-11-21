# V4 / Fase 1 — Revisão pelo parecer: resultados novos

Gerado por `scripts/36_revisao_parecer.py` (tabelas em `reports/janelas/revisao/{crimes,sinistros}/tabelas/`). Mudanças aplicadas em tudo: contagem de crime por BO único; horas PRÉ/DURANTE/PÓS dos 5 jogos do Brasil na Copa de 2022 fora da amostra; modelo principal da cidade com EF hora × mês; entorno como diferença em diferenças (GLM binomial da fração no disco contra o resto da cidade). Crimes e sinistros separados.

## Funil de registros (BO único; sinistro = registro do Infosiga)

| dominio | desfecho | registros_municipio | com_hora | pct_com_hora | com_hora_coord_valida | pct_coord_valida_entre_com_hora | com_hora_nos_discos_3km_bruto | pile_excluido | pct_pile_dos_discos | com_hora_nos_discos_3km |
|---|---|---|---|---|---|---|---|---|---|---|
| crimes | crime_todos | 971698 | 641697 | 66.0 | 536766 | 83.6 | 50739 | 668 | 1.3 | 50071 |
| crimes | crimes_violentos | 376633 | 344192 | 91.4 | 279533 | 81.2 | 24157 | 226 | 0.9 | 23931 |
| crimes | lesao_corporal_dolosa | 65413 | 59790 | 91.4 | 30108 | 50.4 | 2738 | 53 | 1.9 | 2685 |
| crimes | roubos_total | 305025 | 280197 | 91.9 | 248308 | 88.6 | 21363 | 170 | 0.8 | 21193 |
| crimes | furtos_total | 561908 | 265198 | 47.2 | 228049 | 86.0 | 24195 | 359 | 1.5 | 23836 |
| sinistros | acidentes_com_vitima | 58856 | 58764 | 99.8 | 58383 | 99.4 | 5619 | 0 | 0.0 | 5619 |
| sinistros | acidentes_total | 90829 | 90737 | 99.9 | 90311 | 99.5 | 8686 | 0 | 0.0 | 8686 |
| sinistros | atropelamentos | 12152 | 12114 | 99.7 | 12048 | 99.5 | 1029 | 0 | 0.0 | 1029 |

### BO × natureza → BO único (contagem horária da cidade)

| desfecho | linhas_BO_x_natureza | BO_unicos | excesso_pct | horas_com_diferenca | max_diferenca_hora |
|---|---|---|---|---|---|
| crimes_violentos | 344832 | 344192 | 0.19 | 624 | 3 |
| lesao_corporal_dolosa | 59795 | 59790 | 0.01 | 5 | 1 |
| roubos_total | 280201 | 280197 | 0.00 | 4 | 1 |
| furtos_total | 265199 | 265198 | 0.00 | 1 | 1 |

### Jogos do Brasil na Copa de 2022 excluídos

| jogo | inicio_br | horas_excluidas | fonte |
|---|---|---|---|
| Brasil x Sérvia | 2022-11-24 16:00 | 6 | Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); horario local AST (UTC+3) convertido para Brasilia (UTC-3) |
| Brasil x Suíça | 2022-11-28 13:00 | 6 | Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); horario local AST (UTC+3) convertido para Brasilia (UTC-3) |
| Camarões x Brasil | 2022-12-02 16:00 | 6 | Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); horario local AST (UTC+3) convertido para Brasilia (UTC-3) |
| Brasil x Coreia do Sul | 2022-12-05 16:00 | 6 | Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); horario local AST (UTC+3) convertido para Brasilia (UTC-3) |
| Croácia x Brasil | 2022-12-09 12:00 | 6 | Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); horario local AST (UTC+3) convertido para Brasilia (UTC-3) |

---

# CRIMES

## Cidade toda: modelo principal com EF hora × mês (Tabela 2 nova)

| desfecho | janela | var_pct | IC95_lo | IC95_hi | p | p_BH_dominio | p_placebo | robustez_NB_e_dia_ok | pareado_confirma | pareado_contradiz | veredito |
|---|---|---|---|---|---|---|---|---|---|---|---|
| crimes_violentos | capital PRÉ | 2.862 | 1.001 | 1.057 | 0.043 | 0.205 | 0.002 | True | False | False | sinal não robusto |
| crimes_violentos | capital DURANTE | -1.584 | 0.955 | 1.014 | 0.296 | 0.479 | 0.766 | False | True | True | sem evidência |
| crimes_violentos | capital PÓS | 2.666 | 1.000 | 1.054 | 0.051 | 0.205 | 0.044 | True | False | False | sem evidência |
| crimes_violentos | fora da capital PRÉ | -3.113 | 0.944 | 0.994 | 0.017 | 0.157 | 0.006 | True | False | False | sinal não robusto |
| crimes_violentos | fora da capital DURANTE | -2.171 | 0.948 | 1.010 | 0.171 | 0.399 | 0.076 | False | False | False | sem evidência |
| crimes_violentos | fora da capital PÓS | 0.182 | 0.976 | 1.028 | 0.890 | 0.890 | 0.750 | False | False | False | sem evidência |
| lesao_corporal_dolosa | capital PRÉ | 1.743 | 0.967 | 1.070 | 0.503 | 0.563 | 0.632 | False | False | False | sem evidência |
| lesao_corporal_dolosa | capital DURANTE | -2.615 | 0.922 | 1.028 | 0.340 | 0.500 | 0.788 | False | False | False | sem evidência |
| lesao_corporal_dolosa | capital PÓS | 3.308 | 0.984 | 1.085 | 0.193 | 0.415 | 0.580 | False | False | False | sem evidência |
| lesao_corporal_dolosa | fora da capital PRÉ | -3.944 | 0.907 | 1.017 | 0.171 | 0.399 | 0.314 | False | False | False | sem evidência |
| lesao_corporal_dolosa | fora da capital DURANTE | -2.370 | 0.924 | 1.032 | 0.394 | 0.552 | 0.702 | False | False | False | sem evidência |
| lesao_corporal_dolosa | fora da capital PÓS | -1.651 | 0.934 | 1.036 | 0.528 | 0.568 | 0.754 | False | True | False | sem evidência |
| roubos_total | capital PRÉ | 3.012 | 1.000 | 1.061 | 0.049 | 0.205 | 0.006 | True | False | False | sinal não robusto |
| roubos_total | capital DURANTE | -1.240 | 0.956 | 1.020 | 0.455 | 0.563 | 0.976 | False | True | True | sem evidência |
| roubos_total | capital PÓS | 2.626 | 0.997 | 1.056 | 0.078 | 0.244 | 0.072 | False | False | False | sem evidência |
| roubos_total | fora da capital PRÉ | -3.157 | 0.940 | 0.998 | 0.037 | 0.205 | 0.000 | True | False | False | sinal não robusto |
| roubos_total | fora da capital DURANTE | -2.344 | 0.944 | 1.010 | 0.171 | 0.399 | 0.048 | False | False | False | sem evidência |
| roubos_total | fora da capital PÓS | 0.401 | 0.974 | 1.034 | 0.793 | 0.822 | 0.804 | False | False | False | sem evidência |
| furtos_total | capital PRÉ | 3.145 | 0.998 | 1.066 | 0.066 | 0.231 | 0.042 | True | False | False | sem evidência |
| furtos_total | capital DURANTE | 1.947 | 0.988 | 1.052 | 0.225 | 0.420 | 0.040 | False | False | False | sem evidência |
| furtos_total | capital PÓS | 4.859 | 1.010 | 1.088 | 0.012 | 0.157 | 0.006 | True | False | False | sinal não robusto |
| furtos_total | fora da capital PRÉ | 1.109 | 0.981 | 1.042 | 0.476 | 0.563 | 0.868 | False | False | False | sem evidência |
| furtos_total | fora da capital DURANTE | 1.386 | 0.981 | 1.048 | 0.416 | 0.555 | 0.006 | False | False | False | sem evidência |
| furtos_total | fora da capital PÓS | 1.338 | 0.976 | 1.052 | 0.484 | 0.563 | 0.216 | False | False | False | sem evidência |

## Entorno (3 km), diferença em diferenças, 3 estádios empilhados

IRR = razão entre a variação no disco e a variação no resto da cidade. `p` = cluster por semana; `p_quase` = quase-binomial; `p_dia` = cluster por dia. `dp` = DURANTE+PÓS (janela única de 4 h).

| desfecho | janela | IRR | IC95_lo | IC95_hi | p | p_BH | p_quase | p_dia | p_placebo | pareado_confirma | pareado_contradiz | veredito |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crimes_violentos | pre | 0.994 | 0.866 | 1.140 | 0.929 | 0.947 | 0.927 | 0.926 | 0.980 | False | False | sem evidência |
| crimes_violentos | durante | 1.225 | 1.067 | 1.408 | 0.004 | 0.007 | 0.001 | 0.004 | 0.002 | False | False | robusto no GLM, pareado inconclusivo |
| crimes_violentos | pos | 1.357 | 1.168 | 1.575 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |
| lesao_corporal_dolosa | pre | 1.023 | 0.645 | 1.621 | 0.924 | 0.947 | 0.920 | 0.921 | 0.584 | False | False | sem evidência |
| lesao_corporal_dolosa | durante | 2.378 | 1.703 | 3.322 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | False | True | contradito pelo pareado |
| lesao_corporal_dolosa | pos | 0.713 | 0.459 | 1.107 | 0.131 | 0.171 | 0.150 | 0.160 | 0.142 | False | False | sem evidência |
| roubos_total | pre | 0.995 | 0.859 | 1.153 | 0.947 | 0.947 | 0.944 | 0.945 | 0.894 | False | False | sem evidência |
| roubos_total | durante | 1.147 | 0.988 | 1.331 | 0.072 | 0.105 | 0.036 | 0.065 | 0.024 | False | False | sem evidência |
| roubos_total | pos | 1.434 | 1.229 | 1.673 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |
| furtos_total | pre | 1.296 | 1.129 | 1.488 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |
| furtos_total | durante | 1.575 | 1.370 | 1.811 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |
| furtos_total | pos | 1.872 | 1.594 | 2.197 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |
| furtos_total | dp | 1.710 | 1.518 | 1.926 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True | False | efeito robusto |

Por estádio com p_BH < 0,05 (família por estádio):

| estadio | desfecho | janela | IRR | p | p_BH | veredito |
|---|---|---|---|---|---|---|
| Neo Quimica Arena | crimes_violentos | pos | 1.312 | 0.018 | 0.034 | robusto no GLM, pareado inconclusivo |
| Morumbi | crimes_violentos | durante | 1.646 | 0.000 | 0.001 | robusto no GLM, pareado inconclusivo |
| Morumbi | crimes_violentos | pos | 1.649 | 0.003 | 0.009 | efeito robusto |
| Neo Quimica Arena | lesao_corporal_dolosa | durante | 2.146 | 0.010 | 0.025 | robusto no GLM, pareado inconclusivo |
| Allianz Parque | lesao_corporal_dolosa | durante | 2.012 | 0.017 | 0.033 | robusto no GLM, pareado inconclusivo |
| Morumbi | lesao_corporal_dolosa | durante | 4.205 | 0.000 | 0.001 | contradito pelo pareado |
| Neo Quimica Arena | roubos_total | pos | 1.421 | 0.003 | 0.009 | efeito robusto |
| Allianz Parque | roubos_total | pos | 1.290 | 0.011 | 0.026 | robusto no GLM, pareado inconclusivo |
| Morumbi | roubos_total | durante | 1.553 | 0.003 | 0.008 | robusto no GLM, pareado inconclusivo |
| Morumbi | roubos_total | pos | 1.734 | 0.001 | 0.004 | efeito robusto |
| Neo Quimica Arena | furtos_total | pre | 1.472 | 0.015 | 0.032 | efeito robusto |
| Neo Quimica Arena | furtos_total | durante | 1.924 | 0.000 | 0.000 | efeito robusto |
| Neo Quimica Arena | furtos_total | pos | 2.057 | 0.000 | 0.000 | efeito robusto |
| Allianz Parque | furtos_total | durante | 1.281 | 0.017 | 0.033 | robusto no GLM, pareado inconclusivo |
| Allianz Parque | furtos_total | pos | 1.458 | 0.000 | 0.001 | efeito robusto |
| Morumbi | furtos_total | pre | 1.691 | 0.000 | 0.001 | robusto no GLM, pareado inconclusivo |
| Morumbi | furtos_total | durante | 1.995 | 0.000 | 0.000 | efeito robusto |
| Morumbi | furtos_total | pos | 2.928 | 0.000 | 0.000 | efeito robusto |
| Neo Quimica Arena | furtos_total | dp | 1.988 | 0.000 | 0.000 | efeito robusto |
| Allianz Parque | furtos_total | dp | 1.360 | 0.000 | 0.001 | efeito robusto |
| Morumbi | furtos_total | dp | 2.399 | 0.000 | 0.000 | efeito robusto |

Pareado do entorno (DiD da fração no disco; IC por bootstrap de jogos):

| estadio | janela | n_jogos | DiD_IRR | IC95_lo | IC95_hi | desfecho |
|---|---|---|---|---|---|---|
| Neo Quimica Arena | pre | 40 | 0.980 | 0.699 | 1.339 | crimes_violentos |
| Neo Quimica Arena | durante | 40 | 1.332 | 0.950 | 1.825 | crimes_violentos |
| Neo Quimica Arena | pos | 40 | 1.285 | 0.899 | 1.716 | crimes_violentos |
| Neo Quimica Arena | dp | 40 | 1.309 | 1.040 | 1.648 | crimes_violentos |
| Allianz Parque | pre | 33 | 0.873 | 0.640 | 1.260 | crimes_violentos |
| Allianz Parque | durante | 33 | 1.059 | 0.740 | 1.470 | crimes_violentos |
| Allianz Parque | pos | 33 | 1.020 | 0.755 | 1.349 | crimes_violentos |
| Allianz Parque | dp | 33 | 1.041 | 0.821 | 1.343 | crimes_violentos |
| Morumbi | pre | 38 | 1.127 | 0.716 | 1.749 | crimes_violentos |
| Morumbi | durante | 38 | 1.486 | 0.847 | 2.286 | crimes_violentos |
| Morumbi | pos | 38 | 1.679 | 1.093 | 2.507 | crimes_violentos |
| Morumbi | dp | 38 | 1.570 | 1.141 | 2.165 | crimes_violentos |
| 3 estádios (empilhado) | pre | 111 | 0.976 | 0.795 | 1.200 | crimes_violentos |
| 3 estádios (empilhado) | durante | 111 | 1.248 | 0.977 | 1.539 | crimes_violentos |
| 3 estádios (empilhado) | pos | 111 | 1.259 | 1.033 | 1.512 | crimes_violentos |
| 3 estádios (empilhado) | dp | 111 | 1.253 | 1.069 | 1.437 | crimes_violentos |
| Neo Quimica Arena | pre | 40 | 1.793 | 0.631 | 4.942 | lesao_corporal_dolosa |
| Neo Quimica Arena | durante | 40 | 1.194 | 0.366 | 2.984 | lesao_corporal_dolosa |
| Neo Quimica Arena | pos | 40 | 0.501 | 0.121 | 1.151 | lesao_corporal_dolosa |
| Neo Quimica Arena | dp | 40 | 0.816 | 0.370 | 1.775 | lesao_corporal_dolosa |
| Allianz Parque | pre | 33 | 0.809 | 0.188 | 1.918 | lesao_corporal_dolosa |
| Allianz Parque | durante | 33 | 2.039 | 0.429 | 5.980 | lesao_corporal_dolosa |
| Allianz Parque | pos | 33 | 0.763 | 0.202 | 2.359 | lesao_corporal_dolosa |
| Allianz Parque | dp | 33 | 1.351 | 0.396 | 3.133 | lesao_corporal_dolosa |
| Morumbi | pre | 38 | 1.058 | 0.251 | 5.211 | lesao_corporal_dolosa |
| Morumbi | durante | 38 | 0.785 | 0.163 | 2.296 | lesao_corporal_dolosa |
| Morumbi | pos | 38 | 1.050 | 0.223 | 10.849 | lesao_corporal_dolosa |
| Morumbi | dp | 38 | 0.862 | 0.267 | 2.760 | lesao_corporal_dolosa |
| 3 estádios (empilhado) | pre | 111 | 1.188 | 0.609 | 2.213 | lesao_corporal_dolosa |
| 3 estádios (empilhado) | durante | 111 | 1.243 | 0.673 | 2.224 | lesao_corporal_dolosa |
| 3 estádios (empilhado) | pos | 111 | 0.625 | 0.245 | 1.221 | lesao_corporal_dolosa |
| 3 estádios (empilhado) | dp | 111 | 0.950 | 0.567 | 1.518 | lesao_corporal_dolosa |
| Neo Quimica Arena | pre | 40 | 0.957 | 0.636 | 1.412 | roubos_total |
| Neo Quimica Arena | durante | 40 | 1.385 | 0.999 | 1.875 | roubos_total |
| Neo Quimica Arena | pos | 40 | 1.488 | 1.077 | 2.025 | roubos_total |
| Neo Quimica Arena | dp | 40 | 1.431 | 1.135 | 1.802 | roubos_total |
| Allianz Parque | pre | 33 | 0.865 | 0.615 | 1.248 | roubos_total |
| Allianz Parque | durante | 33 | 0.998 | 0.683 | 1.383 | roubos_total |
| Allianz Parque | pos | 33 | 1.025 | 0.760 | 1.367 | roubos_total |
| Allianz Parque | dp | 33 | 1.012 | 0.793 | 1.286 | roubos_total |
| Morumbi | pre | 38 | 1.168 | 0.696 | 1.830 | roubos_total |
| Morumbi | durante | 38 | 1.581 | 0.884 | 2.578 | roubos_total |
| Morumbi | pos | 38 | 1.758 | 1.126 | 2.630 | roubos_total |
| Morumbi | dp | 38 | 1.661 | 1.205 | 2.287 | roubos_total |
| 3 estádios (empilhado) | pre | 111 | 0.978 | 0.789 | 1.231 | roubos_total |
| 3 estádios (empilhado) | durante | 111 | 1.256 | 0.992 | 1.554 | roubos_total |
| 3 estádios (empilhado) | pos | 111 | 1.346 | 1.092 | 1.657 | roubos_total |
| 3 estádios (empilhado) | dp | 111 | 1.297 | 1.101 | 1.516 | roubos_total |
| Neo Quimica Arena | pre | 40 | 1.654 | 1.055 | 2.348 | furtos_total |
| Neo Quimica Arena | durante | 40 | 1.738 | 1.228 | 2.476 | furtos_total |
| Neo Quimica Arena | pos | 40 | 2.046 | 1.294 | 3.104 | furtos_total |
| Neo Quimica Arena | dp | 40 | 1.880 | 1.298 | 2.599 | furtos_total |
| Allianz Parque | pre | 33 | 1.099 | 0.803 | 1.487 | furtos_total |
| Allianz Parque | durante | 33 | 1.239 | 0.911 | 1.623 | furtos_total |
| Allianz Parque | pos | 33 | 1.917 | 1.344 | 2.636 | furtos_total |
| Allianz Parque | dp | 33 | 1.488 | 1.161 | 1.849 | furtos_total |
| Morumbi | pre | 38 | 1.472 | 0.955 | 2.334 | furtos_total |
| Morumbi | durante | 38 | 1.590 | 1.028 | 2.472 | furtos_total |
| Morumbi | pos | 38 | 2.303 | 1.025 | 4.262 | furtos_total |
| Morumbi | dp | 38 | 1.863 | 1.130 | 2.861 | furtos_total |
| 3 estádios (empilhado) | pre | 111 | 1.352 | 1.078 | 1.650 | furtos_total |
| 3 estádios (empilhado) | durante | 111 | 1.447 | 1.166 | 1.790 | furtos_total |
| 3 estádios (empilhado) | pos | 111 | 2.082 | 1.585 | 2.702 | furtos_total |
| 3 estádios (empilhado) | dp | 111 | 1.701 | 1.402 | 2.032 | furtos_total |

Raio (só modelo principal, empilhado):

| desfecho | janela | 1.0 | 2.0 | 3.0 | 5.0 |
|---|---|---|---|---|---|
| crimes_violentos | durante | 1.34 (p=0.087) | 1.19 (p=0.087) | 1.23 (p=0.004) | 1.05 (p=0.182) |
| crimes_violentos | pos | 3.00 (p=0.000) | 1.57 (p=0.000) | 1.36 (p=0.000) | 1.14 (p=0.007) |
| crimes_violentos | pre | 1.94 (p=0.000) | 1.09 (p=0.375) | 0.99 (p=0.929) | 0.97 (p=0.558) |
| furtos_total | dp | 4.58 (p=0.000) | 2.47 (p=0.000) | 1.71 (p=0.000) | 1.23 (p=0.000) |
| furtos_total | durante | 4.25 (p=0.000) | 2.30 (p=0.000) | 1.58 (p=0.000) | 1.21 (p=0.000) |
| furtos_total | pos | 4.95 (p=0.000) | 2.67 (p=0.000) | 1.87 (p=0.000) | 1.25 (p=0.000) |
| furtos_total | pre | 2.93 (p=0.000) | 1.73 (p=0.000) | 1.30 (p=0.000) | 1.06 (p=0.219) |
| lesao_corporal_dolosa | durante | 3.29 (p=0.010) | 2.78 (p=0.000) | 2.38 (p=0.000) | 1.45 (p=0.001) |
| lesao_corporal_dolosa | pos | 0.95 (p=0.934) | 0.67 (p=0.226) | 0.71 (p=0.131) | 0.74 (p=0.052) |
| lesao_corporal_dolosa | pre | 2.55 (p=0.144) | 1.17 (p=0.604) | 1.02 (p=0.924) | 0.94 (p=0.683) |
| roubos_total | durante | 1.19 (p=0.366) | 1.09 (p=0.438) | 1.15 (p=0.072) | 1.03 (p=0.516) |
| roubos_total | pos | 3.21 (p=0.000) | 1.68 (p=0.000) | 1.43 (p=0.000) | 1.18 (p=0.002) |
| roubos_total | pre | 1.94 (p=0.000) | 1.10 (p=0.359) | 1.00 (p=0.947) | 0.98 (p=0.619) |

## Canal do BO (Tabela 4 nova; * = p_BH < 0,05 dentro da versão)

| desfecho | janela | sem conduta nula | só BO online | só presencial | todos |
|---|---|---|---|---|---|
| crimes_violentos | durante | +14% | +22%* | +24% | +23%* |
| crimes_violentos | pos | +44%* | +53%* | -2% | +36%* |
| crimes_violentos | pre | -2% | +4% | -13% | -1% |
| furtos_total | dp | +67%* | +73%* | +64%* | +71%* |
| furtos_total | durante | +52%* | +67%* | +37%* | +58%* |
| furtos_total | pos | +85%* | +81%* | +97%* | +87%* |
| furtos_total | pre | +30%* | +25%* | +38%* | +30%* |
| roubos_total | durante | +14% | +16% | +10% | +15% |
| roubos_total | pos | +44%* | +56%* | +7% | +43%* |
| roubos_total | pre | -2% | +5% | -18% | -0% |

## Furtos no entorno por subtipo

| desfecho | janela | IRR | IC95_lo | IC95_hi | p | p_BH_subtipos | n_com_hora_todo_municipio |
|---|---|---|---|---|---|---|---|
| furto_veiculo | pre | 1.584 | 1.215 | 2.064 | 0.001 | 0.001 | 75125 |
| furto_veiculo | durante | 2.065 | 1.658 | 2.573 | 0.000 | 0.000 | 75125 |
| furto_veiculo | pos | 2.482 | 1.977 | 3.117 | 0.000 | 0.000 | 75125 |
| furto_veiculo | dp | 2.241 | 1.871 | 2.685 | 0.000 | 0.000 | 75125 |
| furto_transeunte | pre | 2.043 | 1.365 | 3.058 | 0.001 | 0.001 | 22736 |
| furto_transeunte | durante | 1.678 | 1.026 | 2.744 | 0.039 | 0.043 | 22736 |
| furto_transeunte | pos | 2.587 | 1.777 | 3.766 | 0.000 | 0.000 | 22736 |
| furto_transeunte | dp | 2.120 | 1.483 | 3.029 | 0.000 | 0.000 | 22736 |
| furto_outros | pre | 1.039 | 0.868 | 1.242 | 0.679 | 0.679 | 167338 |
| furto_outros | durante | 1.297 | 1.075 | 1.564 | 0.007 | 0.008 | 167338 |
| furto_outros | pos | 1.389 | 1.097 | 1.758 | 0.006 | 0.008 | 167338 |
| furto_outros | dp | 1.339 | 1.131 | 1.586 | 0.001 | 0.001 | 167338 |

## Furtos sem hora

| spec | OR_ou_RR_dia_jogo | IC95_lo | IC95_hi | p | excesso_total_dias_de_jogo | n_dias_jogo | excesso_por_jogo | fator_empirico_todos_sobre_com_hora | fator_suposto_2_12 |
|---|---|---|---|---|---|---|---|---|---|
| (a) fração sem hora no disco | 1.325 | 1.129 | 1.557 | 0.001 | 410.432 | 213 | 1.927 | 4.993 | 2.119 |
| (b) disco vs resto, todos os furtos (com e sem hora) | 1.352 | 1.158 | 1.579 | 0.000 | 1521.020 | 214 | 7.108 | 4.993 | 2.119 |
| (b') disco vs resto, só furtos com hora | 1.147 | 1.086 | 1.211 | 0.000 | 304.628 | 214 | 1.423 | 4.993 | 2.119 |
| (c) janelas PRÉ+DURANTE+PÓS, modelo horário (só com hora) |  |  |  |  | 301.796 | 215 | 1.404 | 4.993 | 2.119 |

## Tabela 7 nova (quarta 21h30)

| desfecho | estadio | janela | esperado_sem_jogo | IRR | excesso | excesso_IC95_lo | excesso_IC95_hi | p |
|---|---|---|---|---|---|---|---|---|
| crimes_violentos | Neo Quimica Arena | pre | 1.43 | 0.89 | -0.16 | -0.46 | 0.23 | 0.38 |
| crimes_violentos | Neo Quimica Arena | durante | 1.76 | 1.14 | 0.25 | -0.15 | 0.74 | 0.24 |
| crimes_violentos | Neo Quimica Arena | pos | 0.80 | 1.31 | 0.25 | 0.04 | 0.52 | 0.02 |
| crimes_violentos | Allianz Parque | pre | 2.90 | 0.99 | -0.04 | -0.51 | 0.52 | 0.89 |
| crimes_violentos | Allianz Parque | durante | 1.94 | 1.07 | 0.13 | -0.28 | 0.65 | 0.56 |
| crimes_violentos | Allianz Parque | pos | 1.21 | 1.24 | 0.29 | 0.03 | 0.61 | 0.03 |
| crimes_violentos | Morumbi | pre | 1.72 | 1.15 | 0.25 | -0.21 | 0.86 | 0.31 |
| crimes_violentos | Morumbi | durante | 1.15 | 1.65 | 0.74 | 0.29 | 1.33 | 0.00 |
| crimes_violentos | Morumbi | pos | 0.65 | 1.65 | 0.42 | 0.12 | 0.85 | 0.00 |
| roubos_total | Neo Quimica Arena | pre | 1.31 | 0.89 | -0.14 | -0.43 | 0.25 | 0.44 |
| roubos_total | Neo Quimica Arena | durante | 1.58 | 1.04 | 0.06 | -0.30 | 0.52 | 0.77 |
| roubos_total | Neo Quimica Arena | pos | 0.59 | 1.42 | 0.25 | 0.07 | 0.47 | 0.00 |
| roubos_total | Allianz Parque | pre | 2.79 | 0.99 | -0.02 | -0.48 | 0.54 | 0.94 |
| roubos_total | Allianz Parque | durante | 1.85 | 1.01 | 0.01 | -0.36 | 0.49 | 0.94 |
| roubos_total | Allianz Parque | pos | 1.21 | 1.29 | 0.35 | 0.07 | 0.69 | 0.01 |
| roubos_total | Morumbi | pre | 1.66 | 1.12 | 0.21 | -0.24 | 0.80 | 0.41 |
| roubos_total | Morumbi | durante | 1.06 | 1.55 | 0.59 | 0.18 | 1.13 | 0.00 |
| roubos_total | Morumbi | pos | 0.62 | 1.73 | 0.45 | 0.15 | 0.88 | 0.00 |
| furtos_total | Neo Quimica Arena | pre | 0.78 | 1.47 | 0.37 | 0.06 | 0.79 | 0.01 |
| furtos_total | Neo Quimica Arena | durante | 0.70 | 1.92 | 0.64 | 0.38 | 0.97 | 0.00 |
| furtos_total | Neo Quimica Arena | pos | 0.65 | 2.06 | 0.69 | 0.39 | 1.09 | 0.00 |
| furtos_total | Neo Quimica Arena | dp | 1.35 | 1.99 | 1.34 | 0.87 | 1.90 | 0.00 |
| furtos_total | Allianz Parque | pre | 2.59 | 1.07 | 0.19 | -0.30 | 0.79 | 0.47 |
| furtos_total | Allianz Parque | durante | 1.85 | 1.28 | 0.52 | 0.09 | 1.05 | 0.02 |
| furtos_total | Allianz Parque | pos | 0.88 | 1.46 | 0.40 | 0.16 | 0.70 | 0.00 |
| furtos_total | Allianz Parque | dp | 2.72 | 1.36 | 0.98 | 0.44 | 1.61 | 0.00 |
| furtos_total | Morumbi | pre | 0.63 | 1.69 | 0.44 | 0.17 | 0.79 | 0.00 |
| furtos_total | Morumbi | durante | 0.33 | 1.99 | 0.33 | 0.18 | 0.53 | 0.00 |
| furtos_total | Morumbi | pos | 0.19 | 2.93 | 0.36 | 0.20 | 0.60 | 0.00 |
| furtos_total | Morumbi | dp | 0.52 | 2.40 | 0.73 | 0.45 | 1.09 | 0.00 |

## Pico: esperado com e sem EF hora × mês (nível 1 h, P90 Pearson)

| esperado | categoria | janela | RR | p_fisher | p_BH_6janelas | prev_teste_media | prev_min | prev_max |
|---|---|---|---|---|---|---|---|---|
| sem_hm | capital | pre | 1.289 | 0.059 | 0.356 | 8.069 | 3.629 | 19.792 |
| sem_hm | capital | durante | 1.172 | 0.251 | 0.518 | 8.069 | 3.629 | 19.792 |
| sem_hm | capital | pos | 1.125 | 0.412 | 0.617 | 8.069 | 3.629 | 19.792 |
| sem_hm | fora_da_capital | pre | 0.827 | 0.259 | 0.518 | 8.069 | 3.629 | 19.792 |
| sem_hm | fora_da_capital | durante | 0.988 | 1.000 | 1.000 | 8.069 | 3.629 | 19.792 |
| sem_hm | fora_da_capital | pos | 0.997 | 1.000 | 1.000 | 8.069 | 3.629 | 19.792 |
| com_hm | capital | pre | 1.156 | 0.286 | 0.571 | 9.007 | 4.167 | 21.429 |
| com_hm | capital | durante | 1.109 | 0.459 | 0.688 | 9.007 | 4.167 | 21.429 |
| com_hm | capital | pos | 1.298 | 0.049 | 0.294 | 9.007 | 4.167 | 21.429 |
| com_hm | fora_da_capital | pre | 0.765 | 0.106 | 0.319 | 9.007 | 4.167 | 21.429 |
| com_hm | fora_da_capital | durante | 0.938 | 0.712 | 0.712 | 9.007 | 4.167 | 21.429 |
| com_hm | fora_da_capital | pos | 1.069 | 0.634 | 0.712 | 9.007 | 4.167 | 21.429 |

---

# SINISTROS

## Cidade toda: modelo principal com EF hora × mês (Tabela 2 nova)

| desfecho | janela | var_pct | IC95_lo | IC95_hi | p | p_BH_dominio | p_placebo | robustez_NB_e_dia_ok | pareado_confirma | pareado_contradiz | veredito |
|---|---|---|---|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | capital PRÉ | 0.992 | 0.958 | 1.065 | 0.715 | 0.883 | 0.552 | False | False | False | sem evidência |
| acidentes_com_vitima | capital DURANTE | 3.606 | 0.974 | 1.102 | 0.263 | 0.714 | 0.112 | False | False | False | sem evidência |
| acidentes_com_vitima | capital PÓS | 3.829 | 0.979 | 1.101 | 0.212 | 0.714 | 0.024 | False | False | False | sem evidência |
| acidentes_com_vitima | fora da capital PRÉ | 1.983 | 0.966 | 1.077 | 0.482 | 0.825 | 0.132 | False | False | False | sem evidência |
| acidentes_com_vitima | fora da capital DURANTE | 0.247 | 0.946 | 1.062 | 0.933 | 0.933 | 0.404 | False | False | False | sem evidência |
| acidentes_com_vitima | fora da capital PÓS | 3.398 | 0.974 | 1.097 | 0.272 | 0.714 | 0.000 | False | False | False | sem evidência |
| acidentes_total | capital PRÉ | 3.606 | 0.987 | 1.087 | 0.150 | 0.714 | 0.068 | False | False | False | sem evidência |
| acidentes_total | capital DURANTE | 3.424 | 0.975 | 1.097 | 0.265 | 0.714 | 0.084 | False | False | False | sem evidência |
| acidentes_total | capital PÓS | 2.607 | 0.967 | 1.089 | 0.393 | 0.825 | 0.058 | False | False | False | sem evidência |
| acidentes_total | fora da capital PRÉ | -0.341 | 0.946 | 1.050 | 0.898 | 0.933 | 0.642 | False | False | False | sem evidência |
| acidentes_total | fora da capital DURANTE | 1.857 | 0.964 | 1.076 | 0.511 | 0.825 | 0.204 | False | False | False | sem evidência |
| acidentes_total | fora da capital PÓS | -0.566 | 0.944 | 1.047 | 0.829 | 0.933 | 0.594 | False | False | False | sem evidência |
| atropelamentos | capital PRÉ | 4.823 | 0.941 | 1.167 | 0.391 | 0.825 | 0.078 | False | False | False | sem evidência |
| atropelamentos | capital DURANTE | -3.524 | 0.847 | 1.099 | 0.589 | 0.877 | 0.846 | False | False | False | sem evidência |
| atropelamentos | capital PÓS | 10.310 | 0.960 | 1.268 | 0.168 | 0.714 | 0.076 | False | False | False | sem evidência |
| atropelamentos | fora da capital PRÉ | -2.971 | 0.859 | 1.096 | 0.627 | 0.877 | 0.706 | False | False | False | sem evidência |
| atropelamentos | fora da capital DURANTE | -2.375 | 0.863 | 1.104 | 0.702 | 0.883 | 0.894 | False | False | False | sem evidência |
| atropelamentos | fora da capital PÓS | 9.671 | 0.943 | 1.276 | 0.232 | 0.714 | 0.452 | False | False | False | sem evidência |

## Entorno (3 km), diferença em diferenças, 3 estádios empilhados

IRR = razão entre a variação no disco e a variação no resto da cidade. `p` = cluster por semana; `p_quase` = quase-binomial; `p_dia` = cluster por dia. `dp` = DURANTE+PÓS (janela única de 4 h).

| desfecho | janela | IRR | IC95_lo | IC95_hi | p | p_BH | p_quase | p_dia | p_placebo | pareado_confirma | pareado_contradiz | veredito |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | pre | 1.469 | 1.167 | 1.848 | 0.001 | 0.008 | 0.002 | 0.001 | 0.000 | True | False | efeito robusto |
| acidentes_com_vitima | durante | 1.155 | 0.891 | 1.498 | 0.276 | 0.709 | 0.321 | 0.305 | 0.236 | True | False | sem evidência |
| acidentes_com_vitima | pos | 1.016 | 0.747 | 1.381 | 0.922 | 0.926 | 0.926 | 0.926 | 0.924 | False | False | sem evidência |
| acidentes_com_vitima | dp | 1.092 | 0.897 | 1.329 | 0.382 | 0.756 | 0.435 | 0.430 | 0.364 | False | False | sem evidência |
| acidentes_total | pre | 1.353 | 1.125 | 1.626 | 0.001 | 0.008 | 0.003 | 0.005 | 0.002 | True | False | efeito robusto |
| acidentes_total | durante | 1.011 | 0.802 | 1.275 | 0.926 | 0.926 | 0.930 | 0.931 | 0.924 | False | False | sem evidência |
| acidentes_total | pos | 0.957 | 0.727 | 1.260 | 0.754 | 0.926 | 0.750 | 0.761 | 0.830 | False | False | sem evidência |
| acidentes_total | dp | 0.986 | 0.825 | 1.179 | 0.879 | 0.926 | 0.884 | 0.889 | 0.932 | False | False | sem evidência |
| atropelamentos | pre | 1.870 | 1.165 | 3.002 | 0.010 | 0.038 | 0.004 | 0.024 | 0.002 | False | False | robusto no GLM, pareado inconclusivo |
| atropelamentos | durante | 0.661 | 0.304 | 1.436 | 0.295 | 0.709 | 0.187 | 0.283 | 0.346 | False | False | sem evidência |
| atropelamentos | pos | 0.954 | 0.426 | 2.134 | 0.909 | 0.926 | 0.886 | 0.915 | 0.812 | False | False | sem evidência |
| atropelamentos | dp | 0.778 | 0.411 | 1.473 | 0.441 | 0.756 | 0.279 | 0.417 | 0.370 | False | False | sem evidência |

Por estádio com p_BH < 0,05 (família por estádio):

_nenhum_

Pareado do entorno (DiD da fração no disco; IC por bootstrap de jogos):

| estadio | janela | n_jogos | DiD_IRR | IC95_lo | IC95_hi | boot_finitos | correcao_continuidade | desfecho |
|---|---|---|---|---|---|---|---|---|
| Neo Quimica Arena | pre | 40 | 2.147 | 1.097 | 4.135 | 1000 | 0.500 | acidentes_com_vitima |
| Neo Quimica Arena | durante | 40 | 1.599 | 0.671 | 3.638 | 1000 | 0.500 | acidentes_com_vitima |
| Neo Quimica Arena | pos | 40 | 1.748 | 0.483 | 4.011 | 1000 | 0.500 | acidentes_com_vitima |
| Neo Quimica Arena | dp | 40 | 1.672 | 0.795 | 3.316 | 1000 | 0.500 | acidentes_com_vitima |
| Allianz Parque | pre | 33 | 1.979 | 0.970 | 3.871 | 1000 | 0.500 | acidentes_com_vitima |
| Allianz Parque | durante | 33 | 1.859 | 0.805 | 4.247 | 1000 | 0.500 | acidentes_com_vitima |
| Allianz Parque | pos | 33 | 0.885 | 0.288 | 1.866 | 1000 | 0.500 | acidentes_com_vitima |
| Allianz Parque | dp | 33 | 1.343 | 0.716 | 2.448 | 1000 | 0.500 | acidentes_com_vitima |
| Morumbi | pre | 38 | 0.797 | 0.378 | 1.440 | 1000 | 0.500 | acidentes_com_vitima |
| Morumbi | durante | 38 | 1.594 | 0.636 | 3.326 | 1000 | 0.500 | acidentes_com_vitima |
| Morumbi | pos | 38 | 0.952 | 0.289 | 1.933 | 1000 | 0.500 | acidentes_com_vitima |
| Morumbi | dp | 38 | 1.287 | 0.608 | 2.374 | 1000 | 0.500 | acidentes_com_vitima |
| 3 estádios (empilhado) | pre | 111 | 1.558 | 1.051 | 2.294 | 1000 | 0.500 | acidentes_com_vitima |
| 3 estádios (empilhado) | durante | 111 | 1.710 | 1.049 | 2.683 | 1000 | 0.500 | acidentes_com_vitima |
| 3 estádios (empilhado) | pos | 111 | 1.169 | 0.633 | 1.946 | 1000 | 0.500 | acidentes_com_vitima |
| 3 estádios (empilhado) | dp | 111 | 1.438 | 0.985 | 2.082 | 1000 | 0.500 | acidentes_com_vitima |
| Neo Quimica Arena | pre | 40 | 2.540 | 1.551 | 4.255 | 1000 | 0.500 | acidentes_total |
| Neo Quimica Arena | durante | 40 | 0.912 | 0.402 | 1.819 | 1000 | 0.500 | acidentes_total |
| Neo Quimica Arena | pos | 40 | 2.333 | 1.079 | 4.168 | 1000 | 0.500 | acidentes_total |
| Neo Quimica Arena | dp | 40 | 1.462 | 0.821 | 2.343 | 1000 | 0.500 | acidentes_total |
| Allianz Parque | pre | 33 | 1.677 | 0.957 | 2.683 | 1000 | 0.500 | acidentes_total |
| Allianz Parque | durante | 33 | 1.532 | 0.651 | 3.216 | 1000 | 0.500 | acidentes_total |
| Allianz Parque | pos | 33 | 0.978 | 0.376 | 1.815 | 1000 | 0.500 | acidentes_total |
| Allianz Parque | dp | 33 | 1.264 | 0.691 | 2.055 | 1000 | 0.500 | acidentes_total |
| Morumbi | pre | 38 | 0.676 | 0.349 | 1.167 | 1000 | 0.500 | acidentes_total |
| Morumbi | durante | 38 | 1.139 | 0.457 | 2.359 | 1000 | 0.500 | acidentes_total |
| Morumbi | pos | 38 | 0.946 | 0.355 | 1.836 | 1000 | 0.500 | acidentes_total |
| Morumbi | dp | 38 | 1.054 | 0.449 | 1.916 | 1000 | 0.500 | acidentes_total |
| 3 estádios (empilhado) | pre | 111 | 1.514 | 1.107 | 2.068 | 1000 | 0.500 | acidentes_total |
| 3 estádios (empilhado) | durante | 111 | 1.141 | 0.695 | 1.746 | 1000 | 0.500 | acidentes_total |
| 3 estádios (empilhado) | pos | 111 | 1.394 | 0.886 | 2.066 | 1000 | 0.500 | acidentes_total |
| 3 estádios (empilhado) | dp | 111 | 1.252 | 0.886 | 1.729 | 1000 | 0.500 | acidentes_total |
| Neo Quimica Arena | pre | 40 | 3.223 | 0.981 | 12.061 | 1000 | 0.500 | atropelamentos |
| Neo Quimica Arena | durante | 40 | 0.632 | 0.090 | 3.324 | 1000 | 0.500 | atropelamentos |
| Neo Quimica Arena | pos | 40 | 1.702 | 0.123 | 9.400 | 1000 | 0.500 | atropelamentos |
| Neo Quimica Arena | dp | 40 | 1.303 | 0.154 | 4.805 | 1000 | 0.500 | atropelamentos |
| Allianz Parque | pre | 33 | 0.627 | 0.125 | 2.552 | 1000 | 0.500 | atropelamentos |
| Allianz Parque | durante | 33 | 2.521 | 0.526 | 8.496 | 1000 | 0.500 | atropelamentos |
| Allianz Parque | pos | 33 | 0.433 | 0.207 | 1.259 | 1000 | 0.500 | atropelamentos |
| Allianz Parque | dp | 33 | 1.702 | 0.273 | 5.759 | 1000 | 0.500 | atropelamentos |
| Morumbi | pre | 38 | 1.347 | 0.200 | 4.375 | 1000 | 0.500 | atropelamentos |
| Morumbi | durante | 38 | 0.932 | 0.132 | 6.134 | 1000 | 0.500 | atropelamentos |
| Morumbi | pos | 38 | 0.438 | 0.159 | 1.414 | 1000 | 0.500 | atropelamentos |
| Morumbi | dp | 38 | 0.636 | 0.095 | 2.950 | 1000 | 0.500 | atropelamentos |
| 3 estádios (empilhado) | pre | 111 | 2.339 | 0.950 | 5.072 | 1000 | 0.500 | atropelamentos |
| 3 estádios (empilhado) | durante | 111 | 1.273 | 0.372 | 3.478 | 1000 | 0.500 | atropelamentos |
| 3 estádios (empilhado) | pos | 111 | 1.302 | 0.108 | 4.584 | 1000 | 0.500 | atropelamentos |
| 3 estádios (empilhado) | dp | 111 | 1.305 | 0.395 | 3.139 | 1000 | 0.500 | atropelamentos |

Raio (só modelo principal, empilhado):

| desfecho | janela | 1.0 | 2.0 | 3.0 | 5.0 |
|---|---|---|---|---|---|
| acidentes_com_vitima | durante | 1.23 (p=0.644) | 0.95 (p=0.836) | 1.16 (p=0.276) | 1.02 (p=0.863) |
| acidentes_com_vitima | pos | 0.79 (p=0.688) | 1.00 (p=0.985) | 1.02 (p=0.922) | 1.16 (p=0.100) |
| acidentes_com_vitima | pre | 2.14 (p=0.037) | 1.38 (p=0.063) | 1.47 (p=0.001) | 1.09 (p=0.250) |
| acidentes_total | durante | 1.13 (p=0.738) | 0.89 (p=0.588) | 1.01 (p=0.926) | 0.94 (p=0.465) |
| acidentes_total | pos | 0.76 (p=0.556) | 0.97 (p=0.895) | 0.96 (p=0.754) | 1.10 (p=0.250) |
| acidentes_total | pre | 1.83 (p=0.034) | 1.56 (p=0.003) | 1.35 (p=0.001) | 1.11 (p=0.118) |
| atropelamentos | durante | 3.82 (p=0.142) | 1.17 (p=0.773) | 0.66 (p=0.295) | 0.82 (p=0.402) |
| atropelamentos | pos | 18.71 (p=0.056) | 3.02 (p=0.048) | 0.95 (p=0.909) | 1.32 (p=0.244) |
| atropelamentos | pre | 2.33 (p=0.178) | 1.81 (p=0.068) | 1.87 (p=0.010) | 1.25 (p=0.202) |

## Tabela 7 nova (quarta 21h30)

| desfecho | estadio | janela | esperado_sem_jogo | IRR | excesso | excesso_IC95_lo | excesso_IC95_hi | p |
|---|---|---|---|---|---|---|---|---|
| acidentes_com_vitima | Neo Quimica Arena | pre | 0.35 | 1.58 | 0.20 | 0.04 | 0.43 | 0.01 |
| acidentes_com_vitima | Neo Quimica Arena | durante | 0.12 | 1.28 | 0.03 | -0.02 | 0.12 | 0.29 |
| acidentes_com_vitima | Neo Quimica Arena | pos | 0.16 | 1.10 | 0.02 | -0.07 | 0.19 | 0.78 |
| acidentes_com_vitima | Allianz Parque | pre | 0.20 | 1.44 | 0.09 | -0.01 | 0.25 | 0.10 |
| acidentes_com_vitima | Allianz Parque | durante | 0.12 | 0.99 | -0.00 | -0.05 | 0.08 | 0.97 |
| acidentes_com_vitima | Allianz Parque | pos | 0.09 | 0.95 | -0.00 | -0.04 | 0.06 | 0.86 |
| acidentes_com_vitima | Morumbi | pre | 0.30 | 1.39 | 0.12 | -0.03 | 0.35 | 0.15 |
| acidentes_com_vitima | Morumbi | durante | 0.12 | 1.21 | 0.03 | -0.03 | 0.11 | 0.42 |
| acidentes_com_vitima | Morumbi | pos | 0.09 | 1.01 | 0.00 | -0.04 | 0.06 | 0.98 |

## Pico: esperado com e sem EF hora × mês (nível 1 h, P90 Pearson)

| esperado | categoria | janela | RR | p_fisher | p_BH_6janelas | prev_teste_media | prev_min | prev_max |
|---|---|---|---|---|---|---|---|---|
| sem_hm | capital | pre | 1.008 | 0.935 | 1.000 | 12.977 | 7.661 | 21.121 |
| sem_hm | capital | durante | 1.055 | 0.682 | 1.000 | 12.977 | 7.661 | 21.121 |
| sem_hm | capital | pos | 1.219 | 0.141 | 0.755 | 12.977 | 7.661 | 21.121 |
| sem_hm | fora_da_capital | pre | 1.123 | 0.378 | 0.755 | 12.977 | 7.661 | 21.121 |
| sem_hm | fora_da_capital | durante | 0.992 | 1.000 | 1.000 | 12.977 | 7.661 | 21.121 |
| sem_hm | fora_da_capital | pos | 1.130 | 0.344 | 0.755 | 12.977 | 7.661 | 21.121 |
| com_hm | capital | pre | 0.959 | 0.869 | 0.936 | 13.758 | 7.930 | 23.420 |
| com_hm | capital | durante | 1.029 | 0.806 | 0.936 | 13.758 | 7.930 | 23.420 |
| com_hm | capital | pos | 1.193 | 0.191 | 0.936 | 13.758 | 7.930 | 23.420 |
| com_hm | fora_da_capital | pre | 1.008 | 0.936 | 0.936 | 13.758 | 7.930 | 23.420 |
| com_hm | fora_da_capital | durante | 0.971 | 0.883 | 0.936 | 13.758 | 7.930 | 23.420 |
| com_hm | fora_da_capital | pos | 1.127 | 0.385 | 0.936 | 13.758 | 7.930 | 23.420 |

---

# Antes × depois (números do artigo atual que mudaram)


## CRIMES (168 de 207 números conferidos mudaram)

| item | antes | depois | fonte_nova |
|---|---|---|---|
| Tab. 2 Crimes violentos capital PRÉ (%) | +4,7 | +2,9 | vereditos.csv |
| Tab. 2 Crimes violentos capital PRÉ (marca) | † | * | vereditos.csv |
| p_BH Crimes violentos capital PRÉ | 0,041 | 0,205 | vereditos.csv |
| Tab. 2 Crimes violentos capital DURANTE (%) | -2,1 | -1,6 | vereditos.csv |
| Tab. 2 Crimes violentos capital PÓS (marca) | * | (sem) | vereditos.csv |
| p_BH Crimes violentos capital PÓS | 0,223 | 0,205 | vereditos.csv |
| Tab. 2 Crimes violentos fora da capital PRÉ (%) | -1,5 | -3,1 | vereditos.csv |
| Tab. 2 Crimes violentos fora da capital PRÉ (marca) | (sem) | * | vereditos.csv |
| p_BH Crimes violentos fora da capital PRÉ | 0,519 | 0,157 | vereditos.csv |
| Tab. 2 Crimes violentos fora da capital DURANTE (%) | -2,5 | -2,2 | vereditos.csv |
| Tab. 2 Crimes violentos fora da capital PÓS (%) | -0,2 | +0,2 | vereditos.csv |
| Tab. 2 Lesão corporal dolosa capital PRÉ (%) | +2,5 | +1,7 | vereditos.csv |
| p_BH Lesão corporal dolosa capital PRÉ | 0,520 | 0,563 | vereditos.csv |
| Tab. 2 Lesão corporal dolosa capital DURANTE (%) | -3,1 | -2,6 | vereditos.csv |
| Tab. 2 Lesão corporal dolosa capital PÓS (%) | +3,4 | +3,3 | vereditos.csv |
| Tab. 2 Lesão corporal dolosa fora da capital DURANTE (%) | -2,3 | -2,4 | vereditos.csv |
| Tab. 2 Lesão corporal dolosa fora da capital PÓS (%) | -1,8 | -1,7 | vereditos.csv |
| Tab. 2 Roubos capital PRÉ (%) | +5,3 | +3,0 | vereditos.csv |
| Tab. 2 Roubos capital PRÉ (marca) | † | * | vereditos.csv |
| p_BH Roubos capital PRÉ | 0,041 | 0,205 | vereditos.csv |
| Tab. 2 Roubos capital DURANTE (%) | -1,8 | -1,2 | vereditos.csv |
| Tab. 2 Roubos fora da capital PRÉ (%) | -1,1 | -3,2 | vereditos.csv |
| Tab. 2 Roubos fora da capital PRÉ (marca) | (sem) | * | vereditos.csv |
| p_BH Roubos fora da capital PRÉ | 0,606 | 0,205 | vereditos.csv |
| Tab. 2 Roubos fora da capital DURANTE (%) | -2,8 | -2,3 | vereditos.csv |
| Tab. 2 Roubos fora da capital PÓS (%) | +0,0 | +0,4 | vereditos.csv |
| Tab. 2 Furtos capital PRÉ (%) | +4,1 | +3,1 | vereditos.csv |
| Tab. 2 Furtos capital PRÉ (marca) | * | (sem) | vereditos.csv |
| p_BH Furtos capital PRÉ | 0,147 | 0,231 | vereditos.csv |
| Tab. 2 Furtos capital DURANTE (%) | +1,4 | +1,9 | vereditos.csv |
| Tab. 2 Furtos capital PÓS (%) | +4,1 | +4,9 | vereditos.csv |
| p_BH Furtos capital PÓS | 0,195 | 0,157 | vereditos.csv |
| Tab. 2 Furtos fora da capital PRÉ (%) | +2,4 | +1,1 | vereditos.csv |
| Tab. 2 Furtos fora da capital DURANTE (%) | +1,1 | +1,4 | vereditos.csv |
| Tab. 2 Furtos fora da capital PÓS (%) | +0,4 | +1,3 | vereditos.csv |
| pareado Crimes violentos pre DiD_IRR (%) | +1,2 | +1,3 | controles_pareados.csv |
| pareado Crimes violentos pre IC95_lo (%) | -3,1 | -2,6 | controles_pareados.csv |
| pareado Crimes violentos pre IC95_hi (%) | +5,0 | +5,4 | controles_pareados.csv |
| pareado Crimes violentos durante IC95_lo (%) | -10,4 | -10,8 | controles_pareados.csv |
| pareado Crimes violentos durante IC95_hi (%) | -2,7 | -2,6 | controles_pareados.csv |
| pareado Crimes violentos pos DiD_IRR (%) | +1,2 | +1,3 | controles_pareados.csv |
| pareado Crimes violentos pos IC95_lo (%) | -3,1 | -3,0 | controles_pareados.csv |
| pareado Roubos pre DiD_IRR (%) | +1,3 | +1,5 | controles_pareados.csv |
| pareado Roubos pre IC95_lo (%) | -3,3 | -3,1 | controles_pareados.csv |
| pareado Roubos pre IC95_hi (%) | +6,0 | +6,1 | controles_pareados.csv |
| pareado Roubos durante DiD_IRR (%) | -6,6 | -6,5 | controles_pareados.csv |
| pareado Roubos durante IC95_lo (%) | -10,9 | -10,6 | controles_pareados.csv |
| pareado Roubos durante IC95_hi (%) | -2,1 | -1,6 | controles_pareados.csv |
| pareado Roubos pos IC95_lo (%) | -3,4 | -3,3 | controles_pareados.csv |
| pareado Roubos pos IC95_hi (%) | +6,4 | +6,2 | controles_pareados.csv |
| placebo p Crimes violentos capital pre | 0,000 | 0,002 | placebo_permutacao.csv |
| placebo p Crimes violentos capital durante | 0,428 | 0,766 | placebo_permutacao.csv |
| placebo p Crimes violentos capital pos | 0,036 | 0,044 | placebo_permutacao.csv |
| pré-tendência p (capital) | 0,007 | 0,045 | event_study.csv |
| pré-tendência p (fora_da_capital) | 0,084 | 0,273 | event_study.csv |
| event study Crimes violentos capital k=-3 (%) | +3,9 | +3,3 | event_study.csv |
| event study Crimes violentos capital k=-2 (%) | +4,4 | +1,9 | event_study.csv |
| event study Crimes violentos capital k=-1 (%) | +5,5 | +4,1 | event_study.csv |
| event study Crimes violentos capital k=0 (%) | -0,9 | -1,0 | event_study.csv |
| event study Crimes violentos capital k=1 (%) | -2,9 | -1,9 | event_study.csv |
| event study Crimes violentos capital k=2 (%) | +1,4 | +1,2 | event_study.csv |
| event study Crimes violentos capital k=3 (%) | +4,5 | +4,7 | event_study.csv |
| tercil C_pre__T1 Crimes violentos (%) | +0,6 | +0,8 | dose_resposta_publico.csv |
| tercil C_pre__T3 Crimes violentos (%) | +6,2 | +6,3 | dose_resposta_publico.csv |
| entorno 3 estádios Crimes violentos durante (%) | +15 | +23 | entorno_modelo_principal.csv |
| entorno 3 estádios Crimes violentos durante p_BH | 0,055 | 0,007 | entorno_modelo_principal.csv |
| entorno 3 estádios Crimes violentos pos (%) | +31 | +36 | entorno_modelo_principal.csv |
| entorno 3 estádios Crimes violentos pre (%) | +5 | -1 | entorno_modelo_principal.csv |
| entorno 3 estádios Crimes violentos pre p_BH | 0,479 | 0,947 | entorno_modelo_principal.csv |
| entorno 3 estádios Furtos durante (%) | +66 | +58 | entorno_modelo_principal.csv |
| entorno 3 estádios Furtos pos (%) | +85 | +87 | entorno_modelo_principal.csv |
| entorno 3 estádios Furtos pre (%) | +32 | +30 | entorno_modelo_principal.csv |
| entorno 3 estádios Lesão corporal dolosa durante (%) | +104 | +138 | entorno_modelo_principal.csv |
| entorno 3 estádios Lesão corporal dolosa pos (%) | -26 | -29 | entorno_modelo_principal.csv |
| entorno 3 estádios Lesão corporal dolosa pos p_BH | 0,237 | 0,171 | entorno_modelo_principal.csv |
| entorno 3 estádios Lesão corporal dolosa pre (%) | +10 | +2 | entorno_modelo_principal.csv |
| entorno 3 estádios Lesão corporal dolosa pre p_BH | 0,672 | 0,947 | entorno_modelo_principal.csv |
| entorno 3 estádios Roubos durante (%) | +8 | +15 | entorno_modelo_principal.csv |
| entorno 3 estádios Roubos durante p_BH | 0,324 | 0,105 | entorno_modelo_principal.csv |
| entorno 3 estádios Roubos pos (%) | +39 | +43 | entorno_modelo_principal.csv |
| entorno 3 estádios Roubos pre (%) | +6 | -0 | entorno_modelo_principal.csv |
| entorno 3 estádios Roubos pre p_BH | 0,479 | 0,947 | entorno_modelo_principal.csv |
| Tab. 5a prevalência média (1 h, %) | 8,1 | 9,0 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5a prevalência mín (1 h, %) | 3,6 | 4,2 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5a prevalência máx (1 h, %) | 19,9 | 21,4 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5b RR capital pre | 1,31 | 1,16 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital pre | 0,041 | 0,286 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR capital durante | 1,15 | 1,11 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital durante | 0,325 | 0,459 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR capital pos | 1,20 | 1,30 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital pos | 0,190 | 0,049 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR fora_da_capital pre | 0,87 | 0,76 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital pre | 0,421 | 0,106 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR fora_da_capital durante | 0,99 | 0,94 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital durante | 1,000 | 0,712 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR fora_da_capital pos | 1,02 | 1,07 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital pos | 0,874 | 0,634 | pico_com_hm/pico_por_janela.csv |
| Tab. 7 Neo Quimica Arena pre Crimes violentos rel (%) | -8 | -11 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Crimes violentos abs | -0,12 | -0,16 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Crimes violentos rel (%) | +6 | +14 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Crimes violentos abs | +0,11 | +0,25 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Crimes violentos rel (%) | +4 | -1 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Crimes violentos abs | +0,11 | -0,04 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Crimes violentos rel (%) | +4 | +7 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Crimes violentos abs | +0,08 | +0,13 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Crimes violentos rel (%) | +21 | +24 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Crimes violentos abs | +0,26 | +0,29 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Crimes violentos rel (%) | +26 | +15 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Crimes violentos abs | +0,44 | +0,25 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Crimes violentos rel (%) | +58 | +65 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Crimes violentos abs | +0,67 | +0,74 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Crimes violentos rel (%) | +64 | +65 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Roubos rel (%) | -8 | -11 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Roubos abs | -0,10 | -0,14 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Roubos rel (%) | -3 | +4 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Roubos abs | -0,05 | +0,06 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pos Roubos rel (%) | +43 | +42 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Roubos rel (%) | +5 | -1 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Roubos abs | +0,15 | -0,02 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Roubos rel (%) | -0 | +1 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Roubos abs | -0,00 | +0,01 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Roubos rel (%) | +26 | +29 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Roubos abs | +0,31 | +0,35 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Roubos rel (%) | +23 | +12 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Roubos abs | +0,38 | +0,21 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Roubos rel (%) | +49 | +55 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Roubos abs | +0,52 | +0,59 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Roubos rel (%) | +71 | +73 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Roubos abs | +0,44 | +0,45 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Furtos rel (%) | +55 | +47 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Furtos abs | +0,43 | +0,37 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Furtos rel (%) | +94 | +92 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Furtos abs | +0,66 | +0,64 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pos Furtos rel (%) | +108 | +106 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pos Furtos abs | +0,71 | +0,69 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Furtos rel (%) | +14 | +7 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Furtos abs | +0,36 | +0,19 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Furtos rel (%) | +45 | +46 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Furtos abs | +0,39 | +0,40 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Furtos rel (%) | +55 | +69 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Furtos abs | +0,35 | +0,44 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Furtos rel (%) | +95 | +99 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Furtos abs | +0,32 | +0,33 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Furtos rel (%) | +187 | +193 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Furtos abs | +0,35 | +0,36 | entorno_tabela_risco.csv |
| Tab. 4 Crimes violentos durante todos (%) | +15 | +23 | entorno_canal.csv |
| Tab. 4 Crimes violentos pos todos (%) | +31 | +36 | entorno_canal.csv |
| Tab. 4 Furtos durante todos (%) | +66 | +58 | entorno_canal.csv |
| Tab. 4 Furtos pos todos (%) | +85 | +87 | entorno_canal.csv |
| Tab. 4 Roubos durante todos (%) | +8 | +15 | entorno_canal.csv |
| Tab. 4 Roubos pos todos (%) | +39 | +43 | entorno_canal.csv |
| Tab. 4 Crimes violentos durante sem conduta nula (%) | +7 | +14 | entorno_canal.csv |
| Tab. 4 Crimes violentos pos sem conduta nula (%) | +40 | +44 | entorno_canal.csv |
| Tab. 4 Furtos durante sem conduta nula (%) | +58 | +52 | entorno_canal.csv |
| Tab. 4 Furtos pos sem conduta nula (%) | +82 | +85 | entorno_canal.csv |
| Tab. 4 Roubos durante sem conduta nula (%) | +7 | +14 | entorno_canal.csv |
| Tab. 4 Roubos pos sem conduta nula (%) | +40 | +44 | entorno_canal.csv |
| Tab. 4 Crimes violentos durante só BO online (%) | +14 | +22 | entorno_canal.csv |
| Tab. 4 Crimes violentos pos só BO online (%) | +44 | +53 | entorno_canal.csv |
| Tab. 4 Furtos durante só BO online (%) | +61 | +67 | entorno_canal.csv |
| Tab. 4 Roubos durante só BO online (%) | +8 | +16 | entorno_canal.csv |
| Tab. 4 Roubos pos só BO online (%) | +49 | +56 | entorno_canal.csv |
| Tab. 4 Crimes violentos durante só presencial (%) | +14 | +24 | entorno_canal.csv |
| Tab. 4 Crimes violentos pos só presencial (%) | -0 | -2 | entorno_canal.csv |
| Tab. 4 Furtos durante só presencial (%) | +47 | +37 | entorno_canal.csv |
| Tab. 4 Furtos pos só presencial (%) | +105 | +97 | entorno_canal.csv |
| Tab. 4 Roubos durante só presencial (%) | +6 | +10 | entorno_canal.csv |
| Tab. 4 Roubos pos só presencial (%) | +11 | +7 | entorno_canal.csv |

## SINISTROS (91 de 115 números conferidos mudaram)

| item | antes | depois | fonte_nova |
|---|---|---|---|
| Tab. 2 Sinistros com vítima capital PRÉ (%) | +1,5 | +1,0 | vereditos.csv |
| p_BH Sinistros com vítima capital PRÉ | 0,723 | 0,883 | vereditos.csv |
| Tab. 2 Sinistros com vítima capital DURANTE (%) | +2,9 | +3,6 | vereditos.csv |
| Tab. 2 Sinistros com vítima capital PÓS (%) | +3,9 | +3,8 | vereditos.csv |
| Tab. 2 Sinistros com vítima fora da capital PRÉ (%) | +2,6 | +2,0 | vereditos.csv |
| Tab. 2 Sinistros com vítima fora da capital DURANTE (%) | +0,6 | +0,2 | vereditos.csv |
| Tab. 2 Sinistros com vítima fora da capital PÓS (%) | +4,3 | +3,4 | vereditos.csv |
| Tab. 2 Sinistros totais capital PRÉ (%) | +4,0 | +3,6 | vereditos.csv |
| p_BH Sinistros totais capital PRÉ | 0,692 | 0,714 | vereditos.csv |
| Tab. 2 Sinistros totais capital DURANTE (%) | +2,6 | +3,4 | vereditos.csv |
| Tab. 2 Sinistros totais capital PÓS (%) | +2,8 | +2,6 | vereditos.csv |
| Tab. 2 Sinistros totais fora da capital PRÉ (%) | -0,1 | -0,3 | vereditos.csv |
| Tab. 2 Sinistros totais fora da capital PÓS (%) | +0,0 | -0,6 | vereditos.csv |
| Tab. 2 Atropelamentos capital PRÉ (%) | +4,4 | +4,8 | vereditos.csv |
| p_BH Atropelamentos capital PRÉ | 0,692 | 0,825 | vereditos.csv |
| Tab. 2 Atropelamentos capital DURANTE (%) | -7,0 | -3,5 | vereditos.csv |
| Tab. 2 Atropelamentos capital PÓS (%) | +8,4 | +10,3 | vereditos.csv |
| Tab. 2 Atropelamentos fora da capital PRÉ (%) | -3,4 | -3,0 | vereditos.csv |
| Tab. 2 Atropelamentos fora da capital DURANTE (%) | -5,3 | -2,4 | vereditos.csv |
| Tab. 2 Atropelamentos fora da capital PÓS (%) | +9,6 | +9,7 | vereditos.csv |
| pareado Sinistros com vítima pre DiD_IRR (%) | +2,3 | +2,1 | controles_pareados.csv |
| pareado Sinistros com vítima pre IC95_lo (%) | -4,8 | -5,1 | controles_pareados.csv |
| pareado Sinistros com vítima pre IC95_hi (%) | +10,6 | +10,1 | controles_pareados.csv |
| pareado Sinistros com vítima durante DiD_IRR (%) | +4,2 | +4,9 | controles_pareados.csv |
| pareado Sinistros com vítima durante IC95_lo (%) | -3,0 | -3,3 | controles_pareados.csv |
| pareado Sinistros com vítima durante IC95_hi (%) | +12,9 | +13,0 | controles_pareados.csv |
| pareado Sinistros com vítima pos DiD_IRR (%) | -2,4 | -2,0 | controles_pareados.csv |
| pareado Sinistros com vítima pos IC95_lo (%) | -12,4 | -12,1 | controles_pareados.csv |
| pareado Sinistros com vítima pos IC95_hi (%) | +6,7 | +8,9 | controles_pareados.csv |
| placebo p Sinistros com vítima capital pre | 0,436 | 0,552 | placebo_permutacao.csv |
| placebo p Sinistros com vítima capital durante | 0,272 | 0,112 | placebo_permutacao.csv |
| pré-tendência p (capital) | 0,890 | 0,975 | event_study.csv |
| pré-tendência p (fora_da_capital) | 0,210 | 0,227 | event_study.csv |
| event study Sinistros com vítima capital k=-3 (%) | +1,4 | -0,1 | event_study.csv |
| event study Sinistros com vítima capital k=-2 (%) | +2,4 | +1,7 | event_study.csv |
| event study Sinistros com vítima capital k=-1 (%) | -0,3 | -0,7 | event_study.csv |
| event study Sinistros com vítima capital k=0 (%) | +6,0 | +6,9 | event_study.csv |
| event study Sinistros com vítima capital k=1 (%) | -0,7 | -0,1 | event_study.csv |
| event study Sinistros com vítima capital k=2 (%) | +6,4 | +5,7 | event_study.csv |
| event study Sinistros com vítima capital k=3 (%) | +1,8 | +2,9 | event_study.csv |
| tercil C_pre__T2 Sinistros com vítima (%) | -0,8 | -0,9 | dose_resposta_publico.csv |
| tercil C_pre__T3 Sinistros com vítima (%) | +4,6 | +4,5 | dose_resposta_publico.csv |
| entorno 3 estádios Sinistros com vítima durante (%) | +18 | +16 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros com vítima durante p_BH | 0,418 | 0,709 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros com vítima pos (%) | +6 | +2 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros com vítima pos p_BH | 0,777 | 0,926 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros com vítima pre (%) | +46 | +47 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros com vítima pre p_BH | 0,004 | 0,008 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros totais durante (%) | +5 | +1 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros totais durante p_BH | 0,777 | 0,926 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros totais pos p_BH | 0,777 | 0,926 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros totais pre (%) | +38 | +35 | entorno_modelo_principal.csv |
| entorno 3 estádios Sinistros totais pre p_BH | 0,004 | 0,008 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos durante (%) | -21 | -34 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos durante p_BH | 0,771 | 0,709 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos pos (%) | -100 | -5 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos pos p_BH | 0,000 | 0,926 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos pre (%) | +60 | +87 | entorno_modelo_principal.csv |
| entorno 3 estádios Atropelamentos pre p_BH | 0,163 | 0,038 | entorno_modelo_principal.csv |
| Tab. 5a prevalência média (1 h, %) | 12,9 | 13,8 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5a prevalência mín (1 h, %) | 7,5 | 7,9 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5a prevalência máx (1 h, %) | 21,1 | 23,4 | pico_com_hm/pico_validacao_folds.csv |
| Tab. 5b RR capital pre | 0,98 | 0,96 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital pre | 1,000 | 0,869 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR capital durante | 1,06 | 1,03 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital durante | 0,682 | 0,806 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR capital pos | 1,22 | 1,19 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher capital pos | 0,141 | 0,191 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR fora_da_capital pre | 1,12 | 1,01 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital pre | 0,378 | 0,936 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b RR fora_da_capital durante | 0,99 | 0,97 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital durante | 1,000 | 0,883 | pico_com_hm/pico_por_janela.csv |
| Tab. 5b p Fisher fora_da_capital pos | 0,344 | 0,385 | pico_com_hm/pico_por_janela.csv |
| Tab. 7 Neo Quimica Arena pre Sinistros com vítima rel (%) | +69 | +58 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pre Sinistros com vítima abs | +0,24 | +0,20 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Sinistros com vítima rel (%) | +38 | +28 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena durante Sinistros com vítima abs | +0,05 | +0,03 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pos Sinistros com vítima rel (%) | +8 | +10 | entorno_tabela_risco.csv |
| Tab. 7 Neo Quimica Arena pos Sinistros com vítima abs | +0,01 | +0,02 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Sinistros com vítima rel (%) | +38 | +44 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pre Sinistros com vítima abs | +0,08 | +0,09 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Sinistros com vítima rel (%) | +5 | -1 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque durante Sinistros com vítima abs | +0,01 | -0,00 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Sinistros com vítima rel (%) | +2 | -5 | entorno_tabela_risco.csv |
| Tab. 7 Allianz Parque pos Sinistros com vítima abs | +0,00 | -0,00 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Sinistros com vítima rel (%) | +27 | +39 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pre Sinistros com vítima abs | +0,08 | +0,12 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Sinistros com vítima rel (%) | +9 | +21 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi durante Sinistros com vítima abs | +0,01 | +0,03 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Sinistros com vítima rel (%) | +8 | +1 | entorno_tabela_risco.csv |
| Tab. 7 Morumbi pos Sinistros com vítima abs | +0,01 | +0,00 | entorno_tabela_risco.csv |
