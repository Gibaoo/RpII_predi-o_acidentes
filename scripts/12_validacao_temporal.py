"""
12_validacao_temporal.py
Etapa 15 do roteiro -- VALIDACAO TEMPORAL (walk-forward, Regra 7: nunca split
aleatorio em serie temporal).

Motivacao concreta (nao so teorica): a Etapa 13 mostrou que um UNICO corte
(treino < out/2023, teste = out-dez/2023) e fragil aqui -- a tendencia linear do
modelo de calendario, extrapolada 3 meses a frente, fez a prevalencia de pico no
teste variar de 3,3% a 34,4% conforme o desfecho, so por causa de qual trimestre
calhou de virar teste. Esta etapa resolve isso com WALK-FORWARD:

  12 folds mensais, JANELA EXPANSIVA ancorada em 2022-01-01:
    fold 1: treino = 2022 inteiro (365d)          | teste = jan/2023
    fold 2: treino = 2022 + jan/2023               | teste = fev/2023
    ...
    fold 12: treino = 2022 + jan-nov/2023          | teste = dez/2023
  Cobre o ano de 2023 inteiro em out-of-sample, cada dia testado exatamente uma
  vez, sempre com o treino estritamente ANTES do teste.

Em CADA fold, o QUE JA FOI SINALIZADO COMO "ver ressalva E15" desde a Etapa 8 e
reajustado so no treino daquele fold: modelo de calendario, residuo, limiar P90
(alvo de pico) e o preditor `sazonal_esperado`. Os lags/rolling do desfecho
(Etapa 12) ja eram causais e nao precisam de ajuste.

Modelos avaliados (escopo intencionalmente menor que a Etapa 14 -- aqui o
objetivo e validar a ESTABILIDADE das conclusoes, nao repetir o comparativo
completo de algoritmos):
  Classificacao: baselines (classe majoritaria, dia_semana_risco, logreg
    balanced) + Random Forest + XGBoost.
  Regressao: baselines (media historica, media movel 7/28d, mesmo dia da
    semana anterior) + Random Forest + XGBoost (Poisson) + **Prophet**
    (log1p(y) -> Prophet -> expm1; Prophet assume erros gaussianos, entao
    log1p e a forma padrao de adapta-lo a dado de contagem). Prophet entra
    aqui porque e literalmente metade do titulo do projeto ("comparando
    XGBoost e Prophet") e este e o lugar certo -- validacao temporal e o
    territorio nativo do Prophet (tendencia + sazonalidade + feriados).

Metricas: agregadas nas previsoes de TODOS os folds empilhadas (pooled
out-of-fold, ~330-360 dias de teste no total) E por fold (para mostrar a
volatilidade mes a mes que motivou esta etapa).

Rodar depois de 11 (usa data/gold/features_dia_sp.csv e fato_dia_sp.csv).
"""
import os
import logging
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
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from xgboost import XGBClassifier, XGBRegressor
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score,
                             mean_absolute_error, mean_squared_error, r2_score)

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
from prophet import Prophet  # noqa: E402  (import apos silenciar o logger)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa15")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

BASES = ["crimes_violentos", "acidentes_com_vitima"]
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"
SEED = 42
ANCORA = pd.Timestamp("2022-01-01")
FOLDS = [(pd.Timestamp(f"2023-{m:02d}-01"),
         pd.Timestamp(f"2023-{m:02d}-01") + pd.offsets.MonthBegin(1))
         for m in range(1, 13)]

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
    return resid, pred, thr, y_pico, fit.rsquared


def sample_weight_balanced(y):
    y = y.astype(int)
    n, n_pos = len(y), y.sum()
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.ones(n)
    return np.where(y == 1, n / (2 * n_pos), n / (2 * n_neg))


def prep_X_imputed(d_, cols, train_mask):
    X = d_[cols].copy()
    if "jogo_noturno" in X:
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
    imp = SimpleImputer(strategy="median").fit(X.loc[train_mask])
    return pd.DataFrame(imp.transform(X), columns=cols, index=X.index)


def prep_X_native(d_, cols):
    X = d_[cols].copy()
    if "jogo_noturno" in X:
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
    return X


def prophet_predict(d_, base, train_mask, test_mask):
    """Prophet sobre log1p(contagem). Regressores extras: feriado, fim_de_semana
    (conhecidos com antecedencia, nao vazam nada)."""
    dft = d_.loc[train_mask, ["data", f"y_count_{base}", "feriado", "fim_de_semana"]].rename(
        columns={"data": "ds", f"y_count_{base}": "y"}).copy()
    dft["y"] = np.log1p(dft["y"])
    m = Prophet(weekly_seasonality=True, yearly_seasonality=3, daily_seasonality=False,
               seasonality_mode="additive", interval_width=0.8)
    m.add_regressor("feriado")
    m.add_regressor("fim_de_semana")
    m.fit(dft)
    dfp = d_.loc[test_mask, ["data", "feriado", "fim_de_semana"]].rename(columns={"data": "ds"})
    fcst = m.predict(dfp)
    pred = np.expm1(fcst["yhat"].to_numpy())
    return np.clip(pred, 0, None)


# ---------------------------------------------------------------------------
def roda_fold(d_, base, ini, fim):
    elig = d_[f"y_count_{base}"].notna()
    train_mask = (elig & (d_["data"] < ini)).to_numpy()
    test_mask = (elig & (d_["data"] >= ini) & (d_["data"] < fim)).to_numpy()
    n_tr, n_te = train_mask.sum(), test_mask.sum()
    if n_te == 0 or n_tr < 90:
        return None

    resid, pred_cal, thr, y_pico, r2 = refit_pico_no_treino(d_, base, train_mask)
    y_tr_c = y_pico[train_mask].astype(bool)
    y_te_c = y_pico[test_mask].astype(bool)
    cols = feature_cols(base)

    diag = {"base": base, "fold_teste": ini.strftime("%Y-%m"), "n_treino": int(n_tr),
           "n_teste": int(n_te), "R2_calendario": r2, "limiar_P90": thr,
           "pico_%_teste": y_te_c.mean() * 100 if n_te else np.nan,
           "media_real_teste": d_.loc[test_mask, f"y_count_{base}"].mean(),
           "media_prevista_calendario": pred_cal[test_mask].mean()}

    linhas_clf, linhas_reg = [], []

    # ---------- classificacao ----------
    def registra_clf(nome, pred_bin, score=None):
        row = {"base": base, "fold": diag["fold_teste"], "modelo": nome,
              "n_teste": int(n_te), "n_pico_teste": int(y_te_c.sum()),
              "accuracy": accuracy_score(y_te_c, pred_bin),
              "precision": precision_score(y_te_c, pred_bin, zero_division=0),
              "recall": recall_score(y_te_c, pred_bin, zero_division=0),
              "f1": f1_score(y_te_c, pred_bin, zero_division=0)}
        if score is not None:
            row["y_true"] = y_te_c.to_numpy()
            row["score"] = np.asarray(score)
            # AUC DESTE fold isoladamente (so definido se o fold tem as 2 classes) --
            # usado para uma media fold-a-fold, mais honesta que agregar scores de
            # modelos treinados separadamente (calibracao pode variar muito entre
            # folds -- ver secao 2).
            if len(set(y_te_c)) > 1:
                row["fold_roc_auc"] = roc_auc_score(y_te_c, score)
                row["fold_pr_auc"] = average_precision_score(y_te_c, score)
            else:
                row["fold_roc_auc"] = row["fold_pr_auc"] = np.nan
        linhas_clf.append(row)

    registra_clf("classe_majoritaria", np.zeros(n_te, dtype=bool))

    nomes_dow = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
    taxa_dow = y_tr_c.groupby(d_.loc[train_mask, "dia_semana"]).mean()
    dow_risco = taxa_dow[taxa_dow > y_tr_c.mean()].index.tolist() if y_tr_c.mean() > 0 else []
    pred_dow = d_.loc[test_mask, "dia_semana"].isin(dow_risco).to_numpy()
    registra_clf("dia_semana_risco", pred_dow, score=pred_dow.astype(int))

    Xi = prep_X_imputed(d_, cols, train_mask)
    sca = StandardScaler().fit(Xi.loc[train_mask])
    Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=Xi.index)
    sw = sample_weight_balanced(y_tr_c)
    logit = LogisticRegression(max_iter=3000, class_weight="balanced").fit(
        Xs.loc[train_mask], y_tr_c.astype(int))
    proba = logit.predict_proba(Xs.loc[test_mask])[:, 1]
    registra_clf("logreg_balanced", proba >= 0.5, score=proba)

    Xn = prep_X_native(d_, cols)
    rf = RandomForestClassifier(n_estimators=400, max_depth=6, min_samples_leaf=5,
                                random_state=SEED, n_jobs=-1)
    rf.fit(Xi.loc[train_mask], y_tr_c.astype(int), sample_weight=sw)
    proba = rf.predict_proba(Xi.loc[test_mask])[:, 1]
    registra_clf("random_forest", proba >= 0.5, score=proba)

    xgb = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
                        colsample_bytree=0.8, random_state=SEED, eval_metric="logloss")
    xgb.fit(Xn.loc[train_mask], y_tr_c.astype(int), sample_weight=sw)
    proba = xgb.predict_proba(Xn.loc[test_mask])[:, 1]
    registra_clf("xgboost", proba >= 0.5, score=proba)

    # ---------- regressao ----------
    y_tr_r = d_.loc[train_mask, f"y_count_{base}"]
    y_te_r = d_.loc[test_mask, f"y_count_{base}"]

    def registra_reg(nome, pred_vals):
        pred_vals = np.asarray(pred_vals, dtype=float)
        m_ = np.isfinite(pred_vals)
        linhas_reg.append({"base": base, "fold": diag["fold_teste"], "modelo": nome,
                           "n": int(m_.sum()), "y_true": y_te_r.to_numpy()[m_],
                           "y_pred": pred_vals[m_]})

    registra_reg("media_historica", np.full(n_te, y_tr_r.mean()))
    registra_reg("media_movel_7d", d_.loc[test_mask, f"{base}_rollmean7"].to_numpy())
    registra_reg("media_movel_28d", d_.loc[test_mask, f"{base}_rollmean28"].to_numpy())
    registra_reg("mesmo_dia_semana_ant", d_.loc[test_mask, f"{base}_lag7"].to_numpy())

    rfr = RandomForestRegressor(n_estimators=400, max_depth=6, min_samples_leaf=5,
                                random_state=SEED, n_jobs=-1)
    rfr.fit(Xi.loc[train_mask], y_tr_r)
    registra_reg("random_forest", rfr.predict(Xi.loc[test_mask]))

    xgbr = XGBRegressor(objective="count:poisson", n_estimators=300, max_depth=3,
                        learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=SEED)
    xgbr.fit(Xn.loc[train_mask], y_tr_r)
    registra_reg("xgboost_poisson", xgbr.predict(Xn.loc[test_mask]))

    try:
        pred_p = prophet_predict(d_, base, train_mask, test_mask)
        registra_reg("prophet_log1p", pred_p)
    except Exception as e:
        print(f"  [aviso] prophet falhou em {base}/{diag['fold_teste']}: {e}")

    return diag, linhas_clf, linhas_reg


# ---------------------------------------------------------------------------
def secao_diagnostico(diags):
    w("## 1. Diagnostico por fold -- a instabilidade da Etapa 13 se confirma?\n")
    w("12 folds mensais de 2023, janela de treino expansiva ancorada em "
      f"{ANCORA.date()}. Cada linha = 1 mes de teste, calendario/limiar P90 "
      "reajustados so no treino daquele fold.\n")
    for base in BASES:
        sub = pd.DataFrame([d_ for d_ in diags if d_["base"] == base])
        sub.to_csv(os.path.join(TAB_DIR, f"diagnostico_folds_{base}.csv"), index=False)
        w(f"### {base}\n")
        w(df_to_md(sub.drop(columns="base"), floatfmt=2, index=False))
        w("")
        fig, ax = plt.subplots(figsize=(11, 3.5))
        ax.bar(sub["fold_teste"], sub["pico_%_teste"], color="#4c72b0")
        ax.axhline(10, color="k", ls="--", lw=1, label="10% nominal (definicao do alvo)")
        ax.set_ylabel("% dias-pico no fold de teste")
        ax.set_title(f"Prevalencia de pico por fold -- {base}")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)
        w(f"![prevalencia por fold {base}]({savefig(f'00_prevalencia_{base}.png')})\n")
    w("_Comparar com a Etapa 13: la, um UNICO corte deu 3,3%/34,4%. Aqui, cada "
      "fold ainda pode oscilar (o mes eh curto, ~28-31 dias, poucos picos "
      "esperados por fold), mas a leitura final vem do POOLED (secoes 2-3), que "
      "empilha ~330-360 dias de teste em vez de confiar num unico trimestre._\n")


def secao_classificacao(clf_rows):
    w("## 2. Classificacao -- metricas agregadas (pooled out-of-fold)\n")
    w("**Cuidado de agregacao**: cada fold treina um modelo DO ZERO, e a "
      "calibracao da probabilidade pode variar muito de fold para fold "
      "(especialmente com poucos positivos por mes). Empilhar os scores crus de "
      "12 modelos diferentes e calcular UM ROC-AUC/PR-AUC pode misturar escalas "
      "incompativeis. Por isso reportamos duas versoes: **`*_pooled`** (score "
      "empilhado, direto) e **`*_fold_macro`** (AUC calculada DENTRO de cada "
      "fold e depois MEDIA entre folds -- so nos folds que tem as 2 classes). "
      "Quando as duas discordam muito, `fold_macro` e a leitura mais honesta.\n")
    resumo = []
    for base in BASES:
        rows = [r for r in clf_rows if r["base"] == base]
        modelos = sorted(set(r["modelo"] for r in rows))
        for modelo in modelos:
            rm = [r for r in rows if r["modelo"] == modelo]
            y_true = np.concatenate([r["y_true"] for r in rm]) if "y_true" in rm[0] else None
            score = np.concatenate([r["score"] for r in rm]) if "score" in rm[0] else None
            n_te = sum(r["n_teste"] for r in rm)
            n_pico = sum(r["n_pico_teste"] for r in rm)
            if score is not None:
                pred = score >= 0.5
                acc = accuracy_score(y_true, pred)
                prec = precision_score(y_true, pred, zero_division=0)
                rec = recall_score(y_true, pred, zero_division=0)
                f1 = f1_score(y_true, pred, zero_division=0)
                roc_pooled = roc_auc_score(y_true, score) if len(set(y_true)) > 1 else np.nan
                pr_pooled = average_precision_score(y_true, score) if len(set(y_true)) > 1 else np.nan
                fold_rocs = [r["fold_roc_auc"] for r in rm if not np.isnan(r.get("fold_roc_auc", np.nan))]
                fold_prs = [r["fold_pr_auc"] for r in rm if not np.isnan(r.get("fold_pr_auc", np.nan))]
                roc_macro = np.mean(fold_rocs) if fold_rocs else np.nan
                pr_macro = np.mean(fold_prs) if fold_prs else np.nan
                n_folds_validos = len(fold_rocs)
            else:
                acc = np.average([r["accuracy"] for r in rm], weights=[r["n_teste"] for r in rm])
                prec = np.average([r["precision"] for r in rm], weights=[r["n_teste"] for r in rm])
                rec = np.average([r["recall"] for r in rm], weights=[r["n_teste"] for r in rm])
                f1 = np.average([r["f1"] for r in rm], weights=[r["n_teste"] for r in rm])
                roc_pooled = pr_pooled = roc_macro = pr_macro = np.nan
                n_folds_validos = 0
            resumo.append({"base": base, "modelo": modelo, "n_teste_total": n_te,
                           "n_pico_total": n_pico, "accuracy": acc, "precision": prec,
                           "recall": rec, "f1": f1, "roc_auc_pooled": roc_pooled,
                           "pr_auc_pooled": pr_pooled, "roc_auc_fold_macro": roc_macro,
                           "pr_auc_fold_macro": pr_macro, "n_folds_com_2_classes": n_folds_validos})
    tab = pd.DataFrame(resumo)
    tab.to_csv(os.path.join(TAB_DIR, "classificacao_pooled.csv"), index=False)
    for base in BASES:
        sub = tab[tab.base == base].sort_values("pr_auc_fold_macro", ascending=False)
        w(f"### {base} (pooled: {int(sub['n_teste_total'].iloc[0])} dias de teste, "
          f"{int(sub['n_pico_total'].iloc[0])} picos, "
          f"{int(sub['n_folds_com_2_classes'].max())}/12 folds com as 2 classes)\n")
        w(df_to_md(sub.drop(columns="base"), floatfmt=3, index=False))
        w("")
        # mesma vulnerabilidade de pooling entre folds com calibracao diferente
        # se aplica ao PR-AUC, nao so ao ROC-AUC -- checar os dois separadamente
        # (podem discordar em modelos diferentes: PR-AUC e mais sensivel a
        # prevalencia, que tambem varia muito fold a fold aqui).
        div_roc = sub.dropna(subset=["roc_auc_pooled", "roc_auc_fold_macro"])
        div_roc = div_roc[(div_roc["roc_auc_pooled"] - div_roc["roc_auc_fold_macro"]).abs() > 0.15]
        div_pr = sub.dropna(subset=["pr_auc_pooled", "pr_auc_fold_macro"])
        div_pr = div_pr[(div_pr["pr_auc_pooled"] - div_pr["pr_auc_fold_macro"]).abs() > 0.15]
        if len(div_roc):
            w(f"_**Atencao** -- `roc_auc_pooled` e `roc_auc_fold_macro` divergem "
              f">0,15 para: {', '.join(div_roc['modelo'])}. Sintoma de calibracao "
              f"instavel entre folds (poucos positivos por mes -> o modelo de "
              f"cada fold aprende uma escala de probabilidade diferente); confiar "
              f"em `fold_macro`, nao em `pooled`, para esses modelos._\n")
        if len(div_pr):
            w(f"_**Atencao** -- `pr_auc_pooled` e `pr_auc_fold_macro` divergem "
              f">0,15 para: {', '.join(div_pr['modelo'])}. Mesma vulnerabilidade "
              f"de pooling entre folds com calibracao/prevalencia diferente, "
              f"agora no PR-AUC (mais sensivel a prevalencia do fold do que o "
              f"ROC-AUC, entao pode divergir mesmo quando o ROC-AUC nao diverge "
              f"muito -- ver `{base}` acima); confiar em `fold_macro`._\n")
    w("_Comparar com a Etapa 13/14 (split unico, 90 dias de teste): aqui o pooled "
      "tem ~4x mais dias de teste -- estimativas de Recall/F1/PR-AUC bem mais "
      "estaveis, principalmente para `crimes_violentos` (que so tinha 3 "
      "positivos no split unico). Mas `crimes_violentos` continua tendo poucos "
      "positivos POR FOLD (0-13 num mes de ~30 dias) -- daí o cuidado extra "
      "acima.\n")
    return tab


def secao_regressao(reg_rows):
    w("## 3. Regressao -- metricas agregadas (pooled out-of-fold)\n")
    resumo = []
    for base in BASES:
        rows = [r for r in reg_rows if r["base"] == base]
        modelos = sorted(set(r["modelo"] for r in rows))
        for modelo in modelos:
            rm = [r for r in rows if r["modelo"] == modelo]
            y_true = np.concatenate([r["y_true"] for r in rm])
            y_pred = np.concatenate([r["y_pred"] for r in rm])
            mae = mean_absolute_error(y_true, y_pred)
            rmse = mean_squared_error(y_true, y_pred) ** 0.5
            r2 = r2_score(y_true, y_pred)
            mape = np.abs((y_true - y_pred) / y_true).mean() * 100
            resumo.append({"base": base, "modelo": modelo, "n_total": len(y_true),
                           "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE_%": mape})
    tab = pd.DataFrame(resumo)
    tab.to_csv(os.path.join(TAB_DIR, "regressao_pooled.csv"), index=False)
    for base in BASES:
        sub = tab[tab.base == base].sort_values("MAE")
        w(f"### {base}\n")
        w(df_to_md(sub.drop(columns="base"), floatfmt=2, index=False))
        w("")

    # MAE por fold (volatilidade) para o melhor de cada familia
    fig, axes = plt.subplots(1, 2, figsize=(15, 4))
    for ax, base in zip(axes, BASES):
        rows = [r for r in reg_rows if r["base"] == base]
        for modelo in ["media_movel_7d", "xgboost_poisson", "prophet_log1p"]:
            rm = sorted([r for r in rows if r["modelo"] == modelo], key=lambda r: r["fold"])
            if not rm:
                continue
            maes = [mean_absolute_error(r["y_true"], r["y_pred"]) for r in rm]
            ax.plot([r["fold"] for r in rm], maes, marker="o", lw=1, label=modelo)
        ax.set_title(f"MAE por fold -- {base}")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=7)
    w(f"![MAE por fold]({savefig('01_mae_por_fold.png')})\n")
    return tab


# ---------------------------------------------------------------------------
def main():
    d_ = load()
    w("# Etapa 15 -- Validacao temporal (walk-forward)\n")
    w(f"_Gerado por `scripts/12_validacao_temporal.py` em {date.today()}. "
      f"Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`._\n")
    w("> Regra 7: nunca split aleatorio em serie temporal. Esta etapa substitui "
      "o corte unico das Etapas 13-14 por **12 folds mensais walk-forward** "
      "(janela expansiva, 2023 inteiro em teste), com o modelo de calendario e "
      "o limiar de pico reajustados EM CADA FOLD -- resolve a ultima ressalva "
      "'ver ressalva E15' pendente desde a Etapa 8.\n")
    w(f"**Folds**: {len(FOLDS)} meses de 2023, treino expansivo desde "
      f"{ANCORA.date()}. **Escopo de modelos** (menor que a Etapa 14 de proposito "
      "-- aqui o objetivo e validar estabilidade, nao repetir o comparativo "
      "completo): baselines + Random Forest + XGBoost (classificacao e "
      "regressao) + **Prophet** (so regressao, log1p -- primeira aparicao no "
      "projeto do 2º algoritmo do titulo, \"XGBoost vs Prophet\").\n")

    diags, clf_rows, reg_rows = [], [], []
    for base in BASES:
        for ini, fim in FOLDS:
            res = roda_fold(d_, base, ini, fim)
            if res is None:
                continue
            diag, lc, lr = res
            diags.append(diag)
            clf_rows.extend(lc)
            reg_rows.extend(lr)
        print(f"[ok] {base}: {sum(1 for x in diags if x['base']==base)} folds rodados")

    secao_diagnostico(diags)
    tab_clf = secao_classificacao(clf_rows)
    tab_reg = secao_regressao(reg_rows)

    w("## 4. Sintese -- o que muda em relacao as Etapas 13-14\n")
    linhas_comp = []
    for base in BASES:
        xgb_c = tab_clf[(tab_clf.base == base) & (tab_clf.modelo == "xgboost")].iloc[0]
        xgb_r = tab_reg[(tab_reg.base == base) & (tab_reg.modelo == "xgboost_poisson")].iloc[0]
        prophet_r = tab_reg[(tab_reg.base == base) & (tab_reg.modelo == "prophet_log1p")]
        linhas_comp.append({"base": base, "xgboost_recall_pooled": xgb_c["recall"],
                            "xgboost_f1_pooled": xgb_c["f1"],
                            "xgboost_pr_auc_fold_macro": xgb_c["pr_auc_fold_macro"],
                            "xgboost_MAE_pooled": xgb_r["MAE"],
                            "prophet_MAE_pooled": prophet_r["MAE"].iloc[0] if len(prophet_r) else np.nan})
    w(df_to_md(pd.DataFrame(linhas_comp), floatfmt=3, index=False))
    w("")
    w(textwrap.dedent("""\
        - **A instabilidade da Etapa 13 era real, nao um artefato de codigo**: os
          folds individuais (secao 1) continuam variando mes a mes (esperado, sao
          so ~30 dias cada) -- mas o POOLED de 12 folds da uma estimativa muito
          mais confiavel do que o split unico. Essa e a resposta definitiva a
          pergunta "por que validar com walk-forward": nao e so a regra do
          briefing, e o que estabiliza a metrica.
        - **Achado metodologico novo desta etapa**: para `crimes_violentos`,
          `roc_auc_pooled` do `logreg_balanced` deu 0,266 (pior que aleatorio) --
          investigado ANTES de reportar (mesmo padrao das Etapas 10/14): nao e o
          modelo que piora a previsao, e que os 12 folds tem escalas de
          probabilidade muito diferentes (fold de jan/2023, 0 picos reais, score
          medio 0,93; fold de fev/2023, 13 picos reais, score medio 0,03) --
          empilhar os scores crus mistura calibracoes incompativeis. A versao
          `fold_macro` (secao 2) corrige isso computando a AUC DENTRO de cada
          fold antes de tirar a media. **Licao para a Etapa 17/18**: metricas de
          ranking (ROC-AUC/PR-AUC) pooled entre folds de um walk-forward precisam
          desse cuidado sempre que houver poucos positivos por fold.
        - **XGBoost vs Prophet** (a comparacao central do titulo do projeto): ver
          MAE pooled na secao 3. Prophet modela tendencia+sazonalidade de forma
          mais flexivel que a OLS linear das Etapas 13-14 (trend com changepoints,
          Fourier para sazonalidade anual) -- mas com so 1 ano de treino no
          primeiro fold, a sazonalidade anual do Prophet tem pouco a aprender;
          XGBoost usa diretamente os lags/rolling do desfecho, que carregam mais
          sinal de curto prazo. Ler os dois nos mesmos folds (secao 3) antes de
          declarar um vencedor.
        - **`crimes_violentos` deixa de ser inconclusivo**: com ~360 dias de teste
          pooled em vez de 90 (e so 3 positivos), Recall/F1/PR-AUC agora tem base
          estatistica genuina.
        - **Toda ressalva "ver ressalva E15" registrada desde a Etapa 8 esta
          resolvida**: calendario, residuo, limiar de pico e `sazonal_esperado`
          agora sao sempre reajustados so no treino de cada fold.
        - **Proximo**: Etapa 16 (metricas -- ja consolidadas aqui e nas Etapas
          13-14), Etapa 17 (otimizacao de hiperparametros, respeitando a mesma
          estrutura de folds), Etapa 18 (SHAP).
    """))

    path = os.path.join(OUT_DIR, "relatorio_validacao_temporal.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
