# Prompt V2: refazer a análise por janelas de horário (pré, durante, pós-jogo e fora)

## Contexto

A professora avaliou que trabalhar com os dados no grão DIA ficou ruim e pediu para refazer a análise por janelas de horário em torno de cada jogo:

1. **PRÉ**: as 2 horas antes do início do jogo
2. **DURANTE**: do apito inicial até 2 horas depois (90 min + intervalo + acréscimos)
3. **PÓS**: as 2 horas seguintes ao fim do jogo
4. **FORA**: todas as outras horas

O objetivo final não muda: verificar se jogos de futebol em São Paulo aumentam a violência (e os sinistros de trânsito).

A professora também pediu que **crimes e sinistros de trânsito sejam validados separadamente, tanto o cálculo quanto o pico**. Ver a seção "Regra transversal: crimes e sinistros sempre separados".

Por que isso pode mudar a conclusão: no grão diário, efeitos opostos dentro do mesmo dia (por exemplo, queda durante o jogo, quando muita gente está assistindo, e alta depois) se cancelam, e um efeito concentrado em poucas horas se dilui nas outras 20. A literatura que usa esse desenho encontra justamente deslocamento temporal do crime em torno dos jogos (Montolio e Planells-Struse, 2016; Ivandić et al., 2024). Use isso como hipótese a testar, não como resultado esperado.

## Antes de começar

- Leia `CLAUDE.md`, `docs/briefing_original.md` e o fim de `docs/Changelog.md`. As regras inegociáveis do briefing continuam valendo: não inventar dados/URLs, nunca usar random split em série temporal, sempre comparar com baseline, separar correlação de causalidade, declarar limitação em vez de fabricar solução.
- Decisões antigas continuam válidas quando não dependem do grão diário: filtro `CD_IBGE == 3550308`; mandantes Corinthians, Palmeiras e São Paulo; definição de clássico; `crimes_violentos` = `CATEGORIAS_VIOLENTAS` + `ROUBO*` (ver `02_limpeza.py`); exclusão dos dias censurados 2023-12-30/31, das lacunas do Infosiga (2022-01-17 e 2023-08-07) e tratamento do artefato de lote de furtos em 2022-06-19.
- Não faça commit nem push. Não edite os `.tex` ainda.
- Trabalhe em fases e pare no fim de cada fase com um resumo para eu revisar (mesmo esquema de checkpoint de antes).

## Regra transversal: crimes e sinistros sempre separados

- São dois domínios independentes:
  - **CRIMES** (SSP): alvo principal `crimes_violentos`; desfechos secundários `lesao_corporal_dolosa`, `roubos_total` e `furtos_total`.
  - **SINISTROS** (Infosiga): alvo principal `acidentes_com_vitima`; desfechos secundários `acidentes_total` e `atropelamentos`.
- Em todas as fases, cada domínio tem o seu próprio **cálculo** (contagens, modelo, event study, placebo, robustez), a sua própria **definição e validação de pico**, as suas próprias tabelas e figuras e a sua própria conclusão.
- Nunca juntar crime e sinistro num índice ou alvo único, e nunca colocar os dois na mesma família de correção de Benjamini-Hochberg (uma família por domínio).
- Os dois domínios têm escala e problemas de dado diferentes, e a validação precisa mostrar isso: crime tem ~35% de registros sem hora (puxado por furtos) e geocodificação ruim; sinistro tem hora quase completa e coordenada boa, mas contagens horárias pequenas (muitas horas com 0 a 3 ocorrências), o que afeta a definição de pico.
- Relatórios em `reports/janelas/crimes/` e `reports/janelas/sinistros/`, mais um resumo que compara os dois lado a lado.

## Fatos já verificados nos dados (conferir, não redescobrir)

1. **O horário dos jogos está no fuso errado na base de futebol, e isso afeta o trabalho antigo.** A coluna `time` do `BR-Football-Dataset.csv` está no horário do Reino Unido (Europe/London: GMT no inverno europeu, BST no verão) e a coluna `date` é a data no Reino Unido, não no Brasil.
   - Evidências: a final da Copa do Brasil 2023 (São Paulo x Flamengo, 24/09/2023, 16h de Brasília) aparece como `20:00`; a última rodada do Brasileirão 2022 (Corinthians x Atlético-MG, 13/11/2022, 16h de Brasília) aparece como `19:00`.
   - Depois de converter (`tz_localize('Europe/London')` e `tz_convert('America/Sao_Paulo')`, montando o timestamp a partir de `date` + `time`), os horários ficam realistas: 16:00, 21:30, 19:00, 20:00, 21:00, 18:30, 11:00.
   - Consequências: **52 dos 137 jogos em SP capital de 2022-2023 (38%) mudam de data** depois da conversão (os jogos noturnos estavam marcados no dia seguinte), e o `jogo_noturno` do `02_limpeza.py` (hora UK >= 19) estava errado.
   - Tarefas: (a) corrigir na nova base; (b) documentar no Changelog e no `CLAUDE.md` como bug do pipeline diário; (c) rodar de novo só o GLM diário da Etapa 7 com as datas corrigidas, para saber se o nulo antigo se mantém (é uma checagem, não refazer o projeto antigo inteiro); (d) investigar o horário estranho `01:24:28` que aparece em um jogo.
2. **Hora do crime (SSP):** `HORA_OCORRENCIA_BO`, numa amostra de SP capital do 2º semestre de 2023, está ausente em ~35% dos registros, mas o problema se concentra em furtos (~53% sem hora, porque a vítima só percebe depois). Roubos (~9%) e lesão corporal (~7%) têm boa cobertura. Há arredondamento: ~33% dos horários estão no minuto :00 e ~53% em :00 ou :30, por isso o grão deve ser de 1 hora, não menor. Em 2023 algumas colunas mudam de nome (`DESC_PERIODO`, `NOME_MUNICIPIO`, `DATA_REGISTRO`). Confirmar esses números para os 4 arquivos.
3. **Hora do sinistro (Infosiga):** `hora_sinistro` ausente em só ~0,1%.
4. **INMET:** já é horário, em UTC (subtrair 3h; Brasil sem horário de verão desde 2019).
5. Existe um rascunho `scripts/30_eventos_horarios.py` (extrai do bronze 1 linha por registro com timestamp local, para crime e sinistros, e uma tabela de qualidade da hora). **Ele não foi executado nem testado**: revise, corrija se necessário e use como ponto de partida, ou substitua.

## Fase 1: base horária (parar ao final)

- `scripts/30_eventos_horarios.py`: bronze para `data/silver/crime_eventos_sp.csv.gz` e `data/silver/acidentes_eventos_sp.csv.gz` (timestamp local, flag `tem_hora`), mais tabela de qualidade da hora por tipo de desfecho (% sem hora, arredondamento).
- `scripts/31_jogos_horarios.py`: um registro por jogo com início em horário de Brasília (`inicio_br`), corrigindo o fuso; flags de clássico, noturno (início >= 19h de Brasília, já corrigido), fim de semana, competição e estádio do mandante. A base não informa o estádio: assumir o estádio habitual de cada clube e declarar isso como limitação.
- `scripts/32_base_horaria.py` gerando `data/gold/fato_hora_sp.csv`: 1 linha = 1 hora, de 2022-01-01 00h a 2023-12-31 23h (17.520 linhas), com:
  - contagens por hora, só com registros que têm hora: `crimes_violentos`, `lesao_corporal_dolosa`, `roubos_total`, `furtos_total`, `acidentes_total`, `acidentes_com_vitima`, `atropelamentos`; e, por dia, quantos registros de cada tipo ficaram sem hora;
  - calendário (hora do dia, dia da semana, mês, feriado, véspera de feriado, férias) e clima horário (chuva, temperatura);
  - `janela` em {pre, durante, pos, fora}, `hora_relativa` ao início do jogo (de -6 a +12), id do jogo e atributos do jogo.
- Regras de classificação da janela (documentar no relatório):
  - as janelas são definidas na linha do tempo contínua, não por dia: um jogo às 21:30 tem PÓS indo até 01:30 do dia seguinte;
  - como os inícios podem ser em :30 ou :45, cada hora entra na janela que contém o seu ponto médio (hh:30);
  - dias com 2 jogos: se as janelas se sobrepõem, prioridade durante > pós > pré, com flag `jogo_duplo`;
  - FORA fica separado em `fora_dia_jogo` (horas distantes do jogo, mas no mesmo dia) e `dia_sem_jogo`, para testar transbordamento.
- Teste de seleção: a proporção de registros sem hora é diferente em dias com e sem jogo? (GLM diário com controles de calendário.) Se for, é uma limitação a declarar.
- Relatório `reports/janelas/fase1_base_horaria.md`.

## Fase 2: análise explicativa (núcleo do trabalho; parar ao final)

Script `scripts/33_analise_janelas.py`, saídas em `reports/janelas/crimes/` e `reports/janelas/sinistros/`. Todos os itens abaixo rodam uma vez para cada domínio.

1. **Descritivo:** média por hora em cada janela versus as mesmas horas do relógio em dias sem jogo do mesmo dia da semana; perfil horário (0-23h) de dias com e sem jogo; figura alinhada pela hora relativa ao jogo.
2. **Modelo principal:** GLM Poisson no painel horário,

   `log E[y] = β_pre·PRE + β_dur·DURANTE + β_pos·PÓS + EF(hora do dia × dia da semana) + EF(ano × mês) + feriado + véspera + férias + chuva + temperatura`

   com erros-padrão agrupados por semana (cobre janelas que passam da meia-noite; agrupamento por dia como robustez). Reportar IRR = exp(β), variação %, IC95% e correção de Benjamini-Hochberg por família (desfechos × janelas). Binomial negativa como robustez.

   Justificativa do efeito fixo hora × dia da semana (deixar escrita no relatório): os jogos acontecem em horários que já têm um nível de crime próprio (domingo 16h, quarta 21:30). Sem esse controle, o modelo confunde "horário do jogo" com "efeito do jogo". É a versão horária do confundidor de calendário que já derrubou o efeito no grão diário.
3. **Event study:** dummies para cada hora relativa de -6 a +12, com os mesmos efeitos fixos; gráfico dos coeficientes com IC. As horas -6 a -3 servem de checagem de pré-tendência. Ir até +12 porque Ivandić et al. (2024) encontram efeitos até cerca de 10 horas depois do jogo.
4. **Placebo / permutação:** sortear inícios falsos em dias sem jogo (mesma distribuição de horário por dia da semana dos jogos reais), reestimar de 500 a 1.000 vezes e comparar os β reais com a distribuição placebo.
5. **Heterogeneidade:** clássico vs comum; noturno vs diurno (com o horário corrigido); fim de semana vs meio de semana; competição; resultado do mandante, só na janela PÓS (o resultado só é conhecido depois do jogo).
6. **Espaço × tempo:** entorno do estádio do mandante daquele jogo (Neo Química Arena, Allianz Parque, Morumbi; raio de 2 a 3 km ou bairros vizinhos) vs resto da cidade, por janela. Sinistros têm coordenada boa (99,5% válida). Para crime, reaproveitar as lições da Etapa 10 (pile-up de geocodificação nas coordenadas do próprio estádio, ~20% de coordenadas inválidas): excluir os pontos de pile-up e usar bairro como alternativa.
7. **Robustez com controles pareados** (fácil de explicar na apresentação): para cada jogo, controles = mesmo dia da semana, mesma faixa de horário, ±4 semanas, sem jogo e sem feriado. Comparar a janela do jogo com a mesma faixa nos controles e fazer a diferença em relação às horas FORA dos mesmos dias.

8. **Pico no grão horário (separado para crimes e para sinistros):**
   - Esperado = modelo só de calendário e clima (hora do dia × dia da semana, ano × mês, feriado, véspera, férias, chuva, temperatura), **sem nenhuma variável de jogo**, para o esperado não absorver o efeito que queremos medir.
   - Como a contagem horária muda muito ao longo do dia (madrugada vs fim de tarde), o resíduo bruto não serve: usar o resíduo de Pearson `(obs - esp) / sqrt(esp)` ou a probabilidade de cauda de Poisson `P(Y >= obs | esp)`. Pico = acima do P90 (P95 como robustez), a mesma lógica da Etapa 11 adaptada para hora.
   - Para sinistros, testar também o pico na soma de cada janela de 2 horas, porque contagens horárias pequenas deixam o pico por hora instável. Reportar qual nível de agregação foi escolhido em cada domínio e por quê.
   - Pergunta a responder, por domínio: a frequência de pico é maior em PRÉ/DURANTE/PÓS do que em FORA? (Razão de taxas com IC, e logística com os mesmos controles ou teste exato de Fisher.)
   - **Validação do pico, por domínio:** reestimar o esperado e o limiar só no treino de cada um dos 12 folds mensais (como na Etapa 15) e checar se a prevalência de pico no teste fica perto de 10% em cada fold; medir a concordância entre as definições (P90, P95, cauda de Poisson). Se um domínio não tiver pico estável, declarar isso em vez de forçar.

Ao final da fase, responder em linguagem direta, **separadamente para crimes e para sinistros**: em qual janela (se alguma) há aumento, de quanto, onde (cidade toda ou entorno do estádio), se os picos ficam mais frequentes nas janelas de jogo e se o resultado resiste aos placebos e às robustezes.

## Fase 3: bloco preditivo (confirmar comigo antes de fazer)

O objetivo oficial do trabalho ainda fala em modelo de previsão. Proposta: no painel horário, XGBoost Poisson com walk-forward de 12 folds mensais (mesmo esquema da Etapa 15), baseline = média por hora × dia da semana, e ablação com e sem os atributos de janela de jogo, medindo o ganho principalmente nas horas PRÉ/DURANTE/PÓS. A pergunta que esse bloco responde: saber que haverá jogo melhora a previsão hora a hora? Tudo separado por domínio: regressão da contagem horária e classificação de pico (usando a definição validada na Fase 2) para crimes e, à parte, para sinistros, cada um com as suas métricas (MAE e deviance de Poisson; PR-AUC `fold_macro` e Recall, nunca Accuracy).

## Opcional (perguntar antes): completar o calendário de jogos

Paulistão e Libertadores não estão na base. Na análise horária, as horas desses jogos ficam marcadas como FORA e contaminam o grupo de comparação, o que puxa os efeitos para zero (e janeiro e fevereiro ficam sem nenhum jogo). Se eu aprovar: montar a lista de jogos em casa dos 3 clubes nessas competições em 2022-2023, com data e horário de Brasília, a partir de fonte verificável, com `fonte_jogo` preenchido, e rodar o modelo principal com e sem esses jogos.

## Entregáveis e documentação

- Scripts 30 a 33 (e 34 se houver a Fase 3), `data/gold/fato_hora_sp.csv` com dicionário de colunas, relatórios e figuras em `reports/janelas/crimes/` e `reports/janelas/sinistros/`, mais o resumo comparativo.
- Entrada no `docs/Changelog.md` por fase e nova seção "V2: análise por janelas de horário" no `CLAUDE.md`, marcando o que do trabalho diário foi superado (incluindo o bug do fuso).
- Um texto curto de justificativa metodológica para a apresentação (a professora costuma perguntar por que escolhemos cada técnica), citando apenas referências verificadas:
  - Montolio, D.; Planells-Struse, S. (2016). How time shapes crime: the temporal impacts of football matches on crime. *Regional Science and Urban Economics*, 61, 99-113. (Barcelona, dados horários, deslocamento do crime em torno dos jogos.)
  - Ivandić, R.; Kirchmaier, T.; Saeidi, Y.; Torres-Blas, N. (2024). Football, alcohol, and domestic abuse. *Journal of Public Economics*, 230, 105031. (Manchester, queda durante as 2 horas de jogo e alta depois.)
  - Kurland, J.; Johnson, S. D.; Tilley, N. (2014). Offenses around stadiums: a natural experiment on crime attraction and generation. *Journal of Research in Crime and Delinquency*, 51(1), 5-28. (Wembley, padrão espacial e temporal do crime em dias com e sem evento.)
- Só depois de eu aprovar os resultados: atualizar metodologia e resultados nos `.tex`.
