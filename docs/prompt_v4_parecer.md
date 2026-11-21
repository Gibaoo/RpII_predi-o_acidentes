# Prompt V4: revisão do artigo RP_II a partir do parecer externo

## Contexto
A professora pediu que o artigo mostre o resultado, sem falar de caminhos que deram errado (como a análise diária). Por isso o grupo escreveu uma versão nova do artigo, a RP_II (PDF `RP_II_1.pdf`, título "Crimes e Sinistros de Trânsito nas Horas em torno dos Jogos de Futebol na Cidade de São Paulo: Efeito por Janela e Ganho Preditivo"). Um parecer externo revisou essa versão. Este prompt traz só os pontos que aceitamos.

Antes de começar, leia a seção "V2: análise por janelas de horário" do `CLAUDE.md`, o fim de `docs/Changelog.md` (a partir de "V2 / Fase 1") e os prompts `docs/prompt_v2_janelas.md` e `docs/prompt_v3_entrega3.md`. O artigo novo foi escrito por um colega fora deste ambiente, então não há registro dele no `CLAUDE.md` nem no Changelog. A pasta LaTeX completa dele está em `..\entrega_parcial\rp_ii\`, junto com o `RP_II_1.pdf`. A partir de agora, essa pasta é a versão oficial do artigo. O `entrega3/main.tex` fica como está.

**Princípio que guia toda a revisão: mostrar o resultado final, não o caminho.** Robustez entra como linha de tabela ou uma frase, nunca como narrativa do tipo "primeiro achamos X, depois vimos que era Y".

## Regras que continuam valendo
- As do briefing: não inventar dados nem URLs, nunca random split em série temporal, sempre comparar com baseline, separar correlação de causalidade, declarar limitação em vez de fabricar solução.
- Crimes e sinistros sempre separados (texto, tabelas, conclusões, famílias de BH).
- Não commitar nem dar push. Não tocar em `entrega_parcial/entrega2/` nem nos `.tex` de `docs/`.
- `tab_*.tex` e `fig_*.png` só via `scripts/35_figuras_artigo_v2.py`, nunca à mão. Todo número novo no artigo precisa estar em `reports/janelas/artigo/numeros_artigo.csv` com a tabela de origem. Os números citados neste prompt são lembretes: confira sempre nos CSVs.
- Não rodar de novo os scripts 30 a 34. As análises novas vão num script novo, `scripts/36_revisao_parecer.py`, que lê `data/gold/fato_hora_sp.csv` e as bases de eventos em `data/silver/`, com saídas em `reports/janelas/revisao/crimes/` e `reports/janelas/revisao/sinistros/`. Se precisar regenerar relatório antigo, use `REUSA=1`.
- No texto do artigo: não usar travessão e nunca "americano" para os Estados Unidos (usar "estadunidense").
- Python: `py -3.14`. Se faltar pacote, instale só o necessário e anote no `CLAUDE.md`.

## Fase 1: conferências e análises novas (parar ao final)

### 1.0 Conferências (só leitura de código e dados, responder no resumo da fase)
**Primeiro, rastreabilidade do artigo novo.** Compare cada número do `rp_ii` com o `numeros_artigo.csv` e com os CSVs de `reports/janelas/`, e liste os que não têm origem nos nossos arquivos (candidatos: Tabela 3 com hora × mês, Tabela 7 com furtos corrigidos, furtos por subtipo, os 10 boletins da DRADE, o GLM diário de furtos). Confira também se as tabelas do `rp_ii` são os `tab_*.tex` gerados pelo script 35 ou se foram editadas à mão, e se o `.bib` dele tem todas as referências citadas. Não corrija nada ainda: só liste.

Depois, o artigo afirma ou deixa ambíguas as coisas abaixo. Confira no código e nos dados e responda cada uma:
1. **137 partidas:** confirmar que são os jogos na capital do Brasileiro e da Copa do Brasil vindos do `BR-Football-Dataset` (o "52 dos 137" da correção de fuso). Dizer de onde vêm os jogos fora da capital dessas competições.
2. **"7 mandos em Barueri e na Vila Belmiro":** o que são exatamente (mandos dos clubes da capital jogados fora dela?). Listar os 7.
3. **`crimes_violentos` no pipeline horário:** a definição exata usada em `30`/`32` (o V2 diz `CATEGORIAS_VIOLENTAS` + `ROUBO*`). Inclui roubos? Inclui lesão corporal?
4. **Grão da contagem:** as contagens horárias de crime são de BOs únicos ou de BO × rubrica (ver `bos_unicos` vs `crimes_totais` no `CLAUDE.md`)? **Se forem BO × rubrica, PARE e me avise antes de qualquer outra coisa**, com a diferença entre as duas contagens.
5. **Coordenadas:** % dos crimes de SP capital com hora e com coordenada válida; % excluído como ponto de acúmulo no estádio; o mesmo para sinistros.
6. **Público:** fonte e cobertura do "público histórico do mandante" usado como dose e no bloco preditivo.
7. **Ponto médio:** num início às :30, o ponto médio de toda hora cai exatamente numa fronteira de janela. Como o código trata isso (qual lado do intervalo é fechado)? Confirmar a prioridade durante > pós > pré nos dias com dois jogos.
8. **Definições:** o que é "sem conduta nula" (Tabela 4), o que entra em "sinistros totais" e como foram tratadas as falhas da estação do INMET.
9. **Bloco preditivo (Fase 3):** hiperparâmetros do XGBoost, do GLM e do Prophet; como o GLM trata o efeito fixo de ano × mês no mês de teste do walk-forward; se existe o resultado com o clima da véspera (e os números); os números do baseline (média da mesma hora e dia da semana nas quatro semanas anteriores: deviance, ganho, PR-AUC); por que a prevalência de pico de crimes na Tabela 6 (0,075) difere da média da Tabela 5a (8,1%).
10. **Heterogeneidade da Fase 2:** onde estão os resultados de clássico, noturno, fim de semana, competição, resultado do mandante (só PÓS) e tercil de público. Resumir em uma linha cada, para a cidade e, se existir, para o entorno.
11. **Janela 2022-2023:** a cobertura de cada fonte em `data/bronze/`. Se o motivo de usar só 2022-2023 não ficar claro pelos dados, me pergunte em vez de inventar uma justificativa.
12. **Furtos no entorno:** quais subtipos existem nos dados (veículo, transeunte, outros) e se a SSP traz campo de período ou "hora incerta" (`DESC_PERIODO`) para esses registros.

### 1.1 Especificação principal com hora × mês (cidade toda, os dois domínios)
O efeito fixo de hora × mês corta cerca de metade do PRÉ de crimes violentos (Tabela 3 do artigo atual), porque o pôr do sol muda mais de uma hora ao longo do ano e roubo é sensível à escuridão. Esse controle passa a fazer parte do modelo principal:

`log E[y] = β_pre·PRE + β_dur·DURANTE + β_pos·PÓS (por tipo de jogo) + EF(hora × dia da semana) + EF(hora × mês) + EF(ano × mês) + feriado + véspera + férias + chuva + temperatura`, erros agrupados por semana.

- Rodar para todos os desfechos × janelas × tipo de jogo (capital e fora), com BH por domínio, placebo (o mesmo número de inícios falsos do script 33; se passar de ~1 h, use 500 e declare), robustezes (binomial negativa e erro agrupado por dia) e o desenho pareado (que não depende da especificação; reaproveite).
- Aplicar a regra de robustez da Metodologia exatamente como está escrita e gerar as marcas (‡, †, ∗) no código, nunca à mão.
- A especificação anterior (sem hora × mês) vira uma linha de robustez.
- Refazer o event study com a especificação nova (para a Figura 1) e o tercil de público.

### 1.2 Entorno como diferença em diferenças (os dois domínios)
Hoje o resultado mais forte do artigo (furtos no entorno) é o único que não passou pela régua completa (placebo, pareado, hora × mês), e o desenho está descrito de forma ambígua ("comparamos as janelas dos jogos daquele estádio com as dos outros").

- **Unidades:** disco de 3 km de cada estádio (sem os pontos de acúmulo, como hoje) e resto da cidade (fora dos três discos).
- **Modelo:** para cada estádio s e hora t, com efeito fixo de cada hora, o Poisson de duas unidades equivale a um GLM binomial da fração das ocorrências que caem no entorno: `n_entorno_t ~ Binomial(n_entorno_t + n_resto_t, p_t)`, com `logit(p_t) = β_pre·PRE_s + β_dur·DUR_s + β_pos·PÓS_s + EF(hora × dia da semana) + EF(hora × mês) + EF(ano × mês) + feriado + chuva`, mais indicadores das janelas dos jogos nos outros estádios, para não contaminar o controle. `exp(β)` é a razão entre a variação no entorno e a variação no resto da cidade. Erros agrupados por semana. Horas com total zero saem. Para a linha agregada dos três estádios, empilhar com efeitos fixos específicos de cada estádio. Se preferir implementar como Poisson com efeito fixo de hora (por exemplo, `pyfixest`), tudo bem, desde que o estimando seja o mesmo.
- **Régua completa:** BH (uma família por domínio, como hoje); placebo (inícios falsos em dias sem jogo naquele estádio, com a mesma distribuição de horário por dia da semana); robustezes (quase-binomial ou beta-binomial para sobredispersão e erro agrupado por dia); pareado (cada jogo contra o mesmo dia da semana e horário, ±4 semanas, sem jogo naquele estádio, com a diferença da fração na janela em relação às horas FORA dos mesmos dias).
- **Raio:** só o modelo principal com discos de 1, 2, 3 e 5 km.
- **Canal do BO:** refazer as colunas da Tabela 4 (todos, só presencial, só online, sem conduta nula) com o modelo novo.
- **Furtos:** (a) DURANTE + PÓS como uma janela única de 4 horas, que passa a ser o resultado principal de furtos, porque a hora registrada pode ser a da descoberta (o torcedor só percebe o furto do carro quando volta) e isso empurra furtos do DURANTE para o PÓS; (b) separado por subtipo (veículo, transeunte, outros).
- **Furtos sem hora (52,8%):** (a) testar se a fração de furtos sem hora no entorno difere entre dias com e sem jogo (GLM diário com controles de calendário); (b) estimar a variação diária dos furtos no entorno nos dias de jogo usando todos os furtos, com e sem hora, e comparar com a soma das janelas. Isso testa a hipótese por trás da correção de 2,12 da Tabela 7 e, se der, a substitui.
- **Tabela 7** (risco esperado por estádio): recalcular a partir do modelo novo.
- **Regra de parada:** se o aumento de furtos no entorno durante e depois do jogo não passar pela régua, PARE e me mostre antes de mexer no texto, porque isso muda a conclusão principal.

### 1.3 Excluir os jogos do Brasil na Copa de 2022
As horas "sem jogo" incluem os jogos da seleção na Copa de 2022, que pararam a cidade. Excluir as horas PRÉ, DURANTE e PÓS desses jogos com a mesma regra já usada para as finais da Copinha e do Brasileirão Feminino. Horários de Brasília (conferir numa segunda fonte, como o resto do calendário, e registrar a fonte):
- 24/11/2022, 16h, Brasil x Sérvia
- 28/11/2022, 13h, Brasil x Suíça
- 02/12/2022, 16h, Camarões x Brasil
- 05/12/2022, 16h, Brasil x Coreia do Sul
- 09/12/2022, 12h, Croácia x Brasil

Aplicar em tudo o que o script 36 roda. O bloco preditivo não será refeito; o teste dele é 2023 e não é afetado (anotar no Changelog). Shows no Allianz Parque e no Morumbi ficam como limitação (viés conservador no entorno), sem montar lista agora.

### 1.4 Pico: robustez do esperado
- Recalcular a Tabela 5b (pico por janela) e a validação nos 12 folds com hora × mês no modelo do esperado, nos dois domínios. Se as respostas ao objetivo (ii) não mudarem, mantenha a definição atual (o bloco preditivo depende dela) e registre isso para uma frase no artigo. Se mudarem, PARE e me mostre.

### Ao final da Fase 1 (parar e me mostrar)
- A lista de números e tabelas do `rp_ii` sem origem nos nossos arquivos.
- As respostas da 1.0, uma por item.
- `reports/janelas/revisao/resumo_revisao.md` com uma tabela "antes x depois" de cada número que está hoje no artigo e que mudou, separando crimes e sinistros.
- Em linguagem direta, por domínio: o que passa pela régua na cidade e no entorno, e se alguma conclusão do artigo muda.

## Fase 2: artigo (só depois que eu aprovar a Fase 1)
Edite o `.tex` de `..\entrega_parcial\rp_ii\`. Tabelas novas ou alteradas via `scripts/35_figuras_artigo_v2.py`; números novos em `numeros_artigo.csv`. Se alguma tabela do `rp_ii` foi feita à mão, primeiro passe a gerá-la pelo script 35, com o mesmo conteúdo e formato, e só depois altere. Ao terminar, todo número sem origem listado na Fase 1 ou ganha origem num CSV ou sai do texto.

### 2.1 Citar Masiero (2022) e reescrever o ineditismo
É o estudo mais próximo do nosso e não está no artigo. Entrada BibTeX (dados conferidos):
```bibtex
@article{masiero2022,
  author  = {Masiero, Ilaria},
  title   = {Sports-based Entertainment and Crime: Evidence from Football Games in {Brazil}},
  journal = {Journal of Sports Economics},
  volume  = {23},
  number  = {8},
  pages   = {1076--1095},
  year    = {2022},
  doi     = {10.1177/15270025221085714}
}
```
O que o resumo do artigo afirma (não afirme mais nada sem ler o texto completo, que tem acesso aberto em https://archive-ouverte.unige.ch/unige:159833): nove anos de dados horários de roubos e furtos por distrito policial em São Paulo, ligados a 430 partidas; os roubos caem durante os jogos, com queda maior nos jogos de maior audiência; os crimes parecem se deslocar para antes do jogo; não há deslocamento espacial; na cidade, o padrão é de "incapacitação voluntária" de possíveis ofensores; no entorno dos estádios, a concentração de pessoas supera esse efeito e o crime local sobe.
- **Introdução:** apagar "Não encontramos estudo que, para São Paulo, meça o efeito dos jogos hora a hora...". A lacuna passa a ser: Masiero já mediu hora a hora roubos e furtos em São Paulo; falta um estudo que inclua sinistros e jogos fora da capital, compare o entorno com o resto da cidade separando o canal do BO e avalie o ganho preditivo da agenda, com dados de 2022-2023.
- **Trabalhos correlatos:** parágrafo próprio na Seção 2.2, menção na síntese (2.4) e linha na Tabela 1: Método "Painel horário por distrito policial"; Dados "Roubos e furtos por hora, nove anos, 430 jogos (São Paulo)"; Contribuição "Acrescenta sinistros, jogos fora da capital, entorno contra resto da cidade por canal do BO e bloco preditivo".
- **Discussão:** citar como convergência (PRÉ, queda durante o jogo, aumento no entorno, dose por público), sem exagerar o que o nosso DURANTE mostra (ver 2.5).

### 2.2 Resultados com a especificação nova
- **Tabela 2:** com hora × mês e as marcas geradas no código. Se a 1.0 confirmar que crimes violentos inclui roubos, dizer no texto que os dois resultados não são confirmações independentes.
- **Seção 4.2:** apagar como seção narrativa. No lugar, uma tabela compacta de robustez dos resultados principais (nova Tabela 3), com linhas: modelo principal; sem hora × mês; binomial negativa (ou quase-binomial no entorno); erro agrupado por dia; placebo (p); pareado (IC 95%); raio de 1, 2 e 5 km (só entorno). Colunas: PRÉ da cidade (crimes violentos), entorno furtos DURANTE + PÓS, entorno roubos PÓS, entorno crimes violentos PÓS. Texto de um parágrafo, só com resultados. O tercil de público entra em uma frase se continuar valendo.
- **Seção 4.3 (entorno):** reescrever com o modelo de diferença em diferenças. Trocar "o que indica concentração do crime no entorno, e não aumento geral" por algo como: o aumento fica restrito ao entorno; como o resto da cidade tem centenas de ocorrências por dia, um deslocamento de uma ou duas por jogo não seria detectável, então o desenho não separa crime gerado de crime deslocado [Kurland et al. 2014]. Furtos: DURANTE + PÓS como resultado principal, com os subtipos.
- **Canal online:** trocar o argumento "no boletim online o local é o endereço declarado pela vítima" (isso vale para os dois canais) por: no BO online, o local é geocodificado a partir do endereço digitado, sem conferência na delegacia, e o estádio tende a ser informado como referência (a Etapa 10 encontrou acúmulo de BOs online nas coordenadas do próprio estádio); mesmo sem esses pontos, a localização online é menos precisa.
- **Tabela 4:** marcar pBH < 0,05, não p bruto, como o texto da 4.3 já faz.
- **Seção 4.4 (pico):** apagar a frase do P95 como subconjunto e do Jaccard de 0,50, e a coluna "κ P95" da Tabela 5a. Esses valores saem da matemática de duas prevalências encaixadas (10% e 5%), não dos dados: κ = (0,95 - 0,86)/(1 - 0,86) ≈ 0,64 em qualquer base, por isso é idêntico para crimes e sinistros. A validação é a prevalência fora da amostra; o κ com a cauda de Poisson fica como "a estatística escolhida não muda o resultado". Acrescentar a frase da robustez com hora × mês no esperado (1.4).
- **Seção 4.5 (preditivo):** baseline na Tabela 6 (deviance e PR-AUC); explicar a prevalência da Tabela 6; uma frase dizendo que a PR-AUC baixa é esperada por construção (o pico é justamente o que calendário e clima não explicam) e que a ablação testa se a agenda de jogos explica esse resíduo; o resultado com o clima da véspera em uma frase.
- **Seção 4.6:** Tabela 7 do modelo novo e a correção dos furtos sem hora conforme a 1.2.

### 2.3 Metodologia (limite de 2 páginas)
- Definições: crimes violentos (o que inclui), lesão corporal dolosa, sinistros totais, "sem conduta nula".
- Grão da contagem (BO único) e um funil em duas linhas por domínio: registros no município, com hora, com coordenada válida (crime) e no disco. Números no `numeros_artigo.csv`.
- "As 137 partidas na capital do Brasileiro e da Copa do Brasil...", de onde vêm os jogos fora da capital e o que são os 7 mandos.
- Fuso: manter só "os horários dessa base estão no fuso do Reino Unido e foram convertidos para o horário de Brasília". Apagar o contrafactual (52 partidas no dia seguinte, 108 com jogo noturno errado): é o caminho anterior.
- Uma frase com a convenção do ponto médio (qual lado é fechado) e a prioridade nos dias com dois jogos.
- Fonte do público.
- Hora × mês no modelo principal, justificado pelo pôr do sol e pela concentração dos jogos em certos meses e horários.
- Entorno: o modelo de diferença em diferenças em duas frases e o teste de raio.
- Exclusões numa regra só: eventos de massa sem os quatro times (finais da Copinha e do Brasileirão Feminino, jogos do Brasil na Copa de 2022).
- O motivo real da janela 2022-2023 (da 1.0).
- Tratamento das falhas do INMET.
- Hiperparâmetros do bloco preditivo (uma frase ou nota de rodapé).
- Disponibilidade de código e dados: uma frase. Me pergunte o link do repositório e se ele é público; não invente.

### 2.4 Linguagem: associação, não causalidade
A própria análise mostra que o horário dos jogos se confunde com o perfil sazonal, então não vamos defender exogeneidade.
- No texto todo, trocar "efeito do jogo", "os jogos alteram" e "aumentam" por "variação", "associação", "as ocorrências foram X% maiores". Manter "efeito fixo" (termo técnico).
- Título: "Efeito por Janela" vira "Variação por Janela".
- Conferir que resumo, objetivos e conclusão ficaram coerentes com isso. Não mexer no texto dos objetivos definido no V3 além do necessário.

### 2.5 Resumo e Discussão
- **Resumo:** só os resultados com a especificação nova. Sem "cerca de metade desse efeito é sazonalidade" nem qualquer comparação entre especificações.
- **Discussão:** apagar o parágrafo sobre o GLM diário e o fuso ("Os resultados também mostram por que a unidade horária..."). É o caminho anterior, e a Introdução já justifica a unidade horária.
- Trocar "Na previsão, o XGBoost supera o Prophet" por: o XGBoost foi o melhor para crimes e o GLM para sinistros, ambos comparados ao baseline.
- DURANTE: aplicar a mesma régua dos outros resultados. Hoje a queda só aparece no pareado (-6,8%) e não no GLM; não apresentar como estabelecida. Escrever "tendem a cair, como em Manchester [Ivandić et al. 2024] e em São Paulo [Masiero 2022]" só se os números novos sustentarem.
- Respostas aos quatro objetivos atualizadas com os resultados novos, sempre separadas para crimes e sinistros.
- Recomendação de policiamento: suavizar (o excesso absoluto é menor que uma ocorrência por janela, os resultados são associações e o policiamento reforçado pode aumentar o registro).
- Limitações: acrescentar (a) violência doméstica não é desfecho separado, então o nulo dos jogos fora da capital não exclui efeito sobre ela, que motivou parte do desenho; (b) shows nos estádios ficam no controle (viés conservador no entorno).
- Heterogeneidade: uma frase com o resultado de clássico e resultado do mandante (da 1.0). Se não houver resultado utilizável, tirar "testa a heterogeneidade por resultado e clássico" da linha de Card e Dahl na Tabela 1.

### 2.6 Correções pontuais
- **Ristea et al. (2020):** o estudo é no United Center, em Chicago, casa dos Bulls (NBA) e dos Blackhawks (NHL), ou seja, jogos de basquete e hóquei. A previsão usa densidade de kernel localizada como atributo de uma regressão logística com regularização L2, avaliada pela AUC de curvas de vigilância. Corrigir a Seção 2.3 e a Tabela 1 (Método: "Regressão logística com atributos de densidade de kernel, com e sem redes sociais").

### 2.7 Compilação e páginas
- Limites (os da 2ª entrega): título e resumo 1; introdução 2; correlatos 4; metodologia 2; resultados 6; discussão e conclusão 1; referências livre. Se estourar, enxugue texto, não diminua fonte nem margem.
- Rodar `scripts/21_valida_latex.py` no `.tex` (o aviso de `\cite` sem `\bibitem` é falso positivo, o artigo usa BibTeX).

### Ao final da Fase 2 (parar e me mostrar)
- Resumo novo e título novo.
- Lista dos trechos alterados por seção, com o antes e o depois dos parágrafos que mudaram de sentido.
- Tabelas novas (2, 3, 4, 5a, 6, 7) com cada número e o CSV de origem.
- Estimativa de páginas por seção.

## Fase 3: documentação
- Salvar este prompt em `docs/prompt_v4_parecer.md`.
- `CLAUDE.md`: seção nova "V4: revisão pelo parecer" (especificação principal com hora × mês, entorno por diferença em diferenças, exclusão da Copa de 2022, o que mudou no artigo) e "Status" e "Próximos passos" atualizados.
- `docs/Changelog.md`: entrada "V4: revisão pelo parecer (data)", registrando que o artigo `rp_ii` foi escrito por um colega e passou a ser a versão oficial.
- Não commitar: no fim, me passe os comandos de `git add`, `commit` e `push`, conferindo que nada de `data/bronze/` ou `uploads/` nem arquivo acima de 100 MB entra.

## Fora do escopo (não fazer)
- Refazer o bloco preditivo (Fase 3 do V2); só ler os números do baseline e do clima da véspera.
- Teste de Fisher agrupado por jogo, jogos sem público de 2020-2021, violência doméstica como desfecho, lista de shows, raios além de 1 a 5 km.
