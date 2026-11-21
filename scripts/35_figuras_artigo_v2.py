"""
V2 -- 35_figuras_artigo_v2.py
Figuras, tabelas LaTeX e lista de numeros do artigo (3a entrega) gerados SO a partir das tabelas ja
publicadas em reports/janelas/ e data/ (nada estimado aqui). Saidas na pasta do artigo:
  ../entrega_parcial/entrega3/fig_event_study.png, fig_entorno.png
  ../entrega_parcial/entrega3/tab_janelas.tex, tab_pre.tex, tab_canal.tex, tab_preditivo.tex, tab_risco.tex,
  tab_pico.tex (V3)
  reports/janelas/artigo/numeros_artigo.csv   (chave, valor, fonte) -- todo numero citado no texto
Rodar:  python scripts/35_figuras_artigo_v2.py
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(BASE, "reports", "janelas")
REV = os.path.join(REP, "revisao")
# V4 (2026-11-20): o artigo oficial passou a ser ../entrega_parcial/rp_ii/ (escrito por um colega e revisado
# pelo parecer). ARTIGO=entrega3 regenera a 3a entrega como estava (numeros em numeros_artigo_entrega3.csv).
ARTIGO = os.environ.get("ARTIGO", "rp_ii")
ART = os.path.abspath(os.path.join(BASE, "..", "entrega_parcial", ARTIGO))
NUM_DIR = os.path.join(REP, "artigo")
NUM_FILE = "numeros_artigo.csv" if ARTIGO == "rp_ii" else "numeros_artigo_entrega3.csv"
os.makedirs(NUM_DIR, exist_ok=True)
assert os.path.isdir(ART), ART
NUMS = []
EST = ["Neo Quimica Arena", "Allianz Parque", "Morumbi"]
EST_TEX = {"Neo Quimica Arena": "Neo Química Arena", "Allianz Parque": "Allianz Parque", "Morumbi": "Morumbi"}
JAN_TEX = {"pre": "PRÉ", "durante": "DURANTE", "pos": "PÓS"}


def T(dom, nome):
    return pd.read_csv(os.path.join(REP, dom, "tabelas", nome))


def br(x, nd=1, sinal=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    s = f"{x:+.{nd}f}" if sinal else f"{x:.{nd}f}"
    s = s.replace(".", ",")
    return s.replace("-", "$-$") if s.startswith("-") or "-" in s[:1] else s


def num(chave, valor, fonte, nd=1, sinal=False, pct=False):
    v = 100 * (valor - 1) if pct else valor
    NUMS.append({"chave": chave, "valor": br(v, nd, sinal), "valor_bruto": valor, "fonte": fonte})
    return br(v, nd, sinal)


def pfmt(p):
    return "$<$0,001" if p < 0.001 else br(p, 3)


def grava(nome, txt):
    with open(os.path.join(ART, nome), "w", encoding="utf-8") as fh:
        fh.write(txt)


# ---------------------------------------------------------------------------
def tab_janelas():
    """Tabela principal: variacao % por janela (cidade toda), dois tipos de jogo, com veredito."""
    linhas = []
    nomes = {"crimes_violentos": "Crimes violentos", "lesao_corporal_dolosa": "Lesão corporal dolosa",
             "roubos_total": "Roubos", "furtos_total": "Furtos", "acidentes_com_vitima": "Sinistros com vítima",
             "acidentes_total": "Sinistros totais", "atropelamentos": "Atropelamentos"}
    marca = {"efeito robusto": "$^{\\ddagger}$", "robusto no GLM, pareado inconclusivo": "$^{\\dagger}$",
             "contradito pelo pareado": "$^{\\S}$", "sinal não robusto": "$^{*}$", "sem evidência": ""}
    for dom in ("crimes", "sinistros"):
        v = T(dom, "vereditos.csv")
        if dom == "sinistros":
            linhas.append("\\midrule")
        for y in v["desfecho"].unique():
            cel = []
            for t in ("C_pre", "C_durante", "C_pos", "F_pre", "F_durante", "F_pos"):
                r = v[(v["desfecho"] == y) & (v["termo"] == t)].iloc[0]
                cel.append(br(r["var_pct"], 1, True) + marca.get(r["veredito"], ""))
                num(f"{dom}.{y}.{t}.var_pct", r["var_pct"], f"{dom}/tabelas/vereditos.csv", 1, True)
                num(f"{dom}.{y}.{t}.p_BH", r["p_BH_dominio"], f"{dom}/tabelas/vereditos.csv", 3)
                num(f"{dom}.{y}.{t}.IC_lo", 100 * (r["IC95_lo"] - 1), f"{dom}/tabelas/vereditos.csv", 1, True)
                num(f"{dom}.{y}.{t}.IC_hi", 100 * (r["IC95_hi"] - 1), f"{dom}/tabelas/vereditos.csv", 1, True)
            linhas.append(f"{nomes[y]} & " + " & ".join(cel) + " \\\\")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Variação (\%) das ocorrências por hora em cada janela, na cidade toda, em relação às horas sem nenhum jogo dos quatro times (GLM Poisson com efeito fixo hora $\times$ dia da semana e ano $\times$ mês; 2022--2023). $^{\ddagger}$efeito robusto; $^{\dagger}$robusto no GLM, pareado inconclusivo; $^{*}$sinal não robusto ($p<0{,}05$ sem cumprir a regra); sem marca: $p \geq 0{,}05$}
\label{tab:janelas}
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
 & \multicolumn{3}{c}{\textbf{Jogos na capital}} & \multicolumn{3}{c}{\textbf{Jogos fora da capital}} \\
\cmidrule(lr){2-4} \cmidrule(l){5-7}
\textbf{Desfecho} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_janelas.tex", txt)


def tab_pre():
    p = T("crimes", "fase2b_pre_checagens.csv")
    specs = [("principal", "C_pre", "Modelo principal"), ("+ EF hora×mês", "C_pre", "+ efeito fixo hora $\\times$ mês"),
             ("+ EF hora×trimestre", "C_pre", "+ efeito fixo hora $\\times$ trimestre"),
             ("só jogos do pareado", "C_pre", "Só os jogos do desenho pareado"),
             ("só jogos do pareado + EF hora×mês", "C_pre", "Jogos do pareado + hora $\\times$ mês"),
             ("PRÉ estendido + EF hora×mês", "C_pre_ext", "PRÉ estendido ($-3$ a $-1$ h) + hora $\\times$ mês")]
    cp = T("crimes", "controles_pareados.csv")
    linhas = []
    for spec, termo, rot in specs:
        cel = []
        for y in ("crimes_violentos", "roubos_total"):
            r = p[(p["spec"] == spec) & (p["termo"] == termo) & (p["desfecho"] == y)].iloc[0]
            cel.append(f"{br(r['var_pct'], 1, True)} ({pfmt(r['p'])})")
            num(f"pre.{y}.{spec}", r["var_pct"], "crimes/tabelas/fase2b_pre_checagens.csv", 1, True)
            num(f"pre.{y}.{spec}.p", r["p"], "crimes/tabelas/fase2b_pre_checagens.csv", 3)
        linhas.append(f"{rot} & " + " & ".join(cel) + " \\\\")
    cel = []
    for y in ("crimes_violentos", "roubos_total"):
        r = cp[(cp["categoria"] == "capital") & (cp["desfecho"] == y) & (cp["janela"] == "pre")].iloc[0]
        cel.append(f"{br(100*(r['DiD_IRR']-1), 1, True)} ({br(100*(r['IC95_lo']-1), 1, True)} a "
                   f"{br(100*(r['IC95_hi']-1), 1, True)})")
        num(f"pre.{y}.pareado", 100 * (r["DiD_IRR"] - 1), "crimes/tabelas/controles_pareados.csv", 1, True)
    linhas.append("Desenho pareado (DiD; IC 95\\%) & " + " & ".join(cel) + " \\\\")
    n_par = int(p["n_jogos_capital"].dropna().iloc[0])
    num("pre.n_jogos_pareado", n_par, "crimes/tabelas/fase2b_pre_checagens.csv", 0)
    txt = r"""\begin{table}[!htbp]
\centering
\caption{PRÉ dos jogos na capital (cidade toda): variação (\%) e $p$ em especificações alternativas}
\label{tab:pre}
\footnotesize
\begin{tabular}{@{}lrr@{}}
\toprule
\textbf{Especificação} & \textbf{Crimes violentos} & \textbf{Roubos} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_pre.tex", txt)


def tab_canal():
    c = T("crimes", "fase3_canal_modelos.csv")
    a = c[c["estadio"] == "3 estádios"]
    versoes = [("original", "Todos"), ("só presencial (sem Delegacia Eletrônica)", "Só presencial"),
               ("só BO online (Delegacia Eletrônica)", "Só BO online"), ("sem conduta nula", "Sem conduta nula")]
    linhas = []
    for y, rot in (("furtos_total", "Furtos"), ("roubos_total", "Roubos"), ("crimes_violentos", "Crimes violentos")):
        for w in ("durante", "pos"):
            cel = []
            for v, _ in versoes:
                r = a[(a["versao"] == v) & (a["desfecho"] == y) & (a["janela"] == w)].iloc[0]
                s = br(100 * (r["IRR"] - 1), 0, True) + ("$^{*}$" if r["p"] < 0.05 else "")
                cel.append(s)
                num(f"canal.{y}.{w}.{v}", 100 * (r["IRR"] - 1), "crimes/tabelas/fase3_canal_modelos.csv", 0, True)
                num(f"canal.{y}.{w}.{v}.p", r["p"], "crimes/tabelas/fase3_canal_modelos.csv", 3)
            linhas.append(f"{rot if w == 'durante' else ''} & {JAN_TEX[w]} & " + " & ".join(cel) + " \\\\")
    diag = T("crimes", "fase3_canal_diagnostico.csv")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Entorno de 3 km (três estádios agregados): variação (\%) por canal de registro do boletim. $^{*}p<0{,}05$}
\label{tab:canal}
\footnotesize
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Desfecho} & \textbf{Janela} & """ + " & ".join(f"\\textbf{{{r}}}" for _, r in versoes) + r""" \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_canal.tex", txt)


def tab_preditivo():
    blocos = [("crimes", "cidade", "crimes_violentos", "Cidade", "Crimes violentos"),
              ("crimes", "entorno", "crimes_violentos", "Entorno", "Crimes violentos"),
              ("crimes", "entorno", "roubos_total", "Entorno", "Roubos"),
              ("crimes", "entorno", "furtos_total", "Entorno", "Furtos"),
              ("sinistros", "cidade", "acidentes_com_vitima", "Cidade", "Sinistros com vítima"),
              ("sinistros", "entorno", "acidentes_com_vitima", "Entorno", "Sinistros com vítima")]
    linhas = []
    for dom, esc, y, re_, ry in blocos:
        g = T(dom, f"fase3_desempenho_{esc}_{y}.csv").set_index(["modelo", "variante"])
        ab = T(dom, f"fase3_ablacao_{esc}_{y}.csv").set_index(["modelo", "subconjunto"])
        pk = T(dom, f"fase3_pico_{esc}_{y}.csv").set_index(["modelo", "variante"])

        def dev(mod):
            return br(g.loc[(mod, "com_jogo"), "deviance_media"], 3) if (mod, "com_jogo") in g.index else "--"

        def ganho(mod, sub):
            if (mod, sub) not in ab.index:
                return "--"
            r = ab.loc[(mod, sub)]
            num(f"pred.{esc}.{y}.{mod}.{sub}.ganho_dev_pct", r["ganho_dev_pct"],
                f"{dom}/tabelas/fase3_ablacao_{esc}_{y}.csv", 1, True)
            sig = "$^{*}$" if r["ganho_dev_IC_lo"] > 0 else ("$^{-}$" if r["ganho_dev_IC_hi"] < 0 else "")
            return br(r["ganho_dev_pct"], 1, True) + sig
        for mod in ("XGBoost", "Prophet", "GLM"):
            if (mod, "com_jogo") in g.index:
                num(f"pred.{esc}.{y}.{mod}.deviance", g.loc[(mod, "com_jogo"), "deviance_media"],
                    f"{dom}/tabelas/fase3_desempenho_{esc}_{y}.csv", 3)
        num(f"pred.{esc}.{y}.baseline.MAE", g.loc[("baseline", "sem_jogo"), "MAE"],
            f"{dom}/tabelas/fase3_desempenho_{esc}_{y}.csv", 3)
        num(f"pred.{esc}.{y}.XGBoost.MAE", g.loc[("XGBoost", "com_jogo"), "MAE"],
            f"{dom}/tabelas/fase3_desempenho_{esc}_{y}.csv", 3)
        prc, prs = pk.loc[("XGBoost", "com_jogo"), "PR_AUC_fold_macro"], pk.loc[("XGBoost", "sem_jogo"), "PR_AUC_fold_macro"]
        prev = pk.loc[("XGBoost", "com_jogo"), "prevalencia_teste"]
        num(f"pred.{esc}.{y}.prauc_com", prc, f"{dom}/tabelas/fase3_pico_{esc}_{y}.csv", 3)
        num(f"pred.{esc}.{y}.prauc_sem", prs, f"{dom}/tabelas/fase3_pico_{esc}_{y}.csv", 3)
        num(f"pred.{esc}.{y}.prev", prev, f"{dom}/tabelas/fase3_pico_{esc}_{y}.csv", 3)
        linhas.append(f"{re_} & {ry} & {dev('XGBoost')} & {dev('Prophet')} & {dev('GLM')} & "
                      f"{ganho('XGBoost', 'todas as horas')} & {ganho('XGBoost', 'horas PRÉ/DURANTE/PÓS na capital')} & "
                      f"{ganho('GLM', 'horas PRÉ/DURANTE/PÓS na capital')} & {ganho('Prophet', 'horas PRÉ/DURANTE/PÓS na capital')} & "
                      f"{br(prc, 3)} / {br(prs, 3)} ({br(prev, 3)}) \\\\")
        if esc == "entorno" and y == "furtos_total":
            linhas.append("\\midrule")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Bloco preditivo (\textit{walk-forward}, 12 meses de 2023): deviance de Poisson média dos modelos com as variáveis de jogo e ganho (\%) da ablação = redução da deviance ao incluir as variáveis de jogo, no geral e só nas horas PRÉ/DURANTE/PÓS na capital. $^{*}$IC 95\% por \textit{bootstrap} em blocos de semana exclui 0 a favor do jogo; $^{-}$exclui 0 contra. Última coluna: PR-AUC (média por \textit{fold}) do XGBoost com/sem jogo e, entre parênteses, a prevalência de pico}
\label{tab:preditivo}
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}llrrrrrrrr@{}}
\toprule
 & & \multicolumn{3}{c}{\textbf{Deviance (com jogo)}} & \multicolumn{4}{c}{\textbf{Ganho da ablação (\%)}} & \\
\cmidrule(lr){3-5} \cmidrule(lr){6-9}
\textbf{Escala} & \textbf{Alvo} & \textbf{XGB} & \textbf{Prophet} & \textbf{GLM} & \textbf{XGB geral} & \textbf{XGB jan.} & \textbf{GLM jan.} & \textbf{Prophet jan.} & \textbf{PR-AUC} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_preditivo.tex", txt)


def tab_risco():
    r = T("crimes", "fase3_tabela_risco_estadio_janela.csv")
    q = pd.read_csv(os.path.join(BASE, "data", "silver", "qualidade_hora.csv"))
    sem = q[(q["tipo"] == "furtos_total") & (q["recorte"] == "todos")]["pct_sem_hora"].iloc[0] / 100
    fator = 1 / (1 - sem)
    num("furtos.pct_sem_hora", 100 * sem, "data/silver/qualidade_hora.csv", 1)
    num("furtos.fator_correcao", fator, "data/silver/qualidade_hora.csv", 2)
    slot = "quarta 21h30"
    linhas = []
    for s in EST:
        for w in ("pre", "durante", "pos"):
            cel = []
            for y in ("crimes_violentos", "roubos_total", "furtos_total"):
                x = r[(r["estadio"] == s) & (r["janela"] == w) & (r["desfecho"] == y) & (r["jogo_tipico"] == slot)].iloc[0]
                rel = br(100 * (x["IRR"] - 1), 0, True) + ("$^{*}$" if x["p"] < 0.05 else "")
                cel += [rel, br(x["excesso_2h"], 2, True)]
                num(f"risco.{s}.{w}.{y}.excesso", x["excesso_2h"], "crimes/tabelas/fase3_tabela_risco_estadio_janela.csv", 2, True)
                num(f"risco.{s}.{w}.{y}.rel", 100 * (x["IRR"] - 1), "crimes/tabelas/fase3_tabela_risco_estadio_janela.csv", 0, True)
                num(f"risco.{s}.{w}.{y}.base", x["esperado_sem_jogo_2h"], "crimes/tabelas/fase3_tabela_risco_estadio_janela.csv", 2)
                if y == "furtos_total":
                    cel.append(br(x["excesso_2h"] * fator, 2, True))
            linhas.append(f"{EST_TEX[s] if w == 'pre' else ''} & {JAN_TEX[w]} & " + " & ".join(cel) + " \\\\")
        if s != EST[-1]:
            linhas.append("\\midrule")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Risco esperado no entorno de 3 km de cada estádio para um jogo típico (quarta-feira, 21h30): efeito relativo (\%) e excesso absoluto de ocorrências nas 2 horas da janela. $^{*}p<0{,}05$. Furtos corrigidos: excesso multiplicado por """ + br(fator, 2) + r""", supondo que os """ + br(100 * sem, 0) + r"""\% de furtos sem hora se distribuem pelas horas como os com hora}
\label{tab:risco}
\footnotesize
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{@{}llrrrrrrr@{}}
\toprule
 & & \multicolumn{2}{c}{\textbf{Crimes violentos}} & \multicolumn{2}{c}{\textbf{Roubos}} & \multicolumn{3}{c}{\textbf{Furtos}} \\
\cmidrule(lr){3-4} \cmidrule(lr){5-6} \cmidrule(l){7-9}
\textbf{Estádio} & \textbf{Janela} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Abs. corr.} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_risco.tex", txt)


def bh(p):
    """Benjamini-Hochberg (transformacao deterministica dos p ja publicados, nada reestimado)."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    o = np.argsort(p)
    adj = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(adj, 1)
    return out


def tab_pico():
    """V3: validacao do pico e frequencia de pico por janela, crimes e sinistros em blocos separados
    (nunca somados). Fontes: {dom}/tabelas/pico_validacao_folds.csv, pico_concordancia_definicoes.csv,
    pico_por_janela.csv (Fase 2). Chamada depois de numeros_extras() para nao alterar a ordem dos
    numeros ja existentes em numeros_artigo.csv."""
    nomes = {"crimes": "Crimes violentos", "sinistros": "Sinistros com vítima"}
    niv_tex = {"hora": "1 h", "2h": "2 h"}
    lin_a, lin_b = [], []
    for dom in ("crimes", "sinistros"):
        fv = f"{dom}/tabelas/pico_validacao_folds.csv"
        fc = f"{dom}/tabelas/pico_concordancia_definicoes.csv"
        fj = f"{dom}/tabelas/pico_por_janela.csv"
        v, c, j = T(dom, "pico_validacao_folds.csv"), T(dom, "pico_concordancia_definicoes.csv"), T(dom, "pico_por_janela.csv")
        if dom == "sinistros":
            lin_a.append("\\midrule")
            lin_b.append("\\midrule")
        niveis = list(v["nivel"].unique())
        for k, niv in enumerate(niveis):
            vv = v[v["nivel"] == niv]
            pk = f"pico_tab.{dom}.{niv}"
            for col, rot in (("prev_P90_pearson", "P90"), ("prev_P95_pearson", "P95"), ("prev_P90_cauda", "cauda")):
                num(f"{pk}.{rot}.prev_media", 100 * vv[col].mean(), fv, 1)
                num(f"{pk}.{rot}.prev_min", 100 * vv[col].min(), fv, 1)
                num(f"{pk}.{rot}.prev_max", 100 * vv[col].max(), fv, 1)
            ref = {"P90": 0.10, "P95": 0.05}
            desv = (vv["prev_P90_pearson"] - ref["P90"]).abs().mean()
            num(f"{pk}.P90.desvio_medio_pp", 100 * desv, fv, 1)
            n_acima = int((vv["prev_P90_pearson"] > ref["P90"]).sum())
            num(f"{pk}.P90.n_folds_acima_10", n_acima, fv, 0)
            for _, r in vv.iterrows():
                num(f"{pk}.P90.fold_{r['fold']}", 100 * r["prev_P90_pearson"], fv, 1)
            cc = c[c["nivel"] == niv].set_index(["def_1", "def_2"])
            k95 = cc.loc[("P90_pearson", "P95_pearson"), "kappa"]
            j95 = cc.loc[("P90_pearson", "P95_pearson"), "jaccard"]
            kca = cc.loc[("P90_pearson", "P90_cauda_poisson"), "kappa"]
            jca = cc.loc[("P90_pearson", "P90_cauda_poisson"), "jaccard"]
            num(f"{pk}.kappa_P90_P95", k95, fc, 2)
            num(f"{pk}.jaccard_P90_P95", j95, fc, 2)
            num(f"{pk}.kappa_P90_cauda", kca, fc, 2)
            num(f"{pk}.jaccard_P90_cauda", jca, fc, 2)
            rot_dom = nomes[dom] if k == 0 else ""
            esc = "" if niv == "hora" or len(niveis) == 1 else " (alternativa)"
            lin_a.append(f"{rot_dom} & {niv_tex[niv]}{esc} & {br(100 * vv['prev_P90_pearson'].mean(), 1)} & "
                         f"{br(100 * vv['prev_P90_pearson'].min(), 1)}--{br(100 * vv['prev_P90_pearson'].max(), 1)} & "
                         f"{br(100 * desv, 1)} & {br(kca, 2)} & {br(k95, 2)} \\\\")
            # frequencia de pico por janela, por definicao e nivel; BH sobre as 6 janelas do dominio
            for d in j["definicao"].unique():
                jj = j[(j["nivel"] == niv) & (j["definicao"] == d)].copy()
                if jj.empty:
                    continue
                jj["p_BH"] = bh(jj["p_fisher"].values)
                for _, r in jj.iterrows():
                    kk = f"pico_tab.{dom}.{niv}.{d}.{r['categoria']}.{r['janela']}"
                    num(f"{kk}.RR", r["RR"], fj, 2)
                    num(f"{kk}.IC_lo", r["IC95_lo"], fj, 2)
                    num(f"{kk}.IC_hi", r["IC95_hi"], fj, 2)
                    num(f"{kk}.freq_pct", 100 * r["freq_pico"], fj, 1)
                    num(f"{kk}.freq_controle_pct", 100 * r["freq_pico_controle"], fj, 1)
                    num(f"{kk}.p_fisher", r["p_fisher"], fj, 3)
                    num(f"{kk}.p_BH_6janelas", r["p_BH"], fj + " (BH calculado no 35 sobre as 6 janelas)", 3)
        # painel B: nivel escolhido (hora), P90 Pearson
        jb = j[(j["nivel"] == "hora") & (j["definicao"] == "P90_pearson")]
        for k, (cat, rot) in enumerate((("capital", "Na capital"), ("fora_da_capital", "Fora da capital"))):
            cel = []
            for w in ("pre", "durante", "pos"):
                r = jb[(jb["categoria"] == cat) & (jb["janela"] == w)].iloc[0]
                cel.append(f"{br(r['RR'], 2)} ({br(r['p_fisher'], 3)})")
            ctrl = jb["freq_pico_controle"].iloc[0]
            lin_b.append(f"{nomes[dom] if k == 0 else ''} & {rot} & " + " & ".join(cel) +
                         (f" & {br(100 * ctrl, 1)}" if k == 0 else " & ") + " \\\\")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Horas de pico (resíduo de Pearson acima do P90 de um esperado só de calendário e clima), crimes e sinistros em blocos separados. (a) Validação: prevalência de pico (\%) no teste de cada um dos 12 \textit{folds} mensais de 2023, com esperado e limiar reestimados só no treino (ideal: 10\%), desvio médio absoluto em relação a 10\% (p.p.) e concordância ($\kappa$ de Cohen) com a cauda de Poisson e com o P95. (b) Razão entre a frequência de pico em cada janela e nas horas sem jogo (RR) e, entre parênteses, o $p$ do teste exato de Fisher sem correção, no nível de 1 hora}
\label{tab:pico}
\footnotesize
\setlength{\tabcolsep}{4pt}
\textbf{(a) Validação fora da amostra}\\[2pt]
\begin{tabular}{@{}llrrrrr@{}}
\toprule
\textbf{Domínio} & \textbf{Nível} & \textbf{Média} & \textbf{Faixa} & \textbf{Desvio} & \textbf{$\kappa$ cauda} & \textbf{$\kappa$ P95} \\
\midrule
""" + "\n".join(lin_a) + r"""
\bottomrule
\end{tabular}\\[6pt]
\textbf{(b) Frequência de pico por janela}\\[2pt]
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Domínio} & \textbf{Jogos} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} & \textbf{\% sem jogo} \\
\midrule
""" + "\n".join(lin_b) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_pico.tex", txt)


# ---------------------------------------------------------------------------
def fig_event_study():
    fig, axes = plt.subplots(2, 2, figsize=(10, 5.6), sharex=True)
    for i, (dom, y, rot) in enumerate((("crimes", "crimes_violentos", "Crimes violentos"),
                                       ("sinistros", "acidentes_com_vitima", "Sinistros com vítima"))):
        es = T(dom, "event_study.csv")
        for j, (cat, cr) in enumerate((("capital", "jogos na capital"), ("fora_da_capital", "jogos fora da capital"))):
            ax = axes[i, j]
            e = es[(es["desfecho"] == y) & (es["categoria"] == cat) & es["k"].notna()].sort_values("k")
            for a, b, c in ((-2, 0, "#cfe2f3"), (0, 2, "#f4cccc"), (2, 4, "#d9ead3")):
                ax.axvspan(a - .5, b - .5, color=c, alpha=.7, lw=0)
            ax.axhline(1, color="k", lw=.8)
            ax.errorbar(e["k"], e["IRR"], yerr=[e["IRR"] - e["IC95_lo"], e["IC95_hi"] - e["IRR"]], fmt="o-", ms=3,
                        capsize=2, color="#1f4e79", lw=1)
            ax.set_title(f"{rot} — {cr}", fontsize=9)
            ax.grid(alpha=.3)
            ax.set_xticks(range(-6, 13, 2))
            if j == 0:
                ax.set_ylabel("razão de taxas (IC 95%)", fontsize=8)
            if i == 1:
                ax.set_xlabel("horas em relação ao início do jogo", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_event_study.png"), dpi=200)
    plt.close(fig)


def fig_entorno():
    dl = T("crimes", "fase2b_deslocamento_entorno_vs_cidade.csv")
    sp = T("crimes", "fase2b_espaco_bh.csv")
    tipos = (("furtos_total", "Furtos"), ("roubos_total", "Roubos"), ("crimes_violentos", "Crimes violentos"))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.4), sharey=True)
    linhas = [(s, w) for s in EST + ["3 estádios"] for w in ("pre", "durante", "pos")]
    ypos = np.arange(len(linhas))[::-1]
    for ax, (y, rot) in zip(axes, tipos):
        for yp, (s, w) in zip(ypos, linhas):
            if s == "3 estádios":
                r = sp[sp["estadio"].str.startswith("3 est") & (sp["area"] == "disco") & (sp["desfecho"] == y)
                       & (sp["janela"] == w)].iloc[0]
                irr, lo, hi, pb = r["IRR"], r["IC95_lo"], r["IC95_hi"], r["p_BH_agregados"]
                rr = None
            else:
                r = sp[(sp["estadio"] == s) & (sp["area"] == "disco") & (sp["desfecho"] == y) & (sp["janela"] == w)].iloc[0]
                irr, lo, hi, pb = r["IRR"], r["IC95_lo"], r["IC95_hi"], r["p_BH_familia_espacial"]
                rr = dl[(dl["estadio"] == s) & (dl["desfecho"] == y) & (dl["janela"] == w)]["IRR_resto"].iloc[0]
            cor = "#c0392b" if pb < .05 else "#7f8c8d"
            ax.errorbar(irr, yp, xerr=[[irr - lo], [hi - irr]], fmt="o", color=cor, ms=4, capsize=2)
            if rr is not None:
                ax.plot(rr, yp, "x", color="#2c3e50", ms=5)
        ax.axvline(1, color="k", lw=.8)
        ax.set_xscale("log")
        tk = [0.75, 1, 1.5, 2, 3, 4]
        ax.set_xticks(tk)
        ax.set_xticklabels([str(t).replace(".", ",") for t in tk], fontsize=8)
        ax.minorticks_off()
        ax.set_title(rot, fontsize=10)
        ax.grid(axis="x", alpha=.3)
        ax.set_xlabel("razão de taxas (escala log)", fontsize=8)
    axes[0].set_yticks(ypos)
    axes[0].set_yticklabels([f"{EST_TEX.get(s, s)} — {JAN_TEX[w]}" for s, w in linhas], fontsize=7)
    fig.text(0.5, -0.02, "círculo vermelho: entorno de 3 km com p_BH < 0,05 (cinza: não); x: resto da cidade nas "
             "janelas dos jogos do mesmo estádio", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_entorno.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def numeros_extras():
    """numeros citados no texto que nao estao nas tabelas acima."""
    j = pd.read_csv(os.path.join(BASE, "data", "silver", "jogos_sp_horario.csv"))
    fo = pd.read_csv(os.path.join(BASE, "data", "silver", "jogos_fora_capital_horario.csv"))
    ji = j[j["incluir_analise"]]
    jo = j[j["na_base_original"]]
    num("jogos.capital", len(ji), "data/silver/jogos_sp_horario.csv", 0)
    num("jogos.capital_base_original", int(ji["na_base_original"].sum()), "data/silver/jogos_sp_horario.csv", 0)
    num("jogos.capital_novos", int((~ji["na_base_original"]).sum()), "data/silver/jogos_sp_horario.csv", 0)
    num("jogos.fora", int(fo["incluir_analise"].sum()), "data/silver/jogos_fora_capital_horario.csv", 0)
    num("jogos.base_original_total", len(jo), "data/silver/jogos_sp_horario.csv", 0)
    num("fuso.mudam_data", int(jo["mudou_data"].sum()), "data/silver/jogos_sp_horario.csv", 0)
    num("fuso.noturno_errado", int((jo["noturno"] != jo["noturno_antigo_bug"]).sum()), "data/silver/jogos_sp_horario.csv", 0)
    num("jogos.mando_fora_capital", int(jo["fora_da_capital"].astype(bool).sum()), "data/silver/jogos_sp_horario.csv", 0)
    f = pd.read_csv(os.path.join(BASE, "data", "gold", "fato_hora_sp.csv"), usecols=["janela", "janela_fora_capital",
                                                                                      "hora_sem_jogo"])
    num("horas.total", len(f), "data/gold/fato_hora_sp.csv", 0)
    for w in ("pre", "durante", "pos"):
        num(f"horas.capital.{w}", int((f["janela"] == w).sum()), "data/gold/fato_hora_sp.csv", 0)
        num(f"horas.fora.{w}", int((f["janela_fora_capital"] == w).sum()), "data/gold/fato_hora_sp.csv", 0)
    num("horas.sem_jogo", int(f["hora_sem_jogo"].astype(str).str.lower().eq("true").sum()), "data/gold/fato_hora_sp.csv", 0)
    fh = pd.read_csv(os.path.join(BASE, "data", "gold", "fato_hora_sp.csv"),
                     usecols=["crimes_violentos", "acidentes_com_vitima", "furtos_total", "excluir_crime",
                              "excluir_sinistro", "excluir_evento_grande_publico"])
    b = lambda c: fh[c].astype(str).str.lower().eq("true")
    okc, oks = ~b("excluir_crime") & ~b("excluir_evento_grande_publico"), ~b("excluir_sinistro") & ~b("excluir_evento_grande_publico")
    num("media_hora.crimes_violentos", fh.loc[okc, "crimes_violentos"].mean(), "data/gold/fato_hora_sp.csv", 1)
    num("media_hora.furtos_total", fh.loc[okc, "furtos_total"].mean(), "data/gold/fato_hora_sp.csv", 1)
    num("media_hora.acidentes_com_vitima", fh.loc[oks, "acidentes_com_vitima"].mean(), "data/gold/fato_hora_sp.csv", 1)
    q = pd.read_csv(os.path.join(BASE, "data", "silver", "qualidade_hora.csv")).set_index(["tipo", "recorte"])
    for t in ("crime_todos", "roubos_total", "lesao_corporal_dolosa", "acidentes_total"):
        num(f"qualidade.{t}.pct_sem_hora", q.loc[(t, "todos"), "pct_sem_hora"], "data/silver/qualidade_hora.csv", 1)
    num("qualidade.crime.minuto00", q.loc[("crime_todos", "todos"), "pct_minuto_00"], "data/silver/qualidade_hora.csv", 1)
    # pre-tendencia, placebo, pareado durante
    es = T("crimes", "event_study.csv")
    w = es[(es["termo"] == "wald_pretendencia_k-6..-3") & (es["desfecho"] == "crimes_violentos")].set_index("categoria")
    num("es.crimes.pretend.capital.p", w.loc["capital", "p"], "crimes/tabelas/event_study.csv", 3)
    for k in (-3, -2, -1, 0, 1, 2, 3):
        r = es[(es["desfecho"] == "crimes_violentos") & (es["categoria"] == "capital") & (es["k"] == k)].iloc[0]
        num(f"es.crimes.capital.k{k}", 100 * (r["IRR"] - 1), "crimes/tabelas/event_study.csv", 1, True)
    eb = T("crimes", "fase2b_event_study_bh.csv")
    tard = eb[eb["k"].between(4, 12) & (eb["p"] < .05)]
    num("es.crimes.tardias.pBH_min", tard["p_BH_familia_event_study"].min(), "crimes/tabelas/fase2b_event_study_bh.csv", 2)
    num("es.crimes.tardias.pBH_max", tard["p_BH_familia_event_study"].max(), "crimes/tabelas/fase2b_event_study_bh.csv", 2)
    es2 = T("sinistros", "event_study.csv")
    w2 = es2[(es2["termo"] == "wald_pretendencia_k-6..-3") & (es2["desfecho"] == "acidentes_com_vitima")].set_index("categoria")
    num("es.sinistros.pretend.capital.p", w2.loc["capital", "p"], "sinistros/tabelas/event_study.csv", 3)
    cp = T("crimes", "controles_pareados.csv")
    r = cp[(cp["categoria"] == "capital") & (cp["desfecho"] == "crimes_violentos") & (cp["janela"] == "durante")].iloc[0]
    num("pareado.crimes.durante", 100 * (r["DiD_IRR"] - 1), "crimes/tabelas/controles_pareados.csv", 1, True)
    num("pareado.crimes.durante.lo", 100 * (r["IC95_lo"] - 1), "crimes/tabelas/controles_pareados.csv", 1, True)
    num("pareado.crimes.durante.hi", 100 * (r["IC95_hi"] - 1), "crimes/tabelas/controles_pareados.csv", 1, True)
    # entorno agregado (BH) e resto da cidade
    sp = T("crimes", "fase2b_espaco_bh.csv")
    for y in ("furtos_total", "roubos_total", "crimes_violentos", "lesao_corporal_dolosa"):
        for w_ in ("pre", "durante", "pos"):
            r = sp[sp["estadio"].str.startswith("3 est") & (sp["area"] == "disco") & (sp["desfecho"] == y)
                   & (sp["janela"] == w_)].iloc[0]
            num(f"entorno.{y}.{w_}", 100 * (r["IRR"] - 1), "crimes/tabelas/fase2b_espaco_bh.csv", 0, True)
            num(f"entorno.{y}.{w_}.pBH", r["p_BH_agregados"], "crimes/tabelas/fase2b_espaco_bh.csv", 3)
    num("entorno.n_sobrevive_BH", int((sp["p_BH_familia_espacial"] < .05).sum()), "crimes/tabelas/fase2b_espaco_bh.csv", 0)
    num("entorno.n_familia", int(sp["p_BH_familia_espacial"].notna().sum()), "crimes/tabelas/fase2b_espaco_bh.csv", 0)
    ss = T("sinistros", "fase2b_espaco_bh.csv")
    r = ss[ss["estadio"].str.startswith("3 est") & (ss["desfecho"] == "acidentes_com_vitima") & (ss["janela"] == "pre")].iloc[0]
    num("entorno.sinistros.pre", 100 * (r["IRR"] - 1), "sinistros/tabelas/fase2b_espaco_bh.csv", 0, True)
    num("entorno.sinistros.pre.pBH", r["p_BH_agregados"], "sinistros/tabelas/fase2b_espaco_bh.csv", 3)
    # conduta
    cd = T("crimes", "fase2b_conduta_entorno.csv")
    for cond in ("VEICULO", "TRANSEUNTE"):
        r = cd[(cd["janela"] == "DURANTE+PÓS") & (cd["natureza"] == "furto") & (cd["conduta"] == cond)].iloc[0]
        num(f"conduta.furto.{cond}.OE", r["O/E"], "crimes/tabelas/fase2b_conduta_entorno.csv", 1)
        num(f"conduta.furto.{cond}.parcela", 100 * r["parcela_do_excesso_positivo"], "crimes/tabelas/fase2b_conduta_entorno.csv", 0)
    # canal: DRADE e fracao online
    dg = T("crimes", "fase3_canal_diagnostico.csv")
    num("canal.drade.n_janelas", int(dg[(dg["canal"] == "drade") & (dg["valor"])]["O"].sum()),
        "crimes/tabelas/fase3_canal_diagnostico.csv", 0)
    # pico validacao
    for dom in ("crimes", "sinistros"):
        v = T(dom, "pico_validacao_folds.csv")
        v = v[v["nivel"] == "hora"]
        num(f"pico.{dom}.prev_media", 100 * v["prev_P90_pearson"].mean(), f"{dom}/tabelas/pico_validacao_folds.csv", 1)
        num(f"pico.{dom}.prev_min", 100 * v["prev_P90_pearson"].min(), f"{dom}/tabelas/pico_validacao_folds.csv", 1)
        num(f"pico.{dom}.prev_max", 100 * v["prev_P90_pearson"].max(), f"{dom}/tabelas/pico_validacao_folds.csv", 1)
    # dose (EF hora x mes): tercil alto
    ds = T("crimes", "fase2b_dose_ef_hora_mes.csv")
    for termo in ("C_pre__T3", "C_pos__T3", "C_pre__T1", "C_pos__T1"):
        r = ds[(ds["desfecho"] == "crimes_violentos") & (ds["termo"] == termo)].iloc[0]
        num(f"dose.crimes_violentos.{termo}", 100 * (r["IRR"] - 1), "crimes/tabelas/fase2b_dose_ef_hora_mes.csv", 1, True)
        num(f"dose.crimes_violentos.{termo}.p", r["p"], "crimes/tabelas/fase2b_dose_ef_hora_mes.csv", 3)
    # placebo
    pl = T("crimes", "placebo_permutacao.csv")
    r = pl[(pl["desfecho"] == "crimes_violentos") & (pl["categoria"] == "capital") & (pl["janela"] == "pre")].iloc[0]
    num("placebo.crimes.pre.p", r["p_permutacao_bilateral"], "crimes/tabelas/placebo_permutacao.csv", 3)
    # GLM diario com calendario completo (fase 1)
    g = pd.read_csv(os.path.join(REP, "fase1", "tabelas", "glm_diario_datas_corrigidas.csv"))
    for y in ("furtos_total", "crimes_totais"):
        r = g[(g["versao"] == "jogo_completo") & (g["desfecho"] == y)].iloc[0]
        num(f"diario.completo.{y}", 100 * (r["RR"] - 1), "fase1/tabelas/glm_diario_datas_corrigidas.csv", 1, True)
        num(f"diario.completo.{y}.pBH", r["p_BH_dominio"], "fase1/tabelas/glm_diario_datas_corrigidas.csv", 3)
    # risco: domingo 16h tambem (CSV)
    rs = T("sinistros", "fase3_tabela_risco_estadio_janela.csv")
    num("risco.sinistros.max_excesso", rs["excesso_2h"].max(), "sinistros/tabelas/fase3_tabela_risco_estadio_janela.csv", 2, True)


# ===========================================================================
# V4 (2026-11-20): artigo rp_ii revisado pelo parecer. Fontes: reports/janelas/revisao/ (script 36) e, para o
# bloco preditivo (nao refeito), as tabelas fase3_* da V2. Formato das tabelas = o do rp_ii (que tinha as
# tabelas da entrega3 transcritas a mao, com as mesmas linhas de dados; agora sao geradas aqui e entram
# por \input).
# ===========================================================================
NOMES_V4 = {"crimes_violentos": "Crimes violentos", "lesao_corporal_dolosa": "Lesão corporal dolosa",
            "roubos_total": "Roubos", "furtos_total": "Furtos", "acidentes_com_vitima": "Sinistros com vítima",
            "acidentes_total": "Sinistros totais", "atropelamentos": "Atropelamentos"}
MARCA_V4 = {"efeito robusto": "$^{\\ddagger}$", "robusto no GLM, pareado inconclusivo": "$^{\\dagger}$",
            "contradito pelo pareado": "$^{\\S}$", "sinal não robusto": "$^{*}$", "sem evidência": ""}
VERED_CURTO = {"efeito robusto": "robusto$^{\\ddagger}$", "robusto no GLM, pareado inconclusivo": "$^{\\dagger}$",
               "contradito pelo pareado": "contradito", "sinal não robusto": "não robusto$^{*}$",
               "sem evidência": "sem evidência"}


def RV(dom, nome, sub=None):
    p = os.path.join(REV, dom, sub, "tabelas", nome) if sub else os.path.join(REV, dom, "tabelas", nome)
    return pd.read_csv(p)


def fonte(dom, nome, sub=None):
    return f"revisao/{dom}/{sub + '/' if sub else ''}tabelas/{nome}"


def pct(irr):
    return 100 * (irr - 1)


def emp(e, y, w):
    """linha empilhada (3 estadios) do modelo do entorno; dp vem da spec PRE + DURANTE+POS."""
    g = e[e["estadio"].str.startswith("3") & (e["desfecho"] == y) & (e["janela"] == w)]
    if "spec" in g:
        g = g[g["spec"].str.contains("DURANTE\\+PÓS")] if w == "dp" else g[~g["spec"].str.contains("DURANTE\\+PÓS")]
    return g.iloc[0]


def tab_janelas_v4():
    linhas = []
    for dom in ("crimes", "sinistros"):
        v = RV(dom, "vereditos.csv")
        fv = fonte(dom, "vereditos.csv")
        if dom == "sinistros":
            linhas.append("\\midrule")
        for y in v["desfecho"].unique():
            cel = []
            for t in ("C_pre", "C_durante", "C_pos", "F_pre", "F_durante", "F_pos"):
                r = v[(v["desfecho"] == y) & (v["termo"] == t)].iloc[0]
                cel.append(br(r["var_pct"], 1, True) + MARCA_V4[r["veredito"]])
                k = f"v4.cidade.{dom}.{y}.{t}"
                num(f"{k}.var_pct", r["var_pct"], fv, 1, True)
                num(f"{k}.p", r["p"], fv, 3)
                num(f"{k}.p_BH", r["p_BH_dominio"], fv, 3)
                num(f"{k}.p_placebo", r["p_placebo"], fv, 3)
                num(f"{k}.IC_lo", pct(r["IC95_lo"]), fv, 1, True)
                num(f"{k}.IC_hi", pct(r["IC95_hi"]), fv, 1, True)
            linhas.append(f"{NOMES_V4[y]} & " + " & ".join(cel) + " \\\\")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Variação (\%) das ocorrências por hora em cada janela, na cidade toda, em relação às horas sem nenhum jogo dos quatro times (GLM Poisson com efeito fixo de hora $\times$ dia da semana, hora $\times$ mês e ano $\times$ mês; 2022--2023). $^{\ddagger}$cumpre a regra de robustez e o pareado confirma; $^{\dagger}$cumpre a regra, pareado inconclusivo; $^{*}$$p < 0{,}05$ sem cumprir a regra; sem marca: $p \geq 0{,}05$}
\label{tab:janelas}
\small
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
 & \multicolumn{3}{c}{\textbf{Jogos na capital}} & \multicolumn{3}{c}{\textbf{Jogos fora da capital}} \\
\cmidrule(lr){2-4}\cmidrule(l){5-7}
\textbf{Desfecho} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_janelas.tex", txt)


def tab_robustez_v4():
    """Tabela 3 nova: robustez dos resultados principais (crimes). Colunas: PRE da cidade (crimes violentos),
    entorno furtos DURANTE+POS, entorno roubos POS, entorno crimes violentos POS."""
    mp, v = RV("crimes", "modelo_principal_e_robustez.csv"), RV("crimes", "vereditos.csv")
    pl, cp = RV("crimes", "placebo_permutacao.csv"), RV("crimes", "controles_pareados.csv")
    e, e0 = RV("crimes", "entorno_modelo_principal.csv"), RV("crimes", "entorno_sem_hora_mes.csv")
    ep, epp, er = RV("crimes", "entorno_placebo.csv"), RV("crimes", "entorno_pareado.csv"), RV("crimes", "entorno_raio.csv")
    cols = [("entorno", "furtos_total", "dp"), ("entorno", "roubos_total", "pos"), ("entorno", "crimes_violentos", "pos")]
    rot = ["Modelo principal", "$p_{BH}$", "Sem efeito fixo hora $\\times$ mês", "Binomial negativa / quase-binomial",
           "Erro agrupado por dia", "Placebo ($p$)", "Pareado (IC 95\\%)", "Raio de 1 km", "Raio de 2 km",
           "Raio de 5 km", "Classificação"]
    tabela = {r: [] for r in rot}
    # cidade, PRE, crimes violentos
    sel = lambda spec: mp[(mp["desfecho"] == "crimes_violentos") & (mp["termo"] == "C_pre") & mp["spec"].str.startswith(spec)].iloc[0]
    fm = fonte("crimes", "modelo_principal_e_robustez.csv")
    vv = v[(v["desfecho"] == "crimes_violentos") & (v["termo"] == "C_pre")].iloc[0]
    for r_, spec, key in (("Modelo principal", "principal", "principal"), ("Sem efeito fixo hora $\\times$ mês", "sem EF", "sem_hm"),
                          ("Binomial negativa / quase-binomial", "Binomial", "nb"), ("Erro agrupado por dia", "cluster por dia", "dia")):
        x = sel(spec)
        tabela[r_].append(f"{br(x['var_pct'], 1, True)} ({pfmt(x['p'])})")
        num(f"v4.rob.cidade_pre.{key}", x["var_pct"], fm, 1, True)
        num(f"v4.rob.cidade_pre.{key}.p", x["p"], fm, 3)
    tabela["$p_{BH}$"].append(pfmt(vv["p_BH_dominio"]))
    x = pl[(pl["desfecho"] == "crimes_violentos") & (pl["categoria"] == "capital") & (pl["janela"] == "pre")].iloc[0]
    tabela["Placebo ($p$)"].append(pfmt(x["p_permutacao_bilateral"]))
    num("v4.rob.cidade_pre.placebo.p", x["p_permutacao_bilateral"], fonte("crimes", "placebo_permutacao.csv"), 3)
    x = cp[(cp["categoria"] == "capital") & (cp["desfecho"] == "crimes_violentos") & (cp["janela"] == "pre")].iloc[0]
    tabela["Pareado (IC 95\\%)"].append(f"{br(pct(x['DiD_IRR']), 1, True)} ({br(pct(x['IC95_lo']), 1, True)} a {br(pct(x['IC95_hi']), 1, True)})")
    for k_ in ("DiD_IRR", "IC95_lo", "IC95_hi"):
        num(f"v4.rob.cidade_pre.pareado.{k_}", pct(x[k_]), fonte("crimes", "controles_pareados.csv"), 1, True)
    for r_ in ("Raio de 1 km", "Raio de 2 km", "Raio de 5 km"):
        tabela[r_].append("--")
    tabela["Classificação"].append(VERED_CURTO[vv["veredito"]])
    # entorno
    for _, y, w in cols:
        k = f"v4.rob.entorno.{y}.{w}"
        x = emp(e, y, w)
        fe = fonte("crimes", "entorno_modelo_principal.csv")
        tabela["Modelo principal"].append(f"{br(x['var_pct'], 0, True)} ({pfmt(x['p'])})")
        tabela["$p_{BH}$"].append(pfmt(x["p_BH"]))
        tabela["Binomial negativa / quase-binomial"].append(f"{br(x['var_pct'], 0, True)} ({pfmt(x['p_quase'])})")
        tabela["Erro agrupado por dia"].append(f"{br(x['var_pct'], 0, True)} ({pfmt(x['p_dia'])})")
        tabela["Classificação"].append(VERED_CURTO[x["veredito"]])
        for c_, nd in (("var_pct", 0), ("p", 3), ("p_BH", 3), ("p_quase", 3), ("p_dia", 3), ("p_placebo", 3)):
            num(f"{k}.{c_}", x[c_], fe, nd, c_ == "var_pct")
        num(f"{k}.IC_lo", pct(x["IC95_lo"]), fe, 0, True)
        num(f"{k}.IC_hi", pct(x["IC95_hi"]), fe, 0, True)
        x0 = emp(e0, y, w)
        tabela["Sem efeito fixo hora $\\times$ mês"].append(f"{br(x0['var_pct'], 0, True)} ({pfmt(x0['p'])})")
        num(f"{k}.sem_hm", x0["var_pct"], fonte("crimes", "entorno_sem_hora_mes.csv"), 0, True)
        p_ = ep[ep["estadio"].str.startswith("3") & (ep["desfecho"] == y) & (ep["janela"] == w)].iloc[0]
        tabela["Placebo ($p$)"].append(pfmt(p_["p_permutacao_bilateral"]))
        q = epp[epp["estadio"].str.startswith("3") & (epp["desfecho"] == y) & (epp["janela"] == w)].iloc[0]
        tabela["Pareado (IC 95\\%)"].append(f"{br(pct(q['DiD_IRR']), 0, True)} ({br(pct(q['IC95_lo']), 0, True)} a {br(pct(q['IC95_hi']), 0, True)})")
        for k_ in ("DiD_IRR", "IC95_lo", "IC95_hi"):
            num(f"{k}.pareado.{k_}", pct(q[k_]), fonte("crimes", "entorno_pareado.csv"), 0, True)
        for raio, r_ in ((1.0, "Raio de 1 km"), (2.0, "Raio de 2 km"), (5.0, "Raio de 5 km")):
            g = er[(er["desfecho"] == y) & (er["janela"] == w) & (er["raio_km"] == raio)].iloc[0]
            tabela[r_].append(f"{br(g['var_pct'], 0, True)} ({pfmt(g['p'])})")
            num(f"{k}.raio{int(raio)}", g["var_pct"], fonte("crimes", "entorno_raio.csv"), 0, True)
            num(f"{k}.raio{int(raio)}.p", g["p"], fonte("crimes", "entorno_raio.csv"), 3)
    linhas = [f"{r_} & " + " & ".join(tabela[r_]) + " \\\\" for r_ in rot]
    linhas.insert(rot.index("Classificação"), "\\midrule")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Robustez dos resultados principais de crimes: variação (\%) e, entre parênteses, $p$. Cidade: PRÉ dos jogos na capital (GLM Poisson). Entorno: disco de 3~km contra o resto da cidade (diferença em diferenças, três estádios empilhados); furtos na janela DURANTE+PÓS (4 h). Binomial negativa na cidade e quase-binomial no entorno. Classificação pela regra da Seção~3 ($^{\ddagger}$o pareado confirma)}
\label{tab:robustez}
\footnotesize
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{@{}lrrrr@{}}
\toprule
 & \textbf{Cidade} & \multicolumn{3}{c}{\textbf{Entorno de 3~km}} \\
\cmidrule(lr){2-2}\cmidrule(l){3-5}
\textbf{Especificação} & \textbf{Crimes viol. PRÉ} & \textbf{Furtos DUR.+PÓS} & \textbf{Roubos PÓS} & \textbf{Crimes viol. PÓS} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_robustez.tex", txt)


def tab_canal_v4():
    c = RV("crimes", "entorno_canal.csv")
    fc = fonte("crimes", "entorno_canal.csv")
    versoes = [("todos", "Todos"), ("só presencial", "Só presencial"), ("só BO online", "Só BO online"),
               ("sem conduta nula", "Sem conduta nula")]
    jan = {"durante": "DURANTE", "pos": "PÓS", "dp": "DURANTE+PÓS"}
    linhas = []
    for y, rot, ws in (("furtos_total", "Furtos", ("durante", "pos", "dp")), ("roubos_total", "Roubos", ("durante", "pos")),
                       ("crimes_violentos", "Crimes violentos", ("durante", "pos"))):
        for i, w in enumerate(ws):
            cel = []
            for vn, _ in versoes:
                g = c[(c["versao"] == vn) & (c["desfecho"] == y) & (c["janela"] == w)].iloc[0]
                cel.append(br(g["var_pct"], 0, True) + ("$^{*}$" if g["p_BH_versao"] < .05 else ""))
                num(f"v4.canal.{y}.{w}.{vn}", g["var_pct"], fc, 0, True)
                num(f"v4.canal.{y}.{w}.{vn}.p_BH", g["p_BH_versao"], fc, 3)
            linhas.append(f"{rot if i == 0 else ''} & {jan[w]} & " + " & ".join(cel) + " \\\\")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Entorno de 3~km (três estádios empilhados, diferença em diferenças): variação (\%) por canal de registro do boletim, com o resto da cidade restrito ao mesmo canal. $^{*}p_{BH} < 0{,}05$ (correção dentro de cada coluna)}
\label{tab:canal}
\small
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Desfecho} & \textbf{Janela} & """ + " & ".join(f"\\textbf{{{r}}}" for _, r in versoes) + r""" \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_canal.tex", txt)


def tab_pico_v4():
    """definicao mantida (esperado sem hora x mes), dados da V4 (BO unico, sem a Copa de 2022); a variante com
    hora x mes entra no texto como robustez. Sem a coluna kappa P95 (decorre das duas prevalencias encaixadas)."""
    nomes = {"crimes": "Crimes violentos", "sinistros": "Sinistros com vítima"}
    niv_tex = {"hora": "1 h", "2h": "2 h"}
    lin_a, lin_b = [], []
    for dom in ("crimes", "sinistros"):
        sub = "pico_sem_hm"
        v, c, j = RV(dom, "pico_validacao_folds.csv", sub), RV(dom, "pico_concordancia_definicoes.csv", sub), RV(dom, "pico_por_janela.csv", sub)
        fv, fc, fj = fonte(dom, "pico_validacao_folds.csv", sub), fonte(dom, "pico_concordancia_definicoes.csv", sub), fonte(dom, "pico_por_janela.csv", sub)
        if dom == "sinistros":
            lin_a.append("\\midrule")
            lin_b.append("\\midrule")
        niveis = list(v["nivel"].unique())
        for k, niv in enumerate(niveis):
            vv = v[v["nivel"] == niv]
            pk = f"v4.pico.{dom}.{niv}"
            num(f"{pk}.prev_media", 100 * vv["prev_P90_pearson"].mean(), fv, 1)
            num(f"{pk}.prev_min", 100 * vv["prev_P90_pearson"].min(), fv, 1)
            num(f"{pk}.prev_max", 100 * vv["prev_P90_pearson"].max(), fv, 1)
            desv = (vv["prev_P90_pearson"] - 0.10).abs().mean()
            num(f"{pk}.desvio_pp", 100 * desv, fv, 1)
            num(f"{pk}.n_folds_acima_10", int((vv["prev_P90_pearson"] > .10).sum()), fv, 0)
            for _, r in vv.iterrows():
                num(f"{pk}.fold_{r['fold']}", 100 * r["prev_P90_pearson"], fv, 1)
            cc = c[c["nivel"] == niv].set_index(["def_1", "def_2"])
            kca = cc.loc[("P90_pearson", "P90_cauda_poisson"), "kappa"]
            num(f"{pk}.kappa_cauda", kca, fc, 2)
            esc = "" if niv == "hora" or len(niveis) == 1 else " (alternativa)"
            lin_a.append(f"{nomes[dom] if k == 0 else ''} & {niv_tex[niv]}{esc} & {br(100 * vv['prev_P90_pearson'].mean(), 1)} & "
                         f"{br(100 * vv['prev_P90_pearson'].min(), 1)}--{br(100 * vv['prev_P90_pearson'].max(), 1)} & "
                         f"{br(100 * desv, 1)} & {br(kca, 2)} \\\\")
            for dfn in j["definicao"].unique():
                jj = j[(j["nivel"] == niv) & (j["definicao"] == dfn)].copy()
                jj["p_BH"] = bh(jj["p_fisher"].values)
                for _, r in jj.iterrows():
                    kk = f"{pk}.{dfn}.{r['categoria']}.{r['janela']}"
                    num(f"{kk}.RR", r["RR"], fj, 2)
                    num(f"{kk}.IC_lo", r["IC95_lo"], fj, 2)
                    num(f"{kk}.IC_hi", r["IC95_hi"], fj, 2)
                    num(f"{kk}.freq_pct", 100 * r["freq_pico"], fj, 1)
                    num(f"{kk}.freq_controle_pct", 100 * r["freq_pico_controle"], fj, 1)
                    num(f"{kk}.p_fisher", r["p_fisher"], fj, 3)
                    num(f"{kk}.p_BH_6janelas", r["p_BH"], fj + " (BH sobre as 6 janelas, calculado no 35)", 3)
        jb = j[(j["nivel"] == "hora") & (j["definicao"] == "P90_pearson")]
        for k, (cat, rot) in enumerate((("capital", "Na capital"), ("fora_da_capital", "Fora da capital"))):
            cel = []
            for w in ("pre", "durante", "pos"):
                r = jb[(jb["categoria"] == cat) & (jb["janela"] == w)].iloc[0]
                cel.append(f"{br(r['RR'], 2)} ({br(r['p_fisher'], 3)})")
            ctrl = jb["freq_pico_controle"].iloc[0]
            lin_b.append(f"{nomes[dom] if k == 0 else ''} & {rot} & " + " & ".join(cel) +
                         (f" & {br(100 * ctrl, 1)}" if k == 0 else " & ") + " \\\\")
        # robustez: esperado com hora x mes (frase no texto)
        sub2 = "pico_com_hm"
        v2, j2 = RV(dom, "pico_validacao_folds.csv", sub2), RV(dom, "pico_por_janela.csv", sub2)
        v2 = v2[v2["nivel"] == "hora"]
        num(f"v4.pico_hm.{dom}.prev_media", 100 * v2["prev_P90_pearson"].mean(), fonte(dom, "pico_validacao_folds.csv", sub2), 1)
        jj = j2[(j2["nivel"] == "hora") & (j2["definicao"] == "P90_pearson")].copy()
        jj["p_BH"] = bh(jj["p_fisher"].values)
        num(f"v4.pico_hm.{dom}.p_BH_min", jj["p_BH"].min(), fonte(dom, "pico_por_janela.csv", sub2) + " (BH no 35)", 3)
        for _, r in jj.iterrows():
            num(f"v4.pico_hm.{dom}.{r['categoria']}.{r['janela']}.RR", r["RR"], fonte(dom, "pico_por_janela.csv", sub2), 2)
            num(f"v4.pico_hm.{dom}.{r['categoria']}.{r['janela']}.p", r["p_fisher"], fonte(dom, "pico_por_janela.csv", sub2), 3)
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Horas de pico (resíduo de Pearson acima do P90 de um esperado só de calendário e clima), crimes e sinistros em blocos separados. (a) Validação: prevalência de pico (\%) no teste de cada um dos 12 \emph{folds} mensais de 2023, com esperado e limiar reestimados só no treino (ideal: 10\%), desvio médio absoluto em relação a 10\% (p.p.) e concordância ($\kappa$ de Cohen) com a cauda de Poisson. (b) Razão entre a frequência de pico em cada janela e nas horas sem jogo (RR) e, entre parênteses, o $p$ do teste exato de Fisher sem correção, no nível de 1 hora}
\label{tab:pico}
\small
\setlength{\tabcolsep}{5pt}
\textbf{(a) Validação fora da amostra}\\[2pt]
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Domínio} & \textbf{Nível} & \textbf{Média} & \textbf{Faixa} & \textbf{Desvio} & \textbf{$\kappa$ cauda} \\
\midrule
""" + "\n".join(lin_a) + r"""
\bottomrule
\end{tabular}

\vspace{8pt}
\textbf{(b) Frequência de pico por janela}\\[2pt]
\begin{tabular}{@{}llrrrr@{}}
\toprule
\textbf{Domínio} & \textbf{Jogos} & \textbf{PRÉ} & \textbf{DURANTE} & \textbf{PÓS} & \textbf{\% sem jogo} \\
\midrule
""" + "\n".join(lin_b) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_pico.tex", txt)


def tab_preditivo_v4():
    """Fase 3 da V2 (nao refeita): acrescenta o baseline (deviance e PR-AUC) e o clima da vespera."""
    blocos = [("crimes", "cidade", "crimes_violentos", "Cidade", "Crimes violentos"),
              ("crimes", "entorno", "crimes_violentos", "Entorno", "Crimes violentos"),
              ("crimes", "entorno", "roubos_total", "Entorno", "Roubos"),
              ("crimes", "entorno", "furtos_total", "Entorno", "Furtos"),
              ("sinistros", "cidade", "acidentes_com_vitima", "Cidade", "Sinistros com vítima"),
              ("sinistros", "entorno", "acidentes_com_vitima", "Entorno", "Sinistros com vítima")]
    linhas = []
    for dom, esc, y, re_, ry in blocos:
        fd, fa, fp = (f"{dom}/tabelas/fase3_desempenho_{esc}_{y}.csv", f"{dom}/tabelas/fase3_ablacao_{esc}_{y}.csv",
                      f"{dom}/tabelas/fase3_pico_{esc}_{y}.csv")
        g = T(dom, f"fase3_desempenho_{esc}_{y}.csv").set_index(["modelo", "variante"])
        ab = T(dom, f"fase3_ablacao_{esc}_{y}.csv").set_index(["modelo", "subconjunto"])
        pk = T(dom, f"fase3_pico_{esc}_{y}.csv").set_index(["modelo", "variante"])
        kb = f"v4.pred.{esc}.{y}"

        def dev(mod, var="com_jogo"):
            if (mod, var) not in g.index:
                return "--"
            num(f"{kb}.{mod}.{var}.deviance", g.loc[(mod, var), "deviance_media"], fd, 3)
            num(f"{kb}.{mod}.{var}.MAE", g.loc[(mod, var), "MAE"], fd, 2)
            return br(g.loc[(mod, var), "deviance_media"], 3)

        def ganho(mod, sub):
            if (mod, sub) not in ab.index:
                return "--"
            r = ab.loc[(mod, sub)]
            num(f"{kb}.{mod}.{sub}.ganho_dev_pct", r["ganho_dev_pct"], fa, 1, True)
            sig = "$^{*}$" if r["ganho_dev_IC_lo"] > 0 else ("$^{-}$" if r["ganho_dev_IC_hi"] < 0 else "")
            return br(r["ganho_dev_pct"], 1, True) + sig
        d_base = dev("baseline", "sem_jogo")
        cel_dev = [d_base, dev("XGBoost"), dev("Prophet"), dev("GLM")]
        if (("XGBoost clima lag24", "com_jogo")) in g.index:
            dev("XGBoost clima lag24")
            ganho("XGBoost clima lag24", "todas as horas")
            ganho("XGBoost clima lag24", "horas PRÉ/DURANTE/PÓS na capital")
        melhor = min(m_ for m_ in ("XGBoost", "Prophet", "GLM") if (m_, "com_jogo") in g.index)
        best = min(((g.loc[(m_, "com_jogo"), "deviance_media"], m_) for m_ in ("XGBoost", "Prophet", "GLM")
                    if (m_, "com_jogo") in g.index))
        num(f"{kb}.melhor_vs_baseline_pct", 100 * (1 - best[0] / g.loc[("baseline", "sem_jogo"), "deviance_media"]), fd, 1)
        prc, prs = pk.loc[("XGBoost", "com_jogo"), "PR_AUC_fold_macro"], pk.loc[("XGBoost", "sem_jogo"), "PR_AUC_fold_macro"]
        prb = pk.loc[("baseline", "sem_jogo"), "PR_AUC_fold_macro"]
        prev = pk.loc[("XGBoost", "com_jogo"), "prevalencia_teste"]
        for nm, val in (("prauc_com", prc), ("prauc_sem", prs), ("prauc_baseline", prb), ("prev", prev)):
            num(f"{kb}.{nm}", val, fp, 3)
        if ("XGBoost clima lag24", "com_jogo") in pk.index:
            num(f"{kb}.prauc_clima_lag24", pk.loc[("XGBoost clima lag24", "com_jogo"), "PR_AUC_fold_macro"], fp, 3)
        linhas.append(f"{re_} & {ry} & " + " & ".join(cel_dev) + " & "
                      f"{ganho('XGBoost', 'todas as horas')} & {ganho('XGBoost', 'horas PRÉ/DURANTE/PÓS na capital')} & "
                      f"{ganho('GLM', 'horas PRÉ/DURANTE/PÓS na capital')} & {ganho('Prophet', 'horas PRÉ/DURANTE/PÓS na capital')} & "
                      f"{br(prc, 3)} / {br(prs, 3)} / {br(prb, 3)} & {br(prev, 3)} \\\\")
        if esc == "entorno" and y == "furtos_total":
            linhas.append("\\midrule")
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Bloco preditivo (\emph{walk-forward}, 12 meses de 2023): deviance de Poisson média do \emph{baseline} (média da mesma hora e dia da semana nas quatro semanas anteriores) e dos modelos com as variáveis de jogo, e ganho (\%) da ablação = redução da deviance ao incluir as variáveis de jogo, no geral e só nas horas PRÉ/DURANTE/PÓS na capital. $^{*}$IC 95\% por \emph{bootstrap} em blocos de semana exclui 0 a favor do jogo; $^{-}$exclui 0 contra. PR-AUC (média por \emph{fold}) do XGBoost com e sem jogo e do \emph{baseline}, e prevalência de pico no teste}
\label{tab:preditivo}
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{@{}llrrrrrrrrrr@{}}
\toprule
 & & \multicolumn{4}{c}{\textbf{Deviance}} & \multicolumn{4}{c}{\textbf{Ganho da ablação (\%)}} & & \\
\cmidrule(lr){3-6}\cmidrule(lr){7-10}
\textbf{Escala} & \textbf{Alvo} & \textbf{Base.} & \textbf{XGB} & \textbf{Prophet} & \textbf{GLM} & \textbf{XGB geral} & \textbf{XGB jan.} & \textbf{GLM jan.} & \textbf{Prophet jan.} & \textbf{PR-AUC} & \textbf{Prev.} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_preditivo.tex", txt)


def tab_risco_v4():
    r = RV("crimes", "entorno_tabela_risco.csv")
    sh = RV("crimes", "entorno_furtos_sem_hora.csv")
    fr, fs = fonte("crimes", "entorno_tabela_risco.csv"), fonte("crimes", "entorno_furtos_sem_hora.csv")
    fator = float(sh["fator_empirico_todos_sobre_com_hora"].iloc[0])
    num("v4.semhora.fator_empirico", fator, fs, 1)
    slot = "quarta 21h30"
    linhas = []
    for s in EST:
        for w in ("pre", "durante", "pos"):
            cel = []
            for y in ("crimes_violentos", "roubos_total", "furtos_total"):
                x = r[(r["estadio"] == s) & (r["janela"] == w) & (r["desfecho"] == y) & (r["jogo_tipico"] == slot)].iloc[0]
                cel += [br(pct(x["IRR"]), 0, True) + ("$^{*}$" if x["p"] < .05 else ""), br(x["excesso"], 2, True)]
                k = f"v4.risco.{s}.{w}.{y}"
                num(f"{k}.rel", pct(x["IRR"]), fr, 0, True)
                num(f"{k}.excesso", x["excesso"], fr, 2, True)
                num(f"{k}.base", x["esperado_sem_jogo"], fr, 2)
                if y == "furtos_total":
                    cel.append(br(x["excesso"] * fator, 2, True))
                    num(f"{k}.excesso_corr", x["excesso"] * fator, fr + " x fator empírico de " + fs, 2, True)
            linhas.append(f"{EST_TEX[s] if w == 'pre' else ''} & {JAN_TEX[w]} & " + " & ".join(cel) + " \\\\")
        x = r[(r["estadio"] == s) & (r["janela"] == "dp") & (r["desfecho"] == "furtos_total") & (r["jogo_tipico"] == slot)].iloc[0]
        num(f"v4.risco.{s}.dp.furtos_total.rel", pct(x["IRR"]), fr, 0, True)
        num(f"v4.risco.{s}.dp.furtos_total.excesso", x["excesso"], fr, 2, True)
        num(f"v4.risco.{s}.dp.furtos_total.excesso_corr", x["excesso"] * fator, fr, 2, True)
        if s != EST[-1]:
            linhas.append("\\midrule")
    rs = RV("sinistros", "entorno_tabela_risco.csv")
    num("v4.risco.sinistros.max_excesso", rs[rs["jogo_tipico"] == slot]["excesso"].max(), fonte("sinistros", "entorno_tabela_risco.csv"), 2, True)
    txt = r"""\begin{table}[!htbp]
\centering
\caption{Risco esperado no entorno de 3~km de cada estádio para um jogo típico (quarta-feira, 21h30): variação relativa (\%) do modelo do entorno por estádio e excesso absoluto de ocorrências nas 2 horas da janela. $^{*}p < 0{,}05$. Furtos corrigidos: excesso multiplicado por """ + br(fator, 1) + r""", razão entre o excesso diário de todos os furtos (com e sem hora) e o de furtos com hora nos dias de jogo}
\label{tab:risco}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}llrrrrrrr@{}}
\toprule
 & & \multicolumn{2}{c}{\textbf{Crimes violentos}} & \multicolumn{2}{c}{\textbf{Roubos}} & \multicolumn{3}{c}{\textbf{Furtos}} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(l){7-9}
\textbf{Estádio} & \textbf{Janela} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Rel.} & \textbf{Abs.} & \textbf{Abs. corr.} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    grava("tab_risco.tex", txt)


def fig_event_study_v4():
    fig, axes = plt.subplots(2, 2, figsize=(10, 5.6), sharex=True)
    for i, (dom, y, rot) in enumerate((("crimes", "crimes_violentos", "Crimes violentos"),
                                       ("sinistros", "acidentes_com_vitima", "Sinistros com vítima"))):
        es = RV(dom, "event_study.csv")
        for j, (cat, cr) in enumerate((("capital", "jogos na capital"), ("fora_da_capital", "jogos fora da capital"))):
            ax = axes[i, j]
            e = es[(es["desfecho"] == y) & (es["categoria"] == cat) & es["k"].notna()].sort_values("k")
            for a, b, c in ((-2, 0, "#cfe2f3"), (0, 2, "#f4cccc"), (2, 4, "#d9ead3")):
                ax.axvspan(a - .5, b - .5, color=c, alpha=.7, lw=0)
            ax.axhline(1, color="k", lw=.8)
            ax.errorbar(e["k"], e["IRR"], yerr=[e["IRR"] - e["IC95_lo"], e["IC95_hi"] - e["IRR"]], fmt="o-", ms=3,
                        capsize=2, color="#1f4e79", lw=1)
            ax.set_title(f"{rot}: {cr}", fontsize=9)
            ax.grid(alpha=.3)
            ax.set_xticks(range(-6, 13, 2))
            if j == 0:
                ax.set_ylabel("razão de taxas (IC 95%)", fontsize=8)
            if i == 1:
                ax.set_xlabel("horas em relação ao início do jogo", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_event_study.png"), dpi=200)
    plt.close(fig)


def fig_entorno_v4():
    e = RV("crimes", "entorno_modelo_principal.csv")
    e = e[e["spec"] == "janelas"]
    tipos = (("furtos_total", "Furtos"), ("roubos_total", "Roubos"), ("crimes_violentos", "Crimes violentos"))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.4), sharey=True)
    linhas = [(s, w) for s in EST + ["3 estádios"] for w in ("pre", "durante", "pos")]
    ypos = np.arange(len(linhas))[::-1]
    for ax, (y, rot) in zip(axes, tipos):
        for yp, (s, w) in zip(ypos, linhas):
            g = e[(e["desfecho"] == y) & (e["janela"] == w)]
            g = g[g["estadio"].str.startswith("3")] if s == "3 estádios" else g[g["estadio"] == s]
            r = g.iloc[0]
            cor = "#c0392b" if r["p_BH"] < .05 else "#7f8c8d"
            mk = "D" if s == "3 estádios" else "o"
            ax.errorbar(r["IRR"], yp, xerr=[[r["IRR"] - r["IC95_lo"]], [r["IC95_hi"] - r["IRR"]]], fmt=mk, color=cor,
                        ms=4, capsize=2)
        ax.axvline(1, color="k", lw=.8)
        ax.set_xscale("log")
        tk = [0.5, 0.75, 1, 1.5, 2, 3, 4]
        ax.set_xticks(tk)
        ax.set_xticklabels([str(t).replace(".", ",") for t in tk], fontsize=8)
        ax.minorticks_off()
        ax.set_title(rot, fontsize=10)
        ax.grid(axis="x", alpha=.3)
        ax.set_xlabel("razão entre a variação no entorno e no resto da cidade (log)", fontsize=7)
    axes[0].set_yticks(ypos)
    axes[0].set_yticklabels([f"{EST_TEX.get(s, s)}: {JAN_TEX[w]}" for s, w in linhas], fontsize=7)
    fig.text(0.5, -0.02, "vermelho: p_BH < 0,05 (cinza: não); losango: três estádios empilhados", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(ART, "fig_entorno.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def numeros_extras_v4():
    j = pd.read_csv(os.path.join(BASE, "data", "silver", "jogos_sp_horario.csv"))
    fo = pd.read_csv(os.path.join(BASE, "data", "silver", "jogos_fora_capital_horario.csv"))
    ji = j[j["incluir_analise"]]
    jo = j[j["na_base_original"]]
    fj, ff = "data/silver/jogos_sp_horario.csv", "data/silver/jogos_fora_capital_horario.csv"
    num("jogos.capital", len(ji), fj, 0)
    num("jogos.fora", int(fo["incluir_analise"].sum()), ff, 0)
    num("jogos.base_original_total", len(jo), fj, 0)
    num("jogos.base_original_capital", int(jo["incluir_analise"].sum()), fj, 0)
    num("jogos.mando_fora_capital", int(jo["fora_da_capital"].astype(bool).sum()), fj, 0)
    num("jogos.publico.ok", int((ji["publico_status"] == "ok").sum()), fj, 0)
    num("jogos.publico.capacidade_restrita", int((ji["publico_status"] == "capacidade_restrita").sum()), fj, 0)
    num("jogos.publico.portoes_fechados", int((ji["publico_status"] == "portoes_fechados").sum()), fj, 0)
    f = pd.read_csv(os.path.join(BASE, "data", "gold", "fato_hora_sp.csv"), usecols=["janela", "janela_fora_capital"])
    num("horas.total", len(f), "data/gold/fato_hora_sp.csv", 0)
    md = pd.read_csv(os.path.join(REV, "medias_horarias.csv")).set_index("desfecho")
    for y in ("crimes_violentos", "furtos_total", "acidentes_com_vitima"):
        num(f"v4.media_hora.{y}", md.loc[y, "media_hora"], "revisao/medias_horarias.csv", 1)
    fu = pd.read_csv(os.path.join(REV, "funil_registros.csv")).set_index("desfecho")
    for y in fu.index:
        for c in ("registros_municipio", "com_hora", "com_hora_coord_valida", "com_hora_nos_discos_3km", "pile_excluido"):
            num(f"v4.funil.{y}.{c}", fu.loc[y, c], "revisao/funil_registros.csv", 0)
        num(f"v4.funil.{y}.pct_sem_hora", 100 - fu.loc[y, "pct_com_hora"], "revisao/funil_registros.csv", 1)
        num(f"v4.funil.{y}.pct_coord_valida", fu.loc[y, "pct_coord_valida_entre_com_hora"], "revisao/funil_registros.csv", 1)
        num(f"v4.funil.{y}.pct_pile", fu.loc[y, "pct_pile_dos_discos"], "revisao/funil_registros.csv", 1)
    q = pd.read_csv(os.path.join(BASE, "data", "silver", "qualidade_hora.csv")).set_index(["tipo", "recorte"])
    num("qualidade.crime.minuto00", q.loc[("crime_todos", "todos"), "pct_minuto_00"], "data/silver/qualidade_hora.csv", 1)
    dd = RV("crimes", "dedup_bo_unico.csv").set_index("desfecho")
    num("v4.dedup.crimes_violentos.excesso_pct", dd.loc["crimes_violentos", "excesso_pct"], fonte("crimes", "dedup_bo_unico.csv"), 2)
    cp = pd.read_csv(os.path.join(REV, "copa2022_exclusao.csv"))
    num("v4.copa2022.horas", cp["horas_excluidas"].sum(), "revisao/copa2022_exclusao.csv", 0)
    # event study (spec nova) + BH na familia do event study do dominio
    for dom, y in (("crimes", "crimes_violentos"), ("sinistros", "acidentes_com_vitima")):
        es = RV(dom, "event_study.csv")
        fe = fonte(dom, "event_study.csv")
        w = es[(es["termo"] == "wald_pretendencia_k-6..-3") & (es["desfecho"] == y)].set_index("categoria")
        for cat in ("capital", "fora_da_capital"):
            num(f"v4.es.{dom}.pretend.{cat}.p", w.loc[cat, "p"], fe, 3)
        mk = es["k"].notna()
        es.loc[mk, "p_BH"] = bh(es.loc[mk, "p"].values)
        for k in range(-3, 13):
            r = es[(es["desfecho"] == y) & (es["categoria"] == "capital") & (es["k"] == k)].iloc[0]
            num(f"v4.es.{dom}.capital.k{k}", pct(r["IRR"]), fe, 1, True)
            num(f"v4.es.{dom}.capital.k{k}.p", r["p"], fe, 3)
            num(f"v4.es.{dom}.capital.k{k}.p_BH", r["p_BH"], fe + " (BH no 35)", 3)
        tard = es[mk & es["k"].between(4, 12) & (es["p"] < .05) & (es["desfecho"] == y)]
        num(f"v4.es.{dom}.tardias_n", len(tard), fe, 0)
        if len(tard):
            num(f"v4.es.{dom}.tardias.pBH_min", tard["p_BH"].min(), fe + " (BH no 35)", 2)
            num(f"v4.es.{dom}.tardias.pBH_max", tard["p_BH"].max(), fe + " (BH no 35)", 2)
        cpp = RV(dom, "controles_pareados.csv")
        for wj in ("pre", "durante", "pos"):
            r = cpp[(cpp["categoria"] == "capital") & (cpp["desfecho"] == y) & (cpp["janela"] == wj)].iloc[0]
            for c in ("DiD_IRR", "IC95_lo", "IC95_hi"):
                num(f"v4.pareado.{dom}.{y}.{wj}.{c}", pct(r[c]), fonte(dom, "controles_pareados.csv"), 1, True)
        ds = RV(dom, "dose_resposta_publico.csv")
        for t in ("C_pre__T1", "C_pre__T2", "C_pre__T3", "C_pos__T1", "C_pos__T3", "C_pre__x_logpub", "C_pos__x_logpub"):
            r = ds[(ds["desfecho"] == y) & (ds["termo"] == t)]
            if len(r):
                num(f"v4.dose.{dom}.{y}.{t}", pct(r["IRR"].iloc[0]), fonte(dom, "dose_resposta_publico.csv"), 1, True)
                num(f"v4.dose.{dom}.{y}.{t}.p", r["p"].iloc[0], fonte(dom, "dose_resposta_publico.csv"), 3)
        h = RV(dom, "heterogeneidade_classico_resultado.csv")
        for _, r in h.iterrows():
            k = f"v4.het.{dom}.{r['desfecho']}.{r['atributo']}.{r['janela']}.{r['nivel']}"
            num(k, pct(r["IRR"]), fonte(dom, "heterogeneidade_classico_resultado.csv"), 1, True)
            num(f"{k}.p", r["p"], fonte(dom, "heterogeneidade_classico_resultado.csv"), 3)
            num(f"{k}.p_BH", r["p_BH_dominio_atributo"], fonte(dom, "heterogeneidade_classico_resultado.csv"), 3)
        # entorno (todos os desfechos, empilhado e por estadio)
        e = RV(dom, "entorno_modelo_principal.csv")
        fe = fonte(dom, "entorno_modelo_principal.csv")
        for _, r in e.iterrows():
            est = "3" if r["estadio"].startswith("3") else r["estadio"]
            k = f"v4.entorno.{dom}.{est}.{r['desfecho']}.{r['janela']}"
            for c, nd in (("var_pct", 0), ("p", 3), ("p_BH", 3), ("p_placebo", 3)):
                num(f"{k}.{c}", r[c], fe, nd, c == "var_pct")
            num(f"{k}.IC_lo", pct(r["IC95_lo"]), fe, 0, True)
            num(f"{k}.IC_hi", pct(r["IC95_hi"]), fe, 0, True)
        num(f"v4.entorno.{dom}.n_estadio_sobrevive_BH", int((~e["estadio"].str.startswith("3") & (e["p_BH"] < .05)).sum()), fe, 0)
        num(f"v4.entorno.{dom}.n_estadio_testes", int((~e["estadio"].str.startswith("3") & e["p_BH"].notna()).sum()), fe, 0)
        pp = RV(dom, "entorno_pareado.csv")
        for _, r in pp[pp["estadio"].str.startswith("3")].iterrows():
            for c in ("DiD_IRR", "IC95_lo", "IC95_hi"):
                num(f"v4.entorno_pareado.{dom}.{r['desfecho']}.{r['janela']}.{c}", pct(r[c]), fonte(dom, "entorno_pareado.csv"), 0, True)
        ra = RV(dom, "entorno_raio.csv")
        for _, r in ra.iterrows():
            num(f"v4.raio.{dom}.{r['desfecho']}.{r['janela']}.{int(r['raio_km'])}", r["var_pct"], fonte(dom, "entorno_raio.csv"), 0, True)
    st = RV("crimes", "entorno_furtos_subtipos.csv")
    for _, r in st.iterrows():
        num(f"v4.subtipo.{r['desfecho']}.{r['janela']}", r["var_pct"], fonte("crimes", "entorno_furtos_subtipos.csv"), 0, True)
        num(f"v4.subtipo.{r['desfecho']}.{r['janela']}.p_BH", r["p_BH_subtipos"], fonte("crimes", "entorno_furtos_subtipos.csv"), 3)
    sh = RV("crimes", "entorno_furtos_sem_hora.csv")
    fs = fonte("crimes", "entorno_furtos_sem_hora.csv")
    for i, nm in enumerate(("a_fracao_sem_hora", "b_todos", "b_com_hora", "c_janelas")):
        r = sh.iloc[i]
        if not np.isnan(r["OR_ou_RR_dia_jogo"]):
            num(f"v4.semhora.{nm}.razao", r["OR_ou_RR_dia_jogo"], fs, 2)
            num(f"v4.semhora.{nm}.p", r["p"], fs, 3)
        num(f"v4.semhora.{nm}.excesso_por_jogo", r["excesso_por_jogo"], fs, 1)
    dr = RV("crimes", "entorno_drade.csv").set_index("estadio")
    num("v4.drade.bos_3discos", dr.loc["3 discos", "BOs_DRADE_disco_3km"], fonte("crimes", "entorno_drade.csv"), 0)
    # Metodologia: falhas do INMET (mesma regra do 33: chuva ausente -> 0 + indicador; temperatura interpolada ate 24 h)
    fh = pd.read_csv(os.path.join(BASE, "data", "gold", "fato_hora_sp.csv"), usecols=["chuva_mm", "temp_c"])
    num("inmet.horas_sem_chuva", int(fh["chuva_mm"].isna().sum()), "data/gold/fato_hora_sp.csv", 0)
    num("inmet.horas_sem_temp", int(fh["temp_c"].isna().sum()), "data/gold/fato_hora_sp.csv", 0)
    num("inmet.horas_sem_temp_apos_interp", int(fh["temp_c"].interpolate(limit=24).isna().sum()), "data/gold/fato_hora_sp.csv", 0)
    ev = pd.read_csv(os.path.join(BASE, "data", "bronze", "jogos_grande_publico_sem_times_monitorados.csv"))
    num("eventos_grande_publico.n", len(ev), "data/bronze/jogos_grande_publico_sem_times_monitorados.csv", 0)
    num("copa2022.n_jogos", len(cp), "revisao/copa2022_exclusao.csv", 0)
    # parametros fixos dos scripts (configuracao, nao resultado)
    num("cfg.placebo_sorteios", 1000, "scripts/36_revisao_parecer.py (N_PLACEBO)", 0)
    num("cfg.bootstrap", 1000, "scripts/36_revisao_parecer.py (N_BOOT) e 34 (bootstrap da ablacao)", 0)
    for k_, v_ in (("n_estimators", 400), ("max_depth", 4), ("learning_rate", 0.05), ("subsample", 0.8),
                   ("min_child_weight", 5)):
        num(f"cfg.xgb.{k_}", v_, "scripts/34_preditivo_janelas.py (XGB_PARAMS)", 2 if isinstance(v_, float) else 0)
    num("cfg.prophet.fourier_diaria", 8, "scripts/34_preditivo_janelas.py (prev_prophet)", 0)
    num("cfg.prophet.fourier_mensal", 3, "scripts/34_preditivo_janelas.py (prev_prophet)", 0)


def gera_tudo_v4():
    tab_janelas_v4()
    tab_robustez_v4()
    tab_canal_v4()
    tab_pico_v4()
    tab_preditivo_v4()
    tab_risco_v4()
    fig_event_study_v4()
    fig_entorno_v4()
    numeros_extras_v4()


if __name__ == "__main__":
    if ARTIGO == "entrega3":
        tab_janelas()
        tab_pre()
        tab_canal()
        tab_preditivo()
        tab_risco()
        fig_event_study()
        fig_entorno()
        numeros_extras()
        tab_pico()  # V3 (2026-11-19): depois de numeros_extras para preservar a ordem dos numeros antigos
    else:
        gera_tudo_v4()
    pd.DataFrame(NUMS).to_csv(os.path.join(NUM_DIR, NUM_FILE), index=False)
    print(f"[ok] {len(NUMS)} números, tabelas e figuras em {ART}")
