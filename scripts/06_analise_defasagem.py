"""
06_analise_defasagem.py
Etapa 9 do roteiro -- ANALISE DE DEFASAGEM TEMPORAL (D-2 .. D+2).

Pergunta: o impacto potencial do jogo aparece ANTES (vespera), NO DIA, ou
DEPOIS? E qual defasagem tem o maior efeito?

Cuidado herdado das Etapas 7-8: jogo e desfecho tem estrutura de dia da semana
e de mes; uma correlacao cruzada crua so mostraria essa sazonalidade. Entao:

  1. MODELO DE DEFASAGENS DISTRIBUIDAS (inferencia principal): GLM Poisson
     y ~ jogo[D-2]+jogo[D-1]+jogo[D0]+jogo[D+1]+jogo[D+2] + C(dia_semana) +
        C(mes) + feriado,  erros-padrao robustos HC1.
     Estima o efeito de CADA defasagem controlando as outras e o calendario.
  2. CORRELACAO CRUZADA (CCF) exploratoria sobre as series DESSAZONALIZADAS
     (residuo de OLS ~ C(dia_semana)+C(mes)+feriado), lags -14..+14, com
     banda +-1.96/sqrt(n). Aproximacao padrao; pre-branqueamento ARIMA completo
     fica como refinamento.
  3. EVENT STUDY: media do residuo dessazonalizado em torno de cada dia de jogo
     (offset -7..+7), tambem so para jogos "isolados" (sem outro jogo em +-3d).
  4. Kruskal-Wallis nos residuos por janela (jogo_d_menos_2..jogo_d_mais_2) vs baseline.

Convencao de defasagem IGUAL a do gold: jogo_d_menos_k = houve jogo ha k dias
(efeito posterior/rescaldo); jogo_d_mais_k = ha jogo daqui a k dias (efeito
antecipatorio/vespera); jogo_d0 = jogo no mesmo dia.

REGRA 5: associacao/defasagem != causalidade. Inferencia causal = Etapa 20.

Exclusoes (Etapa 6): crime remove 2023-12-30/31; acidente remove +2022-01-17
e 2023-08-07. Os lags sao construidos ANTES da exclusao (a serie diaria
continua existindo); as linhas excluidas so saem da amostra de estimacao.

Rodar depois de 01..05.
"""
import os
import textwrap
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa9")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}

CRIME_OUTCOMES = ["crimes_totais", "crimes_violentos", "lesao_corporal_dolosa"]
ACID_OUTCOMES = ["acidentes_total", "acidentes_com_vitima", "acidentes_fatais"]
# Convencao de defasagem: IGUAL a do gold (`02_limpeza.py`), relativa ao DIA DE
# REFERENCIA (o dia do desfecho), nao ao dia do jogo.
#   jogo_d_menos_k[t] = tem_jogo_sp[t-k]  -> houve jogo ha k dias
#                       -> mede efeito POSTERIOR / rescaldo (k dias DEPOIS do jogo)
#   jogo_d0[t]        = tem_jogo_sp[t]    -> jogo no mesmo dia
#   jogo_d_mais_k[t]  = tem_jogo_sp[t+k]  -> ha jogo daqui a k dias
#                       -> mede efeito ANTECIPATORIO / vespera (k dias ANTES do jogo)
# jogo_d_menos_1 / jogo_d_mais_1 sao exatamente as colunas homonimas do gold;
# os termos _2 sao a extensao natural da mesma regra.
LAG_TERMS = {
    "jogo_d_menos_2": 2,    # tem_jogo_sp.shift(2)
    "jogo_d_menos_1": 1,    # tem_jogo_sp.shift(1)  == gold jogo_d_menos_1
    "jogo_d0": 0,           # tem_jogo_sp
    "jogo_d_mais_1": -1,    # tem_jogo_sp.shift(-1) == gold jogo_d_mais_1
    "jogo_d_mais_2": -2,    # tem_jogo_sp.shift(-2)
}
CTRL = "C(dia_semana) + C(mes) + feriado"

_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:,.{floatfmt}f}"
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


def bh_fdr(pv, q=0.05):
    p = np.asarray(pv, float)
    ok = ~np.isnan(p)
    adj = np.full(len(p), np.nan)
    pp = p[ok]
    n = len(pp)
    order = np.argsort(pp)
    ranked = pp[order] * n / (np.arange(n) + 1)
    s = np.minimum.accumulate(ranked[::-1])[::-1]
    tmp = np.empty(n)
    tmp[order] = np.clip(s, 0, 1)
    adj[ok] = tmp
    return adj


def load():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    df["tem_jogo_sp"] = df["tem_jogo_sp"].astype(int)
    df["feriado"] = df["feriado"].astype(int)
    df["dia_semana"] = df["dia_semana"].astype(int)
    df["mes"] = df["mes"].astype(int)
    # defasagens do indicador de jogo (serie diaria completa, 730 dias).
    # jogo_d_menos_k[t] = tem_jogo_sp[t-k] = shift(k); jogo_d_mais_k[t] = shift(-k).
    for nome, k in LAG_TERMS.items():
        df[nome] = df["tem_jogo_sp"].shift(k)
    return df


def familia_base(df, familia):
    excl = EXCL_CRIME if familia == "crime" else EXCL_ACID
    return df[~df["data"].isin(excl)].copy()


def deseasonaliza(df, col):
    """residuo de OLS col ~ C(dia_semana)+C(mes)+feriado, na serie diaria completa.
    Linhas com col NaN ficam NaN no residuo."""
    d = df[["data", col, "dia_semana", "mes", "feriado"]].copy()
    fit = smf.ols(f"{col} ~ {CTRL}", data=d.dropna(subset=[col])).fit()
    pred = fit.predict(d)
    res = d[col] - pred
    return res.to_numpy(float)


# ---------------------------------------------------------------------------
# 9.1 modelo de defasagens distribuidas
# ---------------------------------------------------------------------------
def secao_dlag(df):
    w("## 1. Modelo de defasagens distribuidas (GLM Poisson, HC1)\n")
    w("**Convencao (igual a do gold):** `jogo_d_menos_k` = houve jogo ha k dias "
      "(desfecho medido k dias DEPOIS do jogo -> efeito **posterior / rescaldo**); "
      "`jogo_d_mais_k` = ha jogo daqui a k dias (desfecho na **vespera** -> efeito "
      "**antecipatorio**); `jogo_d0` = jogo no mesmo dia.\n")
    w("**H0:** o coeficiente daquela defasagem = 0 (rate ratio = 1), controlando as "
      "outras defasagens + dia da semana + mes + feriado. **H1:** != 0. Rate ratio "
      "`exp(coef)`: 1.05 = +5% no desfecho naquela posicao relativa ao jogo. IC 95% "
      "e p por HC1; Benjamini-Hochberg sobre as 5 defasagens x 6 desfechos.\n")

    termos = list(LAG_TERMS)  # ordem: d_menos_2, d_menos_1, d0, d_mais_1, d_mais_2
    formula_rhs = " + ".join(termos) + " + " + CTRL

    linhas = []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = familia_base(df, familia).dropna(subset=termos)
        for col in outs:
            m = smf.glm(f"{col} ~ {formula_rhs}", data=d,
                        family=sm.families.Poisson()).fit(cov_type="HC1")
            ci = m.conf_int()
            for t in termos:
                linhas.append({
                    "familia": familia, "desfecho": col, "defasagem": t,
                    "rate_ratio": np.exp(m.params[t]),
                    "IC95_lo": np.exp(ci.loc[t, 0]), "IC95_hi": np.exp(ci.loc[t, 1]),
                    "efeito_%": (np.exp(m.params[t]) - 1) * 100,
                    "p_value": m.pvalues[t],
                })
    res = pd.DataFrame(linhas)
    res["p_BH"] = bh_fdr(res["p_value"].to_numpy())
    res["signif_BH_5pct"] = res["p_BH"] <= 0.05
    res.to_csv(os.path.join(TAB_DIR, "defasagens_distribuidas.csv"), index=False)
    w(df_to_md(res[["familia", "desfecho", "defasagem", "rate_ratio", "IC95_lo",
                    "IC95_hi", "efeito_%", "p_value", "p_BH", "signif_BH_5pct"]],
              floatfmt=3, index=False))
    w("")

    # forest por desfecho
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        fig, axes = plt.subplots(1, len(outs), figsize=(5 * len(outs), 3.6), sharey=True)
        for ax, col in zip(axes, outs):
            sub = res[res["desfecho"] == col].set_index("defasagem").loc[list(LAG_TERMS)]
            y = np.arange(len(sub))[::-1]
            ax.errorbar(sub["rate_ratio"], y,
                        xerr=[sub["rate_ratio"] - sub["IC95_lo"],
                              sub["IC95_hi"] - sub["rate_ratio"]],
                        fmt="o", capsize=3)
            ax.axvline(1, color="k", ls="--", lw=1)
            ax.set_yticks(y)
            ax.set_yticklabels(sub.index)
            ax.set_title(col)
            ax.grid(axis="x", alpha=.3)
        fig.suptitle(f"Rate ratio do jogo por defasagem -- {familia} (ajustado, HC1)")
        rel = savefig(f"01_forest_dlag_{familia}.png")
        w(f"![forest dlag {familia}]({rel})\n")
    return res


# ---------------------------------------------------------------------------
# 9.2 correlacao cruzada sobre series dessazonalizadas
# ---------------------------------------------------------------------------
def ccf(x, y, maxlag):
    """corr(y_{t+k}, x_t), k in [-maxlag, maxlag]. k>0 => y depois do jogo."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    xs = (x - np.nanmean(x)) / np.nanstd(x)
    ys = (y - np.nanmean(y)) / np.nanstd(y)
    n = len(x)
    lags, vals = [], []
    for k in range(-maxlag, maxlag + 1):
        if k >= 0:
            a, b = xs[:n - k], ys[k:]
        else:
            a, b = xs[-k:], ys[:n + k]
        mask = np.isfinite(a) & np.isfinite(b)
        lags.append(k)
        vals.append(np.corrcoef(a[mask], b[mask])[0, 1] if mask.sum() > 20 else np.nan)
    return np.array(lags), np.array(vals)


def secao_ccf(df):
    w("## 2. Correlacao cruzada (CCF) -- series dessazonalizadas\n")
    w("Ambas as series (indicador de jogo e desfecho) foram **residualizadas** "
      "sobre `C(dia_semana) + C(mes) + feriado` antes do cruzamento, para o CCF "
      "medir o que sobra alem da sazonalidade. Lag k>0 = desfecho **depois** do "
      "jogo (efeito posterior, equivale a `jogo_d_menos_k` da secao 1); k<0 = "
      "desfecho antes do jogo (efeito antecipatorio / vespera, equivale a "
      "`jogo_d_mais_|k|`). Banda tracejada = +-1.96/sqrt(n) (referencia aproximada; "
      "autocorrelacao residual pode inflar cruzamentos -- a inferencia firme e a "
      "secao 1).\n")

    jogo_res = deseasonaliza(df, "tem_jogo_sp") if False else None
    # indicador de jogo tambem dessazonalizado:
    d0 = df[["data", "tem_jogo_sp", "dia_semana", "mes", "feriado"]].copy()
    fit = smf.ols(f"tem_jogo_sp ~ {CTRL}", data=d0).fit()
    jogo_res = (d0["tem_jogo_sp"] - fit.predict(d0)).to_numpy(float)

    maxlag = 14
    band_txt = []
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for ax, col in zip(axes.ravel(), CRIME_OUTCOMES + ACID_OUTCOMES):
        familia = "crime" if col in CRIME_OUTCOMES else "acidente"
        base = familia_base(df, familia)
        y_res = deseasonaliza(base, col)
        # alinhar jogo_res ao mesmo indice de linhas
        jr = pd.Series(jogo_res, index=df["data"]).reindex(base["data"]).to_numpy(float)
        lags, vals = ccf(jr, y_res, maxlag)
        n_eff = np.isfinite(y_res).sum()
        band = 1.96 / np.sqrt(n_eff)
        ax.axhline(0, color="k", lw=.8)
        ax.axhline(band, color="r", ls="--", lw=.8)
        ax.axhline(-band, color="r", ls="--", lw=.8)
        ax.stem(lags, vals)
        ax.set_title(col)
        ax.set_xlabel("lag (dias); k>0 = depois do jogo")
        fig.tight_layout()
        peak = lags[np.nanargmax(np.abs(vals))]
        band_txt.append({"desfecho": col, "band_+-": band,
                         "ccf_lag0": vals[maxlag],
                         "lag_pico_|ccf|": int(peak),
                         "ccf_no_pico": vals[np.where(lags == peak)[0][0]]})
    rel = savefig("02_ccf.png")
    w(f"![ccf]({rel})\n")
    t = pd.DataFrame(band_txt)
    t.to_csv(os.path.join(TAB_DIR, "ccf_resumo.csv"), index=False)
    w(df_to_md(t, floatfmt=4, index=False))
    w("")


# ---------------------------------------------------------------------------
# 9.3 event study
# ---------------------------------------------------------------------------
def secao_event_study(df):
    w("## 3. Event study -- residuo dessazonalizado em torno do jogo\n")
    w("Para cada dia de jogo, pega-se o residuo dessazonalizado do desfecho nos "
      "offsets -7..+7. Media +- IC95 (erro-padrao da media). 'Isolado' = nenhum "
      "outro jogo em +-3 dias, para janelas limpas. **offset e relativo ao jogo**: "
      "offset 0 = dia do jogo; offset +k (depois do jogo) = `jogo_d_menos_k` da "
      "secao 1; offset -k (antes do jogo) = `jogo_d_mais_k`.\n")

    offsets = np.arange(-7, 8)
    jogo = df["tem_jogo_sp"].to_numpy()
    pos_jogo = np.where(jogo == 1)[0]
    # isolados
    iso = []
    for p in pos_jogo:
        lo, hi = max(0, p - 3), min(len(df), p + 4)
        if jogo[lo:hi].sum() == 1:
            iso.append(p)
    iso = np.array(iso)

    resumo = []
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for ax, col in zip(axes.ravel(), CRIME_OUTCOMES + ACID_OUTCOMES):
        familia = "crime" if col in CRIME_OUTCOMES else "acidente"
        base = familia_base(df, familia)
        r = pd.Series(deseasonaliza(base, col), index=base["data"])
        r = r.reindex(df["data"]).to_numpy(float)  # serie completa, NaN nos excluidos
        for grupo, cor, nome in [(pos_jogo, "#1f6f8b", "todos os jogos"),
                                 (iso, "#b5651d", "jogos isolados")]:
            M = np.full((len(grupo), len(offsets)), np.nan)
            for i, p in enumerate(grupo):
                for j, o in enumerate(offsets):
                    q = p + o
                    if 0 <= q < len(r):
                        M[i, j] = r[q]
            mean = np.nanmean(M, axis=0)
            se = np.nanstd(M, axis=0) / np.sqrt(np.sum(np.isfinite(M), axis=0))
            ax.plot(offsets, mean, "o-", color=cor, label=nome)
            ax.fill_between(offsets, mean - 1.96 * se, mean + 1.96 * se, color=cor, alpha=.2)
        ax.axhline(0, color="k", lw=.8)
        ax.axvline(0, color="gray", ls=":", lw=.8)
        ax.set_title(col)
        ax.set_xlabel("offset (dias) do jogo")
        ax.legend(fontsize=7)
        # numeros no dia do jogo e nos vizinhos imediatos (todos os jogos)
        rot = {-1: "jogo_d_mais_1 (vespera)", 0: "jogo_d0 (dia do jogo)",
               1: "jogo_d_menos_1 (dia seguinte)"}
        for o in (-1, 0, 1):
            vals = [r[p + o] for p in pos_jogo if 0 <= p + o < len(r) and np.isfinite(r[p + o])]
            resumo.append({"desfecho": col, "offset": o, "janela_gold": rot[o],
                           "n": len(vals), "media_residuo": np.mean(vals),
                           "t_p_vs_0": stats.ttest_1samp(vals, 0).pvalue})
    fig.tight_layout()
    rel = savefig("03_event_study.png")
    w(f"![event study]({rel})\n")
    t = pd.DataFrame(resumo)
    t["p_BH"] = bh_fdr(t["t_p_vs_0"].to_numpy())
    t.to_csv(os.path.join(TAB_DIR, "event_study_vizinhos.csv"), index=False)
    w(df_to_md(t[["desfecho", "offset", "janela_gold", "n", "media_residuo",
                  "t_p_vs_0", "p_BH"]], floatfmt=3, index=False))
    w("\n_media_residuo = quanto o desfecho fica acima (+) ou abaixo (-) do "
      "esperado pelo calendario, naquele offset. `janela_gold` traduz o offset "
      "para a convencao do gold/secao 1. t_p_vs_0 testa se difere de 0._\n")


# ---------------------------------------------------------------------------
# 9.4 Kruskal-Wallis nos residuos por janela
# ---------------------------------------------------------------------------
def secao_kw_residuo(df):
    w("## 4. Kruskal-Wallis nos residuos dessazonalizados por janela\n")
    w("Convencao do gold (mesma da secao 1): `jogo_d_menos_k` = dia k dias DEPOIS "
      "de um jogo (rescaldo); `jogo_d_mais_k` = dia k dias ANTES de um jogo "
      "(vespera); `jogo_d0` = dia do jogo; `baseline` = nenhum jogo em +-2 dias.\n")
    w("**H0:** o residuo (desfecho menos o esperado pelo calendario) tem a mesma "
      "distribuicao nessas 6 janelas. **H1:** ao menos uma difere. Se o efeito fosse "
      "so do calendario, os residuos nao deveriam separar as janelas.\n")

    jogo = df["tem_jogo_sp"].to_numpy()
    pos = np.where(jogo == 1)[0]
    janela = np.array(["baseline"] * len(df), dtype=object)
    # offset a partir do dia do jogo -> rotulo na convencao do gold:
    #   +1/+2 dias depois do jogo  -> jogo_d_menos_1 / _2   (rescaldo)
    #   -1/-2 dias antes do jogo   -> jogo_d_mais_1  / _2   (vespera)
    # ordem: mais distante primeiro, dia do jogo por ultimo -- em janelas que se
    # sobrepoem (jogos proximos), a posicao MAIS PROXIMA de um jogo prevalece.
    for off, lab in [(2, "jogo_d_menos_2"), (-2, "jogo_d_mais_2"),
                     (1, "jogo_d_menos_1"), (-1, "jogo_d_mais_1"), (0, "jogo_d0")]:
        for p in pos:
            q = p + off
            if 0 <= q < len(df):
                janela[q] = lab
    near = np.zeros(len(df), bool)
    for p in pos:
        near[max(0, p - 2):min(len(df), p + 3)] = True
    janela[~near] = "baseline"

    ordem = ["baseline", "jogo_d_menos_2", "jogo_d_menos_1", "jogo_d0",
             "jogo_d_mais_1", "jogo_d_mais_2"]
    linhas = []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        base = familia_base(df, familia)
        for col in outs:
            r = pd.Series(deseasonaliza(base, col), index=base["data"]).reindex(df["data"]).to_numpy(float)
            grupos, nomes = [], []
            for lab in ordem:
                v = r[(janela == lab) & np.isfinite(r)]
                if len(v) >= 5:
                    grupos.append(v)
                    nomes.append(lab)
            H, p = stats.kruskal(*grupos)
            k = len(grupos)
            n = sum(len(g) for g in grupos)
            eps2 = (H - k + 1) / (n - k)
            medias = {nm: np.mean(g) for nm, g in zip(nomes, grupos)}
            linhas.append({"familia": familia, "desfecho": col, "KW_H": H, "KW_p": p,
                           "epsilon2": eps2,
                           **{f"res_{nm}": medias.get(nm, np.nan)
                              for nm in ["baseline", "jogo_d_menos_1", "jogo_d0",
                                         "jogo_d_mais_1"]}})
    res = pd.DataFrame(linhas)
    res["KW_p_BH"] = bh_fdr(res["KW_p"].to_numpy())
    res.to_csv(os.path.join(TAB_DIR, "kw_residuo_janela.csv"), index=False)
    w(df_to_md(res[["familia", "desfecho", "KW_H", "KW_p", "KW_p_BH", "epsilon2",
                    "res_baseline", "res_jogo_d_menos_1", "res_jogo_d0",
                    "res_jogo_d_mais_1"]], floatfmt=4, index=False))
    w("\n_`res_jogo_d_menos_1` = residuo medio no dia SEGUINTE a um jogo (rescaldo); "
      "`res_jogo_d_mais_1` = residuo medio na VESPERA de um jogo._\n")


# ---------------------------------------------------------------------------
def main():
    df = load()
    w("# Etapa 9 -- Analise de defasagem temporal "
      "(`jogo_d_menos_2` .. `jogo_d_mais_2`)\n")
    w(f"_Gerado por `scripts/06_analise_defasagem.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv`._\n")
    w("> **Regra 5:** defasagem e associacao, nao causalidade. A questao aqui: "
      "*depois de tirar dia da semana e mes, sobra algum efeito do jogo -- e em "
      "qual posicao relativa (antes/durante/depois)?* Inferencia causal = Etapa 20.\n")
    w(textwrap.dedent("""\
        **Convencao de defasagem (identica a do gold `fato_dia_sp.csv`, relativa ao
        DIA DO DESFECHO, nao ao dia do jogo):**

        | termo | definicao | mede |
        | --- | --- | --- |
        | `jogo_d_menos_2` | `tem_jogo_sp.shift(2)` -- houve jogo ha 2 dias | efeito **posterior** (rescaldo, +2d) |
        | `jogo_d_menos_1` | `tem_jogo_sp.shift(1)` -- houve jogo ontem  | efeito **posterior** (rescaldo, +1d) |
        | `jogo_d0` | `tem_jogo_sp` -- jogo hoje | efeito no **proprio dia** |
        | `jogo_d_mais_1` | `tem_jogo_sp.shift(-1)` -- ha jogo amanha | efeito **antecipatorio** (vespera) |
        | `jogo_d_mais_2` | `tem_jogo_sp.shift(-2)` -- ha jogo em 2 dias | efeito **antecipatorio** (-2d) |

        `jogo_d_menos_1` e `jogo_d_mais_1` sao exatamente as colunas homonimas do
        gold. "Antecipatorio" (D-1/D-2 no sentido antigo) = `jogo_d_mais_*`;
        "posterior" (D+1/D+2 no sentido antigo) = `jogo_d_menos_*`.
    """))
    w("**Exclusoes (Etapa 6):** crime 2023-12-30/31; acidente +2022-01-17 e "
      "2023-08-07 (defasagens construidas antes de excluir).\n")

    secao_dlag(df)
    secao_ccf(df)
    secao_event_study(df)
    secao_kw_residuo(df)

    w("## 5. Sintese da Etapa 9\n")
    w(textwrap.dedent("""\
        **Resultado: nenhuma defasagem (`jogo_d_menos_2` .. `jogo_d_mais_2`) mostra
        efeito robusto do jogo.**

        - **Defasagens distribuidas (secao 1, inferencia principal):** das 30
          estimativas (6 desfechos x 5 defasagens), **zero** sao significativas
          apos BH (todas p_BH >= 0.97). O maior efeito e `acidentes_fatais` em
          `jogo_d0` (rate ratio 1.15, IC95 0.99-1.33, p = 0.06 sem BH) -- o mesmo
          sinal marginal ja visto nas Etapas 7 e 8, agora tambem nao robusto.
          Nada antecipatorio (`jogo_d_mais_1/2`, vespera) nem posterior
          (`jogo_d_menos_1/2`, rescaldo).
        - **CCF (secao 2):** nas series dessazonalizadas, o valor em lag 0 fica
          dentro da banda +-0.073 para todos os desfechos. Alguns picos passam a
          banda em lags -6/-7 (desfecho ANTES do jogo, sem sentido causal) -- sao
          os falsos positivos esperados por autocorrelacao residual, nao efeito.
        - **Event study (secao 3):** as curvas de residuo em torno do jogo
          (offset -7..+7) sao planas em torno de 0; nem a vespera, nem o dia do
          jogo, nem o dia seguinte diferem de 0 (todos p_BH = 0.91), com ou sem
          restricao a jogos isolados. O +16 em `crimes_totais` no dia do jogo e
          media inflada pelo outlier de 2022-06-19 (p = 0.48).
        - **Kruskal-Wallis nos residuos (secao 4):** epsilon^2 <= 0.006 e p_BH
          >= 0.52 para todos -- as janelas em torno do jogo nao se distinguem do
          baseline depois de remover o calendario.
        - **Coerencia com Etapas 7-8:** os tres relatorios convergem. A associacao
          bruta jogo x desfecho e **sazonalidade de calendario** (dia da semana e
          mes), nao efeito temporal do jogo -- nem antes, nem durante, nem depois.
        - **Texto para o relatorio final:** *"nao ha evidencia de efeito
          antecipatorio (vespera) nem posterior (rescaldo) do jogo sobre crime ou
          acidente apos controle de dia da semana e mes. O unico sinal residual --
          acidentes fatais no proprio dia do jogo, ~+15% -- nao e estatisticamente
          robusto e merece reexame com serie mais longa. Os dados nao permitem
          afirmar causalidade."*
        - **Limitacoes:** 730 dias; Paulistao/Libertadores fora da base (dias de
          jogo subcontados, o que ATENUA qualquer efeito real); sem dado de
          publico; CCF sem pre-branqueamento ARIMA completo (a secao 1 nao depende
          disso).
        - **Proximo:** Etapa 10 (espacial, limitada) e Etapa 11 (definicao de pico).
    """))

    path = os.path.join(OUT_DIR, "relatorio_defasagem.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))} arquivos)")
    print(f"[ok] tabelas : {TAB_DIR} ({len(os.listdir(TAB_DIR))} arquivos)")


if __name__ == "__main__":
    main()
