"""23_ablacao_futebol.py -- 2a entrega parcial, objetivo (iii): PR-AUC da classificação de pico com e sem as 18 variáveis de futebol.
Replica o walk-forward do scripts/12_validacao_temporal.py (12 folds mensais de 2023, janela
expansiva, calendário e limiar P90 reajustados no treino de cada fold) para os dois
classificadores do sklearn (Regressão Logística balanceada e Random Forest). O XGBoost e o
statsmodels não estão instalados aqui; o ajuste de calendário (OLS) foi reimplementado em numpy."""
import sys, numpy as np, pandas as pd
from scipy.stats import wilcoxon
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score)

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "reports", "entrega2")
os.makedirs(OUT_DIR, exist_ok=True)
PROJ = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR
SEED = 42
BASES = ["crimes_violentos", "acidentes_com_vitima"]
FOLDS = [(pd.Timestamp(f"2023-{m:02d}-01"), pd.Timestamp(f"2023-{m:02d}-01") + pd.offsets.MonthBegin(1)) for m in range(1, 13)]
FEAT_GROUPS = {
    "temporal": ["trend", "sin_doy", "cos_doy", "sin_dow", "cos_dow"] + [f"dow_{k}" for k in range(7)] +
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
def hist_feats(b):
    return ([f"{b}_lag{L}" for L in (1, 2, 3, 7, 14, 28, 364)] + [f"{b}_rollmean{R}" for R in (7, 14, 28)] +
            [f"{b}_rollstd{R}" for R in (7, 14, 28)] + [f"{b}_lag1_vs_rollmean28", f"pico_p90_{b}_lag1", f"pico_p90_{b}_soma7"])
def feature_cols(b, com_futebol=True):
    g = FEAT_GROUPS if com_futebol else {k: v for k, v in FEAT_GROUPS.items() if k != "futebol"}
    return sum(g.values(), []) + hist_feats(b)

fato = pd.read_csv(f"{PROJ}/data/gold/fato_dia_sp.csv", parse_dates=["data"])[["data", "dia_semana"]]
feat = pd.read_csv(f"{PROJ}/data/gold/features_dia_sp.csv", parse_dates=["data"])
d_ = feat.merge(fato, on="data", how="left").sort_values("data").reset_index(drop=True)
d_["t_idx"] = np.arange(len(d_))

def cal_design(x):
    X = pd.DataFrame({"t_idx": x["t_idx"].astype(float), "feriado": x["feriado"].astype(float)}, index=x.index)
    X = X.join(pd.get_dummies(x["dia_semana"].astype(int), prefix="dow").astype(float))
    X = X.join(pd.get_dummies(x["mes"].astype(int), prefix="mes").astype(float))
    return X

def refit_pico(base, train_mask):
    y = d_[f"y_count_{base}"]
    X = cal_design(d_)
    fit_rows = train_mask & y.notna().to_numpy()
    lr = LinearRegression().fit(X[fit_rows], y[fit_rows])  # mesmo espaço de predições do OLS do script 12
    resid = y - lr.predict(X)
    thr = resid[fit_rows].quantile(0.90)
    return pd.Series(np.where(y.notna(), resid > thr, np.nan), index=d_.index).astype("boolean"), thr

def sw_bal(y):
    y = y.astype(int); n, p = len(y), y.sum()
    return np.ones(n) if p in (0, n) else np.where(y == 1, n / (2 * p), n / (2 * (n - p)))

def roda(com_futebol):
    rows = []
    for base in BASES:
        elig = d_[f"y_count_{base}"].notna()
        cols = feature_cols(base, com_futebol)
        for ini, fim in FOLDS:
            tr = (elig & (d_["data"] < ini)).to_numpy(); te = (elig & (d_["data"] >= ini) & (d_["data"] < fim)).to_numpy()
            y_pico, thr = refit_pico(base, tr)
            ytr = y_pico[tr].astype(bool); yte = y_pico[te].astype(bool)
            X = d_[cols].copy()
            if "jogo_noturno" in X: X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
            imp = SimpleImputer(strategy="median").fit(X.loc[tr])
            Xi = pd.DataFrame(imp.transform(X), columns=cols, index=X.index)
            sca = StandardScaler().fit(Xi.loc[tr]); Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=X.index)
            modelos = {}
            lg = LogisticRegression(max_iter=3000, class_weight="balanced").fit(Xs.loc[tr], ytr.astype(int))
            modelos["logreg_balanced"] = lg.predict_proba(Xs.loc[te])[:, 1]
            rf = RandomForestClassifier(n_estimators=400, max_depth=6, min_samples_leaf=5, random_state=SEED, n_jobs=-1)
            rf.fit(Xi.loc[tr], ytr.astype(int), sample_weight=sw_bal(ytr))
            modelos["random_forest"] = rf.predict_proba(Xi.loc[te])[:, 1]
            for nome, sc in modelos.items():
                two = len(set(yte)) > 1
                rows.append({"base": base, "modelo": nome, "fold": ini.strftime("%Y-%m"), "y": yte.to_numpy(), "score": sc,
                             "fold_pr": average_precision_score(yte, sc) if two else np.nan,
                             "fold_roc": roc_auc_score(yte, sc) if two else np.nan})
    out = []
    for (base, nome), g in pd.DataFrame(rows).groupby(["base", "modelo"], sort=False):
        y = np.concatenate(g["y"].to_list()); s = np.concatenate(g["score"].to_list()); pb = s >= 0.5
        out.append({"base": base, "modelo": nome, "futebol": "com" if com_futebol else "sem", "n": len(y), "n_pico": int(y.sum()),
                    "accuracy": accuracy_score(y, pb), "precision": precision_score(y, pb, zero_division=0),
                    "recall": recall_score(y, pb, zero_division=0), "f1": f1_score(y, pb, zero_division=0),
                    "pr_auc_fold_macro": g["fold_pr"].mean(), "roc_auc_fold_macro": g["fold_roc"].mean(),
                    "n_folds_2_classes": int(g["fold_pr"].notna().sum()), "n_features": len(feature_cols(base, com_futebol))})
    return pd.DataFrame(out), pd.DataFrame(rows)

pd.set_option("display.width", 220)
com, rows_com = roda(True)
pub = pd.read_csv(f"{PROJ}/reports/etapa15/tabelas/classificacao_pooled.csv")
chk = com.merge(pub, on=["base", "modelo"], suffixes=("", "_pub"))
print("Conferência com a Etapa 15 (com futebol):")
print(chk[["base", "modelo", "recall", "recall_pub", "precision", "precision_pub", "pr_auc_fold_macro", "pr_auc_fold_macro_pub"]].round(4).to_string(index=False))
sem, rows_sem = roda(False)
res = pd.concat([com, sem])
res.to_csv(os.path.join(OUT_DIR, "ablacao_futebol.csv"), index=False)
print("\nCom x sem variáveis de futebol:")
print(res.round(4).to_string(index=False))
# diferença de PR-AUC por fold (pareada) para cada modelo
for (base, nome) in [(b, m) for b in BASES for m in ["logreg_balanced", "random_forest"]]:
    a = rows_com[(rows_com.base == base) & (rows_com.modelo == nome)].set_index("fold")["fold_pr"]
    b = rows_sem[(rows_sem.base == base) & (rows_sem.modelo == nome)].set_index("fold")["fold_pr"]
    dlt = (a - b).dropna()
    print(f"{base:22s} {nome:16s} folds={len(dlt):2d} delta_medio={dlt.mean():+.4f} folds_com_ganho={int((dlt>0).sum())} folds_com_perda={int((dlt<0).sum())} wilcoxon_p={wilcoxon(dlt).pvalue:.3f}")
