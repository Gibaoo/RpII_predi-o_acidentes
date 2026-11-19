"""
V2 / Fase 2b -- 33b_robustez_janelas.py
Rodada curta de checagens pedida depois da Fase 2, SEM mudar o modelo principal (33_analise_janelas.py),
so acrescentando robustezes. Crimes e sinistros sempre separados (familias de BH por dominio).

1. PRE da capital (GLM "robusto", pareado nao confirma, pre-tendencia):
   a. GLM principal + EF hora do dia x mes (e, alternativa, hora x trimestre), alem de hora x dia da semana:
      controla a mudanca do perfil horario ao longo do ano (por do sol), que o pareado controla por
      construcao (semanas proximas) e o GLM principal nao.
   b. GLM principal so com os jogos do desenho pareado (separa diferenca de estimador de diferenca de amostra).
   c. Dose-resposta do publico com o controle do item a.
   d. PRE estendido (k = -3 a -1).
   e. Regra do veredito revista (implementada em 33_analise_janelas.py::conclusao).
2. Entorno dos estadios: (a) BH na familia espacial; (b) tabela por estadio x tipo, com o resto da cidade
   na mesma janela e nos jogos do mesmo estadio; (c) furtos/roubos do entorno por DESCR_CONDUTA (bronze);
   (d) leituras alternativas nao testaveis (no relatorio).
3. Exploratorios com p_BH: horas tardias do event study e PRE de sinistros no entorno.

Saidas: reports/janelas/{crimes,sinistros}/relatorio_fase2b_<dom>.md + tabelas/fase2b_*.csv,
        reports/janelas/resumo_fase2b.md
Rodar (depois do 33):  python scripts/33b_robustez_janelas.py      (~10 min)
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
BRONZE = os.path.join(BASE, "data", "bronze")
REP = m.REP
WIN = m.WIN
TP = m.T_PRINC


def tab(out, nome):
    return os.path.join(out, "tabelas", nome)


# ---------------------------------------------------------------------------
# 1. PRE da capital
# ---------------------------------------------------------------------------
def checagens_pre(f, jogos, fora, dom, out):
    d = m.amostra(f, dom)
    X0 = m.base_X(d, (dom, "main"))
    Xhm = m._interacoes_hora(X0, d, "hm")
    Xht = m._interacoes_hora(X0, d, "htri")
    g = d["semana_id"].to_numpy()
    rows = []
    # (a) EF hora x mes / hora x trimestre
    for y in m.DOM[dom]["desfechos"]:
        for nome, X in (("principal", X0), ("+ EF hora×mês", Xhm), ("+ EF hora×trimestre", Xht)):
            r = m.ajusta(d[y], X, d[TP], g)
            rows += m.coefs(r, TP, {"desfecho": y, "spec": nome, "item": "1a"})
    # (d) PRE estendido k=-3..-1
    T = d[TP].copy()
    ext = d["hora_relativa"].isin([-3, -2, -1]) & d["jogo_id"].notna()
    T["C_pre_ext"] = ext.astype(float)
    T["C_fdj"] = ((d["C_fdj"] == 1) & ~ext).astype(float)
    T = T.drop(columns=["C_pre"])
    for y in m.DOM[dom]["desfechos"]:
        for nome, X in (("PRÉ estendido (k=−3..−1)", X0), ("PRÉ estendido + EF hora×mês", Xhm)):
            r = m.ajusta(d[y], X, T, g)
            rows += m.coefs(r, ["C_pre_ext", "C_durante", "C_pos"], {"desfecho": y, "spec": nome, "item": "1d"})
    # (b) so os jogos do desenho pareado
    pj = pd.read_csv(tab(out, "controles_pareados_jogos.csv"), parse_dates=["dia"])
    dias = set(pj.loc[pj["categoria"] == "capital", "dia"])
    ids = set(jogos.loc[jogos["data_br"].dt.normalize().isin(dias), "jogo_id"])
    fora_do_par = (d["janela"].isin(WIN) & ~d["jogo_id"].isin(ids)) | \
        (d["dia_de_jogo"] & ~d["jogo_id_do_dia"].fillna("").isin(ids))
    ds = d[~fora_do_par]
    gs = ds["semana_id"].to_numpy()
    for y in m.DOM[dom]["desfechos"]:
        for nome, ex in (("só jogos do pareado", ()), ("só jogos do pareado + EF hora×mês", ("hm",))):
            r = m.ajusta(ds[y], m.d_override_X(ds, list(ex)), ds[TP], gs)
            rows += m.coefs(r, TP, {"desfecho": y, "spec": nome, "item": "1b", "n_jogos_capital": len(ids)})
    res = pd.DataFrame(rows)
    res["janela"] = res["termo"].map({**m.ROTULO, "C_pre_ext": "capital PRÉ estendido (k=−3..−1)"})
    res.to_csv(tab(out, "fase2b_pre_checagens.csv"), index=False)
    # (c) dose-resposta com EF hora x mes
    dose = m.dose_publico(f, jogos, dom, out, d_override=d, rotulo="cidade toda + EF hora×mês", extra_fe=["hm"])
    dose.to_csv(tab(out, "fase2b_dose_ef_hora_mes.csv"), index=False)
    return res, dose, len(ids)


# ---------------------------------------------------------------------------
# 2. entorno dos estadios
# ---------------------------------------------------------------------------
def bh_espacial(out):
    sp = pd.read_csv(tab(out, "espaco_tempo.csv"))
    est = sp["estadio"].isin(m.ESTADIOS)
    agg = sp["estadio"].str.startswith("3 est")
    sp.loc[est, "p_BH_familia_espacial"] = m.bh(sp.loc[est, "p"])     # estadios x janelas x desfechos x area
    sp.loc[agg, "p_BH_agregados"] = m.bh(sp.loc[agg, "p"])            # 3 estadios agregados
    sp.to_csv(tab(out, "fase2b_espaco_bh.csv"), index=False)
    return sp


def deslocamento(f, jogos, dom, out, sp):
    """Resto da cidade com as janelas separadas por estadio do jogo -> lado a lado com o entorno."""
    cont, _ = m.contagens_espaciais(dom)
    d = m.amostra(f, dom)
    X = m.base_X(d, (dom, "main"))
    T = pd.DataFrame(index=d.index)
    for w in WIN:
        for s in m.ESTADIOS:
            T[f"C_{w}__{s}"] = ((d[f"C_{w}"] == 1) & d["jogo_estadio"].eq(s)).astype(float)
        T[f"C_{w}__outro"] = ((d[f"C_{w}"] == 1) & ~d["jogo_estadio"].isin(m.ESTADIOS)).astype(float)
    T[["C_fdj", "F_pre", "F_durante", "F_pos"]] = d[["C_fdj", "F_pre", "F_durante", "F_pos"]]
    rows = []
    for y in m.DOM[dom]["desfechos"]:
        yy = cont[("resto", "resto", y)].reindex(d["hora_ts"]).to_numpy()
        r = m.ajusta(yy, X, T, d["semana_id"].to_numpy())
        for w in WIN:
            for s in m.ESTADIOS:
                c = f"C_{w}__{s}"
                rows.append({"desfecho": y, "estadio": s, "janela": w, "IRR_resto": np.exp(r.params[c]),
                             "p_resto": r.pvalues[c]})
    rs = pd.DataFrame(rows)
    e = sp[sp["estadio"].isin(m.ESTADIOS)]
    piv = e.pivot_table(index=["desfecho", "estadio", "janela"], columns="area",
                        values=["IRR", "p", "p_BH_familia_espacial"], aggfunc="first")
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    t = piv.reset_index().merge(rs, on=["desfecho", "estadio", "janela"], how="left")
    t["janela"] = pd.Categorical(t["janela"], WIN)
    t = t.sort_values(["desfecho", "estadio", "janela"])
    t.to_csv(tab(out, "fase2b_deslocamento_entorno_vs_cidade.csv"), index=False)
    return t


def conduta_entorno(f, out):
    """Furtos e roubos com hora no disco de 3 km de cada estadio (sem as celulas de empilhamento), por
    DESCR_CONDUTA (bronze). Observado nas janelas dos jogos daquele estadio vs esperado pela taxa das horas
    sem jogo no mesmo estadio, mesma hora do dia x dia da semana. DESCRITIVO/exploratorio (sem EF de mes)."""
    m30 = importlib.import_module("30_eventos_horarios")
    cols = ["CD_IBGE", "DATA_OCORRENCIA_BO", "HORA_OCORRENCIA_BO", "NATUREZA_APURADA", "DESCR_CONDUTA",
            "LATITUDE", "LONGITUDE"]
    partes = []
    for arq in m30.CRIME_FILES:
        for ch in pd.read_csv(os.path.join(BRONZE, arq), usecols=cols, dtype=str, chunksize=400_000):
            ch = ch[pd.to_numeric(ch["CD_IBGE"], errors="coerce") == m30.CD_IBGE_SP]
            nat = ch["NATUREZA_APURADA"].astype(str).str.strip().str.upper()
            ch = ch[nat.str.startswith("ROUBO") | nat.str.startswith("FURTO")].copy()
            ch["nat"] = np.where(nat[ch.index].str.startswith("ROUBO"), "roubo", "furto")
            ch["lat"] = pd.to_numeric(ch["LATITUDE"].str.replace(",", "."), errors="coerce")
            ch["lon"] = pd.to_numeric(ch["LONGITUDE"].str.replace(",", "."), errors="coerce")
            ok = ch["lat"].between(*m.BBOX["lat"]) & ch["lon"].between(*m.BBOX["lon"]) & (ch["lat"].abs() > .01)
            ch = ch[ok]
            perto = np.zeros(len(ch), bool)
            for la, lo in m.ESTADIOS.values():
                perto |= m.dist_km(ch["lat"].to_numpy(), ch["lon"].to_numpy(), la, lo) <= m.R_ENTORNO
            partes.append(ch[perto])
    ev = pd.concat(partes, ignore_index=True)
    h, mi, tem, _ = m30.parse_hora(ev["HORA_OCORRENCIA_BO"])
    ev = ev[tem].copy()
    ev["h"] = pd.to_datetime(ev["DATA_OCORRENCIA_BO"].str[:10], errors="coerce") + pd.to_timedelta(h[tem], unit="h")
    ev["ck"] = ev["lat"].round(3).astype(str) + "," + ev["lon"].round(3).astype(str)
    pile = set()
    diag = pd.read_csv(tab(out, "espaco_empilhamento_bairros.csv"))
    for c in diag["celulas_empilhamento_excluidas"].dropna():
        pile |= {x.strip() for x in str(c).split(";")}
    ev = ev[~ev["ck"].isin(pile)]
    import unicodedata
    sem_acento = lambda x: "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    ev["conduta"] = ev["DESCR_CONDUTA"].fillna("(nulo)").astype(str).str.strip().str.upper()         .replace("NULL", "(nulo)").map(sem_acento)          # a fonte grafa VEICULO e VEICULO com acento
    top = ev["conduta"].value_counts().head(7).index
    ev["conduta"] = np.where(ev["conduta"].isin(top), ev["conduta"], "DEMAIS (agrupadas)")
    d = m.amostra(f, "crimes").set_index("hora_ts")
    rows = []
    for s, (la, lo) in m.ESTADIOS.items():
        es_ = ev[m.dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo) <= m.R_ENTORNO]
        es_ = es_[es_["h"].isin(d.index)]
        es_ = es_.join(d[["hd", "janela", "jogo_estadio", "hora_sem_jogo"]], on="h")
        ctrl_h = d[d["hora_sem_jogo"]]
        n_ctrl = ctrl_h.groupby("hd").size()
        for grupo, wins in (("PRÉ", ["pre"]), ("DURANTE+PÓS", ["durante", "pos"])):
            jan_h = d[d["janela"].isin(wins) & d["jogo_estadio"].eq(s)]
            hd_cnt = jan_h.groupby("hd").size()
            for (nat, cond), gg in es_.groupby(["nat", "conduta"]):
                taxa = gg[gg["hora_sem_jogo"]].groupby("hd").size().reindex(n_ctrl.index, fill_value=0) / n_ctrl
                E = float((taxa.reindex(hd_cnt.index, fill_value=0) * hd_cnt).sum())
                O = int((gg["janela"].isin(wins) & gg["jogo_estadio"].eq(s)).sum())
                rows.append({"estadio": s, "janela": grupo, "natureza": nat, "conduta": cond, "O": O, "E": E})
    r = pd.DataFrame(rows)
    a = r.groupby(["janela", "natureza", "conduta"])[["O", "E"]].sum().reset_index()
    a["O/E"] = a["O"] / a["E"]
    a["IC95_lo"] = stats.chi2.ppf(.025, 2 * a["O"]) / 2 / a["E"]
    a["IC95_hi"] = stats.chi2.ppf(.975, 2 * (a["O"] + 1)) / 2 / a["E"]
    a["excesso"] = a["O"] - a["E"]
    tot = a.groupby(["janela", "natureza"])["excesso"].transform(lambda x: x.clip(lower=0).sum())
    a["parcela_do_excesso_positivo"] = np.where(a["excesso"] > 0, a["excesso"] / tot, 0)
    a.to_csv(tab(out, "fase2b_conduta_entorno.csv"), index=False)
    return a


# ---------------------------------------------------------------------------
# 3. exploratorios
# ---------------------------------------------------------------------------
def exploratorios(out, dom, sp):
    es = pd.read_csv(tab(out, "event_study.csv"))
    mk = es["k"].notna()
    es.loc[mk, "p_BH_familia_event_study"] = m.bh(es.loc[mk, "p"])
    es.to_csv(tab(out, "fase2b_event_study_bh.csv"), index=False)
    tard = es[es["k"].between(4, 12) & (es["p"] < .05)][["desfecho", "categoria", "k", "IRR", "p",
                                                         "p_BH_familia_event_study"]]
    ent = sp[sp["estadio"].str.startswith("3 est") & (sp["janela"] == "pre")][
        ["desfecho", "area", "IRR", "p", "p_BH_agregados"]]
    return tard, ent


# ---------------------------------------------------------------------------
# relatorio
# ---------------------------------------------------------------------------
def pct(x):
    return f"{100*(x-1):+.1f}%"


def relatorio(dom, out, pre, dose, n_par, sp, desl, cond, tard, ent):
    L = []
    w = L.append
    nome = "CRIMES" if dom == "crimes" else "SINISTROS"
    alvo = ["crimes_violentos", "roubos_total"] if dom == "crimes" else ["acidentes_com_vitima"]
    w(f"# V2 / Fase 2b — {nome}: checagens de robustez\n")
    w("Gerado por `scripts/33b_robustez_janelas.py`. **O modelo principal da Fase 2 não muda**; aqui só se "
      "acrescentam robustezes. Domínio analisado isoladamente.\n")

    w("## 1. PRÉ da capital\n")
    a = pre[(pre["termo"].isin(["C_pre", "C_pre_ext"])) & pre["desfecho"].isin(alvo)]
    w("### 1a/1b/1d. GLM com EF hora × mês, só com os jogos do pareado e PRÉ estendido\n")
    w("O pareado compara cada jogo com semanas próximas e por isso controla a mudança do perfil horário ao "
      "longo do ano (o pôr do sol muda mais de 1 h em SP; roubo é sensível à escuridão); o GLM principal só "
      "tinha hora × dia da semana + ano × mês. **1a** acrescenta EF hora do dia × mês (alternativa: × "
      f"trimestre). **1b** reestima o GLM só com os {n_par} jogos que entraram no desenho pareado (as janelas e "
      "dias dos outros jogos da capital saem da amostra). **1d** PRÉ estendido = horas k = −3, −2, −1.\n")
    w(m.md(a[["desfecho", "spec", "janela", "IRR", "var_pct", "IC95_lo", "IC95_hi", "p"]], 3))
    full = pre[pre["desfecho"].isin(m.DOM[dom]["desfechos"]) & pre["item"].eq("1a")]
    piv = full.assign(cel=full.apply(lambda r: f"{r['IRR']:.3f} (p={r['p']:.3f})", axis=1)).pivot_table(
        index=["desfecho", "termo"], columns="spec", values="cel", aggfunc="first").reset_index()
    w("\nTodos os termos e desfechos, principal vs EF hora × mês / × trimestre:\n")
    w(m.md(piv))
    w("\n" + _leitura_pre(dom, pre, alvo, n_par))
    w("\n### 1c. Dose-resposta do público com EF hora × mês (cidade toda)\n")
    dd = dose[dose["desfecho"].isin(alvo)][["desfecho", "spec", "termo", "IRR", "IC95_lo", "IC95_hi", "p"]]
    w(m.md(dd, 3))
    w("\n### 1e. Regra do veredito revista\n")
    w("Implementada em `33_analise_janelas.py` (vereditos da Fase 2 regenerados): entre os candidatos (p_BH < "
      "0,05, placebo p < 0,05, NB e cluster por dia com o mesmo sinal), **efeito robusto** só se o pareado "
      "**confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, pareado inconclusivo** se o pareado não "
      "confirma mas não contradiz (IC95 do pareado contém a estimativa do GLM); **contradito pelo pareado** se o "
      "IC95 do pareado exclui a estimativa do GLM. Assim, nenhum efeito é chamado de robusto com o pareado "
      "contra.\n")
    v = pd.read_csv(tab(out, "vereditos.csv"))
    w(m.md(v[v["veredito"] != "sem evidência"][["desfecho", "janela", "var_pct", "p_BH_dominio", "p_placebo",
                                                 "pareado_confirma", "pareado_contradiz", "veredito"]], 3)
      if (v["veredito"] != "sem evidência").any() else "_Nenhum termo com p < 0,05 no domínio._")

    w("\n## 2. Entorno dos estádios\n")
    w("### 2a. BH na família espacial\n")
    nfam = int(sp["p_BH_familia_espacial"].notna().sum())
    w(f"Família = estádios × janelas × desfechos × (disco{'/bairros' if dom == 'crimes' else ''}) = {nfam} "
      "testes; os 3 estádios agregados formam uma família à parte.\n")
    ag = sp[sp["estadio"].str.startswith("3 est")][["desfecho", "area", "janela", "IRR", "IC95_lo", "IC95_hi",
                                                    "p", "p_BH_agregados"]]
    w(m.md(ag, 3))
    sig = sp[sp["p_BH_familia_espacial"] < .05][["estadio", "area", "desfecho", "janela", "IRR", "p",
                                                  "p_BH_familia_espacial"]]
    w("\nTermos por estádio que sobrevivem ao BH da família espacial:\n")
    w(m.md(sig, 3) if len(sig) else "_nenhum_")
    w("\n### 2b. Por estádio e tipo, com o resto da cidade na mesma janela\n")
    w("`IRR_resto` = resto da cidade (fora dos 3 discos) nas janelas **dos jogos daquele estádio**, mesmo "
      "modelo. Deslocamento = entorno sobe enquanto o resto da cidade fica igual ou cai.\n")
    cols = [c for c in ["desfecho", "estadio", "janela", "IRR_disco", "p_disco", "p_BH_familia_espacial_disco",
                        "IRR_bairros", "p_bairros", "IRR_resto", "p_resto"] if c in desl.columns]
    w(m.md(desl[cols], 3))
    w("\n" + _leitura_desl(desl))
    if cond is not None:
        w("\n### 2c. Furtos e roubos do entorno por DESCR_CONDUTA (exploratório)\n")
        w("Registros com hora no disco de 3 km (sem células de empilhamento). O = observado nas janelas dos "
          "jogos do próprio estádio; E = taxa das horas sem jogo no mesmo estádio, mesma hora × dia da semana. "
          "Descritivo (sem EF de mês nem de clima): serve para ver **que tipo** de ocorrência sobe, não para "
          "medir o tamanho do efeito.\n")
        w(m.md(cond[["janela", "natureza", "conduta", "O", "E", "O/E", "IC95_lo", "IC95_hi",
                     "parcela_do_excesso_positivo"]], 2))
        w("\n" + _leitura_conduta(cond))
    w("\n### 2d. Leituras alternativas que não dá para testar com estes dados\n")
    w("- **Mais policiamento → mais registro.** Em dia de jogo há operação policial reforçada no entorno do "
      "estádio. Parte do aumento pode ser de registro (mais flagrantes, BOs feitos ali mesmo), não de "
      "ocorrência. Sem dado de efetivo/operação por hora, não é possível separar.")
    w("- **Mais gente → mais contagem, não necessariamente mais risco.** O entorno recebe dezenas de milhares de "
      "pessoas a mais nas janelas do jogo; a contagem sobe com a população presente mesmo que o risco por "
      "pessoa não mude. Kurland, Johnson e Tilley (2014), em Wembley, discutem exatamente essa diferença entre "
      "atração/geração de crime e o tamanho da população exposta — sem um denominador da população presente "
      "por hora, a taxa por pessoa não é estimável aqui.")
    if cond is not None:
        nu = cond[cond["conduta"] == "(NULO)"].set_index(["janela", "natureza"])
        if ("DURANTE+PÓS", "furto") in nu.index:
            a_, b_ = nu.loc[("DURANTE+PÓS", "furto")], nu.loc[("DURANTE+PÓS", "roubo")]
            w(f"- **Indício a favor da leitura do registro (item 2c):** nos BOs do entorno, os registros **sem "
              f"`DESCR_CONDUTA`** sobem muito mais que os demais nas janelas DURANTE+PÓS (furto O/E "
              f"{a_['O/E']:.1f}, {int(a_['O'])} vs {a_['E']:.1f} esperados; roubo O/E {b_['O/E']:.1f}) — padrão "
              "compatível com BOs registrados na operação do próprio estádio, com preenchimento diferente. Não "
              "prova o canal, mas mostra que parte do excesso tem assinatura de registro, não só de ocorrência.")
    w("- As duas leituras não anulam o resultado (há mais ocorrências registradas no entorno durante e depois "
      "do jogo), mas impedem ler o IRR como aumento de risco individual.\n")

    w("## 3. Exploratórios (com p_BH; sem destaque no texto principal)\n")
    w("Horas tardias do event study (+4..+12 h) com p < 0,05 — BH na família do event study do domínio (todos "
      "os k × categorias × desfechos):\n")
    w(m.md(tard, 3) if len(tard) else "_nenhuma_")
    if dom == "sinistros":
        w("\nPRÉ no entorno dos estádios (agregado) — exploratório:\n")
        w(m.md(ent, 3))
    with open(os.path.join(out, f"relatorio_fase2b_{dom}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return L


def _leitura_pre(dom, pre, alvo, n_par):
    L = []
    for y in alvo:
        g = pre[(pre["desfecho"] == y)].set_index(["spec", "termo"])
        try:
            b = g.loc[("principal", "C_pre")]
            hm = g.loc[("+ EF hora×mês", "C_pre")]
            ht = g.loc[("+ EF hora×trimestre", "C_pre")]
            sp_ = g.loc[("só jogos do pareado", "C_pre")]
            sphm = g.loc[("só jogos do pareado + EF hora×mês", "C_pre")]
            ex = g.loc[("PRÉ estendido (k=−3..−1)", "C_pre_ext")]
            exhm = g.loc[("PRÉ estendido + EF hora×mês", "C_pre_ext")]
        except KeyError:
            continue
        queda = (hm["var_pct"] / b["var_pct"]) if b["var_pct"] else np.nan
        L.append(f"- `{y}`: PRÉ {pct(b['IRR'])} (p={b['p']:.3f}) no principal → {pct(hm['IRR'])} (p={hm['p']:.3f}) "
                 f"com EF hora×mês e {pct(ht['IRR'])} (p={ht['p']:.3f}) com hora×trimestre "
                 f"({100*queda:.0f}% do efeito original com hora×mês). Só os {n_par} jogos do pareado: "
                 f"{pct(sp_['IRR'])} (p={sp_['p']:.3f}); + hora×mês: {pct(sphm['IRR'])} (p={sphm['p']:.3f}). "
                 f"PRÉ estendido k=−3..−1: {pct(ex['IRR'])} (p={ex['p']:.3f}); + hora×mês {pct(exhm['IRR'])} "
                 f"(p={exhm['p']:.3f}).")
    return "**Leitura:**\n" + "\n".join(L)


def _leitura_desl(t):
    g = t[(t["janela"] == "durante")]
    if not len(g) or "IRR_disco" not in g:
        return ""
    up = g[(g["IRR_disco"] > 1) & (g["IRR_resto"] < 1)]
    return (f"Na janela DURANTE, {len(up)} de {len(g)} combinações estádio × desfecho têm entorno acima de 1 e "
            "resto da cidade abaixo de 1 (padrão de deslocamento).")


def _leitura_conduta(c):
    L = []
    for (jan, nat), g in c.groupby(["janela", "natureza"]):
        g = g.sort_values("parcela_do_excesso_positivo", ascending=False)
        top = g.iloc[0]
        L.append(f"- {nat} {jan}: maior parcela do excesso em `{top['conduta']}` "
                 f"({100*top['parcela_do_excesso_positivo']:.0f}%; O/E {top['O/E']:.2f}).")
    return "**Leitura:**\n" + "\n".join(L)


if __name__ == "__main__":
    import time
    t0 = time.time()
    f, jogos, fora = m.carrega()
    f["hm"] = f["hora_do_dia"].astype(str) + "_" + f["mes"].astype(str)
    f["htri"] = f["hora_do_dia"].astype(str) + "_" + ((f["mes"] - 1) // 3 + 1).astype(str)
    resumo = ["# V2 / Fase 2b — resumo das checagens\n",
              "Detalhe em `crimes/relatorio_fase2b_crimes.md` e `sinistros/relatorio_fase2b_sinistros.md`.\n"]
    for dom in os.environ.get("DOMS", "crimes,sinistros").split(","):
        out = m.dirs(dom)
        print("==", dom)
        if os.environ.get("REUSA") == "1":     # so refaz o relatorio a partir das tabelas fase2b_* ja salvas
            pre = pd.read_csv(tab(out, "fase2b_pre_checagens.csv"))
            dose = pd.read_csv(tab(out, "fase2b_dose_ef_hora_mes.csv"))
            n_par = int(pre["n_jogos_capital"].dropna().iloc[0])
            sp = pd.read_csv(tab(out, "fase2b_espaco_bh.csv"))
            desl = pd.read_csv(tab(out, "fase2b_deslocamento_entorno_vs_cidade.csv"))
            cond = pd.read_csv(tab(out, "fase2b_conduta_entorno.csv")) if dom == "crimes" else None
        else:
            if not os.path.exists(tab(out, "controles_pareados_jogos.csv")):
                m.controles_pareados(f, jogos, fora, dom, out)
            pre, dose, n_par = checagens_pre(f, jogos, fora, dom, out); print("  pre", round(time.time() - t0))
            sp = bh_espacial(out)
            desl = deslocamento(f, jogos, dom, out, sp); print("  deslocamento", round(time.time() - t0))
            cond = conduta_entorno(f, out) if dom == "crimes" else None
            print("  conduta", round(time.time() - t0))
        tard, ent = exploratorios(out, dom, sp)
        relatorio(dom, out, pre, dose, n_par, sp, desl, cond, tard, ent)
        alvo = ["crimes_violentos", "roubos_total"] if dom == "crimes" else ["acidentes_com_vitima"]
        resumo.append(f"## {dom.upper()}\n")
        resumo.append(_leitura_pre(dom, pre, alvo, n_par))
        resumo.append("")
        print(pre[pre["termo"].isin(["C_pre", "C_pre_ext"]) & pre["desfecho"].isin(alvo)]
              [["desfecho", "spec", "IRR", "p"]].round(3).to_string())
    with open(os.path.join(REP, "resumo_fase2b.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(resumo) + "\n")
    print("[ok]", round(time.time() - t0), "s")
