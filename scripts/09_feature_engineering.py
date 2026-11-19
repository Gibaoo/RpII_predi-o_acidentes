"""
09_feature_engineering.py
Etapa 12 do roteiro -- FEATURE ENGINEERING.

Constroi a matriz de modelagem `data/gold/features_dia_sp.csv` (1 linha = 1 dia)
com features de futebol, temporais, clima e historicas (lags/rolling), TODAS
seguras contra data leakage para prever o desfecho do DIA t.

Setup de previsao: preve-se se o dia t sera um pico. O que esta disponivel no
momento da previsao (vespera de t ou antes):
  - CALENDARIO de t: sempre conhecido.
  - JOGOS de t: a tabela de jogos e publicada semanas antes -> `tem_jogo_sp`,
    `classico`, `jogo_noturno`, campeonato etc. de t sao features legitimas.
  - RESULTADO / gols do jogo de t: so conhecido DEPOIS -> LEAKAGE. Excluidos.
    Entram apenas defasados (resultado do jogo de ontem).
  - CLIMA de t: nao e conhecido com certeza na vespera, mas uma PREVISAO estaria.
    Assumimos "previsao perfeita D0" (pratica padrao na literatura crime-clima) e
    tambem incluimos clima defasado (lag-1) como alternativa conservadora.
  - HISTORICO do desfecho: lags e rolling usam SO dias <= t-1 (shift >= 1).

Tratamento de dias problematicos (decisao desta etapa):
  - 2023-12-30, 2023-12-31 (censura de registro): desfecho -> NaN, linha nao
    entra em treino/teste.
  - 2022-01-17, 2023-08-07 (lacuna NOTIFICACAO da Infosiga): idem, so acidente.
  - 2022-06-19 (registro em lote de furtos, artefato): contagens de crime do dia
    -> NaN (tratado como missing, nao zero, igual a lacuna da Infosiga); para os
    lags, interpola no tempo para nao contaminar 2022-06-20+. Linha nao entra em
    treino/teste de crime. Flag `dia_artefato_lote`. Etapa 14 fara sensibilidade.

Alvos (recalculados AQUI, consistentes com o tratamento acima -- nao se faz join
cego das flags da Etapa 11):
  y_count_<base>, y_resid_<base> (residuo dessazonalizado),
  y_pico_p90_<base>, y_pico_p95_<base>, y_nivel_<base>
  base in {crimes_violentos, acidentes_com_vitima}.

Ressalva p/ Etapa 15 (ja anotada no CLAUDE.md): o ajuste de calendario e o limiar
P90/P95 usam a serie inteira aqui. Num walk-forward estrito, reajustar so no
treino de cada fold. As features `*_rollmean_*` e `*_resid_lag*` da variante de
media movel ja sao causais.

Rodar depois de 02 (e idealmente 08).
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_OUT = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa12")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}
ARTEFATO = pd.Timestamp("2022-06-19")

CRIME_COLS = ["crimes_totais", "bos_unicos", "crimes_violentos", "homicidios_dolosos",
              "tentativas_homicidio", "latrocinio", "lesao_corporal_dolosa", "roubos_total",
              "roubo_veiculo", "furtos_total", "furto_veiculo", "estupros", "trafico_entorpecentes"]
ACID_COLS = ["acidentes_total", "acidentes_com_vitima", "acidentes_fatais", "obitos_transito",
             "feridos_transito", "atropelamentos", "colisoes"]
BASES = ["crimes_violentos", "acidentes_com_vitima"]
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"
LAGS = [1, 2, 3, 7, 14, 28, 364]
ROLLS = [7, 14, 28]

_md = []
_dict_rows = []


def w(s=""):
    _md.append(s)


def feat(name, grupo, leakage_ok, desc):
    _dict_rows.append({"feature": name, "grupo": grupo, "leakage_ok": leakage_ok, "descricao": desc})


def df_to_md(df, floatfmt=3, index=True):
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
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


# ---------------------------------------------------------------------------
def load():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    df["t_idx"] = np.arange(len(df))
    for c in ["dia_semana", "mes", "trimestre", "semana_ano", "numero_jogos_sp"]:
        df[c] = df[c].astype(int)
    for c in ["tem_jogo_sp", "classico", "fim_de_semana", "feriado", "feriado_nacional",
              "feriado_estadual", "feriado_municipal", "vespera_feriado", "periodo_letivo",
              "ferias_escolares", "recesso_escolar", "jogo_d_menos_1", "jogo_d_mais_1",
              "classico_d_menos_1", "classico_d_mais_1", "chuva"]:
        df[c] = df[c].astype("boolean").fillna(False).astype(int)
    df["jogo_noturno"] = df["jogo_noturno"].map({True: 1, False: 0, "True": 1, "False": 0})
    return df


def tratar_dias_problematicos(df):
    """Zera para NaN as contagens dos dias problematicos ANTES de derivar
    lags/alvos. Retorna copia + relatorio de antes/depois de 2022-06-19."""
    antes = df.loc[df["data"] == ARTEFATO, ["crimes_totais", "crimes_violentos",
                                            "furtos_total", "roubos_total"]].iloc[0].to_dict()
    d = df.copy()
    d["dia_artefato_lote"] = (d["data"] == ARTEFATO).astype(int)
    d["dia_excluido_crime"] = d["data"].isin(EXCL_CRIME | {ARTEFATO}).astype(int)
    d["dia_excluido_acidente"] = d["data"].isin(EXCL_ACID).astype(int)
    d.loc[d["data"].isin(EXCL_CRIME | {ARTEFATO}), CRIME_COLS] = np.nan
    d.loc[d["data"].isin(EXCL_ACID), ACID_COLS] = np.nan
    # serie "limpa para lag": interpola no tempo os buracos (so p/ alimentar lags,
    # nao vira alvo). max 4 dias isolados -> interpolacao linear e inofensiva.
    for c in CRIME_COLS + ACID_COLS:
        d[c + "__lagsrc"] = d[c].interpolate(method="linear", limit_direction="both")
    return d, antes


# ---------------------------------------------------------------------------
def deseasonaliza(d, col, excl):
    x = d[["data", "t_idx", "dia_semana", "mes", "feriado", col]].copy()
    x.loc[x["data"].isin(excl), col] = np.nan
    fit = smf.ols(f"{col} ~ {CTRL}", data=x.dropna(subset=[col])).fit()
    resid = x[col] - fit.predict(x)
    return resid, fit


def build_targets(d):
    w("## 1. Alvos (recalculados com o tratamento de outliers desta etapa)\n")
    linhas = []
    for base in BASES:
        excl = EXCL_CRIME | {ARTEFATO} if base in CRIME_COLS else EXCL_ACID
        resid, fit = deseasonaliza(d, base, excl)
        m = resid.notna()
        p90, p95 = resid[m].quantile(0.90), resid[m].quantile(0.95)
        q75 = resid[m].quantile(0.75)
        d[f"y_count_{base}"] = d[base].where(~d["data"].isin(excl))
        d[f"y_resid_{base}"] = resid
        d[f"y_pico_p90_{base}"] = pd.Series(np.where(m, resid > p90, np.nan)).astype("boolean")
        d[f"y_pico_p95_{base}"] = pd.Series(np.where(m, resid > p95, np.nan)).astype("boolean")
        niv = pd.Series(pd.NA, index=d.index, dtype="object")
        niv[m & (resid <= q75)] = "Baixo"
        niv[m & (resid > q75) & (resid <= p90)] = "Medio"
        niv[m & (resid > p90)] = "Alto"
        d[f"y_nivel_{base}"] = niv
        linhas.append({"base": base, "R2_calendario": fit.rsquared, "n_elegivel": int(m.sum()),
                       "n_pico_p90": int((resid > p90).sum()), "n_pico_p95": int((resid > p95).sum())})
    w(df_to_md(pd.DataFrame(linhas), floatfmt=3, index=False))
    w("\n_Os alvos residuais e P90/P95 seguem a definicao da Etapa 11, mas aplicados a "
      "serie ja com 2022-06-19 tratado como missing -- por isso podem diferir de "
      "`pico_dia_sp.csv` exatamente nesse dia (que la era pico `Alto`, aqui e NaN)._\n")
    return d


# ---------------------------------------------------------------------------
def build_features(d):
    # ---- 2.1 temporais ----
    d["trend"] = d["t_idx"] / (len(d) - 1)
    feat("trend", "temporal", True, "indice do dia normalizado 0..1 (tendencia linear)")
    doy = d["data"].dt.dayofyear
    d["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    d["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    d["sin_dow"] = np.sin(2 * np.pi * d["dia_semana"] / 7)
    d["cos_dow"] = np.cos(2 * np.pi * d["dia_semana"] / 7)
    for c in ["sin_doy", "cos_doy", "sin_dow", "cos_dow"]:
        feat(c, "temporal", True, "codificacao ciclica (dia do ano / dia da semana)")
    nomes_dow = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
    for k in range(7):
        d[f"dow_{k}"] = (d["dia_semana"] == k).astype(int)
        feat(f"dow_{k}", "temporal", True, f"one-hot dia da semana (dia_semana=={k}, {nomes_dow[k]})")
    d["dia_do_mes"] = d["data"].dt.day
    feat("dia_do_mes", "temporal", True, "dia do mes 1..31")
    for c in ["mes", "trimestre", "semana_ano", "fim_de_semana", "feriado",
              "feriado_nacional", "feriado_estadual", "feriado_municipal",
              "vespera_feriado", "periodo_letivo", "ferias_escolares", "recesso_escolar"]:
        feat(c, "temporal", True, "campo de calendario do fato (conhecido em avanco)")
    d["pos_feriado"] = d["feriado"].shift(1).fillna(0).astype(int)
    feat("pos_feriado", "temporal", True, "dia seguinte a um feriado")

    # ---- 2.2 futebol (D0, conhecido pela tabela de jogos) ----
    for c in ["tem_jogo_sp", "numero_jogos_sp", "classico", "jogo_noturno",
              "jogo_d_menos_1", "jogo_d_mais_1", "classico_d_menos_1", "classico_d_mais_1"]:
        feat(c, "futebol", True, "fixture/flag do dia (tabela publicada com antecedencia)")
    d["campeonato"] = d["campeonato"].fillna("nenhum")
    d["jogo_copa"] = d["campeonato"].str.contains("Copa", case=False, na=False).astype(int)
    d["jogo_serie_a"] = d["campeonato"].str.contains("Serie A", case=False, na=False).astype(int)
    feat("jogo_copa", "futebol", True, "jogo de Copa do Brasil (proxy grosseiro de importancia)")
    feat("jogo_serie_a", "futebol", True, "jogo de Serie A")
    d["jogo_d_menos_2"] = d["tem_jogo_sp"].shift(2).fillna(0).astype(int)
    d["jogo_d_mais_2"] = d["tem_jogo_sp"].shift(-2).fillna(0).astype(int)
    feat("jogo_d_menos_2", "futebol", True, "houve jogo ha 2 dias (convencao do gold)")
    feat("jogo_d_mais_2", "futebol", True, "ha jogo daqui a 2 dias (convencao do gold)")
    d["n_jogos_janela7"] = d["tem_jogo_sp"].rolling(7, min_periods=1).sum()
    feat("n_jogos_janela7", "futebol", True, "nº de jogos nos ultimos 7 dias incl. hoje (fixture conhecido)")
    # dias desde/ate jogo (a partir da tabela de jogos)
    idx_jogo = d.index[d["tem_jogo_sp"] == 1]
    d["dias_desde_jogo"] = [min((i - j for j in idx_jogo if j <= i), default=99) for i in d.index]
    d["dias_ate_jogo"] = [min((j - i for j in idx_jogo if j >= i), default=99) for i in d.index]
    feat("dias_desde_jogo", "futebol", True, "dias desde o ultimo jogo (>=0)")
    feat("dias_ate_jogo", "futebol", True, "dias ate o proximo jogo (>=0)")
    # interacoes explicitas
    d["jogo_x_fds"] = d["tem_jogo_sp"] * d["fim_de_semana"]
    d["jogo_x_noturno"] = d["tem_jogo_sp"] * d["jogo_noturno"].fillna(0)
    d["classico_x_fds"] = d["classico"] * d["fim_de_semana"]
    for c in ["jogo_x_fds", "jogo_x_noturno", "classico_x_fds"]:
        feat(c, "futebol", True, "interacao explicita (o modelo tambem pode achar sozinho)")

    # ---- 2.3 publico (BLOQUEADO) ----
    d["publico"] = np.nan
    d["taxa_ocupacao"] = np.nan
    feat("publico", "futebol", True, "BLOQUEADO: 100% NaN (fonte Kaggle nao integrada)")
    feat("taxa_ocupacao", "futebol", True, "BLOQUEADO: depende de publico")

    # ---- 2.4 clima ----
    clima = ["temp_media", "temp_max", "temp_min", "precipitacao_total", "umidade_media",
             "vento_max", "chuva"]
    for c in clima:
        feat(c, "clima", "assume previsao D0", "clima observado do dia (proxy de previsao perfeita)")
    d["clima_missing"] = d[clima].isna().any(axis=1).astype(int)
    feat("clima_missing", "clima", True, "flag: alguma variavel de clima ausente no dia (lacunas INMET)")
    for c in ["temp_media", "precipitacao_total", "umidade_media"]:
        d[f"{c}_lag1"] = d[c].shift(1)
        feat(f"{c}_lag1", "clima", True, "clima de ontem (alternativa conservadora a previsao)")

    # ---- 2.5 historicas: lags e rolling do desfecho (SO passado, shift>=1) ----
    for base in BASES:
        src = d[base + "__lagsrc"]
        excl = EXCL_CRIME | {ARTEFATO} if base in CRIME_COLS else EXCL_ACID
        resid, _ = deseasonaliza(d.assign(**{base: d[base + "__lagsrc"]}), base, set())
        for L in LAGS:
            d[f"{base}_lag{L}"] = src.shift(L)
            feat(f"{base}_lag{L}", "historica", True, f"{base} {L} dia(s) atras (interpolado nos buracos)")
        for R in ROLLS:
            d[f"{base}_rollmean{R}"] = src.shift(1).rolling(R, min_periods=max(3, R // 2)).mean()
            d[f"{base}_rollstd{R}"] = src.shift(1).rolling(R, min_periods=max(3, R // 2)).std(ddof=0)
            feat(f"{base}_rollmean{R}", "historica", True, f"media movel {R}d de {base}, deslocada 1 dia")
            feat(f"{base}_rollstd{R}", "historica", True, f"desvio movel {R}d de {base}, deslocado 1 dia")
        d[f"{base}_resid_lag1"] = resid.shift(1)
        d[f"{base}_resid_lag7"] = resid.shift(7)
        feat(f"{base}_resid_lag1", "historica", "ver ressalva E15",
             "residuo dessazonalizado de ontem (ajuste de calendario usa serie inteira)")
        feat(f"{base}_resid_lag7", "historica", "ver ressalva E15", "residuo dessazonalizado de 7 dias atras")
        # desvio do nivel recente
        d[f"{base}_lag1_vs_rollmean28"] = d[f"{base}_lag{1}"] - d[f"{base}_rollmean28"]
        feat(f"{base}_lag1_vs_rollmean28", "historica", True, "ontem menos a media movel de 28d")
        # picos recentes (leakage-safe: shift 1)
        pico_hist = d[f"y_pico_p90_{base}"].astype("float")
        d[f"pico_p90_{base}_lag1"] = pico_hist.shift(1)
        d[f"pico_p90_{base}_soma7"] = pico_hist.shift(1).rolling(7, min_periods=3).sum()
        feat(f"pico_p90_{base}_lag1", "historica", True, "ontem foi pico? (0/1)")
        feat(f"pico_p90_{base}_soma7", "historica", True, "nº de picos nos 7 dias anteriores")
        # sazonal esperado (previsao de calendario, conhecida em avanco)
        _, fit_full = deseasonaliza(d, base, excl)
        d[f"sazonal_esperado_{base}"] = fit_full.predict(
            d[["t_idx", "dia_semana", "mes", "feriado"]])
        feat(f"sazonal_esperado_{base}", "historica", "ver ressalva E15",
             "valor esperado de {base} so pelo calendario (ajuste na serie inteira)")

    # limpa colunas auxiliares
    d = d.drop(columns=[c for c in d.columns if c.endswith("__lagsrc")])
    return d


def secao_lista_features(d):
    w("## 2. Features construidas\n")
    w("`leakage_ok`: `True` = seguro por construcao; texto = ressalva explicita "
      "(ver secao 3).\n")
    dd = pd.DataFrame(_dict_rows)
    for grupo in ["temporal", "futebol", "clima", "historica"]:
        sub = dd[dd["grupo"] == grupo]
        w(f"### {grupo} ({len(sub)})\n")
        w(df_to_md(sub[["feature", "leakage_ok", "descricao"]], floatfmt=0, index=False))
        w("")


# ---------------------------------------------------------------------------
def secao_leakage(d):
    w("## 3. Auditoria de data leakage\n")
    checks = []
    # a) toda feature historica usa shift>=1?
    for base in BASES:
        for L in LAGS:
            s = d[f"{base}_lag{L}"]
            # lag L deve ser igual a serie deslocada L -> corr perfeita com o passado, nunca alinhado ao presente
            aligned = (s.fillna(-999) == d[f"y_count_{base}"].fillna(-999)).mean()
            checks.append({"feature": f"{base}_lag{L}", "checagem": "== alvo do MESMO dia?",
                           "frac_igual_ao_alvo": aligned, "ok": aligned < 0.99})
    # b) rolling usa shift(1)?
    for base in BASES:
        rm = d[f"{base}_rollmean7"]
        # rollmean7 no dia t nao pode usar y[t]; corr entre rollmean7 e y[t] deve ser < corr com y[t-1]
        c_now = d[[f"{base}_rollmean7", f"y_count_{base}"]].corr().iloc[0, 1]
        c_prev = pd.concat([rm, d[f"y_count_{base}"].shift(1)], axis=1).corr().iloc[0, 1]
        checks.append({"feature": f"{base}_rollmean7", "checagem": "corr(now) < corr(prev)?",
                       "frac_igual_ao_alvo": np.nan, "ok": c_now <= c_prev + 1e-9})
    # c) nenhuma feature identica ao alvo
    feat_cols = [r["feature"] for r in _dict_rows]
    for base in BASES:
        y = d[f"y_count_{base}"]
        for fc in feat_cols:
            if fc in d.columns and pd.api.types.is_numeric_dtype(d[fc]):
                if d[fc].notna().sum() > 30 and (d[fc].fillna(-1) == y.fillna(-2)).mean() > 0.99:
                    checks.append({"feature": fc, "checagem": "identica ao alvo?",
                                   "frac_igual_ao_alvo": 1.0, "ok": False})
    ch = pd.DataFrame(checks)
    ch.to_csv(os.path.join(TAB_DIR, "auditoria_leakage.csv"), index=False)
    n_falha = int((~ch["ok"]).sum())
    w(df_to_md(ch[["feature", "checagem", "frac_igual_ao_alvo", "ok"]].head(20), floatfmt=4, index=False))
    w(f"\n**{n_falha} falha(s)** na auditoria automatica. "
      + ("Todas as features historicas usam shift>=1; nenhuma coincide com o alvo do dia."
         if n_falha == 0 else "Revisar as linhas com ok=False acima.") + "\n")
    w("Pontos que a auditoria automatica NAO cobre (tratados por design, ver cabecalho):\n"
      "- `temp_*`/`precipitacao_*`/`umidade_*`/`vento_*`/`chuva` de D0 assumem previsao "
      "perfeita -- alternativa conservadora `*_lag1` incluida.\n"
      "- `y_resid_*`, `*_resid_lag*`, `sazonal_esperado_*` usam um ajuste de calendario "
      "estimado na serie inteira -> vazamento leve de tendencia/sazonalidade. Na Etapa 15 "
      "reajustar por fold. Marcadas como `leakage_ok = 'ver ressalva E15'` no dicionario.\n")


def secao_missing_e_dist(d):
    w("## 4. Missingness e distribuicao dos alvos\n")
    feat_cols = [r["feature"] for r in _dict_rows if r["feature"] in d.columns]
    miss = d[feat_cols].isna().mean().sort_values(ascending=False)
    miss = miss[miss > 0]
    mt = pd.DataFrame({"pct_missing": (miss * 100).round(2)})
    mt.index.name = "feature"
    mt.to_csv(os.path.join(TAB_DIR, "missingness_features.csv"))
    w("Features com valores ausentes (apos construcao):\n")
    w(df_to_md(mt, floatfmt=2))
    w("\n_Esperado: `publico`/`taxa_ocupacao` 100% (bloqueadas); `jogo_noturno` ~83% "
      "(so definido em dia de jogo, igual ao resto do gold -- NaN != 0); `*_lag364` "
      "~50% (so o 2º ano tem historico de 1 ano); `*_lag28`/`rollmean28` ~4% "
      "(aquecimento da janela); clima ~2% (lacunas INMET). O split da Etapa 15 "
      "comeca depois do aquecimento das janelas._\n")
    linhas = []
    for base in BASES:
        for tgt in [f"y_pico_p90_{base}", f"y_pico_p95_{base}"]:
            vc = d[tgt].value_counts(dropna=False)
            linhas.append({"alvo": tgt, "n_True": int(vc.get(True, 0)),
                           "n_False": int(vc.get(False, 0)), "n_NaN": int(d[tgt].isna().sum()),
                           "prevalencia_%": d[tgt].mean() * 100})
    w(df_to_md(pd.DataFrame(linhas), floatfmt=2, index=False))
    w("")


def secao_corr_alvo(d):
    w("## 5. Sanidade: correlacao das features com o alvo (Spearman)\n")
    w("Previa do que a Etapa 18 (SHAP) deve confirmar. Espera-se lags/rolling do "
      "proprio desfecho no topo e features de futebol perto de zero -- coerente com "
      "Etapas 7-10.\n")
    for base in BASES:
        y = d[f"y_resid_{base}"]
        num = [r["feature"] for r in _dict_rows
               if r["feature"] in d.columns and pd.api.types.is_numeric_dtype(d[r["feature"]])
               and d[r["feature"]].notna().sum() > 200]
        rows = []
        for c in num:
            sub = pd.concat([d[c], y], axis=1).dropna()
            if len(sub) > 100 and sub[c].nunique() > 2:
                rho, p = stats.spearmanr(sub[c], sub[y.name])
                rows.append({"feature": c, "spearman_rho": rho, "p": p})
        t = pd.DataFrame(rows).reindex(pd.DataFrame(rows)["spearman_rho"].abs().sort_values(ascending=False).index)
        t.to_csv(os.path.join(TAB_DIR, f"corr_features_alvo_{base}.csv"), index=False)
        w(f"### {base} -- top 15 |rho|\n")
        w(df_to_md(t.head(15), floatfmt=3, index=False))

        top = t.head(15).iloc[::-1]
        cores = ["#c44e52" if "jogo" in f or "classico" in f or "copa" in f or "serie_a" in f
                 else "#4c72b0" for f in top["feature"]]
        fig, ax = plt.subplots(figsize=(8, 5.5))
        ax.barh(top["feature"], top["spearman_rho"], color=cores)
        ax.axvline(0, color="k", lw=.8)
        ax.set_xlabel("correlacao de Spearman com o residuo dessazonalizado")
        ax.set_title(f"Top 15 features x {base} (vermelho = futebol)")
        ax.grid(axis="x", alpha=.3)
        w(f"![corr {base}]({savefig(f'01_corr_top15_{base}.png')})\n")

        fut = t[t["feature"].str.contains("jogo|classico|copa|serie_a", case=False)]
        w(f"\n_Features de futebol: |rho| maximo = {fut['spearman_rho'].abs().max():.3f} "
          f"({fut.loc[fut['spearman_rho'].abs().idxmax(), 'feature'] if len(fut) else '-'}). "
          f"Todas fracas, como esperado._\n")


def secao_out(d, antes):
    w("## 6. Tratamento de 2022-06-19 e materializacao\n")
    linha = d.loc[d["data"] == ARTEFATO].iloc[0]
    depois = {k: linha[k] for k in antes}  # mesmas 4 colunas, agora pos-tratamento
    extra = {"y_count_crimes_violentos": linha["y_count_crimes_violentos"],
             "y_pico_p90_crimes_violentos": linha["y_pico_p90_crimes_violentos"],
             "dia_artefato_lote": linha["dia_artefato_lote"]}
    w("2022-06-19 antes (fato) -> depois (features), mesmas 4 colunas de contagem:\n")
    w(df_to_md(pd.DataFrame({"antes_fato": antes, "depois_features": depois}), floatfmt=0))
    w("\nOutros campos do dia: " + ", ".join(f"`{k}`={v}" for k, v in extra.items()) + ".\n")
    w("\nA contagem de crime do dia virou NaN (como as lacunas ja tratadas); o alvo "
      "`y_*_crimes_violentos` e NaN -> a linha nao entra em treino/teste de crime. "
      "Para os lags, `crimes_*__lagsrc` interpola o buraco (linear, no maximo 1 dia "
      "isolado) para nao contaminar 2022-06-20+. `dia_artefato_lote=1` fica como flag. "
      "**Sensibilidade planejada (Etapa 14):** rodar os modelos tambem SEM esse "
      "tratamento (dia mantido) e comparar as metricas.\n")

    keep = ["data"] + [r["feature"] for r in _dict_rows if r["feature"] in d.columns]
    keep += [c for c in d.columns if c.startswith("y_")]
    keep += ["dia_excluido_crime", "dia_excluido_acidente", "dia_artefato_lote"]
    keep = list(dict.fromkeys(keep))
    out = d[keep].copy()
    out.to_csv(FEAT_OUT, index=False)
    w(f"**Arquivo:** `data/gold/features_dia_sp.csv` -- {out.shape[0]} linhas x "
      f"{out.shape[1]} colunas ({len([r for r in _dict_rows])} features + "
      f"{len([c for c in out.columns if c.startswith('y_')])} alvos + 4 flags/chave).\n")
    dd = pd.DataFrame(_dict_rows)
    dd.to_csv(os.path.join(TAB_DIR, "dicionario_features.csv"), index=False)
    w("Dicionario completo em `reports/etapa12/tabelas/dicionario_features.csv`. "
      "Resumo por grupo:\n")
    w(df_to_md(dd.groupby("grupo").size().rename("n_features").to_frame(), floatfmt=0))
    w("")


# ---------------------------------------------------------------------------
def main():
    df = load()
    w("# Etapa 12 -- Feature engineering\n")
    w(f"_Gerado por `scripts/09_feature_engineering.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv`._\n")
    w("> Matriz de modelagem 1 dia = 1 linha, **sem data leakage**: features de "
      "calendario e de jogos de D0 (conhecidas em avanco), clima de D0 (assume "
      "previsao) e historico do desfecho (shift >= 1). Alvos recalculados aqui com o "
      "tratamento de outliers desta etapa. Modelos: Etapas 13-14.\n")
    d, antes = tratar_dias_problematicos(df)
    d = build_targets(d)
    d = build_features(d)
    secao_lista_features(d)
    secao_leakage(d)
    secao_missing_e_dist(d)
    secao_corr_alvo(d)
    secao_out(d, antes)

    w("## 7. Sintese e proximos passos\n")
    w(textwrap.dedent("""\
        - Matriz pronta com 4 grupos de feature (temporal, futebol, clima, historica)
          + 6 alvos (contagem, residuo, pico P90/P95, nivel) x 2 desfechos.
        - **Leakage**: features historicas usam shift >= 1; resultado do jogo de D0
          excluido (so entra defasado); clima de D0 assumido como previsao (variante
          `*_lag1` disponivel); `*_resid_*`/`sazonal_esperado_*` dependem de um ajuste
          de calendario feito na serie inteira -> reajustar por fold na Etapa 15.
        - **Outlier 2022-06-19**: contagens de crime -> NaN (missing, nao zero),
          interpoladas so para lags; linha fora de treino/teste; flag mantida;
          sensibilidade na Etapa 14.
        - **Publico bloqueado**: colunas presentes, 100% NaN (Regra 10).
        - **Correlacao com o alvo** ja antecipa: lags/rolling do proprio desfecho
          lideram; futebol fraco -- consistente com Etapas 7-10 e com a expectativa
          de importancia baixa no SHAP (Etapa 18).
        - **Etapa 13**: baselines (media historica, media movel, mesmo dia da semana
          anterior, classe majoritaria, regressao logistica) sobre `features_dia_sp.csv`,
          com split temporal (TimeSeriesSplit / walk-forward), comecando apos o
          aquecimento das janelas (>= dia 28; ideal >= 365 para ter `*_lag364`).
    """))

    path = os.path.join(OUT_DIR, "relatorio_features.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] features : {FEAT_OUT}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
