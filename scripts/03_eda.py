"""
03_eda.py
Etapa 6 do roteiro - Analise Exploratoria de Dados (EDA) do dataset analitico
final data/gold/fato_dia_sp.csv (1 linha = 1 dia, SP capital, 2022-2023).

Nao modela nada aqui. Objetivo: qualidade, estatistica descritiva, distribuicoes
e series temporais - exatamente os 4 blocos da Secao 6 do briefing. Comparacao
formal jogo vs nao-jogo (testes de hipotese) fica para a Etapa 7 (04_*).

Saidas:
  reports/eda/eda_report.md      - relatorio em markdown com todas as tabelas
  reports/eda/figures/*.png      - figuras (series temporais, distribuicoes, etc.)
  reports/eda/tabelas/*.csv      - tabelas exportadas para reuso

Rodar depois de 01_ingestao.py e 02_limpeza.py.
"""
import os
import textwrap
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from statsmodels.graphics.tsaplots import plot_acf
    HAS_SM = True
except Exception:
    HAS_SM = False

from scipy import stats

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "eda")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

# alvos principais do estudo (contagens diarias)
ALVOS_CRIME = ["crimes_totais", "bos_unicos", "crimes_violentos", "homicidios_dolosos",
               "tentativas_homicidio", "lesao_corporal_dolosa", "roubos_total",
               "roubo_veiculo", "furtos_total", "furto_veiculo", "estupros"]
ALVOS_ACIDENTE = ["acidentes_total", "acidentes_com_vitima", "acidentes_fatais",
                  "obitos_transito", "feridos_transito", "atropelamentos", "colisoes"]
CLIMA = ["temp_media", "temp_max", "temp_min", "precipitacao_total", "umidade_media", "vento_max"]

# lacunas ja conhecidas (CLAUDE.md) - a EDA deve confirma-las, nao descobri-las do zero
GAPS_CONHECIDOS = [
    ("2023-11-27", "2023-11-27", "INMET sem nenhuma leitura (falha de estacao)"),
    ("2023-08-25", "2023-09-11", "sensor de precipitacao do INMET fora do ar (temp ok, chuva NaN)"),
    ("2023-12-30", "2023-12-31", "censura no fim da serie: contagens de crime/acidente artificialmente baixas (defasagem de registro)"),
]

_md = []


def w(line=""):
    _md.append(line)


def df_to_md(df, floatfmt=3, index=True):
    """markdown table sem depender de 'tabulate'."""
    d = df.copy()
    if index:
        d = d.reset_index()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, float) or isinstance(v, (np.floating,)):
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
def load_gold():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"])
    df = df.sort_values("data").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 6.1 QUALIDADE
# ---------------------------------------------------------------------------
def secao_qualidade(df):
    w("## 1. Qualidade dos dados\n")

    dmin, dmax = df["data"].min(), df["data"].max()
    n_esperado = (dmax - dmin).days + 1
    grade_completa = pd.date_range(dmin, dmax, freq="D")
    faltando = grade_completa.difference(df["data"])

    w(f"- Linhas: **{len(df)}** | Colunas: **{df.shape[1]}**")
    w(f"- Intervalo: **{dmin.date()} a {dmax.date()}** ({n_esperado} dias no calendario)")
    w(f"- Dias ausentes na grade diaria: **{len(faltando)}** "
      + ("" if len(faltando) == 0 else f"({', '.join(str(x.date()) for x in faltando[:10])}...)"))
    w(f"- Datas duplicadas: **{int(df['data'].duplicated().sum())}**")
    w(f"- Linhas totalmente duplicadas: **{int(df.duplicated().sum())}**")
    w("")

    # ---- missing values ----
    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    miss_tab = pd.DataFrame({"n_missing": miss, "pct": (miss / len(df) * 100).round(2)})
    miss_tab.index.name = "coluna"
    miss_tab.to_csv(os.path.join(TAB_DIR, "missing_values.csv"))
    w("### 1.1 Valores ausentes (colunas com pelo menos 1 NaN)\n")
    if len(miss_tab):
        w(df_to_md(miss_tab, floatfmt=2))
        w("")
        w(textwrap.dedent("""\
            Leitura esperada (ver `CLAUDE.md`):
            - Colunas de **futebol** (`mandante`, `visitante`, `publico`, `taxa_ocupacao`, ...):
              NaN em todo dia sem jogo -- isso e *ausencia de evento*, nao falha de dado.
              `publico`/`taxa_ocupacao` sao NaN em 100% das linhas (fonte de publico ainda nao integrada).
            - Colunas de **crime/acidente**: NaN aqui indicaria falha de ingestao. Esperado 0.
            - Colunas de **clima**: NaN concentrado nas lacunas conhecidas do INMET.
            - `pico_*` e `nivel_risco`: placeholders vazios de proposito (definidos na Etapa 11)."""))
    else:
        w("Nenhum valor ausente.")
    w("")

    # ---- lacunas de clima conhecidas ----
    w("### 1.2 Lacunas de clima conhecidas -- confirmacao\n")
    linhas = []
    for ini, fim, desc in GAPS_CONHECIDOS:
        janela = df[(df["data"] >= ini) & (df["data"] <= fim)]
        linhas.append({
            "janela": f"{ini} a {fim}", "descricao": desc,
            "temp_media_NaN": int(janela["temp_media"].isna().sum()),
            "precipitacao_NaN": int(janela["precipitacao_total"].isna().sum()),
            "n_dias": len(janela),
        })
    w(df_to_md(pd.DataFrame(linhas), index=False))
    w("")

    # ---- valores impossiveis / inconsistencias ----
    w("### 1.3 Valores impossiveis e inconsistencias\n")
    checks = []

    def chk(nome, mask):
        n = int(mask.sum())
        exemplos = ", ".join(str(x.date()) for x in df.loc[mask, "data"].head(5))
        checks.append({"checagem": nome, "n_dias": n, "exemplos": exemplos})

    cont_cols = [c for c in ALVOS_CRIME + ALVOS_ACIDENTE if c in df.columns]
    chk("alguma contagem de crime/acidente negativa", (df[cont_cols] < 0).any(axis=1))
    chk("temp_min > temp_max", df["temp_min"] > df["temp_max"])
    chk("temp_media fora de [temp_min, temp_max]",
        (df["temp_media"] < df["temp_min"]) | (df["temp_media"] > df["temp_max"]))
    chk("umidade_media fora de [0, 100]", (df["umidade_media"] < 0) | (df["umidade_media"] > 100))
    chk("precipitacao_total negativa", df["precipitacao_total"] < 0)
    chk("vento_max negativo", df["vento_max"] < 0)
    if "taxa_ocupacao" in df.columns:
        chk("taxa_ocupacao > 1 (publico > capacidade)", df["taxa_ocupacao"] > 1)
    chk("tem_jogo_sp=True mas numero_jogos_sp=0",
        (df["tem_jogo_sp"]) & (df["numero_jogos_sp"] == 0))
    chk("tem_jogo_sp=False mas mandante preenchido",
        (~df["tem_jogo_sp"]) & (df["mandante"].notna()))
    chk("classico=True mas tem_jogo_sp=False", (df["classico"]) & (~df["tem_jogo_sp"]))
    w(df_to_md(pd.DataFrame(checks), index=False))
    w("")

    # ---- outliers ----
    w("### 1.4 Outliers (metodo IQR e z-score) nas contagens principais\n")
    alvo_out = [c for c in ["crimes_totais", "crimes_violentos", "roubos_total", "furtos_total",
                            "acidentes_total", "acidentes_com_vitima", "atropelamentos", "colisoes"]
                if c in df.columns]
    rows = []
    for c in alvo_out:
        s = df[c].dropna()
        q1, q3 = s.quantile(.25), s.quantile(.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        z = (s - s.mean()) / s.std(ddof=0)
        rows.append({
            "coluna": c, "min": s.min(), "max": s.max(),
            "lim_inf_IQR": round(lo, 1), "lim_sup_IQR": round(hi, 1),
            "n_out_IQR": int(((s < lo) | (s > hi)).sum()),
            "n_out_z>3": int((z.abs() > 3).sum()),
        })
    w(df_to_md(pd.DataFrame(rows), index=False))
    w("")
    w("_Nota: contagens diarias de crime tem forte sazonalidade semanal; um 'outlier' "
      "IQR marginal pode ser so o efeito de dia da semana, nao um ponto anomalo real. "
      "A remocao (se houver) e decidida na Etapa 12, nao aqui._")
    w("")

    # ---- dias com contagem anormalmente baixa (identifica a censura concretamente) ----
    w("### 1.4b Dias nos extremos -- checagem de censura, lacuna e registro em lote\n")
    dd = df.copy()
    dd["frac_com_vitima"] = dd["acidentes_com_vitima"] / dd["acidentes_total"]
    for col, extra in [("crimes_totais", []), ("acidentes_total", ["frac_com_vitima"])]:
        low = dd.nsmallest(6, col)[["data", col, "nome_dia_semana", "feriado", "tem_jogo_sp"] + extra].copy()
        low["data"] = low["data"].dt.date
        w(f"**{col}** (6 menores):\n")
        w(df_to_md(low, index=False, floatfmt=2))
        w("")
        low.to_csv(os.path.join(TAB_DIR, f"extremos_{col}_menores.csv"), index=False)
    w("**crimes_totais** (6 maiores):\n")
    hi = df.nlargest(6, "crimes_totais")[["data", "crimes_totais", "furtos_total",
         "roubos_total", "crimes_violentos", "nome_dia_semana", "feriado", "tem_jogo_sp"]].copy()
    hi["data"] = hi["data"].dt.date
    w(df_to_md(hi, index=False, floatfmt=0))
    hi.to_csv(os.path.join(TAB_DIR, "extremos_crimes_totais_maiores.csv"), index=False)
    w("")
    w(textwrap.dedent("""\
        Leitura:
        - **crimes_totais (maiores)**: `2022-06-19` (3371) e um ponto muito acima dos demais,
          puxado por `furtos_total`=2633 (mediana ~780). Pico isolado desse tamanho num unico
          domingo sugere registro em lote / efeito de mutirao de BOs, nao um dia real 3x mais
          violento. Nao remover agora -- sinalizar e reavaliar na Etapa 12 (a definicao de
          'pico' da Etapa 11 nao pode ser dominada por 1 artefato). Os demais dias no topo
          sao fins de semana (com e sem jogo), coerente com a sazonalidade semanal.
        - **crimes_totais (menores)**: `2023-12-31` (161) e `2023-12-30` (554) sao os dois
          menores e nao sao feriado -> confirmam a censura por defasagem de registro no fim
          da serie ja anotada no `CLAUDE.md`. `2023-12-25` e `2022-12-25` sao Natal (queda real).
        - **acidentes_total (menores)**: `2022-01-17` (7) e `2023-08-07` (24) sao segundas
          comuns, sem feriado, cercadas de dias ~110-150. Em ambos `frac_com_vitima` ~= 1.0
          (tipico ~0.65): o fluxo so-dano-material (`tipo_registro = NOTIFICACAO`) nao entrou
          nesses dias. E lacuna de registro da fonte Infosiga, nao reducao real -- adicionada
          agora ao `CLAUDE.md`. Tratar `acidentes_total`/`colisoes` desses 2 dias como
          missing (nao zero) na Etapa 12.
        - `2023-12-31` tambem aparece no fundo de acidentes (61); `2023-12-30` nao, entao a
          censura de fim de serie pesa mais no crime do que no acidente."""))
    w("")

    # ---- distribuicao temporal ----
    w("### 1.5 Distribuicao temporal (contagem de dias e volume por mes)\n")
    tmp = df.copy()
    tmp["ano_mes"] = tmp["data"].dt.to_period("M").astype(str)
    dist = tmp.groupby("ano_mes").agg(
        n_dias=("data", "size"),
        crimes_totais=("crimes_totais", "sum"),
        acidentes_total=("acidentes_total", "sum"),
        dias_com_jogo=("tem_jogo_sp", "sum"),
    )
    dist.to_csv(os.path.join(TAB_DIR, "distribuicao_temporal_mensal.csv"))
    w(df_to_md(dist, floatfmt=0))
    w("")

    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax[0].bar(dist.index, dist["crimes_totais"], color="#b5651d")
    ax[0].set_title("Volume mensal de crimes_totais (SP capital)")
    ax[1].bar(dist.index, dist["acidentes_total"], color="#1f6f8b")
    ax[1].set_title("Volume mensal de acidentes_total (SP capital)")
    for a in ax:
        a.tick_params(axis="x", rotation=90)
        a.grid(axis="y", alpha=.3)
    rel = savefig("01_volume_mensal.png")
    w(f"![volume mensal]({rel})\n")

    return {"faltando": faltando, "dist_mensal": dist}


# ---------------------------------------------------------------------------
# 6.2 ESTATISTICA DESCRITIVA
# ---------------------------------------------------------------------------
def secao_descritiva(df):
    w("## 2. Estatistica descritiva\n")
    cols = [c for c in ALVOS_CRIME + ALVOS_ACIDENTE + CLIMA if c in df.columns]

    def resumo(s):
        s = s.dropna()
        media = s.mean()
        return pd.Series({
            "n": int(s.size), "media": media, "mediana": s.median(),
            "desvio_padrao": s.std(ddof=1), "min": s.min(),
            "q25": s.quantile(.25), "q50": s.quantile(.5), "q75": s.quantile(.75),
            "max": s.max(),
            "coef_variacao": (s.std(ddof=1) / media) if media else np.nan,
            "assimetria": stats.skew(s), "curtose": stats.kurtosis(s),
        })

    tab = df[cols].apply(resumo).T
    tab.to_csv(os.path.join(TAB_DIR, "estatistica_descritiva.csv"))
    w(df_to_md(tab, floatfmt=3))
    w("")
    w(textwrap.dedent("""\
        - **Coeficiente de variacao (CV = desvio/media)**: quanto maior, mais volatil a
          contagem. Contagens raras (homicidios, latrocinio, acidentes fatais) tem CV alto
          e distribuicao muito assimetrica -- favorece modelagem de contagem
          (Poisson/Neg. Binomial) e nao regressao gaussiana ingenua.
        - **Assimetria > 0** em quase todas as contagens: cauda a direita, esperado para
          dados de ocorrencias. Sera relevante na escolha de teste (Etapa 7) e transformacao."""))
    w("")

    # descritiva rapida jogo vs nao-jogo (SEM teste - so leitura preliminar)
    w("### 2.1 Leitura preliminar: dia com jogo vs dia sem jogo (apenas descritivo)\n")
    grp = df.groupby("tem_jogo_sp")
    prelim = grp[["crimes_totais", "crimes_violentos", "acidentes_total",
                  "acidentes_com_vitima"]].agg(["mean", "median", "std", "count"]).T
    w(df_to_md(prelim, floatfmt=2))
    w("")
    w("_A comparacao formal (intervalo de confianca, Mann-Whitney/t-test, effect size, "
      "controle de dia da semana e feriado) e a Etapa 7. Aqui e so panorama._")
    w("")
    return tab


# ---------------------------------------------------------------------------
# 6.3 DISTRIBUICOES
# ---------------------------------------------------------------------------
def secao_distribuicoes(df):
    w("## 3. Distribuicoes\n")

    alvos = [c for c in ["crimes_totais", "crimes_violentos", "roubos_total", "furtos_total",
                         "acidentes_total", "acidentes_com_vitima", "atropelamentos", "colisoes"]
             if c in df.columns]
    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    for ax, c in zip(axes.ravel(), alvos):
        s = df[c].dropna()
        ax.hist(s, bins=30, color="#4c72b0", edgecolor="white")
        ax.axvline(s.mean(), color="red", ls="--", lw=1, label=f"media {s.mean():.0f}")
        ax.axvline(s.median(), color="k", ls=":", lw=1, label=f"mediana {s.median():.0f}")
        ax.set_title(c)
        ax.legend(fontsize=7)
    for ax in axes.ravel()[len(alvos):]:
        ax.axis("off")
    rel = savefig("02_hist_contagens.png")
    w(f"### 3.1 Crimes e acidentes\n\n![histogramas]({rel})\n")

    # normalidade (D'Agostino-Pearson) - so informativo
    rows = []
    for c in alvos:
        s = df[c].dropna()
        try:
            k2, p = stats.normaltest(s)
        except Exception:
            k2, p = np.nan, np.nan
        rows.append({"coluna": c, "assimetria": stats.skew(s),
                     "curtose": stats.kurtosis(s),
                     "normaltest_p": p,
                     "normal_5pct": "nao rejeita" if (p and p > .05) else "rejeita"})
    w(df_to_md(pd.DataFrame(rows), index=False))
    w("\n_Praticamente todas rejeitam normalidade -> testes nao-parametricos "
      "(Mann-Whitney, Kruskal-Wallis) sao a escolha default na Etapa 7._\n")

    # numero de jogos
    w("### 3.2 Numero de jogos por dia\n")
    vc = df["numero_jogos_sp"].value_counts().sort_index()
    vc_tab = pd.DataFrame({"n_dias": vc, "pct": (vc / len(df) * 100).round(2)})
    w(df_to_md(vc_tab, floatfmt=2))
    w("")
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(vc.index.astype(int).astype(str), vc.values, color="#55a868")
    ax.set_xlabel("numero_jogos_sp no dia")
    ax.set_ylabel("dias")
    ax.set_title("Distribuicao do numero de jogos/dia (2022-2023)")
    ax.grid(axis="y", alpha=.3)
    rel = savefig("03_dist_num_jogos.png")
    w(f"![num jogos]({rel})\n")

    # publico
    w("### 3.3 Publico\n")
    pub = df["publico"].dropna()
    if len(pub) == 0:
        w("`publico` esta **100% ausente** -- fonte de publico pagante ainda nao integrada "
          "(hook `clean_football(kaggle_publico_path=...)`). Toda analise por publico "
          "(Etapa 7 'alto vs baixo publico' e feature `taxa_ocupacao`) fica **bloqueada** "
          "ate essa fonte entrar. Limitacao declarada, nao contornada.")
    else:
        w(df_to_md(pub.describe().to_frame("publico"), floatfmt=1))
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.hist(pub, bins=25, color="#c44e52", edgecolor="white")
        ax.set_title("Distribuicao de publico (dias com dado)")
        rel = savefig("04_dist_publico.png")
        w(f"\n![publico]({rel})\n")
    w("")


# ---------------------------------------------------------------------------
# 6.4 SERIES TEMPORAIS
# ---------------------------------------------------------------------------
def secao_series(df):
    w("## 4. Series temporais\n")
    d = df.set_index("data")

    def serie_com_rolling(col, cor, titulo, fname):
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(d.index, d[col], color=cor, alpha=.35, lw=.8, label=col)
        ax.plot(d.index, d[col].rolling(7, center=True).mean(), color=cor, lw=1.8,
                label="media movel 7d")
        ax.plot(d.index, d[col].rolling(28, center=True).mean(), color="k", lw=1.2,
                label="media movel 28d")
        ax.set_title(titulo)
        ax.legend(ncol=3, fontsize=8)
        ax.grid(alpha=.3)
        return savefig(fname)

    r1 = serie_com_rolling("crimes_totais", "#b5651d",
                           "crimes_totais ao longo do tempo (SP capital)", "05_ts_crimes.png")
    w(f"### 4.1 Crimes ao longo do tempo\n\n![ts crimes]({r1})\n")
    w("_Queda abrupta nos 2 ultimos dias = censura de registro (2023-12-30/31), nao "
      "reducao real. Candidata a exclusao no split (Etapa 15)._\n")

    r2 = serie_com_rolling("acidentes_total", "#1f6f8b",
                           "acidentes_total ao longo do tempo (SP capital)", "06_ts_acidentes.png")
    w(f"### 4.2 Acidentes ao longo do tempo\n\n![ts acidentes]({r2})\n")

    # jogos ao longo do tempo
    w("### 4.3 Jogos ao longo do tempo\n")
    mensal = df.assign(ano_mes=df["data"].dt.to_period("M").astype(str)) \
               .groupby("ano_mes").agg(dias_com_jogo=("tem_jogo_sp", "sum"),
                                       jogos=("numero_jogos_sp", "sum"),
                                       classicos=("classico", "sum"))
    fig, ax = plt.subplots(figsize=(13, 3.5))
    ax.bar(mensal.index, mensal["jogos"], color="#8172b2", label="jogos no mes")
    ax.bar(mensal.index, mensal["classicos"], color="#c44e52", label="classicos")
    ax.tick_params(axis="x", rotation=90)
    ax.legend()
    ax.set_title("Jogos de mandante SP-capital por mes")
    ax.grid(axis="y", alpha=.3)
    r3 = savefig("07_ts_jogos.png")
    w(f"![ts jogos]({r3})\n")
    w(df_to_md(mensal, floatfmt=0))
    w("")

    # crimes vs jogos / acidentes vs jogos: overlay + boxplot
    w("### 4.4 Crimes vs jogos e acidentes vs jogos\n")
    for col, cor, fname, titulo in [
        ("crimes_totais", "#b5651d", "08_crimes_vs_jogos.png", "crimes_totais com dias de jogo destacados"),
        ("acidentes_total", "#1f6f8b", "09_acidentes_vs_jogos.png", "acidentes_total com dias de jogo destacados"),
    ]:
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(d.index, d[col].rolling(7, center=True).mean(), color=cor, lw=1.5,
                label=f"{col} (mm 7d)")
        jogo = d[d["tem_jogo_sp"]]
        ax.scatter(jogo.index, jogo[col], s=14, color="k", zorder=3, label="dia com jogo")
        cl = d[d["classico"]]
        ax.scatter(cl.index, cl[col], s=34, color="red", marker="D", zorder=4, label="classico")
        ax.set_title(titulo)
        ax.legend(fontsize=8)
        ax.grid(alpha=.3)
        rel = savefig(fname)
        w(f"![{col}]({rel})\n")

    # boxplots jogo x nao-jogo
    fig, axes = plt.subplots(1, 4, figsize=(15, 4))
    for ax, col in zip(axes, ["crimes_totais", "crimes_violentos", "acidentes_total", "acidentes_com_vitima"]):
        grupos = [df.loc[~df["tem_jogo_sp"], col].dropna(),
                  df.loc[df["tem_jogo_sp"], col].dropna()]
        ax.boxplot(grupos, tick_labels=["sem jogo", "com jogo"])
        ax.set_title(col)
        ax.grid(axis="y", alpha=.3)
    r = savefig("10_boxplot_jogo.png")
    w(f"![boxplot jogo]({r})\n")
    w("_Somente visual. Diferenca de medianas aqui **nao** e evidencia -- Etapa 7 faz o teste "
      "com controle de dia da semana (jogos concentram em fim de semana, que ja tem padrao proprio)._\n")

    # heatmap dia-da-semana x mes
    w("### 4.5 Sazonalidade: dia da semana x mes\n")
    for col, fname in [("crimes_totais", "11_heatmap_crimes.png"),
                       ("acidentes_total", "12_heatmap_acidentes.png")]:
        piv = df.pivot_table(index="nome_dia_semana", columns="mes", values=col, aggfunc="mean")
        ordem = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
        piv = piv.reindex([o for o in ordem if o in piv.index])
        fig, ax = plt.subplots(figsize=(9, 3.6))
        im = ax.imshow(piv.values, aspect="auto", cmap="magma")
        ax.set_xticks(range(piv.shape[1]))
        ax.set_xticklabels(piv.columns)
        ax.set_yticks(range(piv.shape[0]))
        ax.set_yticklabels(piv.index)
        ax.set_title(f"media de {col} por dia da semana x mes")
        fig.colorbar(im, ax=ax, shrink=.8)
        rel = savefig(fname)
        w(f"![heatmap {col}]({rel})\n")

    # media por dia da semana (tabela)
    dow = df.groupby("nome_dia_semana")[["crimes_totais", "crimes_violentos",
                                         "acidentes_total", "acidentes_com_vitima"]].mean()
    dow = dow.reindex([o for o in ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
                       if o in dow.index])
    dow.to_csv(os.path.join(TAB_DIR, "media_por_dia_semana.csv"))
    w("Media por dia da semana:\n")
    w(df_to_md(dow, floatfmt=2))
    w("")

    # ACF
    if HAS_SM:
        w("### 4.6 Autocorrelacao (ACF) -- estrutura temporal\n")
        fig, axes = plt.subplots(1, 2, figsize=(13, 3.5))
        for ax, col in zip(axes, ["crimes_totais", "acidentes_total"]):
            plot_acf(df[col].dropna(), lags=35, ax=ax)
            ax.set_title(f"ACF {col}")
        r = savefig("13_acf.png")
        w(f"![acf]({r})\n")
        w("_Pico em lag 7 e multiplos = sazonalidade semanal forte. Justifica lags "
          "7/14/28 e `rolling_mean_7` na Etapa 12, e validacao temporal (nunca split "
          "aleatorio) na Etapa 15._\n")

    # correlacao entre alvos e clima (Pearson e Spearman) - exploratorio
    w("### 4.7 Correlacao exploratoria (alvos x clima x calendario)\n")
    corr_cols = [c for c in ["crimes_totais", "crimes_violentos", "acidentes_total",
                             "acidentes_com_vitima", "atropelamentos", "colisoes",
                             "temp_media", "precipitacao_total", "umidade_media", "vento_max",
                             "fim_de_semana", "feriado", "numero_jogos_sp"] if c in df.columns]
    cdf = df[corr_cols].astype(float)
    pear = cdf.corr(method="pearson")
    spear = cdf.corr(method="spearman")
    pear.to_csv(os.path.join(TAB_DIR, "corr_pearson.csv"))
    spear.to_csv(os.path.join(TAB_DIR, "corr_spearman.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, m, nome in [(axes[0], pear, "Pearson"), (axes[1], spear, "Spearman")]:
        im = ax.imshow(m.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(m))); ax.set_xticklabels(m.columns, rotation=90)
        ax.set_yticks(range(len(m))); ax.set_yticklabels(m.index)
        ax.set_title(f"Correlacao {nome}")
        for i in range(len(m)):
            for j in range(len(m)):
                ax.text(j, i, f"{m.values[i, j]:.2f}", ha="center", va="center", fontsize=6)
        fig.colorbar(im, ax=ax, shrink=.8)
    r = savefig("14_correlacao.png")
    w(f"![correlacao]({r})\n")
    w("_Exploratorio. Correlacao != causalidade (Regra 5 do briefing). O teste com "
      "confundidores controlados e Etapas 7-8 e 20._\n")


# ---------------------------------------------------------------------------
def main():
    df = load_gold()
    w(f"# EDA -- fato_dia_sp.csv (Etapa 6)\n")
    w(f"_Gerado por `scripts/03_eda.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv` ({len(df)} linhas x {df.shape[1]} colunas)._\n")
    w("> Escopo desta etapa: qualidade, estatistica descritiva, distribuicoes e series "
      "temporais. Testes de hipotese formais (jogo vs nao-jogo, classico, noturno) sao a "
      "Etapa 7. Definicao de 'pico' e a Etapa 11. Nada e modelado aqui.\n")

    secao_qualidade(df)
    secao_descritiva(df)
    secao_distribuicoes(df)
    secao_series(df)

    w("## 5. Sintese para as proximas etapas\n")
    w(textwrap.dedent("""\
        1. **Contagens assimetricas, nao-normais, com sazonalidade semanal forte** ->
           testes nao-parametricos (Etapa 7), modelos de contagem (Etapa 14), lags 7/14/28
           e validacao temporal walk-forward (Etapa 15).
        2. **`publico`/`taxa_ocupacao` 100% ausentes** -> analises por publico bloqueadas
           ate integrar a fonte Kaggle. Declarar como limitacao.
        3. **Censura no fim da serie (2023-12-30/31)** -> excluir do treino/teste ou marcar.
        3b. **Lacuna nova descoberta nesta EDA**: 2022-01-17 e 2023-08-07 tem quase so
           acidentes com vitima (some o fluxo `NOTIFICACAO` da Infosiga). Marcar
           `acidentes_total`/`colisoes` desses 2 dias como missing, nao zero. Adicionar ao
           `CLAUDE.md`.
        4. **Lacunas de clima do INMET** (27/11/2023; precip 25/08-11/09/2023) -> imputar
           com cautela ou usar flag de missing; nao inventar valores.
        5. **Janela curta (730 dias)** -> pouca folga para o split temporal; considerar
           TimeSeriesSplit com poucos folds e reportar incerteza larga.
        6. **Jogos concentrados em fim de semana** -> qualquer comparacao jogo vs nao-jogo
           precisa controlar dia da semana e feriado (confundidores).
    """))

    report_path = os.path.join(OUT_DIR, "eda_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {report_path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))} arquivos)")
    print(f"[ok] tabelas : {TAB_DIR} ({len(os.listdir(TAB_DIR))} arquivos)")


if __name__ == "__main__":
    main()
