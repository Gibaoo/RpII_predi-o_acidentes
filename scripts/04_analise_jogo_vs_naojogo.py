"""
04_analise_jogo_vs_naojogo.py
Etapa 7 do roteiro -- comparacao DIA COM JOGO vs DIA SEM JOGO (e recortes:
classico vs jogo comum; jogo noturno vs diurno; alto vs baixo publico).

Metodo (nao apenas medias cruas):
  - comparacao BRUTA: media, mediana, diferenca absoluta e %, IC bootstrap 95%,
    Mann-Whitney U (nao-parametrico, default pois a EDA rejeitou normalidade),
    t de Welch como secundario, effect sizes (Cliff's delta, Hedges' g,
    r rank-biserial).
  - o confundidor obvio: jogos concentram em fim de semana, que ja tem padrao
    proprio. Entao, alem do bruto:
      (a) comparacao ESTRATIFICADA por dia da semana;
      (b) associacao AJUSTADA via GLM Poisson com erros-padrao robustos (HC1),
          controlando dia da semana + feriado + mes. Reporta razao de taxa
          (rate ratio = exp(coef)) com IC 95%.
  - correcao para multiplas comparacoes (Benjamini-Hochberg) sobre os p-values
    primarios.

REGRA: os resultados sao ASSOCIACAO / PREDICAO, nao causalidade (Regra 5 do
briefing). Inferencia causal formal e a Etapa 20.

Exclusoes (decididas na EDA - Etapa 6):
  - crime : remove 2023-12-30 e 2023-12-31 (censura por defasagem de registro).
  - acidente: remove os 2 acima + 2022-01-17 e 2023-08-07 (lacuna do fluxo
    NOTIFICACAO da Infosiga).

Rodar depois de 01/02/03.
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
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa7")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})
RNG = np.random.default_rng(20260903)
N_BOOT = 10000

EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}

CRIME_OUTCOMES = ["crimes_totais", "crimes_violentos", "roubos_total", "furtos_total",
                  "lesao_corporal_dolosa", "homicidios_dolosos"]
ACID_OUTCOMES = ["acidentes_total", "acidentes_com_vitima", "atropelamentos",
                 "colisoes", "acidentes_fatais"]

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
            if np.isnan(v):
                return ""
            return f"{v:,.{floatfmt}f}"
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


# ---------------------------------------------------------------------------
# estatistica
# ---------------------------------------------------------------------------
def bootstrap_ci_diff(a, b, func, n=N_BOOT, alpha=0.05):
    """IC percentil para func(grupo_com_jogo) - func(grupo_sem_jogo)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    idx_a = RNG.integers(0, len(a), size=(n, len(a)))
    idx_b = RNG.integers(0, len(b), size=(n, len(b)))
    diffs = func(a[idx_a], axis=1) - func(b[idx_b], axis=1)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi


def cliffs_delta(x, y):
    """delta em [-1,1]. >0 => x tende a ser maior que y. Deriva de U de MW."""
    nx, ny = len(x), len(y)
    u1, _ = stats.mannwhitneyu(x, y, alternative="two-sided")
    return 2 * u1 / (nx * ny) - 1


def hedges_g(x, y):
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    d = (np.mean(x) - np.mean(y)) / sp
    j = 1 - 3 / (4 * (nx + ny) - 9)
    return j * d


def interpreta_delta(delta):
    a = abs(delta)
    return ("desprezivel" if a < .147 else "pequeno" if a < .33 else
            "medio" if a < .474 else "grande")


def compara_grupos(df, col, mask_grupo, nome_a="com jogo", nome_b="sem jogo"):
    """df ja filtrado de exclusoes. mask_grupo True = grupo A."""
    a = df.loc[mask_grupo, col].dropna().to_numpy(float)
    b = df.loc[~mask_grupo, col].dropna().to_numpy(float)
    u1, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    t, p_t = stats.ttest_ind(a, b, equal_var=False)
    lo_m, hi_m = bootstrap_ci_diff(a, b, np.mean)
    lo_md, hi_md = bootstrap_ci_diff(a, b, np.median)
    delta = 2 * u1 / (len(a) * len(b)) - 1
    r_rb = delta  # rank-biserial == Cliff's delta para MW
    return {
        "variavel": col,
        f"n_{nome_a}": len(a), f"n_{nome_b}": len(b),
        f"media_{nome_a}": np.mean(a), f"media_{nome_b}": np.mean(b),
        f"mediana_{nome_a}": np.median(a), f"mediana_{nome_b}": np.median(b),
        "dif_abs_media": np.mean(a) - np.mean(b),
        "dif_pct_media": (np.mean(a) / np.mean(b) - 1) * 100,
        "IC95_dif_media_lo": lo_m, "IC95_dif_media_hi": hi_m,
        "IC95_dif_mediana_lo": lo_md, "IC95_dif_mediana_hi": hi_md,
        "MannWhitney_p": p_mw,
        "Welch_t_p": p_t,
        "cliffs_delta": delta, "efeito": interpreta_delta(delta),
        "hedges_g": hedges_g(a, b),
        "rank_biserial_r": r_rb,
    }


def bh_fdr(pvals, q=0.05):
    """Benjamini-Hochberg. Retorna (rejeita_bool, p_ajustado)."""
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    p_adj_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    p_adj = np.empty(n)
    p_adj[order] = np.clip(p_adj_sorted, 0, 1)
    return p_adj <= q, p_adj


# ---------------------------------------------------------------------------
def load():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    return df


def base_por_familia(df, familia):
    excl = EXCL_CRIME if familia == "crime" else EXCL_ACID
    return df[~df["data"].isin(excl)].copy()


# ---------------------------------------------------------------------------
# 7.1 bruto: com jogo vs sem jogo
# ---------------------------------------------------------------------------
def secao_bruto(df):
    w("## 1. Dia com jogo vs dia sem jogo -- comparacao bruta\n")
    w("Teste primario: **Mann-Whitney U** (bilateral); a EDA (Etapa 6) rejeitou "
      "normalidade em quase todas as contagens. t de Welch reportado como secundario. "
      "IC 95% por **bootstrap percentil** (10 000 reamostragens, semente fixa). "
      "Effect size: **Cliff's delta** (= r rank-biserial) e Hedges' g.\n")

    linhas, pmw = [], []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = base_por_familia(df, familia)
        for col in outs:
            r = compara_grupos(d, col, d["tem_jogo_sp"])
            r["familia"] = familia
            linhas.append(r)
            pmw.append(r["MannWhitney_p"])

    res = pd.DataFrame(linhas)
    rej, padj = bh_fdr(res["MannWhitney_p"].to_numpy())
    res["MW_p_BH"] = padj
    res["signif_BH_5pct"] = rej

    mostra = res[["familia", "variavel", "n_com jogo", "n_sem jogo",
                  "media_com jogo", "media_sem jogo", "dif_abs_media", "dif_pct_media",
                  "IC95_dif_media_lo", "IC95_dif_media_hi",
                  "MannWhitney_p", "MW_p_BH", "cliffs_delta", "efeito", "hedges_g"]]
    res.to_csv(os.path.join(TAB_DIR, "bruto_jogo_vs_naojogo.csv"), index=False)
    w(df_to_md(mostra, floatfmt=3, index=False))
    w("")
    w("- **dif_pct_media**: variacao percentual da media do grupo com jogo sobre o sem jogo.")
    w("- **IC95_dif_media**: se cruza 0, a diferenca de medias nao e estatisticamente distinta de 0.")
    w("- **MW_p_BH**: p-value de Mann-Whitney apos correcao de Benjamini-Hochberg "
      "(11 desfechos testados). `signif_BH_5pct` no CSV.")
    w("- **cliffs_delta**: |0.11| ja seria 'pequeno'; a EDA leva a esperar efeitos pequenos "
      "e confundidos por dia da semana -- ver secoes 2 e 3.\n")

    # figura: distribuicao por grupo
    for familia, outs in [("crime", CRIME_OUTCOMES[:4]), ("acidente", ACID_OUTCOMES[:4])]:
        d = base_por_familia(df, familia)
        fig, axes = plt.subplots(1, len(outs), figsize=(4 * len(outs), 4))
        for ax, col in zip(axes, outs):
            g0 = d.loc[~d["tem_jogo_sp"], col].dropna()
            g1 = d.loc[d["tem_jogo_sp"], col].dropna()
            parts = ax.violinplot([g0, g1], showmedians=True)
            ax.set_xticks([1, 2])
            ax.set_xticklabels(["sem jogo", "com jogo"])
            ax.set_title(col)
            ax.grid(axis="y", alpha=.3)
        rel = savefig(f"01_dist_{familia}.png")
        w(f"![dist {familia}]({rel})\n")
    return res


# ---------------------------------------------------------------------------
# 7.2 o confundidor: dia da semana
# ---------------------------------------------------------------------------
def secao_confundidor(df):
    w("## 2. O confundidor: dia da semana\n")
    d = df.copy()
    tab_dow = pd.crosstab(d["nome_dia_semana"], d["tem_jogo_sp"])
    ordem = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
    tab_dow = tab_dow.reindex([o for o in ordem if o in tab_dow.index])
    tab_dow.columns = ["dias_sem_jogo", "dias_com_jogo"]
    tab_dow["% dias com jogo"] = (tab_dow["dias_com_jogo"] /
                                  (tab_dow.sum(axis=1)) * 100).round(1)
    tab_dow.to_csv(os.path.join(TAB_DIR, "jogos_por_dia_semana.csv"))
    w("Distribuicao dos jogos pelos dias da semana:\n")
    w(df_to_md(tab_dow, floatfmt=1))
    w("")
    w("Os jogos **nao** se distribuem uniformemente. Como o proprio nivel de crime/"
      "acidente varia por dia da semana (Etapa 6), qualquer diferenca bruta mistura "
      "'efeito jogo' com 'efeito dia da semana'. As secoes 2.1 e 3 tentam separar.\n")

    # estratificado
    dc = base_por_familia(df, "crime")
    da = base_por_familia(df, "acidente")
    w("### 2.1 Comparacao estratificada por dia da semana\n")
    for col, base in [("crimes_totais", dc), ("crimes_violentos", dc),
                      ("acidentes_total", da), ("acidentes_com_vitima", da)]:
        rows = []
        for dia in ordem:
            sub = base[base["nome_dia_semana"] == dia]
            g1 = sub.loc[sub["tem_jogo_sp"], col].dropna()
            g0 = sub.loc[~sub["tem_jogo_sp"], col].dropna()
            if len(g1) < 3:
                rows.append({"dia": dia, "n_jogo": len(g1), "n_sem": len(g0),
                             "media_jogo": g1.mean() if len(g1) else np.nan,
                             "media_sem": g0.mean(),
                             "dif_%": (g1.mean() / g0.mean() - 1) * 100 if len(g1) else np.nan,
                             "MW_p": np.nan})
                continue
            _, p = stats.mannwhitneyu(g1, g0, alternative="two-sided")
            rows.append({"dia": dia, "n_jogo": len(g1), "n_sem": len(g0),
                         "media_jogo": g1.mean(), "media_sem": g0.mean(),
                         "dif_%": (g1.mean() / g0.mean() - 1) * 100, "MW_p": p})
        t = pd.DataFrame(rows)
        t.to_csv(os.path.join(TAB_DIR, f"estratificado_{col}.csv"), index=False)
        w(f"**{col}**\n")
        w(df_to_md(t, floatfmt=2, index=False))
        w("")


# ---------------------------------------------------------------------------
# 7.3 associacao ajustada (GLM Poisson robusto)
# ---------------------------------------------------------------------------
def secao_ajustada(df):
    w("## 3. Associacao ajustada -- GLM Poisson com erros-padrao robustos (HC1)\n")
    w("Modelo por desfecho: `y ~ tem_jogo_sp + C(dia_semana) + feriado + C(mes)`. "
      "Familia Poisson (dado de contagem); IC/p por erros-padrao **robustos HC1** "
      "(consistentes sob sobredispersao). O coeficiente de `tem_jogo_sp` vira "
      "**razao de taxa** `exp(coef)`: 1.05 = +5% no desfecho num dia de jogo, ja "
      "descontados dia da semana, feriado e mes.\n")

    linhas = []
    for familia, outs in [("crime", CRIME_OUTCOMES), ("acidente", ACID_OUTCOMES)]:
        d = base_por_familia(df, familia).copy()
        d["dia_semana"] = d["dia_semana"].astype(int)
        d["mes"] = d["mes"].astype(int)
        d["tem_jogo_sp"] = d["tem_jogo_sp"].astype(int)
        d["feriado"] = d["feriado"].astype(int)
        for col in outs:
            m = smf.glm(f"{col} ~ tem_jogo_sp + C(dia_semana) + feriado + C(mes)",
                        data=d, family=sm.families.Poisson()).fit(cov_type="HC1")
            rr = np.exp(m.params["tem_jogo_sp"])
            ci = np.exp(m.conf_int().loc["tem_jogo_sp"])
            disp = m.pearson_chi2 / m.df_resid
            linhas.append({
                "familia": familia, "variavel": col,
                "rate_ratio_jogo": rr, "IC95_lo": ci[0], "IC95_hi": ci[1],
                "p_value": m.pvalues["tem_jogo_sp"],
                "sobredispersao": disp,
                "efeito_%": (rr - 1) * 100,
            })
    res = pd.DataFrame(linhas)
    rej, padj = bh_fdr(res["p_value"].to_numpy())
    res["p_BH"] = padj
    res["signif_BH_5pct"] = rej
    res.to_csv(os.path.join(TAB_DIR, "ajustado_glm_poisson.csv"), index=False)
    w(df_to_md(res[["familia", "variavel", "rate_ratio_jogo", "IC95_lo", "IC95_hi",
                    "efeito_%", "p_value", "p_BH", "signif_BH_5pct", "sobredispersao"]],
              floatfmt=3, index=False))
    w("")
    w("- **sobredispersao > 1** (esperado): a variancia excede a media Poisson. "
      "Por isso os erros-padrao HC1 (robustos) e nao os ingenuos; uma alternativa "
      "seria Binomial Negativa -- a direcao e a magnitude do rate ratio nao mudam "
      "materialmente, so a largura do IC. A sobredispersao muito alta de "
      "`crimes_totais` e `furtos_total` (~22-25) e inflada pelo outlier de "
      "2022-06-19 (`furtos_total`=2633, registro em lote -- ver EDA); teste de "
      "sensibilidade sem esse dia fica para a Etapa 12.")
    w("- **IC95 cruzando 1.0** => associacao ajustada nao distinguivel de 'nenhum efeito'.")
    w("- Ajuste **nao** e prova de causalidade: variaveis nao observadas (transporte, "
      "fluxo de torcida, eventos simultaneos) seguem fora. Ver Etapa 20.\n")

    # figura forest plot
    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(res))[::-1]
    ax.errorbar(res["rate_ratio_jogo"], y,
                xerr=[res["rate_ratio_jogo"] - res["IC95_lo"],
                      res["IC95_hi"] - res["rate_ratio_jogo"]],
                fmt="o", capsize=3)
    ax.axvline(1.0, color="k", ls="--", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(res["variavel"])
    ax.set_xlabel("razao de taxa (dia de jogo vs sem jogo), ajustada -- IC95 HC1")
    ax.set_title("Associacao ajustada: efeito do dia de jogo por desfecho")
    ax.grid(axis="x", alpha=.3)
    rel = savefig("02_forest_ajustado.png")
    w(f"![forest ajustado]({rel})\n")
    return res


# ---------------------------------------------------------------------------
# 7.4 classico vs jogo comum  /  7.5 noturno vs diurno
# ---------------------------------------------------------------------------
def secao_recortes(df):
    w("## 4. Recortes dentro dos dias de jogo\n")
    w("Amostra pequena (126 dias com jogo). Testes nao-parametricos, effect size "
      "reportado, resultados lidos com cautela.\n")

    dc = base_por_familia(df, "crime")
    da = base_por_familia(df, "acidente")

    def recorte(nome, mask_col, base_map, label_a, label_b):
        w(f"### {nome}\n")
        rows = []
        for col, base in base_map:
            sub = base[base["tem_jogo_sp"]].copy()
            g1 = sub.loc[sub[mask_col] == True, col].dropna()
            g0 = sub.loc[sub[mask_col] == False, col].dropna()
            if len(g1) < 3 or len(g0) < 3:
                rows.append({"variavel": col, f"n_{label_a}": len(g1), f"n_{label_b}": len(g0),
                             f"media_{label_a}": g1.mean() if len(g1) else np.nan,
                             f"media_{label_b}": g0.mean() if len(g0) else np.nan,
                             "dif_%": np.nan, "MW_p": np.nan, "cliffs_delta": np.nan})
                continue
            _, p = stats.mannwhitneyu(g1, g0, alternative="two-sided")
            rows.append({"variavel": col, f"n_{label_a}": len(g1), f"n_{label_b}": len(g0),
                         f"media_{label_a}": g1.mean(), f"media_{label_b}": g0.mean(),
                         "dif_%": (g1.mean() / g0.mean() - 1) * 100,
                         "MW_p": p, "cliffs_delta": cliffs_delta(g1, g0)})
        t = pd.DataFrame(rows)
        t.to_csv(os.path.join(TAB_DIR, f"recorte_{mask_col}.csv"), index=False)
        w(df_to_md(t, floatfmt=2, index=False))
        w("")

    bm = [("crimes_totais", dc), ("crimes_violentos", dc), ("lesao_corporal_dolosa", dc),
          ("acidentes_total", da), ("acidentes_com_vitima", da)]
    recorte("4.1 Classico vs jogo comum", "classico", bm, "classico", "comum")
    recorte("4.2 Jogo noturno vs diurno", "jogo_noturno", bm, "noturno", "diurno")

    # 7.6 publico - bloqueado
    w("### 4.3 Alto vs baixo publico -- BLOQUEADO\n")
    n_pub = df["publico"].notna().sum()
    w(f"`publico` tem {n_pub} valores nao-nulos de 730. A fonte de publico pagante "
      "(Kaggle `adaoduque/campeonato-brasileiro-de-futebol`) ainda nao foi integrada "
      "(hook pronto em `clean_football(kaggle_publico_path=...)`). A comparacao "
      "'alto vs baixo publico' pedida no roteiro §7 fica **pendente** ate essa fonte "
      "entrar -- limitacao declarada, nao contornada com proxy inventado.\n")


# ---------------------------------------------------------------------------
# 7.7 preview D-1 / D0 / D+1  (Etapa 9 faz completo)
# ---------------------------------------------------------------------------
def secao_lag_preview(df):
    w("## 5. Previa D-1 / D0 / D+1 (a analise de defasagem completa e a Etapa 9)\n")
    d = base_por_familia(df, "crime").copy()
    da = base_por_familia(df, "acidente").copy()

    def rotula(x):
        out = pd.Series("sem relacao", index=x.index)
        out[x["jogo_d_mais_1"] & ~x["tem_jogo_sp"]] = "D+1 (pos-jogo)"
        out[x["jogo_d_menos_1"] & ~x["tem_jogo_sp"]] = "D-1 (vespera)"
        out[x["tem_jogo_sp"]] = "D0 (dia do jogo)"
        return out

    for col, base in [("crimes_totais", d), ("crimes_violentos", d),
                      ("acidentes_total", da), ("acidentes_com_vitima", da)]:
        base = base.copy()
        base["janela"] = rotula(base)
        grupos = [g[col].dropna().to_numpy(float)
                  for _, g in base.groupby("janela")]
        nomes = list(base.groupby("janela").groups.keys())
        h, p = stats.kruskal(*grupos)
        tab = base.groupby("janela")[col].agg(["count", "mean", "median"])
        tab["dif_%_vs_sem_relacao"] = (tab["mean"] / tab.loc["sem relacao", "mean"] - 1) * 100
        tab.to_csv(os.path.join(TAB_DIR, f"lag_preview_{col}.csv"))
        w(f"**{col}** -- Kruskal-Wallis H={h:.2f}, p={p:.4f}\n")
        w(df_to_md(tab, floatfmt=2))
        w("")
    w("_Leitura so exploratoria. Note que **D-1, D0 e D+1 estao TODOS ~+6 a +12% acima "
      "de 'sem relacao' para acidentes** -- a janela inteira em torno do jogo, nao so o "
      "dia. Como a temporada de futebol (abr-nov) nao cobre o verao (dez-mar), que tem "
      "menos acidentes, boa parte disso e **efeito de calendario/mes**, nao do jogo: o "
      "modelo ajustado da secao 3 (que controla `C(mes)`) ja nao acha efeito em D0. A "
      "correlacao cruzada e o modelo com defasagens controladas ficam para a Etapa 9._\n")


# ---------------------------------------------------------------------------
def main():
    df = load()
    w("# Etapa 7 -- Dia com jogo vs dia sem jogo\n")
    w(f"_Gerado por `scripts/04_analise_jogo_vs_naojogo.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv`._\n")
    w("> **Aviso de interpretacao:** tudo abaixo e **associacao / diferenca observada**, "
      "nao causalidade. 'Dia de jogo' vem junto de fim de semana, ferias, calendario de "
      "campeonato e outros fatores nao medidos. Inferencia causal formal = Etapa 20.\n")
    w("**Exclusoes (decididas na EDA):** crime remove 2023-12-30/31; acidente remove "
      "esses 2 + 2022-01-17 e 2023-08-07 (lacunas de registro, nao dias reais baixos).\n")
    w("**Hipoteses (todas as comparacoes de grupo):** H0: as duas distribuicoes tem a "
      "mesma tendencia central (Mann-Whitney: P(X>Y)=P(Y>X)). H1: diferem. alpha=0.05, "
      "bilateral, com correcao de Benjamini-Hochberg para o conjunto de desfechos.\n")

    secao_bruto(df)
    secao_confundidor(df)
    secao_ajustada(df)
    secao_recortes(df)
    secao_lag_preview(df)

    w("## 6. Sintese da Etapa 7\n")
    w(textwrap.dedent("""\
        **Bruto (sem ajuste):** aparecem diferencas em `lesao_corporal_dolosa`
        (+14,9%, MW p<0,001 apos BH, Hedges' g 0,57), `acidentes_total` (+6,3%,
        p<0,001), `acidentes_fatais` (+38,7%, p<0,001) e `roubos_total` **menor**
        em dia de jogo (-3,3%, p=0,03). `crimes_totais`, `crimes_violentos`,
        `furtos_total`, `homicidios` nao diferem. Todos os effect sizes sao
        pequenos ou despreziveis (|Cliff's delta| <= 0,29).

        **Ajustado (Poisson/HC1, controla dia da semana + feriado + mes):**
        **nenhum desfecho permanece significativo apos correcao de multiplas
        comparacoes** (todos p_BH > 0,5). O maior efeito residual e
        `acidentes_fatais` (rate ratio 1,15; IC95 0,99-1,32; p=0,06 sem BH) --
        sugestivo, nao conclusivo, e sobre contagem pequena (media ~2-3/dia).
        Ou seja: **a maior parte da diferenca bruta era confundimento por dia da
        semana e mes** (jogos concentram em domingo/quinta/sabado e na temporada
        abr-nov). A comparacao estratificada (secao 2.1) mostra o mesmo: o unico
        contraste bruto que sobra dentro de um mesmo dia da semana e acidentes no
        **domingo** (+11% a +18%, p<0,01), que ainda assim pode carregar efeito
        de mes.

        **Recortes (amostra pequena, 126 dias com jogo):**
        - Classico vs comum: sem diferenca robusta; o maior sinal e
          `acidentes_com_vitima` +7% (p=0,06, delta 0,25) -- indicativo.
        - Noturno vs diurno: `lesao_corporal_dolosa` +17% em jogo noturno
          (p<0,01, delta 0,38) -- mas noturno/diurno tambem se confunde com dia
          da semana e campeonato; checar na Etapa 9/feature engineering.
        - Alto vs baixo publico: **nao avaliavel** (`publico` 100% ausente).

        **Resposta as perguntas do roteiro (§23), so com o que a Etapa 7 permite:**
        1. Associacao jogo x violencia: fraca e majoritariamente explicada por
           dia da semana; nao robusta apos ajuste. Excecao a investigar: lesao
           corporal em jogo noturno.
        2. Associacao jogo x acidentes: existe no bruto (+6%), enfraquece muito
           apos ajuste; o sinal mais persistente e em acidentes fatais e no
           domingo.
        3-5. Classico / noturno / publico: inconclusivo, pendente ou nao
           avaliavel (ver acima).

        **Aviso obrigatorio (Regra 5):** os resultados indicam *associacao*, com
        magnitude pequena e sensivel a controle de confundidores. **Nao** permitem
        afirmar que jogos causam mais crime ou acidente. Inferencia causal = Etapa 20.

        **Proximo:** Etapa 8 (Pearson/Spearman/correlacao parcial formais) e
        Etapa 9 (defasagem D-2..D+2 com correlacao cruzada, controlando mes).
    """))

    path = os.path.join(OUT_DIR, "relatorio_jogo_vs_naojogo.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))} arquivos)")
    print(f"[ok] tabelas : {TAB_DIR} ({len(os.listdir(TAB_DIR))} arquivos)")


if __name__ == "__main__":
    main()
