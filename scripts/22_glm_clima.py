"""22_glm_clima.py -- 2a entrega parcial, objetivo (i): GLM de Poisson com erros-padrão HC1, controle de calendário e clima.
Reimplementa em numpy o modelo do 04_analise_jogo_vs_naojogo.py (statsmodels não está
disponível neste ambiente) e confere contra a tabela publicada antes de adicionar clima."""
import sys, numpy as np, pandas as pd
from scipy import stats

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "reports", "entrega2")
os.makedirs(OUT_DIR, exist_ok=True)
PROJ = sys.argv[1] if len(sys.argv) > 1 else BASE_DIR
df = pd.read_csv(f"{PROJ}/data/gold/fato_dia_sp.csv", parse_dates=["data"]).sort_values("data").reset_index(drop=True)
EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}
CRIME = ["crimes_totais", "crimes_violentos", "roubos_total", "furtos_total", "lesao_corporal_dolosa", "homicidios_dolosos"]
ACID = ["acidentes_total", "acidentes_com_vitima", "atropelamentos", "colisoes", "acidentes_fatais"]
PARADA = {pd.Timestamp("2022-06-19"), pd.Timestamp("2023-06-11")}

def design(d, clima=False, parada=False):
    X = pd.DataFrame({"const": 1.0, "tem_jogo_sp": d["tem_jogo_sp"].astype(int)}, index=d.index)
    X = X.join(pd.get_dummies(d["dia_semana"].astype(int), prefix="dow", drop_first=True).astype(float))
    X["feriado"] = d["feriado"].astype(int)
    X = X.join(pd.get_dummies(d["mes"].astype(int), prefix="mes", drop_first=True).astype(float))
    if clima:
        for c in ["temp_media", "precipitacao_total", "umidade_media"]:
            X[c] = d[c].astype(float)
    if parada:
        X["parada"] = d["data"].isin(PARADA).astype(float)
    return X

def poisson_hc1(y, X, iters=100):
    Xv, yv = X.to_numpy(float), y.to_numpy(float)
    beta = np.zeros(Xv.shape[1]); beta[0] = np.log(yv.mean())
    for _ in range(iters):
        eta = Xv @ beta; mu = np.exp(eta)
        z = eta + (yv - mu) / mu
        WX = Xv * mu[:, None]
        new = np.linalg.solve(Xv.T @ WX, WX.T @ z)
        if np.max(np.abs(new - beta)) < 1e-10:
            beta = new; break
        beta = new
    mu = np.exp(Xv @ beta)
    n, k = Xv.shape
    bread = np.linalg.inv(Xv.T @ (Xv * mu[:, None]))
    S = Xv * (yv - mu)[:, None]
    # o statsmodels (cov_type="HC1" em GLM), usado no script 04, não aplica o fator n/(n-k);
    # mantemos a mesma fórmula para os números serem comparáveis com a tabela publicada
    cov = bread @ (S.T @ S) @ bread
    se = np.sqrt(np.diag(cov))
    return beta, se, n

def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    r = p[o] * n / (np.arange(n) + 1)
    a = np.minimum.accumulate(r[::-1])[::-1]
    out = np.empty(n); out[o] = np.clip(a, 0, 1); return out

def roda(clima=False, parada=False):
    rows = []
    for fam, outs, excl in [("crime", CRIME, EXCL_CRIME), ("acidente", ACID, EXCL_ACID)]:
        d = df[~df["data"].isin(excl)].copy()
        if clima:
            d = d.dropna(subset=["temp_media", "precipitacao_total", "umidade_media"])
        X = design(d, clima, parada)
        for col in outs:
            beta, se, n = poisson_hc1(d[col], X)
            j = list(X.columns).index("tem_jogo_sp")
            b, s = beta[j], se[j]
            p = 2 * stats.norm.sf(abs(b / s))
            rows.append({"familia": fam, "desfecho": col, "n": n, "RR": np.exp(b),
                         "IC_lo": np.exp(b - 1.959964 * s), "IC_hi": np.exp(b + 1.959964 * s), "p": p})
    r = pd.DataFrame(rows); r["p_BH"] = bh(r["p"]); r["efeito_%"] = (r["RR"] - 1) * 100
    return r

pd.set_option("display.width", 200)
base = roda()
pub = pd.read_csv(f"{PROJ}/reports/etapa7/tabelas/ajustado_glm_poisson.csv")
chk = base.merge(pub, left_on="desfecho", right_on="variavel")
print("Conferência com a tabela publicada (calendário):")
print("max |RR - RR_pub| =", np.abs(chk["RR"] - chk["rate_ratio_jogo"]).max(),
      " max |p - p_pub| =", np.abs(chk["p"] - chk["p_value"]).max(),
      " max |IC_lo - pub| =", np.abs(chk["IC_lo"] - chk["IC95_lo"]).max())
clima = roda(clima=True)
print("\nCalendário + clima (temperatura, precipitação, umidade):")
print(clima.round(4).to_string(index=False))
clima.to_csv(os.path.join(OUT_DIR, "glm_calendario_clima.csv"), index=False)
cp = roda(clima=True, parada=True)
print("\nCalendário + clima + indicador da Parada LGBT+:")
print(cp.round(4).to_string(index=False))
cp.to_csv(os.path.join(OUT_DIR, "glm_calendario_clima_parada.csv"), index=False)
