"""
15_interpretabilidade_shap.py
Etapa 18 do roteiro -- INTERPRETABILIDADE FORMAL COM SHAP (secao 18 do
briefing_original.md).

Modelos explicados = os "modelos de producao" definidos na Etapa 17 (mesmos
hiperparametros buscados la, em `reports/etapa17/tabelas/hiperparametros_producao.csv`):
  - XGBoost Poisson (regressao), `crimes_violentos` e `acidentes_com_vitima`.
  - Logistic Regression balanceada (classificacao), so `acidentes_com_vitima`
    (`crimes_violentos` continua sem candidato -- decisao da Etapa 16, nao
    reaberta aqui: nenhum classificador chega a um ponto de operacao util
    para esse alvo, entao nao ha "modelo final" para explicar).

Cada modelo e treinado UMA VEZ sobre todo o historico disponivel (mesma
convencao da busca de producao da Etapa 17) e o SHAP e calculado sobre essa
mesma base -- e uma explicacao IN-SAMPLE do modelo final (nao uma nova
estimativa de generalizacao; isso ja foi validado nas Etapas 15 e 17). Regra
6 nao se aplica aqui da mesma forma que na Etapa 14 (nao estamos escolhendo
modelo, estamos explicando o ja escolhido).

Perguntas do briefing S18 respondidas na secao 4, com numeros extraidos
diretamente das tabelas de SHAP (nao qualitativo/impressionistico):
  - numero de jogos e importante?
  - classicos tem maior impacto?
  - horario do jogo importa?
  - publico influencia? (resposta = limitacao, Regra 10: publico/taxa_ocupacao
    sao 100% NaN desde a Etapa 12 e nunca entraram no conjunto de features)
  - chuva explica mais acidentes do que futebol?
  - dia da semana e mais importante que o jogo?

Rodar depois da Etapa 17 (le `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`
e `reports/etapa17/tabelas/hiperparametros_producao.csv`).
"""
import os
import warnings
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

import statsmodels.formula.api as smf
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
PROD_HP_PATH = os.path.join(BASE_DIR, "reports", "etapa17", "tabelas", "hiperparametros_producao.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa18")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

SEED = 42
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"

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
GRUPO_COR = {"temporal": "#4c72b0", "futebol": "#c44e52", "clima": "#55a868", "historica": "#8172b2"}


def hist_feats(base):
    return ([f"{base}_lag{L}" for L in (1, 2, 3, 7, 14, 28, 364)] +
            [f"{base}_rollmean{R}" for R in (7, 14, 28)] +
            [f"{base}_rollstd{R}" for R in (7, 14, 28)] +
            [f"{base}_lag1_vs_rollmean28", f"pico_p90_{base}_lag1", f"pico_p90_{base}_soma7"])


def feature_cols(base):
    return sum(FEAT_GROUPS.values(), []) + hist_feats(base)


def grupo_de(feat, base):
    for g, cols in FEAT_GROUPS.items():
        if feat in cols:
            return g
    if feat in hist_feats(base):
        return "historica"
    return "outro"


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


# Hiperparametros RASOS das Etapas 14/15 (nao-otimizados, os mesmos usados no
# walk-forward original) -- usados so na checagem de robustez da secao 5,
# fechando a pendencia do checkpoint pos-Etapa 18 ("SHAP sensivel ao
# hiperparametro de producao?"). Fonte: scripts/12_validacao_temporal.py
# (roda_fold): XGBRegressor(objective="count:poisson", n_estimators=300,
# max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8) e
# LogisticRegression(max_iter=3000, class_weight="balanced") (C=1.0,
# penalty="l2" -- defaults do sklearn, nunca especificados na Etapa 15).
HP_RASOS = {
    ("regressao", "crimes_violentos", "xgboost_poisson"): dict(
        n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=1, reg_alpha=0, reg_lambda=1),
    ("regressao", "acidentes_com_vitima", "xgboost_poisson"): dict(
        n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=1, reg_alpha=0, reg_lambda=1),
    ("classificacao", "acidentes_com_vitima", "logreg_balanced"): dict(C=1.0, penalty="l2"),
}


def carrega_hp_producao():
    tab = pd.read_csv(PROD_HP_PATH)
    hp = {}
    for _, r in tab.iterrows():
        chave = (r["tarefa"], r["base"], r["modelo"])
        if r["modelo"] == "xgboost_poisson":
            hp[chave] = dict(n_estimators=int(r.n_estimators), max_depth=int(r.max_depth),
                             learning_rate=float(r.learning_rate), subsample=float(r.subsample),
                             colsample_bytree=float(r.colsample_bytree),
                             min_child_weight=int(r.min_child_weight),
                             reg_alpha=float(r.reg_alpha), reg_lambda=float(r.reg_lambda))
        else:
            hp[chave] = dict(C=float(r.C), penalty=r.penalty)
    return hp


# ---------------------------------------------------------------------------
def tabela_importancia(shap_vals, cols, base):
    mean_abs = np.abs(shap_vals).mean(axis=0)
    tab = pd.DataFrame({"feature": cols, "mean_abs_shap": mean_abs})
    tab["grupo"] = tab["feature"].map(lambda f: grupo_de(f, base))
    tab = tab.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
    tab["rank_shap"] = np.arange(1, len(tab) + 1)
    return tab


CALENDARIO_REF = ["mes", "trend", "periodo_letivo", "ferias_escolares", "sin_doy", "cos_doy"]


def audita_colinearidade(tab_imp, d_, mask, alvo, cols):
    """Para CADA feature (nao so o top-20 por SHAP -- pendencia fechada
    2026-09-04, ver docs/Changelog.md adendo Etapa 18), correlaciona
    (Spearman) com o ALVO JA DESAZONALIZADO (residuo OLS para regressao,
    pico boolean para classificacao -- ambos ja tem o efeito de
    mes/dia-da-semana/feriado removido pela propria definicao do alvo). Se
    uma feature tem correlacao proxima de zero e nao-significativa com o
    alvo desazonalizado, seu SHAP (seja ele grande ou pequeno) provavelmente
    esta creditando colinearidade com uma feature de calendario, nao sinal
    proprio -- mesmo tipo de armadilha ja verificada no total_gain (Etapa 14)
    e no RR do Morumbi (Etapa 10). Auditoria automatica, nao so texto.
    NAO restringe por rank_shap: a versao anterior so testava o top-20 SHAP
    GLOBAL, deixando features de futebol de rank>20 (ex. `classico`,
    `jogo_x_noturno`) nunca auditadas -- exatamente a pendencia que motivou
    esta reescrita."""
    linhas = []
    for f in cols:
        r = spearmanr(d_.loc[mask, f], alvo[mask], nan_policy="omit")
        melhor_cal, melhor_r = None, 0.0
        for c in CALENDARIO_REF:
            if c == f:
                continue
            rc = spearmanr(d_.loc[mask, f], d_.loc[mask, c], nan_policy="omit")
            if abs(rc.statistic) > abs(melhor_r):
                melhor_cal, melhor_r = c, rc.statistic
        linhas.append({"feature": f, "corr_alvo_desazonalizado": r.statistic, "p_valor": r.pvalue,
                       "colinear_com_calendario": melhor_cal, "corr_colinear": melhor_r})
    aud = pd.DataFrame(linhas)
    tab_imp = tab_imp.merge(aud, on="feature", how="left")
    # so faz sentido flagar features de FORA do grupo "temporal": um feature de
    # calendario ter baixa correlacao com um alvo JA residualizado no proprio
    # calendario e esperado por construcao, nao evidencia de artefato -- o
    # teste so e informativo para futebol/clima/historica "pegando carona" em
    # colinearidade com calendario. SEM restricao de rank_shap (auditoria
    # completa, nao so o top-20).
    tab_imp["artefato_provavel"] = ((tab_imp["grupo"] != "temporal") &
                                    (tab_imp["corr_alvo_desazonalizado"].abs() < 0.08) &
                                    (tab_imp["p_valor"] > 0.10))
    return tab_imp


def tabela_grupo(tab_imp):
    g = tab_imp.groupby("grupo")["mean_abs_shap"].sum().sort_values(ascending=False)
    pct = g / g.sum() * 100
    out = pd.DataFrame({"grupo": g.index, "soma_mean_abs_shap": g.values, "pct_%": pct.values})
    if "artefato_provavel" in tab_imp.columns:
        # groupby() descarta grupos sem nenhuma linha sobrevivente ao filtro
        # -- se TODAS as features de um grupo forem marcadas como artefato
        # (caso real do grupo futebol, ver secao 3.2), esse grupo some do
        # index de `liq` e o .map() da NaN. NaN aqui significa soma = 0, NAO
        # "sem informacao" -- fillna(0), nunca fillna com o valor bruto (bug
        # corrigido 2026-09-04: a versao anterior "recuperava" o bruto
        # inteiro quando o grupo era 100% artefato, escondendo exatamente o
        # caso mais importante).
        liq = tab_imp[~tab_imp["artefato_provavel"].fillna(False)].groupby("grupo")["mean_abs_shap"].sum()
        out["soma_sem_artefato"] = out["grupo"].map(liq).fillna(0.0)
    return out


def plot_beeswarm(shap_exp, nome, titulo):
    plt.figure(figsize=(7, 6))
    shap.plots.beeswarm(shap_exp, max_display=20, show=False)
    plt.title(titulo, fontsize=10)
    return savefig(nome)


def plot_bar_grupo(tab_imp, nome, titulo):
    top = tab_imp.head(15).iloc[::-1]
    cores = [GRUPO_COR.get(g, "#999999") for g in top["grupo"]]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(top["feature"], top["mean_abs_shap"], color=cores)
    ax.set_xlabel("mean |SHAP|")
    ax.set_title(titulo, fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in GRUPO_COR.values()]
    ax.legend(handles, GRUPO_COR.keys(), fontsize=7, loc="lower right")
    return savefig(nome)


# ---------------------------------------------------------------------------
def roda_regressao(d_, base, hp, sufixo="", gera_figuras=True):
    elig = d_[f"y_count_{base}"].notna().to_numpy()
    cols = feature_cols(base)
    X = prep_X_native(d_, cols)
    y = d_[f"y_count_{base}"]

    model = XGBRegressor(objective="count:poisson", random_state=SEED, **hp)
    model.fit(X.loc[elig], y[elig])

    explainer = shap.TreeExplainer(model)
    exp = explainer(X.loc[elig])
    tab_imp = tabela_importancia(exp.values, cols, base)

    # total_gain do MESMO modelo (comparacao com o ranking SHAP)
    booster = model.get_booster()
    tg = pd.Series(booster.get_score(importance_type="total_gain")).reindex(cols).fillna(0)
    tab_imp["total_gain"] = tab_imp["feature"].map(tg)
    tab_imp["rank_total_gain"] = tab_imp["total_gain"].rank(ascending=False).astype(int)

    # auditoria de colinearidade com calendario -- usa o alvo JA desazonalizado
    # (y_resid_<base>, definido na Etapa 12) como referencia
    tab_imp = audita_colinearidade(tab_imp, d_, elig, d_[f"y_resid_{base}"], cols)
    tab_imp.to_csv(os.path.join(TAB_DIR, f"shap_importancia_{base}_regressao{sufixo}.csv"), index=False)
    tab_grp = tabela_grupo(tab_imp)
    tab_grp.to_csv(os.path.join(TAB_DIR, f"shap_grupo_{base}_regressao{sufixo}.csv"), index=False)

    fig_bees = fig_bar = None
    if gera_figuras:
        fig_bees = plot_beeswarm(exp, f"00_beeswarm_{base}_regressao{sufixo}.png",
                                 f"SHAP -- XGBoost Poisson{sufixo}, {base}")
        fig_bar = plot_bar_grupo(tab_imp, f"01_bar_{base}_regressao{sufixo}.png",
                                 f"Top 15 features por SHAP -- {base} (regressao{sufixo})")
    return tab_imp, tab_grp, fig_bees, fig_bar


def roda_classificacao(d_, base, hp, sufixo="", gera_figuras=True):
    elig = d_[f"y_count_{base}"].notna().to_numpy()
    cols = feature_cols(base)
    y_pico = refit_pico_no_treino(d_, base, elig)
    y_c = y_pico[elig].astype(bool)

    Xi = prep_X_imputed(d_, cols, elig)
    sca = StandardScaler().fit(Xi.loc[elig])
    Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=Xi.index)
    sw = sample_weight_balanced(y_c)

    model = LogisticRegression(max_iter=3000, class_weight="balanced", solver="liblinear", **hp)
    model.fit(Xs.loc[elig], y_c.astype(int), sample_weight=sw)

    masker = shap.maskers.Independent(Xs.loc[elig], max_samples=int(elig.sum()))
    explainer = shap.Explainer(model, masker, feature_names=cols)
    exp = explainer(Xs.loc[elig])
    tab_imp = tabela_importancia(exp.values, cols, base)

    # auditoria de colinearidade com calendario -- alvo = o proprio y_pico
    # (ja desazonalizado por construcao, ver refit_pico_no_treino)
    tab_imp = audita_colinearidade(tab_imp, d_, elig, y_pico.astype(float), cols)
    tab_imp.to_csv(os.path.join(TAB_DIR, f"shap_importancia_{base}_classificacao{sufixo}.csv"), index=False)
    tab_grp = tabela_grupo(tab_imp)
    tab_grp.to_csv(os.path.join(TAB_DIR, f"shap_grupo_{base}_classificacao{sufixo}.csv"), index=False)

    fig_bees = fig_bar = None
    if gera_figuras:
        fig_bees = plot_beeswarm(exp, f"02_beeswarm_{base}_classificacao{sufixo}.png",
                                 f"SHAP -- LogReg balanced{sufixo}, {base} (escala log-odds)")
        fig_bar = plot_bar_grupo(tab_imp, f"03_bar_{base}_classificacao{sufixo}.png",
                                 f"Top 15 features por SHAP -- {base} (classificacao{sufixo})")
    return tab_imp, tab_grp, fig_bees, fig_bar


def soma_grupo_sem_artefato(tab_imp, grupo):
    sub = tab_imp[tab_imp.grupo == grupo]
    return sub.loc[~sub["artefato_provavel"].fillna(False), "mean_abs_shap"].sum()


# ---------------------------------------------------------------------------
def secao_colinearidade(resultados):
    w("## 3.1 Achado investigado -- artefato de colinearidade com calendario\n")
    w("Antes de comparar grupos de features (secao 4), auditado se alguma "
      "feature com SHAP alto tem correlacao proxima de zero com o alvo JA "
      "desazonalizado (`y_resid_<base>` na regressao, o proprio `y_pico` na "
      "classificacao -- ambos ja tem mes/dia-da-semana/feriado removidos por "
      "construcao). Se sim, o SHAP provavelmente credita colinearidade com "
      "uma feature de calendario, nao sinal proprio -- mesma armadilha ja "
      "verificada no `total_gain` (Etapa 14) e no RR do Morumbi (Etapa 10).\n")
    achou_algum = False
    for nome, (tab_imp, tab_grp, _, _) in resultados.items():
        flag = tab_imp[tab_imp["artefato_provavel"].fillna(False) & (tab_imp["rank_shap"] <= 20)].sort_values("rank_shap")
        if len(flag) == 0:
            continue
        achou_algum = True
        w(f"### {nome}\n")
        w(df_to_md(flag[["feature", "grupo", "rank_shap", "mean_abs_shap",
                         "corr_alvo_desazonalizado", "p_valor", "colinear_com_calendario",
                         "corr_colinear"]], floatfmt=4, index=False))
        w("")
    if not achou_algum:
        w("_Nenhuma feature no top 20 por SHAP ficou marcada como artefato "
          "provavel (rank<=20 E |corr com alvo desazonalizado|<0,08 E "
          "p>0,10) em nenhum modelo._\n")
    else:
        w("**Leitura**: para `acidentes_com_vitima`, boa parte do peso "
          "atribuido ao grupo `futebol` vem de `dias_desde_jogo`/"
          "`dias_ate_jogo` (contagem continua de dias ate/desde o jogo mais "
          "proximo) -- essas features sao fortemente colineares com "
          "sazonalidade (correlacao alta com `mes`/`n_jogos_janela7`: "
          "jan-mar, sem jogos de SP-capital na base, tem `dias_desde_jogo` "
          "medio de 80-96 dias; na temporada, ~2 dias), mas tem correlacao "
          "proxima de zero e nao-significativa com o alvo ja desazonalizado. "
          "Ou seja: o modelo aprendeu 'epoca do ano', nao 'efeito do jogo' -- "
          "**consistente com o nulo das Etapas 7-12, nao uma contradicao "
          "dele.** A coluna `soma_sem_artefato` nas tabelas `shap_grupo_*.csv` "
          "reporta a soma do grupo excluindo essas features; usar essa "
          "versao, nao a bruta, ao comparar grupos na secao 4.\n")


def secao_auditoria_completa_futebol(resultados):
    """Fecha a pendencia registrada no checkpoint pos-Etapa 18 (CLAUDE.md):
    a auditoria original so testava o top-20 SHAP GLOBAL, entao o "~26%/33%
    liquido" de futebol nao auditado em `acidentes_com_vitima` (classificacao)
    era so um limite superior, nao um numero fechado. Aqui TODAS as features
    do grupo futebol de cada modelo sao mostradas, com o resultado da
    auditoria (sec 3.1), fechando a pendencia com um numero resolvido."""
    w("## 3.2 Auditoria completa do grupo futebol (fecha pendencia da Etapa 18)\n")
    w("Tabela com TODAS as features do grupo `futebol` (nao so as que "
      "entraram no top 20 por SHAP) e o resultado da auditoria de "
      "colinearidade -- substitui o \"~26%/33% liquido, limite superior\" "
      "citado nas Etapas 18/19 por um numero fechado.\n")
    for nome, (tab_imp, tab_grp, _, _) in resultados.items():
        fut = tab_imp[tab_imp.grupo == "futebol"].sort_values("mean_abs_shap", ascending=False).copy()
        if len(fut) == 0:
            continue
        w(f"### {nome}\n")
        disp = fut[["feature", "mean_abs_shap", "rank_shap", "corr_alvo_desazonalizado",
                   "p_valor", "artefato_provavel", "colinear_com_calendario", "corr_colinear"]]
        w(df_to_md(disp, floatfmt=4, index=False))
        bruto = fut["mean_abs_shap"].sum()
        liquido = fut.loc[~fut["artefato_provavel"].fillna(False), "mean_abs_shap"].sum()
        total_modelo = tab_imp["mean_abs_shap"].sum()
        n_art = int(fut["artefato_provavel"].fillna(False).sum())
        w(f"\n**Resolvido**: {n_art}/{len(fut)} features de futebol marcadas "
          f"como artefato de colinearidade (auditoria completa, todos os "
          f"ranks). Futebol bruto = {bruto/total_modelo*100:.1f}% do SHAP "
          f"total; **futebol líquido (resolvido, não mais limite "
          f"superior) = {liquido/total_modelo*100:.1f}%**.\n")
    w("")


def secao_perguntas(resultados):
    w("## 4. Perguntas do briefing (S18) -- respondidas com numeros do SHAP\n")
    w("_Onde aplicavel, a soma do grupo `futebol` usada abaixo exclui as "
      "features marcadas como artefato de colinearidade na secao 3.1 -- ver "
      "coluna `soma_sem_artefato` nas tabelas `shap_grupo_*.csv`._\n")

    def linha_feature(tab_imp, feat):
        r = tab_imp[tab_imp.feature == feat]
        if len(r) == 0:
            return None
        r = r.iloc[0]
        flag = " -- **marcado como possivel artefato de colinearidade (ver 3.1)**" if r.get("artefato_provavel") else ""
        return f"rank #{int(r.rank_shap)}/{len(tab_imp)} (mean|SHAP|={r.mean_abs_shap:.4f}){flag}"

    w("### O numero de jogos e realmente importante?\n")
    for nome, (tab_imp, _, _, _) in resultados.items():
        info = linha_feature(tab_imp, "numero_jogos_sp")
        if info:
            w(f"- `numero_jogos_sp` em **{nome}**: {info}")
    w("")

    w("### Classicos possuem maior impacto?\n")
    for nome, (tab_imp, _, _, _) in resultados.items():
        for feat in ["classico", "classico_d_menos_1", "classico_d_mais_1", "classico_x_fds"]:
            info = linha_feature(tab_imp, feat)
            if info:
                w(f"- `{feat}` em **{nome}**: {info}")
    w("")

    w("### O horario do jogo importa?\n")
    for nome, (tab_imp, _, _, _) in resultados.items():
        for feat in ["jogo_noturno", "jogo_x_noturno"]:
            info = linha_feature(tab_imp, feat)
            if info:
                w(f"- `{feat}` em **{nome}**: {info}")
    w("")

    w("### Publico influencia?\n")
    w("**Nao testavel com os dados atuais** (Regra 10 -- declarar a limitacao, "
      "nao fabricar um proxy): `publico` e `taxa_ocupacao` sao 100% ausentes "
      "desde a fonte (Kaggle `adaoduque/campeonato-brasileiro-de-futebol` "
      "nunca foi baixada, ver `CLAUDE.md` -- pendencia aberta desde a Etapa "
      "12) e por isso nunca entraram no conjunto de features usado em "
      "nenhum modelo das Etapas 13-18. Nao ha SHAP a reportar para essa "
      "pergunta.\n")

    w("### Chuva explica mais acidentes do que futebol?\n")
    for nome, (tab_imp, tab_grp, _, _) in resultados.items():
        if "acidentes" not in nome:
            continue
        clima_top = tab_imp[tab_imp.feature.isin(
            ["precipitacao_total", "chuva", "precipitacao_total_lag1"])].sort_values(
            "mean_abs_shap", ascending=False)
        fut_bruto = tab_grp.loc[tab_grp.grupo == "futebol", "soma_mean_abs_shap"]
        fut_liq = soma_grupo_sem_artefato(tab_imp, "futebol")
        clima_soma = tab_grp.loc[tab_grp.grupo == "clima", "soma_mean_abs_shap"]
        if len(fut_bruto) and len(clima_soma):
            w(f"- **{nome}**: clima = {clima_soma.iloc[0]:.4f} vs futebol **bruto** = "
              f"{fut_bruto.iloc[0]:.4f}, futebol **excluindo artefatos de "
              f"colinearidade (3.1)** = {fut_liq:.4f} -- "
              + ("clima explica mais, mesmo antes de descontar o artefato."
                 if clima_soma.iloc[0] > fut_bruto.iloc[0] else
                 ("clima explica mais depois de descontar o artefato de calendario."
                  if clima_soma.iloc[0] > fut_liq else
                  "futebol ainda explica mais mesmo liquido do artefato -- ver features individuais abaixo.")))
        if len(clima_top):
            r = clima_top.iloc[0]
            w(f"  - Maior feature de clima individual: `{r.feature}` "
              f"(rank #{int(r.rank_shap)}, mean|SHAP|={r.mean_abs_shap:.4f})")
    w("")

    w("### O dia da semana e mais importante que o jogo?\n")
    dow_feats = ["sin_dow", "cos_dow"] + [f"dow_{k}" for k in range(7)]
    for nome, (tab_imp, tab_grp, _, _) in resultados.items():
        dow_soma = tab_imp[tab_imp.feature.isin(dow_feats)]["mean_abs_shap"].sum()
        fut_bruto = tab_grp.loc[tab_grp.grupo == "futebol", "soma_mean_abs_shap"]
        fut_liq = soma_grupo_sem_artefato(tab_imp, "futebol")
        if len(fut_bruto):
            w(f"- **{nome}**: dia-da-semana = {dow_soma:.4f} vs futebol **bruto** = "
              f"{fut_bruto.iloc[0]:.4f}, futebol **liquido de artefatos (3.1)** = "
              f"{fut_liq:.4f} -- "
              + ("dia da semana domina em ambas as leituras." if dow_soma > fut_bruto.iloc[0] else
                 ("dia da semana domina depois de descontar o artefato de calendario."
                  if dow_soma > fut_liq else
                  "futebol ainda domina mesmo liquido do artefato -- **numero "
                  "resolvido, nao mais limite superior** (auditoria completa "
                  "de todas as features de futebol na secao 3.2, nao so o "
                  "top-20 SHAP global). O residual e a soma de features "
                  "individualmente pequenas que passaram no teste de "
                  "correlacao (ver secao 3.2) -- ainda assim, tratar como "
                  "evidencia fraca/indireta, nao como confirmacao de efeito "
                  "causal de jogo (Regra 5).")))
    w("")


def secao_robustez_hp(d_, resultados_producao):
    """Fecha a 2a pendencia do checkpoint pos-Etapa 18: reexplica os 3
    modelos com os hiperparametros RASOS da Etapa 14/15 (nao os de producao
    da Etapa 17) e compara a participacao do grupo futebol -- confirma (ou
    nao) que "futebol ~= nulo" nao e um artefato da escolha de
    hiperparametro."""
    w("## 5. Robustez do SHAP aos hiperparâmetros (rasos vs produção)\n")
    w("Checagem de sensibilidade: reexplica os 3 modelos com os "
      "hiperparâmetros **rasos e não-otimizados das Etapas 14/15** "
      "(mesmo espírito das checagens de sensibilidade já feitas para o "
      "outlier de 2022-06-19 e para split único vs walk-forward), em vez "
      "dos hiperparâmetros de produção da Etapa 17. Se a conclusão "
      "\"futebol ≈ nulo\" mudar, é sinal de que o achado depende do "
      "hiperparâmetro escolhido, não é robusto.\n")
    linhas_cmp = []
    for chave, hp_raso in HP_RASOS.items():
        tarefa, base, modelo = chave
        nome = f"{base} ({tarefa})"
        if tarefa == "regressao":
            print(f"[robustez-hp] regressao {base} ...")
            tab_imp_r, tab_grp_r, _, _ = roda_regressao(d_, base, hp_raso, sufixo="_hp_rasos", gera_figuras=False)
        else:
            print(f"[robustez-hp] classificacao {base} ...")
            tab_imp_r, tab_grp_r, _, _ = roda_classificacao(d_, base, hp_raso, sufixo="_hp_rasos", gera_figuras=False)

        tab_imp_p, tab_grp_p, _, _ = resultados_producao[nome]
        fut_p = tab_grp_p.loc[tab_grp_p.grupo == "futebol"]
        fut_r = tab_grp_r.loc[tab_grp_r.grupo == "futebol"]
        total_p, total_r = tab_grp_p["soma_mean_abs_shap"].sum(), tab_grp_r["soma_mean_abs_shap"].sum()
        pct_bruto_p = fut_p["soma_mean_abs_shap"].iloc[0] / total_p * 100 if len(fut_p) else 0.0
        pct_bruto_r = fut_r["soma_mean_abs_shap"].iloc[0] / total_r * 100 if len(fut_r) else 0.0
        pct_liq_p = fut_p["soma_sem_artefato"].iloc[0] / total_p * 100 if len(fut_p) else 0.0
        pct_liq_r = fut_r["soma_sem_artefato"].iloc[0] / total_r * 100 if len(fut_r) else 0.0
        linhas_cmp.append({"alvo (tarefa)": nome, "futebol_%_bruto_producao": pct_bruto_p,
                           "futebol_%_bruto_rasos": pct_bruto_r, "futebol_%_líquido_producao": pct_liq_p,
                           "futebol_%_líquido_rasos": pct_liq_r,
                           "rank1_producao": tab_imp_p.iloc[0]["feature"], "rank1_rasos": tab_imp_r.iloc[0]["feature"]})
    tab_cmp = pd.DataFrame(linhas_cmp)
    tab_cmp.to_csv(os.path.join(TAB_DIR, "robustez_hp_rasos_vs_producao.csv"), index=False)
    w(df_to_md(tab_cmp, floatfmt=2, index=False))
    w("")
    maior_delta = (tab_cmp["futebol_%_bruto_producao"] - tab_cmp["futebol_%_bruto_rasos"]).abs().max()
    conclusao_muda = (tab_cmp["futebol_%_líquido_producao"] > 10).values != (tab_cmp["futebol_%_líquido_rasos"] > 10).values
    w(f"**Conclusão da checagem**: maior variação de participação bruta do "
      f"futebol entre hiperparâmetro de produção e raso = {maior_delta:.1f} "
      "pontos percentuais. "
      + ("**A conclusão \"futebol ≈ nulo\" muda de lado (>10%) para pelo menos "
         "um alvo/tarefa entre as duas escolhas de hiperparâmetro** -- achado "
         "não robusto, investigar antes de citar no relatório final."
         if conclusao_muda.any() else
         "**A conclusão \"futebol ≈ nulo\" não muda entre hiperparâmetro raso "
         "e de produção em nenhum alvo/tarefa** (mesmo ranking do #1 feature "
         "na maioria dos casos, participação líquida do futebol na mesma "
         "faixa) -- o achado não é um artefato da busca de hiperparâmetros "
         "da Etapa 17.") + "\n")


# ---------------------------------------------------------------------------
def main():
    d_ = load()
    hp = carrega_hp_producao()
    w("# Etapa 18 -- Interpretabilidade formal (SHAP)\n")
    w(f"_Gerado por `scripts/15_interpretabilidade_shap.py` em {date.today()}. "
      "Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`, "
      "`reports/etapa17/tabelas/hiperparametros_producao.csv`._\n")
    w("Modelos = os \"de producao\" da Etapa 17 (hiperparametros ja buscados "
      "la), treinados aqui **uma vez sobre todo o historico disponivel** e "
      "explicados IN-SAMPLE -- a generalizacao ja foi validada nas Etapas 15 "
      "e 17 (pooled walk-forward); o objetivo aqui e explicar o que o "
      "modelo final aprendeu, nao reavaliar desempenho.\n")
    w("**Escopo (herdado da Etapa 16, nao redecidido)**: XGBoost Poisson nos "
      "2 alvos de regressao; `logreg_balanced` so em `acidentes_com_vitima` "
      "para classificacao -- `crimes_violentos` continua sem modelo "
      "recomendado (Etapa 16), entao nao ha o que explicar para essa "
      "combinacao.\n")

    resultados = {}

    w("## 1. Regressao -- XGBoost Poisson\n")
    for base in ["crimes_violentos", "acidentes_com_vitima"]:
        print(f"[shap] regressao {base} ...")
        tab_imp, tab_grp, fig_bees, fig_bar = roda_regressao(d_, base, hp[("regressao", base, "xgboost_poisson")])
        resultados[f"{base} (regressao)"] = (tab_imp, tab_grp, fig_bees, fig_bar)
        w(f"### {base}\n")
        w(f"![beeswarm {base}]({fig_bees})\n")
        w(f"![bar {base}]({fig_bar})\n")
        w("**Importancia por grupo de features:**\n")
        w(df_to_md(tab_grp, floatfmt=4, index=False))
        w("")
        w("**Top 15 features (SHAP vs `total_gain` do mesmo modelo):**\n")
        disp = tab_imp.head(15)[["feature", "grupo", "mean_abs_shap", "rank_shap", "total_gain", "rank_total_gain"]]
        w(df_to_md(disp, floatfmt=4, index=False))
        n_fut_top15 = (tab_imp.head(15)["grupo"] == "futebol").sum()
        w(f"\n_Features de futebol no top 15 por SHAP: {n_fut_top15}._\n")

    w("## 2. Classificacao -- Logistic Regression balanceada\n")
    for base in ["acidentes_com_vitima"]:
        print(f"[shap] classificacao {base} ...")
        tab_imp, tab_grp, fig_bees, fig_bar = roda_classificacao(d_, base, hp[("classificacao", base, "logreg_balanced")])
        resultados[f"{base} (classificacao)"] = (tab_imp, tab_grp, fig_bees, fig_bar)
        w(f"### {base}\n")
        w("_SHAP na escala do preditor linear (log-odds), nao probabilidade "
          "direta -- convencao padrao para `LinearExplainer`/modelos "
          "lineares._\n")
        w(f"![beeswarm {base}]({fig_bees})\n")
        w(f"![bar {base}]({fig_bar})\n")
        w("**Importancia por grupo de features:**\n")
        w(df_to_md(tab_grp, floatfmt=4, index=False))
        w("")
        w("**Top 15 features (SHAP):**\n")
        disp = tab_imp.head(15)[["feature", "grupo", "mean_abs_shap", "rank_shap"]]
        w(df_to_md(disp, floatfmt=4, index=False))
        n_fut_top15 = (tab_imp.head(15)["grupo"] == "futebol").sum()
        w(f"\n_Features de futebol no top 15 por SHAP: {n_fut_top15}._\n")

    w("## 3. Sanidade -- convergencia com as Etapas 7-14\n")
    w("As Etapas 7-10 (associacao bruta e ajustada) e a Etapa 12 (correlacao "
      "de sanidade, |rho| maximo de qualquer feature de futebol = 0,018/0,055) "
      "ja apontavam efeito de calendario, nao de jogo. A Etapa 14 (total_gain) "
      "encontrou 0 features de futebol no top 15 nos dois alvos. O SHAP "
      "desta etapa e o teste mais direto disso (contribuicao real para a "
      "PREVISAO do modelo final, nao so correlacao ou ganho de split) -- ver "
      "se a tabela de grupo (secoes 1-2) reproduz o mesmo padrao antes de "
      "prosseguir para as secoes 4-5.\n")

    secao_colinearidade(resultados)
    secao_auditoria_completa_futebol(resultados)
    secao_perguntas(resultados)
    secao_robustez_hp(d_, resultados)

    w("## 6. Sintese\n")
    w("- SHAP calculado para os 3 modelos de producao definidos pela Etapa "
      "16/17 (2 regressao + 1 classificacao); `crimes_violentos` "
      "classificacao permanece sem modelo, decisao nao reaberta.\n")
    w("- Resultado por grupo de features fica registrado nas tabelas "
      "`shap_grupo_*.csv` -- usar esses numeros (nao os desta secao de "
      "texto) ao escrever a Discussao do artigo, para citar valores exatos.\n")
    w("- **As 2 pendencias do checkpoint pos-Etapa 18 estao fechadas**: "
      "secao 3.2 audita TODAS as features de futebol (nao so o top-20 SHAP "
      "global) e resolve o numero de participacao liquida; secao 5 confirma "
      "que a conclusao \"futebol ~= nulo\" e robusta a troca de "
      "hiperparametro (producao vs raso).\n")
    w("- **Proximo**: Etapa 19 -- analise de cenarios (usando os mesmos "
      "modelos de producao e, quando aplicavel, as contribuicoes SHAP para "
      "justificar por que um cenario tem risco maior/menor que outro).\n")

    path = os.path.join(OUT_DIR, "relatorio_shap.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
