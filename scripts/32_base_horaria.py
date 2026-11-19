"""
V2 / Fase 1 -- 32_base_horaria.py
Monta data/gold/fato_hora_sp.csv: 1 linha = 1 hora local (Brasilia), de
2022-01-01 00h a 2023-12-31 23h (17.520 linhas), com contagens por hora,
calendario, clima horario e a classificacao da janela de jogo.

Entradas: data/silver/{crime,acidentes}_eventos_sp.csv.gz (30), jogos_sp_horario.csv (31),
          calendario_sp.csv (02), bronze INMET.
Saidas:   data/gold/fato_hora_sp.csv, data/gold/fato_hora_sp_dicionario.csv,
          reports/janelas/fase1/tabelas/*, reports/janelas/fase1_base_horaria.md

REGRAS DA JANELA (documentadas tambem no relatorio):
  - linha do tempo continua (nao por dia): um jogo 21:30 tem POS ate 01:30 do dia seguinte;
  - s = inicio do jogo; PRE = [s-2h, s), DURANTE = [s, s+2h), POS = [s+2h, s+4h);
  - cada hora [hh:00, hh+1:00) entra na janela que contem o seu PONTO MEDIO hh:30
    (inicios em :30/:45 nao partem horas ao meio); hora_relativa = floor((hh:30 - s)/1h),
    guardada de -6 a +12 -> PRE = {-2,-1}, DURANTE = {0,1}, POS = {2,3};
  - hora perto de 2 jogos: prioridade DURANTE > POS > PRE (empate: jogo mais proximo),
    flag jogo_duplo quando 2+ jogos reivindicam a hora para PRE/DURANTE/POS;
  - FORA separado em fora_dia_jogo (mesma data de Brasilia de um jogo, fora das 3 janelas)
    e dia_sem_jogo (data sem jogo).

Contagens horarias usam SO registros com hora. Os sem hora entram como contagem DIARIA
(`sem_hora_<tipo>`, repetida nas 24 linhas do dia) para medir/declarar a perda.

Rodar:  python scripts/32_base_horaria.py
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE = os.path.join(BASE, "data", "bronze")
SILVER = os.path.join(BASE, "data", "silver")
GOLD = os.path.join(BASE, "data", "gold")
REP = os.path.join(BASE, "reports", "janelas")
TAB = os.path.join(REP, "fase1", "tabelas")
os.makedirs(TAB, exist_ok=True)

H_INI, H_FIM = pd.Timestamp("2022-01-01 00:00"), pd.Timestamp("2023-12-31 23:00")
EXCL_CENSURA = [pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")]
EXCL_LACUNA_INFOSIGA = [pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")]
EXCL_LOTE_FURTOS = [pd.Timestamp("2022-06-19")]

TIPOS_CRIME = {"crimes_violentos": "is_violento", "lesao_corporal_dolosa": "is_lesao_dolosa",
               "roubos_total": "is_roubo", "furtos_total": "is_furto"}
TIPOS_ACID = {"acidentes_total": None, "acidentes_com_vitima": "com_vitima",
              "atropelamentos": "atropelamento"}
PRIORIDADE = {"durante": 3, "pos": 2, "pre": 1}


# ---------------------------------------------------------------------------
def contagens():
    crime = pd.read_csv(os.path.join(SILVER, "crime_eventos_sp.csv.gz"),
                        usecols=["data", "timestamp", "tem_hora"] + list(TIPOS_CRIME.values()),
                        parse_dates=["data", "timestamp"])
    acid = pd.read_csv(os.path.join(SILVER, "acidentes_eventos_sp.csv.gz"),
                       usecols=["data", "timestamp", "tem_hora", "com_vitima", "atropelamento"],
                       parse_dates=["data", "timestamp"])
    acid["_todos"] = True
    horas = pd.date_range(H_INI, H_FIM, freq="h")
    dias = pd.date_range(H_INI.normalize(), H_FIM.normalize(), freq="D")
    hor, dia = pd.DataFrame(index=horas), pd.DataFrame(index=dias)
    for df, tipos in ((crime, TIPOS_CRIME), (acid, {k: (v or "_todos") for k, v in TIPOS_ACID.items()})):
        h = df["timestamp"].dt.floor("h")
        for tipo, flag in tipos.items():
            sel = df[flag].astype(bool)
            hor[tipo] = sel[df["tem_hora"]].groupby(h[df["tem_hora"]]).sum().reindex(horas, fill_value=0)
            dia[f"sem_hora_{tipo}"] = sel[~df["tem_hora"]].groupby(df.loc[~df["tem_hora"], "data"]).sum() \
                .reindex(dias, fill_value=0)
            dia[f"total_dia_{tipo}"] = sel.groupby(df["data"]).sum().reindex(dias, fill_value=0)
    return hor.astype(int), dia.astype(int)


def clima_horario():
    frames = []
    for ano in (2022, 2023):
        df = pd.read_csv(os.path.join(BRONZE, f"inmet_{ano}.csv"), sep=";", skiprows=8,
                         encoding="latin1", decimal=",")
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        utc = pd.to_datetime(df["Data"] + " " + df["Hora UTC"].str[:4], format="%Y/%m/%d %H%M")
        frames.append(pd.DataFrame({
            "ts": utc - pd.Timedelta(hours=3),  # UTC -> Brasilia (sem horario de verao desde 2019)
            "chuva_mm": pd.to_numeric(df["PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"], errors="coerce"),
            "temp_c": pd.to_numeric(df["TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)"], errors="coerce"),
        }))
    c = pd.concat(frames).set_index("ts")
    c[c <= -9999] = np.nan
    c = c[~c.index.duplicated()]
    return c.reindex(pd.date_range(H_INI, H_FIM, freq="h"))


def calendario():
    cal = pd.read_csv(os.path.join(SILVER, "calendario_sp.csv"), parse_dates=["data"])
    b = lambda s: s.astype(str).str.lower().eq("true")
    return pd.DataFrame({
        "data": cal["data"], "dia_semana": cal["dia_semana"], "ano": cal["ano"], "mes": cal["mes"],
        "feriado": b(cal["feriado"]), "vespera_feriado": b(cal["vespera_feriado"]),
        "ferias_escolares": b(cal["ferias_escolares"]), "recesso_escolar": b(cal["recesso_escolar"]),
    }).assign(ferias=lambda d: d["ferias_escolares"] | d["recesso_escolar"])


# ---------------------------------------------------------------------------
def classifica_janelas(horas, jogos):
    """Tabela longa (hora, jogo) para todo par com hora_relativa em [-6, 12]; depois escolhe
    1 jogo por hora (prioridade de janela, depois proximidade)."""
    meio = horas + pd.Timedelta(minutes=30)
    pares = []
    for _, g in jogos.iterrows():
        s = g["inicio_br"]
        mk = (meio >= s - pd.Timedelta(hours=7)) & (meio < s + pd.Timedelta(hours=14))
        dif_h = (meio[mk] - s) / pd.Timedelta(hours=1)
        hr = np.floor(dif_h).astype(int)
        ok = (hr >= -6) & (hr <= 12)
        pares.append(pd.DataFrame({"hora": horas[mk][ok], "jogo_id": g["jogo_id"],
                                   "hora_relativa": hr[ok], "dist_h": np.abs(dif_h[ok])}))
    p = pd.concat(pares, ignore_index=True)
    p["janela_jogo"] = np.select([p["hora_relativa"].isin([-2, -1]), p["hora_relativa"].isin([0, 1]),
                                  p["hora_relativa"].isin([2, 3])], ["pre", "durante", "pos"], "nenhuma")
    p["prio"] = p["janela_jogo"].map(PRIORIDADE).fillna(0)
    n_rev = p[p["prio"] > 0].groupby("hora").size()
    n_raio = p.groupby("hora").size()
    p = p.sort_values(["hora", "prio", "dist_h"], ascending=[True, False, True])
    esc = p.drop_duplicates("hora").set_index("hora")
    esc["jogo_duplo"] = n_rev.reindex(esc.index, fill_value=0) >= 2
    esc["n_jogos_ate_12h"] = n_raio.reindex(esc.index)
    # checagem: cada jogo deve ter exatamente 2 horas em cada janela (salvo sobreposicao)
    cont = p[p["prio"] > 0].groupby(["jogo_id", "janela_jogo"]).size().unstack(fill_value=0)
    return esc, cont


def classifica_fora(horas_idx, fora):
    """Mesma regra de janela (ponto medio hh:30, linha do tempo continua) para os jogos fora da capital.
    Por hora: janela de maior prioridade entre os jogos (durante > pos > pre), hora_relativa e id desse jogo,
    n_jogos_fora_simultaneos = quantos jogos tem a hora em PRE/DURANTE/POS, times envolvidos e se algum
    deles foi na Regiao Metropolitana de SP (Barueri etc.)."""
    meio = horas_idx + pd.Timedelta(minutes=30)
    pares = []
    for _, g in fora.iterrows():
        s0 = g["inicio_br"]
        mk = (meio >= s0 - pd.Timedelta(hours=7)) & (meio < s0 + pd.Timedelta(hours=14))
        dif = (meio[mk] - s0) / pd.Timedelta(hours=1)
        hr = np.floor(dif).astype(int)
        ok = (hr >= -6) & (hr <= 12)
        pares.append(pd.DataFrame({"hora": horas_idx[mk][ok], "jogo": g["jogo_id_fora"], "hr": hr[ok],
                                   "dist": np.abs(dif[ok]), "times": g["times_monitorados"],
                                   "rmsp": bool(g["regiao_metropolitana_sp"])}))
    p = pd.concat(pares, ignore_index=True)
    p["jan"] = np.select([p["hr"].isin([-2, -1]), p["hr"].isin([0, 1]), p["hr"].isin([2, 3])],
                         ["pre", "durante", "pos"], "nenhum")
    p["prio"] = p["jan"].map(PRIORIDADE).fillna(0)
    ativos = p[p["prio"] > 0]
    agg = ativos.groupby("hora").agg(
        n_jogos_fora_simultaneos=("jogo", "nunique"),
        times_fora_capital=("times", lambda x: "+".join(sorted({t for v in x for t in v.split("+")}))),
        fora_capital_rmsp=("rmsp", "any"))
    esc = p.sort_values(["hora", "prio", "dist"], ascending=[True, False, True]).drop_duplicates("hora") \
        .set_index("hora")
    out = pd.DataFrame({"janela_fora_capital": esc["jan"].where(esc["prio"] > 0),
                        "hora_relativa_fora_capital": esc["hr"],
                        "jogo_id_fora_capital": esc["jogo"]}).join(agg)
    return out


def monta_fato():
    hor, dia = contagens()
    jogos = pd.read_csv(os.path.join(SILVER, "jogos_sp_horario.csv"),
                        parse_dates=["inicio_br", "data_br"])
    cal = calendario()
    clima = clima_horario()

    f = hor.copy()
    f.index.name = "hora_ts"
    f = f.reset_index()
    f["data"] = f["hora_ts"].dt.normalize()
    f["hora_do_dia"] = f["hora_ts"].dt.hour
    f = f.merge(cal, on="data", how="left")
    f = f.merge(dia, left_on="data", right_index=True, how="left")
    f["chuva_mm"] = clima["chuva_mm"].to_numpy()
    f["temp_c"] = clima["temp_c"].to_numpy()
    f["chuva"] = (f["chuva_mm"] > 0).where(f["chuva_mm"].notna())
    seg = f["data"] - pd.to_timedelta((f["data"].dt.weekday), unit="D")  # segunda da semana
    f["semana_id"] = ((seg - seg.min()).dt.days // 7).astype(int)

    # calendario completo (principal) = jogos com incluir_analise; robustez = so os da base original
    todos = jogos
    jogos = todos[todos["incluir_analise"]].copy()
    jogos_orig = jogos[jogos["na_base_original"]]
    horas_idx = pd.DatetimeIndex(f["hora_ts"])

    esc, cont = classifica_janelas(horas_idx, jogos)
    f = f.merge(esc[["jogo_id", "hora_relativa", "janela_jogo", "jogo_duplo", "n_jogos_ate_12h"]],
                left_on="hora_ts", right_index=True, how="left")
    f["jogo_duplo"] = f["jogo_duplo"].eq(True)
    f["n_jogos_ate_12h"] = f["n_jogos_ate_12h"].fillna(0).astype(int)
    f["dia_de_jogo"] = f["data"].isin(set(jogos["data_br"]))
    f["janela"] = np.where(f["janela_jogo"].isin(["pre", "durante", "pos"]), f["janela_jogo"],
                           np.where(f["dia_de_jogo"], "fora_dia_jogo", "dia_sem_jogo"))
    f["janela4"] = np.where(f["janela"].isin(["fora_dia_jogo", "dia_sem_jogo"]), "fora", f["janela"])
    f.loc[f["hora_relativa"].isna(), "jogo_id"] = np.nan

    # robustez: mesma regra, so com a base original (BR-Football-Dataset, fuso e estadio corrigidos)
    esc_o, _ = classifica_janelas(horas_idx, jogos_orig)
    f = f.merge(esc_o[["hora_relativa", "janela_jogo"]].rename(
        columns={"hora_relativa": "hora_relativa_base_original", "janela_jogo": "_jj_o"}),
        left_on="hora_ts", right_index=True, how="left")
    f["dia_de_jogo_base_original"] = f["data"].isin(set(jogos_orig["data_br"]))
    f["janela_base_original"] = np.where(f["_jj_o"].isin(["pre", "durante", "pos"]), f["_jj_o"],
                                         np.where(f["dia_de_jogo_base_original"], "fora_dia_jogo", "dia_sem_jogo"))
    f = f.drop(columns=["_jj_o"])

    # categoria 2 (NAO exclusiva da 1a): jogos dos 4 times FORA da capital (fora de casa, Santos na Vila,
    # mandos da capital em Barueri/Vila Belmiro). Efeito de assistir pela TV / em bares na cidade.
    fora = pd.read_csv(os.path.join(SILVER, "jogos_fora_capital_horario.csv"), parse_dates=["inicio_br"])
    fora = fora[fora["incluir_analise"]]
    f = f.merge(classifica_fora(horas_idx, fora), left_on="hora_ts", right_index=True, how="left")
    f["janela_fora_capital"] = f["janela_fora_capital"].fillna("nenhum")
    f["n_jogos_fora_simultaneos"] = f["n_jogos_fora_simultaneos"].fillna(0).astype(int)
    f["fora_capital_rmsp"] = f["fora_capital_rmsp"].eq(True)
    f["hora_sem_jogo"] = (f["janela4"] == "fora") & (f["janela_fora_capital"] == "nenhum") \
        & ~f["dia_de_jogo"]

    # eventos de grande publico na capital SEM os 4 times (finais do Brasileirao Feminino e da Copinha):
    # decisao do usuario -> nem tratamento nem controle: flag nas horas PRE/DURANTE/POS, fora da amostra
    # principal da Fase 2 (robustez com essas horas de volta)
    ev = pd.read_csv(os.path.join(BRONZE, "jogos_grande_publico_sem_times_monitorados.csv"),
                     parse_dates=["inicio_br"]).rename(columns={"evento_id": "jogo_id"})
    esc_e, _ = classifica_janelas(horas_idx, ev)
    esc_e = esc_e[esc_e["janela_jogo"].isin(["pre", "durante", "pos"])]
    f["hora_evento_grande_publico"] = f["hora_ts"].map(esc_e["jogo_id"])
    f["excluir_evento_grande_publico"] = f["hora_evento_grande_publico"].notna()

    attrs = jogos.set_index("jogo_id")[["inicio_br", "mandante", "visitante", "competicao", "fase", "classico",
                                        "noturno", "fim_de_semana", "estadio", "estadio_lat", "estadio_lon",
                                        "resultado_mandante", "horario_aproximado", "na_base_original",
                                        "publico", "publico_status"]]
    attrs = attrs.rename(columns={c: f"jogo_{c}" for c in attrs.columns})
    f = f.merge(attrs, left_on="jogo_id", right_index=True, how="left")
    jd = jogos.groupby("data_br")["jogo_id"].agg("+".join)
    f["jogo_id_do_dia"] = f["data"].map(jd)

    f["excluir_crime"] = f["data"].isin(EXCL_CENSURA + EXCL_LOTE_FURTOS)
    f["excluir_sinistro"] = f["data"].isin(EXCL_CENSURA + EXCL_LACUNA_INFOSIGA)

    ordem = (["hora_ts", "data", "hora_do_dia", "dia_semana", "ano", "mes", "semana_id",
              "feriado", "vespera_feriado", "ferias", "ferias_escolares", "recesso_escolar",
              "chuva_mm", "chuva", "temp_c"]
             + list(TIPOS_CRIME) + list(TIPOS_ACID)
             + [f"sem_hora_{t}" for t in list(TIPOS_CRIME) + list(TIPOS_ACID)]
             + [f"total_dia_{t}" for t in list(TIPOS_CRIME) + list(TIPOS_ACID)]
             + ["janela", "janela4", "hora_relativa", "jogo_id", "jogo_duplo", "n_jogos_ate_12h",
                "dia_de_jogo", "jogo_id_do_dia"] + list(attrs.columns)
             + ["janela_base_original", "hora_relativa_base_original", "dia_de_jogo_base_original",
                "janela_fora_capital", "hora_relativa_fora_capital", "n_jogos_fora_simultaneos",
                "times_fora_capital", "jogo_id_fora_capital", "fora_capital_rmsp", "hora_sem_jogo",
                "hora_evento_grande_publico", "excluir_evento_grande_publico",
                "excluir_crime", "excluir_sinistro"])
    f = f[ordem]
    assert len(f) == 17520 and f["hora_ts"].is_unique
    return f, todos, cont


# ---------------------------------------------------------------------------
DICIONARIO = {
    "hora_ts": ("chave", "inicio da hora local (Brasilia), 2022-01-01 00:00 a 2023-12-31 23:00"),
    "data": ("calendario", "data local da hora"),
    "hora_do_dia": ("calendario", "0-23"),
    "dia_semana": ("calendario", "0=domingo ... 6=sabado (mesma convencao de calendario_sp.csv)"),
    "ano": ("calendario", "ano"), "mes": ("calendario", "1-12"),
    "semana_id": ("calendario", "indice da semana (segunda a domingo) desde 2021-12-27; cluster dos erros-padrao na Fase 2"),
    "feriado": ("calendario", "feriado nacional/estadual/municipal (02_limpeza.py)"),
    "vespera_feriado": ("calendario", "dia anterior a feriado"),
    "ferias": ("calendario", "ferias_escolares OU recesso_escolar (SME-SP)"),
    "ferias_escolares": ("calendario", "ferias escolares SME-SP"),
    "recesso_escolar": ("calendario", "recesso escolar SME-SP"),
    "chuva_mm": ("clima", "precipitacao da hora, INMET A701, UTC-3; NaN = falha do sensor"),
    "chuva": ("clima", "chuva_mm > 0 (NaN se chuva_mm ausente)"),
    "temp_c": ("clima", "temperatura do ar (bulbo seco) da hora, INMET A701"),
    "crimes_violentos": ("crimes", "registros COM hora nesta hora: CATEGORIAS_VIOLENTAS + ROUBO* (grao BO x natureza)"),
    "lesao_corporal_dolosa": ("crimes", "registros com hora: LESAO CORPORAL DOLOSA"),
    "roubos_total": ("crimes", "registros com hora: natureza comecando com ROUBO"),
    "furtos_total": ("crimes", "registros com hora: natureza comecando com FURTO"),
    "acidentes_total": ("sinistros", "sinistros com hora nesta hora (Infosiga, os 3 tipo_registro)"),
    "acidentes_com_vitima": ("sinistros", "sinistros com hora: SINISTRO NAO FATAL + SINISTRO FATAL"),
    "atropelamentos": ("sinistros", "sinistros com hora: tp_sinistro_atropelamento == S"),
    "janela": ("jogo", "pre | durante | pos | fora_dia_jogo | dia_sem_jogo (regras no relatorio da Fase 1)"),
    "janela4": ("jogo", "pre | durante | pos | fora (fora = fora_dia_jogo + dia_sem_jogo)"),
    "hora_relativa": ("jogo", "floor((hh:30 - inicio)/1h), -6..+12; NaN fora desse raio. PRE={-2,-1}, DURANTE={0,1}, POS={2,3}"),
    "jogo_id": ("jogo", "jogo associado a hora (so quando hora_relativa existe)"),
    "jogo_duplo": ("jogo", "2+ jogos reivindicam a hora para PRE/DURANTE/POS (prioridade durante>pos>pre)"),
    "n_jogos_ate_12h": ("jogo", "nº de jogos com esta hora em hora_relativa -6..+12"),
    "dia_de_jogo": ("jogo", "a data de Brasilia da hora tem jogo em SP capital (calendario completo, fuso corrigido)"),
    "jogo_id_do_dia": ("jogo", "jogo da data (independe de a hora estar perto dele)"),
    "jogo_inicio_br": ("jogo", "inicio do jogo associado, horario de Brasilia (fuso corrigido)"),
    "jogo_mandante": ("jogo", "Corinthians | Palmeiras | Sao Paulo"), "jogo_visitante": ("jogo", "visitante"),
    "jogo_competicao": ("jogo", "Serie A | Copa do Brasil | Campeonato Paulista | Copa Libertadores | Copa Sul-Americana | Recopa Sul-Americana"),
    "jogo_classico": ("jogo", "visitante tambem do grupo Corinthians/Palmeiras/Sao Paulo/Santos"),
    "jogo_noturno": ("jogo", "inicio >= 19h de Brasilia (corrigido)"),
    "jogo_fim_de_semana": ("jogo", "jogo em sabado/domingo (data de Brasilia)"),
    "jogo_estadio": ("jogo", "estadio REAL do jogo (conferido na Wikipedia, 31a)"),
    "jogo_fase": ("jogo", "fase/rodada (so jogos complementares; vazio na base original)"),
    "jogo_na_base_original": ("jogo", "True = jogo do BR-Football-Dataset; False = complementar (Wikipedia)"),
    "janela_base_original": ("jogo", "ROBUSTEZ: janela so com os jogos da base original (sem Paulistao/Libertadores/Sul-Americana/Recopa)"),
    "hora_relativa_base_original": ("jogo", "ROBUSTEZ: hora_relativa so com a base original"),
    "dia_de_jogo_base_original": ("jogo", "ROBUSTEZ: dia de jogo so com a base original"),
    "jogo_publico": ("jogo", "publico do jogo na capital (Wikipedia, total); NaN = ausente; 0 so com portoes fechados"),
    "jogo_publico_status": ("jogo", "ok | capacidade_restrita (COVID 23/01-09/03/2022, teto 70%) | portoes_fechados"),
    "janela_fora_capital": ("jogo_fora", "pre | durante | pos | nenhum -- jogos dos 4 times FORA da capital (TV/bares); nao exclusiva de `janela`"),
    "hora_relativa_fora_capital": ("jogo_fora", "hora relativa (-6..+12) ao jogo fora da capital escolhido"),
    "n_jogos_fora_simultaneos": ("jogo_fora", "nº de jogos fora da capital com esta hora em PRE/DURANTE/POS"),
    "times_fora_capital": ("jogo_fora", "times monitorados envolvidos nesses jogos (ex. Corinthians+Santos)"),
    "jogo_id_fora_capital": ("jogo_fora", "id do jogo fora da capital escolhido (prioridade durante>pos>pre)"),
    "fora_capital_rmsp": ("jogo_fora", "algum desses jogos foi na Regiao Metropolitana de SP (ex. Arena Barueri)"),
    "hora_evento_grande_publico": ("flag", "id do evento de grande publico SEM os 4 times (final Brasileirao Feminino/Copinha) cuja janela PRE/DURANTE/POS contem a hora"),
    "excluir_evento_grande_publico": ("flag", "True = hora fora da amostra principal da Fase 2 (nem tratamento nem controle); robustez com elas de volta"),
    "hora_sem_jogo": ("controle", "CONTROLE da Fase 2: fora das janelas da capital, janela_fora_capital=nenhum e data sem jogo na capital"),
    "jogo_estadio_lat": ("jogo", "latitude do estadio (Etapa 10)"), "jogo_estadio_lon": ("jogo", "longitude do estadio (Etapa 10)"),
    "jogo_resultado_mandante": ("jogo", "vitoria|empate|derrota -- so conhecido apos o jogo: usar so na janela POS"),
    "jogo_horario_aproximado": ("jogo", "horario original com segundos != 00, arredondado a 30 min"),
    "excluir_crime": ("flag", "dia fora das analises de crime: censura 2023-12-30/31 + lote de furtos 2022-06-19"),
    "excluir_sinistro": ("flag", "dia fora das analises de sinistro: censura 2023-12-30/31 + lacunas Infosiga 2022-01-17, 2023-08-07"),
}
for _t in list(TIPOS_CRIME) + list(TIPOS_ACID):
    _d = "crimes" if _t in TIPOS_CRIME else "sinistros"
    DICIONARIO[f"sem_hora_{_t}"] = (_d, f"DIARIO (repetido nas 24h do dia): registros de {_t} da data sem hora valida")
    DICIONARIO[f"total_dia_{_t}"] = (_d, f"DIARIO: total de {_t} na data (com + sem hora) = silver diario")


def dicionario(f):
    d = pd.DataFrame([{"coluna": c, "grupo": DICIONARIO[c][0], "descricao": DICIONARIO[c][1],
                       "dtype": str(f[c].dtype), "pct_nulo": round(100 * f[c].isna().mean(), 2)}
                      for c in f.columns])
    d.to_csv(os.path.join(GOLD, "fato_hora_sp_dicionario.csv"), index=False)
    return d


# ---------------------------------------------------------------------------
def teste_selecao(f, col_jogo="dia_de_jogo", sufixo=""):
    """A proporcao de registros SEM hora difere entre dias com e sem jogo?
    GLM binomial diario: (sem_hora, com_hora) ~ dia_de_jogo + C(dia_semana) + C(mes) + C(ano)
    + feriado + ferias, erros HC1. BH separado por dominio.
    col_jogo = dia_de_jogo (calendario completo) ou dia_de_jogo_base_original (robustez)."""
    d = f.drop_duplicates("data").copy()
    d["dia_de_jogo"] = d[col_jogo]
    for c in ("feriado", "ferias", "dia_de_jogo"):
        d[c] = d[c].astype(int)
    linhas = []
    for dom, tipos, excl in (("crimes", TIPOS_CRIME, "excluir_crime"), ("sinistros", TIPOS_ACID, "excluir_sinistro")):
        dd = d[~d[excl]]
        for t in tipos:
            sem, tot = dd[f"sem_hora_{t}"], dd[f"total_dia_{t}"]
            row = {"dominio": dom, "tipo": t, "n_dias": len(dd),
                   "pct_sem_hora_dia_jogo": 100 * sem[dd["dia_de_jogo"] == 1].sum() / tot[dd["dia_de_jogo"] == 1].sum(),
                   "pct_sem_hora_sem_jogo": 100 * sem[dd["dia_de_jogo"] == 0].sum() / tot[dd["dia_de_jogo"] == 0].sum()}
            tab = [[sem[dd["dia_de_jogo"] == 1].sum(), (tot - sem)[dd["dia_de_jogo"] == 1].sum()],
                   [sem[dd["dia_de_jogo"] == 0].sum(), (tot - sem)[dd["dia_de_jogo"] == 0].sum()]]
            row["fisher_OR_bruto"], row["fisher_p_bruto"] = stats.fisher_exact(tab)
            try:
                y = np.column_stack([sem, tot - sem])
                X = pd.get_dummies(dd[["dia_semana", "mes", "ano"]].astype(str), drop_first=True).astype(float)
                X[["dia_de_jogo", "feriado", "ferias"]] = dd[["dia_de_jogo", "feriado", "ferias"]].to_numpy()
                X = sm.add_constant(X)
                m = sm.GLM(y, X, family=sm.families.Binomial()).fit(cov_type="HC1")
                ci = np.exp(m.conf_int().loc["dia_de_jogo"])
                row.update({"OR_ajustado": np.exp(m.params["dia_de_jogo"]), "IC95_lo": ci[0], "IC95_hi": ci[1],
                            "p_ajustado": m.pvalues["dia_de_jogo"],
                            "sobredispersao": m.pearson_chi2 / m.df_resid})
            except Exception as e:  # noqa: BLE001 -- contagens muito pequenas (sinistros)
                row.update({"OR_ajustado": np.nan, "erro_modelo": str(e)[:80]})
            linhas.append(row)
    res = pd.DataFrame(linhas)
    for dom in ("crimes", "sinistros"):
        mk = (res["dominio"] == dom) & res["p_ajustado"].notna()
        p = res.loc[mk, "p_ajustado"].to_numpy()
        if len(p):
            o = np.argsort(p); n = len(p)
            adj = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
            out = np.empty(n); out[o] = np.minimum(adj, 1)
            res.loc[mk, "p_BH_dominio"] = out
    res.to_csv(os.path.join(TAB, f"teste_selecao_sem_hora{sufixo}.csv"), index=False)
    return res


def resumo_janelas(f):
    linhas = []
    for dom, tipos, excl in (("crimes", TIPOS_CRIME, "excluir_crime"), ("sinistros", TIPOS_ACID, "excluir_sinistro")):
        ff = f[~f[excl]]
        g = ff.groupby("janela")
        for t in tipos:
            for jan, gg in g:
                linhas.append({"dominio": dom, "tipo": t, "janela": jan, "n_horas": len(gg),
                               "media_por_hora": gg[t].mean(), "pct_horas_zero": 100 * (gg[t] == 0).mean(),
                               "p50": gg[t].median(), "p90": gg[t].quantile(.9)})
    r = pd.DataFrame(linhas)
    r.to_csv(os.path.join(TAB, "resumo_por_janela_bruto.csv"), index=False)
    return r


# ---------------------------------------------------------------------------
def md_tab(df, floatfmt=2):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cel = []
        for v in r:
            if isinstance(v, (float, np.floating)):
                cel.append("" if pd.isna(v) else f"{v:.{floatfmt}f}")
            else:
                cel.append(str(v))
        out.append("| " + " | ".join(cel) + " |")
    return "\n".join(out)


def secao_calendario(w, jall, jinc, f):
    tabs = {k: pd.read_csv(os.path.join(TAB, f"{k}.csv")) for k in
            ("jogos_por_mes_calendario_completo", "jogos_excluidos", "jogos_estadio_nao_habitual",
             "jogos_dias_com_2_jogos", "jogos_por_competicao_origem")}
    comp = pd.read_csv(os.path.join(BRONZE, "jogos_complementares.csv"))
    conf = pd.read_csv(os.path.join(BRONZE, "jogos_base_conferencia_wikipedia.csv"))
    w("## 1b. Calendário completo: Paulistão, Libertadores, Sul-Americana e Recopa\n")
    w("Aprovado pelo usuário (item opcional do prompt V2, ampliado para Sul-Americana e Recopa). Gerado por "
      "`scripts/31a_jogos_complementares.py` → `data/bronze/jogos_complementares.csv`.\n")
    w("**Fonte e verificação:**")
    w("- Primária: páginas de temporada de cada clube na Wikipédia em inglês (ex. *2022 SE Palmeiras season*), "
      "onde cada partida é um *football box* com data, **horário com fuso explícito** "
      "(`{{UTZ|21:00|-3}}` = UTC−3 = Brasília — confirma que o horário da fonte está em Brasília), "
      "mandante, cidade, estádio e link da súmula. As páginas de **edição** (ex. Paulistão 2022 na "
      "pt.wikipedia) trazem a fase de grupos só como tabela cruzada de placares, sem data/horário/estádio, "
      "por isso foram usadas como **conferência** onde têm football box. A tabela oficial da FPF exige "
      "desafio anti-robô (Cloudflare) e não foi usada.")
    w("- `fonte_jogo` = permalink da revisão exata (`...&oldid=REVID`); snapshots do wikitext e manifesto em "
      "`data/bronze/wikipedia/`.")
    w(f"- {int(comp['conferido_pagina_edicao'].sum())} jogos conferidos contra páginas de edição (Libertadores, "
      "Sul-Americana, Recopa, mata-mata do Paulistão 2023): **0 divergências de horário**. "
      f"Data conferida com o link da súmula do ge em todos que o têm: {int((~comp['data_sumula_confere']).sum())} "
      "divergências.")
    w("- Segunda fonte (busca manual, URL em `fonte_extra`) para os casos suspeitos: mandos fora do estádio "
      "habitual e o jogo de Série A ausente da base.")
    w(f"- Jogos sem horário confirmado: {int((~comp['horario_confirmado']).sum())} (a regra os deixaria com "
      "flag e fora da análise principal).\n")
    w("**A mesma fonte conferiu os 137 jogos da base original:** "
      f"{int(conf['hora_bate_wiki'].sum())}/137 com o horário convertido (fuso corrigido) **idêntico** ao da "
      "Wikipédia — confirmação independente da correção do fuso. Mas **"
      f"{int(conf['fora_da_capital'].sum())} dos 137 foram mandos fora da capital** (Arena Barueri e Vila "
      "Belmiro, por shows no Allianz/Morumbi) — saem da `janela` e passam para `janela_fora_capital` "
      "(seção 1d), junto com a final da Sul-Americana 2022 (campo neutro, Córdoba). Também apareceu 1 jogo de Série A que o BR-Football-Dataset não tem "
      "(Palmeiras × Bragantino, 13/05/2023, Allianz Parque — conferido em 2ª fonte); entrou no calendário.\n")
    w("Mandos dos 3 clubes da capital que NÃO entram na `janela` (estão em `janela_fora_capital`):\n")
    w(md_tab(tabs["jogos_excluidos"].drop(columns=["fonte_extra"])))
    w("\nJogos na capital em estádio não habitual (a análise espacial usa o estádio real):\n")
    w(md_tab(tabs["jogos_estadio_nao_habitual"]))
    w("\nJogos por competição (`na_base_original` = veio do BR-Football-Dataset):\n")
    w(md_tab(tabs["jogos_por_competicao_origem"]))
    w(f"\n**Total analisável: {len(jinc)} jogos** ({int(jinc['na_base_original'].sum())} da base original + "
      f"{int((~jinc['na_base_original']).sum())} novos). Por mês:\n")
    w(md_tab(tabs["jogos_por_mes_calendario_completo"]))
    jm = f[f["mes"] <= 3]
    h_novo = int(jm["janela"].isin(["pre", "durante", "pos"]).sum())
    h_orig = int(jm["janela_base_original"].isin(["pre", "durante", "pos"]).sum())
    d_novo = jm.loc[jm["dia_de_jogo"], "data"].nunique()
    d_orig = jm.loc[jm["dia_de_jogo_base_original"], "data"].nunique()
    w(f"\n- **Jan–mar (2 anos): horas de jogo (PRÉ+DURANTE+PÓS) passam de {h_orig} para {h_novo}**; dias de "
      f"jogo de {d_orig} para {d_novo}. A violação de positividade de jan–fev (Etapa 20) deixa de existir.")
    w(f"- **Dias com 2 jogos em SP capital: {len(tabs['jogos_dias_com_2_jogos'])}** — mesmo com {len(jinc)} jogos, "
      "nunca há 2 mandos na capital no mesmo dia; a regra de prioridade de janelas segue implementada, mas "
      "não é acionada.")
    novos = pd.to_datetime(jinc.loc[~jinc["na_base_original"], "inicio_br"]).dt.strftime("%H:%M").value_counts()
    w("- Horário de início dos jogos novos: " + ", ".join(f"{k} ({v})" for k, v in novos.items()) + ".\n")
    w("Na Fase 2 a análise principal usa o calendário completo (`janela`) e uma robustez roda só com a base "
      "original (`janela_base_original` — os 130 jogos do BR-Football-Dataset em SP capital, já com fuso e "
      "estádio corrigidos), para medir quanto a falta desses jogos mudava o resultado.\n")


def secao_santos_fora_publico(w, f, jall):
    fora = pd.read_csv(os.path.join(SILVER, "jogos_fora_capital_horario.csv"))
    vfuso = pd.read_csv(os.path.join(TAB, "conferencia_fuso_jogos_fora_capital.csv"))
    amostra = pd.read_csv(os.path.join(BRONZE, "publico_conferencia_amostra.csv"))
    gp = pd.read_csv(os.path.join(BRONZE, "jogos_grande_publico_sem_times_monitorados.csv"))
    jinc = jall[jall["incluir_analise"]]

    w("## 1c. Santos como 4º time monitorado\n")
    w("Decisão do usuário (substitui \"Santos fica de fora como mandante\"): Corinthians, Palmeiras, São Paulo e "
      "Santos. Páginas *2022/2023 Santos FC season* (Wikipédia em inglês) baixadas no mesmo padrão "
      "(permalink `oldid` em `fonte_jogo`). Nelas a data vem sem ano e o fuso como `[[UTC-03:00]]` — o parser "
      "foi ajustado (ano da própria página). O Santos foi **mandante na capital 1 vez** (Santos × Ferroviária, "
      "Paulistão, 28/01/2023, Canindé) — entra na `janela`. Seus jogos na capital como visitante já estavam. "
      "Os demais jogos do Santos (Vila Belmiro e fora) entram em `janela_fora_capital`.\n")

    w("## 1d. Jogos fora da capital (`janela_fora_capital`)\n")
    w("Todos os jogos oficiais dos 4 times disputados fora da capital: fora de casa dos 3 clubes, Santos na "
      "Vila Belmiro e em outros lugares, os mandos da capital em Barueri/Vila Belmiro e jogos no exterior. "
      "Mede o efeito de assistir pela TV/em bares na cidade. Coluna separada e **não exclusiva** de `janela` "
      "(uma hora pode estar nas duas). Mesma regra de janela (ponto médio hh:30, linha do tempo contínua).\n")
    w(f"- **{len(fora)} jogos** ({int(fora['incluir_analise'].sum())} com horário confirmado). Por competição:\n")
    w(md_tab(fora.groupby("competicao").size().rename_axis("competicao").reset_index(name="n")))
    tm = fora["times_monitorados"].str.split("+").explode().value_counts()
    w("\nJogos por time monitorado envolvido (um jogo entre dois monitorados conta para os dois): "
      + ", ".join(f"{k} {v}" for k, v in tm.items()) + ".")
    w(f"- Região Metropolitana de SP (`fora_capital_rmsp`): {int(fora['regiao_metropolitana_sp'].sum())} jogos "
      f"(Barueri, Santo André, São Bernardo, Diadema…); mandos dos clubes da capital fora dela: "
      f"{int(fora['mando_proprio_fora_capital'].sum())}.")
    w("- **Conversão de fuso** (horário local → Brasília com o fuso indicado na própria página: "
      "`inicio_br = hora_local + (−3 − offset)`). As páginas usam duas convenções: a do Corinthians dá hora "
      "local com fuso local (ex. La Paz `20:30 UTC−4` → 21:30), as de Palmeiras/São Paulo/Santos já dão a "
      "hora de Brasília marcada `UTC−3`. Offsets encontrados: "
      + ", ".join(f"UTC{int(k):+d} ({v})" for k, v in fora["utc_offset_local"].value_counts().items()) + ".")
    for fonte, g in vfuso.groupby("fonte_conf"):
        nome = {"br_football": "BR-Football-Dataset (UK → Brasília, fonte independente)",
                "pagina_edicao": "páginas de edição Libertadores/Sul-Americana (hora local + fuso local)"}[fonte]
        w(f"  - vs {nome}: {int(g['achou'].sum())} jogos pareados, {int(g['bate'].sum())} batem (≤15 min).")
    nc = int(fora["horario_corrigido_fonte"].notna().sum())
    w(f"  - Na 1ª passada houve {nc} divergências; uma 3ª fonte confirmou a fonte independente em todas e o "
      "horário foi corrigido com a URL em `horario_corrigido_fonte` (Goiás × São Paulo 18/10/2023 21h30; "
      "Santos × Cuiabá 06/11/2023 21h; Bahia × São Paulo 29/11/2023 20h; Santos × Newell's 06/06/2023 21h30; "
      "Santos × Corinthians 21/06/2023 20h, conflito entre as páginas do Santos e do Corinthians).")
    vc = f["janela_fora_capital"].value_counts()
    w(f"- Horas: PRÉ {vc.get('pre', 0)}, DURANTE {vc.get('durante', 0)}, PÓS {vc.get('pos', 0)}. "
      "Jogos simultâneos fora da capital (`n_jogos_fora_simultaneos`): "
      + ", ".join(f"{k} jogo(s): {v} h" for k, v in f.loc[f["n_jogos_fora_simultaneos"] > 0,
                                                            "n_jogos_fora_simultaneos"].value_counts()
                  .sort_index().items()) + "; times em `times_fora_capital`.")
    w("\nSobreposição das duas categorias (horas; linhas = `janela4` da capital, colunas = `janela_fora_capital`):\n")
    w(md_tab(pd.crosstab(f["janela4"], f["janela_fora_capital"]).reset_index()))
    w(f"\n- **Controle da Fase 2 = `hora_sem_jogo`**: {int(f['hora_sem_jogo'].sum())} horas sem nenhuma janela "
      "de jogo dos 4 times (nem na capital nem fora) e em data sem jogo na capital.\n")

    w("## 1e. Público dos jogos na capital\n")
    st = jinc["publico_status"].value_counts()
    w(f"- Integrado para os {len(jinc)} jogos da `janela` a partir das mesmas páginas (público **total** do "
      f"estádio). Cobertura: {int(jinc['publico'].notna().sum())}/{len(jinc)}; ausente vira NaN, nunca zero.")
    pf = jinc[jinc["publico_status"] == "portoes_fechados"]
    pf_txt = "; ".join(f"{r.mandante} × {r.visitante} ({str(r.data_br)[:10]})" for r in pf.itertuples())
    w("- Status: " + ", ".join(f"`{k}` {v}" for k, v in st.items()) + f". `portoes_fechados` = {pf_txt}, punição por cantos homofóbicos (nota da própria página) — público 0 real, não ausente. "
      "`capacidade_restrita` = jogos de 23/01 a 09/03/2022 (teto de 70% do governo estadual; a página só anota "
      "nos jogos do Corinthians, a regra foi aplicada a todos com a fonte em `publico_restricao_fonte`).")
    p = jinc.loc[jinc["publico_status"] == "ok", "publico"]
    fm = lambda x: f"{x:,.0f}".replace(",", ".")
    w(f"- Distribuição (status ok): mediana {fm(p.median())}, P25 {fm(p.quantile(.25))}, P75 "
      f"{fm(p.quantile(.75))}, mín {fm(p.min())}, máx {fm(p.max())}.")
    w("- Fora da capital o público do estádio não entra na análise (fica só como registro no bronze).")
    ok = amostra["concorda"].eq("exato").sum()
    nf = amostra["concorda"].eq("nao_encontrado").sum()
    w(f"\n**Conferência com 2ª fonte** (amostra estratificada de {len(amostra)} jogos, 7 por clube da capital + "
      "o jogo do Santos, semente fixa; tabela da FPF e fbref bloqueiam acesso automatizado (não contornado), "
      "borderô da CBF não testado — usadas fichas técnicas da imprensa, que reproduzem o borderô): "
      f"**{len(amostra) - nf} encontrados, {ok} idênticos**, {len(amostra) - nf - ok} com diferença de 0,6% "
      f"(Palmeiras × Grêmio: Wikipédia = ESPN 37.532; Gazeta 37.752), {nf} não encontrados. Observação: a "
      "Wikipédia usa o público **total**; algumas bases (ESPN) usam o pagante (0,4–1% menor). Tabela em "
      "`data/bronze/publico_conferencia_amostra.csv`.\n")

    w("## 1f. Jogos de grande público na capital sem os 4 times (verificação pedida — NADA incluído)\n")
    w("Busca na web por eventos de futebol com grande público nos estádios da capital em 2022–2023 sem o time "
      "principal masculino dos 4 clubes. Candidatos encontrados (não é uma lista exaustiva; aguardam decisão):\n")
    w(md_tab(gp.drop(columns=["fonte"])))
    w("\nNão foram encontrados jogos da seleção brasileira (masculina) na capital nesses anos. As finais da "
      "Copinha são de times sub-20 de clubes monitorados.\n")
    w(f"**Decisão do usuário:** não são tratamento nem controle. As horas PRÉ/DURANTE/PÓS desses 4 eventos "
      f"(horário de início confirmado na imprensa, URL em `fonte_horario`) ficam com "
      f"`excluir_evento_grande_publico = True` ({int(f['excluir_evento_grande_publico'].sum())} horas) e saem da "
      "amostra principal da Fase 2; robustez com elas de volta.\n")


def relatorio(f, jogos, cont, sel, resj):
    q = pd.read_csv(os.path.join(TAB, "qualidade_hora.csv"))
    conf = pd.read_csv(os.path.join(TAB, "conferencia_com_diario.csv"))
    per = pd.read_csv(os.path.join(TAB, "periodo_dos_sem_hora_crime.csv"))
    inval = pd.read_csv(os.path.join(TAB, "hora_formatos_invalidos.csv"))
    hbr = pd.read_csv(os.path.join(TAB, "jogos_horario_br.csv"))
    huk = pd.read_csv(os.path.join(TAB, "jogos_horario_uk.csv"))
    aprox = pd.read_csv(os.path.join(TAB, "jogos_horario_aproximado.csv"))
    evid = pd.read_csv(os.path.join(TAB, "jogos_evidencia_fuso.csv"))
    glm = pd.read_csv(os.path.join(TAB, "glm_diario_datas_corrigidas.csv"))
    stat = pd.read_csv(os.path.join(TAB, "glm_diario_status_dias.csv"), index_col=0)
    noct = pd.read_csv(os.path.join(TAB, "jogos_noturno_antes_depois.csv"))

    jall = jogos
    jogos = jall[jall["na_base_original"]]
    jinc = jall[jall["incluir_analise"]]
    nj = len(jogos)
    n_mud = int(jogos["mudou_data"].sum())
    n_noct_err = int((jogos["noturno"] != jogos["noturno_antigo_bug"]).sum())
    n_dias_jogo_antigo = int(stat.iloc[1].sum())
    n_dias_jogo_novo = int(stat.iloc[:, 1].sum())
    jan_ct = f["janela"].value_counts()
    cont_ok = ((cont[["pre", "durante", "pos"]] == 2).all(axis=1)).sum()
    clima_na = f[["chuva_mm", "temp_c"]].isna().sum()
    qg = q[q["recorte"] == "todos"].drop(columns=["recorte"])
    qa = q[q["recorte"] != "todos"][["dominio", "tipo", "recorte", "n", "pct_sem_hora", "pct_minuto_00",
                                    "pct_minuto_00_ou_30"]]
    glm_w = glm.pivot_table(index=["familia", "desfecho"], columns="versao",
                            values=["RR", "p", "p_BH_dominio"]).round(3)
    glm_w.columns = [f"{a}_{b.replace('jogo_', '')}" for a, b in glm_w.columns]
    glm_w = glm_w.reset_index()[["familia", "desfecho", "RR_antigo", "p_antigo", "RR_corrigido", "p_corrigido",
                                 "p_BH_dominio_corrigido", "RR_completo", "p_completo", "p_BH_dominio_completo"]]
    gc = glm[glm["versao"] == "jogo_completo"]
    sig_comp = gc[gc["p_BH_dominio"] < 0.05]
    fat = glm[(glm["desfecho"] == "acidentes_fatais") & (glm["versao"] == "jogo_corrigido")].iloc[0]
    n_sig_bh = int((glm[glm["versao"] == "jogo_corrigido"]["p_BH_dominio"] < 0.05).sum())
    n_sig_raw = glm[(glm["versao"] == "jogo_corrigido") & (glm["p"] < 0.05)]["desfecho"].tolist()

    L = []
    w = L.append
    w("# V2 / Fase 1 — Base horária e janelas de jogo\n")
    w("Gerado por `scripts/32_base_horaria.py` (lê saídas de `30_eventos_horarios.py` e "
      "`31_jogos_horarios.py`). Crimes e sinistros tratados como **domínios separados** em todas as "
      "tabelas abaixo. Nenhum modelo de efeito do jogo foi estimado nesta fase — isso é a Fase 2.\n")

    w("## 1. Bug do fuso na base de futebol (afeta o trabalho diário)\n")
    w("A coluna `time` do `BR-Football-Dataset.csv` está no horário do Reino Unido (Europe/London, "
      "GMT/BST) e `date` é a data no Reino Unido. Correção: `date`+`time` → "
      "`tz_localize('Europe/London')` → `tz_convert('America/Sao_Paulo')`. Evidências (horário oficial "
      "de Brasília citado no prompt V2, conferido contra a base):\n")
    w(md_tab(evid))
    w(f"\n- Horários UK na base (2022-2023, mandante SP capital) incluem 00:00, 00:30, 01:00, 01:30 e "
      f"01:45 — implausíveis como início em Brasília. Depois da conversão: "
      f"{', '.join(hbr['inicio_br'].astype(str).tolist())} (todos plausíveis).")
    w(f"- **{n_mud} de {nj} jogos ({100*n_mud/nj:.0f}%) mudam de data**: jogos noturnos de Brasília "
      f"estavam no dia seguinte.")
    w(f"- **`jogo_noturno` antigo (hora UK ≥ 19) errado em {n_noct_err}/{nj} jogos** "
      f"({100*n_noct_err/nj:.0f}%):\n")
    w(md_tab(noct))
    w(f"\n- **Os \"dias com 2 jogos\" do pipeline antigo eram artefato do bug**: dias de jogo passam de "
      f"{n_dias_jogo_antigo} (com {nj - n_dias_jogo_antigo} jogos \"duplos\") para {n_dias_jogo_novo} "
      f"(= {nj} jogos, nenhum dia com 2 jogos em SP capital). Status dos 730 dias (linhas = antigo, "
      f"colunas = corrigido):\n")
    w(md_tab(stat.reset_index().rename(columns={"jogo_antigo": "antigo \\ corrigido"})))
    w("\n### Horário estranho `01:24:28` (e outros com segundos ≠ 00)\n")
    w("Três jogos de SP capital têm segundos ≠ 00 — no conjunto inteiro da base são "
      "419/10.296 linhas (4%), com minutos variados (:59, :29, :01…), padrão de carimbo de coleta, não "
      "de horário oficial de início. O `01:24:28` é São Paulo × Flamengo, Copa do Brasil 2022 "
      "(placar 1×3 na base), que vira 21:24:28 em Brasília. Sem fonte oficial verificada para o "
      "horário de início, os 3 foram **arredondados para os 30 min mais próximos e marcados "
      "`horario_aproximado`** (impacto pequeno: a regra do ponto médio desloca no máximo 1 hora de "
      "janela, e só se o erro real for > 30 min).\n")
    w(md_tab(aprox))

    w("\n### Checagem: GLM diário da Etapa 7 com as datas corrigidas\n")
    w("Mesma especificação da Etapa 7 (`y ~ jogo + C(dia_semana) + feriado + C(mes)`, Poisson, HC1, "
      "mesmas exclusões), trocando só a data do jogo. `p_BH_dominio` = BH por domínio (regra V2); a "
      "coluna `p_BH_etapa7` (família única, como na Etapa 7) está no CSV.\n")
    w(md_tab(glm_w, 3))
    w(f"\n**Leitura:** o nulo diário se mantém — {n_sig_bh} desfecho(s) significativo(s) após BH por "
      f"domínio com as datas corrigidas. Sem correção, p < 0,05 só em: "
      f"{', '.join(n_sig_raw) if n_sig_raw else 'nenhum'}. O resíduo já conhecido de `acidentes_fatais` "
      f"fica um pouco mais forte (RR {fat['RR']:.3f}, p = {fat['p']:.3f}; p_BH = "
      f"{fat['p_BH_dominio']:.3f}) — continua não robusto à correção múltipla, mas é o candidato a "
      f"olhar com atenção na Fase 2. `homicidios_dolosos` troca de sinal (0,91 → 1,05), ambos ns.\n")
    if len(sig_comp):
        lst = "; ".join(f"`{r.desfecho}` RR {r.RR:.3f} (p = {r.p:.3f}, p_BH = {r.p_BH_dominio:.3f})"
                        for r in sig_comp.itertuples())
        w(f"**Com o calendário completo (colunas `_completo`, seção 1b), o nulo diário deixa de ser total:** "
          f"{lst}. Ou seja, parte do nulo antigo vinha de dias de Paulistão/Libertadores/Sul-Americana "
          "classificados como \"sem jogo\" (diluição + jan–mar sem nenhum jogo). É uma checagem no grão "
          "diário com a especificação simples da Etapa 7, **não** a estimativa do projeto: a Fase 2 testa "
          "isso direito (janelas, EF hora × dia da semana, placebo).\n")
    else:
        w("Com o calendário completo (colunas `_completo`, seção 1b) o nulo diário também se mantém.\n")
    secao_calendario(w, jall, jinc, f)
    secao_santos_fora_publico(w, f, jall)

    w("## 2. Qualidade da hora — CRIMES (SSP)\n")
    w("Hora de `HORA_OCORRENCIA_BO`; `NULL`/vazio = sem hora. Formatos aceitos `HH:MM`, `HH:MM:SS` e o "
      "artefato de célula do Excel `1900-01-01 HH:MM:SS` (hora válida). Datas no campo hora "
      "(ex. `2000-06-01 00:00:00`) = formato inválido → sem hora "
      f"({int(inval['n'].sum())} registros, lista em `fase1/tabelas/hora_formatos_invalidos.csv`). "
      "`razao_hora0_vs_vizinhas` < 1,2 em todos os tipos → **00:00 não é placeholder de hora "
      "desconhecida**.\n")
    w(md_tab(qg[qg["dominio"] == "crimes"].drop(columns=["dominio"])))
    w("\nPor arquivo (os 4 semestres) — números do prompt confirmados e estáveis entre arquivos:\n")
    w(md_tab(qa[qa["dominio"] == "crimes"].drop(columns=["dominio"])))
    w("\n- **Furtos: ~53% sem hora** (a vítima percebe depois); roubos ~8%, lesão corporal dolosa ~9%, "
      "`crimes_violentos` ~9% (puxado por roubos). O prompt citava ~7% para lesão numa amostra do "
      "2º sem/2023; na base completa é 8,6%.")
    w("- **Arredondamento**: ~33% no minuto :00 e ~53% em :00/:30 → grão de 1 hora (não menor), como "
      "previsto. Arredondamento para a hora cheia pode puxar registros de hh:59 para hh+1:00 — viés "
      "de no máximo 1 hora, simétrico entre dias com e sem jogo.")
    w("- `DESCR_PERIODO` dos registros sem hora (turno aproximado, não usado nas contagens horárias; "
      "fica para robustez):\n")
    w(md_tab(per[per["tipo"].isin(["crimes_violentos", "furtos_total"])]))

    w("\n## 3. Qualidade da hora — SINISTROS (Infosiga)\n")
    w(md_tab(qg[qg["dominio"] == "sinistros"].drop(columns=["dominio"])))
    w("\n" + md_tab(qa[qa["dominio"] == "sinistros"].drop(columns=["dominio"])))
    w("\n- Hora quase completa (0,1% sem hora) e **sem arredondamento relevante** (2,5% no :00, perto "
      "dos 1,7% esperados ao acaso) — a hora do sinistro é muito mais confiável que a do crime.")
    w("- O problema do sinistro é outro: **contagens horárias pequenas** (ver seção 6).\n")

    w("## 4. Conferência com o pipeline diário\n")
    w("Total por dia (com + sem hora) da extração horária vs `data/silver/*_diario_sp.csv` "
      "(`02_limpeza.py`): mesmo filtro e mesmo grão.\n")
    w(md_tab(conf))

    w("\n## 5. Base horária `data/gold/fato_hora_sp.csv`\n")
    w(f"- {len(f):,} linhas (1 = 1 hora local, 2022-01-01 00h → 2023-12-31 23h), {f.shape[1]} colunas; "
      f"dicionário em `data/gold/fato_hora_sp_dicionario.csv`.")
    w("- Contagens por hora **só com registros que têm hora**; os sem hora ficam em `sem_hora_<tipo>` "
      "(diário, repetido nas 24 linhas do dia) e `total_dia_<tipo>` (= silver diário).")
    w("- Calendário (`calendario_sp.csv`): hora do dia, dia da semana, mês, feriado, véspera, férias "
      "(= férias escolares ou recesso SME). Clima horário INMET A701 (UTC−3): `chuva_mm`, `temp_c`. "
      f"Horas sem leitura: chuva {int(clima_na['chuva_mm'])} ({100*clima_na['chuva_mm']/len(f):.1f}%), "
      f"temperatura {int(clima_na['temp_c'])} ({100*clima_na['temp_c']/len(f):.1f}%). Principais lacunas: "
      "sensor de chuva fora em 25/08–11/09/2023 (432 h); estação sem leitura em 27/11/2023; as 3 últimas "
      "horas de 2023-12-31 caem no arquivo INMET de 2024, ausente (dia já censurado); o resto são "
      "falhas horárias esparsas. NaN fica NaN (não zero) — a Fase 2 decide entre excluir ou imputar.")
    w("- Exclusões por domínio (flags, linhas mantidas): `excluir_crime` = 2023-12-30/31 (censura) + "
      "2022-06-19 (lote de furtos — 2.633 furtos, só 17% com hora, então o lote cai quase todo em "
      "`sem_hora_furtos_total`); `excluir_sinistro` = 2023-12-30/31 + 2022-01-17 e 2023-08-07 "
      "(lacunas Infosiga).\n")
    w("### Regras de classificação da janela\n")
    w("1. Linha do tempo contínua, não por dia: s = início (Brasília); PRÉ = [s−2h, s), "
      "DURANTE = [s, s+2h), PÓS = [s+2h, s+4h). Um jogo às 21:30 tem PÓS até 01:30 do dia seguinte.")
    w("2. Cada hora [hh:00, hh+1) entra na janela que contém o seu **ponto médio hh:30**. "
      "`hora_relativa` = ⌊(hh:30 − s)/1h⌋, de −6 a +12 → PRÉ = {−2,−1}, DURANTE = {0,1}, PÓS = {2,3}. "
      "Ex.: jogo 21:30 → PRÉ 19h–20h, DURANTE 21h–22h, PÓS 23h–00h; jogo 21:45 → PRÉ 20h–21h, "
      "DURANTE 22h–23h, PÓS 00h–01h.")
    w("3. Hora reivindicada por 2 jogos: prioridade DURANTE > PÓS > PRÉ (empate: jogo mais próximo), "
      "flag `jogo_duplo`.")
    w("4. FORA separado em `fora_dia_jogo` (mesma data de Brasília do jogo, fora das 3 janelas) e "
      "`dia_sem_jogo`.\n")
    w(f"Resultado (calendário completo): {cont_ok}/{len(cont)} jogos com exatamente 2 horas em cada janela; "
      f"`jogo_duplo` = {int(f['jogo_duplo'].sum())} horas. Horas por janela (calendário completo vs "
      f"só a base original, coluna `janela_base_original`, para a robustez da Fase 2):\n")
    jc = pd.DataFrame({"completo": jan_ct, "base_original": f["janela_base_original"].value_counts()})
    w(md_tab(jc.rename_axis("janela").reset_index()))
    w(f"\n- `hora_sem_jogo` (controle da Fase 2: nenhuma janela de jogo dos 4 times, nem na capital nem fora, "
      f"e data sem jogo na capital) = {int(f['hora_sem_jogo'].sum())} horas.")
    n_pos_vira = int(((f["janela"] == "pos") & (~f["dia_de_jogo"])).sum())
    n_resc = int(((f["janela"] == "dia_sem_jogo") & f["hora_relativa"].between(4, 12)).sum())
    w(f"\n- {n_pos_vira} horas de PÓS caem na madrugada do dia seguinte (data sem jogo).")
    w(f"- {n_resc} horas classificadas como `dia_sem_jogo` estão a +4…+12 h de um jogo da noite "
      "anterior (transbordamento para o dia seguinte). Ficam no grupo de comparação no modelo de "
      "janelas, mas o event study da Fase 2 (até +12) as isola via `hora_relativa`.\n")

    w("## 6. Escala das contagens horárias (motiva a definição de pico da Fase 2)\n")
    w("Média bruta por hora e % de horas com zero, por janela (sem controle nenhum — **não é "
      "estimativa de efeito**: as janelas caem em horários com nível próprio, o que a Fase 2 controla "
      "com EF hora × dia da semana).\n")
    for dom in ("crimes", "sinistros"):
        w(f"**{dom.upper()}**\n")
        r = resj[resj["dominio"] == dom].drop(columns=["dominio"])
        w(md_tab(r))
        w("")
    w("- Crimes: `crimes_violentos` tem dezenas de registros por hora; `lesao_corporal_dolosa` já é "
      "pequena por hora.")
    w("- Sinistros: `acidentes_com_vitima` tem poucos eventos por hora e `atropelamentos` é zero na "
      "maioria das horas → pico horário instável; testar o pico na soma da janela de 2 h (prompt, Fase 2).\n")

    w("## 7. Teste de seleção: a falta de hora depende do dia de jogo?\n")
    w("GLM binomial diário `(sem_hora, com_hora) ~ dia_de_jogo + C(dia_semana) + C(mes) + C(ano) + "
      "feriado + ferias`, erros HC1, dias excluídos por domínio; BH por domínio. Fisher bruto ao lado.\n")
    cols = ["dominio", "tipo", "n_dias", "pct_sem_hora_dia_jogo", "pct_sem_hora_sem_jogo", "OR_ajustado",
            "IC95_lo", "IC95_hi", "p_ajustado", "p_BH_dominio", "fisher_p_bruto"]
    w("**Calendário completo (principal):**\n")
    w(md_tab(sel[[c for c in cols if c in sel.columns]], 3))
    sel_o = pd.read_csv(os.path.join(TAB, "teste_selecao_sem_hora_base_original.csv"))
    w("\n**Só a base original (robustez; era o resultado da 1ª versão desta fase):**\n")
    w(md_tab(sel_o[[c for c in cols if c in sel_o.columns]], 3))
    sig_o = sel_o[sel_o["p_BH_dominio"] < 0.05]
    raw = sel[sel["p_ajustado"] < 0.05]
    if len(sig_o):
        w(f"\nCom a base original havia seleção após BH em {', '.join(sig_o['tipo'])}; com o calendário "
          "completo ela não sobrevive à correção múltipla"
          + (f" (p bruto < 0,05 ainda em {', '.join(raw['tipo'])}, OR "
             + ", ".join(f"{v:.2f}" for v in raw['OR_ajustado']) + ")" if len(raw) else "")
          + ". Leitura: o sinal antigo era em parte efeito de comparar dias de jogo com dias de "
          "Paulistão/Libertadores marcados como \"sem jogo\". Mesmo assim, por cautela, a Fase 2 reporta "
          "junto o efeito no total diário (com + sem hora) de `lesao_corporal_dolosa` e `crimes_violentos`.\n")
    sig = sel[sel.get("p_BH_dominio", pd.Series(dtype=float)) < 0.05]
    if len(sig):
        w(f"\n**Seleção detectada** em: {', '.join(sig['dominio'] + '/' + sig['tipo'])}.")
        for _, r in sig.iterrows():
            p0 = r["pct_sem_hora_sem_jogo"] / 100
            p1 = p0 * r["OR_ajustado"] / (1 - p0 + p0 * r["OR_ajustado"])
            w(f"- `{r['tipo']}`: OR ajustado {r['OR_ajustado']:.3f} → de ~{100*p0:.1f}% para "
              f"~{100*p1:.1f}% sem hora em dia de jogo (+{100*(p1-p0):.1f} p.p.). A contagem horária "
              f"(só com hora) desse tipo fica ~{100*(1-(1-p1)/(1-p0)):.1f}% menor em dia de jogo só por "
              "registro, o que puxa um eventual efeito do jogo para BAIXO nesse tamanho.")
        w("\nÉ uma limitação a declarar, pequena em magnitude. Na Fase 2: (i) reportar junto o efeito "
          "no total diário (com + sem hora) desses tipos; (ii) robustez distribuindo os sem hora pelo "
          "`DESCR_PERIODO` (turno), quando informado. Roubos e furtos não mostram seleção após "
          "controles (o Fisher bruto significativo some com calendário: dias de jogo concentram-se em "
          "fins de semana/meses com perfil de registro diferente).\n")
    else:
        w("\n**Sem seleção detectável** após controles de calendário e BH por domínio: a proporção de "
          "registros sem hora não difere entre dias com e sem jogo em nenhum tipo. A perda de "
          "registros sem hora reduz a amostra (muito em furtos), mas não parece enviesar a comparação "
          "jogo × não-jogo.\n")

    w("## 8. Limitações declaradas nesta fase\n")
    w("- Estádio: a base de futebol não informa; **agora conferido jogo a jogo na Wikipédia** (seção 1b). "
      "7 mandos fora da capital vão para `janela_fora_capital`; 4 jogos na capital em estádio não habitual "
      "usam o estádio real (Canindé sem coordenada no projeto: lat/lon NaN, a definir na análise espacial).")
    w("- 3 horários de início aproximados (segundos ≠ 00), arredondados a 30 min.")
    w("- Furtos: 53% sem hora — a série horária de furtos representa só a metade com hora.")
    w("- `janela`: todas as competições oficiais com jogo na capital dos 4 times. `janela_fora_capital`: "
      "todos os jogos oficiais dos 4 times fora da capital, inclusive Supercopa do Brasil e o exterior; "
      "amistosos não entram (as páginas não listam amistosos nesses anos).")
    w("- Horários das fases de grupos do Paulistão vêm de uma fonte (Wikipédia, com fuso explícito UTC−3), "
      "sem página de edição para conferência cruzada; a data foi conferida com o link da súmula do ge.")
    w("- Público: total do estádio (Wikipédia), não pagante; conferido em amostra (seção 1e). Restrição da "
      "COVID marcada por regra (decreto estadual), não só onde a fonte anota.")
    w("- Público como dose-resposta (Fase 2) mede a multidão no estádio, não a audiência de TV; e o público "
      "real não é conhecido antes do jogo (Fase 3 só pode usar média histórica do mandante).\n")
    w("## Arquivos\n")
    w("- `scripts/30_eventos_horarios.py` → `data/silver/crime_eventos_sp.csv.gz`, "
      "`acidentes_eventos_sp.csv.gz`, `qualidade_hora.csv`")
    w("- `scripts/31_jogos_horarios.py` → `data/silver/jogos_sp_horario.csv`")
    w("- `scripts/32_base_horaria.py` → `data/gold/fato_hora_sp.csv`, `fato_hora_sp_dicionario.csv`, "
      "este relatório")
    w("- Tabelas em `reports/janelas/fase1/tabelas/`, figura em `reports/janelas/fase1/figuras/`.")
    with open(os.path.join(REP, "fase1_base_horaria.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    print("V2 Fase 1 / 32: base horaria")
    f, jogos, cont = monta_fato()
    f.to_csv(os.path.join(GOLD, "fato_hora_sp.csv"), index=False)
    dicionario(f)
    print(f"  fato_hora_sp: {f.shape}")
    print(f["janela"].value_counts().to_string())
    print("  jogos com 2/2/2 horas:", ((cont[["pre", "durante", "pos"]] == 2).all(axis=1)).sum(), "/", len(cont))
    sel_o = teste_selecao(f, "dia_de_jogo_base_original", "_base_original")
    sel = teste_selecao(f)
    print(sel.round(4).to_string(index=False))
    resj = resumo_janelas(f)
    relatorio(f, jogos, cont, sel, resj)
    print("[ok] data/gold/fato_hora_sp.csv, reports/janelas/fase1_base_horaria.md")
