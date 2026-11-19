"""
10_baselines.py
Etapa 13 do roteiro -- BASELINES (Regra 9: sempre comparar modelos de ML contra
baseline; Regra 8: nao escolher modelo so pela Accuracy).

Regressao (prever a CONTAGEM, `y_count_<base>`):
  - media historica (constante = media do treino)
  - media movel (rollmean 7d e 28d, ja causais desde a Etapa 12)
  - mesmo dia da semana anterior (lag 7)

Classificacao (prever PICO):
  - sempre a classe majoritaria (nunca pico)
  - dia-da-semana de risco (heuristica calendario-only: marca como pico os dias
    da semana com maior taxa de pico NO TREINO -- conecta com o achado das
    Etapas 6-11 de que o calendario domina)
  - Logistic Regression (nao ponderada e com class_weight='balanced')

SPLIT TEMPORAL (Regra 7: nunca split aleatorio):
  corte fixo em 2023-10-01. TREINO = [inicio, corte); TESTE = [corte, fim].
  Sem embaralhar, sem folds sobrepostos aqui -- a validacao formal com multiplos
  folds e a Etapa 15.

CORRECAO DE VAZAMENTO (vai alem da Etapa 12): o alvo de pico usado aqui NAO e o
`y_pico_p90_<base>` do `features_dia_sp.csv` (esse foi definido com um ajuste de
calendario na SERIE INTEIRA). Aqui o modelo de calendario e o limiar P90 sao
REAJUSTADOS SO NO TREINO e aplicados ao teste -- a primeira vez no projeto que a
ressalva "reajustar por fold" (Etapas 8/9/11/12) e realmente executada.

Rodar depois de 09 (usa data/gold/features_dia_sp.csv e data/gold/fato_dia_sp.csv).
"""
import os
import textwrap
from datetime import date

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, confusion_matrix,
                             mean_absolute_error, mean_squared_error, r2_score,
                             precision_recall_curve, roc_curve)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "fato_dia_sp.csv")
FEAT_PATH = os.path.join(BASE_DIR, "data", "gold", "features_dia_sp.csv")
OUT_DIR = os.path.join(BASE_DIR, "reports", "etapa13")
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tabelas")
for d in (FIG_DIR, TAB_DIR):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 9})

CUTOFF = pd.Timestamp("2023-10-01")
BASES = ["crimes_violentos", "acidentes_com_vitima"]
CTRL = "t_idx + C(dia_semana) + C(mes) + feriado"

FEAT_GROUPS = {
    "temporal": ["trend", "sin_doy", "cos_doy", "sin_dow", "cos_dow"] +
                [f"dow_{k}" for k in range(7)] +
                ["dia_do_mes", "mes", "trimestre", "semana_ano", "fim_de_semana", "feriado",
                 "feriado_nacional", "feriado_estadual", "feriado_municipal", "vespera_feriado",
                 "periodo_letivo", "ferias_escolares", "recesso_escolar", "pos_feriado"],
    "futebol": ["tem_jogo_sp", "numero_jogos_sp", "classico", "jogo_noturno",
                "jogo_d_menos_1", "jogo_d_mais_1", "classico_d_menos_1", "classico_d_mais_1",
                "jogo_copa", "jogo_serie_a", "jogo_d_menos_2", "jogo_d_mais_2",
                "n_jogos_janela7", "dias_desde_jogo", "dias_ate_jogo",
                "jogo_x_fds", "jogo_x_noturno", "classico_x_fds"],
    "clima": ["temp_media", "temp_max", "temp_min", "precipitacao_total", "umidade_media",
              "vento_max", "chuva", "clima_missing", "temp_media_lag1",
              "precipitacao_total_lag1", "umidade_media_lag1"],
}
# historica (por base): lag1,2,3,7,14,28 + rollmean/rollstd 7,14,28 + lag1_vs_rollmean28
# + pico_p90_lag1/soma7 -- SEM lag364 (muito NaN no ano 1) e SEM resid_lag*/sazonal_esperado
# (dependem do ajuste na serie inteira, ver docstring).

_md = []


def w(s=""):
    _md.append(s)


def df_to_md(df, floatfmt=3, index=True):
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if pd.isna(v) else f"{v:,.{floatfmt}f}"
        return str(v)

    out = ["| " + " | ".join(map(str, cols)) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in d.iterrows():
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
    for c in [c for c in feat.columns if c.startswith("y_pico_")]:
        feat[c] = feat[c].map({"True": True, "False": False, True: True, False: False}).astype("boolean")
    d = feat.merge(fato, on="data", how="left").sort_values("data").reset_index(drop=True)
    d["t_idx"] = np.arange(len(d))
    return d


def hist_feats(base):
    return ([f"{base}_lag{L}" for L in (1, 2, 3, 7, 14, 28)] +
            [f"{base}_rollmean{R}" for R in (7, 14, 28)] +
            [f"{base}_rollstd{R}" for R in (7, 14, 28)] +
            [f"{base}_lag1_vs_rollmean28", f"pico_p90_{base}_lag1", f"pico_p90_{base}_soma7"])


# ---------------------------------------------------------------------------
def refit_pico_no_treino(d, base, train_mask):
    """Reajusta o modelo de calendario e o limiar P90 SO no treino; aplica a
    todo o dataset. Retorna (residuo, pred_calendario, thr_p90, y_pico)."""
    x = d[["data", "t_idx", "dia_semana", "mes", "feriado", f"y_count_{base}"]].copy()
    x = x.rename(columns={f"y_count_{base}": "y"})
    fit = smf.ols(f"y ~ {CTRL}", data=x.loc[train_mask].dropna(subset=["y"])).fit()
    pred = fit.predict(x)
    resid = x["y"] - pred
    thr = resid[train_mask & x["y"].notna()].quantile(0.90)
    y_pico = pd.Series(np.where(x["y"].notna(), resid > thr, np.nan), index=d.index).astype("boolean")
    return resid, pred, thr, y_pico, fit.rsquared


def secao_split(d):
    w("## 1. Split temporal\n")
    w(f"Corte fixo: **treino** = antes de {CUTOFF.date()}, **teste** = a partir de "
      f"{CUTOFF.date()} (sem embaralhar; validacao com multiplos folds = Etapa 15).\n")
    linhas, diag = [], []
    curvas_pred = {}
    for base in BASES:
        elig = d[f"y_count_{base}"].notna()
        train_mask = elig & (d["data"] < CUTOFF)
        test_mask = elig & (d["data"] >= CUTOFF)
        resid, pred, thr, y_pico, r2 = refit_pico_no_treino(d, base, train_mask)
        n_pico_tr = int((y_pico[train_mask]).sum())
        n_pico_te = int((y_pico[test_mask]).sum())
        linhas.append({"base": base, "n_treino": int(train_mask.sum()), "n_teste": int(test_mask.sum()),
                       "R2_calendario_treino": r2, "limiar_P90_treino": thr,
                       "pico_treino_%": n_pico_tr / train_mask.sum() * 100,
                       "pico_teste_%": n_pico_te / test_mask.sum() * 100})
        diag.append({"base": base,
                     "media_real_teste": d.loc[test_mask, f"y_count_{base}"].mean(),
                     "media_prevista_calendario_teste": pred[test_mask].mean(),
                     "residuo_medio_teste": resid[test_mask].mean(),
                     "residuo_medio_treino": resid[train_mask].mean()})
        curvas_pred[base] = (d.loc[test_mask, "data"], d.loc[test_mask, f"y_count_{base}"], pred[test_mask])
    w(df_to_md(pd.DataFrame(linhas), floatfmt=2, index=False))
    w("\n_O limiar P90 e o ajuste de calendario vem SO do treino; a % de pico no "
      "teste nao precisa ficar em 10% porque o limiar nao foi calibrado nele "
      "(esperado, e o preco de nao vazar o teste para a definicao do alvo) -- "
      "mas o desvio aqui e grande demais pra ser so isso. Ver 1.1._\n")

    w("### 1.1 Por que a prevalencia de pico no teste foge tanto de 10%\n")
    w(df_to_md(pd.DataFrame(diag), floatfmt=2, index=False))
    w("")
    w(textwrap.dedent("""\
        O termo de **tendencia linear** (`t_idx`) do modelo de calendario, ajustado
        so ate set/2023, extrapola mal para out-dez/2023:
        - `crimes_violentos`: a previsao media do calendario no teste (558,5) fica
          MUITO acima do real (510,1) -> residuo medio de -48 no teste (vs 0 por
          construcao no treino) -> quase nenhum dia ultrapassa o limiar P90 do
          treino -> **prevalencia de pico cai pra 3,3%** (so 3 dias em 90).
        - `acidentes_com_vitima`: o oposto -- o calendario SUBESTIMA o teste
          (77,9 previsto vs 85,6 real) -> residuo medio de +7,7 -> muitos dias
          passam do limiar -> **prevalencia sobe pra 34,4%** (31 em 90).

        Isso NAO e um bug -- e uma demonstracao concreta de por que um unico corte
        temporal e fragil para series de 2 anos com tendencia: o `t_idx` linear
        extrapolado 3 meses a frente erra facil. **Consequencia pratica desta
        etapa**: com so 3 positivos no teste de `crimes_violentos`, qualquer
        metrica de classificacao para esse desfecho (secao 3) tem variancia
        enorme e deve ser lida como ilustrativa, nao conclusiva -- a Etapa 15
        (walk-forward, calendario reajustado em cada fold, metricas agregadas em
        varias janelas) e o que da uma leitura confiavel.
    """))
    fig, axes = plt.subplots(1, 2, figsize=(15, 4))
    for ax, base in zip(axes, BASES):
        dt, y, p = curvas_pred[base]
        ax.plot(dt, y, "k-", lw=1.2, label="observado")
        ax.plot(dt, p, color="#c44e52", lw=1.2, label="previsto so pelo calendario (ajustado no treino)")
        ax.set_title(base)
        ax.legend(fontsize=7)
        ax.tick_params(axis="x", rotation=30)
    w(f"![previsto vs real]({savefig('00_calendario_extrapolado.png')})\n")


# ---------------------------------------------------------------------------
def secao_regressao(d):
    w("## 2. Baselines de regressao (prever a contagem)\n")
    w("**H:** um modelo de ML (Etapa 14) so vale a pena se bater estes 3 "
      "baselines no teste. Metricas: MAE, RMSE, R^2 (vs media do PROPRIO teste), "
      "MAPE.\n")
    linhas = []
    for base in BASES:
        elig = d[f"y_count_{base}"].notna()
        train_mask = elig & (d["data"] < CUTOFF)
        test_mask = elig & (d["data"] >= CUTOFF)
        y_test = d.loc[test_mask, f"y_count_{base}"]
        y_train_mean = d.loc[train_mask, f"y_count_{base}"].mean()

        preds = {
            "media_historica": pd.Series(y_train_mean, index=y_test.index),
            "media_movel_7d": d.loc[test_mask, f"{base}_rollmean7"],
            "media_movel_28d": d.loc[test_mask, f"{base}_rollmean28"],
            "mesmo_dia_semana_ant": d.loc[test_mask, f"{base}_lag7"],
        }
        for nome, yhat in preds.items():
            m = yhat.notna() & y_test.notna()
            yt, yp = y_test[m], yhat[m]
            mae = mean_absolute_error(yt, yp)
            rmse = mean_squared_error(yt, yp) ** 0.5
            r2 = r2_score(yt, yp) if yt.nunique() > 1 else np.nan
            mape = (np.abs((yt - yp) / yt)).mean() * 100
            linhas.append({"base": base, "baseline": nome, "n": int(m.sum()),
                           "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE_%": mape})
    tab = pd.DataFrame(linhas)
    tab.to_csv(os.path.join(TAB_DIR, "baselines_regressao.csv"), index=False)
    for base in BASES:
        w(f"### {base}\n")
        w(df_to_md(tab[tab["base"] == base].drop(columns="base"), floatfmt=2, index=False))
        w("")
    w("_R^2 negativo e possivel e esperado para a media historica (constante do "
      "treino avaliada contra a variancia do teste) -- nao e bug._\n")

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.2))
    for ax, base in zip(axes, BASES):
        test_mask = d[f"y_count_{base}"].notna() & (d["data"] >= CUTOFF)
        sub = d.loc[test_mask]
        ax.plot(sub["data"], sub[f"y_count_{base}"], "k-", lw=1.3, label="observado")
        ax.plot(sub["data"], sub[f"{base}_rollmean7"], lw=1, label="media movel 7d")
        ax.plot(sub["data"], sub[f"{base}_lag7"], lw=1, ls="--", label="mesmo dia sem. ant.")
        ax.axhline(d.loc[(d["data"] < CUTOFF), f"y_count_{base}"].mean(), color="gray",
                   ls=":", label="media historica")
        ax.set_title(base)
        ax.legend(fontsize=7)
        ax.tick_params(axis="x", rotation=30)
    w(f"![baselines regressao]({savefig('01_baselines_regressao.png')})\n")


# ---------------------------------------------------------------------------
def secao_classificacao(d):
    w("## 3. Baselines de classificacao (prever pico)\n")
    w("**H0 implicita de cada baseline:** nao ha estrutura previsivel alem "
      "dela. Metricas: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC "
      "(Regra 8: nao julgar so pela Accuracy -- com ~10% de prevalencia, "
      "'nunca preve pico' ja acerta ~90%).\n")

    linhas, curvas = [], {}
    for base in BASES:
        elig = d[f"y_count_{base}"].notna()
        train_mask = elig & (d["data"] < CUTOFF)
        test_mask = elig & (d["data"] >= CUTOFF)
        resid, pred, thr, y_pico, _ = refit_pico_no_treino(d, base, train_mask)
        y_tr = y_pico[train_mask].astype(bool)
        y_te = y_pico[test_mask].astype(bool)
        prevalencia_teste = y_te.mean()

        def registra(nome, yhat_bin, score=None):
            row = {"base": base, "baseline": nome, "n_teste": len(y_te),
                  "n_pico_teste": int(y_te.sum()),
                  "accuracy": accuracy_score(y_te, yhat_bin),
                  "precision": precision_score(y_te, yhat_bin, zero_division=0),
                  "recall": recall_score(y_te, yhat_bin, zero_division=0),
                  "f1": f1_score(y_te, yhat_bin, zero_division=0)}
            if score is not None and y_te.nunique() > 1:
                row["roc_auc"] = roc_auc_score(y_te, score)
                row["pr_auc"] = average_precision_score(y_te, score)
            else:
                row["roc_auc"] = np.nan
                row["pr_auc"] = np.nan
            linhas.append(row)
            return row

        # 1. classe majoritaria
        registra("classe_majoritaria", pd.Series(False, index=y_te.index))

        # 2. dia-da-semana de risco (heuristica so-calendario, ajustada no treino)
        nomes_dow = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
        taxa_pico_dow = y_tr.groupby(d.loc[train_mask, "dia_semana"]).mean()
        dow_risco = taxa_pico_dow[taxa_pico_dow > y_tr.mean()].index.tolist()
        pred_dow = d.loc[test_mask, "dia_semana"].isin(dow_risco)
        nome_dow_risco = "dia_semana_risco (" + "/".join(nomes_dow[k] for k in dow_risco) + ")"
        registra(nome_dow_risco, pred_dow, score=pred_dow.astype(int))

        # 3-4. Logistic Regression (com e sem balanceamento de classe)
        cols = sum(FEAT_GROUPS.values(), []) + hist_feats(base)
        X = d[cols].copy()
        X["jogo_noturno"] = X["jogo_noturno"].fillna(0)
        imp = SimpleImputer(strategy="median").fit(X.loc[train_mask])
        Xi = pd.DataFrame(imp.transform(X), columns=cols, index=X.index)
        sca = StandardScaler().fit(Xi.loc[train_mask])
        Xs = pd.DataFrame(sca.transform(Xi), columns=cols, index=X.index)
        for nome, cw in [("logreg", None), ("logreg_balanced", "balanced")]:
            clf = LogisticRegression(max_iter=3000, class_weight=cw).fit(Xs.loc[train_mask], y_tr)
            proba = clf.predict_proba(Xs.loc[test_mask])[:, 1]
            row = registra(nome, proba >= 0.5, score=proba)
            if nome == "logreg":
                curvas[base] = (y_te.to_numpy(), proba)

        w(f"### {base} (prevalencia no teste: {prevalencia_teste*100:.1f}%, "
          f"n_teste={len(y_te)}, n_pico={int(y_te.sum())})\n")
        tab_base = pd.DataFrame([r for r in linhas if r["base"] == base]).drop(columns="base")
        w(df_to_md(tab_base, floatfmt=3, index=False))
        w("")

    tab = pd.DataFrame(linhas)
    tab.to_csv(os.path.join(TAB_DIR, "baselines_classificacao.csv"), index=False)
    w("_`roc_auc`/`pr_auc` em branco = classificador sem score continuo "
      "(classe majoritaria sempre prediz 0, nao ha curva a tracar)._\n")

    # curvas ROC/PR do logreg
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    for j, base in enumerate(BASES):
        y_te, proba = curvas[base]
        fpr, tpr, _ = roc_curve(y_te, proba)
        prec, rec, _ = precision_recall_curve(y_te, proba)
        axes[0, j].plot(fpr, tpr, label=f"AUC={roc_auc_score(y_te, proba):.2f}")
        axes[0, j].plot([0, 1], [0, 1], "k--", lw=.7)
        axes[0, j].set_title(f"ROC -- {base}")
        axes[0, j].set_xlabel("FPR"); axes[0, j].set_ylabel("TPR"); axes[0, j].legend(fontsize=8)
        base_rate = y_te.mean()
        axes[1, j].plot(rec, prec, label=f"PR-AUC={average_precision_score(y_te, proba):.2f}")
        axes[1, j].axhline(base_rate, color="k", ls="--", lw=.7, label=f"base={base_rate:.2f}")
        axes[1, j].set_title(f"Precision-Recall -- {base}")
        axes[1, j].set_xlabel("Recall"); axes[1, j].set_ylabel("Precision"); axes[1, j].legend(fontsize=8)
    w(f"![roc pr]({savefig('02_roc_pr_logreg.png')})\n")

    # matriz de confusao do logreg (threshold 0.5)
    for base in BASES:
        y_te, proba = curvas[base]
        cm = confusion_matrix(y_te, proba >= 0.5)
        cmdf = pd.DataFrame(cm, index=["real: nao-pico", "real: pico"],
                            columns=["prev: nao-pico", "prev: pico"])
        w(f"Matriz de confusao -- Logistic Regression, `{base}` (threshold 0.5):\n")
        w(df_to_md(cmdf, floatfmt=0))
        w("")


# ---------------------------------------------------------------------------
def main():
    d = load()
    w("# Etapa 13 -- Baselines\n")
    w(f"_Gerado por `scripts/10_baselines.py` em {date.today()}. "
      f"Fontes: `data/gold/features_dia_sp.csv` + `fato_dia_sp.csv`._\n")
    w("> Regra 9 do briefing: todo modelo de ML da Etapa 14 em diante sera "
      "comparado contra os baselines desta etapa. Regra 8: nunca escolher por "
      "Accuracy isolada -- ver Recall/F1/PR-AUC, dado o desbalanceamento "
      "(~10% de pico).\n")

    secao_split(d)
    secao_regressao(d)
    secao_classificacao(d)

    w("## 4. Sintese\n")
    w(textwrap.dedent("""\
        - **O resultado mais importante desta etapa nao e qual baseline "ganhou",
          e a secao 1.1**: um unico corte temporal com tendencia linear extrapolada
          3 meses a frente pode distorcer MUITO a prevalencia do alvo no teste
          (3,3% vs 34,4%, ambos longe do 10% nominal). Isso e um argumento de peso
          -- com numeros do proprio projeto, nao so teorico -- para a validacao
          walk-forward da Etapa 15 em vez de confiar num split unico.
        - **Regressao**: comparar MAE/RMSE dos modelos da Etapa 14 aos 3 baselines
          acima, por desfecho. A media movel bateu a media historica e o
          mesmo-dia-da-semana-anterior nos dois desfechos neste corte -- piso
          realista a superar.
        - **Classificacao**: leitura por desfecho, nao agregada --
          `acidentes_com_vitima` (31 positivos no teste) da uma comparacao razoavel:
          `logreg_balanced` supera a classe majoritaria e o `dia_semana_risco` em
          Recall/F1 (0,74/0,55). Ja `crimes_violentos` (so 3 positivos no teste) NAO
          deve ser usado para julgar modelo nenhum nesta rodada -- o proprio
          `dia_semana_risco` sai com ROC-AUC abaixo de 0,5 so por causa do n
          minusculo, nao porque calendario "piora" a previsao.
        - **Vazamento corrigido**: o alvo de pico foi redefinido com o modelo de
          calendario ajustado SO no treino -- primeira aplicacao concreta da
          ressalva repetida desde a Etapa 8. A Etapa 15 generaliza isso para
          multiplos folds (walk-forward), o que tambem deve estabilizar a
          prevalencia do alvo no teste.
        - **Proximo**: Etapa 14 -- Decision Tree, Random Forest, XGBoost,
          LightGBM/CatBoost e comparacao final contra estes baselines, incluindo a
          sensibilidade ao outlier de 2022-06-19. Considerar, na Etapa 14/15,
          suavizar ou remover o termo de tendencia linear do modelo de calendario
          (ou reajusta-lo com mais frequencia) para evitar a extrapolacao vista
          aqui.
    """))

    path = os.path.join(OUT_DIR, "relatorio_baselines.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_md))
    print(f"[ok] relatorio: {path}")
    print(f"[ok] figuras : {FIG_DIR} ({len(os.listdir(FIG_DIR))})  tabelas: {TAB_DIR} ({len(os.listdir(TAB_DIR))})")


if __name__ == "__main__":
    main()
