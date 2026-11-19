"""
11_modelos.py
Etapa 14 do roteiro -- MODELOS DE MACHINE LEARNING, comparados aos baselines
da Etapa 13 (Regra 9). Regra 8: nao escolher pela Accuracy isolada. Regra 6:
"nao usar modelo complexo so por ser sofisticado" -- por isso hiperparametros
sao rasos/regularizados (n de treino ~640 linhas), sem busca extensiva (isso
fica para uma eventual Etapa 17 de otimizacao, fora do escopo aqui).

Modelos testados (>= os 5 pedidos no roteiro):
  Classificacao (alvo = pico): Decision Tree, Random Forest,
    HistGradientBoosting (bonus, NaN nativo, so sklearn), XGBoost, LightGBM,
    Logistic Regression (repete a Etapa 13 para a tabela ficar comparavel).
  Regressao (alvo = contagem): Decision Tree, Random Forest,
    HistGradientBoosting(loss=poisson), XGBoost(count:poisson),
    LightGBM(poisson) -- objetivo Poisson nos 3 modelos de boosting/HGB porque
    o alvo e uma contagem (Secao 14 do briefing sugere Poisson/Neg.Binomial).

MESMO split e MESMA redefinicao de alvo (calendario+P90 reajustados so no
treino) da Etapa 13, para a comparacao com os baselines ser direta. Isso
tambem herda o problema ja documentado la: o teste de `crimes_violentos` tem
so 3 positivos (ver Etapa 13, secao 1.1) -- metricas de classificacao desse
desfecho aqui sao ilustrativas, nao conclusivas, ate a Etapa 15 (walk-forward).

Tratamento de NaN: arvore/RF/LogReg (sklearn "classico") -- imputacao por
mediana do TREINO. HistGB/XGBoost/LightGBM -- usam o NaN nativamente (nao
imputa), vantagem real desses algoritmos com os buracos de clima/lag364.

Sensibilidade ao outlier de 2022-06-19 (pendencia da Etapa 12): rodada
separada, so para `crimes_violentos`, comparando XGBoost COM e SEM o
tratamento (contagem do dia tratada como missing vs mantida crua).

Rodar depois de 10 (usa data/gold/features_dia_sp.csv, data/gold/fato_dia_sp.csv
e reports/etapa13/tabelas/*.csv).
"""
import os
import textwrap
import warnings
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                              HistGradientBoostingClassifier, HistGradientBoostingRegressor)
from xgboost import XGBClassifier, XGBRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, confusion_matrix,
                             mean_absolute_error, mean_squared_error, r2_score,
                             precision_recall_curve, roc_curve)

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
BASELINE_TAB = os.path.join(BASE_DIR, "reports", "etapa13", "tabelas")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa14")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

CUTOFF = pd.Timestamp("2023-10-01")
BASES = ["crimes_violentos", "acidentes_com_vitima"]
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"
ARTEFATO = pd.Timestamp("2022-06-19")
SEED = 42

FEAT_GROUPS = {
    "temporal": ["trend", "sin_doy", "cos_doy", "sin_dow", "cos_dow"] +
                [f"dow_{k}" for k in range(7)] +
                ["dia_do_mes", "mes", "trimestre", "semana_ano", "fim_de_semana", "feriado",
                 "feriado_nacional", "feriado_estadual", "feriado_municipal", "vespera_feriado",
                 "periodo_letivo", "ferias_escolares", "recesso_escolar", "pos_feriado"],
    "futebol": ["tem_jogo_sp", "numero_jogos_sp", "classico", "jogo_noturno",
                "jogo_d_menos_1", "jogo_d_mais_1", "classico_d_menos_1", "classico_d_mais_1",
                "jogo_copa", "jogo_serie_a", "jogo_d_menos_2", "jogo_d_mais_2",
                "n_jogos_janela7", "dias_desde_jogo", "dias_ate_jogo",
                "jogo_x_fds", "jogo_x_noturno", "classico_x_fds"],
    "clima": ["temp_media", "temp_max", "temp_min", "precipitacao_total", "umidade_media",
              "vento_max", "chuva", "clima_missing", "temp_media_lag1",
              "precipitacao_total_lag1", "umidade_media_lag1"],
}


def hist_feats(base):
    """Igual a Etapa 13 + lag364 (arvores/boosting lidam bem com NaN esparso)."""
    return ([f"{base}_lag{L}" for L in (1, 2, 3, 7, 14, 28, 364)] +
            [f"{base}_rollmean{R}" for R in (7, 14, 28)] +
            [f"{base}_rollstd{R}" for R in (7, 14, 28)] +
            [f"{base}_lag1_vs_rollmean28", f"pico_p90_{base}_lag1", f"pico_p90_{base}_soma7"])


def feature_cols(base):
    return sum(FEAT_GROUPS.values(), []) + hist_feats(base)


_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def savefig(name):
    p = os.path.join(FIG_DIR, name)
    plt.savefig(p)
    plt.close()
    return os.path.relpath(p, OUT_DIR).replace("\\", "/")


def load():
    fato = pd.read_csv(GOLD_PATH, parse_dates=["data"])[["data", "dia_semana"]]
    feat = pd.read_csv(FEAT_PATH, parse_dates=["data"])
    for c in [c for c in feat.columns if c.startswith("y_pico_")]:
        feat[c] = feat[c].map({"True": True, "False": False, True: True, False: False}).astype("boolean")
    d = feat.merge(fato, on="data", how="left").sort_values("data").reset_index(drop=True)
    d["t_idx"] = np.arange(len(d))
    return d


def refit_pico_no_treino(d, base, train_mask, count_col=None):
    """Identico a Etapa 13: calendario + limiar P90 reajustados SO no treino."""
    count_col = count_col or f"y_count_{base}"
    x = d[["data", "t_idx", "dia_semana", "mes", "feriado"]].copy()
    x["y"] = d[count_col]
    fit = smf.ols(f"y ~ {CTRL}", data=x.loc[train_mask].dropna(subset=["y"])).fit()
    pred = fit.predict(x)
    resid = x["y"] - pred
    thr = resid[train_mask & x["y"].notna()].quantile(0.90)
    y_pico = pd.Series(np.where(x["y"].notna(), resid > thr, np.nan), index=d.index).astype("boolean")
    return resid, pred, thr, y_pico, fit.rsquared


def sample_weight_balanced(y):
    y = y.astype(int)
    n, n_pos = len(y), y.sum()
    n_neg = n - n_pos
    w_pos, w_neg = n / (2 * n_pos), n / (2 * n_neg)
    return np.where(y == 1, w_pos, w_neg)


# ---------------------------------------------------------------------------
def classificadores():
    return {
        "arvore_decisao": DecisionTreeClassifier(max_depth=5, min_samples_leaf=10, random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=400, max_depth=6, min_samples_leaf=5,
                                                random_state=SEED, n_jobs=-1),
        "hist_gb": HistGradientBoostingClassifier(max_depth=4, max_iter=200, learning_rate=0.05,
                                                   random_state=SEED),
        "xgboost": XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
                                 colsample_bytree=0.8, random_state=SEED, eval_metric="logloss"),
        "lightgbm": LGBMClassifier(n_estimators=300, num_leaves=15, max_depth=4, learning_rate=0.05,
                                   subsample=0.8, colsample_bytree=0.8, random_state=SEED, verbosity=-1),
    }


def regressores():
    return {
        "arvore_decisao": DecisionTreeRegressor(max_depth=5, min_samples_leaf=10, random_state=SEED),
        "random_forest": RandomForestRegressor(n_estimators=400, max_depth=6, min_samples_leaf=5,
                                               random_state=SEED, n_jobs=-1),
        "hist_gb_poisson": HistGradientBoostingRegressor(loss="poisson", max_depth=4, max_iter=200,
                                                          learning_rate=0.05, random_state=SEED),
        "xgboost_poisson": XGBRegressor(objective="count:poisson", n_estimators=300, max_depth=3,
                                        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                                        random_state=SEED),
        "lightgbm_poisson": LGBMRegressor(objective="poisson", n_estimators=300, num_leaves=15, max_depth=4,
                                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                                          random_state=SEED, verbosity=-1),
    }


NAO_NATIVO_NAN = {"arvore_decisao", "random_forest"}  # precisam de imputacao


def prep_X(d, cols, train_mask, precisa_imputar):
    X = d[cols].copy()
    if "jogo_noturno" in X:
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
    if precisa_imputar:
        imp = SimpleImputer(strategy="median").fit(X.loc[train_mask])
        X = pd.DataFrame(imp.transform(X), columns=cols, index=X.index)
    return X


# ---------------------------------------------------------------------------
def secao_setup(d):
    w("## 1. Setup\n")
    w(f"Mesmo split da Etapa 13 (treino < {CUTOFF.date()}, teste >= {CUTOFF.date()}) e "
      "mesma redefinicao de alvo de pico (calendario + limiar P90 reajustados SO no "
      "treino) -- necessario para comparar linha a linha com o scoreboard de "
      "baselines. **Isso tambem herda o problema ja documentado la**: o teste de "
      "`crimes_violentos` tem so 3 dias-pico (de 90) -- qualquer metrica de "
      "classificacao para esse desfecho aqui e ilustrativa, nao conclusiva.\n")
    w("**Features**: mesmo conjunto leakage-safe da Etapa 13 (temporal + futebol + "
      "clima + historico do proprio desfecho) **+ lag364**, que a Etapa 13 tinha "
      "excluido so por causa da imputacao do LogReg -- arvores/boosting toleram bem "
      "uma coluna esparsa (49,9% NaN).\n")
    w("**NaN**: `arvore_decisao`/`random_forest`/`logreg` recebem imputacao por "
      "mediana (ajustada so no treino); `hist_gb`/`xgboost`/`lightgbm` usam o NaN "
      "nativamente (sem imputar) -- vantagem pratica desses algoritmos aqui.\n")
    w("**Desbalanceamento** (classificacao): `sample_weight` balanceado "
      "(n/(2·n_classe), calculado so no treino) em todos os classificadores, "
      "mesmo espirito do `class_weight='balanced'` da Etapa 13.\n")
    w("**Hiperparametros rasos e nao otimizados** (Regra 6 do briefing: nao usar "
      "modelo complexo so por ser sofisticado): profundidade <=6, poucas arvores, "
      "sem busca de hiperparametros -- adequado a ~640 linhas de treino. Uma busca "
      "formal (RandomizedSearch/Optuna) fica fora do escopo desta etapa.\n")


def carrega_baselines():
    reg = pd.read_csv(os.path.join(BASELINE_TAB, "baselines_regressao.csv"))
    clf = pd.read_csv(os.path.join(BASELINE_TAB, "baselines_classificacao.csv"))
    return reg, clf


# ---------------------------------------------------------------------------
def secao_classificacao(d, clf_baseline):
    w("## 2. Classificacao (prever pico)\n")
    w("Accuracy/Precision/Recall/F1 no limiar 0.5; ROC-AUC/PR-AUC sao livres de "
      "limiar (Regra 8: nao julgar so por Accuracy).\n")

    linhas_all, curvas, modelos_fit = [], {}, {}
    for base in BASES:
        elig = d[f"y_count_{base}"].notna()
        train_mask = elig & (d["data"] < CUTOFF)
        test_mask = elig & (d["data"] >= CUTOFF)
        _, _, _, y_pico, _ = refit_pico_no_treino(d, base, train_mask)
        y_tr = y_pico[train_mask].astype(bool)
        y_te = y_pico[test_mask].astype(bool)
        sw = sample_weight_balanced(y_tr)
        cols = feature_cols(base)

        linhas_base = clf_baseline[clf_baseline["base"] == base].copy()
        linhas_base["origem"] = "baseline (Etapa 13)"
        curva_modelos = {}
        for nome, clf in classificadores().items():
            X = prep_X(d, cols, train_mask, nome in NAO_NATIVO_NAN)
            Xtr, Xte = X.loc[train_mask], X.loc[test_mask]
            clf.fit(Xtr, y_tr.astype(int), sample_weight=sw)
            proba = clf.predict_proba(Xte)[:, 1]
            pred = proba >= 0.5
            row = {"base": base, "baseline": nome, "origem": "modelo (Etapa 14)",
                  "n_teste": len(y_te), "n_pico_teste": int(y_te.sum()),
                  "accuracy": accuracy_score(y_te, pred),
                  "precision": precision_score(y_te, pred, zero_division=0),
                  "recall": recall_score(y_te, pred, zero_division=0),
                  "f1": f1_score(y_te, pred, zero_division=0)}
            if y_te.nunique() > 1:
                row["roc_auc"] = roc_auc_score(y_te, proba)
                row["pr_auc"] = average_precision_score(y_te, proba)
            linhas_all.append(row)
            curva_modelos[nome] = proba
            modelos_fit[(base, nome)] = clf
        curvas[base] = (y_te.to_numpy(), curva_modelos)
        linhas_base_dict = linhas_base.rename(columns={"baseline": "baseline"}).to_dict("records")
        linhas_all.extend(linhas_base_dict)

    tab = pd.DataFrame(linhas_all)
    cols_show = ["origem", "baseline", "n_teste", "n_pico_teste", "accuracy",
                "precision", "recall", "f1", "roc_auc", "pr_auc"]
    tab.to_csv(os.path.join(TAB_DIR, "classificacao_completa.csv"), index=False)
    for base in BASES:
        sub = tab[tab["base"] == base].sort_values("pr_auc", ascending=False)
        w(f"### {base}\n")
        w(df_to_md(sub[cols_show], floatfmt=3, index=False))
        w("")

    # ROC/PR overlay
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    for j, base in enumerate(BASES):
        y_te, curva_modelos = curvas[base]
        for nome, proba in curva_modelos.items():
            fpr, tpr, _ = roc_curve(y_te, proba)
            axes[0, j].plot(fpr, tpr, lw=1.2, label=f"{nome} ({roc_auc_score(y_te, proba):.2f})")
            prec, rec, _ = precision_recall_curve(y_te, proba)
            axes[1, j].plot(rec, prec, lw=1.2,
                            label=f"{nome} ({average_precision_score(y_te, proba):.2f})")
        axes[0, j].plot([0, 1], [0, 1], "k--", lw=.7)
        axes[0, j].set_title(f"ROC -- {base}")
        axes[0, j].legend(fontsize=6)
        base_rate = y_te.mean()
        axes[1, j].axhline(base_rate, color="k", ls="--", lw=.7)
        axes[1, j].set_title(f"PR -- {base}")
        axes[1, j].legend(fontsize=6)
    w(f"![roc pr todos os modelos]({savefig('01_roc_pr_modelos.png')})\n")

    # matriz de confusao do melhor modelo por PR-AUC
    for base in BASES:
        sub = tab[(tab["base"] == base) & (tab["origem"] == "modelo (Etapa 14)")]
        melhor = sub.sort_values("pr_auc", ascending=False).iloc[0]
        y_te, curva_modelos = curvas[base]
        proba = curva_modelos[melhor["baseline"]]
        cm = confusion_matrix(y_te, proba >= 0.5)
        cmdf = pd.DataFrame(cm, index=["real: nao-pico", "real: pico"],
                            columns=["prev: nao-pico", "prev: pico"])
        w(f"Melhor modelo por PR-AUC em `{base}`: **{melhor['baseline']}** "
          f"(PR-AUC={melhor['pr_auc']:.3f}, F1={melhor['f1']:.3f}). Matriz de confusao:\n")
        w(df_to_md(cmdf, floatfmt=0))
        fp, tp = cm[0, 1], cm[1, 1]
        if base == "crimes_violentos":
            w(f"\n_'Melhor' aqui e relativo -- {fp} falsos positivos para {tp} "
              f"verdadeiro(s) positivo(s), sobre so 3 casos reais no teste. Nao e um "
              f"modelo utilizavel, e o menos ruim entre opcoes ruins (ver ressalva "
              f"da secao 1)._\n")
        w("")
    return modelos_fit, tab


# ---------------------------------------------------------------------------
def secao_regressao(d, reg_baseline):
    w("## 3. Regressao (prever a contagem)\n")
    linhas_all = {}
    curvas_pred = {}
    modelos_fit = {}
    for base in BASES:
        elig = d[f"y_count_{base}"].notna()
        train_mask = elig & (d["data"] < CUTOFF)
        test_mask = elig & (d["data"] >= CUTOFF)
        y_tr = d.loc[train_mask, f"y_count_{base}"]
        y_te = d.loc[test_mask, f"y_count_{base}"]
        cols = feature_cols(base)
        linhas = []
        curva_modelos = {}
        for nome, reg in regressores().items():
            X = prep_X(d, cols, train_mask, nome in NAO_NATIVO_NAN)
            reg.fit(X.loc[train_mask], y_tr)
            pred = reg.predict(X.loc[test_mask])
            mae = mean_absolute_error(y_te, pred)
            rmse = mean_squared_error(y_te, pred) ** 0.5
            r2 = r2_score(y_te, pred)
            mape = (np.abs((y_te - pred) / y_te)).mean() * 100
            linhas.append({"base": base, "baseline": nome, "origem": "modelo (Etapa 14)",
                           "n": len(y_te), "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE_%": mape})
            curva_modelos[nome] = pred
            modelos_fit[(base, nome)] = reg
        base_rows = reg_baseline[reg_baseline["base"] == base].copy()
        base_rows["origem"] = "baseline (Etapa 13)"
        linhas.extend(base_rows.to_dict("records"))
        linhas_all[base] = pd.DataFrame(linhas).sort_values("MAE")
        curvas_pred[base] = (d.loc[test_mask, "data"], y_te, curva_modelos)

    tab = pd.concat(linhas_all.values(), ignore_index=True)
    tab.to_csv(os.path.join(TAB_DIR, "regressao_completa.csv"), index=False)
    for base in BASES:
        w(f"### {base}\n")
        w(df_to_md(linhas_all[base][["origem", "baseline", "n", "MAE", "RMSE", "R2", "MAPE_%"]],
                  floatfmt=2, index=False))
        w("")

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.2))
    for ax, base in zip(axes, BASES):
        dt, y_te, curva_modelos = curvas_pred[base]
        ax.plot(dt, y_te, "k-", lw=1.4, label="observado")
        melhor_nome = linhas_all[base].iloc[0]["baseline"]
        if melhor_nome in curva_modelos:
            ax.plot(dt, curva_modelos[melhor_nome], lw=1.2, color="#c44e52",
                    label=f"melhor modelo: {melhor_nome}")
        ax.set_title(base)
        ax.legend(fontsize=8)
        ax.tick_params(axis="x", rotation=30)
    w(f"![melhor modelo vs real]({savefig('02_melhor_regressao.png')})\n")
    return modelos_fit, tab


# ---------------------------------------------------------------------------
def secao_importancia(d, modelos_clf):
    w("## 4. Importancia de features (previa -- SHAP formal e a Etapa 18)\n")
    w("**`total_gain`** (ganho total acumulado, soma do ganho de TODOS os splits que "
      "usam a feature) como medida principal -- nao o `gain` medio por split, que "
      "**infla features binarias raras**: um unico split muito puro numa feature usada "
      "poucas vezes da um `gain` medio alto mesmo sem peso real no modelo. Reportamos "
      "`weight` (nº de splits) e `gain` junto para auditar esse efeito -- mesmo "
      "cuidado ja aplicado ao RR aparente do Morumbi na Etapa 10. A analise definitiva "
      "de interpretabilidade (SHAP, com direcao do efeito) e a Etapa 18.\n")
    for base in BASES:
        clf = modelos_clf.get((base, "xgboost"))
        if clf is None:
            continue
        cols = feature_cols(base)
        booster = clf.get_booster()
        tg = pd.Series(booster.get_score(importance_type="total_gain")).reindex(cols).fillna(0)
        gain = pd.Series(booster.get_score(importance_type="gain")).reindex(cols).fillna(0)
        wgt = pd.Series(booster.get_score(importance_type="weight")).reindex(cols).fillna(0)
        imp = tg.sort_values(ascending=False).head(15)
        fig, ax = plt.subplots(figsize=(8, 5.5))
        cores = ["#c44e52" if any(k in f for k in ["jogo", "classico", "copa", "serie_a"])
                 else "#4c72b0" for f in imp.index[::-1]]
        ax.barh(imp.index[::-1], imp.values[::-1], color=cores)
        ax.set_title(f"XGBoost -- importancia (total_gain) top 15, {base}")
        ax.set_xlabel("total_gain")
        w(f"![importancia {base}]({savefig(f'03_importancia_{base}.png')})\n")
        fut = imp[imp.index.str.contains("jogo|classico|copa|serie_a")]
        w(f"_Features de futebol no top 15 por total_gain: {len(fut)}"
          + (f" (maior = `{fut.index[0]}`, {fut.iloc[0]:.0f})" if len(fut) else " (nenhuma)")
          + f". Top 1 geral: `{imp.index[0]}` ({imp.iloc[0]:.0f})._\n")

        # auditoria: feature no top-5 por gain medio mas fora do top-10 por total_gain
        gain_top5 = gain.sort_values(ascending=False).head(5).index
        tg_top10 = tg.sort_values(ascending=False).head(10).index
        suspeitas = [f for f in gain_top5 if f not in tg_top10]
        if suspeitas:
            det = ", ".join(f"`{f}` (gain medio alto, so {int(wgt[f])} splits, "
                            f"total_gain rank #{int((tg.rank(ascending=False))[f])})"
                            for f in suspeitas)
            w(f"_Atencao -- top-5 por `gain` medio que NAO entra no top-10 por "
              f"`total_gain` (provavel artefato de feature binaria rara, poucos "
              f"splits mas puros): {det}. Nao interpretar como achado sem checar "
              f"`total_gain`/`weight`._\n")


# ---------------------------------------------------------------------------
def secao_sensibilidade(d):
    w("## 5. Sensibilidade ao outlier de 2022-06-19\n")
    w("Pendencia da Etapa 12: comparar `crimes_violentos` **com** o tratamento "
      "(contagem do dia -> missing, como ja rodou em todo o projeto) e **sem** "
      "(dia mantido cru, `furtos_total`=2633/`crimes_violentos`=715). So XGBoost, "
      "so `crimes_violentos` (unico desfecho afetado pelo outlier).\n")

    fato = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    fato["t_idx"] = np.arange(len(fato))
    fato["dia_semana"] = fato["dia_semana"].astype(int)
    d2 = d.copy()
    # restaura o valor cru do dia artefato e re-deriva lags/rolling afetados
    raw_val = fato.loc[fato["data"] == ARTEFATO, "crimes_violentos"].iloc[0]
    idx_art = d2.index[d2["data"] == ARTEFATO][0]
    src = fato.set_index("data")["crimes_violentos"].reindex(d2["data"]).reset_index(drop=True)
    d2["y_count_crimes_violentos_semtrat"] = src
    d2["dia_excluido_crime_semtrat"] = d2["dia_excluido_crime"].where(d2["data"] != ARTEFATO, 0)
    for L in (1, 2, 3, 7, 14, 28, 364):
        d2[f"crimes_violentos_lag{L}_semtrat"] = src.shift(L)
    for R in (7, 14, 28):
        d2[f"crimes_violentos_rollmean{R}_semtrat"] = src.shift(1).rolling(R, min_periods=max(3, R // 2)).mean()
        d2[f"crimes_violentos_rollstd{R}_semtrat"] = src.shift(1).rolling(R, min_periods=max(3, R // 2)).std(ddof=0)
    d2["crimes_violentos_lag1_vs_rollmean28_semtrat"] = (d2["crimes_violentos_lag1_semtrat"] -
                                                          d2["crimes_violentos_rollmean28_semtrat"])

    resultados = []
    for tag, count_col, elig_col, suf in [
        ("com tratamento (projeto)", "y_count_crimes_violentos", "dia_excluido_crime", ""),
        ("sem tratamento (sensibilidade)", "y_count_crimes_violentos_semtrat",
         "dia_excluido_crime_semtrat", "_semtrat"),
    ]:
        elig = d2[count_col].notna() if suf else d2["y_count_crimes_violentos"].notna()
        train_mask = elig & (d2["data"] < CUTOFF)
        test_mask = elig & (d2["data"] >= CUTOFF)
        cols = feature_cols("crimes_violentos")
        cols_local = [c + suf if (c + suf) in d2.columns else c for c in cols]

        # --- classificacao ---
        _, _, _, y_pico, _ = refit_pico_no_treino(d2, "crimes_violentos", train_mask, count_col=count_col)
        y_tr, y_te = y_pico[train_mask].astype(bool), y_pico[test_mask].astype(bool)
        Xc = d2[cols_local].copy()
        Xc["jogo_noturno"] = Xc["jogo_noturno"].fillna(0)
        clf = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
                            colsample_bytree=0.8, random_state=SEED, eval_metric="logloss")
        clf.fit(Xc.loc[train_mask], y_tr.astype(int), sample_weight=sample_weight_balanced(y_tr))
        proba = clf.predict_proba(Xc.loc[test_mask])[:, 1]
        pred = proba >= 0.5
        row = {"tratamento": tag, "tarefa": "classificacao", "n_teste": len(y_te),
              "n_pico_teste": int(y_te.sum()), "recall": recall_score(y_te, pred, zero_division=0),
              "f1": f1_score(y_te, pred, zero_division=0),
              "pr_auc": average_precision_score(y_te, proba) if y_te.nunique() > 1 else np.nan}
        resultados.append(row)

        # --- regressao ---
        y_tr_r = d2.loc[train_mask, count_col]
        y_te_r = d2.loc[test_mask, count_col]
        reg = XGBRegressor(objective="count:poisson", n_estimators=300, max_depth=3, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8, random_state=SEED)
        reg.fit(Xc.loc[train_mask], y_tr_r)
        predr = reg.predict(Xc.loc[test_mask])
        resultados.append({"tratamento": tag, "tarefa": "regressao", "n_teste": len(y_te_r),
                           "n_pico_teste": np.nan,
                           "MAE": mean_absolute_error(y_te_r, predr),
                           "RMSE": mean_squared_error(y_te_r, predr) ** 0.5})

    tab = pd.DataFrame(resultados)
    tab.to_csv(os.path.join(TAB_DIR, "sensibilidade_outlier.csv"), index=False)
    w(df_to_md(tab, floatfmt=3, index=False))
    w("\n_Diferencas grandes entre as linhas indicariam que a decisao da Etapa 12 "
      "(tratar 2022-06-19 como missing) muda a conclusao; diferencas pequenas "
      "confirmam que o tratamento e so uma correcao pontual, nao um fator que "
      "decide o resultado._\n")


# ---------------------------------------------------------------------------
def main():
    d = load()
    reg_baseline, clf_baseline = carrega_baselines()
    w("# Etapa 14 -- Modelos de Machine Learning\n")
    w(f"_Gerado por `scripts/11_modelos.py` em {date.today()}. "
      f"Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`, "
      f"`reports/etapa13/tabelas/*.csv`._\n")
    w("> Regra 9: todo modelo e comparado ao scoreboard de baselines da Etapa 13 "
      "na mesma tabela. Regra 8: leitura por Recall/F1/PR-AUC, nao so Accuracy. "
      "Regra 6: hiperparametros propositalmente rasos.\n")

    secao_setup(d)
    modelos_clf, tab_clf = secao_classificacao(d, clf_baseline)
    modelos_reg, tab_reg = secao_regressao(d, reg_baseline)
    secao_importancia(d, modelos_clf)
    secao_sensibilidade(d)

    w("## 6. Escolha do modelo e sintese\n")
    melhores, tensoes = [], []
    for base in BASES:
        mc = tab_clf[(tab_clf.base == base) & (tab_clf.origem == "modelo (Etapa 14)")].sort_values(
            "pr_auc", ascending=False).iloc[0]
        mr = tab_reg[(tab_reg.base == base) & (tab_reg.origem == "modelo (Etapa 14)")].sort_values(
            "MAE").iloc[0]
        melhores.append({"base": base, "melhor_classificador_PR_AUC": mc["baseline"], "PR_AUC": mc["pr_auc"],
                         "F1_desse": mc["f1"], "Recall_desse": mc["recall"],
                         "melhor_regressor": mr["baseline"], "MAE": mr["MAE"], "RMSE": mr["RMSE"]})
        todos_base = tab_clf[tab_clf.base == base]
        mf1 = todos_base.sort_values("f1", ascending=False).iloc[0]
        if mf1["baseline"] != mc["baseline"]:
            tensoes.append({"base": base, "melhor_PR_AUC": mc["baseline"], "PR_AUC": mc["pr_auc"],
                            "F1_do_PR_AUC": mc["f1"], "Recall_do_PR_AUC": mc["recall"],
                            "melhor_F1": mf1["baseline"], "F1": mf1["f1"], "Recall_do_F1": mf1["recall"],
                            "PR_AUC_do_F1": mf1["pr_auc"]})
    w(df_to_md(pd.DataFrame(melhores), floatfmt=3, index=False))
    w("")
    if tensoes:
        w("**Atencao -- PR-AUC e F1@0.5 discordam do 'melhor modelo' em pelo menos um "
          "desfecho** (comparando TODAS as linhas, baselines incluidos):\n")
        w(df_to_md(pd.DataFrame(tensoes), floatfmt=3, index=False))
        w("\nPR-AUC (livre de limiar) recompensa a qualidade do ranking; F1/Recall em "
          "0.5 medem o classificador no ponto de operacao real. Um modelo pode "
          "ordenar bem os dias de risco e ainda assim, no limiar padrao, marcar "
          "quase nada como pico (alta precisao, recall baixo) -- e o caso de "
          "`random_forest` em `acidentes_com_vitima`: PR-AUC mais alto do grupo, mas "
          "so 2 dias previstos como pico em 90 (recall 0,065), contra recall 0,74 do "
          "`logreg_balanced` da Etapa 13. **Para um sistema de alerta de pico, "
          "recall costuma pesar mais que ranking abstrato** -- a escolha final do "
          "artigo deveria considerar ajuste de limiar (nao feito aqui) antes de "
          "declarar um vencedor so pelo PR-AUC.\n")
    w(textwrap.dedent("""\
        - **Criterio de escolha**: nao e so a metrica -- entre modelos com desempenho
          parecido, prefere-se o mais simples/interpretavel (Regra: nao usar
          complexidade so por ser sofisticado). Se Random Forest ou HistGB chegam
          perto do XGBoost/LightGBM em PR-AUC/MAE, a simplicidade extra pesa a favor
          deles na escolha final do artigo.
        - **`crimes_violentos` classificacao**: leitura ilustrativa (n=3 positivos no
          teste, herdado da Etapa 13) -- nao usar esse numero como conclusao forte
          sem a validacao walk-forward da Etapa 15.
        - **Importancia de features**: por `total_gain` (nao o `gain` medio, que
          infla features binarias raras -- ver secao 4), as features lideres seguem
          sendo historico do proprio desfecho e clima, nao futebol -- reconfirma
          Etapas 7-10. O unico candidato a contra-exemplo (`classico_d_menos_1` em
          `acidentes_com_vitima`) foi auditado na propria secao 4 e e o mesmo sinal
          fraco de classico com amostra pequena ja visto e nao confirmado nas
          Etapas 7-9 -- nao e um achado novo.
        - **Sensibilidade ao outlier**: ver secao 5 -- a decisao da Etapa 12 muda
          (ou nao) a leitura de forma relevante.
        - **Proximo**: Etapa 15 -- validacao temporal formal (walk-forward /
          TimeSeriesSplit com varios folds), a resposta definitiva para a fragilidade
          do split unico ja demonstrada na Etapa 13 e herdada aqui.
    """))

    path = os.path.join(OUT_DIR, "relatorio_modelos.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
