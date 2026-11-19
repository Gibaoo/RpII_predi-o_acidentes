# PROJETO — PREDIÇÃO DE PICOS DE VIOLÊNCIA E ACIDENTES EM DIAS DE JOGOS DE FUTEBOL

## Papel

Atue como um *Cientista de Dados Sênior, Engenheiro de Dados e especialista em Machine Learning e Séries Temporais*, com experiência em análise de criminalidade, eventos esportivos, dados urbanos e modelagem preditiva.

Seu objetivo é desenvolver um projeto completo de Ciência de Dados para investigar e prever *picos de violência e acidentes associados a dias de jogos de futebol, inicialmente com foco na cidade de **São Paulo — SP, Brasil*.

Não faça apenas uma análise superficial. O projeto deve ter rigor estatístico, preocupação com causalidade, prevenção de data leakage e metodologia adequada para séries temporais.

---

# 1. OBJETIVO DO PROJETO

Investigar a relação entre jogos de futebol e:

1. violência;
2. crimes;
3. acidentes de trânsito;
4. outros tipos de ocorrências urbanas relevantes.

Posteriormente, desenvolver modelos de Machine Learning capazes de:

### Problema A — Regressão

Prever a quantidade de:

* crimes violentos;
* ocorrências policiais;
* acidentes;
* ou outro indicador disponível.

### Problema B — Classificação

Prever se determinado dia terá um *pico de violência/acidentes*.

Exemplo:

text
0 = não é pico
1 = pico


Também pode ser considerada uma classificação:

text
Baixo
Médio
Alto


Escolha a formulação mais adequada de acordo com os dados disponíveis.

---

# 2. PRIMEIRO PASSO — ENTENDER OS DADOS

Antes de realizar qualquer modelagem:

1. liste todos os arquivos disponíveis;
2. identifique formato, tamanho e estrutura;
3. mostre as colunas;
4. identifique tipos de dados;
5. identifique chaves primárias;
6. identifique possíveis chaves estrangeiras;
7. identifique granularidade temporal;
8. identifique granularidade geográfica;
9. identifique valores ausentes;
10. identifique duplicidades;
11. identifique inconsistências;
12. identifique outliers;
13. identifique possíveis problemas de qualidade.

Para cada dataset, apresente:

| Dataset | Granularidade | Período | Região | Nº linhas | Principais variáveis |
| ------- | ------------- | ------- | ------ | --------- | -------------------- |

Não assuma que uma coluna é uma chave primária sem verificar sua unicidade.

---

# 3. COLETA DE DADOS EXTERNOS

Caso os dados fornecidos não sejam suficientes, pesquise na internet por dados públicos que possam enriquecer o projeto.

Priorize fontes oficiais.

Procure dados de:

### Futebol

* jogos do Corinthians;
* Palmeiras;
* São Paulo FC;
* Santos;
* Campeonato Brasileiro;
* Copa do Brasil;
* Libertadores;
* Paulistão;
* datas;
* horários;
* estádio;
* mandante;
* visitante;
* resultado;
* público;
* cartões;
* expulsões;
* importância da partida.

### Segurança pública

Priorize:

* SSP-SP;
* Governo do Estado de São Paulo;
* Ministério da Justiça;
* SINESP;
* dados abertos municipais.

Procure indicadores como:

* homicídios;
* tentativa de homicídio;
* roubos;
* furtos;
* roubos de veículos;
* furtos de veículos;
* agressões;
* lesões corporais;
* ocorrências violentas;
* apreensões;
* ocorrências relacionadas a armas.

### Acidentes

Procure:

* CET-SP;
* DATASUS;
* SAMU, quando houver dados públicos;
* Polícia Rodoviária;
* órgãos municipais;
* bases públicas de acidentes de trânsito.

### Clima

Utilize fontes como:

* INMET;
* Open-Meteo;
* NASA POWER.

Variáveis:

* temperatura;
* precipitação;
* umidade;
* vento;
* condição climática.

### Contexto urbano

Quando possível, procure:

* feriados;
* eventos públicos;
* shows;
* carnaval;
* grandes eventos;
* manifestações;
* férias escolares;
* fluxo de transporte;
* trânsito;
* metrô;
* população.

Para cada fonte encontrada, informe:

* nome;
* URL;
* período;
* granularidade;
* variáveis;
* formato;
* possibilidade de download;
* limitações;
* licença, quando disponível.

*Não invente datasets ou URLs.*

---

# 4. DEFINIR A UNIDADE DE ANÁLISE

Defina explicitamente qual será a unidade de observação.

Priorize:

text
1 linha = 1 dia


Caso os dados permitam, considere também:

text
1 linha = 1 hora


ou:

text
1 linha = região + dia


Explique qual granularidade é estatisticamente mais adequada.

Se houver dados de ocorrências por horário, prefira uma análise temporal mais granular.

---

# 5. CONSTRUÇÃO DO DATASET FINAL

Construa um dataset analítico consolidado.

Exemplo:

| data | jogos | publico | classico | horario_jogo | chuva | temperatura | feriado | crimes | acidentes |
| ---- | ----: | ------: | -------: | ------------ | ----: | ----------: | ------: | -----: | --------: |

Crie também features derivadas.

## Features de futebol

* tem_jogo
* numero_jogos
* jogo_em_casa
* mandante
* visitante
* classico
* rivalidade
* horario_jogo
* jogo_noturno
* fim_de_semana
* campeonato
* fase_campeonato
* jogo_decisivo
* publico
* capacidade_estadio
* taxa_ocupacao
* resultado
* vitoria_mandante
* derrota_mandante
* empate
* cartoes
* expulsoes

## Features temporais

* dia da semana;
* fim de semana;
* mês;
* trimestre;
* ano;
* feriado;
* véspera de feriado;
* férias;
* dia anterior ao jogo;
* dia do jogo;
* dia posterior ao jogo.

Crie explicitamente:

text
D-1
D0
D+1


onde:

* D-1 = dia anterior ao jogo;
* D0 = dia do jogo;
* D+1 = dia seguinte.

Isso permitirá investigar se o efeito acontece antes, durante ou depois da partida.

---

# 6. ANÁLISE EXPLORATÓRIA DE DADOS — EDA

Faça uma análise exploratória completa.

Inclua:

### Qualidade

* missing values;
* duplicidades;
* outliers;
* inconsistências;
* valores impossíveis;
* distribuição temporal.

### Estatística descritiva

Calcule:

* média;
* mediana;
* desvio padrão;
* mínimo;
* máximo;
* quartis;
* coeficiente de variação.

### Distribuições

Analise:

* distribuição de crimes;
* distribuição de acidentes;
* distribuição do número de jogos;
* distribuição do público.

### Séries temporais

Crie gráficos de:

* crimes ao longo do tempo;
* acidentes ao longo do tempo;
* jogos ao longo do tempo;
* crimes vs jogos;
* acidentes vs jogos.

---

# 7. COMPARAÇÃO JOGO VS NÃO JOGO

Essa é uma das análises mais importantes.

Compare:

text
Dias com jogo
vs
Dias sem jogo


Para:

* crimes;
* violência;
* acidentes.

Calcule:

* média;
* mediana;
* diferença absoluta;
* diferença percentual;
* distribuição;
* intervalo de confiança.

Depois faça a comparação:

text
Dias de clássico
vs
Dias de jogos comuns


e:

text
Jogos noturnos
vs
Jogos diurnos


e:

text
Jogos com alto público
vs
Jogos com baixo público


---

# 8. ANÁLISE ESTATÍSTICA

Não conclua que futebol causa violência apenas porque existe correlação.

Calcule:

* Pearson;
* Spearman;
* correlação parcial, quando aplicável.

Faça testes estatísticos apropriados.

Considere:

* Mann-Whitney;
* t-test;
* Kruskal-Wallis;
* ANOVA;
* teste de proporções.

Escolha o teste com base na distribuição dos dados.

Informe:

text
H0
H1
estatística do teste
p-value
efeito
interpretação


Além do p-value, calcule *effect size* quando aplicável.

---

# 9. ANÁLISE DE DEFASAGEM TEMPORAL

Investigue se existe efeito:

text
D-2
D-1
D0
D+1
D+2


Por exemplo:

text
crime(D0) vs jogo(D0)
crime(D+1) vs jogo(D0)
crime(D-1) vs jogo(D0)


Faça análise de correlação cruzada e outras técnicas adequadas.

Objetivo:

descobrir *quando o impacto potencial é maior*.

---

# 10. ANÁLISE ESPACIAL

Se houver latitude/longitude, bairro, distrito policial ou região:

analise:

* concentração de ocorrências;
* distância do estádio;
* bairros próximos ao estádio;
* regiões com maior aumento relativo em dias de jogo.

Crie mapas quando os dados permitirem.

Compare:

text
região próxima ao estádio
vs
região distante do estádio


---

# 11. DEFINIÇÃO DE "PICO"

Não defina arbitrariamente o que é um pico.

Teste diferentes abordagens.

### Opção 1 — Percentil

Exemplo:

text
pico = ocorrência acima do percentil 90


Também avalie:

text
P95
P90


### Opção 2 — Z-score

text
z > 2


### Opção 3 — média móvel

Compare o valor observado com uma média móvel histórica.

Escolha a metodologia mais adequada e justifique.

---

# 12. FEATURE ENGINEERING

Crie features robustas.

Inclua:

### Futebol

* número de jogos;
* clássico;
* público;
* taxa de ocupação;
* horário;
* importância;
* resultado.

### Temporais

* dia da semana;
* mês;
* feriado;
* fim de semana;
* tendência temporal;
* sazonalidade.

### Clima

* temperatura;
* chuva;
* umidade;
* vento.

### Histórico

Crie lags:

text
crime_t-1
crime_t-7
crime_t-14
crime_t-28


e médias móveis:

text
rolling_mean_7
rolling_mean_14
rolling_mean_28


*Cuidado extremo com data leakage.*

Nenhuma feature pode utilizar informação que só estaria disponível depois do momento da previsão.

---

# 13. BASELINES

Antes de utilizar Machine Learning, crie modelos baseline.

Exemplos:

### Regressão

* média histórica;
* média móvel;
* mesmo dia da semana anterior.

### Classificação

* sempre prever classe majoritária;
* Logistic Regression.

Compare todos os modelos de ML contra esses baselines.

---

# 14. MODELOS DE MACHINE LEARNING

Teste pelo menos:

### Modelo 1

Decision Tree

### Modelo 2

Random Forest

### Modelo 3

XGBoost

### Modelo 4

LightGBM ou CatBoost

### Modelo 5

Logistic Regression

Se fizer sentido para os dados, considere:

* Gradient Boosting;
* HistGradientBoosting;
* modelos Poisson/Negative Binomial para contagens.

Não utilize modelos complexos apenas por serem sofisticados.

Escolha o modelo final com base em desempenho e interpretabilidade.

---

# 15. SÉRIES TEMPORAIS

Como os dados possuem dimensão temporal, *não faça um train_test_split aleatório*.

Use divisão temporal.

Exemplo:

text
Train: 2018–2023
Validation: 2024
Test: 2025


Adapte as datas ao período real disponível.

Considere:

* TimeSeriesSplit;
* walk-forward validation;
* backtesting.

Explique por que essa abordagem é necessária.

---

# 16. MÉTRICAS

## Regressão

Calcule:

* MAE;
* RMSE;
* R²;
* MAPE, apenas quando apropriado;
* SMAPE, se necessário.

## Classificação

Calcule:

* Accuracy;
* Precision;
* Recall;
* F1;
* ROC-AUC;
* PR-AUC;
* matriz de confusão.

Como o objetivo é identificar *picos*, dê atenção especial ao:

text
Recall
Precision
F1
PR-AUC


Não escolha o modelo apenas pela Accuracy.

---

# 17. OTIMIZAÇÃO DOS MODELOS

Faça tuning de hiperparâmetros utilizando:

* RandomizedSearchCV;
* GridSearchCV;
* ou Optuna.

Mas o processo de tuning também deve respeitar a temporalidade.

Não permita que dados futuros contaminem o treinamento.

---

# 18. INTERPRETABILIDADE

Depois de treinar o melhor modelo, explique:

### Quais variáveis mais influenciam a previsão?

Utilize:

* feature importance;
* permutation importance;
* SHAP.

Responda perguntas como:

> O número de jogos é realmente importante?

> Clássicos possuem maior impacto?

> O horário do jogo importa?

> Público influencia?

> Chuva explica mais acidentes do que futebol?

> O dia da semana é mais importante que o jogo?

---

# 19. ANÁLISE DE CENÁRIOS

Depois do modelo final, faça simulações.

Exemplo:

text
Cenário A:
Domingo + jogo comum + 20 mil pessoas

Cenário B:
Domingo + clássico + 50 mil pessoas

Cenário C:
Quarta-feira + jogo noturno + 40 mil pessoas

Cenário D:
Domingo + clássico + chuva


Estime o risco esperado de pico em cada cenário.

Deixe claro que isso representa *previsão/modelagem*, e não causalidade comprovada.

---

# 20. ANÁLISE DE CAUSALIDADE

Se os dados permitirem, vá além da correlação.

Considere metodologias como:

* Difference-in-Differences;
* Propensity Score;
* Interrupted Time Series;
* regressões com controles;
* Event Study.

Controle possíveis fatores de confusão:

* dia da semana;
* feriado;
* clima;
* tendência temporal;
* sazonalidade;
* eventos simultâneos.

Se os dados não permitirem inferência causal confiável, diga explicitamente:

> "Os resultados indicam associação, mas não permitem afirmar causalidade."

---

# 21. CÓDIGO

Forneça código Python completo e executável.

Utilize preferencialmente:

python
pandas
numpy
matplotlib
scipy
statsmodels
scikit-learn
xgboost
lightgbm
shap


Quando fizer sentido, utilize:

python
geopandas
folium


Organize o projeto em módulos:

text
01_ingestao.py
02_limpeza.py
03_eda.py
04_feature_engineering.py
05_modelagem.py
06_avaliacao.py
07_interpretabilidade.py
08_previsao.py


Se estiver trabalhando em Jupyter Notebook, organize por células/seções equivalentes.

---

# 22. ESTRUTURA DO PIPELINE

O pipeline final deve seguir:

text
Dados brutos
      ↓
Data Quality
      ↓
Integração
      ↓
EDA
      ↓
Feature Engineering
      ↓
Definição de pico
      ↓
Baseline
      ↓
Modelos ML
      ↓
Validação temporal
      ↓
Hyperparameter tuning
      ↓
Avaliação
      ↓
SHAP / interpretação
      ↓
Previsão
      ↓
Análise dos resultados


---

# 23. RESULTADOS ESPERADOS

Ao final, responda objetivamente:

1. Existe associação entre jogos de futebol e violência?
2. Existe associação entre jogos e acidentes?
3. Clássicos apresentam maior risco?
4. Jogos noturnos apresentam maior risco?
5. O público influencia?
6. Qual é o período de maior risco: antes, durante ou depois do jogo?
7. Quais variáveis mais explicam os picos?
8. Qual modelo apresentou melhor desempenho?
9. Qual é o Recall para identificação de picos?
10. É possível prever um pico com antecedência?
11. Qual é a margem de erro da previsão?
12. Quais são as limitações do estudo?

---

# 24. VISUALIZAÇÕES FINAIS

Crie gráficos profissionais:

1. série temporal de crimes;
2. série temporal de acidentes;
3. jogos ao longo do tempo;
4. crimes em dias com/sem jogos;
5. acidentes em dias com/sem jogos;
6. clássico vs jogo comum;
7. jogo diurno vs noturno;
8. heatmap por dia da semana e horário;
9. distribuição de ocorrências;
10. importância das features;
11. SHAP summary plot;
12. matriz de confusão;
13. curva Precision-Recall;
14. curva ROC;
15. previsão vs observado.

---

# 25. RELATÓRIO FINAL

Produza uma conclusão com estrutura acadêmica:

## Introdução

Contextualização do problema.

## Objetivo

Objetivo geral e objetivos específicos.

## Dados

Descrição das fontes e variáveis.

## Metodologia

Explique:

* limpeza;
* integração;
* EDA;
* estatística;
* feature engineering;
* Machine Learning;
* validação temporal.

## Resultados

Apresente os principais resultados quantitativos.

## Modelo

Mostre:

* melhor algoritmo;
* métricas;
* principais features;
* limitações.

## Discussão

Interprete os resultados sem confundir correlação com causalidade.

## Conclusão

Responda às perguntas de pesquisa.

## Limitações

Discuta:

* qualidade dos dados;
* variáveis não observadas;
* mudanças na política de segurança;
* subnotificação;
* diferenças de granularidade;
* possíveis confundidores;
* limitações da inferência causal.

## Trabalhos futuros

Sugira:

* dados horários;
* dados geográficos;
* transporte;
* fluxo de torcedores;
* dados de redes sociais;
* modelos espaço-temporais;
* causal inference;
* sistemas de alerta.

---

# 26. REGRAS IMPORTANTES

### Regra 1

Não invente dados.

### Regra 2

Não invente resultados.

### Regra 3

Não invente URLs ou fontes.

### Regra 4

Toda fonte externa deve ser identificada.

### Regra 5

Diferencie claramente:

text
correlação
associação
predição
causalidade


### Regra 6

Evite data leakage.

### Regra 7

Não use random train/test split em séries temporais.

### Regra 8

Não escolha o modelo apenas pela Accuracy.

### Regra 9

Sempre compare com baseline.

### Regra 10

Se os dados forem insuficientes para determinada análise, explique a limitação em vez de fabricar uma solução.

---

# 27. PRIMEIRA ENTREGA

Comece o trabalho seguindo esta ordem:

### Etapa 1

Identifique todos os dados disponíveis.

### Etapa 2

Pesquise na internet por fontes adicionais confiáveis.

### Etapa 3

Apresente uma arquitetura de dados mostrando como as fontes serão cruzadas.

### Etapa 4

Defina o schema do dataset analítico final.

### Etapa 5

Forneça o código de ingestão e limpeza.

### Etapa 6

Forneça o código completo da EDA.

### Etapa 7

Faça a análise estatística.

### Etapa 8

Construa as features.

### Etapa 9

Defina a variável alvo.

### Etapa 10

Treine e compare os modelos.

### Etapa 11

Faça validação temporal.

### Etapa 12

Escolha o melhor modelo.

### Etapa 13

Faça interpretabilidade com SHAP.

### Etapa 14

Faça previsões e cenários.

### Etapa 15

Produza a conclusão acadêmica.

---

## IMPORTANTE

Não pule etapas.

Sempre explique *por que* determinada técnica está sendo utilizada.

Sempre apresente o código antes de apresentar o resultado quando estivermos trabalhando com dados reais.

Se houver arquivos CSV fornecidos pelo usuário, utilize os arquivos reais e não crie dados fictícios para substituir informações ausentes.

O objetivo final é entregar um projeto que possa ser reproduzido por outro cientista de dados e defendido tecnicamente em uma apresentação acadêmica.
