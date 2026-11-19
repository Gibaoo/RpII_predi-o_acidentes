# Defesa da metodologia — perguntas prováveis e respostas curtas

Material de apoio para a apresentação da 3ª entrega (V2: análise por janelas de horário).
Os números vêm das tabelas em `reports/janelas/` (lista rastreável em
`reports/janelas/artigo/numeros_artigo.csv`). Crimes e sinistros sempre em modelos separados.

---

## Dados

**1. Por que só 2022 e 2023?**
É a janela em comum entre as três bases principais (SSP-SP, Infosiga e INMET). Dois anos são pouco para
sazonalidade anual, o que está declarado como limitação; por isso o modelo usa efeito fixo de ano × mês e
não tenta extrapolar tendência longa.

**2. O que é o "bug do fuso"?**
Na base de jogos (BR-Football-Dataset), a hora e a data estavam no fuso do Reino Unido (GMT/BST), não no de
Brasília. Um jogo às 21h30 de quarta aparecia como 00h30 ou 01h30 de quinta. Resultado: 52 dos 137 jogos da
base original estavam no dia seguinte, e a classificação de jogo noturno estava errada em 108. Corrigimos com
`tz_localize('Europe/London')` → `tz_convert('America/Sao_Paulo')` e conferimos os 137 horários com uma
segunda fonte (páginas de temporada dos clubes na Wikipédia): 137 de 137 bateram.

**3. Por que completar o calendário com Paulistão, Libertadores, Sul-Americana e Recopa?**
Esses jogos apareciam como "horas sem jogo" e contaminavam o grupo de controle, o que puxa qualquer efeito
para zero; além disso, janeiro e fevereiro ficavam sem nenhum jogo. Com o calendário completo são 216 jogos
na capital. Só isso já muda o modelo diário: furtos passam a +4,0% em dia de jogo (p_BH = 0,024).

**4. Por que incluir o Santos e os jogos fora da capital?**
O Santos é um dos quatro grandes do estado e joga na capital como visitante (e uma vez como mandante, no
Canindé). Jogos fora da capital (301) são assistidos na cidade pela TV ou em bares; separá-los permite
distinguir o efeito da multidão perto do estádio do efeito de assistir ao jogo (Ivandić et al., 2024).

**5. Por que contar só os registros com hora? Isso não perde dados?**
Perde: 33,9% dos crimes não têm hora (52,8% dos furtos, porque a vítima percebe depois; 8,1% dos roubos) e
0,1% dos sinistros. Sem hora não há como colocar o registro numa janela. Testamos se a falta de hora é maior
em dia de jogo: com o calendário completo, não há diferença depois da correção. A consequência é que o
excesso absoluto de furtos está subestimado; a tabela de risco mostra uma coluna corrigida, supondo que os
furtos sem hora se distribuem pelas horas como os com hora.

**6. Por que a hora, e não a meia hora ou o minuto?**
32,9% dos horários de crime estão no minuto :00 e mais da metade em :00 ou :30 (arredondamento de quem
registra). Uma unidade menor que a hora mediria esse arredondamento, não o crime.

## Janelas

**7. Por que janelas de 2 horas?**
É a duração de uma partida (90 min + intervalo + acréscimos), e a literatura com dados horários usa
janelas parecidas (Montolio e Planells-Struse, 2016; Ivandić et al., 2024). PRÉ = 2 h antes, DURANTE =
início até +2 h, PÓS = +2 h a +4 h. O *event study* (−6 a +12 h) mostra que o resultado não depende desse
corte: dá para ver hora a hora onde o efeito aparece.

**8. Por que sair do grão diário?**
No total do dia, efeitos opostos se cancelam (queda durante o jogo e alta depois) e um efeito de poucas horas
se dilui nas outras vinte. Foi exatamente o que aconteceu: no grão diário não havia efeito; no horário, os
furtos no entorno sobem 66% DURANTE e 85% PÓS.

**9. Como se decide em que janela cai uma hora, se o jogo começa às 21h30?**
Pelo ponto médio da hora (hh:30), numa linha do tempo contínua. Assim cada janela tem exatamente 2 horas e um
jogo às 21h30 tem PÓS até 1h30 do dia seguinte.

**10. Qual é o grupo de controle?**
Horas sem nenhum jogo dos quatro times (nem na capital nem fora). As horas de dia de jogo fora das janelas têm
um indicador próprio. Eventos de grande público sem os quatro times (finais do Brasileirão Feminino e da
Copinha) ficam fora da amostra, porque não são tratamento nem controle.

## Modelo explicativo

**11. Por que Poisson, e não regressão linear?**
O desfecho é uma contagem (muitas horas com 0 a 3 sinistros), sempre ≥ 0 e com variância que cresce com a
média. O GLM de Poisson modela isso diretamente e dá o efeito como razão de taxas (+x%). A binomial negativa,
que acomoda sobredispersão, é uma das robustezes e dá o mesmo resultado.

**12. Por que efeito fixo hora × dia da semana?**
Os jogos acontecem em horários que já têm um nível próprio de ocorrências (domingo 16h, quarta 21h30). Sem
esse controle o modelo compara "domingo 16h com jogo" com "terça 4h sem jogo" e confunde horário com jogo. É a
versão horária do confundidor de calendário que derrubou o efeito no grão diário.

**13. E o efeito fixo ano × mês? E hora × mês?**
Ano × mês absorve sazonalidade e tendência de cada mês. Hora × mês foi testado como robustez porque o perfil
horário muda ao longo do ano (o pôr do sol muda mais de uma hora, e roubo é sensível à escuridão): com ele, o
PRÉ da cidade toda cai de +4,7% para +2,7% (p = 0,053). Esse teste mostrou que cerca de metade do PRÉ era
sazonalidade.

**14. Por que erro agrupado por semana?**
As janelas atravessam a meia-noite e horas próximas são correlacionadas; o erro "comum" subestimaria a
incerteza. A semana cobre isso; o agrupamento por dia é robustez.

**15. Por que Benjamini-Hochberg, e por que uma família por domínio?**
Testamos muitos desfechos × janelas; sem correção, alguns dariam p < 0,05 por acaso. BH controla a taxa de
falsas descobertas e é menos conservador que Bonferroni. Uma família por domínio porque crimes e sinistros são
perguntas diferentes, com fontes diferentes; misturá-los diluiria ou inflaria a correção de um pelo outro.

**16. Para que o *event study*?**
Para ver o efeito hora a hora, checar pré-tendência (horas −6 a −3 deveriam ser ≈ 1) e procurar efeitos
tardios (até +12 h, por causa de Ivandić et al., 2024). Em crimes violentos a pré-tendência foi rejeitada
(p = 0,007) com sinais mistos: a subida começa ~3 h antes, compatível com deslocamento de torcedores. As
horas tardias com p < 0,05 não sobrevivem à correção.

**17. Para que o placebo?**
Para testar se o efeito real se distingue de "um horário qualquer": sorteamos 1.000 vezes inícios falsos, no
mesmo dia da semana e horário dos jogos reais, em dias sem jogo. Na 1ª versão o placebo estava enviesado
(modelo de base ajustado com as horas de jogo dentro e poucos dias candidatos); corrigimos antes de concluir.

**18. Por que o desenho pareado, se já há o GLM?**
É fácil de explicar e não depende da forma do modelo: cada jogo é comparado com o mesmo dia da semana e
horário em semanas próximas sem jogo, em diferença em relação às horas sem janela dos mesmos dias. Ele
controla por construção a sazonalidade do perfil horário. Foi ele que mostrou a fragilidade do PRÉ: +1,2%,
sem significância.

**19. Qual é a regra do veredito?**
Um efeito é "robusto" só se: p_BH < 0,05 no modelo principal, placebo p < 0,05, mesmo sinal na binomial
negativa e no erro por dia, **e** o pareado confirma. Se o pareado não confirma mas não contradiz: "robusto no
GLM, pareado inconclusivo" (é o caso do PRÉ de crimes violentos e roubos).

## Entorno dos estádios

**20. Por que 3 km?**
Cobre os bairros vizinhos do estádio (caminho a pé, estações, estacionamentos) sem engolir regiões inteiras da
cidade. Repetimos com os bairros do entorno como unidade, e o resultado se mantém.

**21. E o problema de geocodificação no estádio (Etapa 10)?**
Boletins online às vezes são geocodificados no ponto do próprio estádio. Excluímos essas coordenadas
acumuladas (2–3 células por estádio) e repetimos por bairro.

**22. O aumento no entorno não é só mais policiamento registrando mais?**
Pode ser em parte, e isso está declarado. Checamos o canal de registro: a delegacia de intolerância esportiva
(DRADE) registrou só 10 boletins no entorno em 2 anos. Os furtos sobem nos boletins presenciais (+105% PÓS) e
nos online (+81%). Já roubos e crimes violentos pós-jogo sobem só nos online (+49% e +44%), em que o local é
declarado pela vítima — por isso tratamos esses dois como indício e furtos como o achado principal.

**23. Mais crimes no entorno significa que o torcedor corre mais risco?**
Não necessariamente. Medimos contagem, não taxa por pessoa. Com dezenas de milhares de pessoas a mais no
entorno, a contagem sobe mesmo que o risco por pessoa não mude — é a distinção de Kurland, Johnson e Tilley
(2014) em Wembley. Sem a população presente por hora, a taxa por pessoa não é estimável.

## Pico e previsão

**24. Por que o pico é definido pelo resíduo, e não pela contagem?**
Um limiar sobre a contagem faria do pico um sinônimo de sexta à noite. O esperado vem de um modelo só de
calendário e clima, **sem** variável de jogo (para não absorver o efeito do jogo); o resíduo de Pearson
divide pelo desvio esperado, porque a contagem muda muito entre madrugada e fim de tarde. Pico = acima do P90.
No entorno, com contagens baixas, "hora de risco" = probabilidade de cauda de Poisson < 0,10.

**25. Por que a previsão é feita "na véspera"?**
É o uso prático (planejar o policiamento do dia seguinte) e impede vazamento: só entram variáveis conhecidas
até 23h59 do dia anterior. O público real do jogo não é conhecido antes, então só entra a média dos jogos
anteriores do mandante.

**26. Por que walk-forward, e não validação cruzada comum?**
Em série temporal, embaralhar coloca o futuro no treino e infla o desempenho. Usamos 12 folds mensais de 2023,
cada um treinado só com o passado, com tudo (inclusive o limiar de pico) reajustado no treino.

**27. Por que XGBoost?**
Lida com interações (hora × dia × jogo) e com valores ausentes sem pré-processamento, tem perda de Poisson
para contagens e foi o melhor nas etapas anteriores e em trabalhos parecidos (Soliani et al., 2024). Foi o
melhor modelo para crimes também aqui (deviance 1,643 na cidade, contra 1,824 do Prophet e 1,845 do GLM).

**28. Por que comparar com o Prophet?**
O título do trabalho compara XGBoost e Prophet. O Prophet modela sazonalidades diária e semanal de forma
interpretável, mas é gaussiano em log(1+y) e não usa o histórico recente como variável; ficou atrás do
XGBoost. No entorno não foi usado, porque as contagens são esparsas (0,1 a 1 por hora).

**29. Por que hiperparâmetros fixos e rasos?**
A Etapa 17 mostrou, com busca aninhada, que o tuning não traz ganho estável com este volume de dados; fixar
evita sobreajuste da busca e deixa a ablação limpa.

**30. O que é a ablação e o que ela mostrou?**
O mesmo modelo treinado com e sem as variáveis de jogo, nos mesmos folds. O jogo não melhora a previsão no
geral (as horas de jogo são poucas), mas melhora nas horas de jogo: −3,9% de deviance na cidade e −13,9% para
furtos no entorno (XGBoost). Não melhora a detecção de picos (PR-AUC igual com e sem jogo). Sinistros: sem
ganho.

**31. Por que deviance de Poisson e MAE, e nunca acurácia?**
A deviance é a métrica natural de contagens e pesa mais os erros nas horas de excesso; o MAE mostra o erro
típico. Para pico, a acurácia é enganosa (com ~5–10% de picos, "nunca é pico" acerta mais de 90%); usamos
PR-AUC (média por fold) e recall.

**32. Por que o IC por bootstrap em blocos de semana?**
Os erros de horas próximas são correlacionados; reamostrar semanas inteiras preserva essa dependência.

## Conclusão

**33. Então o futebol aumenta a violência em São Paulo?**
Não na cidade como um todo. O jogo concentra furtos (e, com evidência mais fraca, roubos) no entorno do
estádio durante e depois da partida; o PRÉ da cidade toda é pequeno e em parte sazonal; jogos fora da capital
não têm efeito; sinistros não mudam fora do entorno. São associações, não efeitos causais: a agenda de jogos
não varia de forma exógena.

**34. Por que o trabalho diário dizia "efeito de calendário, não do jogo"?**
Por três motivos: diluição (efeito de poucas horas e poucos km no total diário da cidade), calendário
incompleto (sem Paulistão e copas) e o bug do fuso (mais de um terço dos jogos no dia errado).
