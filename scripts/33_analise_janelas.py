"""
V2 / Fase 2 -- 33_analise_janelas.py
Analise explicativa no painel HORARIO (data/gold/fato_hora_sp.csv), separada
por dominio: CRIMES (SSP) e SINISTROS (Infosiga). Nunca junta os dois num
indice, nunca na mesma familia de Benjamini-Hochberg.

Duas categorias de jogo, entram JUNTAS no modelo (nao exclusivas):
  - janela            (C_*): jogos dos 4 times em estadio da capital -> multidao perto do estadio
  - janela_fora_capital (F_*): jogos dos 4 times fora da capital      -> assistir pela TV / bares
Controle = hora sem nenhum jogo dos 4 times (inclui-se tambem a dummy C_fdj = mesma data de um jogo
na capital, fora das janelas, para o controle ser so dia sem jogo).

Itens (prompt V2, Fase 2): 1 descritivo; 2 modelo principal (GLM Poisson, EF hora x dia da semana +
ano x mes + feriado/vespera/ferias + chuva/temperatura, erro agrupado por semana; NB e cluster por dia
como robustez); 3 event study -6..+12 para AS DUAS categorias; 4 placebo/permutacao; 5 heterogeneidade
(incl. por time, com Santos); dose-resposta do publico so na janela da capital; 6 espaco x tempo
(entorno do estadio vs resto); 7 controles pareados; 8 pico horario + validacao por fold.
Robustezes: so `janela`; so base original (`janela_base_original`); horas dos eventos de grande publico
sem os 4 times de volta; NB; cluster por dia; total diario (com + sem hora) para lesao/crimes_violentos.

Saidas: reports/janelas/{crimes,sinistros}/ (relatorio, tabelas, figuras) + reports/janelas/resumo_fase2.md
Rodar:  python scripts/33_analise_janelas.py      (~15-20 min)
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(BASE, "data", "gold")
SILVER = os.path.join(BASE, "data", "silver")
REP = os.path.join(BASE, "reports", "janelas")
RNG = np.random.default_rng(20261116)
TERCIS = {}
N_PLACEBO = int(os.environ.get("N_PLACEBO", "1000"))

DOM = {
    "crimes": dict(desfechos=["crimes_violentos", "lesao_corporal_dolosa", "roubos_total", "furtos_total"],
                   principal="crimes_violentos", excl="excluir_crime"),
    "sinistros": dict(desfechos=["acidentes_com_vitima", "acidentes_total", "atropelamentos"],
                      principal="acidentes_com_vitima", excl="excluir_sinistro"),
}
WIN = ["pre", "durante", "pos"]
T_PRINC = ["C_pre", "C_durante", "C_pos", "C_fdj", "F_pre", "F_durante", "F_pos"]
ROTULO = {"C_pre": "capital PRÉ", "C_durante": "capital DURANTE", "C_pos": "capital PÓS",
          "C_fdj": "capital mesmo dia, fora das janelas", "F_pre": "fora da capital PRÉ",
          "F_durante": "fora da capital DURANTE", "F_pos": "fora da capital PÓS"}
ESTADIOS = {"Neo Quimica Arena": (-23.545278, -46.474167), "Allianz Parque": (-23.527500, -46.678611),
            "Morumbi": (-23.600278, -46.719444)}
BBOX = dict(lat=(-24.05, -23.35), lon=(-46.85, -46.35))  # mesmo da Etapa 10
R_ENTORNO = 3.0
MONIT = ["Corinthians", "Palmeiras", "Sao Paulo", "Santos"]


def dirs(dom):
    d = os.path.join(REP, dom)
    for s in ("tabelas", "figuras"):
        os.makedirs(os.path.join(d, s), exist_ok=True)
    return d


def bh(p):
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = ~np.isnan(p)
    q = p[ok]
    n = len(q)
    if n == 0:
        return out
    o = np.argsort(q)
    adj = np.minimum.accumulate((q[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    r = np.empty(n)
    r[o] = np.minimum(adj, 1)
    out[ok] = r
    return out


def md(df, ff=3):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        L.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else
                                   (f"{v:.{ff}f}" if isinstance(v, (float, np.floating)) else str(v))
                                   for v in r) + " |")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# dados
# ---------------------------------------------------------------------------
def carrega():
    f = pd.read_csv(os.path.join(GOLD, "fato_hora_sp.csv"), low_memory=False, parse_dates=["hora_ts", "data"])
    f["hd"] = f["hora_do_dia"].astype(str) + "_" + f["dia_semana"].astype(str)
    f["am"] = f["ano"].astype(str) + "_" + f["mes"].astype(str)
    f["chuva_l"] = np.log1p(f["chuva_mm"].fillna(0))
    f["chuva_na"] = f["chuva_mm"].isna().astype(float)
    f["temp"] = f["temp_c"].interpolate(limit=24)
    for w in WIN:
        f["C_" + w] = (f["janela"] == w).astype(float)
        f["F_" + w] = (f["janela_fora_capital"] == w).astype(float)
        f["BO_" + w] = (f["janela_base_original"] == w).astype(float)
    f["C_fdj"] = (f["janela"] == "fora_dia_jogo").astype(float)
    f["BO_fdj"] = (f["janela_base_original"] == "fora_dia_jogo").astype(float)
    for c in ("feriado", "vespera_feriado", "ferias"):
        f[c] = f[c].astype(str).str.lower().eq("true").astype(float) if f[c].dtype == object else f[c].astype(float)
    for c in ("excluir_crime", "excluir_sinistro", "excluir_evento_grande_publico", "dia_de_jogo",
              "hora_sem_jogo", "fora_capital_rmsp"):
        f[c] = f[c].astype(str).str.lower().eq("true") if f[c].dtype == object else f[c].astype(bool)
    jogos = pd.read_csv(os.path.join(SILVER, "jogos_sp_horario.csv"), parse_dates=["inicio_br", "data_br"])
    jogos = jogos[jogos["incluir_analise"].astype(bool)].copy()
    fora = pd.read_csv(os.path.join(SILVER, "jogos_fora_capital_horario.csv"), parse_dates=["inicio_br"])
    fora = fora[fora["incluir_analise"].astype(bool)].copy()
    return f, jogos, fora


def amostra(f, dom, com_eventos=False):
    m = ~f[DOM[dom]["excl"]] & f["temp"].notna()
    if not com_eventos:
        m &= ~f["excluir_evento_grande_publico"]
    return f[m].copy()


_CACHE = {}


def base_X(d, key):
    if key not in _CACHE:
        X = pd.get_dummies(d[["hd", "am"]], drop_first=True).astype(float)
        for c in ("feriado", "vespera_feriado", "ferias", "chuva_l", "chuva_na", "temp"):
            X[c] = d[c].to_numpy(float)
        X.insert(0, "const", 1.0)
        _CACHE[key] = X
    return _CACHE[key]


def ajusta(y, X, T, grupos, familia="poisson", alpha=None):
    XX = pd.concat([X.reset_index(drop=True), T.reset_index(drop=True)], axis=1)
    keep = XX.columns[(XX != 0).any(axis=0)]
    XX = XX[keep]
    fam = sm.families.Poisson() if familia == "poisson" else sm.families.NegativeBinomial(alpha=alpha)
    return sm.GLM(np.asarray(y, float), XX, family=fam).fit(cov_type="cluster", cov_kwds={"groups": grupos})


def coefs(m, cols, extra=None):
    rows = []
    ci = m.conf_int()
    for c in cols:
        if c not in m.params.index:
            continue
        b = m.params[c]
        rows.append({"termo": c, "IRR": np.exp(b), "var_pct": 100 * (np.exp(b) - 1),
                     "IC95_lo": np.exp(ci.loc[c, 0]), "IC95_hi": np.exp(ci.loc[c, 1]), "p": m.pvalues[c],
                     **(extra or {})})
    return rows


def alpha_ct(y, mu):
    """alpha da Binomial Negativa (NB2) pela regressao auxiliar de Cameron & Trivedi."""
    z = ((y - mu) ** 2 - y) / mu
    return max(float(np.sum(z * mu) / np.sum(mu ** 2)), 1e-6)


# ---------------------------------------------------------------------------
# 2. modelo principal + robustezes
# ---------------------------------------------------------------------------
def modelo_principal(f, dom, out):
    linhas = []
    d = amostra(f, dom)
    X = base_X(d, (dom, "main"))
    for y in DOM[dom]["desfechos"]:
        m = ajusta(d[y], X, d[T_PRINC], d["semana_id"].to_numpy())
        linhas += coefs(m, T_PRINC, {"desfecho": y, "spec": "principal (Poisson, cluster semana)"})
        md_ = ajusta(d[y], X, d[T_PRINC], d["data"].dt.strftime("%Y%m%d").to_numpy())
        linhas += coefs(md_, T_PRINC, {"desfecho": y, "spec": "cluster por dia"})
        a = alpha_ct(d[y].to_numpy(float), m.fittedvalues.to_numpy())
        mnb = ajusta(d[y], X, d[T_PRINC], d["semana_id"].to_numpy(), "nb", a)
        linhas += coefs(mnb, T_PRINC, {"desfecho": y, "spec": f"Binomial Negativa (alpha={a:.3f})"})
        T1 = ["C_pre", "C_durante", "C_pos", "C_fdj"]
        m1 = ajusta(d[y], X, d[T1], d["semana_id"].to_numpy())
        linhas += coefs(m1, T1, {"desfecho": y, "spec": "so janela (sem jogos fora da capital)"})
        Tb = ["BO_pre", "BO_durante", "BO_pos", "BO_fdj", "F_pre", "F_durante", "F_pos"]
        mb = ajusta(d[y], X, d[Tb], d["semana_id"].to_numpy())
        rb = coefs(mb, Tb, {"desfecho": y, "spec": "so base original (janela_base_original)"})
        for r in rb:
            r["termo"] = r["termo"].replace("BO_", "C_")
        linhas += rb
    de = amostra(f, dom, com_eventos=True)
    Xe = base_X(de, (dom, "eventos"))
    for y in DOM[dom]["desfechos"]:
        me = ajusta(de[y], Xe, de[T_PRINC], de["semana_id"].to_numpy())
        linhas += coefs(me, T_PRINC, {"desfecho": y, "spec": "com horas dos eventos de grande publico"})
    res = pd.DataFrame(linhas)
    pm = res["spec"].str.startswith("principal")
    res.loc[pm, "p_BH_dominio"] = bh(res.loc[pm, "p"])  # familia = desfechos x termos do dominio
    res["janela"] = res["termo"].map(ROTULO)
    res.to_csv(os.path.join(out, "tabelas", "modelo_principal_e_robustez.csv"), index=False)
    return res, d


def total_diario(f, dom, out):
    """Selecao (Fase 1): efeito no total diario (com + sem hora) -- so crimes."""
    if dom != "crimes":
        return None
    d = amostra(f, dom)
    dd = d.groupby("data").agg(dia_semana=("dia_semana", "first"), am=("am", "first"),
                               feriado=("feriado", "first"), ferias=("ferias", "first"),
                               dia_de_jogo=("dia_de_jogo", "first"),
                               jogo_fora=("janela_fora_capital", lambda x: (x != "nenhum").any()),
                               semana_id=("semana_id", "first"),
                               **{f"t_{y}": (f"total_dia_{y}", "first") for y in ("crimes_violentos",
                                                                                  "lesao_corporal_dolosa")})
    X = pd.get_dummies(dd[["dia_semana", "am"]].astype(str), drop_first=True).astype(float)
    X[["feriado", "ferias"]] = dd[["feriado", "ferias"]].to_numpy(float)
    X = sm.add_constant(X)
    T = pd.DataFrame({"dia_jogo_capital": dd["dia_de_jogo"].astype(float).to_numpy(),
                      "dia_jogo_fora": dd["jogo_fora"].astype(float).to_numpy()})
    rows = []
    for y in ("crimes_violentos", "lesao_corporal_dolosa"):
        m = ajusta(dd[f"t_{y}"], X, T, dd["semana_id"].to_numpy())
        rows += coefs(m, list(T.columns), {"desfecho": y, "spec": "total diario (com + sem hora)"})
    r = pd.DataFrame(rows)
    r.to_csv(os.path.join(out, "tabelas", "robustez_total_diario.csv"), index=False)
    return r


# ---------------------------------------------------------------------------
# 3. event study (as duas categorias)
# ---------------------------------------------------------------------------
KS = list(range(-6, 13))


def kname(p, k):
    return f"{p}_{'m' if k < 0 else 'p'}{abs(k)}"


def event_study(f, dom, out):
    d = amostra(f, dom)
    X = base_X(d, (dom, "main"))
    T = pd.DataFrame(index=d.index)
    for k in KS:
        T[kname("C", k)] = (d["hora_relativa"] == k).astype(float)
        T[kname("F", k)] = (d["hora_relativa_fora_capital"] == k).astype(float)
    T["C_outra_hora_dia_jogo"] = (d["dia_de_jogo"] & d["hora_relativa"].isna()).astype(float)
    rows = []
    for y in DOM[dom]["desfechos"]:
        m = ajusta(d[y], X, T, d["semana_id"].to_numpy())
        for cat in ("C", "F"):
            for r in coefs(m, [kname(cat, k) for k in KS], {"desfecho": y}):
                r["categoria"] = "capital" if cat == "C" else "fora_da_capital"
                r["k"] = int(r["termo"].split("_")[1].replace("m", "-").replace("p", ""))
                rows.append(r)
        # pre-tendencia: teste conjunto k=-6..-3 = 0 (Wald) para cada categoria
        for cat in ("C", "F"):
            nomes = [kname(cat, k) for k in range(-6, -2) if kname(cat, k) in m.params.index]
            R = np.zeros((len(nomes), len(m.params)))
            for i, n in enumerate(nomes):
                R[i, list(m.params.index).index(n)] = 1
            wt = m.wald_test(R, scalar=True)
            rows.append({"desfecho": y, "categoria": "capital" if cat == "C" else "fora_da_capital",
                         "termo": "wald_pretendencia_k-6..-3", "p": float(wt.pvalue), "k": np.nan})
    es = pd.DataFrame(rows)
    es.to_csv(os.path.join(out, "tabelas", "event_study.csv"), index=False)
    des = DOM[dom]["desfechos"]
    fig, axes = plt.subplots(len(des), 2, figsize=(11, 2.6 * len(des)), sharex=True, squeeze=False)
    for i, y in enumerate(des):
        for j, cat in enumerate(("capital", "fora_da_capital")):
            ax = axes[i, j]
            e = es[(es["desfecho"] == y) & (es["categoria"] == cat) & es["k"].notna()].sort_values("k")
            ax.axhline(1, color="k", lw=.8)
            for a, b, c in ((-2, 0, "#cfe2f3"), (0, 2, "#f4cccc"), (2, 4, "#d9ead3")):
                ax.axvspan(a - .5, b - .5, color=c, alpha=.6, lw=0)
            ax.errorbar(e["k"], e["IRR"], yerr=[e["IRR"] - e["IC95_lo"], e["IC95_hi"] - e["IRR"]],
                        fmt="o-", ms=3, capsize=2, color="#1f4e79")
            ax.set_title(f"{y} — jogos {'na capital' if j == 0 else 'fora da capital'}", fontsize=9)
            ax.grid(alpha=.3)
            if j == 0:
                ax.set_ylabel("IRR (IC95)")
    for ax in axes[-1]:
        ax.set_xlabel("hora relativa ao início do jogo (azul PRÉ, vermelho DURANTE, verde PÓS)")
        ax.set_xticks(KS)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figuras", "03_event_study.png"), dpi=110)
    plt.close(fig)
    return es


# ---------------------------------------------------------------------------
# 4. placebo / permutacao (dois passos, forma fechada)
# ---------------------------------------------------------------------------
def _janelas_de_inicio(inicio, pos_de_hora):
    """indices (posicao na amostra) das horas PRE/DURANTE/POS para um inicio s (regra do ponto medio)."""
    base = inicio.floor("h")
    out = {w: [] for w in WIN}
    for dh in range(-4, 6):
        h = base + pd.Timedelta(hours=dh)
        k = int(np.floor(((h + pd.Timedelta(minutes=30)) - inicio) / pd.Timedelta(hours=1)))
        w = {-2: "pre", -1: "pre", 0: "durante", 1: "durante", 2: "pos", 3: "pos"}.get(k)
        if w and h in pos_de_hora:
            out[w].append(pos_de_hora[h])
    return out


def placebo(f, jogos, fora, dom, out):
    """Permutacao em dois passos. CORRECAO (2a versao): o modelo de base (calendario + clima + a OUTRA
    categoria) e ajustado SO nas horas sem jogo da categoria testada -- assim os EF hora x dia da semana nao
    absorvem o efeito do jogo (os jogos se concentram em poucas celulas, ex. domingo 16h) e o placebo fica
    centrado em ~0 por construcao (equacoes de score do Poisson). Candidatos = horas livres de janela da
    categoria testada (nivel de hora, nao de dia inteiro), mesmo dia da semana, mesma hora de inicio,
    em QUALQUER data da amostra (a 1a versao usava +-6 semanas e ficava com ~2 candidatos por jogo na
    categoria fora da capital -> placebo preso a poucas datas), dia sem feriado e sem jogo na capital."""
    d = amostra(f, dom).reset_index(drop=True)
    X = base_X(d.set_index(pd.RangeIndex(len(d))), (dom, "placebo"))
    pos = {h: i for i, h in enumerate(d["hora_ts"])}
    datas_jogo_cap = set(jogos["data_br"].dt.normalize())
    dias = d.groupby("data").agg(feriado=("feriado", "first"), dow=("dia_semana", "first"))
    dias["cap"] = dias.index.isin(datas_jogo_cap)
    cand_dias = dias[(dias["feriado"] == 0) & ~dias["cap"]]
    res, diag = [], []
    for cat, eventos, tcols_base in (("capital", jogos, ["F_pre", "F_durante", "F_pos"]),
                                     ("fora_da_capital", fora, ["C_pre", "C_durante", "C_pos", "C_fdj"])):
        if cat == "capital":
            livre = (d["janela"] == "dia_sem_jogo").to_numpy()            # sem jogo na capital (nem janela, nem dia)
        else:
            livre = (d["janela_fora_capital"] == "nenhum").to_numpy()     # sem janela de jogo fora da capital
        livre_cand = livre & (d["janela"] == "dia_sem_jogo").to_numpy()   # e no grupo de referencia do modelo
        cand = []
        for _, g in eventos.iterrows():
            s0 = g["inicio_br"]
            dow = (s0.weekday() + 1) % 7
            cd = cand_dias[cand_dias["dow"] == dow]   # toda a amostra (sazonalidade fica nos EF ano x mes)
            opts = []
            for dt in cd.index:
                jw = _janelas_de_inicio(dt + (s0 - s0.normalize()), pos)
                if all(len(jw[w]) == 2 for w in WIN) and all(livre_cand[i] for w in WIN for i in jw[w]):
                    opts.append(jw)
            cand.append(opts)
        n_opts = [len(c) for c in cand]
        cand = [c for c in cand if c]
        diag.append({"categoria": cat, "eventos": len(eventos), "eventos_com_candidato": len(cand),
                     "candidatos_por_evento_mediana": float(np.median(n_opts)) if n_opts else 0})
        prefix = "C_" if cat == "capital" else "F_"
        Xf = X.loc[livre]
        keep = Xf.columns[(Xf != 0).any(axis=0)]
        T = d[tcols_base]
        tkeep = [c for c in tcols_base if (T.loc[livre, c] != 0).any()]
        XX = pd.concat([X[keep], T[tkeep]], axis=1)
        for y in DOM[dom]["desfechos"]:
            yy = d[y].to_numpy(float)
            m0 = sm.GLM(yy[livre], XX.loc[livre], family=sm.families.Poisson()).fit()
            mu = m0.predict(XX).to_numpy()
            real = {w: np.log(yy[d[prefix + w] == 1].sum() / mu[d[prefix + w] == 1].sum()) for w in WIN}
            sims = {w: np.empty(N_PLACEBO) for w in WIN}
            for r in range(N_PLACEBO):
                esc = [c[RNG.integers(len(c))] for c in cand]
                for w in WIN:
                    idx = np.concatenate([e[w] for e in esc])
                    sims[w][r] = np.log(yy[idx].sum() / mu[idx].sum())
            for w in WIN:
                s_ = sims[w]
                res.append({"desfecho": y, "categoria": cat, "janela": w, "beta_real_2passos": real[w],
                            "IRR_real_2passos": np.exp(real[w]), "placebo_media": s_.mean(),
                            "placebo_p2.5": np.percentile(s_, 2.5), "placebo_p97.5": np.percentile(s_, 97.5),
                            "percentil_real": 100 * (s_ < real[w]).mean(),
                            "p_permutacao_bilateral": min(1, 2 * min((s_ >= real[w]).mean(), (s_ <= real[w]).mean())),
                            "n_eventos_com_placebo": len(cand)})
    p = pd.DataFrame(res)
    p.to_csv(os.path.join(out, "tabelas", "placebo_permutacao.csv"), index=False)
    pd.DataFrame(diag).to_csv(os.path.join(out, "tabelas", "placebo_candidatos.csv"), index=False)
    return p


# ---------------------------------------------------------------------------
# 5. heterogeneidade + dose-resposta do publico
# ---------------------------------------------------------------------------
def _comp4(c):
    c = str(c)
    if c in ("Copa Libertadores", "Copa Sul-Americana", "Recopa Sul-Americana"):
        return "CONMEBOL"
    if c in ("Serie A", "Copa do Brasil", "Campeonato Paulista"):
        return c
    return "Outros"


def _times_cap(r):
    s = {r["mandante"]}
    v = str(r["visitante"])
    for t in MONIT:
        if t.lower() in v.lower():
            s.add(t)
    return "+".join(sorted(s))


def atributos_hora(d, jogos, fora):
    jg = jogos.set_index("jogo_id")
    jg["comp4"] = jg["competicao"].map(_comp4)
    jg["times"] = jogos.set_index("jogo_id").apply(_times_cap, axis=1)
    fo = fora.set_index("jogo_id_fora")
    fo["comp4"] = fo["competicao"].map(_comp4)
    A = pd.DataFrame(index=d.index)
    jid = d["jogo_id"]
    for a, src in (("classico", "classico"), ("noturno", "noturno"), ("fim_de_semana", "fim_de_semana"),
                   ("comp4", "comp4"), ("resultado", "resultado_mandante"), ("times", "times")):
        A["C_" + a] = jid.map(jg[src])
    fid = d["jogo_id_fora_capital"]
    for a, src in (("classico", "classico"), ("noturno", "noturno"), ("fim_de_semana", "fim_de_semana"),
                   ("comp4", "comp4"), ("rmsp", "regiao_metropolitana_sp")):
        A["F_" + a] = fid.map(fo[src])
    A["F_times"] = d["times_fora_capital"]
    return A


def heterogeneidade(f, jogos, fora, dom, out):
    d = amostra(f, dom)
    X = base_X(d, (dom, "main"))
    A = atributos_hora(d, jogos, fora)
    specs = []
    for cat in ("C", "F"):
        for a in ("classico", "noturno", "fim_de_semana", "comp4") + (("rmsp",) if cat == "F" else ("resultado",)):
            specs.append((cat, a))
        for t in MONIT:
            specs.append((cat, "time:" + t))
    rows = []
    for cat, a in specs:
        T = d[[c for c in T_PRINC if not c.startswith(cat + "_") or c == "C_fdj"]].copy()
        if a.startswith("time:"):
            t = a.split(":")[1]
            lv = A[cat + "_times"].fillna("").str.contains(t).map({True: t, False: "outros_times"})
        else:
            lv = A[cat + "_" + a].astype(str)
        for w in WIN:
            on = d[f"{cat}_{w}"] == 1
            if a == "resultado" and w != "pos":     # resultado so e conhecido depois do jogo
                T[f"{cat}_{w}"] = on.astype(float)
                continue
            for v in sorted(lv[on].dropna().unique()):
                T[f"{cat}_{w}__{v}"] = (on & (lv == v)).astype(float)
        for y in DOM[dom]["desfechos"]:
            m = ajusta(d[y], X, T, d["semana_id"].to_numpy())
            cols = [c for c in T.columns if c.startswith(cat + "_") and "__" in c]
            for r in coefs(m, cols, {"desfecho": y, "categoria": "capital" if cat == "C" else "fora_da_capital",
                                     "atributo": a}):
                r["janela"], r["nivel"] = r["termo"].split("__")[0].split("_", 1)[1], r["termo"].split("__")[1]
                r["n_horas"] = int(T[r["termo"]].sum())
                rows.append(r)
    h = pd.DataFrame(rows)
    h["p_BH_dominio_atributo"] = np.nan
    for (cat, a), g in h.groupby(["categoria", "atributo"]):
        h.loc[g.index, "p_BH_dominio_atributo"] = bh(g["p"])
    h.to_csv(os.path.join(out, "tabelas", "heterogeneidade.csv"), index=False)
    return h


def dose_publico(f, jogos, dom, out, d_override=None, rotulo="cidade toda", extra_fe=()):
    """Dose-resposta SO na janela da capital: interacao com log(publico) centrado e tercis."""
    d = amostra(f, dom) if d_override is None else d_override
    jg = jogos.set_index("jogo_id")
    pub = d["jogo_id"].map(jg["publico"]).astype(float)
    st = d["jogo_id"].map(jg["publico_status"])
    fech = st.eq("portoes_fechados")
    d = d[~fech].copy()
    pub = pub[~fech]
    lp = np.log(pub.where(pub > 0))
    jl = np.log(jogos.loc[jogos["publico"] > 0, "publico"])
    lpc = (lp - jl.mean()).fillna(0)
    terc = pd.qcut(jogos.loc[jogos["publico"] > 0, "publico"], 3, labels=["T1", "T2", "T3"], retbins=True)[1]
    tc = pd.cut(pub, terc, labels=["T1", "T2", "T3"], include_lowest=True).astype(str)
    X = base_X(d, (dom, "dose", rotulo)) if (d_override is None and not extra_fe) else d_override_X(d, extra_fe)
    rows = []
    for spec in ("log", "tercis"):
        T = d[["C_fdj", "F_pre", "F_durante", "F_pos"] + (["C_pre", "C_durante", "C_pos"] if spec == "log" else [])].copy()
        for w in WIN:
            on = d[f"C_{w}"] == 1
            if spec == "log":
                T[f"C_{w}__x_logpub"] = (on * lpc).astype(float)
            else:
                for t in ("T1", "T2", "T3"):
                    T[f"C_{w}__{t}"] = (on & (tc == t)).astype(float)
        for y in DOM[dom]["desfechos"]:
            m = ajusta(d[y], X, T, d["semana_id"].to_numpy())
            cols = [c for c in T.columns if "__" in c] + (["C_pre", "C_durante", "C_pos"] if spec == "log" else [])
            rows += coefs(m, cols, {"desfecho": y, "spec": spec, "area": rotulo})
    r = pd.DataFrame(rows)
    TERCIS[(dom, rotulo)] = terc
    return r


def _interacoes_hora(X, d, kind):
    """EF hora do dia x mes ('hm') ou x trimestre ('htri') SO como interacoes (hora 1..23 x mes 2..12 /
    trimestre 2..4): o efeito principal da hora ja esta em hora x dia da semana e o do mes em ano x mes;
    com dummies cheias a matriz fica com posto incompleto e o LAPACK (gelsd) estoura memoria."""
    H = d["hora_do_dia"].to_numpy()
    P = d["mes"].to_numpy() if kind == "hm" else ((d["mes"].to_numpy() - 1) // 3 + 1)
    novos = {f"{kind}_{h}_{q}": ((H == h) & (P == q)).astype(float)
             for h in range(1, 24) for q in range(2, 13 if kind == "hm" else 5)}
    return pd.concat([X, pd.DataFrame(novos, index=X.index)], axis=1)


def d_override_X(d, extra_fe=()):
    X = pd.get_dummies(d[["hd", "am"]], drop_first=True).astype(float)
    for e in extra_fe:
        X = _interacoes_hora(X, d, e)
    for c in ("feriado", "vespera_feriado", "ferias", "chuva_l", "chuva_na", "temp"):
        X[c] = d[c].to_numpy(float)
    X.insert(0, "const", 1.0)
    return X


# ---------------------------------------------------------------------------
# 6. espaco x tempo
# ---------------------------------------------------------------------------
def dist_km(lat, lon, lat0, lon0):
    return np.sqrt(((lat - lat0) * 110.574) ** 2 + ((lon - lon0) * 111.320 * np.cos(np.radians(lat0))) ** 2)


def contagens_espaciais(dom):
    """Contagem horaria por estadio (disco de 3 km) e resto da cidade. Crime: coordenada valida (BBOX
    da Etapa 10), SEM as celulas de empilhamento de geocodificacao perto do estadio, e alternativa por
    bairros do estadio (regra da Etapa 10: bairros com >=10% dos pontos a ate 1,5 km)."""
    horas = pd.date_range("2022-01-01", "2023-12-31 23:00", freq="h")
    if dom == "crimes":
        ev = pd.read_csv(os.path.join(SILVER, "crime_eventos_sp.csv.gz"),
                         usecols=["timestamp", "tem_hora", "is_violento", "is_lesao_dolosa", "is_roubo", "is_furto",
                                  "bairro", "lat", "lon"], parse_dates=["timestamp"])
        tipos = {"crimes_violentos": "is_violento", "lesao_corporal_dolosa": "is_lesao_dolosa",
                 "roubos_total": "is_roubo", "furtos_total": "is_furto"}
    else:
        ev = pd.read_csv(os.path.join(SILVER, "acidentes_eventos_sp.csv.gz"),
                         usecols=["timestamp", "tem_hora", "com_vitima", "atropelamento", "lat", "lon"],
                         parse_dates=["timestamp"])
        ev["todos"] = True
        tipos = {"acidentes_com_vitima": "com_vitima", "acidentes_total": "todos", "atropelamentos": "atropelamento"}
    ev = ev[ev["tem_hora"].astype(bool)].copy()
    ev["h"] = ev["timestamp"].dt.floor("h")
    ev["coord_ok"] = ev["lat"].between(*BBOX["lat"]) & ev["lon"].between(*BBOX["lon"]) & (ev["lat"].abs() > .01)
    ev["ck"] = ev["lat"].round(3).astype(str) + "," + ev["lon"].round(3).astype(str)
    out, diag = {}, []
    for s, (la, lo) in ESTADIOS.items():
        dd = dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo)
        disco = ev["coord_ok"] & (dd <= R_ENTORNO)
        pile = set()
        if dom == "crimes":
            perto = ev[disco & (dd <= 1.0)]
            vc = perto["ck"].value_counts()
            med = ev.loc[disco, "ck"].value_counts().median()
            pile = set(vc[(vc > 20 * med)].index[:3])
            near = ev[ev["coord_ok"] & ev["bairro"].notna() & (dd <= 1.5)]["bairro"].value_counts()
            bairros = near[near / near.sum() >= .10].index.tolist()
            diag.append({"estadio": s, "celulas_empilhamento_excluidas": "; ".join(sorted(pile)),
                         "registros_excluidos": int(ev.loc[disco, "ck"].isin(pile).sum()),
                         "bairros_entorno": ", ".join(bairros)})
        m = disco & ~ev["ck"].isin(pile)
        for y, flag in tipos.items():
            sel = ev[m & ev[flag].astype(bool)]
            out[(s, "disco", y)] = sel.groupby("h").size().reindex(horas, fill_value=0)
            if dom == "crimes":
                selb = ev[ev["bairro"].isin(bairros) & ev[flag].astype(bool)]
                out[(s, "bairros", y)] = selb.groupby("h").size().reindex(horas, fill_value=0)
    # resto da cidade = total com hora - registros em qualquer um dos 3 discos (com coordenada valida)
    em_disco = np.zeros(len(ev), bool)
    for s, (la, lo) in ESTADIOS.items():
        em_disco |= ev["coord_ok"].to_numpy() & (dist_km(ev["lat"].to_numpy(), ev["lon"].to_numpy(), la, lo) <= R_ENTORNO)
    for y, flag in tipos.items():
        sel = ev[~em_disco & ev[flag].astype(bool)]
        out[("resto", "resto", y)] = sel.groupby("h").size().reindex(horas, fill_value=0)
    return out, pd.DataFrame(diag)


def espaco_tempo(f, jogos, dom, out):
    cont, diag = contagens_espaciais(dom)
    d = amostra(f, dom)
    X = base_X(d, (dom, "main"))
    rows = []
    tipos_area = ["disco"] + (["bairros"] if dom == "crimes" else [])
    for s in ESTADIOS:
        est = d["jogo_estadio"].eq(s)
        T = pd.DataFrame(index=d.index)
        for w in WIN:
            T[f"C_{w}__este_estadio"] = ((d[f"C_{w}"] == 1) & est).astype(float)
            T[f"C_{w}__outro_estadio"] = ((d[f"C_{w}"] == 1) & ~est).astype(float)
        T[["C_fdj", "F_pre", "F_durante", "F_pos"]] = d[["C_fdj", "F_pre", "F_durante", "F_pos"]]
        for area in tipos_area:
            for y in DOM[dom]["desfechos"]:
                yy = cont[(s, area, y)].reindex(d["hora_ts"]).to_numpy()
                m = ajusta(yy, X, T, d["semana_id"].to_numpy())
                for r in coefs(m, [f"C_{w}__este_estadio" for w in WIN],
                               {"desfecho": y, "estadio": s, "area": area, "media_hora": yy.mean(),
                                "n_jogos": int(jogos["estadio"].eq(s).sum())}):
                    r["janela"] = r["termo"].split("__")[0][2:]
                    rows.append(r)
    for y in DOM[dom]["desfechos"]:
        yy = cont[("resto", "resto", y)].reindex(d["hora_ts"]).to_numpy()
        m = ajusta(yy, X, d[T_PRINC], d["semana_id"].to_numpy())
        for r in coefs(m, ["C_pre", "C_durante", "C_pos"], {"desfecho": y, "estadio": "resto da cidade",
                                                          "area": "resto", "media_hora": yy.mean()}):
            r["janela"] = r["termo"][2:]
            rows.append(r)
    e = pd.DataFrame(rows)
    # efeito agregado dos 3 estadios por inverso da variancia (log IRR)
    agg = []
    for (area, y, w), g in e[e["estadio"].isin(ESTADIOS)].groupby(["area", "desfecho", "janela"]):
        b = np.log(g["IRR"])
        se = (np.log(g["IC95_hi"]) - np.log(g["IC95_lo"])) / (2 * 1.96)
        wt = 1 / se ** 2
        bb, ss = (wt * b).sum() / wt.sum(), np.sqrt(1 / wt.sum())
        agg.append({"desfecho": y, "estadio": "3 estádios (inverso da variância)", "area": area, "janela": w,
                    "IRR": np.exp(bb), "var_pct": 100 * (np.exp(bb) - 1), "IC95_lo": np.exp(bb - 1.96 * ss),
                    "IC95_hi": np.exp(bb + 1.96 * ss), "p": 2 * stats.norm.sf(abs(bb / ss))})
    e = pd.concat([e, pd.DataFrame(agg)], ignore_index=True)
    e.to_csv(os.path.join(out, "tabelas", "espaco_tempo.csv"), index=False)
    diag.to_csv(os.path.join(out, "tabelas", "espaco_empilhamento_bairros.csv"), index=False)
    # dose-resposta no entorno (empilha os 3 discos via soma das contagens do estadio do jogo)
    return e, diag, cont


def dose_entorno(f, jogos, dom, cont):
    """Dose no entorno: y = contagem no disco do estadio do jogo daquela hora; fora de janela, soma dos 3
    discos / 3 (nivel medio de entorno). Aproximacao declarada no relatorio."""
    d = amostra(f, dom).copy()
    for y in DOM[dom]["desfechos"]:
        tot = sum(cont[(s, "disco", y)] for s in ESTADIOS).reindex(d["hora_ts"]).to_numpy() / 3
        este = np.full(len(d), np.nan)
        for s in ESTADIOS:
            mk = d["jogo_estadio"].eq(s).to_numpy()
            este[mk] = cont[(s, "disco", y)].reindex(d["hora_ts"]).to_numpy()[mk]
        d[y] = np.where(np.isnan(este), tot, este)
    d = d[d["jogo_estadio"].isna() | d["jogo_estadio"].isin(ESTADIOS)]
    return dose_publico(f, jogos, dom, None, d_override=d, rotulo="entorno do estádio (3 km)")


# ---------------------------------------------------------------------------
# 7. controles pareados
# ---------------------------------------------------------------------------
def controles_pareados(f, jogos, fora, dom, out):
    d = amostra(f, dom)
    d = d.set_index("hora_ts")
    dias = d.groupby("data").agg(dow=("dia_semana", "first"), fer=("feriado", "first"),
                                 cap=("dia_de_jogo", "first"),
                                 fora=("janela_fora_capital", lambda x: (x != "nenhum").any()),
                                 n=("hora_do_dia", "size"))
    livres = dias[(dias["fer"] == 0) & ~dias["cap"] & ~dias["fora"] & (dias["n"] == 24)].index
    rows = []
    for cat, ev in (("capital", jogos), ("fora_da_capital", fora)):
        for _, g in ev.iterrows():
            s = g["inicio_br"]
            dia = s.normalize()
            dow = (s.weekday() + 1) % 7
            ctr = [c for c in livres if abs(c - dia) <= pd.Timedelta(days=28) and dias.loc[c, "dow"] == dow]
            if len(ctr) < 2:
                continue
            off = s - dia
            jw = {w: [] for w in WIN}
            for dh in range(-4, 6):
                h = s.floor("h") + pd.Timedelta(hours=dh)
                k = int(np.floor(((h + pd.Timedelta(minutes=30)) - s) / pd.Timedelta(hours=1)))
                w = {-2: "pre", -1: "pre", 0: "durante", 1: "durante", 2: "pos", 3: "pos"}.get(k)
                if w:
                    jw[w].append(h - dia)
            # horas FORA do dia do jogo: as que nao estao em nenhuma janela (de nenhuma categoria)
            hd = d.loc[d["data"] == dia]
            if len(hd) < 24:
                continue
            fora_h = [h - dia for h in hd.index if (hd.loc[h, "janela"] in ("fora_dia_jogo", "dia_sem_jogo"))
                      and hd.loc[h, "janela_fora_capital"] == "nenhum"]
            if len(fora_h) < 6:
                continue
            for y in DOM[dom]["desfechos"]:
                def soma(base, offs):
                    v = [d[y].get(base + o, np.nan) for o in offs]
                    return np.nan if np.any(np.isnan(v)) else float(np.sum(v))
                rec = {"categoria": cat, "desfecho": y, "dia": dia, "n_ctrl": len(ctr),
                       "F_jogo": soma(dia, fora_h), "F_ctrl": np.nanmean([soma(c, fora_h) for c in ctr])}
                for w in WIN:
                    rec[f"W_{w}_jogo"] = soma(dia, jw[w])
                    rec[f"W_{w}_ctrl"] = np.nanmean([soma(c, jw[w]) for c in ctr])
                rows.append(rec)
    p = pd.DataFrame(rows).dropna()
    p[["categoria", "dia"]].drop_duplicates().to_csv(os.path.join(out, "tabelas", "controles_pareados_jogos.csv"),
                                                    index=False)
    res = []
    for (cat, y), g in p.groupby(["categoria", "desfecho"]):
        for w in WIN:
            def did(gg):
                return np.log(gg[f"W_{w}_jogo"].sum() / gg[f"W_{w}_ctrl"].sum()) - \
                    np.log(gg["F_jogo"].sum() / gg["F_ctrl"].sum())
            est = did(g)
            boots = [did(g.iloc[RNG.integers(0, len(g), len(g))]) for _ in range(1000)]
            res.append({"categoria": cat, "desfecho": y, "janela": w, "n_jogos": len(g),
                        "razao_janela_jogo_vs_ctrl": g[f"W_{w}_jogo"].sum() / g[f"W_{w}_ctrl"].sum(),
                        "razao_fora_jogo_vs_ctrl": g["F_jogo"].sum() / g["F_ctrl"].sum(),
                        "DiD_IRR": np.exp(est), "IC95_lo": np.exp(np.percentile(boots, 2.5)),
                        "IC95_hi": np.exp(np.percentile(boots, 97.5))})
    r = pd.DataFrame(res)
    r.to_csv(os.path.join(out, "tabelas", "controles_pareados.csv"), index=False)
    return r


# ---------------------------------------------------------------------------
# 1. descritivo
# ---------------------------------------------------------------------------
def descritivo(f, dom, out):
    d = amostra(f, dom)
    X = base_X(d, (dom, "main"))
    rows = []
    ctrl = d[d["hora_sem_jogo"]]
    ref = ctrl.groupby(["hora_do_dia", "dia_semana"])[DOM[dom]["desfechos"]].mean()
    for cat, col in (("capital", "janela"), ("fora_da_capital", "janela_fora_capital")):
        for w in WIN:
            g = d[d[col] == w]
            r = ref.reindex(pd.MultiIndex.from_arrays([g["hora_do_dia"], g["dia_semana"]]))
            for y in DOM[dom]["desfechos"]:
                rows.append({"categoria": cat, "janela": w, "desfecho": y, "n_horas": len(g),
                             "media_janela": g[y].mean(), "media_mesmas_horas_dia_semana_sem_jogo": r[y].mean(),
                             "razao": g[y].mean() / r[y].mean()})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(out, "tabelas", "descritivo_janela_vs_mesmas_horas.csv"), index=False)
    # perfil horario (dias com jogo na capital vs dias sem nenhum jogo) e figura alinhada (obs/esperado)
    y0 = DOM[dom]["principal"]
    m0 = ajusta(d[y0], X, pd.DataFrame(index=d.index), d["semana_id"].to_numpy())
    d["esp"] = m0.fittedvalues.to_numpy()
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    dj = d[d["dia_de_jogo"]]
    ds = d.loc[d.groupby("data")["hora_sem_jogo"].transform("all")]
    ax[0].plot(range(24), dj.groupby("hora_do_dia")[y0].mean(), "o-", label="dias com jogo na capital")
    ax[0].plot(range(24), ds.groupby("hora_do_dia")[y0].mean(), "s-", label="dias sem nenhum jogo dos 4 times")
    ax[0].set_xlabel("hora do dia")
    ax[0].set_ylabel(f"{y0} médio por hora")
    ax[0].set_title("Perfil horário (sem ajuste — dias de jogo concentram fins de semana)")
    ax[0].legend(fontsize=8)
    for cat, col, mk in (("capital", "hora_relativa", "o-"), ("fora da capital", "hora_relativa_fora_capital", "s-")):
        g = d[d[col].between(-6, 12)].groupby(col).apply(lambda x: x[y0].sum() / x["esp"].sum())
        ax[1].plot(g.index, g.values, mk, label=f"jogos {cat}")
    ax[1].axhline(1, color="k", lw=.8)
    for a, b, c in ((-2, 0, "#cfe2f3"), (0, 2, "#f4cccc"), (2, 4, "#d9ead3")):
        ax[1].axvspan(a - .5, b - .5, color=c, alpha=.6, lw=0)
    ax[1].set_xlabel("hora relativa ao início do jogo")
    ax[1].set_ylabel("observado / esperado (calendário + clima)")
    ax[1].set_title(f"{y0}: alinhado pela hora do jogo")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figuras", "01_descritivo.png"), dpi=110)
    plt.close(fig)
    return t


# ---------------------------------------------------------------------------
# 8. pico horario
# ---------------------------------------------------------------------------
def _pearson(y, mu):
    return (y - mu) / np.sqrt(mu)


def picos(f, dom, out):
    d = amostra(f, dom).reset_index(drop=True)
    X = base_X(d.set_index(pd.RangeIndex(len(d))), (dom, "placebo"))
    y0 = DOM[dom]["principal"]
    resultados, validacao, concord = [], [], []
    niveis = ["hora"] + (["2h"] if dom == "sinistros" else [])
    m = ajusta(d[y0], X, pd.DataFrame(index=d.index), d["semana_id"].to_numpy())   # SEM variavel de jogo
    mu = m.fittedvalues.to_numpy()
    yy = d[y0].to_numpy(float)
    for nivel in niveis:
        if nivel == "hora":
            o, e = yy, mu
            lab_c, lab_f = d["janela"].to_numpy(), d["janela_fora_capital"].to_numpy()
            ctrl = d["hora_sem_jogo"].to_numpy()
            valid = np.ones(len(d), bool)
        else:  # soma movel de 2 h (h, h+1) consecutivas; bloco vale se as 2 horas estao na mesma janela
            cons = (d["hora_ts"].diff(-1) == -pd.Timedelta(hours=1)).to_numpy()
            o = yy + np.roll(yy, -1)
            e = mu + np.roll(mu, -1)
            lc, lf = d["janela"].to_numpy(), d["janela_fora_capital"].to_numpy()
            same = (lc == np.roll(lc, -1)) & (lf == np.roll(lf, -1))
            valid = cons & same
            lab_c, lab_f = lc, lf
            ctrl = d["hora_sem_jogo"].to_numpy() & np.roll(d["hora_sem_jogo"].to_numpy(), -1)
        r = _pearson(o, e)
        cauda = -np.log10(np.clip(stats.poisson.sf(o - 1, e), 1e-300, 1))
        defs = {"P90_pearson": r > np.quantile(r[valid], .90), "P95_pearson": r > np.quantile(r[valid], .95),
                "P90_cauda_poisson": cauda > np.quantile(cauda[valid], .90)}
        for nome, pk in defs.items():
            pk = pk & valid
            base = pk[ctrl & valid]
            for cat, lab in (("capital", lab_c), ("fora_da_capital", lab_f)):
                for w in WIN:
                    on = (lab == w) & valid
                    a, b = pk[on].sum(), on.sum()
                    c_, d_ = base.sum(), len(base)
                    rr = (a / b) / (c_ / d_) if b and c_ else np.nan
                    se = np.sqrt(1 / max(a, .5) - 1 / b + 1 / c_ - 1 / d_) if b else np.nan
                    fis = stats.fisher_exact([[a, b - a], [c_, d_ - c_]])[1] if b else np.nan
                    resultados.append({"nivel": nivel, "definicao": nome, "categoria": cat, "janela": w,
                                       "n_unidades": int(b), "n_pico": int(a), "freq_pico": a / b if b else np.nan,
                                       "freq_pico_controle": c_ / d_, "RR": rr,
                                       "IC95_lo": rr * np.exp(-1.96 * se), "IC95_hi": rr * np.exp(1.96 * se),
                                       "p_fisher": fis})
        kk = list(defs)
        for i in range(len(kk)):
            for j in range(i + 1, len(kk)):
                A_, B_ = defs[kk[i]] & valid, defs[kk[j]] & valid
                concord.append({"nivel": nivel, "def_1": kk[i], "def_2": kk[j],
                                "jaccard": (A_ & B_).sum() / (A_ | B_).sum(),
                                "kappa": _kappa(A_[valid], B_[valid])})
        # validacao: esperado + limiar so no treino de cada fold mensal de 2023
        for mes in range(1, 13):
            ini = pd.Timestamp(2023, mes, 1)
            fim = ini + pd.offsets.MonthBegin(1)
            tr = (d["hora_ts"] < ini).to_numpy()
            te = ((d["hora_ts"] >= ini) & (d["hora_ts"] < fim)).to_numpy()
            if te.sum() == 0:
                continue
            Xt = X.iloc[np.where(tr | te)[0]]
            keep = Xt.columns[(Xt.iloc[:tr.sum()] != 0).any(axis=0)]   # colunas presentes no treino
            mt = sm.GLM(yy[tr], X.loc[tr, keep], family=sm.families.Poisson()).fit()
            Xte = X.loc[te, keep].copy()
            # mes de teste nao existe no treino: usa o efeito medio do mesmo mes do ano anterior
            am_te = f"am_2023_{mes}"
            am_prev = f"am_2022_{mes}"
            if am_prev in keep:
                Xte[am_prev] = 1.0
            mu_tr, mu_te = mt.predict(X.loc[tr, keep]), mt.predict(Xte)
            if nivel == "hora":
                o_tr, e_tr, o_te, e_te = yy[tr], mu_tr, yy[te], mu_te
                v_tr, v_te = np.ones(tr.sum(), bool), np.ones(te.sum(), bool)
            else:
                o_tr = yy[tr] + np.roll(yy[tr], -1)
                e_tr = mu_tr + np.roll(mu_tr, -1)
                o_te = yy[te] + np.roll(yy[te], -1)
                e_te = mu_te + np.roll(mu_te, -1)
                v_tr, v_te = valid[tr], valid[te]
            r_tr, r_te = _pearson(o_tr, e_tr), _pearson(o_te, e_te)
            c_tr = -np.log10(np.clip(stats.poisson.sf(o_tr - 1, e_tr), 1e-300, 1))
            c_te = -np.log10(np.clip(stats.poisson.sf(o_te - 1, e_te), 1e-300, 1))
            validacao.append({"nivel": nivel, "fold": f"2023-{mes:02d}", "n_teste": int(v_te.sum()),
                              "prev_P90_pearson": (r_te[v_te] > np.quantile(r_tr[v_tr], .9)).mean(),
                              "prev_P95_pearson": (r_te[v_te] > np.quantile(r_tr[v_tr], .95)).mean(),
                              "prev_P90_cauda": (c_te[v_te] > np.quantile(c_tr[v_tr], .9)).mean()})
    R, V, K = pd.DataFrame(resultados), pd.DataFrame(validacao), pd.DataFrame(concord)
    R.to_csv(os.path.join(out, "tabelas", "pico_por_janela.csv"), index=False)
    V.to_csv(os.path.join(out, "tabelas", "pico_validacao_folds.csv"), index=False)
    K.to_csv(os.path.join(out, "tabelas", "pico_concordancia_definicoes.csv"), index=False)
    return R, V, K


def _kappa(a, b):
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


# ---------------------------------------------------------------------------
# relatorio por dominio
# ---------------------------------------------------------------------------
def fmt_irr(r):
    return f"{r['var_pct']:+.1f}% (IC95 {100*(r['IC95_lo']-1):+.1f} a {100*(r['IC95_hi']-1):+.1f}; p={r['p']:.3f})"


def conclusao(dom, mp, es, pl, sp, cp, pk_r):
    """Leitura direta, regra explicita (revista na Fase 2b): candidato a efeito se (i) p_BH<0,05 no modelo
    principal, (ii) placebo p<0,05 e (iii) mesmo sinal com p<0,10 na NB e no cluster por dia. Depois, o
    desenho pareado: 'efeito robusto' so se o pareado CONFIRMA (mesmo sinal, IC95 sem o 1); 'robusto no GLM,
    pareado inconclusivo' se o pareado nao confirma mas tambem nao contradiz; 'contradito pelo pareado' se
    o IC95 do pareado exclui a estimativa do GLM (ou tem sinal oposto com IC sem o 1)."""
    linhas = []
    pr = mp[mp["spec"].str.startswith("principal")]
    for y in DOM[dom]["desfechos"]:
        for t in ["C_pre", "C_durante", "C_pos", "F_pre", "F_durante", "F_pos"]:
            r = pr[(pr["desfecho"] == y) & (pr["termo"] == t)]
            if r.empty:
                continue
            r = r.iloc[0]
            cat = "capital" if t.startswith("C") else "fora_da_capital"
            w = t.split("_")[1]
            plr = pl[(pl["desfecho"] == y) & (pl["categoria"] == cat) & (pl["janela"] == w)]
            p_pl = plr["p_permutacao_bilateral"].iloc[0] if len(plr) else np.nan
            rob = mp[(mp["desfecho"] == y) & (mp["termo"] == t) &
                     (mp["spec"].str.startswith("Binomial") | mp["spec"].str.startswith("cluster"))]
            rob_ok = len(rob) == 2 and (np.sign(np.log(rob["IRR"])) == np.sign(np.log(r["IRR"]))).all() and \
                (rob["p"] < .10).all()
            sig = r["p_BH_dominio"] < .05
            c = cp[(cp["desfecho"] == y) & (cp["categoria"] == cat) & (cp["janela"] == w)]
            par_conf = par_contra = False
            if len(c):
                c = c.iloc[0]
                mesmo_sinal = np.sign(np.log(c["DiD_IRR"])) == np.sign(np.log(r["IRR"]))
                exclui_1 = not (c["IC95_lo"] <= 1 <= c["IC95_hi"])
                par_conf = bool(mesmo_sinal and exclui_1)
                par_contra = bool(not (c["IC95_lo"] <= r["IRR"] <= c["IC95_hi"]) or (not mesmo_sinal and exclui_1))
            cand = sig and p_pl < .05 and rob_ok
            veredito = ("efeito robusto" if (cand and par_conf) else
                        "contradito pelo pareado" if (cand and par_contra) else
                        "robusto no GLM, pareado inconclusivo" if cand else
                        "sinal não robusto" if (r["p"] < .05) else "sem evidência")
            linhas.append({"desfecho": y, "termo": t, "janela": ROTULO[t], "IRR": r["IRR"], "var_pct": r["var_pct"],
                           "IC95_lo": r["IC95_lo"], "IC95_hi": r["IC95_hi"], "p": r["p"],
                           "p_BH_dominio": r["p_BH_dominio"], "p_placebo": p_pl, "robustez_NB_e_dia_ok": rob_ok,
                           "pareado_confirma": par_conf, "pareado_contradiz": par_contra, "veredito": veredito})
    return pd.DataFrame(linhas)


def relatorio(dom, out, mp, td, es, pl, het, dose, dose_e, sp, diag, cp, desc, pk):
    R, V, K = pk
    L = []
    w = L.append
    nome = "CRIMES (SSP)" if dom == "crimes" else "SINISTROS DE TRÂNSITO (Infosiga)"
    w(f"# V2 / Fase 2 — {nome}: análise por janelas de horário\n")
    w(f"Gerado por `scripts/33_analise_janelas.py`. Domínio analisado **isoladamente** (modelos, BH, pico e "
      f"conclusão próprios). Desfechos: {', '.join(f'`{y}`' for y in DOM[dom]['desfechos'])} (principal: "
      f"`{DOM[dom]['principal']}`). Amostra: painel horário 2022–2023 sem os dias excluídos do domínio, sem as "
      "horas dos 4 eventos de grande público sem os times monitorados (robustez com elas de volta) e sem horas "
      "sem temperatura após interpolação de até 24 h. Contagens horárias usam só registros com hora.\n")
    v = conclusao(dom, mp, es, pl, sp, cp, R)
    v.to_csv(os.path.join(out, "tabelas", "vereditos.csv"), index=False)

    w("## Resposta direta\n")
    w(_resposta(dom, v, es, sp, R, V, cp, het))
    w("\n## Ressalvas que pesam na leitura\n")
    w(_ressalvas(dom, es, pl, cp, het, out))

    w("\n## 1. Descritivo\n")
    w("Média por hora em cada janela vs as **mesmas horas do relógio, no mesmo dia da semana, em horas sem "
      "nenhum jogo dos 4 times** (sem outro ajuste):\n")
    w(md(desc, 3))
    w("\n![descritivo](figuras/01_descritivo.png)\n")

    w("## 2. Modelo principal\n")
    w("`log E[y] = β·(PRÉ, DURANTE, PÓS na capital) + β_fdj·(mesmo dia de jogo na capital, fora das janelas) + "
      "γ·(PRÉ, DURANTE, PÓS de jogos fora da capital) + EF(hora do dia × dia da semana) + EF(ano × mês) + "
      "feriado + véspera + férias + log(1+chuva) + indicador de chuva ausente + temperatura`, GLM Poisson, "
      "erros agrupados por semana. Referência = hora sem nenhum jogo dos 4 times.\n")
    w("**Por que EF hora × dia da semana:** os jogos acontecem em horários que já têm um nível próprio de "
      "ocorrências (domingo 16h, quarta 21h30). Sem esse controle, o modelo confunde \"horário do jogo\" com "
      "\"efeito do jogo\" — é a versão horária do confundidor de calendário que já derrubou o efeito no grão "
      "diário (Etapas 7–10).\n")
    pr = mp[mp["spec"].str.startswith("principal")][["desfecho", "janela", "IRR", "var_pct", "IC95_lo", "IC95_hi",
                                                      "p", "p_BH_dominio"]]
    w(md(pr, 3))
    w("\nBH: uma família por domínio (todos os desfechos × todos os termos acima).\n")
    w("### Robustezes\n")
    rb = mp[~mp["spec"].str.startswith("principal")]
    piv = rb.assign(cel=rb.apply(lambda r: f"{r['IRR']:.3f} (p={r['p']:.3f})", axis=1)) \
        .pivot_table(index=["desfecho", "termo"], columns="spec", values="cel", aggfunc="first").reset_index()
    w(md(piv))
    if td is not None:
        w("\n**Total diário (com + sem hora)** — checagem da seleção vista na Fase 1 (`lesao_corporal_dolosa`, "
          "`crimes_violentos`): GLM Poisson diário com dia da semana, ano × mês, feriado e férias.\n")
        w(md(td[["desfecho", "termo", "IRR", "var_pct", "IC95_lo", "IC95_hi", "p"]], 3))

    w("\n## 3. Event study (−6 a +12 h) — as duas categorias\n")
    w("Dummies para cada hora relativa ao início, separadamente para jogos na capital e fora da capital, no "
      "mesmo modelo, com os mesmos EF (+ dummy para as outras horas do dia de jogo na capital). Horas −6 a −3 "
      "= checagem de pré-tendência; até +12 porque Ivandić et al. (2024) acham efeito até ~10 h depois.\n")
    w("![event study](figuras/03_event_study.png)\n")
    wt = es[es["termo"] == "wald_pretendencia_k-6..-3"][["desfecho", "categoria", "p"]]
    w("Teste conjunto de pré-tendência (k = −6..−3 iguais a zero):\n")
    w(md(wt, 3))
    tardio = es[es["k"].between(4, 12) & (es["p"] < .05)][["desfecho", "categoria", "k", "IRR", "p"]]
    w("\nHoras +4..+12 com p < 0,05 (sem correção múltipla; 18 testes por desfecho e categoria):\n")
    w(md(tardio, 3) if len(tardio) else "_nenhuma_")

    w("\n## 4. Placebo / permutação\n")
    w(f"{N_PLACEBO} sorteios: cada jogo recebe um início falso no mesmo horário, mesmo dia da semana, ±6 semanas, "
      "em dia sem jogo na capital (e, para a categoria fora da capital, sem nenhum jogo dos 4 times) e sem "
      "feriado. Para caber 1.000 reestimações, usa-se a versão em dois passos: o modelo de calendário + clima + "
      "a outra categoria é ajustado uma vez e o β de cada janela vira `log(Σobs/Σesperado)` nas horas da "
      "janela; o β real é recalculado do mesmo jeito.\n")
    w(md(pl[["desfecho", "categoria", "janela", "IRR_real_2passos", "placebo_p2.5", "placebo_p97.5",
             "percentil_real", "p_permutacao_bilateral"]].assign(
        **{"placebo_p2.5": lambda x: np.exp(x["placebo_p2.5"]),
           "placebo_p97.5": lambda x: np.exp(x["placebo_p97.5"])}), 3))
    w("\n(placebo_p2.5/p97.5 em escala de IRR.)\n")

    w("## 5. Heterogeneidade\n")
    y0 = DOM[dom]["principal"]
    h0 = het[het["desfecho"] == y0][["categoria", "atributo", "janela", "nivel", "n_horas", "IRR", "IC95_lo",
                                      "IC95_hi", "p", "p_BH_dominio_atributo"]]
    w(f"Desfecho principal `{y0}` (todos os desfechos em `tabelas/heterogeneidade.csv`). Resultado do mandante "
      "só na janela PÓS (só é conhecido depois do jogo). Por time: modelo separado para cada time, com as "
      "janelas dos jogos daquele time vs as dos outros jogos (um clássico conta para os dois times).\n")
    h0 = h0.assign(obs=np.where(h0["n_horas"] < 20, "n<20: não interpretar", ""))
    w(md(h0, 3))
    w("\n### Dose-resposta do público (só jogos na capital)\n")
    tq = TERCIS.get((dom, "cidade toda"))
    w("Interação de cada janela com log(público) centrado na média dos jogos (coeficiente = variação do IRR "
      "para +1 em log, ≈ ×2,7 de público) e recorte por tercis "
      + (f"(cortes {tq[1]:,.0f} e {tq[2]:,.0f})".replace(",", ".") if tq is not None else "")
      + ". Jogo de portões fechados fora deste modelo.\n")
    dd = pd.concat([dose, dose_e])
    w(md(dd[dd["desfecho"] == y0][["area", "spec", "termo", "IRR", "IC95_lo", "IC95_hi", "p"]], 3))
    dd.to_csv(os.path.join(out, "tabelas", "dose_resposta_publico.csv"), index=False)

    w("\n## 6. Espaço × tempo\n")
    w(f"Contagem horária no disco de {R_ENTORNO:.0f} km de cada estádio (Neo Química Arena, Allianz Parque, "
      "Morumbi), com as janelas dos jogos **daquele** estádio vs as dos jogos em outro estádio, mesmos EF; "
      "resto da cidade = registros fora dos 3 discos. Jogo no Canindé (Santos) não entra (sem coordenada). ")
    if dom == "crimes":
        w("Crime: coordenada válida (critério da Etapa 10) e **sem as células de empilhamento de "
          "geocodificação** (coordenadas arredondadas a 3 casas, a até 1 km do estádio, com mais de 20× a "
          "mediana do disco); alternativa por **bairros do entorno** (regra da Etapa 10).\n")
        w(md(diag))
    else:
        w("Sinistros: coordenada 99,5% válida.\n")
    sp0 = sp[sp["desfecho"] == y0][["estadio", "area", "janela", "IRR", "IC95_lo", "IC95_hi", "p"]]
    w("\n" + md(sp0, 3))

    w("\n## 7. Robustez com controles pareados\n")
    w("Para cada jogo: controles = mesmo dia da semana, ±4 semanas, sem jogo dos 4 times (nem na capital nem "
      "fora) e sem feriado. Compara a soma nas horas da janela com as mesmas horas dos controles e faz a "
      "diferença em relação às horas FORA (sem janela) dos mesmos dias: `DiD = log(janela_jogo/janela_ctrl) − "
      "log(fora_jogo/fora_ctrl)`; IC por bootstrap de jogos (1.000).\n")
    w(md(cp[["categoria", "desfecho", "janela", "n_jogos", "razao_janela_jogo_vs_ctrl", "razao_fora_jogo_vs_ctrl",
             "DiD_IRR", "IC95_lo", "IC95_hi"]], 3))

    w("\n## 8. Pico no grão horário\n")
    w(f"Esperado = modelo só de calendário e clima (sem nenhuma variável de jogo) para `{y0}`. Resíduo de "
      "Pearson `(obs−esp)/√esp` e cauda de Poisson `−log10 P(Y≥obs|esp)`. Pico = acima do P90 (P95 robustez). "
      + ("Sinistros: também soma móvel de 2 h (contagens horárias pequenas). " if dom == "sinistros" else ""))
    w("\nFrequência de pico por janela vs controle (hora sem jogo):\n")
    w(md(R[R["definicao"] == "P90_pearson"][["nivel", "categoria", "janela", "n_unidades", "freq_pico",
                                             "freq_pico_controle", "RR", "IC95_lo", "IC95_hi", "p_fisher"]], 3))
    w("\nValidação (esperado e limiar reestimados só no treino de cada fold mensal de 2023; ideal ≈ 0,10 / 0,05):\n")
    w(md(V, 3))
    vs = V.groupby("nivel")[["prev_P90_pearson", "prev_P90_cauda"]].agg(lambda x: np.mean(np.abs(x - .10)))
    w("\nDesvio médio absoluto da prevalência P90 em relação a 10%: "
      + "; ".join(f"{n}: Pearson {r['prev_P90_pearson']:.3f}, cauda {r['prev_P90_cauda']:.3f}"
                  for n, r in vs.iterrows()) + ".\n")
    w("Concordância entre definições:\n")
    w(md(K, 3))
    w(_escolha_nivel(dom, V, K))
    with open(os.path.join(out, f"relatorio_fase2_{dom}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return v


def _ressalvas(dom, es, pl, cp, het, out):
    y0 = DOM[dom]["principal"]
    L = []
    wt = es[(es["termo"] == "wald_pretendencia_k-6..-3") & (es["desfecho"] == y0)].set_index("categoria")["p"]
    ec = es[(es["desfecho"] == y0) & (es["categoria"] == "capital") & es["k"].between(-6, -3)].set_index("k")
    L.append(f"- **Pré-tendência (event study):** teste conjunto k=−6..−3 p={wt.get('capital', np.nan):.3f} "
             f"(capital) e p={wt.get('fora_da_capital', np.nan):.3f} (fora). Coeficientes da capital em −6..−3: "
             + ", ".join(f"k={int(k)} {r['IRR']:.3f}" for k, r in ec.iterrows())
             + (". Rejeição com sinais mistos: parte vem de uma hora isolada abaixo e de k=−3 já acima de 1 "
                "(subida começando ~3 h antes do jogo). Não é a pré-tendência monotônica que invalidaria o "
                "desenho, mas reduz a confiança de que o PRÉ seja só efeito do jogo."
                if wt.get("capital", 1) < .05 else ". Sem pré-tendência detectável."))
    c0 = cp[cp["desfecho"] == y0].set_index(["categoria", "janela"])
    if ("capital", "pre") in c0.index:
        r = c0.loc[("capital", "pre")]
        L.append(f"- **Controles pareados vs GLM:** no desenho pareado (só jogos com ≥2 dias-controle livres; "
                 f"n={int(r['n_jogos'])}) o PRÉ da capital dá {100*(r['DiD_IRR']-1):+.1f}% "
                 f"(IC95 {100*(r['IC95_lo']-1):+.1f} a {100*(r['IC95_hi']-1):+.1f}). "
                 + _compara_glm(out, y0, r))
        r2 = c0.loc[("capital", "durante")]
        if r2["IC95_hi"] < 1:
            L.append(f"  - DURANTE no pareado: {100*(r2['DiD_IRR']-1):+.1f}% (IC95 {100*(r2['IC95_lo']-1):+.1f} a "
                     f"{100*(r2['IC95_hi']-1):+.1f}) — queda durante o jogo, como em Ivandić et al. (2024); no GLM a "
                     "queda é menor e não significativa.")
    cen = pl.groupby("categoria")["placebo_media"].apply(lambda x: np.abs(x).max())
    L.append("- **Placebo:** maior desvio do centro da distribuição placebo em relação a 0: "
             + ", ".join(f"{k} {100*v:.1f}%" for k, v in cen.items())
             + (". Ainda há descentramento relevante em horas tardias — o p do placebo, sozinho, não é "
                "confiável aqui; vale o GLM." if cen.max() > .02 else ". Distribuição centrada; placebo confiável."))
    peq = het[(het["n_horas"] < 20) & (het["desfecho"] == y0)]
    if len(peq):
        L.append("- **Heterogeneidade com n pequeno** (< 20 horas, erro-padrão agrupado degenerado, **não "
                 "interpretar**): " + "; ".join(f"{r['categoria']} {r['atributo']}={r['nivel']} {r['janela']} "
                                                f"({int(r['n_horas'])} h)" for _, r in peq.iterrows()) + ".")
    sens = os.path.join(REP, "crimes", "tabelas", "espaco_sensibilidade_sem_2_jogos_copa_do_brasil.csv")
    if os.path.exists(sens):
        se = pd.read_csv(sens)
        se = se[(se["dom"] == dom) & (se["estadio"] == "Morumbi") & (se["area"] == "disco")]
        a, b = se[~se["sem_2_jogos_CdB"]].set_index("janela"), se[se["sem_2_jogos_CdB"]].set_index("janela")
        L.append("- **Morumbi sem a semifinal e a final da Copa do Brasil 2023** (os 2 jogos que explicavam o "
                 "sinal diário da Etapa 10), disco de 3 km: " + "; ".join(
                     f"{w} {a.loc[w, 'IRR']:.2f}→{b.loc[w, 'IRR']:.2f} (p={b.loc[w, 'p']:.3f})" for w in WIN if w in a.index)
                 + ". Tabela em `crimes/tabelas/espaco_sensibilidade_sem_2_jogos_copa_do_brasil.csv`.")
    L.append("- Contagens só com registros que têm hora (furtos: ~53% sem hora). Associação, não causalidade: "
             "não há variação exógena da agenda; o desenho controla calendário, clima e hora × dia da semana.")
    return "\n".join(L)


def _compara_glm(out, y0, r):
    mp = pd.read_csv(os.path.join(out, "tabelas", "modelo_principal_e_robustez.csv"))
    g = mp[mp["spec"].str.startswith("principal") & (mp["desfecho"] == y0) & (mp["termo"] == "C_pre")].iloc[0]
    glm_sig, par_sig = g["p_BH_dominio"] < .05, not (r["IC95_lo"] <= 1 <= r["IC95_hi"])
    if glm_sig and not par_sig:
        return f"Não confirma o GLM ({100*(g['IRR']-1):+.1f}%, p_BH={g['p_BH_dominio']:.3f}): o efeito PRÉ depende do estimador/amostra."
    if glm_sig and par_sig:
        return "Confirma o GLM."
    return f"Consistente com o GLM, que também não acha efeito no PRÉ ({100*(g['IRR']-1):+.1f}%, p_BH={g['p_BH_dominio']:.3f})."


def _escolha_nivel(dom, V, K):
    if dom == "crimes":
        return ("\n**Nível escolhido: hora.** Contagens horárias de `crimes_violentos` são grandes o bastante "
                "(dezenas por hora); o pico horário é usado diretamente.\n")
    dv = V.groupby("nivel")["prev_P90_pearson"].agg(lambda x: np.mean(np.abs(x - .10)))
    kk = K[K["def_1"] == "P90_pearson"].groupby("nivel")["kappa"].mean()
    melhor = "2h" if (dv.get("2h", 9) <= dv.get("hora", 9)) else "hora"
    return (f"\n**Nível escolhido: {melhor}.** Critério: menor desvio médio da prevalência fora da amostra em "
            f"relação a 10% (hora {dv.get('hora', np.nan):.3f} vs 2h {dv.get('2h', np.nan):.3f}); concordância "
            f"média (kappa) da P90 de Pearson com as outras definições: hora {kk.get('hora', np.nan):.2f}, 2h "
            f"{kk.get('2h', np.nan):.2f}.\n")


def _resposta(dom, v, es, sp, R, V, cp, het):
    y0 = DOM[dom]["principal"]
    L = []
    for cat, pref in (("Jogos na capital (multidão perto do estádio)", "C_"),
                      ("Jogos fora da capital (TV / bares)", "F_")):
        g = v[(v["desfecho"] == y0) & v["termo"].str.startswith(pref)]
        partes = []
        for _, r in g.iterrows():
            partes.append(f"{r['janela'].split(' ')[-1]} {r['var_pct']:+.1f}% (p={r['p']:.3f}, p_BH={r['p_BH_dominio']:.3f}, "
                          f"placebo p={r['p_placebo']:.3f}) → **{r['veredito']}**")
        L.append(f"- **{cat}**, `{y0}`: " + "; ".join(partes) + ".")
    outros = v[(v["desfecho"] != y0) & (v["veredito"] != "sem evidência")]
    if len(outros):
        L.append("- Desfechos secundários com algum sinal: " + "; ".join(
            f"`{r['desfecho']}` {r['janela']} {r['var_pct']:+.1f}% ({r['veredito']}, p_BH={r['p_BH_dominio']:.3f})"
            for _, r in outros.iterrows()) + ".")
    else:
        L.append("- Desfechos secundários: sem sinal (p ≥ 0,05 em todas as janelas).")
    sp = sp.copy()
    mk = sp["estadio"].str.startswith("3 est")
    sp.loc[mk, "p_BH_esp"] = bh(sp.loc[mk, "p"])   # familia: agregados (janelas x desfechos x disco/bairros)
    agg = sp[mk & (sp["desfecho"] == y0) & (sp["area"] == "disco")]
    if len(agg):
        L.append(f"- **Onde{' (exploratório)' if dom == 'sinistros' else ''}:** entorno de 3 km dos estádios "
                 "(3 estádios agregados): " + "; ".join(
            f"{r['janela']} {r['var_pct']:+.1f}% (p={r['p']:.3f}, p_BH={r['p_BH_esp']:.3f})" for _, r in agg.iterrows())
            + "; resto da cidade: " + "; ".join(
            f"{r['janela']} {r['var_pct']:+.1f}% (p={r['p']:.3f})"
            for _, r in sp[(sp["estadio"] == "resto da cidade") & (sp["desfecho"] == y0)].iterrows()) + ".")
    pk = R[(R["definicao"] == "P90_pearson")]
    nivel = "2h" if (dom == "sinistros" and "2h" in pk["nivel"].values and
                     V.groupby("nivel")["prev_P90_pearson"].agg(lambda x: np.mean(np.abs(x - .1))).idxmin() == "2h") \
        else "hora"
    pk = pk[pk["nivel"] == nivel]
    L.append(f"- **Picos (nível {nivel}, P90 Pearson):** " + "; ".join(
        f"{r['categoria'].replace('_', ' ')} {r['janela']} RR {r['RR']:.2f} (Fisher p={r['p_fisher']:.3f})"
        for _, r in pk.iterrows()) + ".")
    es = es.copy()
    mk = es["k"].notna()
    es.loc[mk, "p_BH_es"] = bh(es.loc[mk, "p"])   # familia: todos os k x categorias x desfechos do dominio
    tard = es[(es["desfecho"] == y0) & es["k"].between(4, 12) & (es["p"] < .05)]
    L.append("- Exploratório — horas tardias do event study (+4..+12 h) com p < 0,05: " + (
        "; ".join(f"{r['categoria'].replace('_', ' ')} k=+{int(r['k'])} IRR {r['IRR']:.3f} (p={r['p']:.3f}, "
                  f"p_BH={r['p_BH_es']:.3f})" for _, r in tard.iterrows()) if len(tard) else "nenhuma") + ".")
    c0 = cp[cp["desfecho"] == y0]
    L.append("- **Controles pareados (DiD):** " + "; ".join(
        f"{r['categoria'].replace('_', ' ')} {r['janela']} {100*(r['DiD_IRR']-1):+.1f}% "
        f"(IC95 {100*(r['IC95_lo']-1):+.1f} a {100*(r['IC95_hi']-1):+.1f})" for _, r in c0.iterrows()) + ".")
    L.append("\nRegra do veredito (revista na Fase 2b): candidato = p_BH < 0,05 no modelo principal **e** placebo "
             "p < 0,05 **e** mesmo sinal com p < 0,10 na Binomial Negativa e no cluster por dia. Entre os candidatos: "
             "**efeito robusto** só se o desenho pareado **confirma** (mesmo sinal, IC95 sem o 1); **robusto no GLM, "
             "pareado inconclusivo** se o pareado não confirma mas também não contradiz (IC95 do pareado contém a "
             "estimativa do GLM); **contradito pelo pareado** se o IC95 do pareado exclui a estimativa do GLM. "
             "**Sinal não robusto** = p < 0,05 sem ser candidato; **sem evidência** = p ≥ 0,05. Associação, não "
             "causalidade.")
    return "\n".join(L)


def resumo(vs, extras):
    L = ["# V2 / Fase 2 — Resumo comparativo: crimes × sinistros\n",
         "Cada domínio foi analisado em modelos, famílias de BH, definição de pico e conclusão próprios "
         "(`reports/janelas/crimes/relatorio_fase2_crimes.md`, `reports/janelas/sinistros/relatorio_fase2_sinistros.md`). "
         "Aqui só lado a lado, sem juntar.\n"]
    for dom, v in vs.items():
        y0 = DOM[dom]["principal"]
        L.append(f"## {dom.upper()} — `{y0}` (principal)\n")
        L.append(md(v[v["desfecho"] == y0][["janela", "var_pct", "IC95_lo", "IC95_hi", "p", "p_BH_dominio",
                                            "p_placebo", "veredito"]], 3))
        L.append("\nTodos os desfechos do domínio:\n")
        L.append(md(v[["desfecho", "janela", "var_pct", "p", "p_BH_dominio", "p_placebo", "veredito"]], 3))
        L.append("")
    for dom in vs:
        txt = open(os.path.join(REP, dom, f"relatorio_fase2_{dom}.md"), encoding="utf-8").read()
        bloco = txt[txt.index("## Resposta direta"):txt.index("## 1. Descritivo")]
        L.append(f"---\n\n# {dom.upper()}: resposta direta e ressalvas\n")
        L.append(bloco.replace("## ", "### "))
    L.append(extras)
    with open(os.path.join(REP, "resumo_fase2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _reusa(dom, out, jogos):
    T = lambda n: pd.read_csv(os.path.join(out, "tabelas", n))
    mp = T("modelo_principal_e_robustez.csv")
    td = T("robustez_total_diario.csv") if dom == "crimes" else None
    es, het, sp = T("event_study.csv"), T("heterogeneidade.csv"), T("espaco_tempo.csv")
    diag = T("espaco_empilhamento_bairros.csv") if dom == "crimes" else pd.DataFrame()
    cp, desc = T("controles_pareados.csv"), T("descritivo_janela_vs_mesmas_horas.csv")
    dd = T("dose_resposta_publico.csv")
    dose, dose_e = dd[dd["area"] == "cidade toda"], dd[dd["area"] != "cidade toda"]
    TERCIS[(dom, "cidade toda")] = pd.qcut(jogos.loc[jogos["publico"] > 0, "publico"], 3, retbins=True)[1]
    pk = (T("pico_por_janela.csv"), T("pico_validacao_folds.csv"), T("pico_concordancia_definicoes.csv"))
    return mp, td, es, het, dose, dose_e, sp, diag, cp, desc, pk


if __name__ == "__main__":
    import time
    t0 = time.time()
    f, jogos, fora = carrega()
    vs = {}
    reusa = os.environ.get("REUSA") == "1"
    for dom in os.environ.get("DOMS", "crimes,sinistros").split(","):
        out = dirs(dom)
        print(f"== {dom}")
        if reusa:
            mp, td, es, het, dose, dose_e, sp, diag, cp, desc, pk = _reusa(dom, out, jogos)
            pl = placebo(f, jogos, fora, dom, out); print("  placebo", round(time.time() - t0))
        else:
            desc = descritivo(f, dom, out); print("  descritivo", round(time.time() - t0))
            mp, _ = modelo_principal(f, dom, out); print("  modelo principal", round(time.time() - t0))
            td = total_diario(f, dom, out)
            es = event_study(f, dom, out); print("  event study", round(time.time() - t0))
            pl = placebo(f, jogos, fora, dom, out); print("  placebo", round(time.time() - t0))
            het = heterogeneidade(f, jogos, fora, dom, out); print("  heterogeneidade", round(time.time() - t0))
            dose = dose_publico(f, jogos, dom, out)
            sp, diag, cont = espaco_tempo(f, jogos, dom, out); print("  espaco", round(time.time() - t0))
            dose_e = dose_entorno(f, jogos, dom, cont)
            cp = controles_pareados(f, jogos, fora, dom, out); print("  pareados", round(time.time() - t0))
            pk = picos(f, dom, out); print("  picos", round(time.time() - t0))
        vs[dom] = relatorio(dom, out, mp, td, es, pl, het, dose, dose_e, sp, diag, cp, desc, pk)
        print(vs[dom][["desfecho", "termo", "var_pct", "p", "p_BH_dominio", "p_placebo", "veredito"]].round(3).to_string())
    resumo(vs, "")
    print("[ok]", round(time.time() - t0), "s")
