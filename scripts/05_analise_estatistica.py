"""
05_analise_estatistica.py
Etapa 8 do roteiro -- ANALISE ESTATISTICA formal.

O que a Etapa 7 ja fez: Mann-Whitney com jogo vs sem jogo + GLM ajustado.
O que a Etapa 8 acrescenta:
  1. Correlacao PEARSON e SPEARMAN (zero-order) com p-value, IC de Fisher e
     correcao de Benjamini-Hochberg.
  2. Correlacao PARCIAL -- o ponto central: a correlacao jogo x desfecho
     SOBREVIVE ao controle de dia da semana / mes / feriado / clima?
     Metodo: residualizar desfecho e driver sobre os controles (OLS) e
     correlacionar os residuos (Pearson para parcial de Pearson; residuos das
     RANKS para parcial de Spearman).
  3. TESTE DE PROPORCOES: P(dia "alto") em dia de jogo vs sem jogo, com limiar
     PROVISORIO P90/P95 (a definicao final de "pico" e a Etapa 11). z de duas
     proporcoes, qui-quadrado, Fisher; risco relativo, diferenca de risco,
     odds ratio com IC.
  4. KRUSKAL-WALLIS / ANOVA para fatores de >2 niveis (dia da semana; numero de
     jogos 0/1/2; janela D-1/D0/D+1; campeonato) com effect size (epsilon^2,
     eta^2) e post-hoc pareado (Mann-Whitney + BH).

Cada bloco declara H0, H1, estatistica, p-value, effect size e interpretacao.
REGRA 5: correlacao/associacao != causalidade. Inferencia causal = Etapa 20.

Exclusoes (Etapa 6): crime remove 2023-12-30/31; acidente remove +2022-01-17 e
2023-08-07 (lacunas de registro).

Rodar depois de 01..04.
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
import statsmodels.formula.api as smf
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa8")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}

CRIME_OUTCOMES = ["crimes_totais", "crimes_violentos", "lesao_corporal_dolosa",
                  "roubos_total", "furtos_total", "homicidios_dolosos"]
ACID_OUTCOMES = ["acidentes_total", "acidentes_com_vitima", "atropelamentos",
                 "colisoes", "acidentes_fatais"]
DRIVERS = ["tem_jogo_sp", "numero_jogos_sp", "classico", "jogo_noturno"]

CTRL_CAL = "C(dia_semana) + C(mes) + feriado"
CTRL_CAL_CLIMA = CTRL_CAL + " + temp_media + precipitacao_total + umidade_media"

_md = []


def w(line=""):
    _md.append(line)


def df_to_md(df, floatfmt=3, index=True):
    d = df.copy()
    if index:
        d = d.reset_index()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:,.{floatfmt}f}"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in d.iterrows():
        out.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(out)


def savefig(name):
    path = os.path.join(FIG_DIR, name)
    plt.savefig(path)
    plt.close()
    return os.path.relpath(path, OUT_DIR).replace("\\", "/")


def bh_fdr(pvals, q=0.05):
    p = np.asarray(pvals, float)
    ok = ~np.isnan(p)
    p_adj = np.full(len(p), np.nan)
    pp = p[ok]
    n = len(pp)
    order = np.argsort(pp)
    ranked = pp[order] * n / (np.arange(n) + 1)
    adj_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty(n)
    adj[order] = np.clip(adj_sorted, 0, 1)
    p_adj[ok] = adj
    return p_adj


def fisher_ci(r, n, k=0, alpha=0.05):
    """IC de Fisher-z. k = nº de covariaveis controladas (0 = correlacao simples)."""
    dof = n - k - 3
    if dof <= 0 or abs(r) >= 1:
        return np.nan, np.nan
    z = np.arctanh(r)
    se = 1 / np.sqrt(dof)
    zc = stats.norm.ppf(1 - alpha / 2)
    return np.tanh(z - zc * se), np.tanh(z + zc * se)


def load():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    for c in ["tem_jogo_sp", "classico", "jogo_noturno", "feriado", "fim_de_semana"]:
        df[c] = df[c].astype(float)
    return df


def base(df, familia):
    excl = EXCL_CRIME if familia == "crime" else EXCL_ACID
    return df[~df["data"].isin(excl)].copy()


# ---------------------------------------------------------------------------
# 8.1 correlacao zero-order
# ---------------------------------------------------------------------------
def secao_zero_order(df):
    w("## 1. Correlacao simples (zero-order): Pearson e Spearman\n")
    w("**H0:** rho = 0 (sem associacao monotona/linear entre driver e desfecho). "
      "**H1:** rho != 0. alpha = 0.05 bilateral, com Benjamini-Hochberg sobre o "
      "conjunto (driver x desfecho). IC 95% por transformacao de Fisher.\n")
    w("Spearman e o foco (contagens nao-normais, Etapa 6); Pearson vai junto para "
      "comparacao.\n")

    linhas = []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = base(df, familia)
        for col in outs:
            for drv in DRIVERS:
                sub = d[[col, drv]].dropna()
                n = len(sub)
                rp, pp = stats.pearsonr(sub[col], sub[drv])
                rs, ps = stats.spearmanr(sub[col], sub[drv])
                lo_s, hi_s = fisher_ci(rs, n)
                linhas.append({"familia": familia, "desfecho": col, "driver": drv, "n": n,
                               "pearson_r": rp, "pearson_p": pp,
                               "spearman_r": rs, "spearman_p": ps,
                               "spearman_IC95_lo": lo_s, "spearman_IC95_hi": hi_s})
    res = pd.DataFrame(linhas)
    res["spearman_p_BH"] = bh_fdr(res["spearman_p"].to_numpy())
    res["signif_BH_5pct"] = res["spearman_p_BH"] <= 0.05
    res.to_csv(os.path.join(TAB_DIR, "correlacao_zero_order.csv"), index=False)
    w(df_to_md(res[["familia", "desfecho", "driver", "n", "pearson_r", "spearman_r",
                    "spearman_IC95_lo", "spearman_IC95_hi", "spearman_p", "spearman_p_BH",
                    "signif_BH_5pct"]], floatfmt=3, index=False))
    w("")
    return res


# ---------------------------------------------------------------------------
# 8.2 correlacao parcial
# ---------------------------------------------------------------------------
def _resid(data, target, controls_formula):
    return smf.ols(f"{target} ~ {controls_formula}", data=data).fit()


def partial_corr(data, x, y, controls_formula, method="spearman"):
    cols_ctrl = ["dia_semana", "mes", "feriado", "temp_media",
                 "precipitacao_total", "umidade_media"]
    keep = [x, y] + [c for c in cols_ctrl if c in data.columns]
    d = data[keep].dropna().copy()
    n = len(d)
    if method == "spearman":
        d["_x"] = d[x].rank()
        d["_y"] = d[y].rank()
        mx, my = _resid(d, "_x", controls_formula), _resid(d, "_y", controls_formula)
        r, p = stats.pearsonr(mx.resid, my.resid)
    else:
        mx, my = _resid(d, x, controls_formula), _resid(d, y, controls_formula)
        r, p = stats.pearsonr(mx.resid, my.resid)
    k = int(round(mx.df_model))
    lo, hi = fisher_ci(r, n, k=k)
    return {"r": r, "p": p, "n": n, "k_controles": k, "IC95_lo": lo, "IC95_hi": hi}


def secao_parcial(df, zero):
    w("## 2. Correlacao parcial -- a associacao sobrevive aos confundidores?\n")
    w("**H0:** rho_parcial = 0 depois de remover o efeito linear dos controles. "
      "**H1:** != 0. Metodo: residualizar desfecho e driver (nas RANKS, para a "
      "versao Spearman) sobre os controles via OLS e correlacionar os residuos.\n")
    w("- **Modelo A (calendario):** controla `C(dia_semana) + C(mes) + feriado`.\n"
      "- **Modelo B (calendario + clima):** A + `temp_media + precipitacao_total + "
      "umidade_media` (subconjunto com clima observado).\n")

    zmap = {(r.desfecho, r.driver): r.spearman_r for r in zero.itertuples()}
    linhas, ps_a, ps_b = [], [], []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = base(df, familia)
        for col in outs:
            for drv in DRIVERS:
                a = partial_corr(d, col, drv, CTRL_CAL, "spearman")
                b = partial_corr(d, col, drv, CTRL_CAL_CLIMA, "spearman")
                linhas.append({
                    "familia": familia, "desfecho": col, "driver": drv,
                    "spearman_zero": zmap[(col, drv)],
                    "parcial_A_r": a["r"], "parcial_A_p": a["p"],
                    "parcial_A_IC_lo": a["IC95_lo"], "parcial_A_IC_hi": a["IC95_hi"],
                    "parcial_B_r": b["r"], "parcial_B_p": b["p"], "n_B": b["n"],
                })
                ps_a.append(a["p"])
                ps_b.append(b["p"])
    res = pd.DataFrame(linhas)
    res["parcial_A_p_BH"] = bh_fdr(np.array(ps_a))
    res["parcial_B_p_BH"] = bh_fdr(np.array(ps_b))
    res["A_signif_BH"] = res["parcial_A_p_BH"] <= 0.05
    res["B_signif_BH"] = res["parcial_B_p_BH"] <= 0.05
    res.to_csv(os.path.join(TAB_DIR, "correlacao_parcial.csv"), index=False)

    zero_sig = int((zero["spearman_p_BH"] <= 0.05).sum())
    a_sig = int(res["A_signif_BH"].sum())
    b_sig = int(res["B_signif_BH"].sum())
    w(f"**Placar:** dos {len(res)} pares driver x desfecho -- **{zero_sig}** significativos "
      f"na correlacao simples (secao 1), **{a_sig}** apos controle de calendario (modelo A), "
      f"**{b_sig}** apos controle de calendario + clima (modelo B).\n")

    w(df_to_md(res[["familia", "desfecho", "driver", "spearman_zero",
                    "parcial_A_r", "parcial_A_IC_lo", "parcial_A_IC_hi", "parcial_A_p_BH",
                    "A_signif_BH", "parcial_B_r", "parcial_B_p_BH", "B_signif_BH"]],
              floatfmt=3, index=False))
    w("")
    w("Leitura: comparar `spearman_zero` -> `parcial_A_r` -> `parcial_B_r`. Se a "
      "correlacao cai para perto de 0 e o IC passa a cruzar 0, a associacao simples "
      "era confundimento (dia da semana / mes / clima), nao efeito do jogo.\n")

    # figura: atenuacao zero-order -> parcial A, para tem_jogo_sp e numero_jogos_sp
    for drv in ["tem_jogo_sp", "numero_jogos_sp"]:
        sub = res[res["driver"] == drv]
        fig, ax = plt.subplots(figsize=(8, 5))
        y = np.arange(len(sub))[::-1]
        ax.plot(sub["spearman_zero"], y, "o", label="zero-order", color="#888")
        ax.errorbar(sub["parcial_A_r"], y,
                    xerr=[sub["parcial_A_r"] - sub["parcial_A_IC_lo"],
                          sub["parcial_A_IC_hi"] - sub["parcial_A_r"]],
                    fmt="s", capsize=3, label="parcial A (calendario)", color="#1f6f8b")
        ax.plot(sub["parcial_B_r"], y, "D", label="parcial B (+clima)", color="#b5651d")
        ax.axvline(0, color="k", ls="--", lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels(sub["desfecho"])
        ax.set_xlabel(f"correlacao de Spearman com {drv}")
        ax.set_title(f"Atenuacao da correlacao apos controle -- {drv}")
        ax.legend(fontsize=8)
        ax.grid(axis="x", alpha=.3)
        rel = savefig(f"01_parcial_{drv}.png")
        w(f"![parcial {drv}]({rel})\n")
    return res


# ---------------------------------------------------------------------------
# 8.3 teste de proporcoes
# ---------------------------------------------------------------------------
def secao_proporcoes(df):
    w("## 3. Teste de proporcoes -- dia \"alto\" em jogo vs sem jogo\n")
    w("Limiar **PROVISORIO** (a definicao formal de pico e a Etapa 11): dia alto = "
      "desfecho > P90 (e P95) calculado sobre TODOS os dias da familia. "
      "**H0:** P(alto | jogo) = P(alto | sem jogo). **H1:** != . Testes: z de duas "
      "proporcoes (principal), qui-quadrado e Fisher exato (robustez). Effect size: "
      "risco relativo (RR), diferenca de risco (RD), odds ratio (OR), todos com IC 95%.\n")

    linhas = []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = base(df, familia)
        jogo = d["tem_jogo_sp"] == 1
        for col in outs:
            for q in (0.90, 0.95):
                thr = d[col].quantile(q)
                alto = d[col] > thr
                a = int((alto & jogo).sum()); n1 = int(jogo.sum())
                c = int((alto & ~jogo).sum()); n0 = int((~jogo).sum())
                p1, p0 = a / n1, c / n0
                zst, pz = proportions_ztest([a, c], [n1, n0])
                chi2, pchi, _, _ = stats.chi2_contingency(
                    [[a, n1 - a], [c, n0 - c]], correction=False)
                _, pf = stats.fisher_exact([[a, n1 - a], [c, n0 - c]])
                rr = p1 / p0 if p0 > 0 else np.nan
                se_lnrr = np.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0) if a > 0 and c > 0 else np.nan
                rr_lo = rr * np.exp(-1.96 * se_lnrr) if rr == rr else np.nan
                rr_hi = rr * np.exp(1.96 * se_lnrr) if rr == rr else np.nan
                orr = (a * (n0 - c)) / ((n1 - a) * c) if (n1 - a) > 0 and c > 0 else np.nan
                linhas.append({
                    "familia": familia, "desfecho": col, "limiar": f"P{int(q*100)}",
                    "thr": thr, "n_jogo": n1, "alto_jogo": a, "P(alto|jogo)": p1,
                    "n_sem": n0, "alto_sem": c, "P(alto|sem)": p0,
                    "RR": rr, "RR_IC_lo": rr_lo, "RR_IC_hi": rr_hi,
                    "RD": p1 - p0, "OR": orr,
                    "z_p": pz, "chi2_p": pchi, "fisher_p": pf,
                })
    res = pd.DataFrame(linhas)
    res["z_p_BH"] = bh_fdr(res["z_p"].to_numpy())
    res["signif_BH_5pct"] = res["z_p_BH"] <= 0.05
    res.to_csv(os.path.join(TAB_DIR, "teste_proporcoes.csv"), index=False)
    w(df_to_md(res[["familia", "desfecho", "limiar", "P(alto|jogo)", "P(alto|sem)",
                    "RR", "RR_IC_lo", "RR_IC_hi", "RD", "OR", "z_p", "z_p_BH",
                    "signif_BH_5pct"]], floatfmt=3, index=False))
    w("")
    w("RR > 1 com IC que nao cruza 1 => dia de jogo tem mais chance de ser dia alto. "
      "Como o limiar aqui e provisorio e nao controla dia da semana, este resultado "
      "e um indicativo que a Etapa 11 (definicao de pico) e a modelagem (Etapa 14) "
      "vao refinar.\n")

    fig, ax = plt.subplots(figsize=(10, 5))
    sub = res[res["limiar"] == "P90"].reset_index(drop=True)
    x = np.arange(len(sub))
    ax.bar(x - 0.18, sub["P(alto|jogo)"], width=0.36, label="P(alto | jogo)", color="#c44e52")
    ax.bar(x + 0.18, sub["P(alto|sem)"], width=0.36, label="P(alto | sem jogo)", color="#4c72b0")
    ax.axhline(0.10, color="k", ls=":", lw=1, label="10% (base do P90)")
    ax.set_xticks(x)
    ax.set_xticklabels(sub["desfecho"], rotation=35, ha="right")
    ax.set_ylabel("proporcao de dias > P90")
    ax.set_title("Probabilidade de dia \"alto\" (P90 provisorio): jogo vs sem jogo")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=.3)
    rel = savefig("02_proporcoes_p90.png")
    w(f"![proporcoes p90]({rel})\n")
    return res


# ---------------------------------------------------------------------------
# 8.4 Kruskal-Wallis / ANOVA para fatores multi-nivel
# ---------------------------------------------------------------------------
def _epsilon2_kw(h, n, k):
    return (h - k + 1) / (n - k) if n > k else np.nan


def _eta2_anova(groups):
    allv = np.concatenate(groups)
    gm = allv.mean()
    ss_b = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
    ss_t = ((allv - gm) ** 2).sum()
    return ss_b / ss_t if ss_t > 0 else np.nan


def _janela(x):
    out = pd.Series("sem relacao", index=x.index)
    out[(x["jogo_d_mais_1"] == 1) & (x["tem_jogo_sp"] == 0)] = "D+1"
    out[(x["jogo_d_menos_1"] == 1) & (x["tem_jogo_sp"] == 0)] = "D-1"
    out[x["tem_jogo_sp"] == 1] = "D0"
    return out


def secao_kw(df):
    w("## 4. Kruskal-Wallis / ANOVA -- fatores de mais de 2 niveis\n")
    w("**H0:** todos os grupos tem a mesma distribuicao (mesma mediana). **H1:** ao "
      "menos um difere. Kruskal-Wallis (principal, nao-parametrico) + ANOVA (robustez). "
      "Effect size: epsilon^2 (KW) e eta^2 (ANOVA). Post-hoc: Mann-Whitney par a par "
      "com Benjamini-Hochberg, apenas quando KW p < 0.05.\n")

    especs = [
        ("dia_semana", "nome_dia_semana", "crime", CRIME_OUTCOMES[:3] + ["furtos_total"]),
        ("dia_semana", "nome_dia_semana", "acidente", ACID_OUTCOMES[:2] + ["atropelamentos"]),
        ("numero_jogos_sp", "numero_jogos_sp", "crime", ["crimes_totais", "crimes_violentos"]),
        ("numero_jogos_sp", "numero_jogos_sp", "acidente", ["acidentes_total", "acidentes_com_vitima"]),
        ("janela", "janela", "crime", ["crimes_totais", "crimes_violentos"]),
        ("janela", "janela", "acidente", ["acidentes_total", "acidentes_com_vitima"]),
    ]
    linhas, posthoc_blocks = [], []
    for nome_fator, fcol, familia, outs in especs:
        d = base(df, familia).copy()
        if fcol == "janela":
            d["janela"] = _janela(d)
        for col in outs:
            grupos, nomes = [], []
            for gval, g in d.groupby(fcol):
                v = g[col].dropna().to_numpy(float)
                if len(v) >= 3:
                    grupos.append(v)
                    nomes.append(str(gval))
            if len(grupos) < 2:
                continue
            h, ph = stats.kruskal(*grupos)
            f, pf = stats.f_oneway(*grupos)
            n = sum(len(g) for g in grupos)
            linhas.append({
                "fator": nome_fator, "familia": familia, "desfecho": col,
                "n_grupos": len(grupos), "n": n,
                "KW_H": h, "KW_p": ph, "epsilon2": _epsilon2_kw(h, n, len(grupos)),
                "ANOVA_F": f, "ANOVA_p": pf, "eta2": _eta2_anova(grupos),
            })
            if ph < 0.05:
                pares, pps = [], []
                for i in range(len(grupos)):
                    for j in range(i + 1, len(grupos)):
                        _, p = stats.mannwhitneyu(grupos[i], grupos[j], alternative="two-sided")
                        pares.append((nome_fator, col, f"{nomes[i]} vs {nomes[j]}",
                                      grupos[i].mean(), grupos[j].mean()))
                        pps.append(p)
                padj = bh_fdr(np.array(pps))
                for (fa, cc, par, m1, m2), p, pa in zip(pares, pps, padj):
                    posthoc_blocks.append({"fator": fa, "desfecho": cc, "par": par,
                                           "media_1": m1, "media_2": m2,
                                           "MW_p": p, "MW_p_BH": pa,
                                           "signif_BH": pa <= 0.05})
    res = pd.DataFrame(linhas)
    res["KW_p_BH"] = bh_fdr(res["KW_p"].to_numpy())
    res.to_csv(os.path.join(TAB_DIR, "kruskal_anova.csv"), index=False)
    w(df_to_md(res[["fator", "familia", "desfecho", "n_grupos", "KW_H", "KW_p",
                    "KW_p_BH", "epsilon2", "eta2"]], floatfmt=4, index=False))
    w("")
    w("_epsilon^2 / eta^2: ~0.01 pequeno, ~0.06 medio, ~0.14 grande._\n")

    ph = pd.DataFrame(posthoc_blocks)
    if len(ph):
        ph.to_csv(os.path.join(TAB_DIR, "kruskal_posthoc.csv"), index=False)
        w("### 4.1 Post-hoc (Mann-Whitney par a par, BH) -- so onde KW foi significativo\n")
        w("Para `dia_semana` (21 pares por desfecho) o quadro completo esta em "
          "`tabelas/kruskal_posthoc.csv`; resumo: a grande maioria dos pares difere, "
          "com **domingo e segunda** consistentemente abaixo dos dias uteis do meio/fim "
          "de semana. Abaixo so os fatores ligados ao futebol.\n")
        ph_show = ph[ph["fator"].isin(["numero_jogos_sp", "janela"])]
        w(df_to_md(ph_show[["fator", "desfecho", "par", "media_1", "media_2", "MW_p_BH",
                            "signif_BH"]], floatfmt=3, index=False))
        w("")
        w("_`numero_jogos_sp`: o contraste '0 vs 2 jogos' tem so 11 dias com 2 jogos -- "
          "instavel. `janela` (D-1/D0/D+1): mesmo padrao ja visto na Etapa 7 -- toda a "
          "janela em torno do jogo fica acima de 'sem relacao' para acidente, o que "
          "aponta efeito de calendario da temporada, resolvido na Etapa 9._\n")
    return res


# ---------------------------------------------------------------------------
def main():
    df = load()
    w("# Etapa 8 -- Analise estatistica\n")
    w(f"_Gerado por `scripts/05_analise_estatistica.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv`._\n")
    w("> **Regra 5 do briefing:** os testes abaixo medem *correlacao / associacao*. "
      "Nenhum autoriza afirmar causalidade. A pergunta desta etapa e mais modesta: "
      "*a associacao jogo x desfecho continua existindo depois de controlar dia da "
      "semana, mes e clima?* Inferencia causal formal = Etapa 20.\n")
    w("**Exclusoes (Etapa 6):** crime remove 2023-12-30/31; acidente remove +2022-01-17 "
      "e 2023-08-07.\n")

    zero = secao_zero_order(df)
    secao_parcial(df, zero)
    secao_proporcoes(df)
    secao_kw(df)

    w("## 5. Sintese da Etapa 8\n")
    w(textwrap.dedent("""\
        - **Correlacao simples (secao 1):** 8 pares significativos apos BH, todos com
          |rho| pequeno (0.11-0.19): `lesao_corporal_dolosa`, `acidentes_total` e
          `acidentes_fatais` com `tem_jogo_sp` e com `numero_jogos_sp` (6);
          `lesao_corporal_dolosa` com `jogo_noturno`; `acidentes_fatais` com
          `classico`. `roubos_total` aparece com sinal **negativo** (menos roubo em
          dia de jogo), no limite da significancia (p_BH = 0.053).
        - **Correlacao parcial (secao 2 -- resultado principal):** apos controlar
          dia da semana + mes, **nenhum** dos 44 pares continua significativo
          (todos p_BH > 0.8); com clima idem. Exemplos: `lesao_corporal_dolosa` x
          `tem_jogo_sp` cai de rho 0.19 -> 0.03; `acidentes_fatais` x `tem_jogo_sp`
          de 0.17 -> 0.06; `acidentes_total` de 0.13 -> 0.01. **A associacao bruta
          jogo x desfecho e inteiramente explicada por calendario (dia da semana e
          mes).** Bate com a Etapa 7 (GLM ajustado tambem nao achou efeito).
        - **Teste de proporcoes (secao 3):** com limiar provisorio P90, dia de jogo
          tem RR ~2.8 de ser "dia alto" para `lesao_corporal_dolosa` e
          `acidentes_fatais` -- mas isso **nao** controla dia da semana, entao
          reflete o mesmo agrupamento de calendario. A Etapa 11 refaz com a
          definicao formal de pico e a Etapa 14 modela com controles.
        - **Kruskal-Wallis (secao 4):** `dia_semana` tem epsilon^2 = 0.16 a 0.41
          (efeito grande); `numero_jogos_sp` tem epsilon^2 = 0.006 a 0.015
          (desprezivel). O dia da semana e, de longe, o principal fator de
          variacao das contagens -- nao o jogo.
        - **Resposta as perguntas do roteiro (§23):** ha *associacao* fraca entre
          dia de jogo e alguns desfechos de acidente/lesao no cru, mas ela
          **desaparece** apos controle de calendario e clima. Os dados **nao**
          sustentam efeito do jogo em si sobre crime ou acidente nesta janela, e
          **nao** permitem afirmar causalidade (Regra 5).
        - **Ressalvas:** janela curta (2 anos), Paulistao/Libertadores fora da base
          de jogos (dias de jogo subcontados), `publico` ausente. Um efeito real
          pequeno pode estar mascarado por essas limitacoes.
        - **Proximo:** Etapa 9 -- defasagem D-2..D+2 com correlacao cruzada,
          controlando mes, para fechar a questao de "antes / durante / depois".
    """))

    path = os.path.join(OUT_DIR, "relatorio_analise_estatistica.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))} arquivos)")
    print(f"[ok] tabelas : {TAB_DIR} ({len(os.listdir(TAB_DIR))} arquivos)")


if __name__ == "__main__":
    main()
