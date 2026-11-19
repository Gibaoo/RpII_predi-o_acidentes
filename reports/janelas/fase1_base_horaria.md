# V2 / Fase 1 — Base horária e janelas de jogo

Gerado por `scripts/32_base_horaria.py` (lê saídas de `30_eventos_horarios.py` e `31_jogos_horarios.py`). Crimes e sinistros tratados como **domínios separados** em todas as tabelas abaixo. Nenhum modelo de efeito do jogo foi estimado nesta fase — isso é a Fase 2.

## 1. Bug do fuso na base de futebol (afeta o trabalho diário)

A coluna `time` do `BR-Football-Dataset.csv` está no horário do Reino Unido (Europe/London, GMT/BST) e `date` é a data no Reino Unido. Correção: `date`+`time` → `tz_localize('Europe/London')` → `tz_convert('America/Sao_Paulo')`. Evidências (horário oficial de Brasília citado no prompt V2, conferido contra a base):

| jogo_id | mandante | visitante | competicao | data_uk | horario_uk | offset_uk_h | inicio_br |
|---|---|---|---|---|---|---|---|
| 20221113_Corinthians | Corinthians | Atletico Mineiro | Serie A | 2022-11-13 | 19:00:00 | 0.00 | 2022-11-13 16:00:00 |
| 20230924_SaoPaulo | Sao Paulo | Flamengo | Copa do Brasil | 2023-09-24 | 20:00:00 | 1.00 | 2023-09-24 16:00:00 |

- Horários UK na base (2022-2023, mandante SP capital) incluem 00:00, 00:30, 01:00, 01:30 e 01:45 — implausíveis como início em Brasília. Depois da conversão: 16:00, 21:30, 19:00, 20:00, 21:00, 18:30, 18:00, 19:30, 16:30, 20:30, 21:45, 11:00 (todos plausíveis).
- **52 de 137 jogos (38%) mudam de data**: jogos noturnos de Brasília estavam no dia seguinte.
- **`jogo_noturno` antigo (hora UK ≥ 19) errado em 108/137 jogos** (79%):

| noturno_antigo(hora UK>=19) | False | True |
|---|---|---|
| False | 2 | 52 |
| True | 56 | 27 |

- **Os "dias com 2 jogos" do pipeline antigo eram artefato do bug**: dias de jogo passam de 126 (com 11 jogos "duplos") para 137 (= 137 jogos, nenhum dia com 2 jogos em SP capital). Status dos 730 dias (linhas = antigo, colunas = corrigido):

| antigo \ corrigido | 0 | 1 |
|---|---|---|
| 0 | 556 | 48 |
| 1 | 37 | 89 |

### Horário estranho `01:24:28` (e outros com segundos ≠ 00)

Três jogos de SP capital têm segundos ≠ 00 — no conjunto inteiro da base são 419/10.296 linhas (4%), com minutos variados (:59, :29, :01…), padrão de carimbo de coleta, não de horário oficial de início. O `01:24:28` é São Paulo × Flamengo, Copa do Brasil 2022 (placar 1×3 na base), que vira 21:24:28 em Brasília. Sem fonte oficial verificada para o horário de início, os 3 foram **arredondados para os 30 min mais próximos e marcados `horario_aproximado`** (impacto pequeno: a regra do ponto médio desloca no máximo 1 hora de janela, e só se o erro real for > 30 min).

| jogo_id | competicao | mandante | visitante | gols_mandante | gols_visitante | data_uk | horario_uk | inicio_br_bruto | inicio_br |
|---|---|---|---|---|---|---|---|---|---|
| 20220807_Palmeiras | Serie A | Palmeiras | Goias | 3.00 | 0.00 | 2022-08-07 | 19:50:28 | 2022-08-07 15:50:28 | 2022-08-07 16:00:00 |
| 20220824_SaoPaulo | Copa do Brasil | Sao Paulo | Flamengo | 1.00 | 3.00 | 2022-08-25 | 01:24:28 | 2022-08-24 21:24:28 | 2022-08-24 21:30:00 |
| 20230930_SaoPaulo | Serie A | Sao Paulo | Corinthians | 2.00 | 1.00 | 2023-09-30 | 22:30:36 | 2023-09-30 18:30:36 | 2023-09-30 18:30:00 |

### Checagem: GLM diário da Etapa 7 com as datas corrigidas

Mesma especificação da Etapa 7 (`y ~ jogo + C(dia_semana) + feriado + C(mes)`, Poisson, HC1, mesmas exclusões), trocando só a data do jogo. `p_BH_dominio` = BH por domínio (regra V2); a coluna `p_BH_etapa7` (família única, como na Etapa 7) está no CSV.

| familia | desfecho | RR_antigo | p_antigo | RR_corrigido | p_corrigido | p_BH_dominio_corrigido | RR_completo | p_completo | p_BH_dominio_completo |
|---|---|---|---|---|---|---|---|---|---|
| acidente | acidentes_com_vitima | 1.015 | 0.333 | 1.012 | 0.443 | 0.617 | 1.023 | 0.082 | 0.205 |
| acidente | acidentes_fatais | 1.146 | 0.063 | 1.164 | 0.025 | 0.124 | 1.058 | 0.333 | 0.333 |
| acidente | acidentes_total | 1.002 | 0.902 | 1.004 | 0.774 | 0.774 | 1.016 | 0.223 | 0.333 |
| acidente | atropelamentos | 1.035 | 0.315 | 1.046 | 0.165 | 0.412 | 1.028 | 0.311 | 0.333 |
| acidente | colisoes | 1.010 | 0.556 | 1.012 | 0.493 | 0.617 | 1.037 | 0.019 | 0.093 |
| crime | crimes_totais | 1.020 | 0.197 | 1.021 | 0.169 | 0.521 | 1.029 | 0.008 | 0.024 |
| crime | crimes_violentos | 1.009 | 0.399 | 1.009 | 0.412 | 0.618 | 1.014 | 0.103 | 0.207 |
| crime | furtos_total | 1.025 | 0.249 | 1.029 | 0.174 | 0.521 | 1.040 | 0.006 | 0.024 |
| crime | homicidios_dolosos | 0.907 | 0.286 | 1.049 | 0.595 | 0.675 | 0.981 | 0.802 | 0.802 |
| crime | lesao_corporal_dolosa | 1.015 | 0.462 | 1.020 | 0.298 | 0.597 | 1.022 | 0.170 | 0.255 |
| crime | roubos_total | 1.009 | 0.471 | 1.005 | 0.675 | 0.675 | 1.012 | 0.231 | 0.277 |

**Leitura:** o nulo diário se mantém — 0 desfecho(s) significativo(s) após BH por domínio com as datas corrigidas. Sem correção, p < 0,05 só em: acidentes_fatais. O resíduo já conhecido de `acidentes_fatais` fica um pouco mais forte (RR 1.164, p = 0.025; p_BH = 0.124) — continua não robusto à correção múltipla, mas é o candidato a olhar com atenção na Fase 2. `homicidios_dolosos` troca de sinal (0,91 → 1,05), ambos ns.

**Com o calendário completo (colunas `_completo`, seção 1b), o nulo diário deixa de ser total:** `crimes_totais` RR 1.029 (p = 0.008, p_BH = 0.024); `furtos_total` RR 1.040 (p = 0.006, p_BH = 0.024). Ou seja, parte do nulo antigo vinha de dias de Paulistão/Libertadores/Sul-Americana classificados como "sem jogo" (diluição + jan–mar sem nenhum jogo). É uma checagem no grão diário com a especificação simples da Etapa 7, **não** a estimativa do projeto: a Fase 2 testa isso direito (janelas, EF hora × dia da semana, placebo).

## 1b. Calendário completo: Paulistão, Libertadores, Sul-Americana e Recopa

Aprovado pelo usuário (item opcional do prompt V2, ampliado para Sul-Americana e Recopa). Gerado por `scripts/31a_jogos_complementares.py` → `data/bronze/jogos_complementares.csv`.

**Fonte e verificação:**
- Primária: páginas de temporada de cada clube na Wikipédia em inglês (ex. *2022 SE Palmeiras season*), onde cada partida é um *football box* com data, **horário com fuso explícito** (`{{UTZ|21:00|-3}}` = UTC−3 = Brasília — confirma que o horário da fonte está em Brasília), mandante, cidade, estádio e link da súmula. As páginas de **edição** (ex. Paulistão 2022 na pt.wikipedia) trazem a fase de grupos só como tabela cruzada de placares, sem data/horário/estádio, por isso foram usadas como **conferência** onde têm football box. A tabela oficial da FPF exige desafio anti-robô (Cloudflare) e não foi usada.
- `fonte_jogo` = permalink da revisão exata (`...&oldid=REVID`); snapshots do wikitext e manifesto em `data/bronze/wikipedia/`.
- 33 jogos conferidos contra páginas de edição (Libertadores, Sul-Americana, Recopa, mata-mata do Paulistão 2023): **0 divergências de horário**. Data conferida com o link da súmula do ge em todos que o têm: 0 divergências.
- Segunda fonte (busca manual, URL em `fonte_extra`) para os casos suspeitos: mandos fora do estádio habitual e o jogo de Série A ausente da base.
- Jogos sem horário confirmado: 0 (a regra os deixaria com flag e fora da análise principal).

**A mesma fonte conferiu os 137 jogos da base original:** 137/137 com o horário convertido (fuso corrigido) **idêntico** ao da Wikipédia — confirmação independente da correção do fuso. Mas **7 dos 137 foram mandos fora da capital** (Arena Barueri e Vila Belmiro, por shows no Allianz/Morumbi) — saem da `janela` e passam para `janela_fora_capital` (seção 1d), junto com a final da Sul-Americana 2022 (campo neutro, Córdoba). Também apareceu 1 jogo de Série A que o BR-Football-Dataset não tem (Palmeiras × Bragantino, 13/05/2023, Allianz Parque — conferido em 2ª fonte); entrou no calendário.

Mandos dos 3 clubes da capital que NÃO entram na `janela` (estão em `janela_fora_capital`):

| jogo_id | competicao | mandante | visitante | estadio | cidade | motivo_exclusao | na_base_original |
|---|---|---|---|---|---|---|---|
| 20220423_Palmeiras | Serie A | Palmeiras | Corinthians | Arena Barueri | Barueri | mando_fora_da_capital | True |
| 20220430_Palmeiras | Copa do Brasil | Palmeiras | Juazeirense | Arena Barueri | Barueri | mando_fora_da_capital | True |
| 20220512_SaoPaulo | Copa do Brasil | Sao Paulo | EC Juventude | Arena Barueri | Barueri | mando_fora_da_capital | True |
| 20221001_SaoPaulo | Copa Sul-Americana | Sao Paulo | Independiente del Valle | Estadio Mario Alberto Kempes | Córdoba | campo_neutro_fora_do_estado | False |
| 20231008_Palmeiras | Serie A | Palmeiras | Santos | Arena Barueri | Barueri | mando_fora_da_capital | True |
| 20231104_Palmeiras | Serie A | Palmeiras | Athletico Paranaense | Arena Barueri | Barueri | mando_fora_da_capital | True |
| 20231108_SaoPaulo | Serie A | Sao Paulo | Bragantino | Vila Belmiro | Santos | mando_fora_da_capital | True |
| 20231111_Palmeiras | Serie A | Palmeiras | Internacional | Arena Barueri | Barueri | mando_fora_da_capital | True |

Jogos na capital em estádio não habitual (a análise espacial usa o estádio real):

| jogo_id | competicao | mandante | visitante | estadio | na_base_original |
|---|---|---|---|---|---|
| 20230128_Santos | Campeonato Paulista | Santos | Ferroviaria | Estádio do Canindé | False |
| 20230204_Palmeiras | Campeonato Paulista | Palmeiras | Santos | Morumbi | False |
| 20230313_SaoPaulo | Campeonato Paulista | Sao Paulo | Agua Santa | Allianz Parque | False |
| 20230420_Palmeiras | Copa Libertadores | Palmeiras | Cerro Porteno | Morumbi | False |

Jogos por competição (`na_base_original` = veio do BR-Football-Dataset):

| competicao | na_base_original | incluir_analise | n |
|---|---|---|---|
| Campeonato Paulista | False | True | 49 |
| Copa Libertadores | False | True | 20 |
| Copa Sul-Americana | False | False | 1 |
| Copa Sul-Americana | False | True | 15 |
| Copa do Brasil | True | False | 2 |
| Copa do Brasil | True | True | 22 |
| Recopa Sul-Americana | False | True | 1 |
| Serie A | False | True | 1 |
| Serie A | True | False | 5 |
| Serie A | True | True | 108 |

**Total analisável: 216 jogos** (130 da base original + 86 novos). Por mês:

| mes | Campeonato Paulista | Copa Libertadores | Copa Sul-Americana | Copa do Brasil | Recopa Sul-Americana | Serie A | total |
|---|---|---|---|---|---|---|---|
| 2022-01 | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| 2022-02 | 8 | 0 | 0 | 0 | 0 | 0 | 8 |
| 2022-03 | 13 | 0 | 0 | 1 | 1 | 0 | 15 |
| 2022-04 | 1 | 3 | 1 | 0 | 0 | 3 | 8 |
| 2022-05 | 0 | 3 | 2 | 1 | 0 | 8 | 14 |
| 2022-06 | 0 | 1 | 0 | 2 | 0 | 9 | 12 |
| 2022-07 | 0 | 1 | 1 | 2 | 0 | 8 | 12 |
| 2022-08 | 0 | 2 | 1 | 2 | 0 | 7 | 12 |
| 2022-09 | 0 | 1 | 1 | 1 | 0 | 6 | 9 |
| 2022-10 | 0 | 0 | 0 | 1 | 0 | 9 | 10 |
| 2022-11 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| 2023-01 | 8 | 0 | 0 | 0 | 0 | 0 | 8 |
| 2023-02 | 10 | 0 | 0 | 0 | 0 | 0 | 10 |
| 2023-03 | 5 | 0 | 0 | 0 | 0 | 0 | 5 |
| 2023-04 | 1 | 2 | 1 | 3 | 0 | 4 | 11 |
| 2023-05 | 0 | 1 | 0 | 2 | 0 | 8 | 11 |
| 2023-06 | 0 | 3 | 2 | 1 | 0 | 5 | 11 |
| 2023-07 | 0 | 0 | 1 | 4 | 0 | 7 | 12 |
| 2023-08 | 0 | 2 | 4 | 1 | 0 | 6 | 13 |
| 2023-09 | 0 | 0 | 1 | 1 | 0 | 7 | 9 |
| 2023-10 | 0 | 1 | 0 | 0 | 0 | 7 | 8 |
| 2023-11 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| 2023-12 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| total | 49 | 20 | 15 | 22 | 1 | 109 | 216 |

- **Jan–mar (2 anos): horas de jogo (PRÉ+DURANTE+PÓS) passam de 6 para 294**; dias de jogo de 1 para 49. A violação de positividade de jan–fev (Etapa 20) deixa de existir.
- **Dias com 2 jogos em SP capital: 0** — mesmo com 216 jogos, nunca há 2 mandos na capital no mesmo dia; a regra de prioridade de janelas segue implementada, mas não é acionada.
- Horário de início dos jogos novos: 21:30 (28), 18:30 (15), 16:00 (10), 19:00 (8), 21:00 (6), 21:35 (5), 19:15 (4), 20:30 (3), 20:00 (2), 19:30 (2), 15:00 (1), 11:00 (1), 21:40 (1).

Na Fase 2 a análise principal usa o calendário completo (`janela`) e uma robustez roda só com a base original (`janela_base_original` — os 130 jogos do BR-Football-Dataset em SP capital, já com fuso e estádio corrigidos), para medir quanto a falta desses jogos mudava o resultado.

## 1c. Santos como 4º time monitorado

Decisão do usuário (substitui "Santos fica de fora como mandante"): Corinthians, Palmeiras, São Paulo e Santos. Páginas *2022/2023 Santos FC season* (Wikipédia em inglês) baixadas no mesmo padrão (permalink `oldid` em `fonte_jogo`). Nelas a data vem sem ano e o fuso como `[[UTC-03:00]]` — o parser foi ajustado (ano da própria página). O Santos foi **mandante na capital 1 vez** (Santos × Ferroviária, Paulistão, 28/01/2023, Canindé) — entra na `janela`. Seus jogos na capital como visitante já estavam. Os demais jogos do Santos (Vila Belmiro e fora) entram em `janela_fora_capital`.

## 1d. Jogos fora da capital (`janela_fora_capital`)

Todos os jogos oficiais dos 4 times disputados fora da capital: fora de casa dos 3 clubes, Santos na Vila Belmiro e em outros lugares, os mandos da capital em Barueri/Vila Belmiro e jogos no exterior. Mede o efeito de assistir pela TV/em bares na cidade. Coluna separada e **não exclusiva** de `janela` (uma hora pode estar nas duas). Mesma regra de janela (ponto médio hh:30, linha do tempo contínua).

- **301 jogos** (301 com horário confirmado). Por competição:

| competicao | n |
|---|---|
| Campeonato Paulista | 48 |
| Copa Libertadores | 20 |
| Copa Sul-Americana | 30 |
| Copa do Brasil | 30 |
| Recopa Sul-Americana | 1 |
| Serie A | 171 |
| Supercopa do Brasil | 1 |

Jogos por time monitorado envolvido (um jogo entre dois monitorados conta para os dois): Santos 115, Palmeiras 67, Sao Paulo 66, Corinthians 64.
- Região Metropolitana de SP (`fora_capital_rmsp`): 17 jogos (Barueri, Santo André, São Bernardo, Diadema…); mandos dos clubes da capital fora dela: 9.
- **Conversão de fuso** (horário local → Brasília com o fuso indicado na própria página: `inicio_br = hora_local + (−3 − offset)`). As páginas usam duas convenções: a do Corinthians dá hora local com fuso local (ex. La Paz `20:30 UTC−4` → 21:30), as de Palmeiras/São Paulo/Santos já dão a hora de Brasília marcada `UTC−3`. Offsets encontrados: UTC-3 (296), UTC-5 (3), UTC-4 (2).
  - vs BR-Football-Dataset (UK → Brasília, fonte independente): 200 jogos pareados, 200 batem (≤15 min).
  - vs páginas de edição Libertadores/Sul-Americana (hora local + fuso local): 40 jogos pareados, 40 batem (≤15 min).
  - Na 1ª passada houve 5 divergências; uma 3ª fonte confirmou a fonte independente em todas e o horário foi corrigido com a URL em `horario_corrigido_fonte` (Goiás × São Paulo 18/10/2023 21h30; Santos × Cuiabá 06/11/2023 21h; Bahia × São Paulo 29/11/2023 20h; Santos × Newell's 06/06/2023 21h30; Santos × Corinthians 21/06/2023 20h, conflito entre as páginas do Santos e do Corinthians).
- Horas: PRÉ 453, DURANTE 541, PÓS 466. Jogos simultâneos fora da capital (`n_jogos_fora_simultaneos`): 1 jogo(s): 1170 h, 2 jogo(s): 238 h, 3 jogo(s): 48 h, 4 jogo(s): 4 h; times em `times_fora_capital`.

Sobreposição das duas categorias (horas; linhas = `janela4` da capital, colunas = `janela_fora_capital`):

| janela4 | durante | nenhum | pos | pre |
|---|---|---|---|---|
| durante | 39 | 249 | 78 | 66 |
| fora | 338 | 15193 | 342 | 351 |
| pos | 71 | 315 | 34 | 12 |
| pre | 93 | 303 | 12 | 24 |

- **Controle da Fase 2 = `hora_sem_jogo`**: 11520 horas sem nenhuma janela de jogo dos 4 times (nem na capital nem fora) e em data sem jogo na capital.

## 1e. Público dos jogos na capital

- Integrado para os 216 jogos da `janela` a partir das mesmas páginas (público **total** do estádio). Cobertura: 216/216; ausente vira NaN, nunca zero.
- Status: `ok` 201, `capacidade_restrita` 14, `portoes_fechados` 1. `portoes_fechados` = Corinthians × Vasco Da Gama RJ (2023-07-29), punição por cantos homofóbicos (nota da própria página) — público 0 real, não ausente. `capacidade_restrita` = jogos de 23/01 a 09/03/2022 (teto de 70% do governo estadual; a página só anota nos jogos do Corinthians, a regra foi aplicada a todos com a fonte em `publico_restricao_fonte`).
- Distribuição (status ok): mediana 39.337, P25 33.250, P75 42.797, mín 11.573, máx 63.077.
- Fora da capital o público do estádio não entra na análise (fica só como registro no bronze).

**Conferência com 2ª fonte** (amostra estratificada de 20 jogos, 7 por clube da capital + o jogo do Santos, semente fixa; tabela da FPF e fbref bloqueiam acesso automatizado (não contornado), borderô da CBF não testado — usadas fichas técnicas da imprensa, que reproduzem o borderô): **18 encontrados, 17 idênticos**, 1 com diferença de 0,6% (Palmeiras × Grêmio: Wikipédia = ESPN 37.532; Gazeta 37.752), 2 não encontrados. Observação: a Wikipédia usa o público **total**; algumas bases (ESPN) usam o pagante (0,4–1% menor). Tabela em `data/bronze/publico_conferencia_amostra.csv`.

## 1f. Jogos de grande público na capital sem os 4 times (verificação pedida — NADA incluído)

Busca na web por eventos de futebol com grande público nos estádios da capital em 2022–2023 sem o time principal masculino dos 4 clubes. Candidatos encontrados (não é uma lista exaustiva; aguardam decisão):

| evento_id | data_br | inicio_br | evento | local | publico | decisao_usuario | fonte_horario |
|---|---|---|---|---|---|---|---|
| copinha_2022 | 2022-01-25 | 2022-01-25 10:00 | Final Copa SP de Futebol Junior (sub-20): Palmeiras x Santos | Allianz Parque | nao encontrado | flag + fora da amostra principal (robustez com as horas de volta) | https://www.goal.com/br/not%C3%ADcias/final-da-copinha-2022-data-horario-estadio-e-mais-da-decisao/blt6a0ebd09a838b0db |
| feminino_2022 | 2022-09-24 | 2022-09-24 14:00 | Final Brasileirao Feminino (volta): Corinthians x Internacional | Neo Quimica Arena | 41070 | flag + fora da amostra principal (robustez com as horas de volta) | https://www.dci.com.br/esporte/brasileirao/final-feminina-corinthians-hoje-onde-vai-passar-e-horario-24-09-2022/ |
| copinha_2023 | 2023-01-25 | 2023-01-25 15:30 | Final Copa SP de Futebol Junior (sub-20): Palmeiras x America-MG | Caninde | nao encontrado | flag + fora da amostra principal (robustez com as horas de volta) | https://www.gazetaesportiva.com/campeonatos/copa-sao-paulo/palmeiras-x-america-mg-final-da-copinha-sera-no-caninde-veja-data-e-horario/ |
| feminino_2023 | 2023-09-10 | 2023-09-10 16:00 | Final Brasileirao Feminino (volta): Corinthians x Ferroviaria | Neo Quimica Arena | 42566 | flag + fora da amostra principal (robustez com as horas de volta) | https://olhardigital.com.br/2023/09/10/internet-e-redes-sociais/corinthians-x-ferroviaria-onde-assistir-horario-e-escalacoes-da-final-do-brasileirao-feminino/ |

Não foram encontrados jogos da seleção brasileira (masculina) na capital nesses anos. As finais da Copinha são de times sub-20 de clubes monitorados.

**Decisão do usuário:** não são tratamento nem controle. As horas PRÉ/DURANTE/PÓS desses 4 eventos (horário de início confirmado na imprensa, URL em `fonte_horario`) ficam com `excluir_evento_grande_publico = True` (24 horas) e saem da amostra principal da Fase 2; robustez com elas de volta.

## 2. Qualidade da hora — CRIMES (SSP)

Hora de `HORA_OCORRENCIA_BO`; `NULL`/vazio = sem hora. Formatos aceitos `HH:MM`, `HH:MM:SS` e o artefato de célula do Excel `1900-01-01 HH:MM:SS` (hora válida). Datas no campo hora (ex. `2000-06-01 00:00:00`) = formato inválido → sem hora (20 registros, lista em `fase1/tabelas/hora_formatos_invalidos.csv`). `razao_hora0_vs_vizinhas` < 1,2 em todos os tipos → **00:00 não é placeholder de hora desconhecida**.

| tipo | n | n_sem_hora | pct_sem_hora | pct_formato_invalido | pct_minuto_00 | pct_minuto_00_ou_30 | pct_minuto_multiplo_5 | pct_meia_noite_exata | razao_hora0_vs_vizinhas |
|---|---|---|---|---|---|---|---|---|---|
| crime_todos | 974737 | 330219 | 33.88 | 0.00 | 32.90 | 53.13 | 86.47 | 0.72 | 0.83 |
| crimes_violentos | 377402 | 32570 | 8.63 | 0.00 | 28.76 | 50.25 | 88.06 | 0.45 | 0.74 |
| lesao_corporal_dolosa | 65418 | 5623 | 8.60 | 0.00 | 35.82 | 56.19 | 82.14 | 0.65 | 0.84 |
| roubos_total | 305029 | 24828 | 8.14 | 0.00 | 27.19 | 48.99 | 89.56 | 0.40 | 0.72 |
| furtos_total | 561909 | 296710 | 52.80 | 0.00 | 40.01 | 59.03 | 86.05 | 1.14 | 0.99 |

Por arquivo (os 4 semestres) — números do prompt confirmados e estáveis entre arquivos:

| tipo | recorte | n | pct_sem_hora | pct_minuto_00 | pct_minuto_00_ou_30 |
|---|---|---|---|---|---|
| crime_todos | arquivo_2022_jan_jun | 227670 | 34.34 | 33.16 | 53.77 |
| crime_todos | arquivo_2022_jul_dez | 247148 | 33.13 | 32.93 | 53.11 |
| crime_todos | arquivo_2023_jan_jun | 248373 | 33.53 | 32.79 | 53.01 |
| crime_todos | arquivo_2023_jul_dez | 251546 | 34.54 | 32.76 | 52.68 |
| crimes_violentos | arquivo_2022_jan_jun | 91631 | 8.28 | 28.71 | 50.72 |
| crimes_violentos | arquivo_2022_jul_dez | 99250 | 8.53 | 28.60 | 49.80 |
| crimes_violentos | arquivo_2023_jan_jun | 94117 | 8.61 | 28.91 | 50.33 |
| crimes_violentos | arquivo_2023_jul_dez | 92404 | 9.10 | 28.85 | 50.16 |
| lesao_corporal_dolosa | arquivo_2022_jan_jun | 14904 | 8.46 | 35.15 | 55.57 |
| lesao_corporal_dolosa | arquivo_2022_jul_dez | 15441 | 8.18 | 34.88 | 54.63 |
| lesao_corporal_dolosa | arquivo_2023_jan_jun | 16744 | 8.91 | 36.31 | 56.55 |
| lesao_corporal_dolosa | arquivo_2023_jul_dez | 18329 | 8.77 | 36.72 | 57.67 |
| roubos_total | arquivo_2022_jan_jun | 75084 | 7.87 | 27.42 | 49.87 |
| roubos_total | arquivo_2022_jul_dez | 81887 | 8.22 | 27.40 | 48.97 |
| roubos_total | arquivo_2023_jan_jun | 75674 | 7.93 | 27.20 | 48.94 |
| roubos_total | arquivo_2023_jul_dez | 72384 | 8.55 | 26.69 | 48.15 |
| furtos_total | arquivo_2022_jan_jun | 129713 | 54.29 | 41.09 | 60.30 |
| furtos_total | arquivo_2022_jul_dez | 141570 | 51.73 | 39.98 | 59.27 |
| furtos_total | arquivo_2023_jan_jun | 143099 | 52.35 | 39.72 | 58.87 |
| furtos_total | arquivo_2023_jul_dez | 147527 | 52.97 | 39.41 | 57.84 |

- **Furtos: ~53% sem hora** (a vítima percebe depois); roubos ~8%, lesão corporal dolosa ~9%, `crimes_violentos` ~9% (puxado por roubos). O prompt citava ~7% para lesão numa amostra do 2º sem/2023; na base completa é 8,6%.
- **Arredondamento**: ~33% no minuto :00 e ~53% em :00/:30 → grão de 1 hora (não menor), como previsto. Arredondamento para a hora cheia pode puxar registros de hh:59 para hh+1:00 — viés de no máximo 1 hora, simétrico entre dias com e sem jogo.
- `DESCR_PERIODO` dos registros sem hora (turno aproximado, não usado nas contagens horárias; fica para robustez):

| tipo | periodo | pct_dos_sem_hora |
|---|---|---|
| crimes_violentos | A NOITE | 30.63 |
| crimes_violentos | PELA MANHÃ | 18.37 |
| crimes_violentos | DE MADRUGADA | 18.17 |
| crimes_violentos | A TARDE | 17.60 |
| crimes_violentos | EM HORA INCERTA | 13.88 |
| crimes_violentos | (NULO) | 1.34 |
| furtos_total | A TARDE | 21.79 |
| furtos_total | A NOITE | 21.35 |
| furtos_total | PELA MANHÃ | 20.41 |
| furtos_total | (NULO) | 19.71 |
| furtos_total | DE MADRUGADA | 12.62 |
| furtos_total | EM HORA INCERTA | 4.12 |

## 3. Qualidade da hora — SINISTROS (Infosiga)

| tipo | n | n_sem_hora | pct_sem_hora | pct_formato_invalido | pct_minuto_00 | pct_minuto_00_ou_30 | pct_minuto_multiplo_5 | pct_meia_noite_exata | razao_hora0_vs_vizinhas |
|---|---|---|---|---|---|---|---|---|---|
| acidentes_total | 90829 | 92 | 0.10 | 0.00 | 2.46 | 4.74 | 23.02 | 0.09 | 1.05 |
| acidentes_com_vitima | 58856 | 92 | 0.16 | 0.00 | 2.73 | 5.36 | 24.42 | 0.07 | 1.10 |
| atropelamentos | 12152 | 38 | 0.31 | 0.00 | 2.35 | 4.83 | 23.33 | 0.06 | 1.02 |

| tipo | recorte | n | pct_sem_hora | pct_minuto_00 | pct_minuto_00_ou_30 |
|---|---|---|---|---|---|
| acidentes_total | arquivo_2022 | 44317 | 0.13 | 2.49 | 4.78 |
| acidentes_total | arquivo_2023 | 46512 | 0.07 | 2.43 | 4.70 |
| acidentes_com_vitima | arquivo_2022 | 28454 | 0.20 | 2.78 | 5.45 |
| acidentes_com_vitima | arquivo_2023 | 30402 | 0.11 | 2.68 | 5.28 |
| atropelamentos | arquivo_2022 | 5803 | 0.41 | 2.21 | 4.53 |
| atropelamentos | arquivo_2023 | 6349 | 0.22 | 2.48 | 5.10 |

- Hora quase completa (0,1% sem hora) e **sem arredondamento relevante** (2,5% no :00, perto dos 1,7% esperados ao acaso) — a hora do sinistro é muito mais confiável que a do crime.
- O problema do sinistro é outro: **contagens horárias pequenas** (ver seção 6).

## 4. Conferência com o pipeline diário

Total por dia (com + sem hora) da extração horária vs `data/silver/*_diario_sp.csv` (`02_limpeza.py`): mesmo filtro e mesmo grão.

| dominio | tipo | dias | dias_divergentes | max_abs_diff | total_novo | total_diario |
|---|---|---|---|---|---|---|
| crimes | crime_todos | 730 | 0 | 0 | 974737 | 974737 |
| crimes | crimes_violentos | 730 | 0 | 0 | 377402 | 377402 |
| crimes | lesao_corporal_dolosa | 730 | 0 | 0 | 65418 | 65418 |
| crimes | roubos_total | 730 | 0 | 0 | 305029 | 305029 |
| crimes | furtos_total | 730 | 0 | 0 | 561909 | 561909 |
| sinistros | acidentes_total | 730 | 0 | 0 | 90829 | 90829 |
| sinistros | acidentes_com_vitima | 730 | 0 | 0 | 58856 | 58856 |
| sinistros | atropelamentos | 730 | 0 | 0 | 12152 | 12152 |

## 5. Base horária `data/gold/fato_hora_sp.csv`

- 17,520 linhas (1 = 1 hora local, 2022-01-01 00h → 2023-12-31 23h), 74 colunas; dicionário em `data/gold/fato_hora_sp_dicionario.csv`.
- Contagens por hora **só com registros que têm hora**; os sem hora ficam em `sem_hora_<tipo>` (diário, repetido nas 24 linhas do dia) e `total_dia_<tipo>` (= silver diário).
- Calendário (`calendario_sp.csv`): hora do dia, dia da semana, mês, feriado, véspera, férias (= férias escolares ou recesso SME). Clima horário INMET A701 (UTC−3): `chuva_mm`, `temp_c`. Horas sem leitura: chuva 649 (3.7%), temperatura 215 (1.2%). Principais lacunas: sensor de chuva fora em 25/08–11/09/2023 (432 h); estação sem leitura em 27/11/2023; as 3 últimas horas de 2023-12-31 caem no arquivo INMET de 2024, ausente (dia já censurado); o resto são falhas horárias esparsas. NaN fica NaN (não zero) — a Fase 2 decide entre excluir ou imputar.
- Exclusões por domínio (flags, linhas mantidas): `excluir_crime` = 2023-12-30/31 (censura) + 2022-06-19 (lote de furtos — 2.633 furtos, só 17% com hora, então o lote cai quase todo em `sem_hora_furtos_total`); `excluir_sinistro` = 2023-12-30/31 + 2022-01-17 e 2023-08-07 (lacunas Infosiga).

### Regras de classificação da janela

1. Linha do tempo contínua, não por dia: s = início (Brasília); PRÉ = [s−2h, s), DURANTE = [s, s+2h), PÓS = [s+2h, s+4h). Um jogo às 21:30 tem PÓS até 01:30 do dia seguinte.
2. Cada hora [hh:00, hh+1) entra na janela que contém o seu **ponto médio hh:30**. `hora_relativa` = ⌊(hh:30 − s)/1h⌋, de −6 a +12 → PRÉ = {−2,−1}, DURANTE = {0,1}, PÓS = {2,3}. Ex.: jogo 21:30 → PRÉ 19h–20h, DURANTE 21h–22h, PÓS 23h–00h; jogo 21:45 → PRÉ 20h–21h, DURANTE 22h–23h, PÓS 00h–01h.
3. Hora reivindicada por 2 jogos: prioridade DURANTE > PÓS > PRÉ (empate: jogo mais próximo), flag `jogo_duplo`.
4. FORA separado em `fora_dia_jogo` (mesma data de Brasília do jogo, fora das 3 janelas) e `dia_sem_jogo`.

Resultado (calendário completo): 216/216 jogos com exatamente 2 horas em cada janela; `jogo_duplo` = 0 horas. Horas por janela (calendário completo vs só a base original, coluna `janela_base_original`, para a robustez da Fase 2):

| janela | completo | base_original |
|---|---|---|
| dia_sem_jogo | 12285 | 14376 |
| fora_dia_jogo | 3939 | 2364 |
| pre | 432 | 260 |
| durante | 432 | 260 |
| pos | 432 | 260 |

- `hora_sem_jogo` (controle da Fase 2: nenhuma janela de jogo dos 4 times, nem na capital nem fora, e data sem jogo na capital) = 11520 horas.

- 51 horas de PÓS caem na madrugada do dia seguinte (data sem jogo).
- 1112 horas classificadas como `dia_sem_jogo` estão a +4…+12 h de um jogo da noite anterior (transbordamento para o dia seguinte). Ficam no grupo de comparação no modelo de janelas, mas o event study da Fase 2 (até +12) as isola via `hora_relativa`.

## 6. Escala das contagens horárias (motiva a definição de pico da Fase 2)

Média bruta por hora e % de horas com zero, por janela (sem controle nenhum — **não é estimativa de efeito**: as janelas caem em horários com nível próprio, o que a Fase 2 controla com EF hora × dia da semana).

**CRIMES**

| tipo | janela | n_horas | media_por_hora | pct_horas_zero | p50 | p90 |
|---|---|---|---|---|---|---|
| crimes_violentos | dia_sem_jogo | 12237 | 19.74 | 0.08 | 18.00 | 35.00 |
| crimes_violentos | durante | 430 | 29.25 | 0.00 | 28.00 | 45.00 |
| crimes_violentos | fora_dia_jogo | 3921 | 16.95 | 0.08 | 16.00 | 27.00 |
| crimes_violentos | pos | 430 | 27.90 | 0.00 | 28.00 | 43.00 |
| crimes_violentos | pre | 430 | 26.39 | 0.00 | 24.00 | 44.00 |
| lesao_corporal_dolosa | dia_sem_jogo | 12237 | 3.32 | 8.61 | 3.00 | 6.00 |
| lesao_corporal_dolosa | durante | 430 | 4.54 | 2.09 | 4.00 | 8.00 |
| lesao_corporal_dolosa | fora_dia_jogo | 3921 | 3.32 | 9.69 | 3.00 | 7.00 |
| lesao_corporal_dolosa | pos | 430 | 4.77 | 2.56 | 5.00 | 9.00 |
| lesao_corporal_dolosa | pre | 430 | 4.54 | 1.86 | 4.00 | 8.00 |
| roubos_total | dia_sem_jogo | 12237 | 16.15 | 0.20 | 14.00 | 30.00 |
| roubos_total | durante | 430 | 24.37 | 0.00 | 24.00 | 39.00 |
| roubos_total | fora_dia_jogo | 3921 | 13.35 | 0.31 | 13.00 | 22.00 |
| roubos_total | pos | 430 | 22.74 | 0.00 | 22.00 | 36.00 |
| roubos_total | pre | 430 | 21.50 | 0.00 | 19.00 | 38.00 |
| furtos_total | dia_sem_jogo | 12237 | 15.33 | 0.00 | 15.00 | 25.00 |
| furtos_total | durante | 430 | 15.91 | 0.00 | 15.00 | 24.00 |
| furtos_total | fora_dia_jogo | 3921 | 14.37 | 0.00 | 13.00 | 24.00 |
| furtos_total | pos | 430 | 13.14 | 0.00 | 13.00 | 19.00 |
| furtos_total | pre | 430 | 19.13 | 0.00 | 18.00 | 29.00 |

**SINISTROS**

| tipo | janela | n_horas | media_por_hora | pct_horas_zero | p50 | p90 |
|---|---|---|---|---|---|---|
| acidentes_total | dia_sem_jogo | 12189 | 5.17 | 6.44 | 5.00 | 10.00 |
| acidentes_total | durante | 432 | 6.09 | 0.46 | 6.00 | 11.00 |
| acidentes_total | fora_dia_jogo | 3939 | 4.95 | 6.75 | 5.00 | 9.00 |
| acidentes_total | pos | 432 | 5.53 | 3.47 | 5.00 | 10.00 |
| acidentes_total | pre | 432 | 7.12 | 0.46 | 7.00 | 12.00 |
| acidentes_com_vitima | dia_sem_jogo | 12189 | 3.35 | 11.03 | 3.00 | 7.00 |
| acidentes_com_vitima | durante | 432 | 3.74 | 3.24 | 4.00 | 6.00 |
| acidentes_com_vitima | fora_dia_jogo | 3939 | 3.26 | 10.97 | 3.00 | 7.00 |
| acidentes_com_vitima | pos | 432 | 3.34 | 9.26 | 3.00 | 7.00 |
| acidentes_com_vitima | pre | 432 | 4.34 | 3.01 | 4.00 | 7.00 |
| atropelamentos | dia_sem_jogo | 12189 | 0.69 | 55.89 | 0.00 | 2.00 |
| atropelamentos | durante | 432 | 0.83 | 48.15 | 1.00 | 2.00 |
| atropelamentos | fora_dia_jogo | 3939 | 0.62 | 58.39 | 0.00 | 2.00 |
| atropelamentos | pos | 432 | 0.77 | 53.24 | 0.00 | 2.00 |
| atropelamentos | pre | 432 | 1.10 | 37.73 | 1.00 | 3.00 |

- Crimes: `crimes_violentos` tem dezenas de registros por hora; `lesao_corporal_dolosa` já é pequena por hora.
- Sinistros: `acidentes_com_vitima` tem poucos eventos por hora e `atropelamentos` é zero na maioria das horas → pico horário instável; testar o pico na soma da janela de 2 h (prompt, Fase 2).

## 7. Teste de seleção: a falta de hora depende do dia de jogo?

GLM binomial diário `(sem_hora, com_hora) ~ dia_de_jogo + C(dia_semana) + C(mes) + C(ano) + feriado + ferias`, erros HC1, dias excluídos por domínio; BH por domínio. Fisher bruto ao lado.

**Calendário completo (principal):**

| dominio | tipo | n_dias | pct_sem_hora_dia_jogo | pct_sem_hora_sem_jogo | OR_ajustado | IC95_lo | IC95_hi | p_ajustado | p_BH_dominio | fisher_p_bruto |
|---|---|---|---|---|---|---|---|---|---|---|
| crimes | crimes_violentos | 727 | 8.736 | 8.574 | 1.018 | 0.988 | 1.049 | 0.248 | 0.330 | 0.106 |
| crimes | lesao_corporal_dolosa | 727 | 8.694 | 8.552 | 1.078 | 1.004 | 1.157 | 0.039 | 0.154 | 0.548 |
| crimes | roubos_total | 727 | 8.200 | 8.098 | 1.000 | 0.966 | 1.036 | 0.978 | 0.978 | 0.354 |
| crimes | furtos_total | 727 | 54.233 | 51.993 | 1.019 | 0.987 | 1.051 | 0.247 | 0.330 | 0.000 |
| sinistros | acidentes_total | 726 | 0.098 | 0.101 | 0.773 | 0.468 | 1.275 | 0.313 | 0.470 | 1.000 |
| sinistros | acidentes_com_vitima | 726 | 0.152 | 0.156 | 0.760 | 0.461 | 1.253 | 0.282 | 0.470 | 1.000 |
| sinistros | atropelamentos | 726 | 0.304 | 0.317 | 0.804 | 0.350 | 1.850 | 0.608 | 0.608 | 1.000 |

**Só a base original (robustez; era o resultado da 1ª versão desta fase):**

| dominio | tipo | n_dias | pct_sem_hora_dia_jogo | pct_sem_hora_sem_jogo | OR_ajustado | IC95_lo | IC95_hi | p_ajustado | p_BH_dominio | fisher_p_bruto |
|---|---|---|---|---|---|---|---|---|---|---|
| crimes | crimes_violentos | 727 | 9.063 | 8.527 | 1.050 | 1.015 | 1.086 | 0.005 | 0.013 | 0.000 |
| crimes | lesao_corporal_dolosa | 727 | 8.697 | 8.573 | 1.119 | 1.032 | 1.214 | 0.007 | 0.013 | 0.648 |
| crimes | roubos_total | 727 | 8.577 | 8.035 | 1.027 | 0.987 | 1.069 | 0.193 | 0.257 | 0.000 |
| crimes | furtos_total | 727 | 55.124 | 52.132 | 1.019 | 0.976 | 1.064 | 0.389 | 0.389 | 0.000 |
| sinistros | acidentes_total | 726 | 0.135 | 0.092 | 1.398 | 0.793 | 2.464 | 0.247 | 0.411 | 0.138 |
| sinistros | acidentes_com_vitima | 726 | 0.211 | 0.142 | 1.370 | 0.779 | 2.410 | 0.274 | 0.411 | 0.105 |
| sinistros | atropelamentos | 726 | 0.402 | 0.293 | 1.316 | 0.531 | 3.261 | 0.553 | 0.553 | 0.403 |

Com a base original havia seleção após BH em crimes_violentos, lesao_corporal_dolosa; com o calendário completo ela não sobrevive à correção múltipla (p bruto < 0,05 ainda em lesao_corporal_dolosa, OR 1.08). Leitura: o sinal antigo era em parte efeito de comparar dias de jogo com dias de Paulistão/Libertadores marcados como "sem jogo". Mesmo assim, por cautela, a Fase 2 reporta junto o efeito no total diário (com + sem hora) de `lesao_corporal_dolosa` e `crimes_violentos`.


**Sem seleção detectável** após controles de calendário e BH por domínio: a proporção de registros sem hora não difere entre dias com e sem jogo em nenhum tipo. A perda de registros sem hora reduz a amostra (muito em furtos), mas não parece enviesar a comparação jogo × não-jogo.

## 8. Limitações declaradas nesta fase

- Estádio: a base de futebol não informa; **agora conferido jogo a jogo na Wikipédia** (seção 1b). 7 mandos fora da capital vão para `janela_fora_capital`; 4 jogos na capital em estádio não habitual usam o estádio real (Canindé sem coordenada no projeto: lat/lon NaN, a definir na análise espacial).
- 3 horários de início aproximados (segundos ≠ 00), arredondados a 30 min.
- Furtos: 53% sem hora — a série horária de furtos representa só a metade com hora.
- `janela`: todas as competições oficiais com jogo na capital dos 4 times. `janela_fora_capital`: todos os jogos oficiais dos 4 times fora da capital, inclusive Supercopa do Brasil e o exterior; amistosos não entram (as páginas não listam amistosos nesses anos).
- Horários das fases de grupos do Paulistão vêm de uma fonte (Wikipédia, com fuso explícito UTC−3), sem página de edição para conferência cruzada; a data foi conferida com o link da súmula do ge.
- Público: total do estádio (Wikipédia), não pagante; conferido em amostra (seção 1e). Restrição da COVID marcada por regra (decreto estadual), não só onde a fonte anota.
- Público como dose-resposta (Fase 2) mede a multidão no estádio, não a audiência de TV; e o público real não é conhecido antes do jogo (Fase 3 só pode usar média histórica do mandante).

## Arquivos

- `scripts/30_eventos_horarios.py` → `data/silver/crime_eventos_sp.csv.gz`, `acidentes_eventos_sp.csv.gz`, `qualidade_hora.csv`
- `scripts/31_jogos_horarios.py` → `data/silver/jogos_sp_horario.csv`
- `scripts/32_base_horaria.py` → `data/gold/fato_hora_sp.csv`, `fato_hora_sp_dicionario.csv`, este relatório
- Tabelas em `reports/janelas/fase1/tabelas/`, figura em `reports/janelas/fase1/figuras/`.
