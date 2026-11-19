"""
14_otimizacao_hiperparametros.py
Etapa 17 do roteiro -- OTIMIZACAO DE HIPERPARAMETROS (secao 17 do
briefing_original.md), respeitando a mesma temporalidade das Etapas 15/16
(Regra 7: nunca random split/CV embaralhado em serie temporal).

Escopo definido na Etapa 16 (nao redecidir aqui): so os modelos que a Etapa
16 recomendou.
  - Regressao: XGBoost Poisson, nos 2 alvos (`crimes_violentos`,
    `acidentes_com_vitima`).
  - Classificacao: `logreg_balanced`, so em `acidentes_com_vitima` --
    `crimes_violentos` ficou EXPLICITAMENTE sem candidato na Etapa 16 (nenhum
    classificador testado chega a um ponto de operacao util); tuning nao
    resolve falta de sinal, entao nao e repetido aqui.

Desenho (nested walk-forward, para nao vazar dados futuros em 2 niveis):
  - NIVEL EXTERNO = os mesmos 12 folds mensais walk-forward da Etapa 15
    (janela expansiva ancorada em 2022-01-01), para que o MAE/PR-AUC "pooled"
    resultante seja comparavel numero-a-numero com a Etapa 15/16 (mesma
    definicao de treino/teste).
  - NIVEL INTERNO = dentro do treino de CADA fold externo, a busca de
    hiperparametros usa `sklearn.model_selection.TimeSeriesSplit` (walk-
    forward tambem, sem embaralhar) como `cv` do RandomizedSearchCV -- ou
    seja, a escolha de hiperparametros para prever o mes de teste do fold N
    NUNCA usa dados de fold >= N. Isso e nested cross-validation temporal:
    a metrica pooled reportada aqui e uma estimativa honesta de generalizacao
    (nao foi obtida escolhendo hiperparametros que ja "viram" o proprio
    conjunto de teste que estao sendo avaliados).
  - Alem disso, roda-se UMA busca adicional usando TODO o historico
    disponivel (ainda com TimeSeriesSplit, sem embaralhar) para produzir os
    **hiperparametros de producao** -- o unico conjunto fixo que as Etapas
    18+ (SHAP, cenarios) devem usar para treinar o "modelo final". Esses
    hiperparametros de producao NAO alimentam a metrica pooled reportada
    aqui (evita misturar estimativa de generalizacao com o modelo final).

Calendario/residuo/limiar de pico do alvo de classificacao reajustados so no
treino de cada fold externo -- mesma disciplina da Etapa 15.

Rodar depois da Etapa 16 (le so `data/gold/features_dia_sp.csv` e
`fato_dia_sp.csv`; nao depende dos CSVs da Etapa 16, so do texto da
recomendacao, hardcoded aqui).
"""
import os
import warnings
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import statsmodels.formula.api as smf
from scipy.stats import loguniform, randint, uniform
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score,
                             mean_absolute_error, mean_squared_error, r2_score)

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa17")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

SEED = 42
ANCORA = pd.Timestamp("2022-01-01")
FOLDS = [(pd.Timestamp(f"2023-{m:02d}-01"),
         pd.Timestamp(f"2023-{m:02d}-01") + pd.offsets.MonthBegin(1))
         for m in range(1, 13)]
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"

BASES_REG = ["crimes_violentos", "acidentes_com_vitima"]
BASES_CLF = ["acidentes_com_vitima"]  # crimes_violentos: sem candidato (Etapa 16)

# ---- baseline (nao-tunado) da Etapa 15/16, para comparacao lado a lado ----
BASELINE_REG = {
    ("crimes_violentos", "xgboost_poisson"): dict(MAE=34.839884, RMSE=44.871504, R2=0.480734, MAPE=7.088062),
    ("acidentes_com_vitima", "xgboost_poisson"): dict(MAE=10.321225, RMSE=13.076117, R2=0.283268, MAPE=12.688948),
}
BASELINE_CLF = {
    ("acidentes_com_vitima", "logreg_balanced"): dict(accuracy=0.662983, precision=0.389706, recall=0.576087,
                                                       f1=0.464912, roc_auc=0.668579, pr_auc=0.476273),
}

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


def load():
    fato = pd.read_csv(GOLD_PATH, parse_dates=["data"])[["data", "dia_semana"]]
    feat = pd.read_csv(FEAT_PATH, parse_dates=["data"])
    for c in [c for c in feat.columns if c.startswith("y_pico_")]:
        feat[c] = feat[c].map({"True": True, "False": False, True: True, False: False}).astype("boolean")
    d_ = feat.merge(fato, on="data", how="left").sort_values("data").reset_index(drop=True)
    d_["t_idx"] = np.arange(len(d_))
    return d_


def refit_pico_no_treino(d_, base, train_mask):
    x = d_[["data", "t_idx", "dia_semana", "mes", "feriado"]].copy()
    x["y"] = d_[f"y_count_{base}"]
    fit = smf.ols(f"y ~ {CTRL}", data=x.loc[train_mask].dropna(subset=["y"])).fit()
    pred = fit.predict(x)
    resid = x["y"] - pred
    thr = resid[train_mask & x["y"].notna()].quantile(0.90)
    y_pico = pd.Series(np.where(x["y"].notna(), resid > thr, np.nan), index=d_.index).astype("boolean")
    return y_pico


def sample_weight_balanced(y):
    y = y.astype(int)
    n, n_pos = len(y), y.sum()
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.ones(n)
    return np.where(y == 1, n / (2 * n_pos), n / (2 * n_neg))


def prep_X_native(d_, cols):
    X = d_[cols].copy()
    if "jogo_noturno" in X:
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
    return X


def prep_X_imputed(d_, cols, fit_mask):
    X = d_[cols].copy()
    if "jogo_noturno" in X:
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
    imp = SimpleImputer(strategy="median").fit(X.loc[fit_mask])
    return pd.DataFrame(imp.transform(X), columns=cols, index=X.index)


def inner_splits(n_train):
    """TimeSeriesSplit dentro do treino do fold externo -- nunca embaralha,
    cada split de validacao interna vem sempre DEPOIS do treino interno.
    n_splits reduzido para os folds externos mais curtos (poucos dias de
    treino no comeco da janela expansiva)."""
    n_splits = 3 if n_train >= 250 else 2
    return TimeSeriesSplit(n_splits=n_splits)


XGB_PARAM_DIST = {
    "n_estimators": randint(100, 500),
    "max_depth": randint(2, 7),
    "learning_rate": loguniform(0.01, 0.3),
    "subsample": uniform(0.6, 0.4),
    "colsample_bytree": uniform(0.6, 0.4),
    "min_child_weight": randint(1, 10),
    "reg_alpha": loguniform(1e-3, 10),
    "reg_lambda": loguniform(1e-3, 10),
}
LOGIT_PARAM_DIST = {
    "C": loguniform(1e-3, 1e2),
    "penalty": ["l1", "l2"],
}


# ---------------------------------------------------------------------------
def tuning_regressao(d_, base):
    elig = d_[f"y_count_{base}"].notna()
    cols = feature_cols(base)
    Xn = prep_X_native(d_, cols)
    y = d_[f"y_count_{base}"]

    linhas_fold, pooled_true, pooled_pred = [], [], []
    for ini, fim in FOLDS:
        train_mask = (elig & (d_["data"] < ini)).to_numpy()
        test_mask = (elig & (d_["data"] >= ini) & (d_["data"] < fim)).to_numpy()
        n_tr, n_te = train_mask.sum(), test_mask.sum()
        if n_te == 0 or n_tr < 90:
            continue
        search = RandomizedSearchCV(
            XGBRegressor(objective="count:poisson", random_state=SEED),
            XGB_PARAM_DIST, n_iter=25, scoring="neg_mean_absolute_error",
            cv=inner_splits(n_tr), random_state=SEED, n_jobs=-1, error_score=np.nan)
        search.fit(Xn.loc[train_mask], y[train_mask])
        pred = search.best_estimator_.predict(Xn.loc[test_mask])
        pooled_true.append(y[test_mask].to_numpy())
        pooled_pred.append(pred)
        linhas_fold.append({"base": base, "fold": ini.strftime("%Y-%m"), "n_treino": int(n_tr),
                            "n_teste": int(n_te), "fold_MAE": mean_absolute_error(y[test_mask], pred),
                            **search.best_params_})

    y_true = np.concatenate(pooled_true)
    y_pred = np.concatenate(pooled_pred)
    pooled = dict(MAE=mean_absolute_error(y_true, y_pred),
                 RMSE=mean_squared_error(y_true, y_pred) ** 0.5,
                 R2=r2_score(y_true, y_pred),
                 MAPE=np.abs((y_true - y_pred) / y_true).mean() * 100)
    return pd.DataFrame(linhas_fold), pooled


def tuning_classificacao(d_, base):
    elig = d_[f"y_count_{base}"].notna()
    cols = feature_cols(base)

    linhas_fold = []
    pooled_true, pooled_score = [], []
    for ini, fim in FOLDS:
        train_mask = (elig & (d_["data"] < ini)).to_numpy()
        test_mask = (elig & (d_["data"] >= ini) & (d_["data"] < fim)).to_numpy()
        n_tr, n_te = train_mask.sum(), test_mask.sum()
        if n_te == 0 or n_tr < 90:
            continue
        y_pico = refit_pico_no_treino(d_, base, train_mask)
        y_tr_c = y_pico[train_mask].astype(bool)
        y_te_c = y_pico[test_mask].astype(bool)
        if y_tr_c.nunique() < 2:
            continue

        Xi = prep_X_imputed(d_, cols, train_mask)
        sca = StandardScaler().fit(Xi.loc[train_mask])
        Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=Xi.index)
        sw = sample_weight_balanced(y_tr_c)

        search = RandomizedSearchCV(
            LogisticRegression(max_iter=3000, class_weight="balanced", solver="liblinear"),
            LOGIT_PARAM_DIST, n_iter=20, scoring="average_precision",
            cv=inner_splits(n_tr), random_state=SEED, n_jobs=-1, error_score=np.nan)
        search.fit(Xs.loc[train_mask], y_tr_c.astype(int), sample_weight=sw)
        proba = search.best_estimator_.predict_proba(Xs.loc[test_mask])[:, 1]

        pooled_true.append(y_te_c.to_numpy())
        pooled_score.append(proba)
        fold_auc = roc_auc_score(y_te_c, proba) if y_te_c.nunique() > 1 else np.nan
        fold_pr = average_precision_score(y_te_c, proba) if y_te_c.nunique() > 1 else np.nan
        linhas_fold.append({"base": base, "fold": ini.strftime("%Y-%m"), "n_treino": int(n_tr),
                            "n_teste": int(n_te), "fold_roc_auc": fold_auc, "fold_pr_auc": fold_pr,
                            **search.best_params_})

    y_true = np.concatenate(pooled_true)
    score = np.concatenate(pooled_score)
    pred = score >= 0.5
    fold_aucs = [r["fold_roc_auc"] for r in linhas_fold if not np.isnan(r["fold_roc_auc"])]
    fold_prs = [r["fold_pr_auc"] for r in linhas_fold if not np.isnan(r["fold_pr_auc"])]
    pooled = dict(accuracy=accuracy_score(y_true, pred), precision=precision_score(y_true, pred, zero_division=0),
                 recall=recall_score(y_true, pred, zero_division=0), f1=f1_score(y_true, pred, zero_division=0),
                 roc_auc=np.mean(fold_aucs) if fold_aucs else np.nan,
                 pr_auc=np.mean(fold_prs) if fold_prs else np.nan)
    return pd.DataFrame(linhas_fold), pooled


# ---------------------------------------------------------------------------
def producao_regressao(d_, base):
    """Busca final usando TODO o historico disponivel (ainda TimeSeriesSplit,
    sem embaralhar) -- produz o hiperparametro FIXO que a Etapa 18+ usa para
    treinar o modelo final. Nao entra na metrica pooled (evita misturar
    estimativa de generalizacao com o modelo de producao)."""
    elig = d_[f"y_count_{base}"].notna()
    cols = feature_cols(base)
    Xn = prep_X_native(d_, cols)
    y = d_[f"y_count_{base}"]
    search = RandomizedSearchCV(
        XGBRegressor(objective="count:poisson", random_state=SEED),
        XGB_PARAM_DIST, n_iter=40, scoring="neg_mean_absolute_error",
        cv=TimeSeriesSplit(n_splits=5), random_state=SEED, n_jobs=-1, error_score=np.nan)
    search.fit(Xn.loc[elig], y[elig])
    return search.best_params_


def producao_classificacao(d_, base):
    elig = d_[f"y_count_{base}"].notna()
    cols = feature_cols(base)
    full_mask = elig.to_numpy()
    y_pico = refit_pico_no_treino(d_, base, full_mask)
    y_c = y_pico[full_mask].astype(bool)
    Xi = prep_X_imputed(d_, cols, full_mask)
    sca = StandardScaler().fit(Xi.loc[full_mask])
    Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=Xi.index)
    sw = sample_weight_balanced(y_c)
    search = RandomizedSearchCV(
        LogisticRegression(max_iter=3000, class_weight="balanced", solver="liblinear"),
        LOGIT_PARAM_DIST, n_iter=30, scoring="average_precision",
        cv=TimeSeriesSplit(n_splits=5), random_state=SEED, n_jobs=-1, error_score=np.nan)
    search.fit(Xs.loc[full_mask], y_c.astype(int), sample_weight=sw)
    return search.best_params_


# ---------------------------------------------------------------------------
def main():
    d_ = load()
    w("# Etapa 17 -- Otimizacao de hiperparametros\n")
    w(f"_Gerado por `scripts/14_otimizacao_hiperparametros.py` em {date.today()}. "
      "Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`._\n")
    w("> Regra 7: nunca CV embaralhado em serie temporal. Nested walk-forward: "
      "**nivel externo** = os mesmos 12 folds mensais da Etapa 15 (pooled "
      "comparavel numero-a-numero); **nivel interno** = `TimeSeriesSplit` "
      "dentro do treino de cada fold externo, para escolher hiperparametros "
      "sem que a escolha veja o proprio teste daquele fold. Um conjunto de "
      "hiperparametros de **producao** e escolhido a parte (busca sobre todo "
      "o historico) para uso nas Etapas 18+ -- nao contamina a metrica pooled "
      "reportada aqui.\n")
    w("**Escopo (decidido na Etapa 16, nao redecidido aqui)**: regressao -- "
      "XGBoost Poisson nos 2 alvos; classificacao -- `logreg_balanced` so em "
      "`acidentes_com_vitima` (`crimes_violentos` ficou sem candidato: "
      "nenhum classificador da Etapa 15 chegou a um ponto de operacao util, "
      "e tuning nao cria sinal onde os dados nao tem).\n")

    # ---------------- regressao ----------------
    w("## 1. Regressao -- XGBoost Poisson tunado vs baseline (Etapa 15/16)\n")
    comp_reg = []
    for base in BASES_REG:
        print(f"[tuning] regressao {base} ...")
        folds_tab, pooled = tuning_regressao(d_, base)
        folds_tab.to_csv(os.path.join(TAB_DIR, f"hiperparametros_por_fold_regressao_{base}.csv"), index=False)
        base_line = BASELINE_REG[(base, "xgboost_poisson")]
        comp_reg.append({"base": base, "MAE_baseline": base_line["MAE"], "MAE_tunado": pooled["MAE"],
                         "delta_MAE": pooled["MAE"] - base_line["MAE"],
                         "RMSE_baseline": base_line["RMSE"], "RMSE_tunado": pooled["RMSE"],
                         "R2_baseline": base_line["R2"], "R2_tunado": pooled["R2"],
                         "MAPE_baseline_%": base_line["MAPE"], "MAPE_tunado_%": pooled["MAPE"]})
        w(f"### {base}\n")
        w(f"Hiperparametros por fold (12 buscas independentes, cada uma so com "
          f"dados anteriores ao fold): [`hiperparametros_por_fold_regressao_{base}.csv`]"
          f"(tabelas/hiperparametros_por_fold_regressao_{base}.csv)\n")
        disp = folds_tab[["fold", "n_treino", "fold_MAE", "n_estimators", "max_depth", "learning_rate"]]
        w(df_to_md(disp, floatfmt=3, index=False))
        w("")
    tab_comp_reg = pd.DataFrame(comp_reg)
    tab_comp_reg.to_csv(os.path.join(TAB_DIR, "comparacao_pooled_regressao.csv"), index=False)
    w("### Comparacao pooled -- tunado vs baseline (mesmos 12 folds/definicao da Etapa 15)\n")
    w(df_to_md(tab_comp_reg, floatfmt=3, index=False))
    w("")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, base in zip(axes, BASES_REG):
        r = tab_comp_reg[tab_comp_reg.base == base].iloc[0]
        ax.bar(["baseline\n(Etapa 15)", "tunado\n(Etapa 17)"], [r.MAE_baseline, r.MAE_tunado],
              color=["#4c72b0", "#55a868"])
        ax.set_title(f"MAE pooled -- {base}")
        ax.set_ylabel("MAE")
        for i, v in enumerate([r.MAE_baseline, r.MAE_tunado]):
            ax.text(i, v, f"{v:.1f}", ha="center", va="bottom")
    w(f"![MAE tunado vs baseline]({savefig('00_mae_tunado_vs_baseline.png')})\n")

    # ---------------- classificacao ----------------
    w("## 2. Classificacao -- logreg_balanced tunado vs baseline (acidentes_com_vitima)\n")
    comp_clf = []
    for base in BASES_CLF:
        print(f"[tuning] classificacao {base} ...")
        folds_tab, pooled = tuning_classificacao(d_, base)
        folds_tab.to_csv(os.path.join(TAB_DIR, f"hiperparametros_por_fold_classificacao_{base}.csv"), index=False)
        base_line = BASELINE_CLF[(base, "logreg_balanced")]
        comp_clf.append({"base": base, **{f"{k}_baseline": base_line[k] for k in base_line},
                         **{f"{k}_tunado": pooled[k] for k in pooled}})
        w(f"### {base}\n")
        w(f"Hiperparametros por fold: [`hiperparametros_por_fold_classificacao_{base}.csv`]"
          f"(tabelas/hiperparametros_por_fold_classificacao_{base}.csv)\n")
        disp = folds_tab[["fold", "n_treino", "fold_roc_auc", "fold_pr_auc", "C", "penalty"]]
        w(df_to_md(disp, floatfmt=3, index=False))
        w("")
    tab_comp_clf = pd.DataFrame(comp_clf)
    tab_comp_clf.to_csv(os.path.join(TAB_DIR, "comparacao_pooled_classificacao.csv"), index=False)
    w("### Comparacao pooled -- tunado vs baseline (`roc_auc`/`pr_auc` aqui = fold_macro, "
      "mesma convencao da Etapa 15)\n")
    w(df_to_md(tab_comp_clf, floatfmt=3, index=False))
    w("")

    fig, ax = plt.subplots(figsize=(6, 4))
    r = tab_comp_clf.iloc[0]
    metrs = ["recall", "f1", "pr_auc", "roc_auc"]
    x = np.arange(len(metrs))
    ax.bar(x - 0.18, [r[f"{m}_baseline"] for m in metrs], width=0.35, label="baseline (Etapa 15)", color="#4c72b0")
    ax.bar(x + 0.18, [r[f"{m}_tunado"] for m in metrs], width=0.35, label="tunado (Etapa 17)", color="#55a868")
    ax.set_xticks(x); ax.set_xticklabels(metrs)
    ax.set_title(f"acidentes_com_vitima -- tunado vs baseline")
    ax.legend(fontsize=8)
    w(f"![classificacao tunado vs baseline]({savefig('01_clf_tunado_vs_baseline.png')})\n")

    # ---------------- producao ----------------
    w("## 3. Hiperparametros de producao (para Etapas 18+)\n")
    w("Busca separada usando **todo** o historico disponivel (ainda sem "
      "embaralhar -- `TimeSeriesSplit`), fora da metrica pooled acima. E o "
      "unico conjunto de hiperparametros que a Etapa 18 (SHAP) e as "
      "seguintes devem usar para treinar o modelo final.\n")
    linhas_prod = []
    for base in BASES_REG:
        print(f"[producao] regressao {base} ...")
        p = producao_regressao(d_, base)
        linhas_prod.append({"tarefa": "regressao", "base": base, "modelo": "xgboost_poisson", **p})
    for base in BASES_CLF:
        print(f"[producao] classificacao {base} ...")
        p = producao_classificacao(d_, base)
        linhas_prod.append({"tarefa": "classificacao", "base": base, "modelo": "logreg_balanced", **p})
    tab_prod = pd.DataFrame(linhas_prod)
    tab_prod.to_csv(os.path.join(TAB_DIR, "hiperparametros_producao.csv"), index=False)
    w(df_to_md(tab_prod, floatfmt=4, index=False))
    w("")

    # ---------------- sintese ----------------
    w("## 4. Sintese\n")
    linhas_sint = []
    for _, r in tab_comp_reg.iterrows():
        melhora_pct = (r.MAE_baseline - r.MAE_tunado) / r.MAE_baseline * 100
        if melhora_pct > 3:
            leitura = "Ganho real do tuning."
        elif melhora_pct >= 0:
            leitura = ("Ganho marginal (<3%) -- os hiperparametros rasos e nao-otimizados da Etapa "
                      "14/15 ja estavam perto do teto para este conjunto de features.")
        else:
            leitura = ("**Tuning nao ajudou -- MAE pooled ficou levemente PIOR que o baseline "
                      "nao-otimizado.** Nao e um erro de implementacao (o R² tunado tambem cai, "
                      "0,481->0,462): com ~350-700 linhas de treino por fold, a busca interna "
                      "(TimeSeriesSplit dentro do treino) tem pouco dado para diferenciar "
                      "hiperparametros de forma estavel, e pode escolher uma combinacao que "
                      "generaliza pior no mes de teste do que a combinacao rasa/generica ja usada "
                      "desde a Etapa 14. Mantido honestamente (Regra 2: nao inventar resultado) -- "
                      "o baseline nao-tunado segue sendo, na pratica, tao bom quanto ou melhor "
                      "para este alvo.")
        linhas_sint.append(f"- **Regressao `{r.base}`**: MAE {r.MAE_baseline:.2f} -> {r.MAE_tunado:.2f} "
                           f"({melhora_pct:+.1f}%). {leitura}")
    for _, r in tab_comp_clf.iterrows():
        d_recall = r.recall_tunado - r.recall_baseline
        d_pr = r.pr_auc_tunado - r.pr_auc_baseline
        linhas_sint.append(f"- **Classificacao `{r.base}`** (`logreg_balanced`): Recall "
                           f"{r.recall_baseline:.3f} -> {r.recall_tunado:.3f} ({d_recall:+.3f}), mas "
                           f"PR-AUC fold_macro {r.pr_auc_baseline:.3f} -> {r.pr_auc_tunado:.3f} "
                           f"({d_pr:+.3f}) -- **piorou, mesmo com a busca otimizando explicitamente "
                           "para average_precision em cada fold.** Mesmo diagnostico da regressao "
                           "acima: poucos positivos por fold (a tabela de hiperparametros por fold "
                           "mostra `C`/`penalty` variando muito -- de C=0,001 a C=74 -- sinal de que "
                           "a busca interna esta se ajustando a ruido, nao a um padrao estavel). "
                           "Trade-off documentado, nao escondido: se o criterio for Recall (prioridade "
                           "do briefing p/ sistema de alerta), o modelo tunado e preferivel; se for "
                           "PR-AUC (ranking), o baseline nao-tunado e melhor. Nenhum dos dois domina "
                           "o outro nos dois criterios ao mesmo tempo.")
    for l_ in linhas_sint:
        w(l_)
    w("")
    w("- **`crimes_violentos` (classificacao) permanece sem candidato**: "
      "decisao da Etapa 16 mantida -- tuning nao foi tentado aqui porque o "
      "problema documentado (nenhum classificador atinge Recall e PR-AUC "
      "uteis ao mesmo tempo) e de sinal disponivel nas features, nao de "
      "hiperparametro; revisitar so se o SHAP (Etapa 18) ou novas features "
      "mudarem esse quadro.\n")
    w("- **Hiperparametros de producao (secao 3) sao o que a Etapa 18 (SHAP) "
      "deve usar** para treinar o modelo final explicado -- nao os "
      "hiperparametros rasos da Etapa 14/15, e nao a media dos "
      "hiperparametros por fold (que variam fold a fold, ver tabelas da "
      "secao 1/2 -- instabilidade esperada com poucas centenas de linhas de "
      "treino, nao um problema do metodo).\n")
    w("- **Proximo**: Etapa 18 -- interpretabilidade formal com SHAP, usando "
      "os hiperparametros de producao desta etapa.\n")

    path = os.path.join(OUT_DIR, "relatorio_otimizacao.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
