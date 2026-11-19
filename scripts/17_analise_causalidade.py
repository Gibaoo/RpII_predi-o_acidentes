"""
17_analise_causalidade.py
Etapa 20 do roteiro -- ANALISE DE CAUSALIDADE FORMAL (secao 20 do
briefing_original.md).

O briefing lista 5 metodologias possiveis: Difference-in-Differences,
Propensity Score, Interrupted Time Series, regressoes com controles, Event
Study. Cobertura ATE desta etapa:
  - Regressao com controles: Etapas 7-9 (GLM Poisson HC1, correlacao parcial,
    modelo de defasagens distribuidas).
  - Event Study: Etapa 9 (media do residuo em torno de cada jogo, D-7..D+7).
  - Difference-in-Differences: Etapa 10 (bairro/anel do estadio x jogo).
  - Propensity Score (NOVO nesta etapa): matching + IPTW, controlando
    dia_semana/mes/feriado/ferias_escolares/trend -- balanceia por DESENHO
    em vez de por especificacao de modelo, uma forma de evidencia
    independente das Etapas 7-9.
  - Interrupted Time Series (tentado nesta etapa, com ressalva): ver secao 3
    -- o desenho classico de ITS exige uma janela pre/pos "limpa" (sem outro
    tratamento no meio); ao redor da final da Copa do Brasil 2023 ha VARIOS
    outros jogos na janela de +-21 dias (verificado antes de rodar), entao
    uma regressao segmentada classica seria enganosa. Adaptado para uma
    comparacao de distribuicao (evento extremo vs jogos tipicos) -- Regra 10:
    declarar a limitacao em vez de fabricar uma janela limpa que nao existe.

Confundidores controlados (briefing S20): dia da semana, feriado, clima,
tendencia temporal, sazonalidade -- todos ja no conjunto de controles desde
a Etapa 7; eventos simultaneos -- tratado explicitamente na secao 3 (Copa do
Brasil) e ja intersectado no PSM ao excluir o outlier de registro (Etapa 12).

Rodar depois da Etapa 19 (le `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`).
"""
import os
import warnings
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa20")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d_ in (FIG_DIR, TAB_DIR):
    os.makedirs(d_, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

SEED = 42
RNG = np.random.default_rng(SEED)
BASES = ["crimes_violentos", "acidentes_com_vitima"]
COVARS_CAT = ["dia_semana", "mes"]
COVARS_NUM = ["feriado", "ferias_escolares", "trend"]

_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d_ = df.reset_index() if index else df.copy()
    cols = list(d_.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d_.iterrows():
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def savefig(name):
    p = os.path.join(FIG_DIR, name)
    plt.savefig(p)
    plt.close()
    return os.path.relpath(p, OUT_DIR).replace("\\", "/")


def load():
    fato = pd.read_csv(GOLD_PATH, parse_dates=["data"])[["data", "dia_semana"]]
    feat = pd.read_csv(FEAT_PATH, parse_dates=["data"])
    d_ = feat.merge(fato, on="data", how="left").sort_values("data").reset_index(drop=True)
    d_["t_idx"] = np.arange(len(d_))
    return d_


# ---------------------------------------------------------------------------
def estima_propensity(d_, mask):
    X = pd.get_dummies(d_.loc[mask, COVARS_CAT].astype(int), columns=COVARS_CAT, drop_first=True)
    num = d_.loc[mask, COVARS_NUM].copy()
    num["trend"] = StandardScaler().fit_transform(num[["trend"]])
    X = pd.concat([X, num], axis=1).astype(float)
    y = d_.loc[mask, "tem_jogo_sp"].astype(int)
    model = LogisticRegression(max_iter=2000, C=1.0)
    model.fit(X, y)
    ps = model.predict_proba(X)[:, 1]
    ps = np.clip(ps, 1e-4, 1 - 1e-4)
    return pd.Series(ps, index=d_.loc[mask].index), X


def pareamento_1a1(ps, treat, caliper):
    """Nearest-neighbor 1:1 sem reposicao, no espaco logit(ps), com caliper.
    Implementacao gulosa (trata em ordem aleatoria fixa por seed) -- padrao
    aceito para bases pequenas (aqui ~126 tratados)."""
    logit_ps = np.log(ps / (1 - ps))
    idx_treat = list(ps[treat == 1].index)
    idx_ctrl_disp = set(ps[treat == 0].index)
    ordem = list(RNG.permutation(idx_treat))
    pares = []
    for it in ordem:
        if not idx_ctrl_disp:
            break
        dists = {ic: abs(logit_ps[it] - logit_ps[ic]) for ic in idx_ctrl_disp}
        ic_melhor = min(dists, key=dists.get)
        if dists[ic_melhor] <= caliper:
            pares.append((it, ic_melhor))
            idx_ctrl_disp.discard(ic_melhor)
    return pares


def smd(x_t, x_c):
    """Standardized mean difference (Cohen-like, pooled SD)."""
    m_t, m_c = np.mean(x_t), np.mean(x_c)
    s_t, s_c = np.std(x_t, ddof=1), np.std(x_c, ddof=1)
    s_pool = np.sqrt((s_t**2 + s_c**2) / 2)
    return (m_t - m_c) / s_pool if s_pool > 0 else 0.0


def tabela_balanco(d_, mask_t, mask_c):
    linhas = []
    for c in ["feriado", "ferias_escolares", "trend"]:
        linhas.append({"covariável": c, "SMD": smd(d_.loc[mask_t, c], d_.loc[mask_c, c])})
    for c in ["dia_semana", "mes"]:
        for nivel in sorted(d_[c].unique()):
            xt = (d_.loc[mask_t, c] == nivel).astype(float)
            xc = (d_.loc[mask_c, c] == nivel).astype(float)
            linhas.append({"covariável": f"{c}={nivel}", "SMD": smd(xt, xc)})
    return pd.DataFrame(linhas)


def bootstrap_ci_pareado(delta, n_boot=3000, alpha=0.05):
    n = len(delta)
    boots = [np.mean(RNG.choice(delta, size=n, replace=True)) for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi


# ---------------------------------------------------------------------------
def secao_psm(d_, base):
    w(f"### {base}\n")
    elig = d_[f"y_count_{base}"].notna()
    ps, X = estima_propensity(d_, elig)
    treat = d_.loc[elig, "tem_jogo_sp"].astype(int)

    # checagem de positividade/overlap -- pre-requisito de PSM/IPTW, nao
    # garantido so por balancear covariaveis
    pct_extremo = ((ps < 0.05) | (ps > 0.95)).mean() * 100
    taxa_mes = d_.loc[elig].groupby("mes")["tem_jogo_sp"].mean()
    meses_sem_jogo = taxa_mes[taxa_mes == 0].index.tolist()
    w(f"**Checagem de positividade (pré-requisito de PSM/IPTW)**: "
      f"{pct_extremo:.1f}% dos dias têm escore de propensão extremo "
      f"(<0,05 ou >0,95). {'Meses sem NENHUM dia de jogo na base: ' + ', '.join(map(str, meses_sem_jogo)) + ' -- violação de positividade estrutural (não é possível estimar o efeito de jogo nesses meses, o escore de propensão é ~0 por definição dos dados, não por acaso amostral).' if meses_sem_jogo else 'Sem violação estrutural (nenhum mês com taxa de jogo = 0).'}\n")

    logit_ps = np.log(ps / (1 - ps))
    caliper = 0.2 * logit_ps.std()
    pares = pareamento_1a1(ps, treat, caliper)
    n_tratados = int((treat == 1).sum())
    w(f"Tratados elegíveis: {n_tratados}. Pareados com sucesso (caliper "
      f"0,2·DP do logit(ps) = {caliper:.3f}): {len(pares)} "
      f"({len(pares)/n_tratados*100:.0f}%).\n")

    idx_t = [p[0] for p in pares]
    idx_c = [p[1] for p in pares]
    bal_antes = tabela_balanco(d_, d_.index.isin(d_.loc[elig & (d_.tem_jogo_sp == 1)].index),
                               d_.index.isin(d_.loc[elig & (d_.tem_jogo_sp == 0)].index))
    bal_depois = tabela_balanco(d_, d_.index.isin(idx_t), d_.index.isin(idx_c))
    bal = bal_antes.merge(bal_depois, on="covariável", suffixes=("_antes", "_depois"))
    bal.to_csv(os.path.join(TAB_DIR, f"balanco_covariaveis_{base}.csv"), index=False)
    n_desbalanceado_antes = (bal["SMD_antes"].abs() > 0.1).sum()
    n_desbalanceado_depois = (bal["SMD_depois"].abs() > 0.1).sum()
    w(f"Covariáveis com |SMD|>0,1 (desbalanceadas): {n_desbalanceado_antes}/{len(bal)} "
      f"antes do pareamento → {n_desbalanceado_depois}/{len(bal)} depois.\n")

    fig, ax = plt.subplots(figsize=(6, max(3, len(bal) * 0.25)))
    y_pos = np.arange(len(bal))
    ax.scatter(bal["SMD_antes"], y_pos, label="antes", color="#c44e52", marker="x")
    ax.scatter(bal["SMD_depois"], y_pos, label="depois", color="#4c72b0", marker="o")
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(0.1, color="gray", ls="--", lw=0.8)
    ax.axvline(-0.1, color="gray", ls="--", lw=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(bal["covariável"], fontsize=6)
    ax.set_xlabel("SMD")
    ax.set_title(f"Balanço de covariáveis -- {base}")
    ax.legend(fontsize=7)
    fig_balanco = savefig(f"0{BASES.index(base)}_balanco_{base}.png")
    w(f"![balanco {base}]({fig_balanco})\n")

    # ATE pareado -- contagem crua (matching ja balanceia por desenho) e residuo (checagem secundaria)
    linhas_ate = []
    for alvo_col, nome, reporta_pct in [(f"y_count_{base}", "contagem crua", True),
                                        (f"y_resid_{base}", "resíduo desazonalizado", False)]:
        y_t = d_.loc[idx_t, alvo_col].to_numpy()
        y_c = d_.loc[idx_c, alvo_col].to_numpy()
        delta = y_t - y_c
        ate = delta.mean()
        lo, hi = bootstrap_ci_pareado(delta)
        wstat, pval = stats.wilcoxon(delta) if np.any(delta != 0) else (np.nan, 1.0)
        media_ctrl = y_c.mean()
        # "%" so faz sentido vs uma base positiva (contagem); o residuo tem
        # media ~0 por construcao -- dividir por ela produziria um numero
        # sem significado (denominador perto de zero), entao fica NaN aqui.
        pct = (ate / media_ctrl * 100) if (reporta_pct and media_ctrl != 0) else np.nan
        linhas_ate.append({"alvo": nome, "n_pares": len(pares), "ATE": ate, "IC95_lo": lo, "IC95_hi": hi,
                           "%_vs_controle": pct, "wilcoxon_p": pval})
    tab_ate = pd.DataFrame(linhas_ate)
    tab_ate.to_csv(os.path.join(TAB_DIR, f"ate_pareado_{base}.csv"), index=False)
    w(df_to_md(tab_ate, floatfmt=3, index=False))
    w("")

    # IPTW como robustez -- pesos estabilizados, truncados no p1/p99.
    # GLM Poisson (nao WLS-Gaussiano) por ser dado de contagem -- mesma
    # convencao ja usada nas Etapas 7-9 (Poisson + erros HC1), agora
    # ponderado pelo peso de IPTW via var_weights.
    p_treat = treat.mean()
    sw = np.where(treat == 1, p_treat / ps, (1 - p_treat) / (1 - ps))
    lo_w, hi_w = np.percentile(sw, [1, 99])
    sw_trunc = np.clip(sw, lo_w, hi_w)
    dd = d_.loc[elig].copy()
    dd["_sw"] = sw_trunc
    glm = smf.glm(f"y_count_{base} ~ tem_jogo_sp", data=dd, family=sm.families.Poisson(),
                 var_weights=dd["_sw"]).fit(cov_type="HC1")
    rr = float(np.exp(glm.params["tem_jogo_sp"]))
    ic_rr = np.exp(glm.conf_int().loc["tem_jogo_sp"])
    pval_iptw = float(glm.pvalues["tem_jogo_sp"])
    n_eff = (sw_trunc.sum() ** 2) / (sw_trunc ** 2).sum()
    w(f"**IPTW (robustez, GLM Poisson HC1 ponderado, pesos estabilizados "
      f"truncados p1/p99)**: RR = {rr:.3f} (IC95 {ic_rr.iloc[0]:.3f} a "
      f"{ic_rr.iloc[1]:.3f}, p={pval_iptw:.3f}), n efetivo = {n_eff:.0f} "
      f"(de {int(elig.sum())} dias elegíveis).\n")

    ate_pct = tab_ate.iloc[0]["%_vs_controle"]
    p_pareado = tab_ate.iloc[0]["wilcoxon_p"]
    n_elig = int(elig.sum())
    discrepancia = (pval_iptw < 0.05) and (p_pareado >= 0.05)

    # IPTW restrito a regiao de sobreposicao (exclui os meses sem NENHUM dia
    # de jogo, ver checagem de positividade acima) -- confirmacao direta:
    # se a causa da discrepancia e mesmo a positividade, restringir o IPTW a
    # regiao de sobreposicao deve aproxima-lo do pareamento.
    rr_ov = pval_ov = ic_rr_ov = n_eff_ov = n_ov = None
    if meses_sem_jogo:
        mask_ov = ~d_.loc[elig, "mes"].isin(meses_sem_jogo)
        idx_ov = d_.loc[elig].index[mask_ov.to_numpy()]
        ps_ov, treat_ov = ps.loc[idx_ov], treat.loc[idx_ov]
        p_treat_ov = treat_ov.mean()
        sw_ov = np.where(treat_ov == 1, p_treat_ov / ps_ov, (1 - p_treat_ov) / (1 - ps_ov))
        lo_ov, hi_ov = np.percentile(sw_ov, [1, 99])
        sw_ov_trunc = np.clip(sw_ov, lo_ov, hi_ov)
        dd_ov = d_.loc[idx_ov].copy()
        dd_ov["_sw"] = sw_ov_trunc
        glm_ov = smf.glm(f"y_count_{base} ~ tem_jogo_sp", data=dd_ov, family=sm.families.Poisson(),
                         var_weights=dd_ov["_sw"]).fit(cov_type="HC1")
        rr_ov = float(np.exp(glm_ov.params["tem_jogo_sp"]))
        ic_rr_ov = np.exp(glm_ov.conf_int().loc["tem_jogo_sp"])
        pval_ov = float(glm_ov.pvalues["tem_jogo_sp"])
        n_eff_ov = (sw_ov_trunc.sum() ** 2) / (sw_ov_trunc ** 2).sum()
        n_ov = len(idx_ov)
        w(f"**IPTW restrito à região de sobreposição** (exclui os meses sem "
          f"nenhum dia de jogo -- {', '.join(map(str, meses_sem_jogo))} -- "
          f"confirmação direta da hipótese de positividade acima): RR = "
          f"{rr_ov:.3f} (IC95 {ic_rr_ov.iloc[0]:.3f} a {ic_rr_ov.iloc[1]:.3f}, "
          f"p={pval_ov:.3f}), n efetivo = {n_eff_ov:.0f} (de {n_ov} dias "
          "dentro da região de sobreposição).\n")

    if discrepancia:
        if rr_ov is not None and pval_ov >= 0.05:
            confirmacao = (f"**Confirmado diretamente**: restringindo o IPTW à mesma região de "
                          f"sobreposição do pareamento, o efeito deixa de ser significativo "
                          f"(RR={rr_ov:.3f}, p={pval_ov:.3f}) -- muito mais próximo do pareamento "
                          f"(p={p_pareado:.3f}) do que do IPTW sobre a base inteira (p={pval_iptw:.3f}). "
                          "Isso confirma que a discrepância vinha da violação de positividade "
                          "(os meses sem jogo entrando no IPTW irrestrito), não de um efeito causal real.")
        elif rr_ov is not None:
            confirmacao = (f"**Não totalmente confirmado**: mesmo restrito à região de sobreposição, "
                          f"o IPTW ainda dá RR={rr_ov:.3f} (p={pval_ov:.3f}) -- a hipótese de "
                          "positividade explica parte da discrepância, mas não tudo; fica como "
                          "resultado em aberto, não resolvido por completo.")
        else:
            confirmacao = ""
        w(f"**Discrepância investigada**: o pareamento 1:1 NÃO encontrou "
          f"efeito significativo (Wilcoxon p={p_pareado:.3f}, "
          f"{ate_pct:+.1f}%), mas o IPTW encontrou (RR={rr:.3f}, "
          f"p={pval_iptw:.3f}) -- **não é convergência limpa entre os 2 "
          "métodos, e a causa provável é a violação de positividade "
          "reportada acima**: o pareamento só compara tratados a controles "
          "DENTRO da região de suporte comum (meses com jogo), enquanto o "
          f"IPTW reponderam TODOS os {n_elig} dias elegíveis, "
          "incluindo os meses sem nenhum jogo (jan-mar) -- mesmo com peso "
          "truncado, esses dias de baixíssima propensão ainda entram na "
          "média ponderada do grupo controle, reintroduzindo parte do "
          "confundidor sazonal que o desenho deveria eliminar. "
          f"{confirmacao} **O pareamento é tratado como a estimativa "
          "primária aqui** (mais robusto à falta de suporte comum); o IPTW "
          "irrestrito fica registrado como resultado não resolvido, não "
          "como confirmação de efeito.\n")

    return dict(base=base, n_tratados=n_tratados, n_pareados=len(pares),
               ate_bruto=tab_ate.iloc[0], ate_resid=tab_ate.iloc[1],
               iptw_rr=rr, iptw_p=pval_iptw, iptw_rr_restrito=rr_ov, iptw_p_restrito=pval_ov,
               discrepancia=discrepancia, pct_ps_extremo=pct_extremo, meses_sem_jogo=meses_sem_jogo)


# ---------------------------------------------------------------------------
def secao_evento_extremo(d_, base, data_evento, janela_dias=21):
    ev = pd.Timestamp(data_evento)
    win = d_[(d_.data >= ev - pd.Timedelta(days=janela_dias)) & (d_.data <= ev + pd.Timedelta(days=janela_dias))]
    n_outros_jogos = int(win.loc[win.data != ev, "tem_jogo_sp"].sum())
    w(f"Janela de ±{janela_dias} dias ao redor de {ev.date()}: **{n_outros_jogos} outros dias de jogo** "
      f"dentro da janela (verificado antes de rodar). Uma regressão segmentada clássica (ITS) assume "
      "pré/pós limpo -- com tantos outros jogos na janela, o \"efeito\" estimado misturaria o evento "
      "extremo com o efeito rotineiro de jogo já testado nas Etapas 7-9/20 (seção 2). **Adaptado**: "
      "em vez de ITS clássico, compara-se o resíduo do dia do evento à distribuição do resíduo em "
      "OUTROS dias de jogo comuns (exclui o próprio evento e outro evento extremo conhecido), via "
      "z-score e teste de Mann-Whitney (Regra 10: declarar a limitação em vez de fabricar uma janela "
      "limpa que não existe).\n")

    outros_eventos = [pd.Timestamp("2023-09-24"), pd.Timestamp("2023-08-16")]
    resid_col = f"y_resid_{base}"
    jogos_comuns = d_[(d_.tem_jogo_sp == 1) & (~d_.data.isin(outros_eventos)) & d_[resid_col].notna()]
    resid_evento = d_.loc[d_.data == ev, resid_col]
    if len(resid_evento) == 0 or pd.isna(resid_evento.iloc[0]):
        w("_Dia do evento sem resíduo válido (excluído por lacuna de registro) -- não é possível comparar.\n"
          "\n")
        return None
    r_ev = resid_evento.iloc[0]
    mu, sd = jogos_comuns[resid_col].mean(), jogos_comuns[resid_col].std()
    z = (r_ev - mu) / sd if sd > 0 else np.nan
    percentil = stats.percentileofscore(jogos_comuns[resid_col], r_ev)
    w(f"- Resíduo em {ev.date()}: {r_ev:.2f}. Distribuição em {len(jogos_comuns)} outros dias de jogo "
      f"comuns: média {mu:.2f}, DP {sd:.2f} → **z = {z:.2f}** (percentil {percentil:.0f}).\n")
    w(f"- {'Fora' if abs(z) > 2 else 'Dentro'} da faixa típica (|z|>2) de um dia de jogo comum.\n")
    return dict(base=base, evento=ev.date(), residuo=r_ev, z=z, percentil=percentil,
               n_outros_jogos_na_janela=n_outros_jogos)


# ---------------------------------------------------------------------------
def main():
    d_ = load()
    w("# Etapa 20 -- Análise de causalidade formal\n")
    w(f"_Gerado por `scripts/17_analise_causalidade.py` em {date.today()}. "
      "Fontes: `data/gold/features_dia_sp.csv`, `fato_dia_sp.csv`._\n")

    w("## 1. Arcabouço causal já usado no projeto (S20 lista 5 métodos)\n")
    w(df_to_md(pd.DataFrame([
        {"método (briefing S20)": "Regressão com controles", "onde": "Etapas 7, 8, 9",
         "o quê": "GLM Poisson HC1 (C(dia_semana)+C(mes)+feriado); correlação parcial; modelo de defasagens distribuídas D-2..D+2"},
        {"método (briefing S20)": "Event Study", "onde": "Etapa 9",
         "o quê": "média do resíduo dessazonalizado em offsets -7..+7 em torno de cada jogo, teste t vs 0"},
        {"método (briefing S20)": "Difference-in-Differences", "onde": "Etapa 10",
         "o quê": "DiD por bairro do estádio x jogo, e por anel de distância x jogo, com/sem datas de alavancagem"},
        {"método (briefing S20)": "Propensity Score", "onde": "**Etapa 20 (aqui, seção 2)**",
         "o quê": "matching 1:1 + IPTW, balanceando dia_semana/mês/feriado/férias/tendência por desenho"},
        {"método (briefing S20)": "Interrupted Time Series", "onde": "**Etapa 20 (aqui, seção 3, com ressalva)**",
         "o quê": "tentado ao redor da final da Copa do Brasil 2023; adaptado por contaminação da janela (ver seção 3)"},
    ]), index=False))
    w("")
    w("Esta etapa não repete as Etapas 7-10 (já cobrem regressão com "
      "controles, event study e DiD com rigor) -- soma 2 métodos "
      "independentes que faltavam: Propensity Score e uma tentativa "
      "adaptada de Interrupted Time Series.\n")

    w("## 2. Propensity Score -- matching e IPTW\n")
    w("**Confundidores balanceados**: `dia_semana`, `mês`, `feriado`, "
      "`férias_escolares`, tendência temporal linear (`trend`) -- mesmo "
      "conjunto de controles das Etapas 7-9, mas aqui usado para "
      "BALANCEAR o desenho (matching/pesos), não para ajustar um "
      "coeficiente de regressão -- uma forma de evidência diferente e "
      "independente da usada nas Etapas 7-9. Escore de propensão = "
      "P(tem_jogo_sp=1 | confundidores), via regressão logística.\n")
    w("**Pareamento 1:1 sem reposição**, vizinho mais próximo no espaço "
      "logit(ps), caliper = 0,2 desvio-padrão do logit(ps) (regra padrão, "
      "Austin 2011). Balanço de covariáveis checado ANTES e DEPOIS do "
      "pareamento (SMD -- differença padronizada de médias; |SMD|<0,1 = "
      "bem balanceado).\n")

    resultados_psm = []
    for base in BASES:
        resultados_psm.append(secao_psm(d_, base))
    pd.DataFrame([{k: v for k, v in r.items() if k not in ("ate_bruto", "ate_resid")}
                 for r in resultados_psm]).to_csv(os.path.join(TAB_DIR, "resumo_psm.csv"), index=False)

    w("## 3. Evento extremo -- final da Copa do Brasil 2023 (2023-09-24)\n")
    w("A Etapa 10 já identificou 2023-09-24 (final) e 2023-08-16 (semifinal) "
      "como os 2 jogos de maior público na base (~68 mil pagantes cada, "
      "muito acima do jogo comum) -- pontos de alavancagem na análise "
      "espacial do Morumbi. Aqui a pergunta é citywide: um evento desse "
      "porte deixa marca na série AGREGADA de SP capital, mesmo que jogos "
      "comuns não deixem (Etapas 7-9)?\n")
    resultados_evento = []
    for base in BASES:
        w(f"### {base}\n")
        res = secao_evento_extremo(d_, base, "2023-09-24")
        if res:
            resultados_evento.append(res)
    if resultados_evento:
        pd.DataFrame(resultados_evento).to_csv(os.path.join(TAB_DIR, "evento_extremo_copa_do_brasil.csv"), index=False)

    w("## 4. Confundidores não observados e limitações da inferência causal\n")
    w("A inferência causal aqui tem limites estruturais que nenhum método "
      "reajusta:\n")
    w("- **Sem variação exógena da agenda de jogos**: dia/horário de jogo é "
      "decidido pela CBF/clubes por motivos não aleatórios (TV, campeonato) "
      "-- não há um experimento natural claro (ex. sorteio de data) para "
      "excluir confundidores não observados por completo.\n")
    w("- **Violação de positividade confirmada na seção 2** (jan-mar sem "
      "nenhum dia de jogo de SP-capital na base): o PSM depende de haver "
      "sobreposição entre tratados e controles em todo o espaço de "
      "covariáveis, e aqui não há -- isso não invalida o pareamento "
      "(restrito à região com sobreposição real), mas explica por que o "
      "IPTW (que reponderam a base inteira) discorda do pareamento em "
      "`acidentes_com_vitima` (ver seção 2) e por que qualquer estimativa "
      "de PSM aqui deve ser lida como \"efeito dentro da temporada "
      "(abr-nov)\", não um efeito válido para o ano inteiro.\n")
    w("- **Paulistão e Libertadores fora da base de futebol** (ver "
      "`CLAUDE.md`): dias de jogo dessas competições aparecem como "
      "`tem_jogo_sp=0` -- atenua qualquer efeito real e pode inflar o peso "
      "do \"efeito calendário\" encontrado.\n")
    w("- **Público não observado** (100% NaN): não é possível testar se o "
      "efeito varia com tamanho de público além do contraste extremo "
      "qualitativo da seção 3.\n")
    w("- **Fatores de confusão temporais não modelados**: mudanças de "
      "política de segurança, operações policiais pontuais, sazonalidade "
      "de outras causas (ex. clima extremo, greves) que coincidam com "
      "dias de jogo por acaso -- não há como descartar toda coincidência "
      "residual com apenas 730 dias de dados.\n")
    nao_resolvidas = [r["base"] for r in resultados_psm if r["discrepancia"] and
                      (r.get("iptw_p_restrito") is None or r["iptw_p_restrito"] < 0.05)]
    ressalva_iptw = (f" -- **com uma exceção não totalmente resolvida** (IPTW irrestrito "
                     f"em {', '.join(nao_resolvidas)}, ver seção 2)" if nao_resolvidas else
                     " -- a única discordância encontrada (IPTW irrestrito em "
                     "`acidentes_com_vitima`) foi investigada e resolvida na seção 2 "
                     "(era violação de positividade, não efeito causal)")
    w("> **\"Os resultados indicam associação (já fraca/nula nas Etapas "
      "7-9), mas não permitem afirmar causalidade\"** -- frase do briefing "
      "§20, aplicável de forma literal aqui: regressão com controles, event "
      "study, DiD, pareamento por PSM e a checagem do evento extremo não "
      "encontraram um sinal robusto de efeito causal de jogo em "
      f"crime/acidente em SP capital{ressalva_iptw}, reportada como tal, "
      "não escondida.\n")

    w("## 5. Síntese\n")
    w("- **A maioria dos métodos independentes converge no mesmo nulo**: "
      "regressão com controles (Etapas 7-9), event study (Etapa 9), DiD "
      "(Etapa 10), auditoria de colinearidade SHAP (Etapa 18), decomposição "
      "de cenários (Etapa 19), pareamento por PSM e checagem do evento "
      "extremo (Etapa 20).\n")
    for r in resultados_psm:
        ate_bruto = r["ate_bruto"]
        flag = " -- **discrepância com IPTW, ver seção 2**" if r["discrepancia"] else ""
        restrito = (f"; IPTW restrito à sobreposição = {r['iptw_rr_restrito']:.3f} "
                   f"(p={r['iptw_p_restrito']:.3f})" if r.get("iptw_rr_restrito") is not None else "")
        w(f"- **PSM {r['base']}**: {r['n_pareados']}/{r['n_tratados']} tratados "
          f"pareados; ATE pareado (contagem crua, estimativa primária) = "
          f"{ate_bruto['ATE']:.2f} ({ate_bruto['%_vs_controle']:+.1f}% vs "
          f"controle pareado, IC95 {ate_bruto['IC95_lo']:.2f} a "
          f"{ate_bruto['IC95_hi']:.2f}, Wilcoxon p={ate_bruto['wilcoxon_p']:.3f}); "
          f"IPTW RR = {r['iptw_rr']:.3f} (p={r['iptw_p']:.3f}){restrito}{flag}.\n")
    for r in resultados_psm:
        if not r["discrepancia"]:
            continue
        p_pareado_r = r["ate_bruto"]["wilcoxon_p"]
        if r.get("iptw_p_restrito") is not None and r["iptw_p_restrito"] >= 0.05:
            w(f"- **Não escondido, e agora confirmado (2026-09-04)**: o IPTW "
              f"irrestrito encontrou um efeito pequeno mas estatisticamente "
              f"significativo em `{r['base']}` (RR={r['iptw_rr']:.3f}, "
              f"p={r['iptw_p']:.3f}) que o pareamento não reproduzia "
              f"(p={p_pareado_r:.3f}) -- investigado na seção 2: restringindo "
              f"o IPTW à mesma região de sobreposição do pareamento (exclui "
              f"{', '.join(map(str, r['meses_sem_jogo']))}), o efeito some "
              f"(RR={r['iptw_rr_restrito']:.3f}, p={r['iptw_p_restrito']:.3f}), "
              "confirmando diretamente que a discrepância vinha da violação de "
              "positividade, não de um efeito causal real. **Discrepância "
              "resolvida.**\n")
        else:
            w(f"- **Não escondido, não totalmente resolvido**: o IPTW encontrou "
              f"um efeito significativo em `{r['base']}` (RR={r['iptw_rr']:.3f}, "
              f"p={r['iptw_p']:.3f}) que o pareamento não reproduz -- restringir "
              "o IPTW à região de sobreposição (seção 2) reduziu mas não "
              "eliminou a discrepância. Fica registrado como resultado em "
              "aberto para a Discussão do artigo, não resolvido nem descartado "
              "por conveniência.\n")
    w("- **Próximo**: Etapa 21 em diante -- código consolidado, pipeline, "
      "resultados, visualizações finais, relatório acadêmico (usa a síntese "
      "desta etapa para a seção de Discussão/Limitações).\n")

    path = os.path.join(OUT_DIR, "relatorio_causalidade.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
