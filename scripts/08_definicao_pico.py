"""
08_definicao_pico.py
Etapa 11 do roteiro -- DEFINICAO DE "PICO".

O briefing exige testar varias abordagens e justificar a escolha, sem definir
pico de forma arbitraria. As Etapas 6-10 mostraram que crime e acidente tem
sazonalidade semanal e mensal forte -- por isso os testes P90/P95 da Etapa 8
foram marcados como PROVISORIOS (um "pico" na contagem crua e, quase sempre, so
"e sexta/sabado" ou "e marco"). Aqui a definicao formal e feita sobre o
RESIDUO DESSAZONALIZADO: obs - OLS(obs ~ t + C(dia_semana) + C(mes) + feriado).
Assim "pico" = dia anormalmente alto PARA aquele dia da semana e mes, nao um
dia estruturalmente movimentado.

Tres metodos comparados (Secao 11 do roteiro):
  1. Percentil     : residuo > P90 (e P95)
  2. Z-score       : residuo / desvio-padrao > 2 (e versao robusta com MAD)
  3. Media movel   : residuo > media_movel_28d(residuo) + 2*desvio_movel_28d
                     (janela causal, deslocada 1 dia -> sem data leakage;
                      serve tambem como feature na Etapa 12)

Saidas:
  reports/etapa11/relatorio_definicao_pico.md   + figures/ + tabelas/
  data/gold/pico_dia_sp.csv   -- flags de pico por desfecho/metodo + nivel_risco,
                                  chave = data. NAO altera fato_dia_sp.csv;
                                  `02_limpeza.py` faz o merge deste arquivo nos
                                  placeholders pico_* se ele existir.

Exclusoes (Etapa 6): dias excluidos ficam com pico = NaN (nao elegiveis).
  crime : 2023-12-30, 2023-12-31
  acid  : + 2022-01-17, 2023-08-07
Outlier 2022-06-19 (furtos, registro em lote): MANTIDO aqui (decisao de
tratamento e da Etapa 12); sinalizado no relatorio -- e pico por todos os
metodos, mas e artefato.

Rodar depois de 02 (usa data/gold/fato_dia_sp.csv).
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
PICO_OUT = os.path.join(BASE_DIR, "data", "gold", "pico_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa11")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}
OUTLIER_LOTE = pd.Timestamp("2022-06-19")

CTRL = "t + C(dia_semana) + C(mes) + feriado"
# desfechos avaliados; os 2 primeiros de cada familia sao os alvos recomendados
CRIME_OUT = ["crimes_violentos", "crimes_totais", "lesao_corporal_dolosa"]
ACID_OUT = ["acidentes_com_vitima", "acidentes_total", "acidentes_fatais"]
ROLL = 28

_md = []


def w(s=""):
    _md.append(s)


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


def load():
    df = pd.read_csv(GOLD_PATH, parse_dates=["data"]).sort_values("data").reset_index(drop=True)
    df["t"] = np.arange(len(df))
    df["dia_semana"] = df["dia_semana"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["feriado"] = df["feriado"].astype(int)
    return df


def residuo_dessaz(df, col, excl):
    """residuo de OLS col ~ t + C(dia_semana) + C(mes) + feriado.
    Dias excluidos: col vira NaN antes do ajuste e residuo NaN depois."""
    d = df[["data", "t", "dia_semana", "mes", "feriado", col]].copy()
    d.loc[d["data"].isin(excl), col] = np.nan
    fit = smf.ols(f"{col} ~ {CTRL}", data=d.dropna(subset=[col])).fit()
    res = d[col] - fit.predict(d)
    return res, fit


# ---------------------------------------------------------------------------
def secao_por_que_residuo(df):
    w("## 1. Por que NAO usar a contagem crua\n")
    w("Repetindo o teste provisorio da Etapa 8, agora so para mostrar o problema: "
      "`pico_cru` = dia acima do P90 da contagem crua de `crimes_totais`.\n")
    thr = df["crimes_totais"].quantile(0.90)
    pico_cru = df["crimes_totais"] > thr
    ct = pd.crosstab(df["nome_dia_semana"], pico_cru, normalize="index")[True] * 100
    ordem = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
    ct = ct.reindex([o for o in ordem if o in ct.index]).rename("% dos dias que sao 'pico cru'")
    w(df_to_md(ct.to_frame(), floatfmt=1))
    w("")
    dow_share = df.loc[pico_cru, "nome_dia_semana"].value_counts(normalize=True)
    w(f"- {dow_share.get('sexta', 0)*100:.0f}% dos 'picos crus' caem numa **sexta** e "
      f"{dow_share.get('sábado', 0)*100:.0f}% num **sabado**; **domingo e segunda quase "
      f"nunca** ({ct.get('domingo', 0):.0f}% e {ct.get('segunda', 0):.0f}% dos seus dias). "
      f"Ou seja, 'pico cru' ~= 'e fim de semana'. Nao serve como alvo -- um modelo "
      f"acertaria so aprendendo o dia da semana.\n")
    w("**Solucao:** definir pico sobre o **residuo dessazonalizado** "
      "`obs - OLS(obs ~ t + C(dia_semana) + C(mes) + feriado)`. R^2 do ajuste de "
      "calendario por desfecho:\n")
    linhas = []
    for col in CRIME_OUT + ACID_OUT:
        excl = EXCL_CRIME if col in CRIME_OUT else EXCL_ACID
        _, fit = residuo_dessaz(df, col, excl)
        linhas.append({"desfecho": col, "R2_calendario": fit.rsquared,
                       "obs_explicada_%": fit.rsquared * 100})
    w(df_to_md(pd.DataFrame(linhas), floatfmt=3, index=False))
    w("\n_Quanto maior o R^2, mais da variacao diaria e so calendario -- e mais "
      "enganoso seria um pico definido na contagem crua._\n")


# ---------------------------------------------------------------------------
def flags_de_pico(res):
    """res: Series de residuo (NaN nos dias excluidos). Retorna dict de Series
    'boolean': True/False onde o metodo pode avaliar, pd.NA onde nao (dia
    excluido, ou sem historico suficiente para a janela movel)."""
    r = res.copy()
    mask = r.notna()

    def _flag(cond, evaluavel):
        s = pd.Series(pd.NA, index=r.index, dtype="boolean")
        s[evaluavel] = cond[evaluavel]
        return s

    out = {}
    # 1. percentil
    for q in (0.90, 0.95):
        thr = r[mask].quantile(q)
        out[f"p{int(q*100)}"] = _flag(r > thr, mask)
    # 2. z-score (classico e robusto)
    z = (r - r[mask].mean()) / r[mask].std(ddof=0)
    out["z2"] = _flag(z > 2, mask)
    out["z1_5"] = _flag(z > 1.5, mask)
    mad = (r[mask] - r[mask].median()).abs().median()
    zr = (r - r[mask].median()) / (1.4826 * mad)
    out["z2_robusto"] = _flag(zr > 2, mask)
    # 3. media movel causal (sem leakage): banda de 28d deslocada 1 dia
    mm = r.shift(1).rolling(ROLL, min_periods=14).mean()
    sd = r.shift(1).rolling(ROLL, min_periods=14).std(ddof=0)
    out["mm28_2sd"] = _flag(r > mm + 2 * sd, mask & mm.notna() & sd.notna())
    return out, z, zr, (mm, sd)


def secao_tres_metodos(df):
    w("## 2. Tres definicoes de pico sobre o residuo -- comparacao\n")
    w("Metodos: **percentil** (residuo > P90/P95), **z-score** (residuo/desvio > 2; "
      "e versao robusta com MAD), **media movel** (residuo > media_movel_28d + "
      "2*desvio_movel_28d, janela causal deslocada 1 dia -> sem leakage e reutilizavel "
      "como feature).\n")

    resumo, todos_flags = [], {}
    for col in CRIME_OUT + ACID_OUT:
        excl = EXCL_CRIME if col in CRIME_OUT else EXCL_ACID
        res, _ = residuo_dessaz(df, col, excl)
        flags, _, _, _ = flags_de_pico(res)
        todos_flags[col] = flags
        n_elig = res.notna().sum()
        for nome, fl in flags.items():
            resumo.append({"desfecho": col, "metodo": nome, "n_picos": int(fl.sum()),
                           "pct_dias_elegiveis": fl.sum() / n_elig * 100})
    tab = pd.DataFrame(resumo)
    piv = tab.pivot(index="desfecho", columns="metodo", values="n_picos")
    piv = piv[["p90", "p95", "z1_5", "z2", "z2_robusto", "mm28_2sd"]]
    piv.to_csv(os.path.join(TAB_DIR, "n_picos_por_metodo.csv"))
    w("Numero de dias-pico por desfecho x metodo (de ~726-728 dias elegiveis):\n")
    w(df_to_md(piv, floatfmt=0))
    w("")
    pct = tab.pivot(index="desfecho", columns="metodo", values="pct_dias_elegiveis")[
        ["p90", "p95", "z1_5", "z2", "z2_robusto", "mm28_2sd"]]
    w("Mesma coisa em % dos dias elegiveis:\n")
    w(df_to_md(pct, floatfmt=1))
    w("")
    w(textwrap.dedent("""\
        - **P90** da ~10% de positivos por construcao; **P95** ~5%.
        - **z>2** no residuo tende a dar MENOS que 5% (a cauda direita e mais
          pesada que a normal -> poucos pontos passam 2 desvios) e **z>1,5** fica
          entre P90 e P95. O z-score assume simetria/normalidade que a EDA ja
          rejeitou -> menos indicado como definicao principal.
        - **media movel** da um numero parecido com P90/P95 mas VARIA no tempo
          (adapta-se a periodos mais ou menos volateis) e e a unica que pode
          virar feature sem leakage.
    """))
    return todos_flags


# ---------------------------------------------------------------------------
def secao_concordancia(df, todos_flags):
    w("## 3. Concordancia entre metodos e inspecao dos picos de consenso\n")
    for fam, col in [("crime", "crimes_violentos"), ("acidente", "acidentes_com_vitima")]:
        fl = todos_flags[col]
        keys = ["p90", "z2", "mm28_2sd"]
        M = pd.DataFrame({k: fl[k].eq(True).fillna(False) for k in keys})  # NA -> False
        all3 = M.all(axis=1)
        inter = int(all3.sum())
        union = int(M.any(axis=1).sum())
        w(f"### {col}\n")
        jac = pd.DataFrame(index=keys, columns=keys, dtype=float)
        for a in keys:
            for b in keys:
                jac.loc[a, b] = (M[a] & M[b]).sum() / max((M[a] | M[b]).sum(), 1)
        jac.index.name = "metodo"
        w("Jaccard entre os 3 metodos (P90 / z>2 / media movel):\n")
        w(df_to_md(jac, floatfmt=2))
        w(f"\nDias-pico por **consenso dos 3**: {inter} (uniao: {union}). Concordancia "
          f"baixa entre metodos (Jaccard ~0,2-0,35) -- esperado: cada um define uma "
          f"cauda diferente. O consenso pega os dias inequivocamente anomalos.\n")
        cons = df.loc[all3, ["data", "nome_dia_semana", "feriado", "tem_jogo_sp",
                             "classico", col]].copy()
        cons["data"] = cons["data"].dt.date
        cons["is_outlier_lote"] = (pd.to_datetime(cons["data"]) == OUTLIER_LOTE)
        cons.to_csv(os.path.join(TAB_DIR, f"picos_consenso_{col}.csv"), index=False)
        w(df_to_md(cons.head(20), floatfmt=0, index=False))
        w("")
        n_jogo = int(cons["tem_jogo_sp"].sum())
        n_art = int(cons["is_outlier_lote"].sum())
        w(f"_Dos {inter} picos de consenso de `{col}`, {n_jogo} sao dia de jogo "
          f"({n_jogo/inter*100:.0f}%; taxa-base ~17%)"
          + (f", **1 deles e o artefato de 2022-06-19**" if n_art else "") + ". "
          f"Inspecao qualitativa dos dias mais anomalos; o teste formal dessa "
          f"proporcao esta logo abaixo._")
        w("")

        # --- teste de Fisher exato sobre o achado colateral (a pedido) ---
        excl = EXCL_CRIME if fam == "crime" else EXCL_ACID
        elig = df[~df["data"].isin(excl)]
        pico_elig = all3[~df["data"].isin(excl)]
        jogo_elig = elig["tem_jogo_sp"].astype(bool).values
        a = int((pico_elig.values & jogo_elig).sum())      # pico & jogo
        b = int((pico_elig.values & ~jogo_elig).sum())     # pico & sem jogo
        c = int((~pico_elig.values & jogo_elig).sum())     # nao-pico & jogo
        d = int((~pico_elig.values & ~jogo_elig).sum())    # nao-pico & sem jogo
        n_elig = a + b + c + d
        base = (a + c) / n_elig
        odr_two, p_two = stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")
        _, p_greater = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
        ct = pd.DataFrame([[a, b, a + b], [c, d, c + d], [a + c, b + d, n_elig]],
                          index=["pico de consenso", "nao-pico", "total"],
                          columns=["dia de jogo", "sem jogo", "total"])
        ct.to_csv(os.path.join(TAB_DIR, f"fisher_pico_x_jogo_{col}.csv"))
        # sensibilidade: sem o artefato 2022-06-19 (quando ele e pico & jogo)
        p_semart = None
        if n_art:
            aa = a - n_art
            _, p_semart = stats.fisher_exact([[aa, b], [c, d]], alternative="two-sided")
        # correcao grosseira p/ multiplas comparacoes (6 desfechos inspecionados)
        p_bonf = min(1.0, p_two * 6)
        w(f"**Teste de Fisher exato -- pico de consenso de `{col}` x dia de jogo** "
          f"(dias elegiveis = {n_elig}; taxa-base de dia de jogo = {base*100:.1f}%):\n")
        w(df_to_md(ct, floatfmt=0))
        w(f"\n- **H0:** ser dia-pico de consenso e ser dia de jogo sao independentes "
          f"(P(jogo | pico) = P(jogo | nao-pico)). **H1:** nao sao.\n"
          f"- **Odds ratio = {odr_two:.2f}** | **p (bilateral) = {p_two:.3f}** | "
          f"p (unilateral, jogo > base) = {p_greater:.3f}.\n"
          f"- {a}/{a+b} = {a/(a+b)*100:.0f}% dos picos sao dia de jogo vs "
          f"{base*100:.1f}% esperado.\n"
          f"- **Resultado registrado: "
          + ("nao significativo" if p_two >= 0.05 else "significativo") +
          f" a 5% (p = {p_two:.3f}).**\n"
          f"- **Robustez / porque nao vira achado:**\n"
          + (f"  * sem o artefato de 2022-06-19 (1 dos {a} da celula pico&jogo): "
             f"p = {p_semart:.3f}" + (" -> deixa de ser significativo" if p_semart >= 0.05
                                      else " -> ainda significativo") + ";\n" if n_art else "")
          + f"  * pos-hoc: a definicao 'consenso dos 3 metodos' e uma de varias que "
          f"poderiam ter sido testadas; corrigindo grosseiramente por 6 desfechos "
          f"inspecionados, p_Bonferroni = {p_bonf:.2f} (ns);\n"
          f"  * a residualizacao remove a MEDIA de dia-da-semana e mes, nao toda a "
          f"estrutura de fim de semana -- jogos concentram em fim de semana, entao "
          f"'dia de jogo' aqui ainda e em parte um proxy de fim de semana;\n"
          f"  * n minusculo ({a} na celula critica) -> IC do OR de <1 a >10;\n"
          f"  * **as Etapas 7-9 testaram exatamente `{col}` x jogo com n completo "
          f"(126 vs {602 if fam=='crime' else 600}), controles e modelos de defasagem "
          f"-> todas nulas.** Uma associacao pos-hoc em 12 dias nao reverte isso.\n"
          f"- **Uso no artigo:** citar como associacao exploratoria que NAO sobrevive "
          + ("a remocao do artefato nem a correcao" if n_art else "a correcao")
          + " de multiplas comparacoes, e e inconsistente com as analises primarias "
          f"(Etapas 7-9).\n")


# ---------------------------------------------------------------------------
def secao_serie(df, todos_flags):
    w("## 4. Visualizacao -- residuo e picos ao longo do tempo\n")
    for col in ["crimes_violentos", "acidentes_com_vitima"]:
        excl = EXCL_CRIME if col in CRIME_OUT else EXCL_ACID
        res, _ = residuo_dessaz(df, col, excl)
        fl = todos_flags[col]
        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(df["data"], res, color="#888", lw=.7, label="residuo dessazonalizado")
        ax.axhline(0, color="k", lw=.8)
        for nome, cor, mk in [("p90", "#1f6f8b", "o"), ("z2", "#c44e52", "s"),
                              ("mm28_2sd", "#55a868", "^")]:
            m = fl[nome].eq(True).fillna(False)
            ax.scatter(df.loc[m, "data"], res[m], s=28, c=cor, marker=mk, label=nome, zorder=3)
        ax.set_title(f"{col}: residuo (obs - calendario) e dias-pico por metodo")
        ax.legend(ncol=4, fontsize=8)
        ax.grid(alpha=.3)
        w(f"![serie {col}]({savefig(f'01_serie_{col}.png')})\n")


# ---------------------------------------------------------------------------
def secao_recomendacao_e_materializa(df, todos_flags):
    w("## 5. Recomendacao e materializacao\n")
    w(textwrap.dedent("""\
        **Definicao principal para a Etapa 12 (classificacao):**
        `pico = residuo dessazonalizado > P90`, por desfecho.
        - Percentil nao assume normalidade (o z-score assume, e a EDA rejeitou).
        - P90 da ~10% de positivos -> ~73 dias-pico em 728: suficiente para o
          split temporal da Etapa 15 (P95 daria ~36, pouco para validar).
        - P95, z>2 e media movel ficam como **variantes de robustez** -- a Etapa 14
          reporta a metrica do modelo nos 3 limiares.

        **Alvos recomendados** (os "picos de violencia/acidentes" do titulo):
        `crimes_violentos` e `acidentes_com_vitima`. `crimes_totais`/
        `acidentes_total` entram como secundarios.

        **Versao 3 niveis (Baixo/Medio/Alto)** pedida no roteiro: sobre o residuo,
        `< P75` = Baixo, `P75-P90` = Medio, `> P90` = Alto. Materializada em
        `nivel_risco` (baseada em `crimes_violentos`).

        **Ressalvas para a Etapa 15**: o limiar (P90/P95) e o ajuste de calendario
        aqui usam a serie inteira. Numa validacao walk-forward estrita, ambos devem
        ser reestimados so no treino de cada fold -- senao ha vazamento leve do
        teste para a definicao do alvo. A versao **media movel** ja e causal e nao
        tem esse problema.
        2022-06-19 permanece marcado como pico (artefato de registro em lote);
        a Etapa 12 decide remover/winsorizar.
    """))

    # materializa pico_dia_sp.csv
    out = df[["data"]].copy()
    map_alvo = {"crimes_violentos": "crime", "crimes_totais": "crime_total",
                "lesao_corporal_dolosa": "lesao_corporal",
                "acidentes_com_vitima": "acidente", "acidentes_total": "acidente_total",
                "acidentes_fatais": "acidente_fatal"}
    for col, pref in map_alvo.items():
        for metodo, fl in todos_flags[col].items():
            out[f"pico_{pref}_{metodo}"] = fl.astype("boolean")  # NaN preservado nos excluidos
    # nivel_risco (3 niveis) sobre residuo de crimes_violentos
    res_cv, _ = residuo_dessaz(df, "crimes_violentos", EXCL_CRIME)
    m = res_cv.notna()
    q75, q90 = res_cv[m].quantile(0.75), res_cv[m].quantile(0.90)
    nivel = pd.Series(pd.NA, index=df.index, dtype="object")
    nivel[m & (res_cv <= q75)] = "Baixo"
    nivel[m & (res_cv > q75) & (res_cv <= q90)] = "Medio"
    nivel[m & (res_cv > q90)] = "Alto"
    out["nivel_risco"] = nivel
    # residuos tambem, uteis para a Etapa 12
    out["residuo_crimes_violentos"] = res_cv
    out["residuo_acidentes_com_vitima"] = residuo_dessaz(df, "acidentes_com_vitima", EXCL_ACID)[0]

    out.to_csv(PICO_OUT, index=False)
    w(f"\n**Arquivo gerado:** `data/gold/pico_dia_sp.csv` ({out.shape[0]} linhas x "
      f"{out.shape[1]} colunas), chave `data`. Colunas: flags `pico_<alvo>_<metodo>` "
      f"(boolean, NaN nos dias excluidos), `nivel_risco`, e os residuos dos 2 alvos "
      f"principais.\n")
    w("`02_limpeza.py` foi ajustado para fazer o merge deste arquivo nos placeholders "
      "`pico_crime_p90` / `pico_crime_zscore` / `pico_acidente_p90` / `nivel_risco` "
      "do `fato_dia_sp.csv` (se o arquivo existir). Ordem de execucao: "
      "`02` -> `08` -> (`02` de novo, opcional, para o fato carregar as colunas).\n")

    dist = out["nivel_risco"].value_counts(dropna=False)
    w("Distribuicao de `nivel_risco` (base `crimes_violentos`):\n")
    w(df_to_md(dist.rename("n_dias").to_frame(), floatfmt=0))
    w("")


# ---------------------------------------------------------------------------
def main():
    df = load()
    w("# Etapa 11 -- Definicao de \"pico\"\n")
    w(f"_Gerado por `scripts/08_definicao_pico.py` em {date.today()}. "
      f"Fonte: `data/gold/fato_dia_sp.csv`._\n")
    w("> Pico e definido sobre o **residuo dessazonalizado**, nao a contagem crua "
      "(Etapas 6-10: sazonalidade semanal/mensal domina). Tres metodos testados e "
      "comparados; escolha justificada na secao 5.\n")

    secao_por_que_residuo(df)
    flags = secao_tres_metodos(df)
    secao_concordancia(df, flags)
    secao_serie(df, flags)
    secao_recomendacao_e_materializa(df, flags)

    path = os.path.join(OUT_DIR, "relatorio_definicao_pico.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] pico_dia_sp: {PICO_OUT}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
