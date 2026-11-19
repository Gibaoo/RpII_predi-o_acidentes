"""
V2 / Fase 1 -- 31_jogos_horarios.py
Um registro por jogo em SP capital (2022-2023) com o inicio em horario de
Brasilia, corrigindo o fuso da base de futebol.

BUG DO PIPELINE DIARIO (corrigido aqui, documentado no Changelog/CLAUDE.md):
a coluna `time` do BR-Football-Dataset esta no horario do Reino Unido
(Europe/London: GMT no inverno europeu, BST no verao) e `date` e a data no
Reino Unido. 02_limpeza.py usava `date` como data do jogo e `time` (hora UK)
para jogo_noturno -> jogos noturnos de Brasilia ficavam no dia seguinte e
jogo_noturno estava errado.

Correcao: timestamp = date + time, tz_localize('Europe/London'),
tz_convert('America/Sao_Paulo'). Brasil sem horario de verao desde 2019.

Horarios com segundos != 00 (ex. 01:24:28): nao sao horarios de inicio
oficiais (inicios sao em :00/:15/:30/:45); parecem carimbo de coleta. Sao
arredondados para os 30 min mais proximos e marcados `horario_aproximado`.

Tambem roda a checagem pedida no prompt V2: o GLM diario da Etapa 7 com as
datas de jogo corrigidas (mesma especificacao, so troca tem_jogo_sp).

CALENDARIO COMPLETO (aprovado pelo usuario em 2026-11-15): os jogos do
BR-Football-Dataset (Serie A + Copa do Brasil, `na_base_original=True`) sao
unidos aos de data/bronze/jogos_complementares.csv (Paulistao, Libertadores,
Sul-Americana, Recopa e 1 jogo de Serie A ausente da base; gerado por
31a_jogos_complementares.py a partir da Wikipedia). Estadio/cidade de TODOS
conferidos na Wikipedia; mando fora da capital (Barueri, Vila Belmiro) e campo
neutro ficam com incluir_analise=False (motivo_exclusao).

Saidas:
  data/silver/jogos_sp_horario.csv
  reports/janelas/fase1/tabelas/jogos_*.csv, glm_diario_datas_corrigidas.csv

Rodar:  python scripts/31_jogos_horarios.py
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE = os.path.join(BASE, "data", "bronze")
SILVER = os.path.join(BASE, "data", "silver")
GOLD = os.path.join(BASE, "data", "gold")
TAB = os.path.join(BASE, "reports", "janelas", "fase1", "tabelas")
os.makedirs(TAB, exist_ok=True)

MANDANTES = ["Corinthians", "Palmeiras", "Sao Paulo"]
GRUPO_CLASSICO = ["Corinthians", "Palmeiras", "Sao Paulo", "Santos"]
# A base NAO informa o estadio. Assume-se o estadio habitual de cada clube
# (limitacao declarada). Coordenadas = as mesmas da Etapa 10 (07_analise_espacial.py).
ESTADIO = {
    "Corinthians": ("Neo Quimica Arena", -23.545278, -46.474167),
    "Palmeiras": ("Allianz Parque", -23.527500, -46.678611),
    "Sao Paulo": ("Morumbi", -23.600278, -46.719444),
}
DURACAO_JANELA_H = 2  # pre = 2h antes; durante = inicio..+2h; pos = +2h..+4h


def carrega_jogos(so_base_original=False):
    df = pd.read_csv(os.path.join(BRONZE, "BR-Football-Dataset.csv"))
    df = df[df["home"].isin(MANDANTES)].copy()
    df["data_uk"] = pd.to_datetime(df["date"])
    # margem de 1 dia nas pontas para nao perder jogo que muda de ano na conversao
    df = df[(df["data_uk"] >= "2021-12-31") & (df["data_uk"] <= "2024-01-01")].copy()

    ts_uk = pd.to_datetime(df["date"] + " " + df["time"], format="%Y-%m-%d %H:%M:%S")
    loc = ts_uk.dt.tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT")
    assert loc.notna().all(), "horario ambiguo/inexistente na transicao de DST do Reino Unido"
    br = loc.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)

    df["horario_uk"] = df["time"]
    df["offset_uk_h"] = loc.map(lambda t: t.utcoffset().total_seconds() / 3600)
    df["inicio_br_bruto"] = br
    df["horario_aproximado"] = ~df["time"].str.endswith(":00")
    df["inicio_br"] = br.where(~df["horario_aproximado"], br.dt.round("30min"))
    df["data_br"] = df["inicio_br"].dt.normalize()
    df = df[(df["data_br"] >= "2022-01-01") & (df["data_br"] <= "2023-12-31")].copy()

    # resultado: ht_result = resultado do time da casa (home team), nao 1o tempo
    gols_ok = np.select([df["home_goal"] > df["away_goal"], df["home_goal"] == df["away_goal"]],
                        ["WON", "DRAW"], "LOST")
    n_incons = int((gols_ok != df["ht_result"]).sum())
    assert n_incons == 0, f"ht_result inconsistente com gols em {n_incons} jogos"

    out = pd.DataFrame({
        "jogo_id": df["data_br"].dt.strftime("%Y%m%d") + "_" + df["home"].str.replace(" ", ""),
        "data_br": df["data_br"].dt.date,
        "inicio_br": df["inicio_br"],
        "fim_janela_durante": df["inicio_br"] + pd.Timedelta(hours=DURACAO_JANELA_H),
        "inicio_br_bruto": df["inicio_br_bruto"],
        "horario_aproximado": df["horario_aproximado"],
        "data_uk": df["data_uk"].dt.date,
        "horario_uk": df["horario_uk"],
        "offset_uk_h": df["offset_uk_h"],
        "mudou_data": df["data_br"].dt.date != df["data_uk"].dt.date,
        "mandante": df["home"], "visitante": df["away"],
        "competicao": df["tournament"],
        "classico": df["away"].isin(GRUPO_CLASSICO),
        "hora_inicio": df["inicio_br"].dt.hour + df["inicio_br"].dt.minute / 60,
        "noturno": df["inicio_br"].dt.hour >= 19,
        "noturno_antigo_bug": pd.to_datetime(df["time"], format="%H:%M:%S").dt.hour >= 19,
        "dia_semana": (df["inicio_br"].dt.weekday + 1) % 7,  # 0=domingo (= calendario_sp)
        "fim_de_semana": df["inicio_br"].dt.weekday >= 5,
        "estadio": df["home"].map(lambda c: ESTADIO[c][0]),
        "estadio_lat": df["home"].map(lambda c: ESTADIO[c][1]),
        "estadio_lon": df["home"].map(lambda c: ESTADIO[c][2]),
        "estadio_assumido": True,
        "gols_mandante": df["home_goal"], "gols_visitante": df["away_goal"],
        "resultado_mandante": df["ht_result"].map({"WON": "vitoria", "DRAW": "empate", "LOST": "derrota"}),
        "fonte_jogo": "br_football_dataset",
    }).sort_values("inicio_br").reset_index(drop=True)

    if so_base_original:  # usado por 31a para conferir os 137 (evita dependencia circular)
        return out
    out["na_base_original"] = True
    out["origem"] = "br_football_dataset"
    out["horario_confirmado"] = True

    # conferencia com a Wikipedia (31a): estadio/cidade reais; mando fora da capital sai da analise
    conf = pd.read_csv(os.path.join(BRONZE, "jogos_base_conferencia_wikipedia.csv"))
    assert conf["hora_bate_wiki"].all(), "horario convertido diverge da Wikipedia em algum jogo"
    out = out.merge(conf[["jogo_id", "estadio_real", "cidade_real", "fora_da_capital", "fonte_jogo", "fonte_extra",
                          "publico", "publico_status"]]
                    .rename(columns={"fonte_jogo": "fonte_conferencia"}), on="jogo_id", how="left")
    out["estadio"] = out["estadio_real"].fillna(out["estadio"])
    out["cidade"] = out["cidade_real"]
    out = out.drop(columns=["estadio_real", "cidade_real"])

    out = pd.concat([out, carrega_complementares()], ignore_index=True)
    out["estadio_assumido"] = False  # todos conferidos na Wikipedia (31a)
    out["estadio_lat"] = out["estadio"].map(lambda e: COORD_ESTADIO.get(e, (None, None))[0])
    out["estadio_lon"] = out["estadio"].map(lambda e: COORD_ESTADIO.get(e, (None, None))[1])
    out["motivo_exclusao"] = np.select(
        [~out["horario_confirmado"], out["fora_da_capital"] & out["cidade"].isin(CIDADES_MANDO_ESTADO_SP),
         out["fora_da_capital"]],
        ["horario_nao_confirmado", "mando_fora_da_capital", "campo_neutro_fora_do_estado"], "")
    out["incluir_analise"] = out["motivo_exclusao"] == ""
    out = out.sort_values("inicio_br").reset_index(drop=True)

    # publico: so faz sentido para jogos na capital; ausente = NaN (nunca zero). Restricao COVID (teto de 70%
    # em todos os estadios do estado de 23/01 a 09/03/2022) marcada por regra, nao so onde a pagina anota.
    out["publico"] = pd.to_numeric(out["publico"], errors="coerce")
    out.loc[out["fora_da_capital"].astype(bool), ["publico", "publico_status"]] = [np.nan, "fora_da_capital"]
    dt = pd.to_datetime(out["data_br"])
    covid = dt.between(COVID_INI, COVID_FIM) & out["publico_status"].isin(["ok", "capacidade_restrita"])
    out.loc[covid, "publico_status"] = "capacidade_restrita"
    out["publico_restricao_fonte"] = np.where(covid, COVID_FONTE, None)
    out["portoes_fechados"] = out["publico_status"] == "portoes_fechados"

    cal = pd.read_csv(os.path.join(SILVER, "calendario_sp.csv"), parse_dates=["data"])
    fer = dict(zip(cal["data"].dt.date, cal["feriado"]))
    out["feriado"] = out["data_br"].map(fer).astype(bool)
    inc = out[out["incluir_analise"]]
    out["n_jogos_no_dia"] = out["data_br"].map(inc.groupby("data_br").size()).fillna(0).astype(int)
    assert out["jogo_id"].is_unique
    return out


COORD_ESTADIO = {v[0]: (v[1], v[2]) for v in ESTADIO.values()}
COVID_INI, COVID_FIM = pd.Timestamp("2022-01-23"), pd.Timestamp("2022-03-09")
COVID_FONTE = ("https://www.mktesportivo.com/2022/01/por-pandemia-sao-paulo-limita-publico-em-estadios-em-70-da-capacidade/ ; "
               "https://agenciabrasil.ebc.com.br/en/geral/noticia/2022-03/government-sp-releases-100-public-football-games-stadiums")
CIDADES_MANDO_ESTADO_SP = {"Barueri", "Santos"}
COMP_PT = {"Campeonato Paulista": "Campeonato Paulista", "Copa Libertadores": "Copa Libertadores",
           "Copa Sudamericana": "Copa Sul-Americana", "Recopa Sudamericana": "Recopa Sul-Americana",
           "Serie A": "Serie A", "Copa do Brasil": "Copa do Brasil", "Supercopa do Brasil": "Supercopa do Brasil",
           "Mundial de Clubes": "Mundial de Clubes"}


def _sem_acento(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))


def carrega_complementares():
    """data/bronze/jogos_complementares.csv (gerado por 31a a partir da Wikipedia)."""
    c = pd.read_csv(os.path.join(BRONZE, "jogos_complementares.csv"))
    ini = pd.to_datetime(c["data_br"] + " " + c["horario_br"].fillna("00:00"))
    ini = ini.where(c["horario_confirmado"])
    vis = c["visitante"].map(_sem_acento)
    gols = c["placar"].str.extract(r"(\d+)\s*-\s*(\d+)").astype(float)
    res = np.select([gols[0] > gols[1], gols[0] == gols[1]], ["vitoria", "empate"], "derrota")
    return pd.DataFrame({
        "jogo_id": pd.to_datetime(c["data_br"]).dt.strftime("%Y%m%d") + "_" + c["mandante"].str.replace(" ", ""),
        "data_br": pd.to_datetime(c["data_br"]).dt.date,
        "inicio_br": ini, "fim_janela_durante": ini + pd.Timedelta(hours=DURACAO_JANELA_H),
        "inicio_br_bruto": ini, "horario_aproximado": False, "mudou_data": False,
        "mandante": c["mandante"], "visitante": vis, "competicao": c["competicao"].map(COMP_PT),
        "fase": c["fase"], "classico": vis.isin(GRUPO_CLASSICO),
        "hora_inicio": ini.dt.hour + ini.dt.minute / 60, "noturno": ini.dt.hour >= 19,
        "dia_semana": (pd.to_datetime(c["data_br"]).dt.weekday + 1) % 7,
        "fim_de_semana": pd.to_datetime(c["data_br"]).dt.weekday >= 5,
        "estadio": c["estadio"], "cidade": c["cidade"], "fora_da_capital": c["fora_da_capital"],
        "gols_mandante": gols[0], "gols_visitante": gols[1],
        "resultado_mandante": np.where(gols[0].notna(), res, None),
        "horario_confirmado": c["horario_confirmado"],
        "fonte_jogo": c["fonte_jogo"], "fonte_conferencia": c["fonte_conferencia"].fillna(c["fonte_sumula"]),
        "fonte_extra": c["fonte_extra"], "publico_wiki": c["publico_wiki"],
        "publico": c["publico"], "publico_status": c["publico_status"],
        "na_base_original": False, "origem": c["origem"],
    })


def carrega_fora_capital():
    """Jogos dos 4 times monitorados FORA da capital (data/bronze/jogos_fora_capital.csv, 31a): jogos fora de
    casa dos 3 clubes, jogos do Santos fora da capital (Vila Belmiro etc.) e os mandos da capital disputados
    fora dela (Barueri, Vila Belmiro). Horario ja convertido para Brasilia com o fuso da propria pagina.
    O publico do estadio NAO entra na analise (fica so como registro)."""
    f = pd.read_csv(os.path.join(BRONZE, "jogos_fora_capital.csv"), parse_dates=["inicio_br"])
    vis_m = f["visitante"].map(_sem_acento)
    man_m = f["mandante"].map(_sem_acento)
    f["jogo_id_fora"] = f["inicio_br"].dt.strftime("%Y%m%d_%H%M") + "_" + f["times_monitorados"].str.replace(" ", "")
    f["classico"] = man_m.isin(GRUPO_CLASSICO) & vis_m.isin(GRUPO_CLASSICO)
    f["noturno"] = f["inicio_br"].dt.hour >= 19
    f["fim_de_semana"] = f["inicio_br"].dt.weekday >= 5
    f["competicao"] = f["competicao"].map(COMP_PT).fillna(f["competicao"])
    f["incluir_analise"] = f["horario_confirmado"].astype(bool)
    assert f["jogo_id_fora"].is_unique
    return f


def resumos(jj):
    tabs = {}
    inc = jj[jj["incluir_analise"]].copy()
    inc["mes"] = pd.to_datetime(inc["data_br"]).dt.to_period("M").astype(str)
    tabs["jogos_por_competicao_origem"] = jj.groupby(["competicao", "na_base_original", "incluir_analise"]).size() \
        .reset_index(name="n")
    tabs["jogos_por_mes_calendario_completo"] = pd.crosstab(inc["mes"], inc["competicao"], margins=True,
                                                            margins_name="total").reset_index()
    tabs["jogos_excluidos"] = jj.loc[~jj["incluir_analise"], ["jogo_id", "competicao", "mandante", "visitante",
                                                            "estadio", "cidade", "motivo_exclusao",
                                                            "na_base_original", "fonte_extra"]]
    tabs["jogos_estadio_nao_habitual"] = inc.loc[inc["estadio"] != inc["mandante"].map(
        lambda c: ESTADIO.get(c, ("(sem estadio habitual na capital)",))[0]),
                                                 ["jogo_id", "competicao", "mandante", "visitante", "estadio",
                                                  "na_base_original"]]
    dup = inc.groupby("data_br").filter(lambda g: len(g) > 1)
    tabs["jogos_dias_com_2_jogos"] = dup[["data_br", "inicio_br", "mandante", "visitante", "competicao",
                                          "estadio", "na_base_original"]]
    j = jj[jj["na_base_original"]]
    tabs["jogos_horario_br"] = j["inicio_br"].dt.strftime("%H:%M").value_counts().rename_axis("inicio_br").reset_index(name="n")
    tabs["jogos_horario_uk"] = j["horario_uk"].value_counts().rename_axis("horario_uk").reset_index(name="n")
    tabs["jogos_por_competicao"] = j.groupby(["competicao", "mandante"]).size().reset_index(name="n")
    tabs["jogos_horario_aproximado"] = j.loc[j["horario_aproximado"], ["jogo_id", "competicao", "mandante", "visitante",
                                                                     "gols_mandante", "gols_visitante", "data_uk",
                                                                     "horario_uk", "inicio_br_bruto", "inicio_br"]]
    tabs["jogos_evidencia_fuso"] = j[j["jogo_id"].isin(["20230924_SaoPaulo", "20221113_Corinthians"])][
        ["jogo_id", "mandante", "visitante", "competicao", "data_uk", "horario_uk", "offset_uk_h", "inicio_br"]]
    tabs["jogos_noturno_antes_depois"] = pd.crosstab(j["noturno_antigo_bug"], j["noturno"]).rename_axis(
        index="noturno_antigo(hora UK>=19)", columns="noturno_corrigido(hora BR>=19)").reset_index()
    for k, v in tabs.items():
        v.to_csv(os.path.join(TAB, f"{k}.csv"), index=False)
    return tabs


def glm_diario_corrigido(j):
    """Reexecuta a especificacao da Etapa 7 (04_analise_jogo_vs_naojogo.py, secao 3):
    y ~ tem_jogo_sp + C(dia_semana) + feriado + C(mes), Poisson, HC1, mesmas exclusoes,
    trocando apenas tem_jogo_sp pela data de jogo corrigida (Brasilia)."""
    fato = pd.read_csv(os.path.join(GOLD, "fato_dia_sp.csv"), parse_dates=["data"])
    excl_c = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
    excl_a = excl_c | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}
    dias_jogo_br = set(pd.to_datetime(j.loc[j["na_base_original"], "data_br"]))
    dias_completo = set(pd.to_datetime(j.loc[j["incluir_analise"], "data_br"]))
    fato["jogo_antigo"] = fato["tem_jogo_sp"].astype(int)
    fato["jogo_corrigido"] = fato["data"].isin(dias_jogo_br).astype(int)
    fato["jogo_completo"] = fato["data"].isin(dias_completo).astype(int)
    status = pd.crosstab(fato["jogo_antigo"], fato["jogo_corrigido"])
    status.to_csv(os.path.join(TAB, "glm_diario_status_dias.csv"))

    familias = [("crime", ["crimes_totais", "crimes_violentos", "roubos_total", "furtos_total",
                           "lesao_corporal_dolosa", "homicidios_dolosos"], excl_c),
                ("acidente", ["acidentes_total", "acidentes_com_vitima", "atropelamentos",
                              "colisoes", "acidentes_fatais"], excl_a)]
    linhas = []
    for fam, outs, excl in familias:
        d = fato[~fato["data"].isin(excl)].copy()
        d["feriado"] = d["feriado"].astype(int)
        for col in outs:
            for versao in ("jogo_antigo", "jogo_corrigido", "jogo_completo"):
                m = smf.glm(f"{col} ~ {versao} + C(dia_semana) + feriado + C(mes)", data=d,
                            family=sm.families.Poisson()).fit(cov_type="HC1")
                ci = np.exp(m.conf_int().loc[versao])
                linhas.append({"familia": fam, "desfecho": col, "versao": versao,
                               "n_dias_jogo": int(d[versao].sum()),
                               "RR": np.exp(m.params[versao]), "IC95_lo": ci[0], "IC95_hi": ci[1],
                               "p": m.pvalues[versao]})
    res = pd.DataFrame(linhas)

    def bh(p):
        p = np.asarray(p); n = len(p); o = np.argsort(p)
        adj = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
        out = np.empty(n); out[o] = np.minimum(adj, 1); return out
    # BH 1: familia unica crime+acidente (= Etapa 7, para comparacao direta)
    # BH 2: uma familia por dominio (regra V2)
    for v in ("jogo_antigo", "jogo_corrigido", "jogo_completo"):
        mk = res["versao"] == v
        res.loc[mk, "p_BH_etapa7"] = bh(res.loc[mk, "p"])
        for fam in ("crime", "acidente"):
            mf = mk & (res["familia"] == fam)
            res.loc[mf, "p_BH_dominio"] = bh(res.loc[mf, "p"])
    res.to_csv(os.path.join(TAB, "glm_diario_datas_corrigidas.csv"), index=False)
    return res, status


if __name__ == "__main__":
    print("V2 Fase 1 / 31: jogos com horario de Brasilia")
    j = carrega_jogos()
    j.to_csv(os.path.join(SILVER, "jogos_sp_horario.csv"), index=False)
    fc = carrega_fora_capital()
    fc.to_csv(os.path.join(SILVER, "jogos_fora_capital_horario.csv"), index=False)
    print(f"  fora da capital: {len(fc)} jogos | incluir {fc['incluir_analise'].sum()} | RMSP "
          f"{fc['regiao_metropolitana_sp'].sum()} | mando proprio fora {fc['mando_proprio_fora_capital'].sum()}")
    ji = j[j["incluir_analise"]]
    print("  publico (capital):", ji["publico_status"].value_counts(dropna=False).to_dict(),
          "| NaN:", int(ji["publico"].isna().sum()))
    tabs = resumos(j)
    jo = j[j["na_base_original"]]
    print(f"  base original: {len(jo)} | mudam de data: {jo['mudou_data'].sum()} "
          f"| horario aproximado: {jo['horario_aproximado'].sum()} | fora da capital: {jo['fora_da_capital'].sum()}")
    print(f"  calendario completo: {len(j)} registros | incluir_analise {j['incluir_analise'].sum()} "
          f"| dias com 2 jogos: {(j[j['incluir_analise']].groupby('data_br').size() > 1).sum()}")
    for k in ("jogos_por_mes_calendario_completo", "jogos_excluidos", "jogos_estadio_nao_habitual",
              "jogos_dias_com_2_jogos"):
        print(tabs[k].to_string(index=False))
    res, status = glm_diario_corrigido(j)
    print(status)
    piv = res.pivot_table(index=["familia", "desfecho"], columns="versao", values=["RR", "p", "p_BH_dominio"])
    print(piv.round(3).to_string())
    print("[ok] data/silver/jogos_sp_horario.csv")
