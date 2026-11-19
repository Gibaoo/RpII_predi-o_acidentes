"""
V2 / Fase 3 -- 34_preditivo_janelas.py
Bloco preditivo no painel horario. Pergunta: saber que havera jogo melhora a previsao hora a hora?
Crimes e sinistros sempre separados.

CENARIO: previsao feita na vespera (ate 23h59 do dia anterior). So entram variaveis conhecidas nesse momento:
  - calendario (hora, dia da semana, mes, tendencia, feriado, vespera, ferias);
  - agenda de jogos (janela, hora_relativa, capital/fora, competicao, classico, mandante, n jogos fora
    simultaneos) e PUBLICO HISTORICO do mandante (media dos jogos ANTERIORES; o publico real nao entra);
  - clima do dia como previsao perfeita (principal) e variante conservadora com o clima da mesma hora do
    dia anterior (lag 24 h);
  - historico do proprio desfecho so com defasagem >= 24 h: lag 24/48/168 h, media da mesma hora x dia da
    semana nas 4 semanas anteriores, media horaria do dia anterior.
ESCALAS: (a) cidade toda; (b) entorno de 3 km de cada estadio (Neo Quimica, Allianz, Morumbi), estadio
como variavel. Alvos: crimes -- crimes_violentos (cidade e entorno), roubos_total e furtos_total (entorno);
sinistros -- acidentes_com_vitima (cidade e entorno).
MODELOS (hiperparametros fixos e rasos; a Etapa 17 mostrou que tuning nao ajuda com este volume):
  baseline = media da mesma hora x dia da semana nas 4 semanas anteriores;
  GLM Poisson = especificacao da Fase 2 sem variaveis proibidas (EF hora x dia da semana, mes do ano +
    tendencia no lugar de ano x mes, que nao existe para o mes de teste; feriado/vespera/ferias; clima; jogo);
    no entorno, um GLM por estadio (= interacao completa com o estadio);
  XGBoost Poisson (todas as variaveis acima, estadio one-hot no entorno);
  Prophet (sazonalidade diaria condicional a dia util/fim de semana + semanal; regressores de jogo e clima;
    log1p) -- so na escala cidade: no entorno as contagens sao esparsas (0,1-1 por hora) e o Prophet
    (gaussiano em log1p) nao e adequado.
VALIDACAO: walk-forward 12 folds mensais de 2023, janela expansiva desde 2022-01, tudo reajustado so no
treino. Exclui dias censurados/lacunas do dominio e horas dos eventos de grande publico sem os 4 times.
ABLACAO: cada modelo com e sem as variaveis de jogo; deviance de Poisson e MAE no geral e so nas horas de
janela; IC da diferenca por bootstrap em blocos de semana (1.000).
PICO: definicao validada na Fase 2 (P90 do residuo de Pearson do modelo calendario+clima ajustado no treino;
hora); no entorno, "hora de risco" = P(Y >= obs | esperado calendario+clima) < 0,10. Score de cada modelo =
P(Y acima do limiar | media prevista) (Poisson). PR-AUC fold_macro e Recall no ponto de operacao (limiar que
reproduz no treino a prevalencia do treino); nunca Accuracy.
SHAP so se a ablacao mostrar ganho, com auditoria de colinearidade com o calendario (Etapa 18).
PRODUTO: tabela de risco esperado por estadio x janela para um jogo tipico.

Rodar:  python scripts/34_preditivo_janelas.py     (~25-35 min)
"""
import importlib
import logging
import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import average_precision_score

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
m = importlib.import_module("33_analise_janelas")
REP = m.REP
RNG = np.random.default_rng(20261117)
XGB_PARAMS = dict(objective="count:poisson", n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.8,
                  colsample_bytree=0.8, min_child_weight=5, tree_method="hist", max_delta_step=0.7, verbosity=0)
ALVOS = {"crimes": {"cidade": ["crimes_violentos"], "entorno": ["crimes_violentos", "roubos_total", "furtos_total"]},
         "sinistros": {"cidade": ["acidentes_com_vitima"], "entorno": ["acidentes_com_vitima"]}}
FOLDS = [(pd.Timestamp(2023, k, 1), pd.Timestamp(2023, k, 1) + pd.offsets.MonthBegin(1)) for k in range(1, 13)]
FOLDS = FOLDS[-int(os.environ.get("N_FOLDS", "12")):]       # N_FOLDS=1 so para teste rapido
MODELOS_PROPHET = os.environ.get("SEM_PROPHET") != "1"


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------
def publico_historico(jogos):
    """media do publico dos jogos ANTERIORES do mesmo mandante (expanding, sem o proprio jogo)."""
    j = jogos.sort_values("inicio_br").copy()
    p = j["publico"].where(j["publico"] > 0)
    j["publico_hist_mandante"] = p.groupby(j["mandante"]).transform(lambda s: s.shift(1).expanding().mean())
    return j.set_index("jogo_id")["publico_hist_mandante"]


def base_horas(f, jogos, fora):
    d = f.copy()
    d["t"] = (d["hora_ts"] - d["hora_ts"].min()).dt.days / 365.0
    d["chuva_lag24"] = d["chuva_mm"].shift(24)
    d["temp_lag24"] = d["temp"].shift(24)
    d["chuva_l_lag24"] = np.log1p(d["chuva_lag24"].fillna(0))
    d["chuva_na_lag24"] = d["chuva_lag24"].isna().astype(float)
    ph = publico_historico(jogos)
    jg = jogos.set_index("jogo_id")
    d["jg_publico_hist"] = d["jogo_id"].map(ph)
    d["jg_classico"] = d["jogo_id"].map(jg["classico"]).astype(float)
    d["jg_noturno"] = d["jogo_id"].map(jg["noturno"]).astype(float)
    comp = d["jogo_id"].map(jg["competicao"]).map(m._comp4)
    for c in ("Serie A", "Copa do Brasil", "Campeonato Paulista", "CONMEBOL"):
        d[f"jg_comp_{c}"] = (comp == c).astype(float)
    mand = d["jogo_id"].map(jg["mandante"])
    for t in m.MONIT:
        d[f"jg_mand_{t}"] = (mand == t).astype(float)
        d[f"fo_time_{t}"] = d["times_fora_capital"].fillna("").str.contains(t).astype(float)
    d["jg_hora_rel"] = d["hora_relativa"]
    d["fo_hora_rel"] = d["hora_relativa_fora_capital"]
    d["fo_n_simult"] = d["n_jogos_fora_simultaneos"].astype(float)
    d["dia_de_jogo_f"] = d["dia_de_jogo"].astype(float)
    dias_est = jogos.assign(dia=jogos["data_br"].dt.normalize()).drop_duplicates("dia").set_index("dia")["estadio"]
    d["estadio_do_dia"] = d["data"].map(dias_est)
    return d


CAL = ["hora_do_dia", "dia_semana", "mes", "t", "feriado", "vespera_feriado", "ferias"]
CLIMA = {"perfeito": ["chuva_l", "chuva_na", "temp"], "lag24": ["chuva_l_lag24", "chuva_na_lag24", "temp_lag24"]}
HIST = ["lag24", "lag48", "lag168", "mm_hd4", "media_dia_anterior"]
JOGO_CAP = ["C_pre", "C_durante", "C_pos", "C_fdj", "jg_hora_rel", "jg_publico_hist", "jg_classico", "jg_noturno",
            "jg_comp_Serie A", "jg_comp_Copa do Brasil", "jg_comp_Campeonato Paulista", "jg_comp_CONMEBOL",
            "dia_de_jogo_f"] + [f"jg_mand_{t}" for t in m.MONIT]
JOGO_FORA = ["F_pre", "F_durante", "F_pos", "fo_hora_rel", "fo_n_simult"] + [f"fo_time_{t}" for t in m.MONIT]
JOGO_GLM = ["C_pre", "C_durante", "C_pos", "C_fdj", "F_pre", "F_durante", "F_pos"]


def historico(y, ts):
    """lags >= 24 h da serie y (indexada por hora continua)."""
    s = pd.Series(y, index=ts)
    out = pd.DataFrame(index=ts)
    out["lag24"], out["lag48"], out["lag168"] = s.shift(24), s.shift(48), s.shift(168)
    out["mm_hd4"] = pd.concat([s.shift(168 * k) for k in (1, 2, 3, 4)], axis=1).mean(axis=1)
    dia = s.groupby(s.index.normalize()).mean()
    out["media_dia_anterior"] = pd.Series(s.index.normalize(), index=ts).map(dia.shift(1, freq="D")).to_numpy()
    return out


def painel(d, dom, escala, y, cont=None):
    """DataFrame de modelagem: 1 linha por hora (cidade) ou por estadio x hora (entorno)."""
    excl = d[m.DOM[dom]["excl"]] | d["excluir_evento_grande_publico"] | d["temp"].isna()
    if escala == "cidade":
        p = d.copy()
        yy = d[y].astype(float).where(~d[m.DOM[dom]["excl"]])     # dia censurado/lacuna nao alimenta lag
        p["y"] = yy
        p = pd.concat([p, historico(yy.to_numpy(), d["hora_ts"]).set_index(p.index)], axis=1)
        p["avaliar"] = ~excl
        p["estadio"] = "cidade"
        return p
    partes = []
    for s in m.ESTADIOS:
        p = d.copy()
        yy = cont[(s, "disco", y)].reindex(d["hora_ts"]).astype(float).where(~d[m.DOM[dom]["excl"]].to_numpy())
        p["y"] = yy.to_numpy()
        p = pd.concat([p, historico(p["y"].to_numpy(), d["hora_ts"]).set_index(p.index)], axis=1)
        este = d["jogo_estadio"].eq(s)
        for w in m.WIN:
            p[f"C_{w}"] = ((d[f"C_{w}"] == 1) & este).astype(float)               # jogo NESTE estadio
            p[f"C_{w}_outro"] = ((d[f"C_{w}"] == 1) & ~este).astype(float)        # jogo em outro estadio
        p["C_fdj"] = ((d["C_fdj"] == 1) & d["estadio_do_dia"].eq(s)).astype(float)   # dia de jogo NESTE estadio
        for c in ("jg_hora_rel", "jg_publico_hist", "jg_classico", "jg_noturno") + \
                tuple(x for x in JOGO_CAP if x.startswith("jg_comp") or x.startswith("jg_mand")):
            p[c] = d[c].where(este)
        p["estadio"] = s
        for s2 in m.ESTADIOS:
            p[f"est_{s2}"] = float(s2 == s)
        p["avaliar"] = ~excl
        partes.append(p)
    return pd.concat(partes, ignore_index=True)


def colunas(escala, com_jogo, clima="perfeito"):
    cols = CAL + CLIMA[clima] + HIST
    if escala == "entorno":
        cols = cols + [f"est_{s}" for s in m.ESTADIOS]
    if com_jogo:
        cols = cols + JOGO_CAP + JOGO_FORA + ([f"C_{w}_outro" for w in m.WIN] if escala == "entorno" else [])
    return cols


# ---------------------------------------------------------------------------
# modelos
# ---------------------------------------------------------------------------
def glm_X(p, com_jogo, escala):
    X = pd.get_dummies(p[["hd"]].assign(mes=p["mes"].astype(str)), drop_first=True).astype(float)
    for c in ("t", "feriado", "vespera_feriado", "ferias", "chuva_l", "chuva_na", "temp"):
        X[c] = p[c].to_numpy(float)
    if com_jogo:
        for c in JOGO_GLM + ([f"C_{w}_outro" for w in m.WIN] if escala == "entorno" else []):
            X[c] = p[c].to_numpy(float)
    X.insert(0, "const", 1.0)
    return X


def prev_glm(p, tr, te, com_jogo, escala):
    out = np.full(len(p), np.nan)
    grupos = [p.index] if escala == "cidade" else [p.index[p["estadio"] == s] for s in m.ESTADIOS]
    for idx in grupos:
        sub = p.loc[idx]
        X = glm_X(sub, com_jogo, escala)
        a, b = tr[idx], te[idx]
        keep = X.columns[(X[a] != 0).any(axis=0)]
        r = sm.GLM(sub.loc[a, "y"].to_numpy(), X.loc[a, keep], family=sm.families.Poisson()).fit()
        out[np.where(np.isin(p.index, idx))[0][b]] = r.predict(X.loc[b, keep])
        out_tr = r.predict(X.loc[a, keep])
        out[np.where(np.isin(p.index, idx))[0][a]] = out_tr
    return out


def prev_xgb(p, tr, te, cols):
    import xgboost as xgb
    mdl = xgb.XGBRegressor(**XGB_PARAMS, random_state=0)
    mdl.fit(p.loc[tr, cols], p.loc[tr, "y"])
    out = np.full(len(p), np.nan)
    out[tr] = mdl.predict(p.loc[tr, cols])
    out[te] = mdl.predict(p.loc[te, cols])
    return out, mdl


def prev_prophet(p, tr, te, com_jogo):
    from prophet import Prophet
    df = pd.DataFrame({"ds": p["hora_ts"], "y": np.log1p(p["y"])})
    df["fds"] = p["dia_semana"].isin([0, 6]).to_numpy()
    df["util"] = ~df["fds"]
    regs = ["chuva_l", "temp", "feriado", "ferias"] + (JOGO_GLM if com_jogo else [])
    for c in regs:
        df[c] = p[c].to_numpy(float)
    mdl = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False,
                  seasonality_mode="additive")
    mdl.add_seasonality("diaria_util", period=1, fourier_order=8, condition_name="util")
    mdl.add_seasonality("diaria_fds", period=1, fourier_order=8, condition_name="fds")
    mdl.add_seasonality("mensal", period=30.5, fourier_order=3)
    for c in regs:
        mdl.add_regressor(c)
    mdl.fit(df.loc[tr])
    out = np.full(len(p), np.nan)
    for msk in (tr, te):
        out[msk] = np.expm1(mdl.predict(df.loc[msk])["yhat"].to_numpy()).clip(min=1e-6)
    return out


def baseline(p):
    b = p["mm_hd4"].to_numpy(float)
    return b


# ---------------------------------------------------------------------------
# metricas
# ---------------------------------------------------------------------------
def dev_poisson(y, mu):
    mu = np.clip(mu, 1e-9, None)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(y > 0, y * np.log(y / mu), 0.0)
    return 2 * (t - (y - mu))


def roda_escala(d, dom, escala, y, cont):
    p = painel(d, dom, escala, y, cont)
    p = p.reset_index(drop=True)
    preds = []
    pico_rows = []
    shap_obj = {}
    for k, (ini, fim) in enumerate(FOLDS):
        tr = ((p["hora_ts"] < ini) & p["avaliar"] & p["y"].notna()).to_numpy()
        te = ((p["hora_ts"] >= ini) & (p["hora_ts"] < fim) & p["avaliar"] & p["y"].notna()).to_numpy()
        if te.sum() == 0:
            continue
        res = {}
        bl = baseline(p)
        fallback = p.loc[tr].groupby(["estadio", "hd"])["y"].mean()
        fb = pd.Series(list(zip(p["estadio"], p["hd"]))).map(fallback).to_numpy()
        res[("baseline", "sem_jogo")] = np.where(np.isnan(bl), fb, bl)
        for cj, nome in ((True, "com_jogo"), (False, "sem_jogo")):
            res[("GLM", nome)] = prev_glm(p, tr, te, cj, escala)
            res[("XGBoost", nome)], mdl = prev_xgb(p, tr, te, colunas(escala, cj))
            if cj and k == len(FOLDS) - 1:
                shap_obj = {"modelo": mdl, "X": p.loc[tr, colunas(escala, True)], "p": p.loc[tr]}
            if escala == "cidade":
                res[("XGBoost clima lag24", nome)], _ = prev_xgb(p, tr, te, colunas(escala, cj, "lag24"))
                if MODELOS_PROPHET:
                    res[("Prophet", nome)] = prev_prophet(p, tr, te, cj)
        # esperado calendario+clima (pico) -- o proprio GLM sem jogo
        esp = res[("GLM", "sem_jogo")]
        yy = p["y"].to_numpy(float)
        if escala == "cidade":
            r_tr = (yy[tr] - esp[tr]) / np.sqrt(esp[tr])
            q90 = np.quantile(r_tr, .90)
            limiar = esp + q90 * np.sqrt(esp)                      # pico se y > limiar
            lab = yy > limiar
            corte = np.floor(limiar)                               # P(Y > limiar) = sf(floor(limiar))
        else:
            # hora de risco: P(Y >= obs | esp) < 0,10  <=>  obs >= c, c = menor k com sf(k-1, esp) < 0,10
            c = stats.poisson.ppf(0.90, esp) + 1
            lab = yy >= c
            corte = c - 1                                          # P(Y >= c) = sf(c-1)
        for (mod, var), mu in res.items():
            for msk, conj in ((te, "teste"),):
                preds.append(pd.DataFrame({"fold": k + 1, "modelo": mod, "variante": var,
                                           "hora_ts": p.loc[msk, "hora_ts"].to_numpy(),
                                           "estadio": p.loc[msk, "estadio"].to_numpy(),
                                           "semana_id": p.loc[msk, "semana_id"].to_numpy(),
                                           "y": yy[msk], "mu": mu[msk], "pico": lab[msk],
                                           "janela_cap": (p.loc[msk, ["C_pre", "C_durante", "C_pos"]].sum(axis=1) > 0).to_numpy(),
                                           "janela_fora": (p.loc[msk, ["F_pre", "F_durante", "F_pos"]].sum(axis=1) > 0).to_numpy()}))
            score_tr = stats.poisson.sf(corte[tr], np.clip(mu[tr], 1e-9, None))
            score_te = stats.poisson.sf(corte[te], np.clip(mu[te], 1e-9, None))
            prev_tr = lab[tr].mean()
            thr = np.quantile(score_tr, 1 - prev_tr) if prev_tr > 0 else 1
            pr = average_precision_score(lab[te], score_te) if lab[te].sum() > 0 else np.nan
            pred = score_te >= thr
            tp = (pred & lab[te]).sum()
            pico_rows.append({"fold": k + 1, "modelo": mod, "variante": var, "n_teste": int(te.sum()),
                              "prevalencia_teste": lab[te].mean(), "PR_AUC": pr,
                              "recall": tp / lab[te].sum() if lab[te].sum() else np.nan,
                              "precision": tp / pred.sum() if pred.sum() else np.nan})
        print(f"    fold {k+1:02d} ok", flush=True)
    return pd.concat(preds, ignore_index=True), pd.DataFrame(pico_rows), shap_obj


def ablacao(P):
    """diferenca (sem jogo - com jogo) na deviance e no MAE; > 0 = as variaveis de jogo ajudam.
    IC95 por bootstrap em blocos de semana."""
    P = P.copy()
    P["dev"] = dev_poisson(P["y"].to_numpy(), P["mu"].to_numpy())
    P["ae"] = np.abs(P["y"] - P["mu"])
    rows = []
    for mod in P["modelo"].unique():
        a = P[(P["modelo"] == mod)]
        if a["variante"].nunique() < 2:
            continue
        w = a.pivot_table(index=["hora_ts", "estadio"], columns="variante", values=["dev", "ae"])
        w.columns = [f"{x}_{v}" for x, v in w.columns]
        info = a[a["variante"] == "com_jogo"].set_index(["hora_ts", "estadio"])[["semana_id", "janela_cap", "janela_fora"]]
        w = w.join(info)
        for sub, msk in (("todas as horas", np.ones(len(w), bool)), ("horas PRÉ/DURANTE/PÓS na capital", w["janela_cap"].to_numpy()),
                         ("horas de jogo fora da capital", w["janela_fora"].to_numpy())):
            ww = w[msk]
            if len(ww) == 0:
                continue
            dd = (ww["dev_sem_jogo"] - ww["dev_com_jogo"]).to_numpy()
            da = (ww["ae_sem_jogo"] - ww["ae_com_jogo"]).to_numpy()
            sem = ww["semana_id"].to_numpy()
            us = np.unique(sem)
            idx = {u: np.where(sem == u)[0] for u in us}
            bd, ba = [], []
            for _ in range(1000):
                ii = np.concatenate([idx[u] for u in RNG.choice(us, len(us))])
                bd.append(dd[ii].mean())
                ba.append(da[ii].mean())
            rows.append({"modelo": mod, "subconjunto": sub, "n_horas": len(ww),
                         "dev_com_jogo": ww["dev_com_jogo"].mean(), "dev_sem_jogo": ww["dev_sem_jogo"].mean(),
                         "ganho_dev": dd.mean(), "ganho_dev_IC_lo": np.percentile(bd, 2.5),
                         "ganho_dev_IC_hi": np.percentile(bd, 97.5),
                         "ganho_dev_pct": 100 * dd.mean() / ww["dev_sem_jogo"].mean(),
                         "mae_com_jogo": ww["ae_com_jogo"].mean(), "mae_sem_jogo": ww["ae_sem_jogo"].mean(),
                         "ganho_mae": da.mean(), "ganho_mae_IC_lo": np.percentile(ba, 2.5),
                         "ganho_mae_IC_hi": np.percentile(ba, 97.5)})
    return pd.DataFrame(rows)


def metricas_gerais(P):
    P = P.copy()
    P["dev"] = dev_poisson(P["y"].to_numpy(), P["mu"].to_numpy())
    P["ae"] = np.abs(P["y"] - P["mu"])
    g = P.groupby(["modelo", "variante"]).agg(deviance_media=("dev", "mean"), MAE=("ae", "mean"),
                                              n=("y", "size")).reset_index()
    gj = P[P["janela_cap"]].groupby(["modelo", "variante"]).agg(deviance_janelas=("dev", "mean"),
                                                                MAE_janelas=("ae", "mean")).reset_index()
    return g.merge(gj, on=["modelo", "variante"], how="left").sort_values("deviance_media")


def resumo_pico(K):
    return K.groupby(["modelo", "variante"]).agg(PR_AUC_fold_macro=("PR_AUC", "mean"), recall_medio=("recall", "mean"),
                                                 precision_media=("precision", "mean"),
                                                 prevalencia_teste=("prevalencia_teste", "mean")).reset_index() \
        .sort_values("PR_AUC_fold_macro", ascending=False)


# ---------------------------------------------------------------------------
# SHAP (condicional) com auditoria de colinearidade
# ---------------------------------------------------------------------------
def shap_auditado(obj, out, rotulo):
    import shap
    X = obj["X"].sample(min(4000, len(obj["X"])), random_state=0)
    sv = shap.TreeExplainer(obj["modelo"]).shap_values(X)
    imp = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
    jogo = [c for c in X.columns if c in JOGO_CAP + JOGO_FORA or c.endswith("_outro")]
    p = obj["p"].loc[X.index]
    rows = []
    for c in jogo:
        v = X[c].fillna(-99)
        rh = stats.spearmanr(v, p["hora_do_dia"])[0] if v.nunique() > 1 else np.nan
        rows.append({"variavel": c, "shap_medio_abs": imp[c], "rank": int(list(imp.index).index(c)) + 1,
                     "rho_com_hora_do_dia": rh})
    t = pd.DataFrame(rows).sort_values("shap_medio_abs", ascending=False)
    t["participacao_pct"] = 100 * t["shap_medio_abs"] / imp.sum()
    t.to_csv(os.path.join(out, "tabelas", f"fase3_shap_{rotulo}.csv"), index=False)
    return t, imp


# ---------------------------------------------------------------------------
# produto pratico: risco esperado por estadio x janela para um jogo tipico
# ---------------------------------------------------------------------------
def tabela_risco(f, dom, out, cont):
    d = m.amostra(f, dom)
    X = m.base_X(d, (dom, "main"))
    slots = {"domingo 16h": (0, 16.0), "quarta 21h30": (3, 21.5)}
    rows = []
    for y in ALVOS[dom]["entorno"]:
        for s in m.ESTADIOS:
            est = d["jogo_estadio"].eq(s)
            T = pd.DataFrame(index=d.index)
            for w in m.WIN:
                T[f"C_{w}__este"] = ((d[f"C_{w}"] == 1) & est).astype(float)
                T[f"C_{w}__outro"] = ((d[f"C_{w}"] == 1) & ~est).astype(float)
            T[["C_fdj", "F_pre", "F_durante", "F_pos"]] = d[["C_fdj", "F_pre", "F_durante", "F_pos"]]
            yy = cont[(s, "disco", y)].reindex(d["hora_ts"])
            r = m.ajusta(yy.to_numpy(), X, T, d["semana_id"].to_numpy())
            cov = r.cov_params()
            base_hd = pd.Series(yy.to_numpy(), index=d.index)[d["hora_sem_jogo"]].groupby(
                [d["dia_semana"], d["hora_do_dia"]]).mean()
            for slot, (dow, hini) in slots.items():
                horas = {"pre": [hini - 2, hini - 1], "durante": [hini, hini + 1], "pos": [hini + 2, hini + 3]}
                for w, hs in horas.items():
                    b0 = 0.0
                    for hh in hs:
                        hr = int(np.floor(hh)) % 24
                        dw = dow if hh < 24 else (dow + 1) % 7
                        b0 += base_hd.get((dw, hr), np.nan)
                    c = f"C_{w}__este"
                    beta, se = r.params[c], np.sqrt(cov.loc[c, c])
                    sims = np.exp(RNG.normal(beta, se, 5000))
                    rows.append({"desfecho": y, "estadio": s, "jogo_tipico": slot, "janela": w,
                                 "esperado_sem_jogo_2h": b0, "IRR": np.exp(beta),
                                 "esperado_com_jogo_2h": b0 * np.exp(beta), "excesso_2h": b0 * (np.exp(beta) - 1),
                                 "excesso_IC95_lo": b0 * (np.percentile(sims, 2.5) - 1),
                                 "excesso_IC95_hi": b0 * (np.percentile(sims, 97.5) - 1), "p": r.pvalues[c]})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(out, "tabelas", "fase3_tabela_risco_estadio_janela.csv"), index=False)
    return t


# ---------------------------------------------------------------------------
# relatorio
# ---------------------------------------------------------------------------
def relatorio(dom, out, blocos, risco):
    L = []
    w = L.append
    nome = "CRIMES" if dom == "crimes" else "SINISTROS"
    w(f"# V2 / Fase 3 — {nome}: bloco preditivo\n")
    w("Gerado por `scripts/34_preditivo_janelas.py`. Previsão feita na véspera (até 23h59 do dia anterior); só "
      "variáveis conhecidas nesse momento (calendário, agenda de jogos, público **histórico** do mandante, clima "
      "como previsão perfeita e variante com clima defasado 24 h, histórico do desfecho com defasagem ≥ 24 h). "
      "Walk-forward 12 folds mensais de 2023, janela expansiva desde 2022-01, tudo reajustado só no treino. "
      "Hiperparâmetros fixos e rasos (Etapa 17). Prophet só na escala cidade (no entorno as contagens são "
      "esparsas e o Prophet, gaussiano em log1p, não é adequado). GLM de previsão = spec da Fase 2 com mês do "
      "ano + tendência no lugar de ano × mês (o mês de teste não existe no treino).\n")
    w("## Resposta direta: saber que haverá jogo melhora a previsão hora a hora?\n")
    for (escala, y), b in blocos.items():
        ab = b["ablacao"]
        partes = []
        for mod in ("XGBoost", "XGBoost clima lag24", "GLM", "Prophet"):
            for sub in ("todas as horas", "horas PRÉ/DURANTE/PÓS na capital"):
                r = ab[(ab["modelo"] == mod) & (ab["subconjunto"] == sub)]
                if len(r):
                    r = r.iloc[0]
                    sig = "**ajuda**" if r["ganho_dev_IC_lo"] > 0 else ("piora" if r["ganho_dev_IC_hi"] < 0 else "não muda")
                    sm_ = "ajuda" if r["ganho_mae_IC_lo"] > 0 else ("piora" if r["ganho_mae_IC_hi"] < 0 else "não muda")
                    partes.append(f"{mod} / {sub}: deviance {r['ganho_dev_pct']:+.1f}% → {sig}; MAE "
                                  f"{r['ganho_mae']:+.3f} → {sm_}")
        w(f"- **{escala} — `{y}`:** " + "; ".join(partes) + ".")
    w("\n(ganho = métrica sem as variáveis de jogo − com; > 0 = jogo ajuda; \"ajuda\"/\"piora\" só quando o IC95 "
      "por bootstrap em blocos de semana exclui 0 — IC completos nas tabelas de ablação. `XGBoost clima lag24` = "
      "variante conservadora com o clima da véspera no lugar da previsão perfeita.)\n")
    w("**Notas de leitura:**")
    w("- **Baseline com deviance muito alta no entorno:** a média das 4 semanas anteriores é 0 em muitas horas de "
      "contagem baixa; quando ocorre 1 registro, a deviance de Poisson explode (μ≈0). Compare o baseline pelo MAE, "
      "que é próximo dos outros modelos.")
    w("- **Deviance × MAE:** a deviance pesa mais os erros em horas de contagem alta/inesperada; o MAE pesa todos "
      "igualmente. Quando o jogo melhora a deviance mas não o MAE, o ganho está em capturar as horas de excesso "
      "(cauda), não em acertar melhor a hora típica.")
    w("- **Classificação de pico / hora de risco:** compare PR-AUC com a prevalência (linha `prevalencia_teste`): "
      "PR-AUC de um classificador aleatório = prevalência.\n")
    for (escala, y), b in blocos.items():
        w(f"## {escala.capitalize()} — `{y}`\n")
        w("### Desempenho (pooled nos 12 folds de teste)\n")
        w(m.md(b["gerais"], 4))
        w("\n### Ablação (com × sem variáveis de jogo)\n")
        w(m.md(b["ablacao"][["modelo", "subconjunto", "n_horas", "dev_sem_jogo", "dev_com_jogo", "ganho_dev",
                             "ganho_dev_IC_lo", "ganho_dev_IC_hi", "ganho_dev_pct", "mae_sem_jogo", "mae_com_jogo",
                             "ganho_mae", "ganho_mae_IC_lo", "ganho_mae_IC_hi"]], 4))
        w("\n### Classificação de " + ("pico (P90 do resíduo de Pearson, definição da Fase 2)" if escala == "cidade"
                                       else "hora de risco (P(Y ≥ obs | esperado calendário+clima) < 0,10)") + "\n")
        w(m.md(b["pico"], 3))
        if b.get("shap") is not None:
            w("\n### SHAP (ablação mostrou ganho) com auditoria de colinearidade\n")
            w("Variáveis de jogo no modelo XGBoost do último fold; `rho_com_hora_do_dia` mostra quanto a "
              "variável pode estar fazendo papel de hora do dia (Etapa 18).\n")
            w(m.md(b["shap"].head(15), 3))
        w("")
    w("## Produto prático: risco esperado por estádio × janela (jogo típico)\n")
    w("Entorno de 3 km; esperado sem jogo = média observada na mesma hora × dia da semana em horas sem nenhum "
      "jogo dos 4 times; com jogo = × IRR da janela daquele estádio (modelo do entorno da Fase 2); excesso = "
      "ocorrências a mais nas 2 horas da janela; IC por simulação do coeficiente.\n")
    w(m.md(risco[["desfecho", "estadio", "jogo_tipico", "janela", "esperado_sem_jogo_2h", "esperado_com_jogo_2h",
                  "excesso_2h", "excesso_IC95_lo", "excesso_IC95_hi", "IRR", "p"]], 2))
    with open(os.path.join(out, f"relatorio_fase3_preditivo_{dom}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    import time
    t0 = time.time()
    f, jogos, fora = m.carrega()
    d = base_horas(f, jogos, fora)
    resumo = ["# V2 / Fase 3 — resumo do bloco preditivo\n"]
    reusa = os.environ.get("REUSA") == "1"      # so refaz os relatorios a partir das tabelas fase3_* salvas
    for dom in os.environ.get("DOMS", "crimes,sinistros").split(","):
        out = m.dirs(dom)
        blocos = {}
        if reusa:
            T = lambda n: pd.read_csv(os.path.join(out, "tabelas", n))
            for escala in ("cidade", "entorno"):
                for y in ALVOS[dom][escala]:
                    b = {"ablacao": T(f"fase3_ablacao_{escala}_{y}.csv"), "gerais": T(f"fase3_desempenho_{escala}_{y}.csv"),
                         "pico": T(f"fase3_pico_{escala}_{y}.csv")}
                    sp = os.path.join(out, "tabelas", f"fase3_shap_{escala}_{y}.csv")
                    b["shap"] = pd.read_csv(sp) if os.path.exists(sp) else None
                    blocos[(escala, y)] = b
            relatorio(dom, out, blocos, T("fase3_tabela_risco_estadio_janela.csv"))
            txt = open(os.path.join(out, f"relatorio_fase3_preditivo_{dom}.md"), encoding="utf-8").read()
            resumo.append(f"## {dom.upper()}\n")
            resumo.append(txt[txt.index("## Resposta direta"):txt.index("\n## ", txt.index("## Resposta direta") + 5)])
            continue
        cont, _ = m.contagens_espaciais(dom)
        for escala in ("cidade", "entorno"):
            for y in ALVOS[dom][escala]:
                print(f"== {dom} / {escala} / {y}", round(time.time() - t0), flush=True)
                P, K, shap_obj = roda_escala(d, dom, escala, y, cont)
                P.to_csv(os.path.join(out, "tabelas", f"fase3_previsoes_{escala}_{y}.csv.gz"), index=False,
                         compression="gzip")
                ab = ablacao(P)
                b = {"ablacao": ab, "gerais": metricas_gerais(P), "pico": resumo_pico(K)}
                ab.to_csv(os.path.join(out, "tabelas", f"fase3_ablacao_{escala}_{y}.csv"), index=False)
                b["gerais"].to_csv(os.path.join(out, "tabelas", f"fase3_desempenho_{escala}_{y}.csv"), index=False)
                b["pico"].to_csv(os.path.join(out, "tabelas", f"fase3_pico_{escala}_{y}.csv"), index=False)
                xg = ab[(ab["modelo"] == "XGBoost") & (ab["subconjunto"] != "todas as horas")]
                if len(xg) and (xg["ganho_dev_IC_lo"] > 0).any() and shap_obj:
                    b["shap"], _ = shap_auditado(shap_obj, out, f"{escala}_{y}")
                blocos[(escala, y)] = b
        risco = tabela_risco(f, dom, out, cont)
        relatorio(dom, out, blocos, risco)
        txt = open(os.path.join(out, f"relatorio_fase3_preditivo_{dom}.md"), encoding="utf-8").read()
        resumo.append(f"## {dom.upper()}\n")
        resumo.append(txt[txt.index("## Resposta direta"):txt.index("\n## ", txt.index("## Resposta direta") + 5)])
    with open(os.path.join(REP, "resumo_fase3.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(resumo) + "\n")
    print("[ok]", round(time.time() - t0), "s")
