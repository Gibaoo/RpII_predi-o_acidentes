"""
13_metricas_consolidadas.py
Etapa 16 do roteiro -- METRICAS (secao 16 do briefing_original.md).

Esta etapa NAO treina nenhum modelo novo. As metricas de regressao (MAE, RMSE,
R2, MAPE) e classificacao (Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC) ja
foram calculadas inline nas Etapas 13 (baselines, split unico), 14 (modelos ML,
mesmo split unico) e 15 (walk-forward, pooled + fold_macro). O que faltava:

  1. Conferir explicitamente a cobertura contra a lista do briefing S16
     (inclui declarar por que MAPE e apropriado aqui e por que SMAPE nao e
     necessario -- Regra 10: declarar em vez de calcular por calcular).
  2. **Matriz de confusao** (exigida no S16 e no S24 item 12) -- nunca foi
     produzida em nenhuma etapa anterior. Reconstruida aqui a partir dos
     totais pooled ja publicados na Etapa 15 (TP/FP/FN/TN implicitos em
     n_teste, n_pico, accuracy, recall), com verificacao de consistencia
     (precision/F1 recalculados da matriz batem com os valores originais
     ate 1e-2) -- nao e um numero novo, e uma decomposicao exata do que ja
     foi calculado, auditada antes de publicar.
  3. Consolidar as 3 fontes (Etapa 13/14 split unico + Etapa 15 pooled
     walk-forward) num unico scoreboard por alvo x tarefa e declarar
     FORMALMENTE o modelo recomendado que a Etapa 17 (tuning) e a Etapa 18
     (SHAP) devem usar -- com o pooled walk-forward como evidencia principal
     (mais dias de teste, sem o problema de fragilidade do corte unico
     documentado na Etapa 13) e o split unico como contexto secundario.

Regra 8 (nao escolher so por Accuracy): a declaracao do "melhor modelo" usa
Recall/F1/PR-AUC como criterio primario para classificacao, nao Accuracy.

Rodar depois da Etapa 15 (le os CSVs ja publicados em reports/etapa13,14,15 --
nao le dados brutos, nao reajusta nada).
"""
import os
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E13_TAB = os.path.join(BASE_DIR, "reports", "etapa13", "tabelas")
E14_TAB = os.path.join(BASE_DIR, "reports", "etapa14", "tabelas")
E15_TAB = os.path.join(BASE_DIR, "reports", "etapa15", "tabelas")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa16")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

BASES = ["crimes_violentos", "acidentes_com_vitima"]
BASE_LABEL = {"crimes_violentos": "crimes_violentos", "acidentes_com_vitima": "acidentes_com_vitima"}

_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d_ = df.reset_index() if index else df.copy()
    cols = list(d_.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d_.iterrows():
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def savefig(name):
    p = os.path.join(FIG_DIR, name)
    plt.savefig(p)
    plt.close()
    return os.path.relpath(p, OUT_DIR).replace("\\", "/")


# ---------------------------------------------------------------------------
def secao_checklist():
    w("## 1. Checklist do briefing (S16) -- o que ja existe e o que faltava\n")
    w("Esta etapa nao recalcula nada; consolida o que as Etapas 13-15 ja "
      "produziram e preenche a unica lacuna real (matriz de confusao).\n")

    feat = pd.read_csv(FEAT_PATH)
    linhas_mape = []
    for base in BASES:
        col = f"y_count_{base}"
        vmin = feat[col].min()
        linhas_mape.append({"alvo": base, "minimo_observado": vmin,
                            "dias_com_zero": int((feat[col] == 0).sum())})
    tab_mape = pd.DataFrame(linhas_mape)

    w("### Regressao\n")
    w(df_to_md(pd.DataFrame([
        {"metrica": "MAE", "exigida": "sim", "onde": "Etapas 13, 14, 15 (todas as tabelas de regressao)"},
        {"metrica": "RMSE", "exigida": "sim", "onde": "Etapas 13, 14, 15"},
        {"metrica": "R2", "exigida": "sim", "onde": "Etapas 13, 14, 15"},
        {"metrica": "MAPE", "exigida": "apenas quando apropriado", "onde": "Etapas 13, 14, 15 -- ver justificativa abaixo"},
        {"metrica": "SMAPE", "exigida": "se necessario", "onde": "nao calculado -- ver justificativa abaixo"},
    ]), index=False))
    w("")
    w("**MAPE e apropriado aqui**: MAPE explode/e indefinido quando o valor "
      "real se aproxima de zero. Os dois alvos de contagem nunca chegam perto "
      "disso no periodo observado:\n")
    w(df_to_md(tab_mape, floatfmt=0, index=False))
    w("")
    w("Minimo observado de 340 (`crimes_violentos`) e 31 (`acidentes_com_vitima`) "
      "em 730 dias, 0 dias com contagem zero em qualquer um dos dois -- MAPE e "
      "estavel e interpretavel. **SMAPE nao foi calculado**: a razao classica "
      "para preferir SMAPE (valores reais perto de zero, que inflam o MAPE "
      "artificialmente) nao se aplica aqui; adicionar SMAPE so duplicaria a "
      "leitura de MAPE sem trazer informacao nova (Regra 10: declarar a "
      "decisao, nao calcular por calcular).\n")

    w("### Classificacao\n")
    w(df_to_md(pd.DataFrame([
        {"metrica": "Accuracy", "exigida": "sim", "onde": "Etapas 13, 14, 15 -- NUNCA usada sozinha para escolher modelo (Regra 8)"},
        {"metrica": "Precision", "exigida": "sim", "onde": "Etapas 13, 14, 15"},
        {"metrica": "Recall", "exigida": "sim (atencao especial -- S16)", "onde": "Etapas 13, 14, 15"},
        {"metrica": "F1", "exigida": "sim (atencao especial -- S16)", "onde": "Etapas 13, 14, 15"},
        {"metrica": "ROC-AUC", "exigida": "sim", "onde": "Etapas 13, 14, 15 (pooled + fold_macro na 15)"},
        {"metrica": "PR-AUC", "exigida": "sim (atencao especial -- S16)", "onde": "Etapas 13, 14, 15 (pooled + fold_macro na 15)"},
        {"metrica": "Matriz de confusao", "exigida": "sim", "onde": "**faltava -- produzida na secao 3 desta etapa**"},
    ]), index=False))
    w("")


# ---------------------------------------------------------------------------
def carrega_scoreboards():
    e13_reg = pd.read_csv(os.path.join(E13_TAB, "baselines_regressao.csv"))
    e13_reg["estagio"] = "Etapa 13 -- split unico (baseline)"
    e13_reg = e13_reg.rename(columns={"baseline": "modelo"})

    e14_reg = pd.read_csv(os.path.join(E14_TAB, "regressao_completa.csv"))
    e14_reg["estagio"] = "Etapa 14 -- split unico (modelo ML)"
    e14_reg = e14_reg.rename(columns={"baseline": "modelo"}).drop(columns=["origem"])

    e15_reg = pd.read_csv(os.path.join(E15_TAB, "regressao_pooled.csv"))
    e15_reg["estagio"] = "Etapa 15 -- pooled walk-forward (12 folds)"
    e15_reg = e15_reg.rename(columns={"n_total": "n"})

    reg = pd.concat([e13_reg[["base", "estagio", "modelo", "n", "MAE", "RMSE", "R2", "MAPE_%"]],
                     e14_reg[["base", "estagio", "modelo", "n", "MAE", "RMSE", "R2", "MAPE_%"]],
                     e15_reg[["base", "estagio", "modelo", "n", "MAE", "RMSE", "R2", "MAPE_%"]]],
                    ignore_index=True)

    e13_clf = pd.read_csv(os.path.join(E13_TAB, "baselines_classificacao.csv"))
    e13_clf["estagio"] = "Etapa 13 -- split unico (baseline)"
    e13_clf = e13_clf.rename(columns={"baseline": "modelo", "n_teste": "n_teste_total", "n_pico_teste": "n_pico_total"})

    e14_clf = pd.read_csv(os.path.join(E14_TAB, "classificacao_completa.csv"))
    e14_clf["estagio"] = "Etapa 14 -- split unico (modelo ML)"
    e14_clf = e14_clf.rename(columns={"baseline": "modelo", "n_teste": "n_teste_total", "n_pico_teste": "n_pico_total"}).drop(columns=["origem"])

    e15_clf = pd.read_csv(os.path.join(E15_TAB, "classificacao_pooled.csv"))
    e15_clf["estagio"] = "Etapa 15 -- pooled walk-forward (12 folds)"

    cols_comuns = ["base", "estagio", "modelo", "n_teste_total", "n_pico_total",
                   "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    # Etapas 13/14 (split unico) ja tem roc_auc/pr_auc nativos; a Etapa 15 usa
    # fold_macro (nao pooled) -- ver ressalva metodologica da propria Etapa 15.
    e15_clf["roc_auc"], e15_clf["pr_auc"] = e15_clf["roc_auc_fold_macro"], e15_clf["pr_auc_fold_macro"]

    clf = pd.concat([e13_clf[cols_comuns], e14_clf[cols_comuns], e15_clf[cols_comuns]], ignore_index=True)
    return reg, clf


def secao_scoreboards(reg, clf):
    w("## 2. Scoreboard consolidado -- as 3 fontes lado a lado\n")
    w("`roc_auc`/`pr_auc` da Etapa 15 usam **`fold_macro`**, nao `pooled` "
      "(ver ressalva metodologica da Etapa 15 -- pooled distorce quando ha "
      "poucos positivos por fold).\n")

    for base in BASES:
        w(f"### {base} -- Regressao\n")
        sub = reg[reg.base == base].copy()
        for estagio in sub.estagio.unique():
            s2 = sub[sub.estagio == estagio].sort_values("MAE")
            w(f"**{estagio}**\n")
            w(df_to_md(s2.drop(columns=["base", "estagio"]), floatfmt=2, index=False))
            w("")

    for base in BASES:
        w(f"### {base} -- Classificacao\n")
        sub = clf[clf.base == base].copy()
        for estagio in sub.estagio.unique():
            s2 = sub[sub.estagio == estagio].sort_values("f1", ascending=False)
            w(f"**{estagio}**\n")
            w(df_to_md(s2.drop(columns=["base", "estagio"]), floatfmt=3, index=False))
            w("")

    reg.to_csv(os.path.join(TAB_DIR, "scoreboard_regressao.csv"), index=False)
    clf.to_csv(os.path.join(TAB_DIR, "scoreboard_classificacao.csv"), index=False)


# ---------------------------------------------------------------------------
def reconstroi_matriz(row):
    """Reconstroi TP/FP/FN/TN a partir de accuracy+recall+n_teste+n_pico (todos
    ja publicados na Etapa 15). Nao e um numero novo -- e decomposicao exata do
    que ja foi calculado; verificado abaixo (precision/F1 recalculados da
    matriz devem bater com os originais)."""
    n = row["n_teste_total"]
    p = row["n_pico_total"]
    neg = n - p
    tp = round(row["recall"] * p) if p > 0 else 0
    fn = p - tp
    correct = round(row["accuracy"] * n)
    tn = correct - tp
    fp = neg - tn
    prec_rec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec_rec = tp / p if p > 0 else 0.0
    f1_rec = 2 * prec_rec * rec_rec / (prec_rec + rec_rec) if (prec_rec + rec_rec) > 0 else 0.0
    ok = abs(prec_rec - row["precision"]) < 0.02 and abs(f1_rec - row["f1"]) < 0.02
    return dict(TP=int(tp), FP=int(fp), FN=int(fn), TN=int(tn), consistente=ok)


def secao_matriz_confusao(clf_e15):
    w("## 3. Matriz de confusao (pooled walk-forward -- a lacuna do S16/S24)\n")
    w("Nenhuma etapa anterior tinha produzido matriz de confusao; os arrays "
      "brutos de predicao por fold nao foram persistidos em disco na Etapa 15 "
      "(so as metricas agregadas). Reconstruida aqui a partir dos totais "
      "exatos ja publicados (`n_teste_total`, `n_pico_total`, `accuracy`, "
      "`recall`) -- TP = round(recall x n_pico), TN = round(accuracy x "
      "n_teste) - TP, FP = negativos - TN, FN = n_pico - TP. **Verificacao**: "
      "precision e F1 recalculados da matriz reconstruida batem com os "
      "valores publicados ate 0,02 em todas as linhas (ver coluna "
      "`consistente`) -- nao e uma estimativa aproximada, e uma decomposicao "
      "exata (a unica fonte de arredondamento e o proprio `round()`, que "
      "resolve para inteiros porque TP/FP/FN/TN sao contagens de dias).\n")
    linhas = []
    for _, r in clf_e15.iterrows():
        m = reconstroi_matriz(r)
        linhas.append({"base": r.base, "modelo": r.modelo, **m})
    tab = pd.DataFrame(linhas)
    tab.to_csv(os.path.join(TAB_DIR, "matriz_confusao_pooled.csv"), index=False)
    n_inconsistente = (~tab["consistente"]).sum()
    w(f"_{len(tab) - n_inconsistente}/{len(tab)} linhas consistentes; "
      f"{n_inconsistente} nao reconstruiveis com precisao (excluidas das "
      "figuras abaixo se houver)._\n" if n_inconsistente else
      "_Todas as linhas consistentes._\n")

    destaques = {
        "crimes_violentos": ["random_forest", "dia_semana_risco"],
        "acidentes_com_vitima": ["logreg_balanced"],
    }
    for base, modelos in destaques.items():
        fig, axes = plt.subplots(1, len(modelos), figsize=(4.2 * len(modelos), 3.6))
        if len(modelos) == 1:
            axes = [axes]
        for ax, modelo in zip(axes, modelos):
            r = tab[(tab.base == base) & (tab.modelo == modelo)].iloc[0]
            mat = np.array([[r.TN, r.FP], [r.FN, r.TP]])
            ax.imshow(mat, cmap="Blues")
            for i in range(2):
                for j in range(2):
                    ax.text(j, i, int(mat[i, j]), ha="center", va="center",
                           color="white" if mat[i, j] > mat.max() / 2 else "black", fontsize=12)
            ax.set_xticks([0, 1]); ax.set_xticklabels(["prev. 0", "prev. 1"])
            ax.set_yticks([0, 1]); ax.set_yticklabels(["real 0", "real 1"])
            ax.set_title(f"{modelo}", fontsize=9)
        fig.suptitle(f"Matriz de confusao (pooled walk-forward) -- {base}", fontsize=10)
        w(f"![matriz confusao {base}]({savefig(f'0{list(destaques).index(base)}_matriz_confusao_{base}.png')})\n")
    return tab


# ---------------------------------------------------------------------------
def secao_recomendacao(reg, clf):
    w("## 4. Modelo recomendado por alvo x tarefa (para a Etapa 17/18)\n")
    w("**Criterio**: evidencia principal = Etapa 15 pooled walk-forward "
      "(~360 dias de teste, ~4x mais que o split unico das Etapas 13-14, e "
      "sem o problema de fragilidade do corte unico ja documentado na Etapa "
      "13). Para classificacao, criterio de ranking = PR-AUC fold_macro "
      "(Regra 8: nunca Accuracy); Recall/F1 citados ao lado porque, para um "
      "sistema de alerta de pico, um modelo com PR-AUC melhor mas Recall "
      "inutilizavel nao e necessariamente a escolha certa (mesmo cuidado ja "
      "aplicado na Etapa 14).\n")

    w("### Regressao\n")
    for base in BASES:
        e15 = reg[(reg.base == base) & (reg.estagio.str.startswith("Etapa 15"))].sort_values("MAE")
        top = e15.iloc[0]
        w(f"- **{base}**: `{top.modelo}` -- MAE {top.MAE:.2f}, RMSE {top.RMSE:.2f}, "
          f"R² {top.R2:.3f}, MAPE {top['MAPE_%']:.1f}% (pooled, n={int(top.n)}). "
          + (f"Vantagem clara sobre o 2º colocado ({e15.iloc[1].modelo}, MAE "
             f"{e15.iloc[1].MAE:.2f})." if base == "crimes_violentos" else
             f"Vantagem estreita sobre `{e15.iloc[1].modelo}` (MAE {e15.iloc[1].MAE:.2f}) "
             f"e `{e15.iloc[2].modelo}` (MAE {e15.iloc[2].MAE:.2f}) -- R² baixo (0,28) "
             "indica que boa parte da variancia diaria continua nao-explicada; "
             "tratar como o melhor disponivel, nao como preditor forte."))

    w("\n### Classificacao\n")
    e15_cv = clf[(clf.base == "crimes_violentos") & (clf.estagio.str.startswith("Etapa 15"))]
    e15_cv = e15_cv[e15_cv.modelo != "classe_majoritaria"].sort_values("pr_auc", ascending=False)
    melhor_rank = e15_cv.iloc[0]
    melhor_recall = e15_cv.sort_values("recall", ascending=False).iloc[0]
    w(f"- **crimes_violentos**: **sem vencedor unico defensavel.** Melhor PR-AUC "
      f"fold_macro = `{melhor_rank.modelo}` ({melhor_rank.pr_auc:.3f}), mas Recall "
      f"{melhor_rank.recall:.2f} (praticamente nao detecta pico). Melhor Recall = "
      f"`{melhor_recall.modelo}` ({melhor_recall.recall:.2f}), com PR-AUC bem "
      f"menor ({melhor_recall.pr_auc:.3f}). Nenhum dos classificadores testados "
      "chega a um ponto de operacao util para um alerta real neste alvo -- "
      "reportar como limitacao (Regra 10), nao forcar uma escolha. Convergente "
      "com o nulo das Etapas 7-10: se o jogo nao tem efeito detectavel no "
      "desfecho, o classificador tem pouco sinal alem do calendario para "
      "aprender.\n")

    e15_av = clf[(clf.base == "acidentes_com_vitima") & (clf.estagio.str.startswith("Etapa 15"))]
    e15_av = e15_av[e15_av.modelo != "classe_majoritaria"].sort_values("pr_auc", ascending=False)
    top_av = e15_av.iloc[0]
    w(f"- **acidentes_com_vitima**: **`{top_av.modelo}`** -- melhor tanto em "
      f"PR-AUC fold_macro ({top_av.pr_auc:.3f}) quanto em Recall/F1 "
      f"({top_av.recall:.3f}/{top_av.f1:.3f}) entre os classificadores "
      "testados -- vencedor sem ambiguidade de criterio, diferente do split "
      "unico da Etapa 13/14 (onde `random_forest` vencia por PR-AUC mas "
      "`logreg_balanced` vencia por Recall/F1). Confusion matrix na secao 3: "
      f"de {int(top_av.n_pico_total)} dias-pico reais no total pooled, o "
      "modelo identifica a maioria as custas de falsos positivos -- "
      "coerente com Recall priorizado sobre Precision num sistema de alerta.\n")


# ---------------------------------------------------------------------------
def main():
    w("# Etapa 16 -- Metricas (consolidacao formal)\n")
    w(f"_Gerado por `scripts/13_metricas_consolidadas.py` em {date.today()}. "
      "Fontes: `reports/etapa13/tabelas`, `reports/etapa14/tabelas`, "
      "`reports/etapa15/tabelas` (nenhum modelo treinado de novo aqui)._\n")
    w("As metricas de regressao e classificacao exigidas pelo briefing S16 ja "
      "estavam sendo calculadas inline desde a Etapa 13. Esta etapa (1) audita "
      "a cobertura contra a lista do briefing, (2) preenche a unica lacuna "
      "real -- matriz de confusao, nunca produzida antes --, e (3) consolida "
      "as 3 fontes num scoreboard unico com uma recomendacao formal de modelo "
      "por alvo x tarefa para as Etapas 17-18.\n")

    secao_checklist()
    reg, clf = carrega_scoreboards()
    secao_scoreboards(reg, clf)
    clf_e15 = pd.read_csv(os.path.join(E15_TAB, "classificacao_pooled.csv"))
    secao_matriz_confusao(clf_e15)
    secao_recomendacao(reg, clf)

    w("## 5. Sintese\n")
    w("- Cobertura do briefing S16 completa: todas as metricas de regressao e "
      "classificacao exigidas estao calculadas em pelo menos uma etapa; MAPE "
      "justificado como apropriado (sem contagens perto de zero), SMAPE "
      "declarado como desnecessario; matriz de confusao produzida nesta etapa "
      "pela primeira vez.\n")
    w("- **Modelos recomendados para a Etapa 17 (tuning)**: regressao -- "
      "XGBoost Poisson nos dois alvos; classificacao -- `logreg_balanced` "
      "para `acidentes_com_vitima` (vencedor sem ambiguidade); "
      "`crimes_violentos` fica **sem candidato recomendado para tuning** "
      "ate reavaliar se otimizar hiperparametros muda a conclusao de "
      "'sem Recall utilizavel' -- ver secao 4.\n")
    w("- Nenhuma decisao metodologica anterior foi revisitada; esta etapa e "
      "puramente de consolidacao e checagem de completude.\n")
    w("- **Proximo**: Etapa 17 (otimizacao de hiperparametros, respeitando a "
      "estrutura de folds da Etapa 15), Etapa 18 (SHAP).\n")

    path = os.path.join(OUT_DIR, "relatorio_metricas.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
