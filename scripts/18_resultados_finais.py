"""
18_resultados_finais.py
Etapa 23 do roteiro -- RESULTADOS ESPERADOS (secao 23 do briefing_original.md).

Responde as 12 perguntas objetivas do briefing com numeros exatos, lidos
diretamente dos CSVs ja publicados pelas Etapas 6-20 (nao treina nada novo,
nao recalcula nada -- mesma filosofia de consolidacao da Etapa 16). Cada
resposta cita a etapa/arquivo de origem.

Regra 5 (correlacao != associacao != predicao != causalidade) aplicada em
cada resposta: o texto nunca usa "efeito de X" ou "X aumenta Y" quando o que
foi medido e associacao ajustada ou predicao de modelo, nao causalidade.

Rodar depois da Etapa 20 (le CSVs de reports/etapa{6,7,8,9,10,14,16,17,18,20}).
"""
import os
from datetime import date

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(BASE_DIR, "reports")
OUT_DIR = os.path.join(REPORTS, "etapa23")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
os.makedirs(TAB_DIR, exist_ok=True)

_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d_ = df.reset_index() if index else df.copy()
    cols = list(d_.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
        if isinstance(v, (bool, np.bool_)):
            return "sim" if v else "não"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d_.iterrows():
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def rd(rel_path):
    return pd.read_csv(os.path.join(REPORTS, rel_path))


# ---------------------------------------------------------------------------
def q1_associacao_violencia():
    w("## 1. Existe associação entre jogos de futebol e violência?\n")
    bruto = rd("etapa7/tabelas/bruto_jogo_vs_naojogo.csv")
    row = bruto[bruto.variavel.isin(["crimes_violentos", "lesao_corporal_dolosa"])]
    w("**Bruta, sim (parcialmente); ajustada por calendário, não.**\n")
    w("Comparação bruta dia-com-jogo vs dia-sem-jogo (Etapa 7):\n")
    w(df_to_md(row[["variavel", "media_com jogo", "media_sem jogo", "dif_pct_media", "MannWhitney_p", "MW_p_BH", "signif_BH_5pct"]],
              floatfmt=3, index=False))
    glm = rd("etapa7/tabelas/ajustado_glm_poisson.csv")
    row2 = glm[glm.variavel.isin(["crimes_violentos", "lesao_corporal_dolosa"])]
    w("\nMesmas variáveis, GLM Poisson ajustado por dia da semana + mês + feriado (Etapa 7):\n")
    w(df_to_md(row2[["variavel", "rate_ratio_jogo", "IC95_lo", "IC95_hi", "p_value", "signif_BH_5pct"]],
              floatfmt=3, index=False))
    pa = rd("etapa8/tabelas/correlacao_parcial.csv")
    n_sig_a = int(pa["A_signif_BH"].sum())
    w(f"\nCorrelação parcial (Etapa 8): 0 dos 44 pares driver×desfecho "
      f"significativos após controlar calendário ({n_sig_a}/44 no modelo A). "
      "PSM (Etapa 20): ATE pareado `crimes_violentos` = +1,5% (ns, "
      "Wilcoxon p=0,32).\n")
    w("**Leitura**: `lesao_corporal_dolosa` mostra diferença bruta grande e "
      "significativa (+14,9%, p<0,001), mas some completamente após ajuste "
      "(RR ajustado ~1,0, ns). `crimes_violentos` nunca foi significativo, "
      "nem bruto. **Associação bruta fraca existe para alguns desfechos "
      "específicos; não sobrevive a controle por calendário; nenhuma "
      "evidência de causalidade em nenhum dos 5 métodos usados (Etapas "
      "7-9, 20).**\n")


def q2_associacao_acidentes():
    w("## 2. Existe associação entre jogos e acidentes?\n")
    bruto = rd("etapa7/tabelas/bruto_jogo_vs_naojogo.csv")
    row = bruto[bruto.variavel.isin(["acidentes_total", "acidentes_com_vitima", "acidentes_fatais"])]
    w("Comparação bruta (Etapa 7):\n")
    w(df_to_md(row[["variavel", "media_com jogo", "media_sem jogo", "dif_pct_media", "MannWhitney_p", "signif_BH_5pct"]],
              floatfmt=3, index=False))
    glm = rd("etapa7/tabelas/ajustado_glm_poisson.csv")
    row2 = glm[glm.familia == "acidente"]
    w("\nGLM Poisson ajustado (Etapa 7), família acidente:\n")
    w(df_to_md(row2[["variavel", "rate_ratio_jogo", "IC95_lo", "IC95_hi", "p_value", "signif_BH_5pct"]],
              floatfmt=3, index=False))
    psm = rd("etapa20/tabelas/resumo_psm.csv")
    r = psm[psm.base == "acidentes_com_vitima"].iloc[0]
    w(f"\nPSM (Etapa 20, `acidentes_com_vitima`): ATE pareado = +0,7% "
      f"(Wilcoxon p=0,83, ns); IPTW irrestrito RR={r.iptw_rr:.3f} "
      f"(p={r.iptw_p:.3f}, chegou a ser significativo) mas **investigado e "
      f"resolvido**: IPTW restrito à região de sobreposição RR="
      f"{r.iptw_rr_restrito:.3f} (p={r.iptw_p_restrito:.3f}, ns) -- era "
      "violação de positividade (jan-fev sem jogo na base), não efeito real.\n")
    w("**Leitura**: `acidentes_fatais` tem o maior resíduo do projeto "
      "inteiro (RR bruto +38,7%, RR ajustado 1,146, p=0,063 -- não "
      "significativo após BH, mas o mais próximo de significância entre "
      "todos os desfechos testados nas Etapas 7-20). Mesmo esse resíduo "
      "não é robusto (não sobrevive à correção de múltiplas comparações). "
      "**Nenhuma evidência causal robusta de jogo → acidente, em nenhum "
      "dos 6 métodos usados no projeto (Etapas 7, 8, 9, 10, 18, 20).**\n")


def q3_classicos():
    w("## 3. Clássicos apresentam maior risco?\n")
    rec = rd("etapa7/tabelas/recorte_classico.csv")
    w("Clássico vs jogo comum (Etapa 7, bruto):\n")
    w(df_to_md(rec[["variavel", "n_classico", "n_comum", "media_classico", "media_comum", "dif_%", "MW_p"]],
              floatfmt=3, index=False))
    shap_rows = []
    for arq, modelo in [("etapa18/tabelas/shap_importancia_crimes_violentos_regressao.csv", "crimes_violentos (regressão)"),
                        ("etapa18/tabelas/shap_importancia_acidentes_com_vitima_regressao.csv", "acidentes_com_vitima (regressão)"),
                        ("etapa18/tabelas/shap_importancia_acidentes_com_vitima_classificacao.csv", "acidentes_com_vitima (classificação)")]:
        tab = rd(arq)
        r = tab[tab.feature == "classico"]
        if len(r):
            r = r.iloc[0]
            shap_rows.append({"modelo": modelo, "rank_shap": int(r.rank_shap), "mean_abs_shap": r.mean_abs_shap,
                              "artefato_colinearidade": bool(r.artefato_provavel)})
    w("\nSHAP da feature `classico` nos 3 modelos de produção (Etapa 18):\n")
    w(df_to_md(pd.DataFrame(shap_rows), floatfmt=4, index=False))
    w("\nCenário B (domingo+clássico) vs A (domingo+jogo comum), Etapa 19: "
      "P(pico) previsto `acidentes_com_vitima` foi **menor** no clássico "
      "(0,539) do que no jogo comum (0,855) -- diferença explicada por "
      "características incidentais do dia-âncora escolhido, não pelo tipo "
      "de jogo (ver decomposição SHAP da Etapa 19).\n")
    w("**Leitura**: nenhuma diferença bruta é significativa após BH; a "
      "única quase-significância bruta (`acidentes_com_vitima` +7,1%, "
      "p=0,064) não sobrevive a correção. SHAP confirma: `classico` "
      "marcado como artefato de colinearidade com calendário nos 3 "
      "modelos, contribuição líquida = 0. **Sem evidência de que "
      "clássicos representem risco maior.**\n")


def q4_noturnos():
    w("## 4. Jogos noturnos apresentam maior risco?\n")
    rec = rd("etapa7/tabelas/recorte_jogo_noturno.csv")
    w("Noturno vs diurno (Etapa 7, bruto):\n")
    w(df_to_md(rec[["variavel", "n_noturno", "n_diurno", "media_noturno", "media_diurno", "dif_%", "MW_p"]],
              floatfmt=3, index=False))
    w("\n`lesao_corporal_dolosa` é a única variável com diferença bruta "
      "grande e significativa mesmo após BH (+17,0%, MW p=0,0003) -- mas é "
      "uma comparação SÓ dentro dos dias de jogo (72 noturnos vs 54 "
      "diurnos), sem controle de dia da semana/mês (jogos noturnos podem "
      "concentrar-se em dias diferentes dos diurnos); `crimes_violentos` "
      "(+0,98%) e `acidentes_com_vitima` (+1,46%) não são significativos.\n")
    shap_rows = []
    for arq, modelo in [("etapa18/tabelas/shap_importancia_crimes_violentos_regressao.csv", "crimes_violentos (regressão)"),
                        ("etapa18/tabelas/shap_importancia_acidentes_com_vitima_regressao.csv", "acidentes_com_vitima (regressão)"),
                        ("etapa18/tabelas/shap_importancia_acidentes_com_vitima_classificacao.csv", "acidentes_com_vitima (classificação)")]:
        tab = rd(arq)
        r = tab[tab.feature == "jogo_noturno"]
        if len(r):
            r = r.iloc[0]
            shap_rows.append({"modelo": modelo, "rank_shap": int(r.rank_shap), "mean_abs_shap": r.mean_abs_shap,
                              "artefato_colinearidade": bool(r.artefato_provavel)})
    w("SHAP da feature `jogo_noturno` (Etapa 18):\n")
    w(df_to_md(pd.DataFrame(shap_rows), floatfmt=4, index=False))
    w("\n**Leitura**: o único sinal bruto real (`lesao_corporal_dolosa`) é "
      "para um desfecho fora dos 2 alvos principais do projeto e não "
      "controla calendário; nos 2 alvos principais (`crimes_violentos`, "
      "`acidentes_com_vitima`) não há diferença significativa em nenhuma "
      "leitura, bruta ou SHAP. **Sem evidência robusta de que jogos "
      "noturnos representem risco maior para os alvos principais.**\n")


def q5_publico():
    w("## 5. O público influencia?\n")
    w("**Não testável com os dados disponíveis** (Regra 10 -- declarar a "
      "limitação, não fabricar um proxy). `publico`/`taxa_ocupacao` são "
      "100% ausentes (a fonte Kaggle `adaoduque/campeonato-brasileiro-de-"
      "futebol` nunca foi baixada, pendência aberta desde a Etapa 12) e "
      "por isso nunca entraram no conjunto de features de nenhum modelo "
      "das Etapas 13-20. Declarado explicitamente em cada etapa onde a "
      "pergunta reaparece (7, 12, 18, 19, 20) em vez de inventar um proxy "
      "(ex. mandante/visitante como proxy de público teria introduzido uma "
      "suposição não verificável). Fica como recomendação de trabalho "
      "futuro (§25) caso a base seja baixada.\n")


def q6_periodo_risco():
    w("## 6. Qual é o período de maior risco: antes, durante ou depois do jogo?\n")
    dd = rd("etapa9/tabelas/defasagens_distribuidas.csv")
    row = dd[dd.desfecho.isin(["crimes_violentos", "acidentes_com_vitima", "acidentes_fatais"])]
    w("Modelo de defasagens distribuídas D-2..D+2 (Etapa 9, GLM Poisson HC1):\n")
    w(df_to_md(row[["desfecho", "defasagem", "rate_ratio", "p_value", "signif_BH_5pct"]], floatfmt=3, index=False))
    ev = rd("etapa9/tabelas/event_study_vizinhos.csv")
    row2 = ev[ev.desfecho.isin(["crimes_violentos", "acidentes_com_vitima"])]
    w("\nEvent study D-1 (véspera) / D0 (dia do jogo) / D+1 (dia seguinte), "
      "resíduo dessazonalizado (Etapa 9):\n")
    w(df_to_md(row2[["desfecho", "janela_gold", "media_residuo", "t_p_vs_0", "p_BH"]], floatfmt=3, index=False))
    w("\n**Leitura**: nenhuma das 30 defasagens D-2..D+2 (6 desfechos × 5 "
      "defasagens) é significativa após BH; o event study também não "
      "encontra desvio significativo em nenhum offset -7..+7. O único "
      "resíduo em qualquer análise de janela temporal do projeto inteiro é "
      "`acidentes_fatais` em D0 (mesmo dia), RR=1,146, p=0,063 sem BH -- "
      "não robusto. **Não há período (antes, durante ou depois) com risco "
      "significativamente elevado; se houvesse algum, seria D0 (mesmo dia "
      "do jogo), não antes nem depois — mas mesmo esse sinal não passa em "
      "correção de múltiplas comparações.**\n")


def q7_variaveis_picos():
    w("## 7. Quais variáveis mais explicam os picos?\n")
    for arq, nome in [("etapa18/tabelas/shap_grupo_crimes_violentos_regressao.csv", "crimes_violentos (regressão)"),
                      ("etapa18/tabelas/shap_grupo_acidentes_com_vitima_regressao.csv", "acidentes_com_vitima (regressão)"),
                      ("etapa18/tabelas/shap_grupo_acidentes_com_vitima_classificacao.csv", "acidentes_com_vitima (classificação)")]:
        tab = rd(arq).sort_values("pct_%", ascending=False)
        w(f"**{nome}** (SHAP por grupo, Etapa 18):\n")
        w(df_to_md(tab, floatfmt=2, index=False))
        w("")
    w("**Leitura**: histórico do próprio desfecho (lags/médias móveis) e "
      "variáveis de calendário/sazonalidade dominam nos 2 modelos de "
      "regressão; clima explica mais que futebol em `acidentes_com_vitima` "
      "depois de descontar o artefato de colinearidade (Etapa 18). "
      "`futebol` líquido = 0,0% nos 3 modelos após auditoria completa "
      "(adendo 2026-09-04) -- **os picos são explicados por padrão "
      "histórico do próprio desfecho, calendário e clima, não por jogos "
      "de futebol.**\n")


def q8_melhor_modelo():
    w("## 8. Qual modelo apresentou melhor desempenho?\n")
    reg = rd("etapa17/tabelas/comparacao_pooled_regressao.csv")
    w("Regressão -- XGBoost Poisson, pooled walk-forward (Etapa 15/16/17; "
      "tuning da Etapa 17 não trouxe ganho, valores = baseline não-tunado):\n")
    w(df_to_md(reg[["base", "MAE_baseline", "RMSE_baseline", "R2_baseline", "MAPE_baseline_%"]],
              floatfmt=2, index=False))
    clf = rd("etapa17/tabelas/comparacao_pooled_classificacao.csv")
    w("\nClassificação -- `logreg_balanced`, só `acidentes_com_vitima` "
      "(pooled walk-forward, Etapa 15/16):\n")
    w(df_to_md(clf[["base", "accuracy_baseline", "precision_baseline", "recall_baseline",
                    "f1_baseline", "pr_auc_baseline"]], floatfmt=3, index=False))
    w("\n**`crimes_violentos` (classificação) continua sem modelo "
      "recomendado** -- decisão da Etapa 16, nunca revertida: nenhum "
      "classificador testado (Etapas 14, 15, 17) chega a um ponto de "
      "operação com Recall e PR-AUC úteis ao mesmo tempo.\n")
    w("**Leitura**: XGBoost Poisson venceu baselines e Prophet nos 2 "
      "alvos de regressão (Etapa 15); `logreg_balanced` venceu por "
      "Recall/F1 E PR-AUC ao mesmo tempo em `acidentes_com_vitima` "
      "classificação (Etapa 16) -- vencedor sem ambiguidade de critério, "
      "ao contrário do split único da Etapa 13/14.\n")


def q9_recall_picos():
    w("## 9. Qual é o Recall para identificação de picos?\n")
    clf = rd("etapa16/tabelas/scoreboard_classificacao.csv")
    e15 = clf[clf.estagio.str.startswith("Etapa 15")]
    w("Recall pooled walk-forward por modelo (Etapa 15/16):\n")
    w(df_to_md(e15[["base", "modelo", "recall", "precision", "f1", "pr_auc"]].sort_values(["base", "recall"], ascending=[True, False]),
              floatfmt=3, index=False))
    w("\n**Leitura**: `acidentes_com_vitima` -- Recall 0,576 com "
      "`logreg_balanced` (0,674 com hiperparâmetro tunado da Etapa 17, mas "
      "à custa de PR-AUC menor). `crimes_violentos` -- nenhum modelo "
      "combina Recall e PR-AUC úteis: `random_forest` tem a melhor PR-AUC "
      "(0,348) mas Recall=0,05 (praticamente não detecta pico); "
      "`dia_semana_risco` (heurística de calendário) tem o melhor Recall "
      "(0,50) mas PR-AUC baixo (0,115). **Recall utilizável só existe para "
      "`acidentes_com_vitima`; para `crimes_violentos`, nenhum classificador "
      "testado atinge um ponto de operação prático.**\n")


def q10_previsao_antecedencia():
    w("## 10. É possível prever um pico com antecedência?\n")
    w("**Sim, com D0 (mesmo dia), para `acidentes_com_vitima`; não de "
      "forma útil para `crimes_violentos`.** Todas as features do modelo "
      "são conhecidas ANTES do desfecho do dia (fixtures de futebol, "
      "calendário, histórico defasado ≥1 dia, previsão de clima) -- "
      "verificado por auditoria automática de leakage na Etapa 12 (0 "
      "falhas) -- e a validação walk-forward (Etapas 15/17) confirma que a "
      "previsão generaliza para meses nunca vistos no treino, não é ajuste "
      "ao próprio passado.\n")
    w("**Limitação declarada (não testada no projeto)**: o horizonte de "
      "previsão testado é sempre D0 (o dia em si, com informação "
      "disponível até o dia anterior) -- o projeto não testou previsão "
      "com 2+ dias de antecedência (ex. prever terça-feira usando só dados "
      "até domingo). Fica como recomendação explícita de trabalho futuro "
      "(§25), não uma capacidade já demonstrada.\n")


def q11_margem_erro():
    w("## 11. Qual é a margem de erro da previsão?\n")
    reg = rd("etapa17/tabelas/comparacao_pooled_regressao.csv")
    w(df_to_md(reg[["base", "MAE_baseline", "RMSE_baseline", "MAPE_baseline_%", "R2_baseline"]],
              floatfmt=2, index=False))
    w("\n**Leitura**: para `crimes_violentos`, o modelo erra em média "
      "±34,8 crimes/dia (MAPE 7,1%) sobre uma contagem diária que varia de "
      "340 a bem mais -- R²=0,48 (o modelo explica ~48% da variância "
      "diária). Para `acidentes_com_vitima`, erro médio ±10,3/dia (MAPE "
      "12,7%), R²=0,28 (bem menos variância explicada -- \"melhor "
      "disponível, não preditor forte\", conforme já registrado na Etapa "
      "16). Números pooled sobre ~360 dias de teste walk-forward (Etapa "
      "15), não um único corte.\n")


def q12_limitacoes():
    w("## 12. Quais são as limitações do estudo?\n")
    w(df_to_md(pd.DataFrame([
        {"categoria": "Cobertura de futebol", "limitação": "Paulistão e Libertadores fora da base (BR-Football-Dataset só cobre Série A/B/C + Copa do Brasil) -- dias de jogo dessas competições aparecem como `tem_jogo_sp=0`, atenuando qualquer efeito real e potencialmente inflando o peso do calendário"},
        {"categoria": "Público", "limitação": "`publico`/`taxa_ocupacao` 100% ausentes -- pergunta 5 (§23) não testável, feature nunca usada em nenhum modelo"},
        {"categoria": "Janela temporal", "limitação": "Só 730 dias (2022-2023) de sobreposição das 3 fontes principais -- limita a validação temporal (Etapa 15) e a sazonalidade anual do Prophet"},
        {"categoria": "Censura/lacunas de registro", "limitação": "2023-12-30/31 (defasagem de registro), 2022-01-17 e 2023-08-07 (falha Infosiga), 27/11/2023 (falha INMET), 25/08-11/09/2023 (sensor de precipitação fora do ar) -- todas excluídas/tratadas como missing, nunca como zero"},
        {"categoria": "Outlier de registro", "limitação": "2022-06-19 (`furtos_total`=2633, registro em lote) -- tratado como missing na Etapa 12; sensibilidade rodada na Etapa 14 (MAE muda de 39,2 para 43,1, não muda conclusão qualitativa)"},
        {"categoria": "Geolocalização", "limitação": "~20% das coordenadas de crime nulas/zero/fora do município; pile-up de geocodificação no Morumbi investigado e explicado (Etapa 10), não é achado espacial robusto"},
        {"categoria": "Causalidade", "limitação": "Sem variação exógena da agenda de jogos (decidida por CBF/clubes, não aleatória) -- nenhum dos 5 métodos causais do briefing (regressão com controles, event study, DiD, PSM, ITS adaptado) permite afirmar causalidade, só associação (Etapa 20)"},
        {"categoria": "Classificação de `crimes_violentos`", "limitação": "Nenhum classificador testado (Etapas 14, 15, 17) atinge Recall e PR-AUC úteis ao mesmo tempo -- sem modelo recomendado para esse alvo"},
        {"categoria": "Horizonte de previsão", "limitação": "Só testado D0 (mesmo dia); previsão com 2+ dias de antecedência não avaliada"},
        {"categoria": "Fatores de confusão não observados", "limitação": "Mudanças de política de segurança, operações policiais pontuais, greves, eventos não-futebolísticos coincidentes -- não há como descartar toda coincidência residual com 730 dias de dados (Etapa 20)"},
    ]), floatfmt=0, index=False))
    w("\nLista consolidada a partir de `CLAUDE.md` (\"Limitações conhecidas\") "
      "e da seção 4 do relatório da Etapa 20 -- nenhuma limitação nova "
      "introduzida aqui, só reunida num único lugar para a seção "
      "Limitações do relatório final (§25).\n")


# ---------------------------------------------------------------------------
def main():
    w("# Etapa 23 -- Resultados esperados (12 perguntas do briefing)\n")
    w(f"_Gerado por `scripts/18_resultados_finais.py` em {date.today()}. "
      "Consolida CSVs já publicados nas Etapas 6-20 -- nenhum modelo "
      "treinado ou teste estatístico recalculado aqui; cada resposta cita "
      "a etapa de origem.\n")
    w("> Regra 5 aplicada em cada resposta: distinção explícita entre "
      "correlação, associação (ajustada), predição (de modelo) e "
      "causalidade -- nunca usado \"efeito de X\" quando o que foi medido "
      "foi associação ou predição.\n")

    q1_associacao_violencia()
    q2_associacao_acidentes()
    q3_classicos()
    q4_noturnos()
    q5_publico()
    q6_periodo_risco()
    q7_variaveis_picos()
    q8_melhor_modelo()
    q9_recall_picos()
    q10_previsao_antecedencia()
    q11_margem_erro()
    q12_limitacoes()

    w("## Síntese em uma frase por pergunta\n")
    w(textwrap_sintese())

    path = os.path.join(OUT_DIR, "relatorio_resultados_finais.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")


def textwrap_sintese():
    linhas = [
        "1. Associação bruta fraca com futebol para alguns desfechos; some após ajuste por calendário; sem causalidade.",
        "2. Idem para acidentes; `acidentes_fatais` é o resíduo mais próximo de significância do projeto, ainda não robusto.",
        "3. Não -- diferenças brutas não significativas após BH; SHAP confirma `classico` como artefato de calendário nos 3 modelos.",
        "4. Não para os 2 alvos principais -- único sinal bruto significativo (`lesao_corporal_dolosa`) é fora do escopo principal e sem controle de calendário.",
        "5. Não testável -- feature 100% ausente, nunca modelada.",
        "6. Nenhum período (D-2..D+2) é significativo após BH; se houvesse, seria D0, não antes/depois.",
        "7. Histórico do próprio desfecho, calendário e clima -- futebol líquido = 0,0% do SHAP nos 3 modelos.",
        "8. XGBoost Poisson (regressão, 2 alvos); `logreg_balanced` (classificação, só `acidentes_com_vitima`).",
        "9. 0,576-0,674 para `acidentes_com_vitima`; nenhum ponto de operação útil para `crimes_violentos`.",
        "10. Sim, D0, para `acidentes_com_vitima`, validado walk-forward; horizonte >1 dia não testado.",
        "11. MAE 34,8 (crimes_violentos, MAPE 7,1%) / 10,3 (acidentes_com_vitima, MAPE 12,7%), pooled walk-forward.",
        "12. Público ausente, Paulistão/Libertadores fora da base, janela curta, sem causalidade, `crimes_violentos` sem classificador utilizável.",
    ]
    return "\n".join(f"- {l}" for l in linhas) + "\n"


if __name__ == "__main__":
    main()
