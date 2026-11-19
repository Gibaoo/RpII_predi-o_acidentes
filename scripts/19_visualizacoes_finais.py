"""
19_visualizacoes_finais.py
Etapa 24 do roteiro -- VISUALIZACOES FINAIS (secao 24 do briefing_original.md,
15 itens exigidos).

Nao recalcula nenhuma estatistica: 13 dos 15 itens ja existem como figuras
publicadas em etapas anteriores (EDA, Etapa 7, 13, 14, 16, 18) -- este script
so (a) gera os 2 itens que nunca tinham virado figura (classico vs comum,
diurno vs noturno -- a Etapa 7 so publicou tabela para esses recortes) e
(b) monta um indice/galeria com link para os 15, citando a etapa de origem
de cada um. Reusa o MESMO dado e a MESMA exclusao de dias censurados/lacuna
ja decidida na Etapa 7 -- so troca a visualizacao (violino, mesmo estilo já
usado em `04_analise_jogo_vs_naojogo.py`), sem reabrir a analise estatística.

Rodar depois da Etapa 7 (le `data/gold/fato_dia_sp.csv`).
"""
import os
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
REPORTS = os.path.join(BASE_DIR, "reports")
OUT_DIR = os.path.join(REPORTS, "etapa24")
FIG_DIR = os.path.join(OUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

# mesma exclusao de dias censurados/lacuna de registro decidida na Etapa 7
EXCL_CRIME = {pd.Timestamp("2023-12-30"), pd.Timestamp("2023-12-31")}
EXCL_ACID = EXCL_CRIME | {pd.Timestamp("2022-01-17"), pd.Timestamp("2023-08-07")}

_md = []


def w(s=""):
    _md.append(s)


def savefig(name):
    p = os.path.join(FIG_DIR, name)
    plt.savefig(p)
    plt.close()
    return os.path.relpath(p, OUT_DIR).replace("\\", "/")


def carrega():
    d = pd.read_csv(GOLD_PATH, parse_dates=["data"])
    return d


# ---------------------------------------------------------------------------
def figura_recorte(d, mask_col, label_a, label_b, nome_arquivo, titulo):
    """Violino do recorte DENTRO dos dias de jogo (mesmo filtro/exclusao da
    Etapa 7 `secao_recortes`), para os 2 alvos principais do projeto."""
    dc = d[~d["data"].isin(EXCL_CRIME)]
    da = d[~d["data"].isin(EXCL_ACID)]
    cols = [("crimes_violentos", dc), ("acidentes_com_vitima", da)]

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, (col, base) in zip(axes, cols):
        sub = base[base["tem_jogo_sp"] == True].copy()
        g1 = sub.loc[sub[mask_col] == True, col].dropna()
        g0 = sub.loc[sub[mask_col] == False, col].dropna()
        parts = ax.violinplot([g0, g1], showmedians=True)
        ax.set_xticks([1, 2])
        ax.set_xticklabels([f"{label_b}\n(n={len(g0)})", f"{label_a}\n(n={len(g1)})"])
        ax.set_title(col)
        ax.grid(axis="y", alpha=.3)
    fig.suptitle(titulo, fontsize=10)
    return savefig(nome_arquivo)


GALERIA = [
    (1, "Série temporal de crimes", "reports/eda/figures/05_ts_crimes.png", "EDA (Etapa 6)"),
    (2, "Série temporal de acidentes", "reports/eda/figures/06_ts_acidentes.png", "EDA (Etapa 6)"),
    (3, "Jogos ao longo do tempo", "reports/eda/figures/07_ts_jogos.png", "EDA (Etapa 6)"),
    (4, "Crimes em dias com/sem jogos", "reports/etapa7/figures/01_dist_crime.png", "Etapa 7"),
    (5, "Acidentes em dias com/sem jogos", "reports/etapa7/figures/01_dist_acidente.png", "Etapa 7"),
    (6, "Clássico vs jogo comum", "reports/etapa24/figures/00_classico_vs_comum.png", "Etapa 24 (novo -- Etapa 7 só tinha tabela)"),
    (7, "Jogo diurno vs noturno", "reports/etapa24/figures/01_noturno_vs_diurno.png", "Etapa 24 (novo -- Etapa 7 só tinha tabela)"),
    (8, "Heatmap por dia da semana × mês (adaptado — sem granularidade horária na base)",
     "reports/eda/figures/11_heatmap_crimes.png / 12_heatmap_acidentes.png", "EDA (Etapa 6)"),
    (9, "Distribuição de ocorrências", "reports/eda/figures/02_hist_contagens.png", "EDA (Etapa 6)"),
    (10, "Importância das features (total_gain XGBoost)",
     "reports/etapa14/figures/03_importancia_crimes_violentos.png / 03_importancia_acidentes_com_vitima.png", "Etapa 14"),
    (11, "SHAP summary plot (beeswarm)",
     "reports/etapa18/figures/00_beeswarm_crimes_violentos_regressao.png / 00_beeswarm_acidentes_com_vitima_regressao.png / 02_beeswarm_acidentes_com_vitima_classificacao.png",
     "Etapa 18"),
    (12, "Matriz de confusão",
     "reports/etapa16/figures/00_matriz_confusao_crimes_violentos.png / 01_matriz_confusao_acidentes_com_vitima.png", "Etapa 16"),
    (13, "Curva Precision-Recall", "reports/etapa14/figures/01_roc_pr_modelos.png", "Etapa 14 (combinada com ROC)"),
    (14, "Curva ROC", "reports/etapa14/figures/01_roc_pr_modelos.png", "Etapa 14 (combinada com PR)"),
    (15, "Previsão vs observado", "reports/etapa14/figures/02_melhor_regressao.png", "Etapa 14"),
]


def main():
    d = carrega()
    w("# Etapa 24 -- Visualizações finais (galeria dos 15 itens do briefing)\n")
    w(f"_Gerado por `scripts/19_visualizacoes_finais.py` em {date.today()}. "
      "13 dos 15 itens já existiam como figuras publicadas em etapas "
      "anteriores -- este script só gera os 2 que faltavam (itens 6 e 7, "
      "clássico e noturno, que a Etapa 7 só tinha publicado como tabela) "
      "e monta o índice abaixo, citando a etapa de origem de cada figura._\n")

    print("[figuras] classico vs comum ...")
    fig6 = figura_recorte(d, "classico", "clássico", "comum",
                          "00_classico_vs_comum.png",
                          "Clássico vs jogo comum (dentro dos dias de jogo, mesmos dados da Etapa 7)")
    print("[figuras] noturno vs diurno ...")
    fig7 = figura_recorte(d, "jogo_noturno", "noturno", "diurno",
                          "01_noturno_vs_diurno.png",
                          "Jogo noturno vs diurno (dentro dos dias de jogo, mesmos dados da Etapa 7)")

    w("## Índice (15 itens do briefing §24)\n")
    w("| # | Visualização | Arquivo(s) | Origem |")
    w("| --- | --- | --- | --- |")
    for n, nome, arq, origem in GALERIA:
        w(f"| {n} | {nome} | `{arq}` | {origem} |")
    w("")
    w("## Novas figuras (itens 6 e 7)\n")
    w("Violino dentro dos dias de jogo (mesmo filtro/exclusão de dias "
      "censurados da Etapa 7 -- `secao_recortes`), para os 2 alvos "
      "principais do projeto. Números (médias, Mann-Whitney p, effect "
      "size) já publicados em `reports/etapa7/tabelas/recorte_classico.csv` "
      "e `recorte_jogo_noturno.csv` -- nenhum teste recalculado aqui, só a "
      "visualização que faltava.\n")
    w(f"![classico vs comum]({fig6})\n")
    w(f"![noturno vs diurno]({fig7})\n")
    w("**Leitura** (já registrada na Etapa 7/23): nenhuma diferença é "
      "significativa após correção de múltiplas comparações para os 2 "
      "alvos principais -- os violinos mostram visualmente a sobreposição "
      "quase total das distribuições.\n")
    w("## Nota sobre o item 8 (heatmap dia da semana × horário)\n")
    w("O briefing pede heatmap por dia da semana **e horário**; a unidade "
      "de análise do projeto é 1 dia (Etapa 4), sem granularidade horária "
      "para crime/acidente -- adaptado para dia da semana × **mês** (já "
      "feito na EDA, Etapa 6), que é a granularidade temporal mais fina "
      "disponível de forma consistente nas 3 fontes principais. Declarado "
      "como adaptação, não substituição silenciosa (Regra 10).\n")

    path = os.path.join(OUT_DIR, "galeria_visualizacoes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")


if __name__ == "__main__":
    main()
