"""
20_figura_artigo.py
Gera as figuras usadas no artigo final (docs/rpII_predicao_acidentes.tex),
a partir dos CSVs ja publicados nas Etapas 15-18 -- nenhum calculo novo,
so consolidacao visual para a Secao 4 (Resultados) e 5 (Discussao) do artigo.

Nao e uma "Etapa" nova do roteiro -- e material de apoio ao relatorio final
(§25), reunido aqui para poder ser regenerado se algum numero de origem mudar.
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(BASE_DIR, "reports")
OUT_DIR = os.path.join(BASE_DIR, "docs", "figuras")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "font.size": 10})


def rd(rel):
    return pd.read_csv(os.path.join(REPORTS, rel))


def figura_futebol_liquido():
    modelos = [
        ("crimes_violentos\n(regressão)", "etapa18/tabelas/shap_grupo_crimes_violentos_regressao.csv"),
        ("acidentes_com_vitima\n(regressão)", "etapa18/tabelas/shap_grupo_acidentes_com_vitima_regressao.csv"),
        ("acidentes_com_vitima\n(classificação)", "etapa18/tabelas/shap_grupo_acidentes_com_vitima_classificacao.csv"),
    ]
    brutos, liquidos, nomes = [], [], []
    for nome, arq in modelos:
        tab = rd(arq)
        fut = tab[tab.grupo == "futebol"].iloc[0]
        nomes.append(nome)
        brutos.append(fut["pct_%"])
        liquidos.append(fut["soma_sem_artefato"] / tab["soma_mean_abs_shap"].sum() * 100)

    x = np.arange(len(nomes))
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.bar(x - 0.18, brutos, width=0.35, label="futebol bruto (% do SHAP total)", color="#c44e52")
    ax.bar(x + 0.18, liquidos, width=0.35, label="futebol líquido\n(após auditoria de colinearidade)", color="#4c72b0")
    for i, (b, l) in enumerate(zip(brutos, liquidos)):
        ax.text(i - 0.18, b + 0.5, f"{b:.1f}%", ha="center", fontsize=8)
        ax.text(i + 0.18, l + 0.5, f"{l:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(nomes, fontsize=9)
    ax.set_ylabel("% do SHAP total atribuído ao grupo futebol")
    ax.set_ylim(0, max(brutos) * 1.25)
    ax.legend(fontsize=8, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    path = os.path.join(OUT_DIR, "futebol_liquido.png")
    plt.savefig(path)
    plt.close()
    print(f"[ok] {path}")


def figura_pipeline():
    """Diagrama simples das 4 etapas do pipeline, referenciado em
    metodologia.tex (Figura fig:pipeline)."""
    fig, ax = plt.subplots(figsize=(8.5, 2.2))
    etapas = ["1. Integração\nde dados", "2. Análise\nexploratória e causal",
             "3. Definição do alvo\ne engenharia de atributos", "4. Modelagem\npreditiva"]
    n = len(etapas)
    box_w, box_h, gap = 1.8, 1.0, 0.5
    for i, txt in enumerate(etapas):
        x = i * (box_w + gap)
        ax.add_patch(plt.Rectangle((x, 0), box_w, box_h, fill=True,
                                   facecolor="#dbe7f5", edgecolor="#4c72b0", linewidth=1.3))
        ax.text(x + box_w / 2, box_h / 2, txt, ha="center", va="center", fontsize=8.5, wrap=True)
        if i < n - 1:
            ax.annotate("", xy=(x + box_w + gap - 0.05, box_h / 2),
                       xytext=(x + box_w + 0.05, box_h / 2),
                       arrowprops=dict(arrowstyle="->", lw=1.3, color="#333333"))
    ax.set_xlim(-0.1, n * (box_w + gap) - gap + 0.1)
    ax.set_ylim(-0.1, box_h + 0.1)
    ax.axis("off")
    path = os.path.join(OUT_DIR, "pipeline.png")
    plt.savefig(path)
    plt.close()
    print(f"[ok] {path}")


def figura_mae_por_fold():
    """Reusa a mesma figura ja publicada na Etapa 15 (so copia para docs/figuras/
    com nome estavel, sem recalcular)."""
    import shutil
    src = os.path.join(REPORTS, "etapa15", "figures", "01_mae_por_fold.png")
    dst = os.path.join(OUT_DIR, "mae_por_fold.png")
    shutil.copyfile(src, dst)
    print(f"[ok] {dst} (copiado de {src})")


def figura_confusao():
    import shutil
    src = os.path.join(REPORTS, "etapa16", "figures", "01_matriz_confusao_acidentes_com_vitima.png")
    dst = os.path.join(OUT_DIR, "matriz_confusao_acidentes.png")
    shutil.copyfile(src, dst)
    print(f"[ok] {dst} (copiado de {src})")


def figura_beeswarm():
    import shutil
    src = os.path.join(REPORTS, "etapa18", "figures", "02_beeswarm_acidentes_com_vitima_classificacao.png")
    dst = os.path.join(OUT_DIR, "shap_beeswarm_acidentes.png")
    shutil.copyfile(src, dst)
    print(f"[ok] {dst} (copiado de {src})")


if __name__ == "__main__":
    figura_futebol_liquido()
    figura_pipeline()
    figura_mae_por_fold()
    figura_confusao()
    figura_beeswarm()
