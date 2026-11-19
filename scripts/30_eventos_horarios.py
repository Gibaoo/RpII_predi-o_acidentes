"""
V2 / Fase 1 -- 30_eventos_horarios.py
Extracao de EVENTOS com horario (crime e sinistros) para a analise por
janelas de horario (pre-jogo / durante / pos-jogo / fora).

Por que um script novo: a camada silver original (02_limpeza.py) agrega tudo
ao grao DIA e descarta a hora. A analise V2 exige o grao HORA, entao voltamos
ao bronze e guardamos 1 linha por registro, com o timestamp local (Brasilia).

Decisoes herdadas (nao redecididas):
  - filtro geografico CD_IBGE == 3550308 (crime) / cod_ibge == 3550308 (Infosiga)
  - data do FATO (DATA_OCORRENCIA_BO / data_sinistro), janela 2022-01-01..2023-12-31
  - grao do crime = linha do bronze (BO x natureza), igual a 02_limpeza.py
  - crimes_violentos = CATEGORIAS_VIOLENTAS + NATUREZA_APURADA comecando com ROUBO
    (constante importada de 02_limpeza.py, nao copiada)
  - acidentes_com_vitima = tipo_registro in {SINISTRO NAO FATAL, SINISTRO FATAL};
    atropelamentos = tp_sinistro_atropelamento == 'S' (mesma regra do diario)

Saidas:
  data/silver/crime_eventos_sp.csv.gz      1 linha = BO x natureza, SP capital
  data/silver/acidentes_eventos_sp.csv.gz  1 linha = sinistro (Infosiga), SP capital
  data/silver/qualidade_hora.csv           % sem hora / arredondamento, por tipo
  reports/janelas/fase1/tabelas/*          qualidade por arquivo, periodo dos sem-hora,
                                           distribuicao por hora, conferencia com o diario
  reports/janelas/fase1/figuras/*          distribuicao de hora e minuto por dominio

Rodar:  python scripts/30_eventos_horarios.py
"""
import importlib
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
_limpeza = importlib.import_module("02_limpeza")
CATEGORIAS_VIOLENTAS = _limpeza.CATEGORIAS_VIOLENTAS

BRONZE = os.path.join(BASE, "data", "bronze")
SILVER = os.path.join(BASE, "data", "silver")
OUT = os.path.join(BASE, "reports", "janelas", "fase1")
TAB = os.path.join(OUT, "tabelas")
FIG = os.path.join(OUT, "figuras")
for d in (TAB, FIG):
    os.makedirs(d, exist_ok=True)

CD_IBGE_SP = 3550308
DATA_MIN, DATA_MAX = pd.Timestamp("2022-01-01"), pd.Timestamp("2023-12-31")

CRIME_FILES = ["crime_2022_jan_jun.csv", "crime_2022_jul_dez.csv",
               "crime_2023_jan_jun.csv", "crime_2023_jul_dez.csv"]
# 2022 usa DESCR_PERIODO; 2023 renomeou para DESC_PERIODO (CIDADE->NOME_MUNICIPIO e
# DATA_COMUNICACAO_BO->DATA_REGISTRO tambem mudam, mas nao sao usadas aqui)
CRIME_COLS = ["NUM_BO", "ANO_BO", "NOME_DELEGACIA", "DATA_OCORRENCIA_BO",
              "HORA_OCORRENCIA_BO", "DESCR_PERIODO", "DESC_PERIODO",
              "DESCR_SUBTIPOLOCAL", "BAIRRO", "LATITUDE", "LONGITUDE",
              "NATUREZA_APURADA", "CD_IBGE"]

# aceita tambem o artefato de celula-hora do Excel "1900-01-01 HH:MM:SS" (a data
# 1900-01-01 e o "dia zero" do Excel; a hora e valida). Outras datas no campo de
# hora (ex. "2000-06-01 00:00:00") NAO sao hora -> formato invalido -> sem hora.
HORA_RE = r"^\s*(?:1900-01-01\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$"


def parse_hora(serie):
    """Devolve (hora, minuto, tem_hora, formato_invalido). 'NULL'/vazio = sem hora;
    texto nao-vazio que nao casa com HH:MM[:SS] valido = formato invalido (tambem sem hora)."""
    s = serie.astype("string")
    hm = s.str.extract(HORA_RE).astype(float)
    h, m = hm[0], hm[1]
    valido = h.notna() & (h < 24) & (m < 60)
    vazio = s.isna() | s.str.strip().str.upper().isin(["", "NULL", "NAN", "NONE"])
    invalido = ~valido & ~vazio
    return h.where(valido), m.where(valido), valido, invalido


def monta_timestamp(df):
    ts = df["data"] + pd.to_timedelta(df["hora"].fillna(0), unit="h") \
        + pd.to_timedelta(df["minuto"].fillna(0), unit="m")
    return ts.where(df["tem_hora"])


# ---------------------------------------------------------------------------
# crime (SSP)
# ---------------------------------------------------------------------------
def extrai_crime():
    partes, n_total = [], 0
    for f in CRIME_FILES:
        path = os.path.join(BRONZE, f)
        cols = [c for c in CRIME_COLS if c in pd.read_csv(path, nrows=0).columns]
        n_f = 0
        for chunk in pd.read_csv(path, usecols=cols, dtype=str, chunksize=400_000):
            n_total += len(chunk)
            chunk = chunk[pd.to_numeric(chunk["CD_IBGE"], errors="coerce") == CD_IBGE_SP].copy()
            if "DESC_PERIODO" in chunk.columns:
                chunk = chunk.rename(columns={"DESC_PERIODO": "DESCR_PERIODO"})
            chunk["data"] = pd.to_datetime(chunk["DATA_OCORRENCIA_BO"].str[:10], errors="coerce")
            chunk = chunk[(chunk["data"] >= DATA_MIN) & (chunk["data"] <= DATA_MAX)]
            chunk["arquivo"] = f.replace("crime_", "").replace(".csv", "")
            n_f += len(chunk)
            partes.append(chunk.drop(columns=["CD_IBGE", "DATA_OCORRENCIA_BO"]))
        print(f"  {f}: {n_f:,} linhas SP capital 2022-2023")
    df = pd.concat(partes, ignore_index=True)

    df["hora_txt"] = df["HORA_OCORRENCIA_BO"]
    df["hora"], df["minuto"], df["tem_hora"], df["hora_formato_invalido"] = parse_hora(df["HORA_OCORRENCIA_BO"])
    df["timestamp"] = monta_timestamp(df)

    nat = df["NATUREZA_APURADA"].astype(str).str.strip().str.upper()
    df["natureza"] = nat
    df["is_roubo"] = nat.str.startswith("ROUBO")
    df["is_furto"] = nat.str.startswith("FURTO")
    df["is_lesao_dolosa"] = nat == "LESÃO CORPORAL DOLOSA"
    df["is_violento"] = nat.isin(CATEGORIAS_VIOLENTAS) | df["is_roubo"]
    df["bo_key"] = (df["NUM_BO"].fillna("") + "_" + df["ANO_BO"].fillna("") + "_"
                    + df["NOME_DELEGACIA"].fillna(""))
    df["lat"] = pd.to_numeric(df["LATITUDE"].str.replace(",", "."), errors="coerce")
    df["lon"] = pd.to_numeric(df["LONGITUDE"].str.replace(",", "."), errors="coerce")
    df = df.rename(columns={"DESCR_PERIODO": "periodo", "DESCR_SUBTIPOLOCAL": "subtipo_local",
                            "BAIRRO": "bairro"})
    keep = ["bo_key", "arquivo", "data", "hora_txt", "hora", "minuto", "tem_hora",
            "hora_formato_invalido", "timestamp", "periodo", "natureza", "is_violento",
            "is_lesao_dolosa", "is_roubo", "is_furto", "subtipo_local", "bairro", "lat", "lon"]
    df = df[keep]
    print(f"  crime: {n_total:,} linhas no estado | {len(df):,} SP capital 2022-2023")
    return df


# ---------------------------------------------------------------------------
# sinistros (Infosiga)
# ---------------------------------------------------------------------------
def extrai_acidentes():
    partes = []
    for ano in (2022, 2023):
        df = pd.read_csv(os.path.join(BRONZE, f"sinistros_{ano}.csv"), sep=";",
                         encoding="latin1", low_memory=False, dtype={"hora_sinistro": str})
        df = df[df["cod_ibge"] == CD_IBGE_SP].copy()
        df["arquivo"] = str(ano)
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["data"] = pd.to_datetime(df["data_sinistro"], format="%d/%m/%Y", errors="coerce")
    df = df[(df["data"] >= DATA_MIN) & (df["data"] <= DATA_MAX)].copy()
    df["hora"], df["minuto"], df["tem_hora"], df["hora_formato_invalido"] = parse_hora(df["hora_sinistro"])
    df["timestamp"] = monta_timestamp(df)
    colisao = [c for c in df.columns if c.startswith("tp_sinistro_colisao")]
    out = pd.DataFrame({
        "id_sinistro": df["id_sinistro"], "arquivo": df["arquivo"], "data": df["data"],
        "hora_txt": df["hora_sinistro"], "hora": df["hora"], "minuto": df["minuto"],
        "tem_hora": df["tem_hora"], "hora_formato_invalido": df["hora_formato_invalido"],
        "timestamp": df["timestamp"], "turno": df["turno"],
        "tipo_registro": df["tipo_registro"],
        "com_vitima": df["tipo_registro"].isin(["SINISTRO NAO FATAL", "SINISTRO FATAL"]),
        "fatal": df["tipo_registro"] == "SINISTRO FATAL",
        "atropelamento": df["tp_sinistro_atropelamento"] == "S",
        "colisao": df[colisao].eq("S").any(axis=1),
        "lat": pd.to_numeric(df["latitude"].astype(str).str.replace(",", "."), errors="coerce"),
        "lon": pd.to_numeric(df["longitude"].astype(str).str.replace(",", "."), errors="coerce"),
    })
    print(f"  acidentes: {len(out):,} sinistros SP capital 2022-2023 "
          f"(id_sinistro duplicado: {out['id_sinistro'].duplicated().sum()})")
    return out


# ---------------------------------------------------------------------------
# qualidade da hora
# ---------------------------------------------------------------------------
def qualidade(df, dominio, tipo, recorte="todos"):
    th = df["tem_hora"]
    m, h = df.loc[th, "minuto"], df.loc[th, "hora"]
    n_h = h.value_counts()
    vizinhos = (n_h.get(23, 0) + n_h.get(1, 0)) / 2
    return {
        "dominio": dominio, "tipo": tipo, "recorte": recorte, "n": len(df),
        "n_sem_hora": int((~th).sum()),
        "pct_sem_hora": round(100 * (~th).mean(), 2),
        "pct_formato_invalido": round(100 * df["hora_formato_invalido"].mean(), 3),
        "pct_minuto_00": round(100 * (m == 0).mean(), 2),
        "pct_minuto_00_ou_30": round(100 * m.isin([0, 30]).mean(), 2),
        "pct_minuto_multiplo_5": round(100 * (m % 5 == 0).mean(), 2),
        "pct_meia_noite_exata": round(100 * ((h == 0) & (m == 0)).mean(), 2),
        # se 00:00 for placeholder de "hora desconhecida", a hora 0 incha vs 23h/1h
        "razao_hora0_vs_vizinhas": round(n_h.get(0, 0) / vizinhos, 2) if vizinhos else np.nan,
    }


TIPOS_CRIME = {
    "crime_todos": lambda d: d.index == d.index,
    "crimes_violentos": lambda d: d["is_violento"],
    "lesao_corporal_dolosa": lambda d: d["is_lesao_dolosa"],
    "roubos_total": lambda d: d["is_roubo"],
    "furtos_total": lambda d: d["is_furto"],
}
TIPOS_ACID = {
    "acidentes_total": lambda d: d.index == d.index,
    "acidentes_com_vitima": lambda d: d["com_vitima"],
    "atropelamentos": lambda d: d["atropelamento"],
}


def tabela_qualidade(crime, acid):
    linhas = []
    for dom, df, tipos in (("crimes", crime, TIPOS_CRIME), ("sinistros", acid, TIPOS_ACID)):
        for tipo, f in tipos.items():
            sub = df[f(df)]
            linhas.append(qualidade(sub, dom, tipo))
            for arq, g in sub.groupby("arquivo"):
                linhas.append(qualidade(g, dom, tipo, f"arquivo_{arq}"))
    return pd.DataFrame(linhas)


def periodo_dos_sem_hora(crime):
    """DESCR_PERIODO dos registros sem hora: diz se ao menos o turno e conhecido."""
    linhas = []
    for tipo, f in TIPOS_CRIME.items():
        sub = crime[f(crime) & ~crime["tem_hora"]]
        vc = sub["periodo"].fillna("(nulo)").str.strip().str.upper().replace("NULL", "(nulo)")
        vc = vc.value_counts(normalize=True).mul(100).round(2)
        for k, v in vc.items():
            linhas.append({"tipo": tipo, "periodo": k, "pct_dos_sem_hora": v})
    return pd.DataFrame(linhas)


def distribuicao_hora(crime, acid):
    linhas = []
    for dom, df, tipos in (("crimes", crime, TIPOS_CRIME), ("sinistros", acid, TIPOS_ACID)):
        for tipo, f in tipos.items():
            sub = df[f(df) & df["tem_hora"]]
            vc = sub["hora"].astype(int).value_counts().reindex(range(24), fill_value=0)
            for h, n in vc.items():
                linhas.append({"dominio": dom, "tipo": tipo, "hora": h, "n": int(n),
                               "pct": round(100 * n / len(sub), 3)})
    return pd.DataFrame(linhas)


def confere_com_diario(crime, acid):
    """Total de registros por dia (com + sem hora) deve bater com o silver diario de
    02_limpeza.py -- prova de que a extracao usa o mesmo filtro/grao."""
    out = []
    cd = pd.read_csv(os.path.join(SILVER, "crime_diario_sp.csv"), parse_dates=["data"]).set_index("data")
    for tipo, f in TIPOS_CRIME.items():
        col = "crimes_totais" if tipo == "crime_todos" else tipo
        novo = crime[f(crime)].groupby("data").size().reindex(cd.index, fill_value=0)
        diff = (novo - cd[col]).abs()
        out.append({"dominio": "crimes", "tipo": tipo, "dias": len(cd),
                    "dias_divergentes": int((diff > 0).sum()), "max_abs_diff": int(diff.max()),
                    "total_novo": int(novo.sum()), "total_diario": int(cd[col].sum())})
    ad = pd.read_csv(os.path.join(SILVER, "acidentes_diario_sp.csv"), parse_dates=["data"]).set_index("data")
    for tipo, f in TIPOS_ACID.items():
        novo = acid[f(acid)].groupby("data").size().reindex(ad.index, fill_value=0)
        diff = (novo - ad[tipo]).abs()
        out.append({"dominio": "sinistros", "tipo": tipo, "dias": len(ad),
                    "dias_divergentes": int((diff > 0).sum()), "max_abs_diff": int(diff.max()),
                    "total_novo": int(novo.sum()), "total_diario": int(ad[tipo].sum())})
    return pd.DataFrame(out)


def figura(dist, crime, acid):
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5))
    for i, (dom, df, tipos) in enumerate((("crimes", crime, TIPOS_CRIME), ("sinistros", acid, TIPOS_ACID))):
        ax = axes[i, 0]
        for tipo in tipos:
            if tipo in ("crime_todos",):
                continue
            d = dist[(dist["dominio"] == dom) & (dist["tipo"] == tipo)]
            ax.plot(d["hora"], d["pct"], marker="o", ms=3, label=tipo)
        ax.set_title(f"{dom}: distribuicao por hora do dia (so registros com hora)")
        ax.set_xlabel("hora local"); ax.set_ylabel("% dos registros"); ax.set_xticks(range(0, 24, 2))
        ax.legend(fontsize=7)
        ax = axes[i, 1]
        m = df.loc[df["tem_hora"], "minuto"].astype(int).value_counts(normalize=True).reindex(range(60), fill_value=0)
        ax.bar(m.index, 100 * m.values, color="tab:gray")
        ax.set_title(f"{dom}: minuto registrado (arredondamento)")
        ax.set_xlabel("minuto"); ax.set_ylabel("% dos registros com hora")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "01_distribuicao_hora_minuto.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    print("V2 Fase 1 / 30: eventos com horario")
    crime = extrai_crime()
    acid = extrai_acidentes()

    q = tabela_qualidade(crime, acid)
    print(q[q["recorte"] == "todos"].to_string(index=False))
    q.to_csv(os.path.join(SILVER, "qualidade_hora.csv"), index=False)
    q.to_csv(os.path.join(TAB, "qualidade_hora.csv"), index=False)

    per = periodo_dos_sem_hora(crime)
    per.to_csv(os.path.join(TAB, "periodo_dos_sem_hora_crime.csv"), index=False)
    dist = distribuicao_hora(crime, acid)
    dist.to_csv(os.path.join(TAB, "distribuicao_por_hora.csv"), index=False)
    conf = confere_com_diario(crime, acid)
    print(conf.to_string(index=False))
    conf.to_csv(os.path.join(TAB, "conferencia_com_diario.csv"), index=False)
    inval = pd.concat([crime.loc[crime["hora_formato_invalido"], "hora_txt"],
                       acid.loc[acid["hora_formato_invalido"], "hora_txt"]]).value_counts().head(20)
    inval.rename("n").to_csv(os.path.join(TAB, "hora_formatos_invalidos.csv"))
    figura(dist, crime, acid)

    crime.to_csv(os.path.join(SILVER, "crime_eventos_sp.csv.gz"), index=False, compression="gzip")
    acid.to_csv(os.path.join(SILVER, "acidentes_eventos_sp.csv.gz"), index=False, compression="gzip")
    print("[ok] data/silver/crime_eventos_sp.csv.gz, acidentes_eventos_sp.csv.gz, qualidade_hora.csv")
