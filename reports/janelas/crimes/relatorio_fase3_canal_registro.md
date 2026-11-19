# V2 / Fase 3 (item 0) — Canal de registro no entorno dos estádios

Gerado por `scripts/34a_canal_registro.py`. Robustez do resultado do entorno da Fase 2 (modelo principal inalterado). Disco de 3 km, registros com hora, sem as células de empilhamento.

Conferência: contagens da versão `original` reproduzem as do `33` (diferença máxima por hora: 0).

## 1. De onde vêm os registros

- **DRADE** (Delegacia de Repressão aos Delitos de Intolerância Esportiva): **10 BOs** no entorno dos 3 estádios em 2022–2023 (todas as naturezas) — não é um canal relevante; não existe um posto do estádio que concentre os registros.
- **Delegacia Eletrônica (BO online):** 64% dos registros do entorno; BOs sem `DESCR_CONDUTA`: 13%.

O/E nas janelas DURANTE+PÓS dos jogos do próprio estádio (crimes violentos + furtos), por canal (O = observado, E = taxa das horas sem jogo, mesma hora × dia da semana; descritivo):

| estadio | canal | valor | O | E | O/E | IC95_lo | IC95_hi | excesso |
|---|---|---|---|---|---|---|---|---|
| Neo Quimica Arena | drade | False | 422 | 284.28 | 1.48 | 1.35 | 1.63 | 137.72 |
| Neo Quimica Arena | eletronica | False | 136 | 104.41 | 1.30 | 1.09 | 1.54 | 31.59 |
| Neo Quimica Arena | eletronica | True | 286 | 179.87 | 1.59 | 1.41 | 1.79 | 106.13 |
| Neo Quimica Arena | conduta_nula | False | 375 | 253.50 | 1.48 | 1.33 | 1.64 | 121.50 |
| Neo Quimica Arena | conduta_nula | True | 47 | 30.79 | 1.53 | 1.12 | 2.03 | 16.21 |
| Allianz Parque | drade | False | 553 | 436.66 | 1.27 | 1.16 | 1.38 | 116.34 |
| Allianz Parque | drade | True | 0 | 0.00 |  |  | inf | 0.00 |
| Allianz Parque | eletronica | False | 153 | 117.34 | 1.30 | 1.11 | 1.53 | 35.66 |
| Allianz Parque | eletronica | True | 400 | 319.32 | 1.25 | 1.13 | 1.38 | 80.68 |
| Allianz Parque | conduta_nula | False | 502 | 411.62 | 1.22 | 1.12 | 1.33 | 90.38 |
| Allianz Parque | conduta_nula | True | 51 | 25.04 | 2.04 | 1.52 | 2.68 | 25.96 |
| Morumbi | drade | False | 347 | 196.60 | 1.77 | 1.58 | 1.96 | 150.40 |
| Morumbi | drade | True | 0 | 0.00 |  |  | inf | 0.00 |
| Morumbi | eletronica | False | 79 | 39.15 | 2.02 | 1.60 | 2.51 | 39.85 |
| Morumbi | eletronica | True | 268 | 157.45 | 1.70 | 1.50 | 1.92 | 110.55 |
| Morumbi | conduta_nula | False | 314 | 185.48 | 1.69 | 1.51 | 1.89 | 128.52 |
| Morumbi | conduta_nula | True | 33 | 11.12 | 2.97 | 2.04 | 4.17 | 21.88 |

Delegacias e tipos de local mais frequentes nas janelas:

| estadio | campo | valor | pct_registros_janelas |
|---|---|---|---|
| Neo Quimica Arena | deleg | DELEGACIA ELETRONICA | 50.0 |
| Neo Quimica Arena | deleg | DELEGACIA ELETRONICA 1 | 17.1 |
| Neo Quimica Arena | deleg | 24º D.P. PONTE RASA | 5.5 |
| Neo Quimica Arena | deleg | 53º D.P. PARQUE DO CARMO | 4.5 |
| Neo Quimica Arena | deleg | 64º D.P. CID.AE CARVALHO | 4.0 |
| Neo Quimica Arena | deleg | 66º D.P. JDIM ARICANDUVA | 3.8 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Via Pública | 62.1 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Via pública | 26.5 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Metroviário e Ferroviário Metropolitano | 1.7 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Outros | 1.4 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Terminal/Estação | 1.2 |
| Neo Quimica Arena | DESCR_SUBTIPOLOCAL | Centro Comerc./Empresarial | 0.5 |
| Allianz Parque | deleg | DELEGACIA ELETRONICA | 47.9 |
| Allianz Parque | deleg | DELEGACIA ELETRONICA 1 | 24.2 |
| Allianz Parque | deleg | 91º D.P. CEASA | 4.7 |
| Allianz Parque | deleg | 23º D.P. PERDIZES | 2.7 |
| Allianz Parque | deleg | 14º D.P. PINHEIROS | 2.5 |
| Allianz Parque | deleg | 13º D.P. CASA VERDE | 1.3 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Via Pública | 55.3 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Via pública | 31.6 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Comércio e serviços | 3.3 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Terminal/Estação | 1.3 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Metroviário e Ferroviário Metropolitano | 1.3 |
| Allianz Parque | DESCR_SUBTIPOLOCAL | Estádio/Ginásio | 1.1 |
| Morumbi | deleg | DELEGACIA ELETRONICA | 52.2 |
| Morumbi | deleg | DELEGACIA ELETRONICA 1 | 24.5 |
| Morumbi | deleg | 89º D.P. JARDIM TABOAO | 5.8 |
| Morumbi | deleg | 34º D.P. MORUMBI | 2.0 |
| Morumbi | deleg | 96º D.P. MONÇÕES | 1.7 |
| Morumbi | deleg | 01º D.P. TABOÃO DA SERRA | 0.9 |
| Morumbi | DESCR_SUBTIPOLOCAL | Via Pública | 68.3 |
| Morumbi | DESCR_SUBTIPOLOCAL | Via pública | 23.1 |
| Morumbi | DESCR_SUBTIPOLOCAL | Metroviário e Ferroviário Metropolitano | 2.0 |
| Morumbi | DESCR_SUBTIPOLOCAL | Veículo em movimento | 0.9 |
| Morumbi | DESCR_SUBTIPOLOCAL | Estádio/Ginásio | 0.6 |
| Morumbi | DESCR_SUBTIPOLOCAL | Lazer e recreação | 0.6 |

## 2. Modelo do entorno sem cada canal (lado a lado)

Mesmo modelo da Fase 2 (Poisson, EF hora × dia da semana + ano × mês + feriado/véspera/férias + clima, janelas dos jogos daquele estádio vs dos outros, cluster por semana).

| estadio | desfecho | janela | original | sem DRADE | sem conduta nula | só presencial (sem Delegacia Eletrônica) | só BO online (Delegacia Eletrônica) |
|---|---|---|---|---|---|---|---|
| 3 estádios | crimes_violentos | durante | 1.15 (1.01–1.31) | 1.15 (1.01–1.31) | 1.07 (0.92–1.24) | 1.14 (0.94–1.39) | 1.14 (0.99–1.32) |
| 3 estádios | crimes_violentos | pos | 1.31 (1.14–1.51) | 1.31 (1.14–1.51) | 1.40 (1.21–1.61) | 1.00 (0.78–1.28) | 1.44 (1.23–1.69) |
| 3 estádios | furtos_total | durante | 1.66 (1.47–1.87) | 1.66 (1.47–1.87) | 1.58 (1.41–1.78) | 1.47 (1.16–1.86) | 1.61 (1.41–1.84) |
| 3 estádios | furtos_total | pos | 1.85 (1.60–2.13) | 1.85 (1.60–2.13) | 1.82 (1.57–2.10) | 2.05 (1.65–2.55) | 1.81 (1.52–2.15) |
| 3 estádios | roubos_total | durante | 1.08 (0.94–1.24) | 1.08 (0.94–1.24) | 1.07 (0.93–1.24) | 1.06 (0.84–1.34) | 1.08 (0.93–1.27) |
| 3 estádios | roubos_total | pos | 1.39 (1.20–1.60) | 1.39 (1.20–1.60) | 1.40 (1.21–1.62) | 1.11 (0.86–1.42) | 1.49 (1.26–1.75) |
| Allianz Parque | crimes_violentos | durante | 1.04 (0.84–1.28) | 1.04 (0.85–1.28) | 0.96 (0.77–1.20) | 1.06 (0.78–1.44) | 1.04 (0.82–1.31) |
| Allianz Parque | crimes_violentos | pos | 1.21 (1.00–1.48) | 1.21 (1.00–1.48) | 1.26 (1.03–1.55) | 1.08 (0.72–1.61) | 1.26 (1.01–1.58) |
| Allianz Parque | furtos_total | durante | 1.28 (1.05–1.55) | 1.28 (1.05–1.55) | 1.28 (1.07–1.54) | 1.24 (0.83–1.83) | 1.30 (1.09–1.56) |
| Allianz Parque | furtos_total | pos | 1.45 (1.18–1.78) | 1.45 (1.18–1.78) | 1.45 (1.18–1.79) | 1.55 (1.13–2.12) | 1.40 (1.08–1.82) |
| Allianz Parque | roubos_total | durante | 1.00 (0.81–1.23) | 1.00 (0.81–1.23) | 0.96 (0.77–1.20) | 1.04 (0.71–1.50) | 0.99 (0.79–1.24) |
| Allianz Parque | roubos_total | pos | 1.26 (1.03–1.54) | 1.26 (1.03–1.54) | 1.26 (1.03–1.55) | 1.10 (0.72–1.69) | 1.31 (1.04–1.64) |
| Morumbi | crimes_violentos | durante | 1.58 (1.20–2.09) | 1.58 (1.20–2.09) | 1.50 (1.09–2.06) | 1.38 (0.81–2.35) | 1.64 (1.21–2.23) |
| Morumbi | crimes_violentos | pos | 1.64 (1.16–2.31) | 1.64 (1.16–2.32) | 1.68 (1.17–2.40) | 0.89 (0.50–1.57) | 1.87 (1.29–2.71) |
| Morumbi | furtos_total | durante | 1.95 (1.51–2.53) | 1.95 (1.51–2.53) | 1.86 (1.45–2.39) | 1.59 (0.97–2.61) | 2.07 (1.52–2.82) |
| Morumbi | furtos_total | pos | 2.87 (2.02–4.09) | 2.87 (2.02–4.09) | 2.76 (1.93–3.95) | 4.30 (2.72–6.81) | 2.23 (1.51–3.29) |
| Morumbi | roubos_total | durante | 1.49 (1.11–2.00) | 1.49 (1.11–2.00) | 1.50 (1.09–2.07) | 1.25 (0.69–2.25) | 1.55 (1.12–2.15) |
| Morumbi | roubos_total | pos | 1.71 (1.22–2.41) | 1.71 (1.22–2.41) | 1.68 (1.17–2.40) | 1.01 (0.54–1.87) | 1.89 (1.32–2.73) |
| Neo Quimica Arena | crimes_violentos | durante | 1.06 (0.87–1.31) | 1.06 (0.87–1.31) | 1.00 (0.78–1.28) | 1.16 (0.87–1.53) | 1.01 (0.80–1.28) |
| Neo Quimica Arena | crimes_violentos | pos | 1.31 (1.04–1.67) | 1.31 (1.04–1.67) | 1.49 (1.17–1.89) | 0.98 (0.67–1.43) | 1.53 (1.15–2.05) |
| Neo Quimica Arena | furtos_total | durante | 1.94 (1.61–2.35) | 1.94 (1.61–2.35) | 1.81 (1.49–2.20) | 1.63 (1.13–2.34) | 2.12 (1.63–2.75) |
| Neo Quimica Arena | furtos_total | pos | 2.08 (1.64–2.64) | 2.08 (1.64–2.64) | 2.04 (1.60–2.60) | 1.82 (1.21–2.74) | 2.20 (1.65–2.94) |
| Neo Quimica Arena | roubos_total | durante | 0.97 (0.76–1.24) | 0.97 (0.76–1.24) | 1.00 (0.78–1.29) | 1.03 (0.73–1.45) | 0.94 (0.71–1.25) |
| Neo Quimica Arena | roubos_total | pos | 1.43 (1.12–1.82) | 1.43 (1.12–1.82) | 1.49 (1.17–1.89) | 1.15 (0.80–1.64) | 1.58 (1.17–2.14) |

**Leitura (3 estádios agregados):**
- `crimes_violentos` DURANTE: original 1.15 (p=0.035); sem conduta nula 1.07 (p=0.365); só presencial 1.14 (p=0.174); só online 1.14 (p=0.074).
- `crimes_violentos` POS: original 1.31 (p=0.000); sem conduta nula 1.40 (p=0.000); só presencial 1.00 (p=0.976); só online 1.44 (p=0.000).
- `roubos_total` DURANTE: original 1.08 (p=0.270); sem conduta nula 1.07 (p=0.348); só presencial 1.06 (p=0.612); só online 1.08 (p=0.315).
- `roubos_total` POS: original 1.39 (p=0.000); sem conduta nula 1.40 (p=0.000); só presencial 1.11 (p=0.425); só online 1.49 (p=0.000).
- `furtos_total` DURANTE: original 1.66 (p=0.000); sem conduta nula 1.58 (p=0.000); só presencial 1.47 (p=0.001); só online 1.61 (p=0.000).
- `furtos_total` POS: original 1.85 (p=0.000); sem conduta nula 1.82 (p=0.000); só presencial 2.05 (p=0.000); só online 1.81 (p=0.000).
