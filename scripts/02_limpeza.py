"""
02_limpeza.py
Camadas SILVER (harmonizacao por fonte) e GOLD (dataset analitico final).

Grao final: 1 linha = 1 dia, municipio de Sao Paulo (CD_IBGE=3550308),
calendario mestre de 2022-01-01 a 2023-12-31 (730 dias).
"""
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
SILVER_DIR = os.path.join(BASE_DIR, "data", "silver")
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
os.makedirs(SILVER_DIR, exist_ok=True)
os.makedirs(GOLD_DIR, exist_ok=True)

CD_IBGE_SP = 3550308
DATA_MIN = pd.Timestamp("2022-01-01")
DATA_MAX = pd.Timestamp("2023-12-31")

SP_CLUBS_MANDANTES = ["Sao Paulo", "Corinthians", "Palmeiras"]  # jogam na capital
SP_CLASSICO_GRUPO = ["Sao Paulo", "Corinthians", "Palmeiras", "Santos"]  # Santos so como visitante
CAPACIDADE_ESTADIO = {  # fonte: paginas oficiais dos clubes / Wikipedia, checadas na Etapa 2/5
    "Corinthians": 49282,   # Neo Quimica Arena
    "Palmeiras": 43713,     # Allianz Parque
    "Sao Paulo": 66795,     # Morumbi (capacidade comercializavel)
}

# ---------------------------------------------------------------------------
# SILVER: criminalidade
# ---------------------------------------------------------------------------

CATEGORIAS_VIOLENTAS = {
    "LESÃO CORPORAL DOLOSA", "LESÃO CORPORAL SEGUIDA DE MORTE",
    "HOMICÍDIO DOLOSO", "TENTATIVA DE HOMICIDIO", "LATROCÍNIO",
    "ESTUPRO", "ESTUPRO DE VULNERÁVEL", "EXTORSÃO MEDIANTE SEQUESTRO",
}


def _harmoniza_colunas_crime(df, ano):
    """2022 usa CIDADE/DATA_COMUNICACAO_BO/DESCR_PERIODO;
    2023 usa NOME_MUNICIPIO/DATA_REGISTRO/DESC_PERIODO. Padroniza para um schema comum."""
    if ano == 2022:
        df = df.rename(columns={"CIDADE": "municipio"})
    else:
        df = df.rename(columns={"NOME_MUNICIPIO": "municipio"})
    return df


def clean_crime():
    print("Limpeza: criminalidade")
    arquivos = [
        (os.path.join(BRONZE_DIR, "crime_2022_jan_jun.csv"), 2022),
        (os.path.join(BRONZE_DIR, "crime_2022_jul_dez.csv"), 2022),
        (os.path.join(BRONZE_DIR, "crime_2023_jan_jun.csv"), 2023),
        (os.path.join(BRONZE_DIR, "crime_2023_jul_dez.csv"), 2023),
    ]
    usecols = ["CIDADE", "NOME_MUNICIPIO", "DATA_OCORRENCIA_BO", "NATUREZA_APURADA",
               "CD_IBGE", "NUM_BO", "ANO_BO", "NOME_DELEGACIA"]

    daily_parts = []
    n_total, n_sp, n_fora_janela = 0, 0, 0

    for path, ano in arquivos:
        cols_presentes = [c for c in usecols if c in pd.read_csv(path, nrows=0).columns]
        df = pd.read_csv(path, usecols=cols_presentes, low_memory=False)
        df = _harmoniza_colunas_crime(df, ano)
        n_total += len(df)

        # filtro geografico: CD_IBGE e a chave confiavel (o texto do municipio
        # tem variantes de espaco em branco, ver Etapa 1)
        df = df[df["CD_IBGE"] == CD_IBGE_SP].copy()
        n_sp += len(df)

        # data do FATO (nao a data de registro) - e o que importa para medir
        # impacto de jogo no dia; ha outliers historicos (ate 1922) no campo,
        # que sao descartados pelo filtro de janela abaixo
        df["data"] = pd.to_datetime(df["DATA_OCORRENCIA_BO"], errors="coerce")
        antes = len(df)
        df = df[(df["data"] >= DATA_MIN) & (df["data"] <= DATA_MAX)]
        n_fora_janela += antes - len(df)

        df["NATUREZA_APURADA"] = df["NATUREZA_APURADA"].astype(str).str.strip().str.upper()
        df["bo_key"] = (
            df["NUM_BO"].astype(str) + "_" + df["ANO_BO"].astype(str) + "_" + df["NOME_DELEGACIA"].astype(str)
        )

        grp = df.groupby(df["data"].dt.date)
        daily = pd.DataFrame({
            "crimes_totais": grp.size(),
            "bos_unicos": grp["bo_key"].nunique(),
            "crimes_violentos": grp.apply(lambda g: g["NATUREZA_APURADA"].isin(CATEGORIAS_VIOLENTAS).sum() +
                                           g["NATUREZA_APURADA"].str.startswith("ROUBO").sum()),
            "homicidios_dolosos": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "HOMICÍDIO DOLOSO").sum()),
            "tentativas_homicidio": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "TENTATIVA DE HOMICIDIO").sum()),
            "latrocinio": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "LATROCÍNIO").sum()),
            "lesao_corporal_dolosa": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "LESÃO CORPORAL DOLOSA").sum()),
            "roubos_total": grp.apply(lambda g: g["NATUREZA_APURADA"].str.startswith("ROUBO").sum()),
            "roubo_veiculo": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "ROUBO DE VEÍCULO").sum()),
            "furtos_total": grp.apply(lambda g: g["NATUREZA_APURADA"].str.startswith("FURTO").sum()),
            "furto_veiculo": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "FURTO DE VEÍCULO").sum()),
            "estupros": grp.apply(lambda g: g["NATUREZA_APURADA"].str.startswith("ESTUPRO").sum()),
            "trafico_entorpecentes": grp.apply(lambda g: (g["NATUREZA_APURADA"] == "TRAFICO DE ENTORPECENTES").sum()),
        })
        daily_parts.append(daily)
        del df

    # concatena os 4 semestres e RE-agrupa por data: um BO registrado no
    # semestre seguinte pode ter data de ocorrencia no semestre anterior
    # (proximo ao corte jun/jul), entao a mesma data pode aparecer em 2 arquivos
    combined = pd.concat(daily_parts)
    combined.index = pd.to_datetime(combined.index)
    combined = combined.groupby(combined.index).sum()
    combined.index.name = "data"
    combined = combined.reset_index()

    print(f"  linhas brutas: {n_total} | SP capital: {n_sp} ({n_sp/n_total*100:.1f}%) "
          f"| descartadas por estarem fora de 2022-2023: {n_fora_janela}")
    print(f"  dias cobertos: {combined['data'].min().date()} a {combined['data'].max().date()} "
          f"({combined['data'].nunique()} dias distintos)")

    out_path = os.path.join(SILVER_DIR, "crime_diario_sp.csv")
    combined.to_csv(out_path, index=False)
    print(f"  [ok] {out_path}")
    return combined


# ---------------------------------------------------------------------------
# SILVER: acidentes de transito (stub - fonte externa exige rede)
# ---------------------------------------------------------------------------

COLISAO_COLS = ["tp_sinistro_colisao_frontal", "tp_sinistro_colisao_traseira",
                "tp_sinistro_colisao_lateral", "tp_sinistro_colisao_transversal",
                "tp_sinistro_colisao_outros"]


def clean_accidents():
    """Fonte: Infosiga SP (Detran-SP), arquivos anuais enviados pelo usuario
    apos o endpoint de ZIP consolidado ter recusado o download automatizado
    ('nao autorizado'). Grao original = 1 linha por sinistro (evento),
    id_sinistro unico confirmado (sem duplicidade).

    tipo_registro tem 3 valores: NOTIFICACAO (sem dado de gravidade -
    provavelmente sinistro sem vitima/dano apenas material), SINISTRO NAO
    FATAL (tem feridos) e SINISTRO FATAL (tem obitos). 'acidentes_total'
    soma os 3; 'acidentes_com_vitima' soma so os 2 ultimos."""
    print("Limpeza: acidentes (Infosiga SP)")
    frames = []
    n_total, n_sp = 0, 0
    for year in (2022, 2023):
        path = os.path.join(BRONZE_DIR, f"sinistros_{year}.csv")
        df = pd.read_csv(path, sep=";", encoding="latin1", low_memory=False)
        n_total += len(df)
        df = df[df["cod_ibge"] == CD_IBGE_SP].copy()
        n_sp += len(df)
        df["data"] = pd.to_datetime(df["data_sinistro"], format="%d/%m/%Y", errors="coerce")
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    antes = len(raw)
    raw = raw[(raw["data"] >= DATA_MIN) & (raw["data"] <= DATA_MAX)]
    n_fora_janela = antes - len(raw)

    raw["com_vitima"] = raw["tipo_registro"].isin(["SINISTRO NAO FATAL", "SINISTRO FATAL"])
    raw["fatal"] = raw["tipo_registro"] == "SINISTRO FATAL"
    raw["atropelamento"] = raw["tp_sinistro_atropelamento"] == "S"
    raw["colisao"] = raw[COLISAO_COLS].eq("S").any(axis=1)

    grp = raw.groupby(raw["data"].dt.date)
    daily = pd.DataFrame({
        "acidentes_total": grp.size(),
        "acidentes_com_vitima": grp["com_vitima"].sum(),
        "acidentes_fatais": grp["fatal"].sum(),
        "obitos_transito": grp["qtd_gravidade_fatal"].sum(),
        "feridos_transito": grp[["qtd_gravidade_grave", "qtd_gravidade_leve"]].sum().sum(axis=1)
                            if False else grp.apply(lambda g: g["qtd_gravidade_grave"].sum() + g["qtd_gravidade_leve"].sum()),
        "atropelamentos": grp["atropelamento"].sum(),
        "colisoes": grp["colisao"].sum(),
    })
    daily.index = pd.to_datetime(daily.index)
    daily.index.name = "data"
    daily = daily.reset_index()
    daily["fonte_acidentes"] = "infosiga_sp"

    print(f"  linhas brutas: {n_total} | SP capital: {n_sp} ({n_sp/n_total*100:.1f}%) "
          f"| descartadas fora de 2022-2023: {n_fora_janela}")
    print(f"  dias cobertos: {daily['data'].min().date()} a {daily['data'].max().date()} "
          f"({daily['data'].nunique()} dias)")

    out_path = os.path.join(SILVER_DIR, "acidentes_diario_sp.csv")
    daily.to_csv(out_path, index=False)
    print(f"  [ok] {out_path}")
    return daily


# ---------------------------------------------------------------------------
# SILVER: futebol
# ---------------------------------------------------------------------------

def clean_football(kaggle_publico_path=None):
    print("Limpeza: futebol")
    path = os.path.join(BRONZE_DIR, "BR-Football-Dataset.csv")
    df = pd.read_csv(path, low_memory=False)
    df["data"] = pd.to_datetime(df["date"])
    df = df[(df["data"] >= DATA_MIN) & (df["data"] <= DATA_MAX)].copy()

    df["tem_jogo_sp"] = df["home"].isin(SP_CLUBS_MANDANTES)
    df_sp = df[df["tem_jogo_sp"]].copy()
    df_sp["classico"] = df_sp["away"].isin(SP_CLASSICO_GRUPO)
    df_sp["horario_jogo"] = df_sp["time"]
    df_sp["jogo_noturno"] = pd.to_datetime(df_sp["time"], format="%H:%M:%S", errors="coerce").dt.hour >= 19
    df_sp["capacidade_estadio"] = df_sp["home"].map(CAPACIDADE_ESTADIO)
    df_sp["publico"] = np.nan  # enriquecido abaixo se kaggle_publico_path for fornecido
    df_sp["fonte_jogo"] = "br_football_dataset"

    resultado_map = {"WON": "vitoria_mandante", "DRAW": "empate", "LOST": "derrota_mandante"}
    df_sp["resultado_mandante"] = df_sp["ht_result"].map(resultado_map)

    if kaggle_publico_path and os.path.exists(kaggle_publico_path):
        pub = pd.read_csv(kaggle_publico_path)
        # join esperado por data + mandante + visitante - schema exato do
        # Kaggle (adaoduque/campeonato-brasileiro-de-futebol) deve ser
        # conferido no momento do download, este e um hook de integracao
        df_sp = df_sp.merge(pub, how="left", on=["data", "home", "away"], suffixes=("", "_kaggle"))
        if "publico_kaggle" in df_sp.columns:
            df_sp["publico"] = df_sp["publico_kaggle"]
        print("  [info] publico enriquecido via Kaggle")
    else:
        print("  [info] publico NAO enriquecido (fonte Kaggle nao baixada neste ambiente)")

    df_sp["publico_disponivel"] = df_sp["publico"].notna()
    df_sp["taxa_ocupacao"] = df_sp["publico"] / df_sp["capacidade_estadio"]

    # agregacao diaria - double-headers existem (Etapa 1: 11 dias em 2022-2023)
    # numero_jogos_sp conta todos; os campos descritivos (mandante, resultado...)
    # ficam com o jogo mais cedo do dia como registro representativo
    df_sp = df_sp.sort_values(["data", "horario_jogo"])
    agg_count = df_sp.groupby("data").size().rename("numero_jogos_sp")
    first_game = df_sp.groupby("data").first()

    daily = first_game.join(agg_count)
    daily["campeonato"] = daily["tournament"]
    daily = daily.rename(columns={"home": "mandante", "away": "visitante",
                                   "home_goal": "gols_mandante", "away_goal": "gols_visitante"})
    cols = ["numero_jogos_sp", "mandante", "visitante", "campeonato", "classico",
            "horario_jogo", "jogo_noturno", "resultado_mandante", "gols_mandante",
            "gols_visitante", "publico", "publico_disponivel", "capacidade_estadio",
            "taxa_ocupacao", "fonte_jogo"]
    daily = daily[cols].reset_index()

    print(f"  jogos em SP capital 2022-2023: {df_sp.shape[0]} | dias com jogo: {daily.shape[0]} "
          f"| dias com >1 jogo: {(agg_count > 1).sum()}")

    out_path = os.path.join(SILVER_DIR, "futebol_diario_sp.csv")
    daily.to_csv(out_path, index=False)
    print(f"  [ok] {out_path}")
    return daily


# ---------------------------------------------------------------------------
# SILVER: clima
# ---------------------------------------------------------------------------

def clean_weather():
    print("Limpeza: clima")
    frames = []
    for year in (2022, 2023):
        path = os.path.join(BRONZE_DIR, f"inmet_{year}.csv")
        df = pd.read_csv(path, sep=";", skiprows=8, encoding="latin1", decimal=",")
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        hora = df["Hora UTC"].str[:4]  # "0000 UTC" -> "0000"
        dt_utc = pd.to_datetime(df["Data"] + " " + hora, format="%Y/%m/%d %H%M")
        df["data_local"] = (dt_utc - pd.Timedelta(hours=3)).dt.date  # Brasil sem DST desde 2019
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    col_temp = "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)"
    col_prec = "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"
    col_umid = "UMIDADE RELATIVA DO AR, HORARIA (%)"
    col_vento = "VENTO, RAJADA MAXIMA (m/s)"

    grp = raw.groupby("data_local")
    daily = pd.DataFrame({
        "temp_media": grp[col_temp].mean(),
        "temp_max": grp[col_temp].max(),
        "temp_min": grp[col_temp].min(),
        "precipitacao_total": grp[col_prec].sum(min_count=1),
        "umidade_media": grp[col_umid].mean(),
        "vento_max": grp[col_vento].max(),
    })
    daily["chuva"] = daily["precipitacao_total"] > 0
    daily.index = pd.to_datetime(daily.index)
    daily.index.name = "data"
    daily = daily.reset_index()
    daily = daily[(daily["data"] >= DATA_MIN) & (daily["data"] <= DATA_MAX)]

    print(f"  dias cobertos: {daily['data'].min().date()} a {daily['data'].max().date()} "
          f"({len(daily)} dias)")

    out_path = os.path.join(SILVER_DIR, "clima_diario_sp.csv")
    daily.to_csv(out_path, index=False)
    print(f"  [ok] {out_path}")
    return daily


# ---------------------------------------------------------------------------
# SILVER: calendario (feriados + calendario escolar)
# ---------------------------------------------------------------------------

def _pascoa(ano):
    """Algoritmo de Meeus/Jones/Butcher - nao depende de rede. Validado contra
    datas publicas conhecidas: Pascoa 2022 = 17/abr, Pascoa 2023 = 09/abr
    (esta ultima bate com a final do Paulistao 2023, achada na Etapa 2)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def _feriados_ano(ano):
    pascoa = _pascoa(ano)
    nacionais = {
        date(ano, 1, 1): "Confraternização Universal",
        pascoa - timedelta(days=47): "Carnaval",
        pascoa - timedelta(days=2): "Sexta-feira Santa",
        pascoa + timedelta(days=60): "Corpus Christi",
        date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho",
        date(ano, 9, 7): "Independência do Brasil",
        date(ano, 10, 12): "Nossa Senhora Aparecida",
        date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República",
        date(ano, 12, 25): "Natal",
    }
    estaduais = {date(ano, 7, 9): "Revolução Constitucionalista de 1932"}
    municipais = {date(ano, 1, 25): "Aniversário da cidade de São Paulo"}
    return nacionais, estaduais, municipais


# calendario escolar municipal (SME-SP), transcrito das resolucoes oficiais
# encontradas na Etapa 2 - nao ha dataset tabular publico para isso
CALENDARIO_ESCOLAR_SME = {
    2022: {
        "letivo": [(date(2022, 2, 7), date(2022, 12, 22))],
        "ferias": [(date(2022, 1, 3), date(2022, 1, 31))],
        "recesso": [(date(2022, 7, 11), date(2022, 7, 22)), (date(2022, 12, 23), date(2022, 12, 31))],
    },
    2023: {
        "letivo": [(date(2023, 2, 6), date(2023, 12, 21))],
        "ferias": [(date(2023, 1, 2), date(2023, 1, 31))],
        "recesso": [(date(2023, 7, 10), date(2023, 7, 21)), (date(2023, 12, 22), date(2023, 12, 29))],
    },
}


def _in_ranges(d, ranges):
    return any(start <= d <= end for start, end in ranges)


def build_calendar():
    print("Construcao: calendario mestre (feriados + calendario escolar)")
    dias = pd.date_range(DATA_MIN, DATA_MAX, freq="D")
    rows = []
    for ts in dias:
        d = ts.date()
        ano = d.year
        nac, est, mun = _feriados_ano(ano)
        cal = CALENDARIO_ESCOLAR_SME[ano]

        nome_feriado = nac.get(d) or est.get(d) or mun.get(d)
        rows.append({
            "data": ts,
            "ano": ano,
            "mes": d.month,
            "trimestre": (d.month - 1) // 3 + 1,
            "dia_semana": (d.weekday() + 1) % 7,  # 0=domingo
            "fim_de_semana": d.weekday() >= 5,
            "semana_ano": d.isocalendar()[1],
            "feriado_nacional": d in nac,
            "feriado_estadual": d in est,
            "feriado_municipal": d in mun,
            "feriado": (d in nac) or (d in est) or (d in mun),
            "nome_feriado": nome_feriado,
            "periodo_letivo": _in_ranges(d, cal["letivo"]) and not _in_ranges(d, cal["recesso"]),
            "ferias_escolares": _in_ranges(d, cal["ferias"]),
            "recesso_escolar": _in_ranges(d, cal["recesso"]),
        })
    dfc = pd.DataFrame(rows)
    dfc["vespera_feriado"] = dfc["feriado"].shift(-1).fillna(False)

    nomes_dia = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
    dfc["nome_dia_semana"] = dfc["dia_semana"].map(lambda i: nomes_dia[i])

    # checagem de sanidade: Pascoa computada bate com fatos conhecidos
    assert _pascoa(2022) == date(2022, 4, 17), "Pascoa 2022 incorreta"
    assert _pascoa(2023) == date(2023, 4, 9), "Pascoa 2023 incorreta"

    out_path = os.path.join(SILVER_DIR, "calendario_sp.csv")
    dfc.to_csv(out_path, index=False)
    print(f"  [ok] {out_path} ({len(dfc)} dias, {dfc['feriado'].sum()} feriados)")
    return dfc


# ---------------------------------------------------------------------------
# GOLD: join final
# ---------------------------------------------------------------------------

def build_gold():
    print("\nConstrucao da camada GOLD (fato_dia_sp)")
    calendario = build_calendar()
    crime = clean_crime()
    acidentes = clean_accidents()
    futebol = clean_football()
    clima = clean_weather()

    gold = calendario.merge(futebol, on="data", how="left")
    gold = gold.merge(clima, on="data", how="left")
    gold = gold.merge(crime, on="data", how="left")
    gold = gold.merge(acidentes, on="data", how="left")

    # colunas de futebol: dia sem jogo fica com tem_jogo_sp=False e o resto
    # NULO (nao zero) - ausencia de jogo != ausencia de dado, ver Etapa 4
    gold["tem_jogo_sp"] = gold["numero_jogos_sp"].notna()
    gold["numero_jogos_sp"] = gold["numero_jogos_sp"].fillna(0).astype(int)
    gold["classico"] = gold["classico"].fillna(False)
    gold["publico_disponivel"] = gold["publico_disponivel"].fillna(False)

    # colunas de crime/clima nunca deveriam ser nulas dentro da janela - um
    # nulo aqui sinaliza falha de ingestao, nao ausencia real de eventos
    crime_cols = ["crimes_totais", "bos_unicos", "crimes_violentos", "homicidios_dolosos",
                  "tentativas_homicidio", "latrocinio", "lesao_corporal_dolosa",
                  "roubos_total", "roubo_veiculo", "furtos_total", "furto_veiculo",
                  "estupros", "trafico_entorpecentes"]
    n_nulos_crime = gold[crime_cols].isna().any(axis=1).sum()
    if n_nulos_crime:
        print(f"  [alerta] {n_nulos_crime} dias sem registro de crime - checar ingestao")

    # janelas de defasagem (Secao 9 do roteiro) - deslocam a variavel de
    # futebol, nao a variavel-alvo, para permitir crime(D0) vs jogo(D-1)/jogo(D+1)
    gold = gold.sort_values("data").reset_index(drop=True)
    gold["jogo_d_menos_1"] = gold["tem_jogo_sp"].shift(1).fillna(False)
    gold["jogo_d_mais_1"] = gold["tem_jogo_sp"].shift(-1).fillna(False)
    gold["classico_d_menos_1"] = gold["classico"].shift(1).fillna(False)
    gold["classico_d_mais_1"] = gold["classico"].shift(-1).fillna(False)

    # colunas de pico - a definicao formal e a Etapa 11 (scripts/08_definicao_pico.py).
    # Se data/gold/pico_dia_sp.csv ja existe, faz o merge; senao deixa NaN e avisa.
    # Ordem de execucao: 02 -> 08 -> (02 de novo para o fato carregar as colunas).
    pico_path = os.path.join(GOLD_DIR, "pico_dia_sp.csv")
    _pico_map = {"pico_crime_p90": "pico_crime_p90",
                 "pico_crime_zscore": "pico_crime_z2",
                 "pico_acidente_p90": "pico_acidente_p90",
                 "nivel_risco": "nivel_risco"}
    if os.path.exists(pico_path):
        pk = pd.read_csv(pico_path, parse_dates=["data"]).set_index("data")
        _b = {"True": True, "False": False, True: True, False: False}
        for dest, src in _pico_map.items():
            if src not in pk.columns:
                gold[dest] = np.nan
                continue
            s = pk[src]
            if dest != "nivel_risco":
                s = s.map(_b).astype("boolean")
            gold[dest] = gold["data"].map(s)
        print(f"  [ok] colunas de pico mescladas de {pico_path}")
    else:
        for dest in _pico_map:
            gold[dest] = np.nan
        print("  [aviso] pico_dia_sp.csv ausente - colunas pico_* ficam NaN; "
              "rode scripts/08_definicao_pico.py e depois 02_limpeza.py de novo")

    out_path = os.path.join(GOLD_DIR, "fato_dia_sp.csv")
    gold.to_csv(out_path, index=False)
    print(f"\n[ok] Dataset analitico final: {out_path}")
    print(f"  shape: {gold.shape}")
    print(f"  datas duplicadas: {gold['data'].duplicated().sum()}")
    print(f"  intervalo: {gold['data'].min().date()} a {gold['data'].max().date()}")
    return gold


if __name__ == "__main__":
    df = build_gold()
    print("\nPreview:")
    print(df.head(3).to_string())
