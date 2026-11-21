"""
V4 / Fase 1 -- 36_revisao_parecer.py
Analises novas pedidas na revisao do artigo RP_II pelo parecer externo (docs/prompt_v4_parecer.md, Fase 1).
NAO reestima nada dos scripts 30-34 no lugar: le data/gold/fato_hora_sp.csv e as bases de eventos de
data/silver/ e grava tudo em reports/janelas/revisao/{crimes,sinistros}/. Crimes e sinistros sempre
separados (modelos, familias de BH, pico, conclusoes).

Mudancas em relacao a V2/V3 (aplicadas em TUDO o que este script roda):
  0. Contagem de crime por BO UNICO: dentro de cada desfecho, um BO conta 1 vez (o fato_hora conta
     BO x natureza; diferenca de 0,19% em crimes violentos -- decisao do usuario, 2026-11-20).
  1.3 Jogos do Brasil na Copa de 2022 (5 jogos) excluidos como os eventos de grande publico sem os 4 times:
     horas PRE/DURANTE/POS fora da amostra principal (robustez "com eventos" as traz de volta).
  1.1 Modelo principal da cidade com EF hora x mes (alem de hora x dia da semana e ano x mes); a
     especificacao anterior vira robustez. Placebo, NB, cluster por dia, pareado, event study, tercis.
  1.2 Entorno como diferenca em diferencas: GLM binomial da fracao das ocorrencias que cai no disco do
     estadio (disco x resto da cidade), por estadio e empilhado (EF especificos de cada estadio),
     com a regua completa (BH, placebo, quase-binomial, cluster por dia, pareado), raio 1/2/3/5 km,
     canal do BO, furtos DURANTE+POS e por subtipo, furtos sem hora e Tabela 7 (risco por estadio).
  1.4 Pico: Tabela 5b e validacao nos 12 folds com hora x mes no esperado.

Rodar:  py -3.14 scripts/36_revisao_parecer.py         (ETAPAS=cidade,entorno,pico,resumo para subconjuntos)
"""
import importlib
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.special import expit

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
m = importlib.import_module("33_analise_janelas")
m30 = importlib.import_module("30_eventos_horarios")
SILVER = os.path.join(BASE, "data", "silver")
REPJ = os.path.join(BASE, "reports", "janelas")
REV = os.path.join(REPJ, "revisao")
RNG = np.random.default_rng(20261120)
N_PLACEBO = int(os.environ.get("N_PLACEBO", "1000"))
N_BOOT = 1000
WIN = m.WIN
EST = list(m.ESTADIOS)
RAIOS = [1.0, 2.0, 3.0, 5.0]
HORAS = pd.date_range("2022-01-01", "2023-12-31 23:00", freq="h")
_BASE_X_ORIG = m.base_X

# 1.3 -- conferidos na Wikipedia (horario local AST, UTC+3 -> Brasilia UTC-3 = -6 h):
#   https://en.wikipedia.org/w/index.php?title=2022_FIFA_World_Cup_Group_G&oldid=1370477664
#   https://en.wikipedia.org/w/index.php?title=2022_FIFA_World_Cup_knockout_stage&oldid=1381834010
COPA2022 = [("2022-11-24 16:00", "Brasil x Sérvia"), ("2022-11-28 13:00", "Brasil x Suíça"),
            ("2022-12-02 16:00", "Camarões x Brasil"), ("2022-12-05 16:00", "Brasil x Coreia do Sul"),
            ("2022-12-09 12:00", "Croácia x Brasil")]
FONTE_COPA = ("Wikipedia en, 2022 FIFA World Cup Group G (oldid 1370477664) e knockout stage (oldid 1381834010); "
              "horario local AST (UTC+3) convertido para Brasilia (UTC-3)")

TIPOS_CRIME = {"crimes_violentos": "is_violento", "lesao_corporal_dolosa": "is_lesao_dolosa",
               "roubos_total": "is_roubo", "furtos_total": "is_furto"}
TIPOS_SIN = {"acidentes_com_vitima": "com_vitima", "acidentes_total": "todos", "atropelamentos": "atropelamento"}
NOMES = {"crimes_violentos": "Crimes violentos", "lesao_corporal_dolosa": "Lesão corporal dolosa",
         "roubos_total": "Roubos", "furtos_total": "Furtos", "acidentes_com_vitima": "Sinistros com vítima",
         "acidentes_total": "Sinistros totais", "atropelamentos": "Atropelamentos"}


def dirs(*p):
    d = os.path.join(REV, *p)
    for s in ("tabelas", "figuras"):
        os.makedirs(os.path.join(d, s), exist_ok=True)
    return d


def tab(dom, nome):
    return os.path.join(REV, dom, "tabelas", nome)


def base_X_hm(d, key=None):
    return m.d_override_X(d, ["hm"])


def base_X_sem_hm(d, key=None):
    return m.d_override_X(d)


# ---------------------------------------------------------------------------
# 0. dados: eventos, BO unico, Copa 2022
# ---------------------------------------------------------------------------
def eventos_crime():
    ev = pd.read_csv(os.path.join(SILVER, "crime_eventos_sp.csv.gz"),
                     usecols=["bo_key", "data", "timestamp", "tem_hora", "natureza", "is_violento", "is_lesao_dolosa",
                              "is_roubo", "is_furto", "periodo", "lat", "lon"],
                     parse_dates=["data", "timestamp"])
    ev["conduta"] = conduta_bronze(ev)
    deleg = ev["bo_key"].astype(str).str.split("_", n=2).str[2].str.upper()
    ev["online"] = deleg.str.contains("ELETR|ONLINE", regex=True)
    ev["conduta_nula"] = ev["conduta"].isna() | ev["conduta"].astype(str).str.strip().str.upper().isin(["", "NULL"])
    cond = ev["conduta"].fillna("").astype(str).str.upper()
    ev["furto_veiculo"] = ev["is_furto"] & ev["natureza"].astype(str).str.upper().str.contains("VE.CULO", regex=True)
    ev["furto_transeunte"] = ev["is_furto"] & ~ev["furto_veiculo"] & cond.str.contains("TRANSEUNTE")
    ev["furto_outros"] = ev["is_furto"] & ~ev["furto_veiculo"] & ~ev["furto_transeunte"]
    return ev


def conduta_bronze(ev):
    """DESCR_CONDUTA (so existe no bronze), alinhada linha a linha com o silver (mesmos filtros e ordem do
    30_eventos_horarios.py; conferido pela chave do BO e pela natureza). Cache em data/silver/."""
    cache = os.path.join(SILVER, "crime_conduta_eventos_sp.csv.gz")
    if os.path.exists(cache):
        c = pd.read_csv(cache, dtype=str)
        assert len(c) == len(ev) and (c["bo_key"].to_numpy() == ev["bo_key"].astype(str).to_numpy()).all()
        return c["conduta"].to_numpy()
    partes = []
    for f in m30.CRIME_FILES:
        path = os.path.join(BASE, "data", "bronze", f)
        cols = ["NUM_BO", "ANO_BO", "NOME_DELEGACIA", "DATA_OCORRENCIA_BO", "NATUREZA_APURADA", "CD_IBGE", "DESCR_CONDUTA"]
        for ch in pd.read_csv(path, usecols=cols, dtype=str, chunksize=400_000):
            ch = ch[pd.to_numeric(ch["CD_IBGE"], errors="coerce") == m30.CD_IBGE_SP]
            dt = pd.to_datetime(ch["DATA_OCORRENCIA_BO"].str[:10], errors="coerce")
            ch = ch[(dt >= m30.DATA_MIN) & (dt <= m30.DATA_MAX)]
            k = ch["NUM_BO"].fillna("") + "_" + ch["ANO_BO"].fillna("") + "_" + ch["NOME_DELEGACIA"].fillna("")
            partes.append(pd.DataFrame({"bo_key": k.to_numpy(), "conduta": ch["DESCR_CONDUTA"].to_numpy(),
                                        "nat": ch["NATUREZA_APURADA"].astype(str).str.strip().str.upper().to_numpy()}))
    c = pd.concat(partes, ignore_index=True)
    assert len(c) == len(ev), (len(c), len(ev))
    assert (c["bo_key"].to_numpy() == ev["bo_key"].astype(str).to_numpy()).all()
    assert (c["nat"].to_numpy() == ev["natureza"].astype(str).to_numpy()).all()
    c[["bo_key", "conduta"]].to_csv(cache, index=False, compression="gzip")
    return c["conduta"].to_numpy()


def eventos_sinistro():
    ev = pd.read_csv(os.path.join(SILVER, "acidentes_eventos_sp.csv.gz"),
                     usecols=["id_sinistro", "data", "timestamp", "tem_hora", "com_vitima", "atropelamento", "lat", "lon"],
                     parse_dates=["data", "timestamp"])
    ev["todos"] = True
    ev["bo_key"] = ev["id_sinistro"].astype(str)
    return ev


def prepara_eventos(ev, dom):
    ev = ev.copy()
    ev["tem_hora"] = ev["tem_hora"].astype(bool)
    ev["h"] = ev["timestamp"].dt.floor("h")
    ev["coord_ok"] = ev["lat"].between(*m.BBOX["lat"]) & ev["lon"].between(*m.BBOX["lon"]) & (ev["lat"].abs() > .01)
    ev["ck"] = ev["lat"].round(3).astype(str) + "," + ev["lon"].round(3).astype(str)
    pile = set()
    if dom == "crimes":   # celulas de empilhamento publicadas pelo 33 (regra da Etapa 10)
        dg = pd.read_csv(os.path.join(REPJ, "crimes", "tabelas", "espaco_empilhamento_bairros.csv"))
        for c in dg["celulas_empilhamento_excluidas"].dropna():
            pile |= {x.strip() for x in str(c).split(";")}
    ev["pile"] = ev["ck"].isin(pile)
    for s, (la, lo) in m.ESTADIOS.items():
        ev[f"dist_{s}"] = np.where(ev["coord_ok"], m.dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo), np.inf)
    return ev


def dedup(ev, flag):
    """BO unico dentro do desfecho (o 1o registro do BO; 8 BOs tem mais de um horario)."""
    e = ev[ev[flag].astype(bool)]
    return e.drop_duplicates("bo_key")


def contagens_cidade(ev, tipos):
    out = {}
    for y, flag in tipos.items():
        e = dedup(ev, flag)
        e = e[e["tem_hora"]]
        out[y] = e.groupby("h").size().reindex(HORAS, fill_value=0)
    return out


def flag_copa(f):
    meio = f["hora_ts"] + pd.Timedelta(minutes=30)
    fl = pd.Series(False, index=f.index)
    for s, _ in COPA2022:
        s = pd.Timestamp(s)
        fl |= (meio >= s - pd.Timedelta(hours=2)) & (meio < s + pd.Timedelta(hours=4))
    return fl


def carrega():
    f, jogos, fora = m.carrega()
    evc = prepara_eventos(eventos_crime(), "crimes")
    evs = prepara_eventos(eventos_sinistro(), "sinistros")
    cc = contagens_cidade(evc, TIPOS_CRIME)
    diag = []
    for y in TIPOS_CRIME:
        novo = cc[y].reindex(f["hora_ts"]).to_numpy()
        diag.append({"desfecho": y, "linhas_BO_x_natureza": int(f[y].sum()), "BO_unicos": int(novo.sum()),
                     "excesso_pct": 100 * (f[y].sum() / novo.sum() - 1),
                     "horas_com_diferenca": int((f[y].to_numpy() != novo).sum()),
                     "max_diferenca_hora": int((f[y].to_numpy() - novo).max())})
        f[y] = novo
    cs = contagens_cidade(evs, TIPOS_SIN)
    for y in TIPOS_SIN:
        assert (cs[y].reindex(f["hora_ts"]).to_numpy() == f[y].to_numpy()).all()
    f["excluir_copa2022"] = flag_copa(f)
    sobre = f["excluir_copa2022"] & (f["janela"].isin(WIN) | (f["janela_fora_capital"] != "nenhum"))
    f["excluir_evento_grande_publico"] = f["excluir_evento_grande_publico"] | f["excluir_copa2022"]
    f["hm"] = f["hora_do_dia"].astype(str) + "_" + f["mes"].astype(str)
    dirs("crimes"), dirs("sinistros")
    pd.DataFrame(diag).to_csv(os.path.join(REV, "crimes", "tabelas", "dedup_bo_unico.csv"), index=False)
    pd.DataFrame([{"jogo": n, "inicio_br": s, "horas_excluidas": int((f["excluir_copa2022"] &
                   (abs((f["hora_ts"] + pd.Timedelta(minutes=30) - pd.Timestamp(s)) / pd.Timedelta(hours=1)) < 4.5)).sum()),
                   "fonte": FONTE_COPA} for s, n in COPA2022]).to_csv(os.path.join(REV, "copa2022_exclusao.csv"), index=False)
    print(f"  Copa 2022: {int(f['excluir_copa2022'].sum())} horas excluidas; sobrepostas a janelas dos 4 times: {int(sobre.sum())}")
    return f, jogos, fora, evc, evs


# ---------------------------------------------------------------------------
# funil (item 1.0.5 e Metodologia)
# ---------------------------------------------------------------------------
def medias_horarias(f):
    """media por hora na amostra principal de cada dominio (BO unico; sem dias excluidos, eventos e Copa)."""
    rows = []
    for dom in ("crimes", "sinistros"):
        d = m.amostra(f, dom)
        for y in m.DOM[dom]["desfechos"]:
            rows.append({"dominio": dom, "desfecho": y, "media_hora": d[y].mean(), "n_horas": len(d)})
    r = pd.DataFrame(rows)
    r.to_csv(os.path.join(REV, "medias_horarias.csv"), index=False)
    return r


def funil(evc, evs):
    rows = []
    evc = evc.assign(todos=True)
    for dom, ev, tipos in (("crimes", evc, {"crime_todos": "todos", **TIPOS_CRIME}), ("sinistros", evs, TIPOS_SIN)):
        for y, flag in tipos.items():
            e = dedup(ev, flag)
            th = e["tem_hora"]
            disco = np.zeros(len(e), bool)
            for s in EST:
                disco |= (e[f"dist_{s}"] <= m.R_ENTORNO).to_numpy()
            rows.append({"dominio": dom, "desfecho": y, "registros_municipio": len(e),
                         "com_hora": int(th.sum()), "pct_com_hora": 100 * th.mean(),
                         "com_hora_coord_valida": int((th & e["coord_ok"]).sum()),
                         "pct_coord_valida_entre_com_hora": 100 * (e.loc[th, "coord_ok"]).mean(),
                         "com_hora_nos_discos_3km_bruto": int((th & disco).sum()),
                         "pile_excluido": int((th & disco & e["pile"]).sum()),
                         "pct_pile_dos_discos": 100 * (th & disco & e["pile"]).sum() / max((th & disco).sum(), 1),
                         "com_hora_nos_discos_3km": int((th & disco & ~e["pile"]).sum())})
    r = pd.DataFrame(rows)
    r.to_csv(os.path.join(REV, "funil_registros.csv"), index=False)
    return r


# ---------------------------------------------------------------------------
# 1.1 cidade toda com EF hora x mes
# ---------------------------------------------------------------------------
def cidade(f, jogos, fora, dom):
    out = dirs(dom)
    m.base_X = base_X_hm
    m._CACHE.clear()
    d = m.amostra(f, dom)
    Xhm, X0 = base_X_hm(d), base_X_sem_hm(d)
    g, gd = d["semana_id"].to_numpy(), d["data"].dt.strftime("%Y%m%d").to_numpy()
    TP = m.T_PRINC
    linhas = []
    for y in m.DOM[dom]["desfechos"]:
        r = m.ajusta(d[y], Xhm, d[TP], g)
        linhas += m.coefs(r, TP, {"desfecho": y, "spec": "principal (Poisson, EF hora×mês, cluster semana)"})
        linhas += m.coefs(m.ajusta(d[y], Xhm, d[TP], gd), TP, {"desfecho": y, "spec": "cluster por dia"})
        a = m.alpha_ct(d[y].to_numpy(float), r.fittedvalues.to_numpy())
        linhas += m.coefs(m.ajusta(d[y], Xhm, d[TP], g, "nb", a), TP, {"desfecho": y, "spec": f"Binomial Negativa (alpha={a:.3f})"})
        linhas += m.coefs(m.ajusta(d[y], X0, d[TP], g), TP, {"desfecho": y, "spec": "sem EF hora×mês (especificação anterior)"})
        T1 = ["C_pre", "C_durante", "C_pos", "C_fdj"]
        linhas += m.coefs(m.ajusta(d[y], Xhm, d[T1], g), T1, {"desfecho": y, "spec": "só janela (sem jogos fora da capital)"})
        Tb = ["BO_pre", "BO_durante", "BO_pos", "BO_fdj", "F_pre", "F_durante", "F_pos"]
        rb = m.coefs(m.ajusta(d[y], Xhm, d[Tb], g), Tb, {"desfecho": y, "spec": "só base original (janela_base_original)"})
        for rr in rb:
            rr["termo"] = rr["termo"].replace("BO_", "C_")
        linhas += rb
    de = m.amostra(f, dom, com_eventos=True)
    Xe = base_X_hm(de)
    for y in m.DOM[dom]["desfechos"]:
        linhas += m.coefs(m.ajusta(de[y], Xe, de[TP], de["semana_id"].to_numpy()), TP,
                          {"desfecho": y, "spec": "com horas dos eventos de grande público e da Copa 2022"})
    mp = pd.DataFrame(linhas)
    pm = mp["spec"].str.startswith("principal")
    mp.loc[pm, "p_BH_dominio"] = m.bh(mp.loc[pm, "p"])
    mp["janela"] = mp["termo"].map(m.ROTULO)
    mp.to_csv(os.path.join(out, "tabelas", "modelo_principal_e_robustez.csv"), index=False)
    print("   modelo principal", flush=True)
    m.N_PLACEBO = N_PLACEBO
    pl = m.placebo(f, jogos, fora, dom, out)
    print("   placebo", flush=True)
    cp = m.controles_pareados(f, jogos, fora, dom, out)
    print("   pareado", flush=True)
    es = m.event_study(f, dom, out)
    dose = m.dose_publico(f, jogos, dom, out, d_override=d, rotulo="cidade toda + EF hora×mês", extra_fe=["hm"])
    dose.to_csv(os.path.join(out, "tabelas", "dose_resposta_publico.csv"), index=False)
    het = heterogeneidade_curta(d, Xhm, jogos, fora, dom)
    het.to_csv(os.path.join(out, "tabelas", "heterogeneidade_classico_resultado.csv"), index=False)
    v = m.conclusao(dom, mp, None, pl, None, cp, None)
    v.to_csv(os.path.join(out, "tabelas", "vereditos.csv"), index=False)
    print("   event study, dose, heterogeneidade, vereditos", flush=True)
    m.base_X = _BASE_X_ORIG
    return mp, pl, cp, es, dose, het, v


def heterogeneidade_curta(d, X, jogos, fora, dom):
    """classico e resultado do mandante (so POS), jogos na capital, com a especificacao nova."""
    A = m.atributos_hora(d, jogos, fora)
    rows = []
    for a in ("classico", "resultado"):
        T = d[[c for c in m.T_PRINC if not c.startswith("C_") or c == "C_fdj"]].copy()
        lv = A["C_" + a].astype(str)
        for w in WIN:
            on = d[f"C_{w}"] == 1
            if a == "resultado" and w != "pos":
                T[f"C_{w}"] = on.astype(float)
                continue
            for val in sorted(lv[on].dropna().unique()):
                T[f"C_{w}__{val}"] = (on & (lv == val)).astype(float)
        for y in m.DOM[dom]["desfechos"]:
            r = m.ajusta(d[y], X, T, d["semana_id"].to_numpy())
            cols = [c for c in T.columns if "__" in c]
            for rr in m.coefs(r, cols, {"desfecho": y, "atributo": a}):
                rr["janela"], rr["nivel"] = rr["termo"].split("__")[0][2:], rr["termo"].split("__")[1]
                rr["n_horas"] = int(T[rr["termo"]].sum())
                rows.append(rr)
    h = pd.DataFrame(rows)
    for a, gg in h.groupby("atributo"):
        h.loc[gg.index, "p_BH_dominio_atributo"] = m.bh(gg["p"])
    return h


# ---------------------------------------------------------------------------
# 1.2 entorno: GLM binomial da fracao no disco (diferenca em diferencas)
# ---------------------------------------------------------------------------
def logit_fwl(blocks, q, maxit=60, tol=1e-10):
    """GLM binomial (logit) com blocos de efeitos fixos especificos de cada estadio e q coeficientes comuns
    (T), por IRLS com Frisch-Waugh-Lovell dentro de cada bloco. Erros: cluster (semana, dia; os clusters
    sao comuns aos blocos, entao horas da mesma semana em estadios diferentes ficam no mesmo cluster) e
    quase-binomial (dispersao de Pearson). Com q=0 so ajusta os efeitos fixos (modelo de base)."""
    st = []
    for b in blocks:
        p0 = np.clip((b["y"] + .5) / (b["N"] + 1), 1e-6, 1 - 1e-6)
        st.append({"eta": np.log(p0 / (1 - p0))})
    beta = np.zeros(q)
    dev_old = np.inf
    for it in range(maxit):
        M, v, cache = np.zeros((q, q)), np.zeros(q), []
        for b, s in zip(blocks, st):
            p = expit(s["eta"])
            W = np.maximum(b["N"] * p * (1 - p), 1e-10)
            z = s["eta"] + (b["y"] - b["N"] * p) / W
            Xw = b["X"] * W[:, None]
            Ainv = np.linalg.pinv(b["X"].T @ Xw)
            if q:
                Tr = b["T"] - b["X"] @ (Ainv @ (Xw.T @ b["T"]))
                zr = z - b["X"] @ (Ainv @ (Xw.T @ z))
                M += Tr.T @ (Tr * W[:, None])
                v += Tr.T @ (W * zr)
            cache.append((z, Xw, Ainv))
        if q:
            beta = np.linalg.solve(M, v)
        dev = 0.0
        for b, s, (z, Xw, Ainv) in zip(blocks, st, cache):
            tb = b["T"] @ beta if q else 0.0
            s["gam"] = Ainv @ (Xw.T @ (z - tb))
            s["eta"] = b["X"] @ s["gam"] + tb
            p = np.clip(expit(s["eta"]), 1e-12, 1 - 1e-12)
            y, N = b["y"], b["N"]
            with np.errstate(divide="ignore", invalid="ignore"):
                dev += 2 * np.sum(np.where(y > 0, y * np.log(y / (N * p)), 0) +
                                  np.where(N - y > 0, (N - y) * np.log((N - y) / (N * (1 - p))), 0))
        if abs(dev - dev_old) < tol * (abs(dev) + 1):
            break
        dev_old = dev
    res = {"beta": beta, "blocks": st, "dev": dev, "iter": it}
    if not q:
        return res
    # sanduiche no ponto final
    U, gw, gd, n, K, pear = [], [], [], 0, q, 0.0
    M = np.zeros((q, q))
    for b, s in zip(blocks, st):
        p = expit(s["eta"])
        W = np.maximum(b["N"] * p * (1 - p), 1e-10)
        Xw = b["X"] * W[:, None]
        Ainv = np.linalg.pinv(b["X"].T @ Xw)
        Tr = b["T"] - b["X"] @ (Ainv @ (Xw.T @ b["T"]))
        e = b["y"] - b["N"] * p
        M += Tr.T @ (Tr * W[:, None])
        U.append(Tr * e[:, None])
        gw.append(b["g"]), gd.append(b["gd"])
        n += len(e)
        K += np.linalg.matrix_rank(b["X"].T @ Xw)     # mesmo posto de X, em k x k (mais barato)
        pear += np.sum(e ** 2 / W)
    U = np.vstack(U)
    Minv = np.linalg.inv(M)
    out = {}
    for nome, g in (("semana", np.concatenate(gw)), ("dia", np.concatenate(gd))):
        S = pd.DataFrame(U).groupby(g).sum().to_numpy()
        G = len(S)
        c = G / (G - 1) * (n - 1) / (n - K)
        out[nome] = np.sqrt(np.diag(c * Minv @ (S.T @ S) @ Minv))
    phi = pear / (n - K)
    out["quase"] = np.sqrt(np.diag(phi * Minv))
    res.update({"se": out, "phi": phi, "n": n, "K": K})
    return res


def X_entorno(d, hm=True):
    """EF hora x dia da semana + hora x mes + ano x mes + feriado + chuva (spec do prompt V4, 1.2).
    hm=False: robustez sem o EF hora x mes."""
    X = pd.get_dummies(d[["hd", "am"]], drop_first=True).astype(float)
    if hm:
        X = m._interacoes_hora(X, d, "hm")
    for c in ("feriado", "chuva_l", "chuva_na"):
        X[c] = d[c].to_numpy(float)
    X.insert(0, "const", 1.0)
    return X


def contagens_entorno(ev, flag, raio, filtro=None):
    """contagem horaria (BO unico, com hora) no disco de cada estadio (sem celulas de empilhamento) e no
    resto da cidade (coordenada valida, fora dos tres discos)."""
    e = ev if filtro is None else ev[filtro(ev)]
    e = dedup(e, flag)
    e = e[e["tem_hora"] & e["coord_ok"] & ~e["pile"]]
    em_disco = np.zeros(len(e), bool)
    out = {}
    for s in EST:
        mk = (e[f"dist_{s}"] <= raio).to_numpy()
        em_disco |= mk
        out[s] = e[mk].groupby("h").size().reindex(HORAS, fill_value=0)
    out["resto"] = e[~em_disco].groupby("h").size().reindex(HORAS, fill_value=0)
    return out


def termos_estadio(d, s, combinar_dp=False):
    est = d["jogo_estadio"].eq(s)
    own = {w: ((d[f"C_{w}"] == 1) & est).astype(float).to_numpy() for w in WIN}
    if combinar_dp:
        own = {"pre": own["pre"], "dp": own["durante"] + own["pos"]}
    ctrl = pd.DataFrame({f"C_{w}_outro": ((d[f"C_{w}"] == 1) & ~est).astype(float) for w in WIN}, index=d.index)
    for c in ("C_fdj", "F_pre", "F_durante", "F_pos"):
        ctrl[c] = d[c].to_numpy(float)
    return own, ctrl


def blocos(d, Xe, cont, estadios, combinar_dp=False, linhas=None):
    bl, nomes = [], None
    for s in estadios:
        ye = cont[s].reindex(d["hora_ts"]).to_numpy(float)
        N = ye + cont["resto"].reindex(d["hora_ts"]).to_numpy(float)
        own, ctrl = termos_estadio(d, s, combinar_dp)
        ok = N > 0
        if linhas is not None:
            ok &= linhas[s]
        X = pd.concat([Xe, ctrl], axis=1).to_numpy(float)[ok]
        X = X[:, (X != 0).any(axis=0)]
        nomes = list(own)
        T = np.column_stack([own[k] for k in nomes])[ok]
        bl.append({"X": X, "T": T, "y": ye[ok], "N": N[ok], "g": d["semana_id"].to_numpy()[ok],
                   "gd": d["data"].dt.strftime("%Y%m%d").to_numpy()[ok], "estadio": s})
    return bl, nomes


def eventos_na_janela(bl):
    """ocorrencias no disco nas horas de cada termo comum (0 = coeficiente nao identificado: separacao)."""
    return np.sum([b["y"] @ b["T"] for b in bl], axis=0)


def coefs_fwl(res, nomes, extra, n_ev=None):
    rows = []
    for i, w in enumerate(nomes):
        b = res["beta"][i]
        r = {"janela": w, "IRR": np.exp(b), "var_pct": 100 * (np.exp(b) - 1), **extra}
        for k, se in res["se"].items():
            sfx = "" if k == "semana" else f"_{k}"
            r[f"IC95_lo{sfx}"], r[f"IC95_hi{sfx}"] = np.exp(b - 1.96 * se[i]), np.exp(b + 1.96 * se[i])
            r[f"p{sfx}"] = 2 * stats.norm.sf(abs(b / se[i]))
        r["phi"] = res["phi"]
        if n_ev is not None:
            r["eventos_na_janela"] = int(n_ev[i])
            if n_ev[i] == 0:      # nenhuma ocorrencia no disco nas horas da janela: beta -> -inf (separacao)
                for c in list(r):
                    if c.startswith(("IRR", "var_pct", "IC95", "p")):
                        r[c] = np.nan
        rows.append(r)
    return rows


def ajusta_entorno(d, Xe, cont, extra, combinar_dp=False, por_estadio=True):
    rows = []
    for est in ([[s] for s in EST] if por_estadio else []) + [EST]:
        bl, nomes = blocos(d, Xe, cont, est, combinar_dp)
        res = logit_fwl(bl, len(nomes))
        rows += coefs_fwl(res, nomes, {**extra, "estadio": est[0] if len(est) == 1 else "3 estádios (empilhado)",
                                       "n_horas": res["n"], "media_hora_disco": np.mean(np.concatenate([b["y"] for b in bl]))},
                          n_ev=eventos_na_janela(bl))
    return rows


def checa_fwl(d, Xe, cont):
    """confere o IRLS-FWL contra o statsmodels num estadio (mesma estimativa e mesmo EP agrupado)."""
    bl, nomes = blocos(d, Xe, cont, [EST[0]])
    b = bl[0]
    res = logit_fwl(bl, len(nomes))
    XX = np.column_stack([b["X"], b["T"]])
    r = sm.GLM(np.column_stack([b["y"], b["N"] - b["y"]]), XX, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": b["g"]})
    q = len(nomes)
    return pd.DataFrame({"termo": nomes, "beta_fwl": res["beta"], "beta_statsmodels": r.params[-q:],
                         "se_fwl": res["se"]["semana"], "se_statsmodels": r.bse[-q:]})


def placebo_entorno(d, Xe, cont, jogos, combinar_dp=False):
    """Permutacao em dois passos por estadio: modelo de base (EF + controles, sem as janelas do proprio
    estadio) ajustado so nas horas livres desse estadio; estatistica = log(sum obs / sum esperado) da
    fracao no disco nas horas da janela. Inicios falsos: mesmo dia da semana e mesmo horario do jogo,
    em qualquer dia da amostra sem jogo naquele estadio e sem feriado, horas fora de qualquer janela da
    capital. Agregado = mesma estatistica somando os tres estadios (sorteio conjunto)."""
    dd = d.reset_index(drop=True)
    pos = {h: i for i, h in enumerate(dd["hora_ts"])}
    janelas_w = ["pre", "durante", "pos", "dp"]
    real_o, real_e, sim_o, sim_e = {}, {}, {}, {}
    dias = dd.groupby("data").agg(fer=("feriado", "first"), dow=("dia_semana", "first"))
    for s in EST:
        ye = cont[s].reindex(dd["hora_ts"]).to_numpy(float)
        N = ye + cont["resto"].reindex(dd["hora_ts"]).to_numpy(float)
        own, ctrl = termos_estadio(dd, s)
        dias_s = set(jogos.loc[jogos["estadio"] == s, "data_br"].dt.normalize())
        dia_s = dd["data"].isin(dias_s).to_numpy()
        livre = (own["pre"] + own["durante"] + own["pos"] == 0) & ~dia_s
        Xall = pd.concat([Xe.reset_index(drop=True), ctrl.reset_index(drop=True)], axis=1).to_numpy(float)
        fit = livre & (N > 0)
        keep = (Xall[fit] != 0).any(axis=0)
        res = logit_fwl([{"X": Xall[fit][:, keep], "T": np.zeros((fit.sum(), 0)), "y": ye[fit], "N": N[fit]}], 0)
        E = N * expit(Xall[:, keep] @ res["blocks"][0]["gam"])
        own["dp"] = own["durante"] + own["pos"]
        for w in janelas_w:
            mk = own[w] == 1
            real_o[(s, w)], real_e[(s, w)] = ye[mk].sum(), E[mk].sum()
        livre_cand = livre & (~dd["janela"].isin(WIN)).to_numpy()
        cand_dias = dias[(dias["fer"] == 0) & ~dias.index.isin(dias_s)]
        cand = []
        for _, gj in jogos[jogos["estadio"] == s].iterrows():
            s0 = gj["inicio_br"]
            dow = (s0.weekday() + 1) % 7
            opts = []
            for dt in cand_dias[cand_dias["dow"] == dow].index:
                jw = m._janelas_de_inicio(dt + (s0 - s0.normalize()), pos)
                if all(len(jw[w]) == 2 for w in WIN) and all(livre_cand[i] for w in WIN for i in jw[w]):
                    jw["dp"] = jw["durante"] + jw["pos"]
                    opts.append(jw)
            if opts:
                cand.append(opts)
        so = {w: np.empty(N_PLACEBO) for w in janelas_w}
        se_ = {w: np.empty(N_PLACEBO) for w in janelas_w}
        for r in range(N_PLACEBO):
            esc = [c[RNG.integers(len(c))] for c in cand]
            for w in janelas_w:
                idx = np.concatenate([e[w] for e in esc])
                so[w][r], se_[w][r] = ye[idx].sum(), E[idx].sum()
        sim_o[s], sim_e[s] = so, se_
    rows = []
    for alvo in EST + ["3 estádios (empilhado)"]:
        ss = EST if alvo.startswith("3") else [alvo]
        for w in janelas_w:
            real = np.log(sum(real_o[(s, w)] for s in ss) / sum(real_e[(s, w)] for s in ss))
            sim = np.log(sum(sim_o[s][w] for s in ss) / sum(sim_e[s][w] for s in ss))
            rows.append({"estadio": alvo, "janela": w, "IRR_real_2passos": np.exp(real),
                         "placebo_p2.5": np.exp(np.percentile(sim, 2.5)), "placebo_p97.5": np.exp(np.percentile(sim, 97.5)),
                         "p_permutacao_bilateral": min(1, 2 * min((sim >= real).mean(), (sim <= real).mean()))})
    return pd.DataFrame(rows)


def pareado_entorno(d, cont, jogos, cc=0.0):
    """cada jogo contra o mesmo dia da semana e horario, +-4 semanas, em dia sem jogo na capital e sem jogo
    fora da capital (mesma regra do pareado da cidade), sem feriado e com as 24 h na amostra; DiD da fracao
    no disco: log(frac janela/frac FORA) no dia do jogo menos o mesmo nos controles (somas sobre os jogos)."""
    dd = d.set_index("hora_ts")
    dias = dd.groupby("data").agg(dow=("dia_semana", "first"), fer=("feriado", "first"), cap=("dia_de_jogo", "first"),
                                  fora=("janela_fora_capital", lambda x: (x != "nenhum").any()), n=("hora_do_dia", "size"))
    livres = dias[(dias["fer"] == 0) & ~dias["cap"] & ~dias["fora"] & (dias["n"] == 24)].index
    na_amostra = HORAS.isin(dd.index)
    resto = cont["resto"].where(na_amostra)          # horas fora da amostra (Copa, dias excluidos) = ausentes
    rows = []
    for s in EST:
        ye = cont[s].where(na_amostra)
        for _, gj in jogos[jogos["estadio"] == s].iterrows():
            s0 = gj["inicio_br"]
            dia = s0.normalize()
            dow = (s0.weekday() + 1) % 7
            ctr = [c for c in livres if abs(c - dia) <= pd.Timedelta(days=28) and dias.loc[c, "dow"] == dow]
            if len(ctr) < 2 or dia not in dias.index or dias.loc[dia, "n"] < 24:
                continue
            jw = {w: [] for w in WIN}
            for dh in range(-4, 6):
                h = s0.floor("h") + pd.Timedelta(hours=dh)
                k = int(np.floor(((h + pd.Timedelta(minutes=30)) - s0) / pd.Timedelta(hours=1)))
                w = {-2: "pre", -1: "pre", 0: "durante", 1: "durante", 2: "pos", 3: "pos"}.get(k)
                if w:
                    jw[w].append(h - dia)
            jw["dp"] = jw["durante"] + jw["pos"]
            hd = dd.loc[dd["data"] == dia]
            fora_h = [h - dia for h in hd.index if hd.loc[h, "janela"] in ("fora_dia_jogo", "dia_sem_jogo")
                      and hd.loc[h, "janela_fora_capital"] == "nenhum"]
            if len(fora_h) < 6:
                continue
            if any((dia + o) not in dd.index for o in jw["pre"] + jw["dp"]):
                continue

            def soma(base, offs):
                hs = [base + o for o in offs]
                a, b = ye.reindex(hs), resto.reindex(hs)
                if a.isna().any() or b.isna().any():
                    return np.nan, np.nan
                return float(a.sum()), float(a.sum() + b.sum())
            rec = {"estadio": s, "dia": dia, "n_ctrl": len(ctr)}
            for w, offs in list(jw.items()) + [("F", fora_h)]:
                a, b = soma(dia, offs)
                ctl = [soma(c, offs) for c in ctr]
                rec[f"{w}_e_j"], rec[f"{w}_N_j"] = a, b
                rec[f"{w}_e_c"], rec[f"{w}_N_c"] = np.nanmean([x[0] for x in ctl]), np.nanmean([x[1] for x in ctl])
            rows.append(rec)
    p = pd.DataFrame(rows).dropna()

    def did(g, w):
        # cc = correcao de continuidade (so sinistros: somas zero no disco em reamostragens com poucos jogos)
        f_ = lambda a, b: np.log((g[a].sum() + cc) / (g[b].sum() + 2 * cc))
        return (f_(f"{w}_e_j", f"{w}_N_j") - f_("F_e_j", "F_N_j")) - (f_(f"{w}_e_c", f"{w}_N_c") - f_("F_e_c", "F_N_c"))
    res = []
    for alvo in EST + ["3 estádios (empilhado)"]:
        g = p if alvo.startswith("3") else p[p["estadio"] == alvo]
        for w in ("pre", "durante", "pos", "dp"):
            est = did(g, w)
            boots = []
            for _ in range(N_BOOT):
                gb = g.iloc[RNG.integers(0, len(g), len(g))]
                with np.errstate(divide="ignore"):
                    boots.append(did(gb, w))
            boots = np.array(boots)
            n_fin = int(np.isfinite(boots).sum())
            boots = boots[np.isfinite(boots)]
            lo, hi = (np.exp(np.percentile(boots, [2.5, 97.5])) if n_fin >= 0.95 * N_BOOT else (np.nan, np.nan))
            res.append({"estadio": alvo, "janela": w, "n_jogos": len(g), "DiD_IRR": np.exp(est),
                        "IC95_lo": lo, "IC95_hi": hi, "boot_finitos": n_fin, "correcao_continuidade": cc})
    return pd.DataFrame(res), p


def veredito_entorno(mainr, pl, cp):
    """mesma regra da Metodologia: candidato = p_BH < 0,05 e placebo p < 0,05 e mesmo sinal com p < 0,10
    na quase-binomial e no cluster por dia; 'efeito robusto' so se o pareado confirma (mesmo sinal, IC sem
    o 1); 'contradito' se o IC do pareado exclui a estimativa (ou sinal oposto com IC sem o 1)."""
    out = []
    for _, r in mainr.iterrows():
        plr = pl[(pl["estadio"] == r["estadio"]) & (pl["janela"] == r["janela"])]
        p_pl = plr["p_permutacao_bilateral"].iloc[0] if len(plr) else np.nan
        rob = (r["p_quase"] < .10) and (r["p_dia"] < .10)   # mesmo sinal: mesmo beta nas duas
        c = cp[(cp["estadio"] == r["estadio"]) & (cp["janela"] == r["janela"])]
        conf = contra = False
        if len(c) and np.isfinite(c.iloc[0][["IC95_lo", "IC95_hi"]].astype(float)).all():
            c = c.iloc[0]
            ms = np.sign(np.log(c["DiD_IRR"])) == np.sign(np.log(r["IRR"]))
            ex1 = not (c["IC95_lo"] <= 1 <= c["IC95_hi"])
            conf = bool(ms and ex1)
            contra = bool(not (c["IC95_lo"] <= r["IRR"] <= c["IC95_hi"]) or (not ms and ex1))
        cand = (r["p_BH"] < .05) and (p_pl < .05) and rob
        v = ("efeito robusto" if cand and conf else "contradito pelo pareado" if cand and contra else
             "robusto no GLM, pareado inconclusivo" if cand else "sinal não robusto" if r["p"] < .05 else "sem evidência")
        out.append({**r.to_dict(), "p_placebo": p_pl, "robustez_quase_e_dia_ok": rob, "pareado_confirma": conf,
                    "pareado_contradiz": contra, "veredito": v})
    return pd.DataFrame(out)


def entorno(f, jogos, ev, dom):
    out = dirs(dom)
    d = m.amostra(f, dom)
    Xe = X_entorno(d)
    tipos = TIPOS_CRIME if dom == "crimes" else TIPOS_SIN
    cont3 = {y: contagens_entorno(ev, flag, 3.0) for y, flag in tipos.items()}
    chk = checa_fwl(d, Xe, cont3[list(tipos)[0]])
    chk.to_csv(os.path.join(out, "tabelas", "entorno_checagem_fwl_vs_statsmodels.csv"), index=False)
    print("   checagem FWL x statsmodels:\n", chk.round(5).to_string(), flush=True)
    # modelo principal (3 km): janelas separadas; furtos tambem DURANTE+POS
    rows = []
    for y in tipos:
        rows += ajusta_entorno(d, Xe, cont3[y], {"desfecho": y, "spec": "janelas"})
        if y == "furtos_total" or dom == "sinistros":
            rows += ajusta_entorno(d, Xe, cont3[y], {"desfecho": y, "spec": "PRÉ + DURANTE+PÓS"}, combinar_dp=True)
    r = pd.DataFrame(rows)
    r = r[~((r["spec"] == "PRÉ + DURANTE+PÓS") & (r["janela"] == "pre"))]   # PRE ja esta na spec de janelas
    agg = r["estadio"].str.startswith("3")
    r.loc[agg, "p_BH"] = m.bh(r.loc[agg, "p"])                 # familia: empilhados (desfechos x janelas)
    r.loc[~agg, "p_BH"] = m.bh(r.loc[~agg, "p"])               # familia: por estadio
    print("   entorno principal", flush=True)
    pls, cps = [], []
    for y in tipos:
        pl = placebo_entorno(d, Xe, cont3[y], jogos)
        pl["desfecho"] = y
        pls.append(pl)
        cp, _ = pareado_entorno(d, cont3[y], jogos, cc=0.5 if dom == "sinistros" else 0.0)
        cp["desfecho"] = y
        cps.append(cp)
    pl, cp = pd.concat(pls), pd.concat(cps)
    pl.to_csv(os.path.join(out, "tabelas", "entorno_placebo.csv"), index=False)
    cp.to_csv(os.path.join(out, "tabelas", "entorno_pareado.csv"), index=False)
    print("   entorno placebo e pareado", flush=True)
    vs = []
    for y in tipos:
        rr = r[r["desfecho"] == y]
        vs.append(veredito_entorno(rr, pl[pl["desfecho"] == y], cp[cp["desfecho"] == y]))
    v = pd.concat(vs)
    v.to_csv(os.path.join(out, "tabelas", "entorno_modelo_principal.csv"), index=False)
    # raio
    rows = []
    for raio in RAIOS:
        for y, flag in tipos.items():
            c = cont3[y] if raio == 3.0 else contagens_entorno(ev, flag, raio)
            rows += ajusta_entorno(d, Xe, c, {"desfecho": y, "raio_km": raio, "spec": "janelas"}, por_estadio=False)
            if y == "furtos_total":
                rr = ajusta_entorno(d, Xe, c, {"desfecho": y, "raio_km": raio, "spec": "PRÉ + DURANTE+PÓS"},
                                    combinar_dp=True, por_estadio=False)
                rows += [x for x in rr if x["janela"] == "dp"]
    pd.DataFrame(rows).to_csv(os.path.join(out, "tabelas", "entorno_raio.csv"), index=False)
    print("   entorno raio", flush=True)
    extras = {}
    if dom == "crimes":
        extras["canal"] = canal(d, Xe, ev, out)
        extras["subtipos"] = subtipos(d, Xe, ev, out)
        extras["sem_hora"] = furtos_sem_hora(f, jogos, ev, d, Xe, cont3["furtos_total"], out)
    extras["risco"] = tabela_risco(d, Xe, cont3, out, dom)
    return v, pl, cp, extras


VERSOES = {"todos": None, "só presencial": lambda e: ~e["online"], "só BO online": lambda e: e["online"],
           "sem conduta nula": lambda e: ~e["conduta_nula"]}


def canal(d, Xe, ev, out):
    rows = []
    for vn, filt in VERSOES.items():
        for y in ("furtos_total", "roubos_total", "crimes_violentos"):
            c = contagens_entorno(ev, TIPOS_CRIME[y], 3.0, filt)
            rows += ajusta_entorno(d, Xe, c, {"versao": vn, "desfecho": y, "spec": "janelas"}, por_estadio=False)
            if y == "furtos_total":
                rr = ajusta_entorno(d, Xe, c, {"versao": vn, "desfecho": y, "spec": "PRÉ + DURANTE+PÓS"},
                                    combinar_dp=True, por_estadio=False)
                rows += [x for x in rr if x["janela"] == "dp"]
    r = pd.DataFrame(rows)
    for vn, g in r.groupby("versao"):
        r.loc[g.index, "p_BH_versao"] = m.bh(g["p"])
    r.to_csv(os.path.join(out, "tabelas", "entorno_canal.csv"), index=False)
    return r


def subtipos(d, Xe, ev, out):
    rows = []
    for st in ("furto_veiculo", "furto_transeunte", "furto_outros"):
        c = contagens_entorno(ev, st, 3.0)
        rows += ajusta_entorno(d, Xe, c, {"desfecho": st, "spec": "janelas"}, por_estadio=False)
        rr = ajusta_entorno(d, Xe, c, {"desfecho": st, "spec": "PRÉ + DURANTE+PÓS"}, combinar_dp=True, por_estadio=False)
        rows += [x for x in rr if x["janela"] == "dp"]
    r = pd.DataFrame(rows)
    r["p_BH_subtipos"] = m.bh(r["p"])
    tot = []
    for st in ("furto_veiculo", "furto_transeunte", "furto_outros"):
        e = dedup(ev, st)
        tot.append({"subtipo": st, "n_com_hora_todo_municipio": int(e["tem_hora"].sum())})
    r = r.merge(pd.DataFrame(tot), left_on="desfecho", right_on="subtipo", how="left").drop(columns="subtipo")
    r.to_csv(os.path.join(out, "tabelas", "entorno_furtos_subtipos.csv"), index=False)
    return r


def furtos_sem_hora(f, jogos, ev, d, Xe, cont_h, out):
    """(a) a fracao de furtos SEM hora no disco muda em dia de jogo naquele estadio? (b) variacao diaria dos
    furtos no disco (todos, com e sem hora; diferenca em diferencas contra o resto da cidade) e excesso
    diario comparado com o excesso das janelas (so furtos com hora). Testa o fator 1/(1-0,528)=2,12."""
    e = dedup(ev, "is_furto")
    e = e[e["coord_ok"] & ~e["pile"]]
    excl = set(f.loc[f["excluir_crime"], "data"]) | set(f.loc[f["excluir_copa2022"], "data"])
    dias = pd.date_range("2022-01-01", "2023-12-31", freq="D")
    cal = f.drop_duplicates("data").set_index("data")[["dia_semana", "am", "feriado", "semana_id"]]
    em_disco = np.zeros(len(e), bool)
    for s in EST:
        em_disco |= (e[f"dist_{s}"] <= 3.0).to_numpy()
    resto_tot = e[~em_disco].groupby("data").size().reindex(dias, fill_value=0)
    resto_ch = e[~em_disco & e["tem_hora"]].groupby("data").size().reindex(dias, fill_value=0)
    partes = []
    for s in EST:
        es = e[(e[f"dist_{s}"] <= 3.0).to_numpy()]
        dj = set(jogos.loc[jogos["estadio"] == s, "data_br"].dt.normalize())
        partes.append(pd.DataFrame({"estadio": s, "data": dias,
                                    "n_tot": es.groupby("data").size().reindex(dias, fill_value=0).to_numpy(),
                                    "n_sem": es[~es["tem_hora"]].groupby("data").size().reindex(dias, fill_value=0).to_numpy(),
                                    "n_ch": es[es["tem_hora"]].groupby("data").size().reindex(dias, fill_value=0).to_numpy(),
                                    "resto_tot": resto_tot.to_numpy(), "resto_ch": resto_ch.to_numpy(),
                                    "jogo": [dt in dj for dt in dias]}))
    p = pd.concat(partes, ignore_index=True)
    p = p[~p["data"].isin(excl)].join(cal, on="data")
    X = pd.get_dummies(p[["dia_semana", "am", "estadio"]].astype(str), drop_first=True).astype(float)
    X["feriado"] = p["feriado"].to_numpy(float)
    X = sm.add_constant(X)
    X["jogo_no_estadio"] = p["jogo"].astype(float).to_numpy()
    g = p["semana_id"].to_numpy()
    rows = []
    specs = {"(a) fração sem hora no disco": (p["n_sem"], p["n_tot"]),
             "(b) disco vs resto, todos os furtos (com e sem hora)": (p["n_tot"], p["n_tot"] + p["resto_tot"]),
             "(b') disco vs resto, só furtos com hora": (p["n_ch"], p["n_ch"] + p["resto_ch"])}
    exc = {}
    for nome, (yv, Nv) in specs.items():
        ok = (Nv > 0).to_numpy()
        yv, Nv = yv.to_numpy(float)[ok], Nv.to_numpy(float)[ok]
        r = sm.GLM(np.column_stack([yv, Nv - yv]), X[ok], family=sm.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": g[ok]})
        b, se = r.params["jogo_no_estadio"], r.bse["jogo_no_estadio"]
        Xcf = X[ok].copy()
        Xcf["jogo_no_estadio"] = 0.0
        pcf = r.predict(Xcf)
        jg = X.loc[ok, "jogo_no_estadio"].to_numpy() == 1
        exc[nome] = float((yv[jg] - Nv[jg] * pcf[jg]).sum())
        rows.append({"spec": nome, "OR_ou_RR_dia_jogo": np.exp(b), "IC95_lo": np.exp(b - 1.96 * se),
                     "IC95_hi": np.exp(b + 1.96 * se), "p": r.pvalues["jogo_no_estadio"],
                     "excesso_total_dias_de_jogo": exc[nome], "n_dias_jogo": int(jg.sum()),
                     "excesso_por_jogo": exc[nome] / max(jg.sum(), 1)})
    # excesso das janelas (modelo horario empilhado, so com hora): PRE + DURANTE+POS
    bl, nomes = blocos(d, Xe, cont_h, EST, combinar_dp=True)
    res = logit_fwl(bl, len(nomes))
    exw = 0.0
    for b_, s_ in zip(bl, res["blocks"]):
        tb = b_["T"] @ res["beta"]
        on = (b_["T"].sum(axis=1) > 0)
        pcf = expit(s_["eta"] - tb)
        exw += float((b_["y"][on] - b_["N"][on] * pcf[on]).sum())
    njog = int(sum(jogos["estadio"].isin(EST)))
    rows.append({"spec": "(c) janelas PRÉ+DURANTE+PÓS, modelo horário (só com hora)", "excesso_total_dias_de_jogo": exw,
                 "n_dias_jogo": njog, "excesso_por_jogo": exw / njog})
    r = pd.DataFrame(rows)
    a_, b_ = exc["(b) disco vs resto, todos os furtos (com e sem hora)"], exc["(b') disco vs resto, só furtos com hora"]
    r["fator_empirico_todos_sobre_com_hora"] = a_ / b_ if b_ else np.nan
    r["fator_suposto_2_12"] = 1 / (1 - 0.528)
    r.to_csv(os.path.join(out, "tabelas", "entorno_furtos_sem_hora.csv"), index=False)
    return r


def tabela_risco(d, Xe, cont3, out, dom):
    """Tabela 7: risco esperado por estadio x janela para um jogo tipico, a partir do modelo novo (por
    estadio). Esperado sem jogo = media das horas sem jogo no disco na mesma hora x dia da semana."""
    slots = {"domingo 16h": (0, 16.0), "quarta 21h30": (3, 21.5)}
    alvos = ["crimes_violentos", "roubos_total", "furtos_total"] if dom == "crimes" else ["acidentes_com_vitima"]
    rows = []
    for y in alvos:
        for s in EST:
            for comb in (False, True):
                if comb and y != "furtos_total":
                    continue
                bl, nomes = blocos(d, Xe, cont3[y], [s], combinar_dp=comb)
                res = logit_fwl(bl, len(nomes))
                ye = pd.Series(cont3[y][s].reindex(d["hora_ts"]).to_numpy(float), index=d.index)
                base_hd = ye[d["hora_sem_jogo"]].groupby([d["dia_semana"], d["hora_do_dia"]]).mean()
                for slot, (dow, hini) in slots.items():
                    hs_w = {"pre": [hini - 2, hini - 1], "durante": [hini, hini + 1], "pos": [hini + 2, hini + 3]}
                    hs_w["dp"] = hs_w["durante"] + hs_w["pos"]
                    for i, w in enumerate(nomes):
                        if comb and w == "pre":
                            continue
                        b0 = sum(base_hd.get(((dow if hh < 24 else (dow + 1) % 7), int(np.floor(hh)) % 24), np.nan)
                                 for hh in hs_w[w])
                        bt, se = res["beta"][i], res["se"]["semana"][i]
                        rows.append({"desfecho": y, "estadio": s, "jogo_tipico": slot, "janela": w,
                                     "n_horas_janela": len(hs_w[w]), "esperado_sem_jogo": b0, "IRR": np.exp(bt),
                                     "excesso": b0 * (np.exp(bt) - 1), "excesso_IC95_lo": b0 * (np.exp(bt - 1.96 * se) - 1),
                                     "excesso_IC95_hi": b0 * (np.exp(bt + 1.96 * se) - 1),
                                     "p": 2 * stats.norm.sf(abs(bt / se))})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(out, "tabelas", "entorno_tabela_risco.csv"), index=False)
    return t


def entorno_sem_hm(f, ev, dom):
    """robustez da Tabela 3: modelo do entorno (empilhado, 3 km) sem o EF hora x mes."""
    d = m.amostra(f, dom)
    X0 = X_entorno(d, hm=False)
    tipos = TIPOS_CRIME if dom == "crimes" else TIPOS_SIN
    rows = []
    for y, flag in tipos.items():
        c = contagens_entorno(ev, flag, 3.0)
        rows += ajusta_entorno(d, X0, c, {"desfecho": y, "spec": "janelas, sem EF hora×mês"}, por_estadio=False)
        rr = ajusta_entorno(d, X0, c, {"desfecho": y, "spec": "PRÉ + DURANTE+PÓS, sem EF hora×mês"},
                            combinar_dp=True, por_estadio=False)
        rows += [x for x in rr if x["janela"] == "dp"]
    r = pd.DataFrame(rows)
    r.to_csv(tab(dom, "entorno_sem_hora_mes.csv"), index=False)
    return r


def drade(evc):
    """BOs registrados pela DRADE (delegacia de intolerancia esportiva) no disco de 3 km dos estadios,
    2022-2023, todas as naturezas, com e sem hora (BO unico; mesma regra de nome do 34a)."""
    e = evc.drop_duplicates("bo_key")
    e = e[e["coord_ok"] & ~e["pile"]]
    deleg = e["bo_key"].astype(str).str.split("_", n=2).str[2].str.upper()
    dr = deleg.str.contains("DRADE|INT.ESP|INTESP|INTOLER", regex=True)
    rows = []
    for s in EST:
        mk = (e[f"dist_{s}"] <= 3.0) & dr
        rows.append({"estadio": s, "BOs_DRADE_disco_3km": int(mk.sum())})
    em = np.zeros(len(e), bool)
    for s in EST:
        em |= (e[f"dist_{s}"] <= 3.0).to_numpy()
    rows.append({"estadio": "3 discos", "BOs_DRADE_disco_3km": int((em & dr).sum()),
                 "BOs_total_disco_3km": int(em.sum())})
    r = pd.DataFrame(rows)
    r.to_csv(tab("crimes", "entorno_drade.csv"), index=False)
    return r


# ---------------------------------------------------------------------------
# 1.4 pico com hora x mes no esperado
# ---------------------------------------------------------------------------
def pico(f, dom):
    res = {}
    for nome, fx in (("com_hm", base_X_hm), ("sem_hm", base_X_sem_hm)):
        out = dirs(dom, "pico_" + nome)
        m.base_X = fx
        R, V, K = m.picos(f, dom, out)
        res[nome] = (R, V, K)
    m.base_X = _BASE_X_ORIG
    return res


# ---------------------------------------------------------------------------
# relatorio e antes x depois
# ---------------------------------------------------------------------------
def br(x, nd=1, sinal=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    s = f"{x:+.{nd}f}" if sinal else f"{x:.{nd}f}"
    return s.replace(".", ",")


MARCA = {"efeito robusto": "‡", "robusto no GLM, pareado inconclusivo": "†", "contradito pelo pareado": "§",
         "sinal não robusto": "*", "sem evidência": ""}


def antes_depois():
    """cada numero do artigo atual (numeros_artigo.csv e tabelas do rp_ii) que tem correspondente novo."""
    A = lambda dom, n: pd.read_csv(os.path.join(REPJ, dom, "tabelas", n))
    N = lambda dom, n: pd.read_csv(tab(dom, n))
    rows = []

    def add(dom, item, antes, depois, nd=1, sinal=True, fonte=""):
        a, b = br(antes, nd, sinal), br(depois, nd, sinal)
        rows.append({"dominio": dom, "item": item, "antes": a, "depois": b, "mudou": a != b, "fonte_nova": fonte})
    for dom in ("crimes", "sinistros"):
        vo, vn = A(dom, "vereditos.csv"), N(dom, "vereditos.csv")
        for _, r in vo.iterrows():
            q = vn[(vn["desfecho"] == r["desfecho"]) & (vn["termo"] == r["termo"])].iloc[0]
            add(dom, f"Tab. 2 {NOMES[r['desfecho']]} {r['janela']} (%)", r["var_pct"], q["var_pct"], fonte="vereditos.csv")
            rows.append({"dominio": dom, "item": f"Tab. 2 {NOMES[r['desfecho']]} {r['janela']} (marca)",
                         "antes": MARCA[r["veredito"]] or "(sem)", "depois": MARCA[q["veredito"]] or "(sem)",
                         "mudou": r["veredito"] != q["veredito"], "fonte_nova": "vereditos.csv"})
            if r["termo"] == "C_pre" or r["p"] < .05 or q["p"] < .05:
                add(dom, f"p_BH {NOMES[r['desfecho']]} {r['janela']}", r["p_BH_dominio"], q["p_BH_dominio"], 3, False, "vereditos.csv")
        co, cn = A(dom, "controles_pareados.csv"), N(dom, "controles_pareados.csv")
        for _, r in co[co["categoria"] == "capital"].iterrows():
            if r["desfecho"] not in (m.DOM[dom]["principal"], "roubos_total"):
                continue
            q = cn[(cn["categoria"] == "capital") & (cn["desfecho"] == r["desfecho"]) & (cn["janela"] == r["janela"])].iloc[0]
            for k in ("DiD_IRR", "IC95_lo", "IC95_hi"):
                add(dom, f"pareado {NOMES[r['desfecho']]} {r['janela']} {k} (%)", 100 * (r[k] - 1), 100 * (q[k] - 1),
                    fonte="controles_pareados.csv")
        po, pn = A(dom, "placebo_permutacao.csv"), N(dom, "placebo_permutacao.csv")
        y0 = m.DOM[dom]["principal"]
        for w in WIN:
            a = po[(po["desfecho"] == y0) & (po["categoria"] == "capital") & (po["janela"] == w)].iloc[0]
            b = pn[(pn["desfecho"] == y0) & (pn["categoria"] == "capital") & (pn["janela"] == w)].iloc[0]
            add(dom, f"placebo p {NOMES[y0]} capital {w}", a["p_permutacao_bilateral"], b["p_permutacao_bilateral"], 3, False,
                "placebo_permutacao.csv")
        eo, en = A(dom, "event_study.csv"), N(dom, "event_study.csv")
        for cat in ("capital", "fora_da_capital"):
            a = eo[(eo["termo"] == "wald_pretendencia_k-6..-3") & (eo["desfecho"] == y0) & (eo["categoria"] == cat)]["p"].iloc[0]
            b = en[(en["termo"] == "wald_pretendencia_k-6..-3") & (en["desfecho"] == y0) & (en["categoria"] == cat)]["p"].iloc[0]
            add(dom, f"pré-tendência p ({cat})", a, b, 3, False, "event_study.csv")
        for k in range(-3, 4):
            a = eo[(eo["desfecho"] == y0) & (eo["categoria"] == "capital") & (eo["k"] == k)]["IRR"].iloc[0]
            b = en[(en["desfecho"] == y0) & (en["categoria"] == "capital") & (en["k"] == k)]["IRR"].iloc[0]
            add(dom, f"event study {NOMES[y0]} capital k={k} (%)", 100 * (a - 1), 100 * (b - 1), fonte="event_study.csv")
        # tercis (artigo: com EF hora x mes, 33b)
        do = A(dom, "fase2b_dose_ef_hora_mes.csv")
        dn = N(dom, "dose_resposta_publico.csv")
        for t in ("C_pre__T1", "C_pre__T2", "C_pre__T3", "C_pos__T3"):
            a = do[(do["desfecho"] == y0) & (do["termo"] == t)]
            b = dn[(dn["desfecho"] == y0) & (dn["termo"] == t)]
            if len(a) and len(b):
                add(dom, f"tercil {t} {NOMES[y0]} (%)", 100 * (a["IRR"].iloc[0] - 1), 100 * (b["IRR"].iloc[0] - 1),
                    fonte="dose_resposta_publico.csv")
        # entorno agregado (artigo: 33b, inverso da variancia) -> empilhado novo
        so, sn = A(dom, "fase2b_espaco_bh.csv"), N(dom, "entorno_modelo_principal.csv")
        so = so[so["estadio"].str.startswith("3 est") & (so["area"] == "disco")]
        for _, r in so.iterrows():
            q = sn[(sn["desfecho"] == r["desfecho"]) & (sn["janela"] == r["janela"]) & sn["estadio"].str.startswith("3")
                   & (sn["spec"] == "janelas")]
            if len(q):
                q = q.iloc[0]
                add(dom, f"entorno 3 estádios {NOMES[r['desfecho']]} {r['janela']} (%)", 100 * (r["IRR"] - 1),
                    100 * (q["IRR"] - 1), 0, True, "entorno_modelo_principal.csv")
                add(dom, f"entorno 3 estádios {NOMES[r['desfecho']]} {r['janela']} p_BH", r["p_BH_agregados"], q["p_BH"],
                    3, False, "entorno_modelo_principal.csv")
        # pico
        for nome, col in (("média", "mean"), ("mín", "min"), ("máx", "max")):
            vo_ = A(dom, "pico_validacao_folds.csv")
            vn_ = pd.read_csv(os.path.join(REV, dom, "pico_com_hm", "tabelas", "pico_validacao_folds.csv"))
            add(dom, f"Tab. 5a prevalência {nome} (1 h, %)", 100 * getattr(vo_[vo_["nivel"] == "hora"]["prev_P90_pearson"], col)(),
                100 * getattr(vn_[vn_["nivel"] == "hora"]["prev_P90_pearson"], col)(), 1, False, "pico_com_hm/pico_validacao_folds.csv")
        ro = A(dom, "pico_por_janela.csv")
        rn = pd.read_csv(os.path.join(REV, dom, "pico_com_hm", "tabelas", "pico_por_janela.csv"))
        for _, r in ro[(ro["nivel"] == "hora") & (ro["definicao"] == "P90_pearson")].iterrows():
            q = rn[(rn["nivel"] == "hora") & (rn["definicao"] == "P90_pearson") & (rn["categoria"] == r["categoria"])
                   & (rn["janela"] == r["janela"])].iloc[0]
            add(dom, f"Tab. 5b RR {r['categoria']} {r['janela']}", r["RR"], q["RR"], 2, False, "pico_com_hm/pico_por_janela.csv")
            add(dom, f"Tab. 5b p Fisher {r['categoria']} {r['janela']}", r["p_fisher"], q["p_fisher"], 3, False,
                "pico_com_hm/pico_por_janela.csv")
        # risco
        to, tn = A(dom, "fase3_tabela_risco_estadio_janela.csv"), N(dom, "entorno_tabela_risco.csv")
        for _, r in to[to["jogo_tipico"] == "quarta 21h30"].iterrows():
            q = tn[(tn["desfecho"] == r["desfecho"]) & (tn["estadio"] == r["estadio"]) & (tn["janela"] == r["janela"])
                   & (tn["jogo_tipico"] == "quarta 21h30")]
            if len(q):
                q = q.iloc[0]
                add(dom, f"Tab. 7 {r['estadio']} {r['janela']} {NOMES[r['desfecho']]} rel (%)", 100 * (r["IRR"] - 1),
                    100 * (q["IRR"] - 1), 0, True, "entorno_tabela_risco.csv")
                add(dom, f"Tab. 7 {r['estadio']} {r['janela']} {NOMES[r['desfecho']]} abs", r["excesso_2h"], q["excesso"],
                    2, True, "entorno_tabela_risco.csv")
    # canal (crimes)
    co, cn = A("crimes", "fase3_canal_modelos.csv"), N("crimes", "entorno_canal.csv")
    mapa = {"original": "todos", "só presencial (sem Delegacia Eletrônica)": "só presencial",
            "só BO online (Delegacia Eletrônica)": "só BO online", "sem conduta nula": "sem conduta nula"}
    for _, r in co[(co["estadio"] == "3 estádios") & co["janela"].isin(["durante", "pos"]) & co["versao"].isin(mapa)].iterrows():
        q = cn[(cn["versao"] == mapa[r["versao"]]) & (cn["desfecho"] == r["desfecho"]) & (cn["janela"] == r["janela"])].iloc[0]
        add("crimes", f"Tab. 4 {NOMES[r['desfecho']]} {r['janela']} {mapa[r['versao']]} (%)", 100 * (r["IRR"] - 1),
            100 * (q["IRR"] - 1), 0, True, "entorno_canal.csv")
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(REV, "antes_depois.csv"), index=False)
    return t


def md(df, ff=3):
    return m.md(df, ff)


def resumo_md(ad):
    L = ["# V4 / Fase 1 — Revisão pelo parecer: resultados novos\n",
         "Gerado por `scripts/36_revisao_parecer.py` (tabelas em `reports/janelas/revisao/{crimes,sinistros}/tabelas/`). "
         "Mudanças aplicadas em tudo: contagem de crime por BO único; horas PRÉ/DURANTE/PÓS dos 5 jogos do Brasil na "
         "Copa de 2022 fora da amostra; modelo principal da cidade com EF hora × mês; entorno como diferença em "
         "diferenças (GLM binomial da fração no disco contra o resto da cidade). Crimes e sinistros separados.\n"]
    fu = pd.read_csv(os.path.join(REV, "funil_registros.csv"))
    L.append("## Funil de registros (BO único; sinistro = registro do Infosiga)\n")
    L.append(md(fu, 1))
    dd = pd.read_csv(tab("crimes", "dedup_bo_unico.csv"))
    L.append("\n### BO × natureza → BO único (contagem horária da cidade)\n")
    L.append(md(dd, 2))
    cp = pd.read_csv(os.path.join(REV, "copa2022_exclusao.csv"))
    L.append("\n### Jogos do Brasil na Copa de 2022 excluídos\n")
    L.append(md(cp, 0))
    for dom in ("crimes", "sinistros"):
        L.append(f"\n---\n\n# {dom.upper()}\n")
        v = pd.read_csv(tab(dom, "vereditos.csv"))
        L.append("## Cidade toda: modelo principal com EF hora × mês (Tabela 2 nova)\n")
        L.append(md(v[["desfecho", "janela", "var_pct", "IC95_lo", "IC95_hi", "p", "p_BH_dominio", "p_placebo",
                       "robustez_NB_e_dia_ok", "pareado_confirma", "pareado_contradiz", "veredito"]], 3))
        if os.path.exists(tab(dom, "entorno_modelo_principal.csv")):
            e = pd.read_csv(tab(dom, "entorno_modelo_principal.csv"))
            ag = e[e["estadio"].str.startswith("3")]
            L.append("\n## Entorno (3 km), diferença em diferenças, 3 estádios empilhados\n")
            L.append("IRR = razão entre a variação no disco e a variação no resto da cidade. `p` = cluster por semana; "
                     "`p_quase` = quase-binomial; `p_dia` = cluster por dia. `dp` = DURANTE+PÓS (janela única de 4 h).\n")
            L.append(md(ag[["desfecho", "janela", "IRR", "IC95_lo", "IC95_hi", "p", "p_BH", "p_quase", "p_dia", "p_placebo",
                            "pareado_confirma", "pareado_contradiz", "veredito"]], 3))
            pe = e[~e["estadio"].str.startswith("3") & (e["p_BH"] < .05)]
            L.append("\nPor estádio com p_BH < 0,05 (família por estádio):\n")
            L.append(md(pe[["estadio", "desfecho", "janela", "IRR", "p", "p_BH", "veredito"]], 3) if len(pe) else "_nenhum_")
            pp = pd.read_csv(tab(dom, "entorno_pareado.csv"))
            L.append("\nPareado do entorno (DiD da fração no disco; IC por bootstrap de jogos):\n")
            L.append(md(pp, 3))
            ra = pd.read_csv(tab(dom, "entorno_raio.csv"))
            ra["cel"] = ra.apply(lambda r: f"{r['IRR']:.2f} (p={r['p']:.3f})", axis=1)
            L.append("\nRaio (só modelo principal, empilhado):\n")
            L.append(m.md(ra.pivot_table(index=["desfecho", "janela"], columns="raio_km", values="cel", aggfunc="first").reset_index()))
        if dom == "crimes" and os.path.exists(tab(dom, "entorno_canal.csv")):
            c = pd.read_csv(tab(dom, "entorno_canal.csv"))
            c["cel"] = c.apply(lambda r: f"{100*(r['IRR']-1):+.0f}%{'*' if r['p_BH_versao'] < .05 else ''}", axis=1)
            L.append("\n## Canal do BO (Tabela 4 nova; * = p_BH < 0,05 dentro da versão)\n")
            L.append(m.md(c.pivot_table(index=["desfecho", "janela"], columns="versao", values="cel", aggfunc="first").reset_index()))
            s = pd.read_csv(tab(dom, "entorno_furtos_subtipos.csv"))
            L.append("\n## Furtos no entorno por subtipo\n")
            L.append(md(s[["desfecho", "janela", "IRR", "IC95_lo", "IC95_hi", "p", "p_BH_subtipos", "n_com_hora_todo_municipio"]], 3))
            sh = pd.read_csv(tab(dom, "entorno_furtos_sem_hora.csv"))
            L.append("\n## Furtos sem hora\n")
            L.append(md(sh, 3))
        if os.path.exists(tab(dom, "entorno_tabela_risco.csv")):
            t = pd.read_csv(tab(dom, "entorno_tabela_risco.csv"))
            L.append("\n## Tabela 7 nova (quarta 21h30)\n")
            L.append(md(t[t["jogo_tipico"] == "quarta 21h30"][["desfecho", "estadio", "janela", "esperado_sem_jogo", "IRR",
                                                                "excesso", "excesso_IC95_lo", "excesso_IC95_hi", "p"]], 2))
        pc = os.path.join(REV, dom, "pico_com_hm", "tabelas", "pico_por_janela.csv")
        if os.path.exists(pc):
            L.append("\n## Pico: esperado com e sem EF hora × mês (nível 1 h, P90 Pearson)\n")
            rows = []
            for nome in ("sem_hm", "com_hm"):
                R = pd.read_csv(os.path.join(REV, dom, f"pico_{nome}", "tabelas", "pico_por_janela.csv"))
                V = pd.read_csv(os.path.join(REV, dom, f"pico_{nome}", "tabelas", "pico_validacao_folds.csv"))
                R = R[(R["nivel"] == "hora") & (R["definicao"] == "P90_pearson")].copy()
                R["p_BH_6janelas"] = m.bh(R["p_fisher"])
                vv = V[V["nivel"] == "hora"]["prev_P90_pearson"]
                for _, r in R.iterrows():
                    rows.append({"esperado": nome, "categoria": r["categoria"], "janela": r["janela"], "RR": r["RR"],
                                 "p_fisher": r["p_fisher"], "p_BH_6janelas": r["p_BH_6janelas"],
                                 "prev_teste_media": 100 * vv.mean(), "prev_min": 100 * vv.min(), "prev_max": 100 * vv.max()})
            L.append(md(pd.DataFrame(rows), 3))
    L.append("\n---\n\n# Antes × depois (números do artigo atual que mudaram)\n")
    for dom in ("crimes", "sinistros"):
        a = ad[(ad["dominio"] == dom) & ad["mudou"]]
        L.append(f"\n## {dom.upper()} ({len(a)} de {int((ad['dominio'] == dom).sum())} números conferidos mudaram)\n")
        L.append(m.md(a[["item", "antes", "depois", "fonte_nova"]]))
    with open(os.path.join(REV, "resumo_revisao.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    t0 = time.time()
    etapas = os.environ.get("ETAPAS", "cidade,entorno,pico,resumo").split(",")
    doms = os.environ.get("DOMS", "crimes,sinistros").split(",")
    f, jogos, fora, evc, evs = carrega()
    print("dados", round(time.time() - t0), flush=True)
    funil(evc, evs)
    medias_horarias(f)
    if "drade" in etapas or "entorno" in etapas:
        print(drade(evc).to_string(), flush=True)
    for dom in doms:
        print("==", dom, flush=True)
        if "cidade" in etapas:
            cidade(f, jogos, fora, dom)
            print("  cidade", round(time.time() - t0), flush=True)
        if "entorno" in etapas:
            entorno(f, jogos, evc if dom == "crimes" else evs, dom)
            print("  entorno", round(time.time() - t0), flush=True)
        if "entorno" in etapas or "sem_hm" in etapas:
            entorno_sem_hm(f, evc if dom == "crimes" else evs, dom)
            print("  entorno sem hora x mes", round(time.time() - t0), flush=True)
        if "pico" in etapas:
            pico(f, dom)
            print("  pico", round(time.time() - t0), flush=True)
    if "resumo" in etapas:
        resumo_md(antes_depois())
    print("[ok]", round(time.time() - t0), "s")
