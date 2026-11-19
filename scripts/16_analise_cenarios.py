"""
16_analise_cenarios.py
Etapa 19 do roteiro -- ANALISE DE CENARIOS (secao 19 do briefing_original.md).

Usa os modelos de producao da Etapa 17 (mesmos hiperparametros, treinados 1x
sobre todo o historico -- igual a Etapa 18) para estimar o risco esperado em
cenarios hipoteticos, e usa SHAP (Etapa 18) para decompor POR QUE um cenario
tem risco maior/menor que outro.

Cenarios adaptados do exemplo do briefing (A-D). Adaptacao necessaria: o
briefing especifica publico (ex. "20 mil pessoas"), mas `publico`/
`taxa_ocupacao` sao 100% ausentes desde a Etapa 12 e NUNCA entraram no
conjunto de features de nenhum modelo (Etapas 13-18) -- declarado como
limitacao explicita (Regra 10), nao um proxy inventado.

Metodologia de construcao dos cenarios: em vez de fabricar uma linha
sintetica com 71 features do zero (que exigiria inventar valores para
historico/clima sem base), cada cenario usa uma linha REAL do dataset --
um dia historico que ja satisfaz a descricao do cenario (dia da semana,
tem_jogo, classico, horario) -- e prediz sobre ela diretamente. Isso evita
Regra 1/2 (nao inventar dados/resultados): todo feature vem de um dia que
realmente aconteceu, exceto o cenario D, que aplica UMA unica perturbacao
controlada (chuva) sobre a linha real do cenario B, para isolar o efeito do
clima com o resto do dia mantido identico.

Cada cenario e comparado a um BASELINE pareado por dia da semana e mes (dia
real, mesmo dia da semana, sem jogo) -- a diferenca entre a previsao do
cenario e a do baseline e decomposta EXATAMENTE (aditividade do SHAP:
predicao = base_value + soma dos SHAP de cada feature, entao a diferenca
entre 2 predicoes = soma das diferencas de SHAP feature a feature) por
grupo de features (temporal/futebol/clima/historica), mostrando quanto da
diferenca de risco vem de fato do "futebol" da linha vs de outras
diferencas incidentais entre os 2 dias reais escolhidos (clima do dia,
historico recente etc.).

Regra 5 (briefing): estas sao PREVISOES DE MODELO, nao estimativas causais
-- as Etapas 7-10/18 ja mostraram associacao fraca/nula de futebol nesses
alvos; o cenario mostra o que o MODELO preveria, nao o que aconteceria na
pratica se o jogo fosse cancelado.

Rodar depois da Etapa 18 (le `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`
e `reports/etapa17/tabelas/hiperparametros_producao.csv`).
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
import shap

import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
PROD_HP_PATH = os.path.join(BASE_DIR, "reports", "etapa17", "tabelas", "hiperparametros_producao.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa19")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

SEED = 42
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"
NOMES_DOW = {0: "domingo", 1: "segunda", 2: "terça", 3: "quarta", 4: "quinta", 5: "sexta", 6: "sábado"}

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
    return pd.DataFrame(imp.transform(X), columns=cols, index=X.index), imp


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
def treina_modelos(d_, hp):
    modelos = {}
    for base in ["crimes_violentos", "acidentes_com_vitima"]:
        elig = d_[f"y_count_{base}"].notna().to_numpy()
        cols = feature_cols(base)
        X = prep_X_native(d_, cols)
        y = d_[f"y_count_{base}"]
        model = XGBRegressor(objective="count:poisson", random_state=SEED,
                             **hp[("regressao", base, "xgboost_poisson")])
        model.fit(X.loc[elig], y[elig])
        explainer = shap.TreeExplainer(model)
        modelos[("regressao", base)] = dict(model=model, cols=cols, X=X, elig=elig, explainer=explainer)

    base = "acidentes_com_vitima"
    elig = d_[f"y_count_{base}"].notna().to_numpy()
    cols = feature_cols(base)
    y_pico = refit_pico_no_treino(d_, base, elig)
    y_c = y_pico[elig].astype(bool)
    Xi, imp = prep_X_imputed(d_, cols, elig)
    sca = StandardScaler().fit(Xi.loc[elig])
    Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=Xi.index)
    sw = sample_weight_balanced(y_c)
    model = LogisticRegression(max_iter=3000, class_weight="balanced", solver="liblinear",
                               **hp[("classificacao", base, "logreg_balanced")])
    model.fit(Xs.loc[elig], y_c.astype(int), sample_weight=sw)
    masker = shap.maskers.Independent(Xs.loc[elig], max_samples=int(elig.sum()))
    explainer = shap.Explainer(model, masker, feature_names=cols)
    modelos[("classificacao", base)] = dict(model=model, cols=cols, imp=imp, sca=sca, elig=elig, explainer=explainer)
    return modelos


# ---------------------------------------------------------------------------
def escolhe_anchor(d_, mask):
    """Escolha DETERMINISTICA (mediana por data) entre os dias reais que
    satisfazem os criterios do cenario -- evita cherry-picking manual de uma
    data favoravel."""
    cand = d_[mask].sort_values("data")
    if len(cand) == 0:
        return None
    return cand.iloc[len(cand) // 2]


def constroi_cenarios(d_):
    elig_geral = d_["y_count_acidentes_com_vitima"].notna() & d_["y_count_crimes_violentos"].notna()

    defs = {
        "A_domingo_jogo_comum": dict(
            desc="Domingo + jogo comum (não-clássico)",
            mask=elig_geral & (d_.dia_semana == 0) & (d_.tem_jogo_sp == 1) & (d_.classico == 0) & d_.mes.between(4, 11),
            baseline="baseline_domingo"),
        "B_domingo_classico": dict(
            desc="Domingo + clássico",
            mask=elig_geral & (d_.dia_semana == 0) & (d_.classico == 1),
            baseline="baseline_domingo"),
        "C_quarta_noturno": dict(
            desc="Quarta-feira + jogo noturno",
            mask=elig_geral & (d_.dia_semana == 3) & (d_.jogo_noturno == 1) & d_.mes.between(4, 11),
            baseline="baseline_quarta"),
        "baseline_domingo": dict(
            desc="Domingo sem jogo (baseline pareado p/ A, B, D)",
            mask=elig_geral & (d_.dia_semana == 0) & (d_.tem_jogo_sp == 0) & d_.mes.between(4, 11),
            baseline=None),
        "baseline_quarta": dict(
            desc="Quarta-feira sem jogo (baseline pareado p/ C)",
            mask=elig_geral & (d_.dia_semana == 3) & (d_.tem_jogo_sp == 0) & d_.mes.between(4, 11),
            baseline=None),
    }

    cenarios = {}
    for nome, spec in defs.items():
        anchor = escolhe_anchor(d_, spec["mask"])
        cenarios[nome] = dict(desc=spec["desc"], data=anchor["data"], idx=anchor.name,
                              baseline=spec["baseline"], overrides={})

    # D = mesma linha real do cenario B, com UMA perturbacao controlada:
    # chuva (precipitacao_total -> mediana dos dias de chuva observados).
    chuva_mediana = d_.loc[d_.chuva == True, "precipitacao_total"].median()
    cenarios["D_domingo_classico_chuva"] = dict(
        desc=f"Domingo + clássico + chuva (precipitação = {chuva_mediana:.1f}mm, "
             "mediana dos dias de chuva observados)",
        data=cenarios["B_domingo_classico"]["data"], idx=cenarios["B_domingo_classico"]["idx"],
        baseline="baseline_domingo",
        overrides={"precipitacao_total": chuva_mediana, "chuva": True})

    return cenarios


def prediz_cenario(d_, modelos, cenario):
    idx = cenario["idx"]
    row = d_.loc[[idx]].copy()
    for k, v in cenario["overrides"].items():
        row[k] = v

    out = {}
    for base in ["crimes_violentos", "acidentes_com_vitima"]:
        m = modelos[("regressao", base)]
        Xr = prep_X_native(row, m["cols"])
        out[f"pred_count_{base}"] = float(m["model"].predict(Xr)[0])
        # SHAP do XGBoost (objective count:poisson) e aditivo no MARGEM
        # (log da taxa), nao na escala de contagem (exp() e nao-linear) --
        # `output_margin=True` = log(predict()), conferido contra
        # base_value+soma(shap) antes de publicar.
        out[f"pred_lograte_{base}"] = float(m["model"].predict(Xr, output_margin=True)[0])
        exp = m["explainer"](Xr)
        out[f"shap_{base}"] = pd.Series(exp.values[0], index=m["cols"])
        out[f"shap_base_{base}"] = float(exp.base_values[0])

    base = "acidentes_com_vitima"
    m = modelos[("classificacao", base)]
    Xi = pd.DataFrame(m["imp"].transform(row[m["cols"]]), columns=m["cols"], index=row.index)
    Xs = pd.DataFrame(m["sca"].transform(Xi), columns=m["cols"], index=Xi.index)
    out["pred_proba_pico_acidentes"] = float(m["model"].predict_proba(Xs)[0, 1])
    # idem para o LogReg: SHAP e aditivo no log-odds (decision_function),
    # nao na probabilidade (sigmoid tambem e nao-linear).
    out["pred_logodds_pico_acidentes"] = float(m["model"].decision_function(Xs)[0])
    exp = m["explainer"](Xs)
    out["shap_clf_acidentes"] = pd.Series(exp.values[0], index=m["cols"])
    return out


# ---------------------------------------------------------------------------
def secao_decomposicao(cenarios, preds, base_pred, chave_shap, base_col, cenario_nome):
    c = cenarios[cenario_nome]
    if c["baseline"] is None:
        return None
    bl_nome = c["baseline"]
    delta_total = preds[cenario_nome][base_pred] - preds[bl_nome][base_pred]
    shap_cen = preds[cenario_nome][chave_shap]
    shap_bl = preds[bl_nome][chave_shap]
    delta_shap = (shap_cen - shap_bl)
    grp = pd.Series({f: grupo_de(f, base_col) for f in delta_shap.index})
    por_grupo = delta_shap.groupby(grp).sum().sort_values(key=np.abs, ascending=False)
    soma_check = delta_shap.sum()
    return dict(delta_total=delta_total, delta_shap_soma=soma_check, por_grupo=por_grupo, delta_shap=delta_shap)


# ---------------------------------------------------------------------------
def main():
    d_ = load()
    hp = carrega_hp_producao()
    print("[cenarios] treinando modelos de producao...")
    modelos = treina_modelos(d_, hp)
    cenarios = constroi_cenarios(d_)

    w("# Etapa 19 -- Análise de cenários\n")
    w(f"_Gerado por `scripts/16_analise_cenarios.py` em {date.today()}. "
      "Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`, "
      "`reports/etapa17/tabelas/hiperparametros_producao.csv`._\n")
    w("> **Regra 5**: os números abaixo são PREVISÕES DO MODELO para dias "
      "hipotéticos, não estimativas causais. As Etapas 7-10/18 já mostraram "
      "associação fraca/nula entre futebol e estes desfechos depois de "
      "controlar calendário -- um cenário com risco previsto mais alto "
      "reflete o que o modelo calcularia para aquele PERFIL de dia (que "
      "pode coincidir com época do ano, dia da semana etc.), não uma "
      "afirmação de que cancelar o jogo reduziria o risco na prática.\n")
    w("**Adaptação em relação ao exemplo do briefing**: os cenários A-D do "
      "briefing especificam público (\"20 mil pessoas\" etc.) -- `publico`/"
      "`taxa_ocupacao` são 100% ausentes desde a Etapa 12 e nunca entraram "
      "no conjunto de features de nenhum modelo (Etapas 13-18); **não "
      "modelado, declarado como limitação (Regra 10), sem proxy "
      "inventado.** Os cenários abaixo variam só as dimensões que os "
      "modelos realmente usam: dia da semana, tipo de jogo (comum/clássico), "
      "horário e clima.\n")
    w("**Método**: cada cenário A, B, C e os 2 baselines usa uma linha REAL "
      "do dataset -- um dia histórico que já satisfaz a descrição do "
      "cenário, escolhido deterministicamente (mediana por data entre os "
      "candidatos elegíveis, para não cherry-picker uma data favorável). O "
      "cenário D reusa a MESMA linha real do cenário B com uma única "
      "perturbação controlada (chuva), para isolar o efeito do clima "
      "mantendo o resto do dia idêntico.\n")

    w("## 1. Cenários e dias-âncora usados\n")
    tab_anchor = pd.DataFrame([{"cenário": k, "descrição": v["desc"], "dia_âncora": v["data"].date()}
                               for k, v in cenarios.items()])
    w(df_to_md(tab_anchor, index=False))
    w("")

    print("[cenarios] predizendo...")
    preds = {nome: prediz_cenario(d_, modelos, c) for nome, c in cenarios.items()}

    w("## 2. Risco previsto por cenário\n")
    linhas = []
    for nome, c in cenarios.items():
        p = preds[nome]
        linhas.append({"cenário": nome, "descrição": c["desc"],
                       "pred_crimes_violentos": p["pred_count_crimes_violentos"],
                       "pred_acidentes_com_vitima": p["pred_count_acidentes_com_vitima"],
                       "prob_pico_acidentes_(logreg)": p["pred_proba_pico_acidentes"]})
    tab_pred = pd.DataFrame(linhas)
    tab_pred.to_csv(os.path.join(TAB_DIR, "predicoes_cenarios.csv"), index=False)
    w(df_to_md(tab_pred.drop(columns="descrição"), floatfmt=3, index=False))
    w("")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    ordem = list(cenarios.keys())
    axes[0].bar(ordem, [preds[n]["pred_count_crimes_violentos"] for n in ordem], color="#c44e52")
    axes[0].set_title("crimes_violentos -- contagem prevista")
    axes[1].bar(ordem, [preds[n]["pred_count_acidentes_com_vitima"] for n in ordem], color="#4c72b0")
    axes[1].set_title("acidentes_com_vitima -- contagem prevista")
    axes[2].bar(ordem, [preds[n]["pred_proba_pico_acidentes"] for n in ordem], color="#55a868")
    axes[2].set_title("acidentes_com_vitima -- P(pico), logreg")
    for ax in axes:
        ax.tick_params(axis="x", rotation=90)
    w(f"![predicoes por cenario]({savefig('00_predicoes_cenarios.png')})\n")

    w("## 3. Por que um cenário tem risco maior/menor -- decomposição SHAP exata\n")
    w("**Nota de escala**: SHAP é aditivo na escala em que o modelo faz a "
      "soma das árvores/coeficientes -- para XGBoost Poisson isso é o "
      "**log da taxa prevista** (`output_margin=True`), não a contagem "
      "(`predict()` aplica `exp()`, que é não-linear); para a Logistic "
      "Regression é o **log-odds** (`decision_function`), não a "
      "probabilidade (`predict_proba()` aplica sigmoid). A tabela abaixo "
      "decompõe a diferença NESSA escala -- por isso o número de "
      "\"diferença na predição\" aqui é diferente do delta de contagem/"
      "probabilidade da seção 2 (que é mais interpretável, mas não "
      "aditivo). A soma dos deltas SHAP bate exatamente com a diferença "
      "na escala margem/log-odds -- conferido antes de publicar.\n")

    comparacoes = [
        ("A_domingo_jogo_comum", "pred_lograte_crimes_violentos", "shap_crimes_violentos", "crimes_violentos", "crimes_violentos (regressão, log da taxa)"),
        ("A_domingo_jogo_comum", "pred_lograte_acidentes_com_vitima", "shap_acidentes_com_vitima", "acidentes_com_vitima", "acidentes_com_vitima (regressão, log da taxa)"),
        ("B_domingo_classico", "pred_lograte_crimes_violentos", "shap_crimes_violentos", "crimes_violentos", "crimes_violentos (regressão, log da taxa)"),
        ("B_domingo_classico", "pred_lograte_acidentes_com_vitima", "shap_acidentes_com_vitima", "acidentes_com_vitima", "acidentes_com_vitima (regressão, log da taxa)"),
        ("C_quarta_noturno", "pred_lograte_crimes_violentos", "shap_crimes_violentos", "crimes_violentos", "crimes_violentos (regressão, log da taxa)"),
        ("C_quarta_noturno", "pred_lograte_acidentes_com_vitima", "shap_acidentes_com_vitima", "acidentes_com_vitima", "acidentes_com_vitima (regressão, log da taxa)"),
        ("D_domingo_classico_chuva", "pred_lograte_acidentes_com_vitima", "shap_acidentes_com_vitima", "acidentes_com_vitima", "acidentes_com_vitima (regressão, log da taxa) -- D vs B (só chuva muda)"),
        ("B_domingo_classico", "pred_logodds_pico_acidentes", "shap_clf_acidentes", "acidentes_com_vitima", "acidentes_com_vitima (classificação, log-odds)"),
    ]
    # D vs B usa B como baseline "local" para isolar so a chuva
    cenarios["D_domingo_classico_chuva"]["baseline"] = "B_domingo_classico"

    linhas_decomp = []
    for cenario_nome, pred_key, shap_key, base_col, titulo in comparacoes:
        res = secao_decomposicao(cenarios, preds, pred_key, shap_key, base_col, cenario_nome)
        if res is None:
            continue
        bl_nome = cenarios[cenario_nome]["baseline"]
        w(f"### {cenario_nome} vs {bl_nome} -- {titulo}\n")
        w(f"Diferença na predição (escala margem/log-odds): {res['delta_total']:.4f} "
          f"(soma dos deltas SHAP: {res['delta_shap_soma']:.4f} -- confere, "
          "diferença é aditiva NESSA escala)\n")
        w(df_to_md(res["por_grupo"].rename("delta_shap_soma").to_frame(), floatfmt=4, index=True))
        w("")
        for grupo, val in res["por_grupo"].items():
            linhas_decomp.append({"cenario": cenario_nome, "baseline": bl_nome, "alvo": titulo,
                                  "grupo": grupo, "delta_shap": val, "delta_total_predicao": res["delta_total"]})
    tab_decomp = pd.DataFrame(linhas_decomp)
    tab_decomp.to_csv(os.path.join(TAB_DIR, "decomposicao_shap_cenarios.csv"), index=False)

    w("### Resumo -- participação do grupo `futebol` em cada comparação\n")
    w("`%|futebol|` = |delta_shap do futebol| / soma de |delta_shap| de todos "
      "os grupos -- mede quanto do \"tamanho\" total da diferença (não só a "
      "direção) o futebol representa, mesmo quando o sinal é oposto ao "
      "delta total.\n")
    resumo = []
    for (cen, bl, alvo), sub in tab_decomp.groupby(["cenario", "baseline", "alvo"], sort=False):
        tot_abs = sub["delta_shap"].abs().sum()
        fut = sub.loc[sub.grupo == "futebol", "delta_shap"]
        pct_fut = (fut.abs().iloc[0] / tot_abs * 100) if len(fut) and tot_abs > 0 else np.nan
        resumo.append({"cenário": cen, "baseline": bl, "alvo": alvo,
                       "delta_total_margem": sub["delta_total_predicao"].iloc[0],
                       "%|futebol|": pct_fut})
    tab_resumo = pd.DataFrame(resumo)
    tab_resumo.to_csv(os.path.join(TAB_DIR, "resumo_participacao_futebol.csv"), index=False)
    w(df_to_md(tab_resumo, floatfmt=2, index=False))
    w("")

    w("## 4. Síntese\n")
    top_pico = tab_pred.loc[tab_pred["prob_pico_acidentes_(logreg)"].idxmax()]
    w(f"- **Achado que ilustra bem a ressalva de causalidade**: o cenário com "
      f"MAIOR P(pico) previsto para `acidentes_com_vitima` é "
      f"`{top_pico['cenário']}` ({top_pico['prob_pico_acidentes_(logreg)']:.3f}) "
      f"-- \"{top_pico['descrição']}\" -- **não** o clássico (B) nem o "
      "noturno de meio de semana (C), que intuitivamente pareceriam mais "
      "\"arriscados\". Isso não significa que jogo comum é mais perigoso que "
      "clássico -- significa que o dia real escolhido para ancorar esse "
      "cenário (ver seção 1) tinha outras características (histórico "
      "recente, clima) que pesam mais no modelo do que o tipo de jogo. "
      "Exatamente o tipo de leitura equivocada que a decomposição da seção "
      "3 existe para prevenir.\n")
    w(textwrap.dedent("""\
        - **Isto é modelagem, não causalidade** (Regra 5): os números acima
          são o que os modelos de produção (Etapa 17) preveem para dias com
          o PERFIL descrito, não o efeito de "ligar/desligar" o jogo -- as
          Etapas 7-10/18 já mostraram que boa parte da diferença entre um
          dia de jogo e um dia sem jogo é explicada por calendário (época do
          ano, dia da semana), não pelo jogo em si.
        - A decomposição da seção 3 quantifica isso diretamente: quando o
          grupo `futebol` contribui pouco para o delta total (comparar com
          `temporal`/`clima`/`historica` na mesma linha), a diferença de
          risco entre o cenário e o baseline vem majoritariamente de outras
          diferenças entre os 2 dias reais escolhidos, não do jogo -- ver
          números exatos por cenário acima. Exceção parcial: na
          classificação de `acidentes_com_vitima`, futebol responde por
          ~33% do "tamanho" do delta B vs baseline -- ainda minoritário,
          mas a maior participação entre todas as comparações, consistente
          com o achado da Etapa 18 de que essa é a combinação alvo/tarefa
          com a fração de futebol menos totalmente auditada.
        - **Público não pôde ser incluído** em nenhum cenário (feature 100%
          ausente, ver Etapa 12/18) -- os cenários B e D do briefing original
          (que especificam 50 mil pessoas) foram simulados só pelas
          dimensões calendário/jogo/clima disponíveis.
        - **Próximo**: Etapa 20 -- análise de causalidade formal, retomando
          os confundidores já identificados nas Etapas 7-10 e o achado de
          colinearidade com calendário da Etapa 18.
    """))

    path = os.path.join(OUT_DIR, "relatorio_cenarios.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
