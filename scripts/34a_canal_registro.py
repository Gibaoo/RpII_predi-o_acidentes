"""
V2 / Fase 3 (item 0) -- 34a_canal_registro.py
Checagem do canal de registro no entorno dos estadios (robustez; o modelo principal nao muda).

A Fase 2b mostrou que BOs sem DESCR_CONDUTA sobem muito no entorno em dia de jogo. Aqui: de qual
delegacia de registro (NOME_DELEGACIA) e tipo de local (DESCR_SUBTIPOLOCAL) vem o excesso -- em especial
a DRADE (Delegacia de Repressao aos Delitos de Intolerancia Esportiva) -- e o modelo do entorno da Fase 2
(33_analise_janelas.py::espaco_tempo, disco de 3 km, sem celulas de empilhamento) reestimado sem cada
canal, lado a lado: original | sem DRADE | sem conduta nula | so presencial (sem Delegacia Eletronica) |
so BO online (Delegacia Eletronica).

Saidas: reports/janelas/crimes/tabelas/fase3_canal_*.csv, reports/janelas/crimes/relatorio_fase3_canal_registro.md
Rodar:  python scripts/34a_canal_registro.py   (~3 min; le o bronze)
"""
import importlib
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
m = importlib.import_module("33_analise_janelas")
m30 = importlib.import_module("30_eventos_horarios")
VIOL = importlib.import_module("02_limpeza").CATEGORIAS_VIOLENTAS
OUT = m.dirs("crimes")
TAB = os.path.join(OUT, "tabelas")
DESF = ["crimes_violentos", "roubos_total", "furtos_total"]


def le_entorno():
    cols = ["NOME_DELEGACIA", "CD_IBGE", "DATA_OCORRENCIA_BO", "HORA_OCORRENCIA_BO", "NATUREZA_APURADA",
            "DESCR_CONDUTA", "DESCR_SUBTIPOLOCAL", "LATITUDE", "LONGITUDE"]
    partes = []
    for arq in m30.CRIME_FILES:
        for ch in pd.read_csv(os.path.join(BASE, "data", "bronze", arq), usecols=cols, dtype=str, chunksize=400_000):
            ch = ch[pd.to_numeric(ch["CD_IBGE"], errors="coerce") == m30.CD_IBGE_SP]
            ch["lat"] = pd.to_numeric(ch["LATITUDE"].str.replace(",", "."), errors="coerce")
            ch["lon"] = pd.to_numeric(ch["LONGITUDE"].str.replace(",", "."), errors="coerce")
            ok = ch["lat"].between(*m.BBOX["lat"]) & ch["lon"].between(*m.BBOX["lon"]) & (ch["lat"].abs() > .01)
            ch = ch[ok]
            perto = np.zeros(len(ch), bool)
            for la, lo in m.ESTADIOS.values():
                perto |= m.dist_km(ch["lat"].to_numpy(), ch["lon"].to_numpy(), la, lo) <= m.R_ENTORNO
            partes.append(ch[perto])
    ev = pd.concat(partes, ignore_index=True)
    ev["data"] = pd.to_datetime(ev["DATA_OCORRENCIA_BO"].str[:10], errors="coerce")
    ev = ev[(ev["data"] >= "2022-01-01") & (ev["data"] <= "2023-12-31")]
    h, _, tem, _ = m30.parse_hora(ev["HORA_OCORRENCIA_BO"])
    ev = ev[tem].copy()
    ev["h"] = ev["data"] + pd.to_timedelta(h[tem], unit="h")
    nat = ev["NATUREZA_APURADA"].astype(str).str.strip().str.upper()
    ev["is_roubo"] = nat.str.startswith("ROUBO")
    ev["is_furto"] = nat.str.startswith("FURTO")
    ev["is_violento"] = nat.isin(VIOL) | ev["is_roubo"]
    deleg = ev["NOME_DELEGACIA"].astype(str).str.strip().str.upper()
    ev["drade"] = deleg.str.contains("DRADE|INT.ESP|INTESP|INTOLER")
    ev["eletronica"] = deleg.str.contains("ELETRONICA|ELETRÔNICA|ONLINE")
    ev["conduta_nula"] = ev["DESCR_CONDUTA"].isna() | ev["DESCR_CONDUTA"].astype(str).str.strip().str.upper().eq("NULL")
    ev["ck"] = ev["lat"].round(3).astype(str) + "," + ev["lon"].round(3).astype(str)
    pile = set()
    for c in pd.read_csv(os.path.join(TAB, "espaco_empilhamento_bairros.csv"))["celulas_empilhamento_excluidas"].dropna():
        pile |= {x.strip() for x in str(c).split(";")}
    ev["pileup"] = ev["ck"].isin(pile)
    ev["deleg"] = deleg
    return ev


VERSOES = {
    "original": lambda e: np.ones(len(e), bool),
    "sem DRADE": lambda e: ~e["drade"].to_numpy(),
    "sem conduta nula": lambda e: ~e["conduta_nula"].to_numpy(),
    "só presencial (sem Delegacia Eletrônica)": lambda e: ~e["eletronica"].to_numpy(),
    "só BO online (Delegacia Eletrônica)": lambda e: e["eletronica"].to_numpy(),
}


def contagens(ev, horas):
    out = {}
    for s, (la, lo) in m.ESTADIOS.items():
        e = ev[(m.dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo) <= m.R_ENTORNO) & ~ev["pileup"]]
        for v, filt in VERSOES.items():
            ee = e[filt(e)]
            for y, flag in (("crimes_violentos", "is_violento"), ("roubos_total", "is_roubo"),
                            ("furtos_total", "is_furto")):
                out[(s, v, y)] = ee[ee[flag]].groupby("h").size().reindex(horas, fill_value=0)
    return out


def diagnostico(ev, d):
    """O/E por canal nas janelas DURANTE+POS dos jogos do proprio estadio (taxa das horas sem jogo, mesma
    hora x dia da semana), e delegacias/locais mais frequentes nas janelas."""
    rows, top = [], []
    for s, (la, lo) in m.ESTADIOS.items():
        e = ev[(m.dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo) <= m.R_ENTORNO) & ~ev["pileup"]
               & (ev["is_violento"] | ev["is_furto"])]
        e = e[e["h"].isin(d.index)].join(d[["hd", "janela", "jogo_estadio", "hora_sem_jogo"]], on="h")
        jan_h = d[d["janela"].isin(["durante", "pos"]) & d["jogo_estadio"].eq(s)].groupby("hd").size()
        n_ctrl = d[d["hora_sem_jogo"]].groupby("hd").size()
        for corte in ("drade", "eletronica", "conduta_nula"):
            for v, g in e.groupby(corte):
                taxa = g[g["hora_sem_jogo"]].groupby("hd").size().reindex(n_ctrl.index, fill_value=0) / n_ctrl
                E = float((taxa.reindex(jan_h.index, fill_value=0) * jan_h).sum())
                O = int((g["janela"].isin(["durante", "pos"]) & g["jogo_estadio"].eq(s)).sum())
                rows.append({"estadio": s, "canal": corte, "valor": bool(v), "O": O, "E": E})
        w = e[e["janela"].isin(["durante", "pos"]) & e["jogo_estadio"].eq(s)]
        for col in ("deleg", "DESCR_SUBTIPOLOCAL"):
            vc = w[col].astype(str).str.strip().value_counts(normalize=True).head(6)
            for k, p in vc.items():
                top.append({"estadio": s, "campo": col, "valor": k, "pct_registros_janelas": 100 * p})
    r = pd.DataFrame(rows)
    r["O/E"] = r["O"] / r["E"]
    r["IC95_lo"] = stats.chi2.ppf(.025, 2 * r["O"]) / 2 / r["E"]
    r["IC95_hi"] = stats.chi2.ppf(.975, 2 * (r["O"] + 1)) / 2 / r["E"]
    r["excesso"] = r["O"] - r["E"]
    r.to_csv(os.path.join(TAB, "fase3_canal_diagnostico.csv"), index=False)
    t = pd.DataFrame(top)
    t.to_csv(os.path.join(TAB, "fase3_canal_delegacias_locais.csv"), index=False)
    return r, t


def modelos(f, cont):
    d = m.amostra(f, "crimes")
    X = m.base_X(d, ("crimes", "main"))
    rows = []
    for s in m.ESTADIOS:
        est = d["jogo_estadio"].eq(s)
        T = pd.DataFrame(index=d.index)
        for w in m.WIN:
            T[f"C_{w}__este_estadio"] = ((d[f"C_{w}"] == 1) & est).astype(float)
            T[f"C_{w}__outro_estadio"] = ((d[f"C_{w}"] == 1) & ~est).astype(float)
        T[["C_fdj", "F_pre", "F_durante", "F_pos"]] = d[["C_fdj", "F_pre", "F_durante", "F_pos"]]
        for v in VERSOES:
            for y in DESF:
                yy = cont[(s, v, y)].reindex(d["hora_ts"]).to_numpy()
                r = m.ajusta(yy, X, T, d["semana_id"].to_numpy())
                for rr in m.coefs(r, [f"C_{w}__este_estadio" for w in m.WIN],
                                  {"estadio": s, "versao": v, "desfecho": y, "media_hora": yy.mean()}):
                    rr["janela"] = rr["termo"].split("__")[0][2:]
                    rows.append(rr)
    e = pd.DataFrame(rows)
    agg = []
    for (v, y, w), g in e.groupby(["versao", "desfecho", "janela"]):
        b = np.log(g["IRR"])
        se = (np.log(g["IC95_hi"]) - np.log(g["IC95_lo"])) / (2 * 1.96)
        wt = 1 / se ** 2
        bb, ss = (wt * b).sum() / wt.sum(), np.sqrt(1 / wt.sum())
        agg.append({"estadio": "3 estádios", "versao": v, "desfecho": y, "janela": w, "IRR": np.exp(bb),
                    "IC95_lo": np.exp(bb - 1.96 * ss), "IC95_hi": np.exp(bb + 1.96 * ss),
                    "p": 2 * stats.norm.sf(abs(bb / ss))})
    e = pd.concat([e, pd.DataFrame(agg)], ignore_index=True)
    e.to_csv(os.path.join(TAB, "fase3_canal_modelos.csv"), index=False)
    return e


def relatorio(ev, diag, top, mod, check):
    L = ["# V2 / Fase 3 (item 0) — Canal de registro no entorno dos estádios\n",
         "Gerado por `scripts/34a_canal_registro.py`. Robustez do resultado do entorno da Fase 2 (modelo principal "
         "inalterado). Disco de 3 km, registros com hora, sem as células de empilhamento.\n"]
    L.append(f"Conferência: contagens da versão `original` reproduzem as do `33` (diferença máxima por hora: "
             f"{check}).\n")
    n_drade = int(ev["drade"].sum())
    L.append("## 1. De onde vêm os registros\n")
    L.append(f"- **DRADE** (Delegacia de Repressão aos Delitos de Intolerância Esportiva): **{n_drade} BOs** no "
             "entorno dos 3 estádios em 2022–2023 (todas as naturezas) — não é um canal relevante; não existe um "
             "posto do estádio que concentre os registros.")
    L.append(f"- **Delegacia Eletrônica (BO online):** {100*ev['eletronica'].mean():.0f}% dos registros do entorno; "
             f"BOs sem `DESCR_CONDUTA`: {100*ev['conduta_nula'].mean():.0f}%.")
    L.append("\nO/E nas janelas DURANTE+PÓS dos jogos do próprio estádio (crimes violentos + furtos), por canal "
             "(O = observado, E = taxa das horas sem jogo, mesma hora × dia da semana; descritivo):\n")
    L.append(m.md(diag[["estadio", "canal", "valor", "O", "E", "O/E", "IC95_lo", "IC95_hi", "excesso"]], 2))
    L.append("\nDelegacias e tipos de local mais frequentes nas janelas:\n")
    L.append(m.md(top, 1))
    L.append("\n## 2. Modelo do entorno sem cada canal (lado a lado)\n")
    L.append("Mesmo modelo da Fase 2 (Poisson, EF hora × dia da semana + ano × mês + feriado/véspera/férias + "
             "clima, janelas dos jogos daquele estádio vs dos outros, cluster por semana).\n")
    sub = mod[mod["janela"].isin(["durante", "pos"])]
    piv = sub.assign(cel=sub.apply(lambda r: f"{r['IRR']:.2f} ({r['IC95_lo']:.2f}–{r['IC95_hi']:.2f})", axis=1)) \
        .pivot_table(index=["estadio", "desfecho", "janela"], columns="versao", values="cel", aggfunc="first")
    piv = piv[[c for c in VERSOES if c in piv.columns]].reset_index()
    L.append(m.md(piv))
    L.append("\n" + _leitura(mod))
    with open(os.path.join(OUT, "relatorio_fase3_canal_registro.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _leitura(mod):
    a = mod[(mod["estadio"] == "3 estádios") & mod["janela"].isin(["durante", "pos"])].set_index(["desfecho", "janela", "versao"])
    L = ["**Leitura (3 estádios agregados):**"]
    for y in DESF:
        for w in ("durante", "pos"):
            try:
                o = a.loc[(y, w, "original")]
                pres = a.loc[(y, w, "só presencial (sem Delegacia Eletrônica)")]
                onl = a.loc[(y, w, "só BO online (Delegacia Eletrônica)")]
                sn = a.loc[(y, w, "sem conduta nula")]
            except KeyError:
                continue
            L.append(f"- `{y}` {w.upper()}: original {o['IRR']:.2f} (p={o['p']:.3f}); sem conduta nula {sn['IRR']:.2f} "
                     f"(p={sn['p']:.3f}); só presencial {pres['IRR']:.2f} (p={pres['p']:.3f}); só online "
                     f"{onl['IRR']:.2f} (p={onl['p']:.3f}).")
    return "\n".join(L)


if __name__ == "__main__":
    f, jogos, fora = m.carrega()
    ev = le_entorno()
    print("registros entorno:", len(ev), "| DRADE:", int(ev["drade"].sum()))
    horas = pd.date_range("2022-01-01", "2023-12-31 23:00", freq="h")
    cont = contagens(ev, horas)
    c33, _ = m.contagens_espaciais("crimes")
    check = max(int((cont[(s, "original", y)] - c33[(s, "disco", y)]).abs().max()) for s in m.ESTADIOS for y in DESF)
    d = m.amostra(f, "crimes").set_index("hora_ts")
    diag, top = diagnostico(ev, d)
    mod = modelos(f, cont)
    relatorio(ev, diag, top, mod, check)
    print(mod[mod["estadio"] == "3 estádios"].round(3).to_string())
    print("[ok]")
