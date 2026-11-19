"""
V2 / Fase 1 (complemento aprovado) -- 31a_jogos_complementares.py
Completa o calendario de jogos em casa de Corinthians, Palmeiras e Sao Paulo
em 2022-2023 com as competicoes que o BR-Football-Dataset NAO tem:
Campeonato Paulista, Copa Libertadores, Copa Sul-Americana e Recopa Sul-Americana.

FONTE (verificavel, sem dado inventado):
  - Primaria: paginas de temporada de cada clube na Wikipedia em ingles
    ("2022 SE Palmeiras season" etc.). Cada partida e um {{football box}} com
    data, horario COM FUSO EXPLICITO ({{UTZ|21:00|-3}} = UTC-3 = Brasilia),
    mandante (team1), visitante, cidade (location), estadio, publico e link da
    sumula (ge.globo / conmebol). As paginas de EDICAO (ex. Paulistao 2022 na
    pt.wikipedia) trazem a fase de grupos so como tabela cruzada de placares,
    sem data/horario/estadio -- por isso nao servem como fonte primaria aqui;
    sao usadas como CONFERENCIA onde tem football box (mata-mata do Paulistao,
    fases de grupos/mata-mata da Libertadores e Sul-Americana, Recopa).
  - fonte_jogo = permalink da revisao usada (index.php?title=...&oldid=REVID),
    para o dado ser reprodutivel mesmo se a pagina mudar depois.
  - Os snapshots do wikitext ficam em data/bronze/wikipedia/ (+ manifesto com
    revid/timestamp). `--baixar` refaz o download; sem a flag, so le os snapshots.

REGRAS:
  - horario so e aceito com fuso explicito UTC-3; sem horario ou com fuso
    diferente -> horario_confirmado=False (fica fora da analise principal);
  - jogo em casa disputado fora da capital (location != Sao Paulo) ->
    fora_da_capital=True (fica fora);
  - o mesmo parser le Serie A e Copa do Brasil dessas paginas para conferir os
    137 jogos da base original (horario convertido do fuso e cidade/estadio).

Saidas:
  data/bronze/wikipedia/*.wiki, manifesto.json
  data/bronze/wikipedia/partidas_temporadas.csv   (todas as partidas das 6 paginas)
  data/bronze/jogos_complementares.csv            (so as 4 competicoes, jogos em casa)
  reports/janelas/fase1/tabelas/conferencia_*.csv

Rodar:  python scripts/31a_jogos_complementares.py [--baixar]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(BASE, "data", "bronze", "wikipedia")
BRONZE = os.path.join(BASE, "data", "bronze")
TAB = os.path.join(BASE, "reports", "janelas", "fase1", "tabelas")
os.makedirs(WIKI, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

UA = "Mozilla/5.0 (academic research script; football calendar)"
# (idioma, titulo, clube, ano, papel) -- papel: primaria (temporada) ou conferencia (edicao)
PAGINAS = [
    ("en", "2022 Sport Club Corinthians Paulista season", "Corinthians", 2022, "primaria"),
    ("en", "2023 Sport Club Corinthians Paulista season", "Corinthians", 2023, "primaria"),
    ("en", "2022 SE Palmeiras season", "Palmeiras", 2022, "primaria"),
    ("en", "2023 SE Palmeiras season", "Palmeiras", 2023, "primaria"),
    ("en", "2022 São Paulo FC season", "Sao Paulo", 2022, "primaria"),
    ("en", "2023 São Paulo FC season", "Sao Paulo", 2023, "primaria"),
    ("en", "2022 Santos FC season", "Santos", 2022, "primaria"),
    ("en", "2023 Santos FC season", "Santos", 2023, "primaria"),
    # conferencia (paginas de edicao)
    ("en", "2022 Copa Libertadores group stage", None, 2022, "conferencia"),
    ("en", "2023 Copa Libertadores group stage", None, 2023, "conferencia"),
    ("en", "2022 Copa Libertadores final stages", None, 2022, "conferencia"),
    ("en", "2023 Copa Libertadores final stages", None, 2023, "conferencia"),
    ("en", "2022 Copa Sudamericana group stage", None, 2022, "conferencia"),
    ("en", "2023 Copa Sudamericana group stage", None, 2023, "conferencia"),
    ("en", "2022 Copa Sudamericana final stages", None, 2022, "conferencia"),
    ("en", "2023 Copa Sudamericana final stages", None, 2023, "conferencia"),
    ("en", "2022 Recopa Sudamericana", None, 2022, "conferencia"),
    ("en", "2022 Campeonato Paulista", None, 2022, "conferencia"),
    ("en", "2023 Campeonato Paulista", None, 2023, "conferencia"),
    ("pt", "Campeonato Paulista de Futebol de 2022", None, 2022, "conferencia"),
    ("pt", "Campeonato Paulista de Futebol de 2023", None, 2023, "conferencia"),
]
CLUBE_ALIAS = {"Corinthians": ["corinthians"], "Palmeiras": ["palmeiras"], "Santos": ["santos"],
               "Sao Paulo": ["são paulo", "sao paulo", "são paulo fc"]}
COMPETICOES_ALVO = {"Campeonato Paulista", "Copa Libertadores", "Copa Sudamericana", "Recopa Sudamericana"}
COMPETICOES_OFICIAIS = COMPETICOES_ALVO | {"Serie A", "Copa do Brasil", "Supercopa do Brasil", "Mundial de Clubes"}
CLUBES_CAPITAL = {"Corinthians", "Palmeiras", "Sao Paulo"}
# Regiao Metropolitana de Sao Paulo (39 municipios, LC estadual 1.139/2011)
RMSP = {"arujá", "barueri", "biritiba-mirim", "caieiras", "cajamar", "carapicuíba", "cotia", "diadema",
        "embu das artes", "embu-guaçu", "ferraz de vasconcelos", "francisco morato", "franco da rocha",
        "guararema", "guarulhos", "itapecerica da serra", "itapevi", "itaquaquecetuba", "jandira",
        "juquitiba", "mairiporã", "mauá", "mogi das cruzes", "osasco", "pirapora do bom jesus", "poá",
        "ribeirão pires", "rio grande da serra", "salesópolis", "santa isabel", "santana de parnaíba",
        "santo andré", "são bernardo do campo", "são caetano do sul", "são lourenço da serra", "são paulo",
        "suzano", "taboão da serra", "vargem grande paulista"}
MESES = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                     "august", "september", "october", "november", "december"], 1)}
MESES_PT = {m: i for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                                        "agosto", "setembro", "outubro", "novembro", "dezembro"], 1)}


def arquivo(lang, titulo):
    return os.path.join(WIKI, f"{lang}__{titulo.replace(' ', '_')}.wiki")


def permalink(lang, titulo, revid):
    return (f"https://{lang}.wikipedia.org/w/index.php?title="
            f"{urllib.parse.quote(titulo.replace(' ', '_'))}&oldid={revid}")


def _get_json(url, tentativas=6):
    for k in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == tentativas - 1:
                raise
            espera = 10 * (k + 1)
            print(f"    429 (limite de taxa) -- esperando {espera}s")
            time.sleep(espera)


def baixar(forcar=False):
    mpath = os.path.join(WIKI, "manifesto.json")
    manifesto = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    for lang, titulo, *_ in PAGINAS:
        if not forcar and f"{lang}:{titulo}" in manifesto and os.path.exists(arquivo(lang, titulo)):
            continue
        time.sleep(3)  # cortesia com a API da Wikipedia
        q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "ids|timestamp|content",
                                    "rvslots": "main", "format": "json", "redirects": 1, "titles": titulo})
        d = _get_json(f"https://{lang}.wikipedia.org/w/api.php?{q}")
        pg = next(iter(d["query"]["pages"].values()))
        if "revisions" not in pg:
            print(f"  [falta] {lang}:{titulo}")
            continue
        rev = pg["revisions"][0]
        with open(arquivo(lang, titulo), "w", encoding="utf-8") as fh:
            fh.write(rev["slots"]["main"]["*"])
        manifesto[f"{lang}:{titulo}"] = {"titulo_resolvido": pg["title"], "revid": rev["revid"],
                                         "timestamp": rev["timestamp"],
                                         "url": permalink(lang, pg["title"], rev["revid"])}
        print(f"  [ok] {lang}:{titulo} rev {rev['revid']}")
        with open(mpath, "w", encoding="utf-8") as fh:  # salva a cada pagina
            json.dump(manifesto, fh, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# parser de wikitext
# ---------------------------------------------------------------------------
def blocos_template(texto, nomes):
    """Devolve (posicao, conteudo) de cada {{nome ...}} com chaves balanceadas."""
    pat = re.compile(r"\{\{\s*(" + "|".join(nomes) + r")\b", re.I)
    for m in pat.finditer(texto):
        i, nivel = m.start(), 0
        j = i
        while j < len(texto) - 1:
            if texto[j:j + 2] == "{{":
                nivel += 1; j += 2; continue
            if texto[j:j + 2] == "}}":
                nivel -= 1; j += 2
                if nivel == 0:
                    break
                continue
            j += 1
        yield m.start(), texto[i + 2:j - 2]


def params(corpo):
    """Separa parametros de template no '|' de nivel zero."""
    partes, nivel, atual = [], 0, []
    k = 0
    while k < len(corpo):
        dois = corpo[k:k + 2]
        if dois in ("{{", "[["):
            nivel += 1; atual.append(dois); k += 2; continue
        if dois in ("}}", "]]"):
            nivel -= 1; atual.append(dois); k += 2; continue
        if corpo[k] == "|" and nivel == 0:
            partes.append("".join(atual)); atual = []
        else:
            atual.append(corpo[k])
        k += 1
    partes.append("".join(atual))
    out = {}
    for p in partes[1:]:
        if "=" in p:
            a, b = p.split("=", 1)
            out[a.strip().lower()] = b.strip()
    return out


def limpa(s):
    if s is None:
        return ""
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\{\{\s*(?:fb|fbaicon|flagicon|flag icon|fb-rt|fbu)[^{}]*\}\}", "", s, flags=re.I)
    s = re.sub(r"\{\{\s*(?:nowrap|small|nobold)\s*\|([^{}]*)\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_data(s, ano=None):
    s0 = s
    m = re.search(r"\{\{\s*(?:start date|dts|date)[^|]*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", s, re.I)
    if m:
        return pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    s = limpa(s).lower()
    m = re.search(r"(\d{1,2})\s+([a-zç]+)\s+(\d{4})", s)
    if m and m[2] in MESES:
        return pd.Timestamp(int(m[3]), MESES[m[2]], int(m[1]))
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m[1] in MESES:
        return pd.Timestamp(int(m[3]), MESES[m[1]], int(m[2]))
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", s)
    if m and m[2] in MESES_PT:
        return pd.Timestamp(int(m[3]), MESES_PT[m[2]], int(m[1]))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s0)
    if m:
        return pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    # sem ano (paginas do Santos: "2 February") -> ano da propria pagina de temporada
    m = re.search(r"^(\d{1,2})\s+([a-z]+)$", s.strip())
    if m and ano and m[2] in MESES:
        return pd.Timestamp(int(ano), MESES[m[2]], int(m[1]))
    return pd.NaT


def parse_hora(s):
    """-> (HH:MM, offset_utc) ou (None, None). Aceita {{UTZ|21:00|-3}} e '21:00 ([[UTC−3]])'."""
    if not s:
        return None, None
    m = re.search(r"UTZ\s*\|\s*(\d{1,2})[:h.](\d{2})\s*\|\s*([+\-−]?\d+)", s, re.I)
    if m:
        return f"{int(m[1]):02d}:{m[2]}", int(m[3].replace("−", "-"))
    m = re.search(r"(\d{1,2})[:h](\d{2}).*?UTC\s*([+\-−]\s*\d+)", s, re.I)
    if m:
        return f"{int(m[1]):02d}:{m[2]}", int(m[3].replace("−", "-").replace(" ", ""))
    m = re.search(r"(\d{1,2})[:h](\d{2})", s)
    if m:
        return f"{int(m[1]):02d}:{m[2]}", None
    return None, None


def normaliza_comp(h):
    h = h.lower()
    if "supercopa" in h:  # antes de "copa do brasil" (Supercopa do Brasil contem o texto)
        return "Supercopa do Brasil"
    if "club world cup" in h or "mundial" in h:
        return "Mundial de Clubes"
    if "friendl" in h or "amistos" in h or "pre-season" in h or "florida cup" in h:
        return "Amistoso"
    if "paulista" in h:
        return "Campeonato Paulista"
    if "libertadores" in h:
        return "Copa Libertadores"
    if "sudamericana" in h or "sul-americana" in h:
        return "Recopa Sudamericana" if "recopa" in h else "Copa Sudamericana"
    if "recopa" in h:
        return "Recopa Sudamericana"
    if "série a" in h or "serie a" in h or "brasileiro" in h:
        return "Serie A"
    if "copa do brasil" in h:
        return "Copa do Brasil"
    if "supercopa" in h:
        return "Supercopa do Brasil"
    return h.strip("= ").title()


def partidas_da_pagina(lang, titulo, ano=None):
    path = arquivo(lang, titulo)
    if not os.path.exists(path):
        return []
    texto = open(path, encoding="utf-8").read()
    heads = [(m.start(), len(m[1]), limpa(m[2])) for m in re.finditer(r"^(=+)\s*(.*?)\s*=+\s*$", texto, re.M)]
    out = []
    for pos, corpo in blocos_template(texto, ["football box collapsible", "football box", "footballbox"]):
        p = params(corpo)
        ctx = [h for h in heads if h[0] < pos]
        comp, fase = None, None
        for _, lvl, nome in reversed(ctx):
            c = normaliza_comp(nome)
            if comp is None and c in COMPETICOES_OFICIAIS | {"Amistoso"}:
                comp = c
            if fase is None and normaliza_comp(nome) == nome.title() and nome.lower() not in ("matches", "results"):
                fase = nome
            if comp:
                break
        hora, off = parse_hora(p.get("time", ""))
        out.append({
            "pagina": f"{lang}:{titulo}", "competicao_secao": comp, "secao": fase,
            "rodada": limpa(p.get("round", "")), "data": parse_data(p.get("date", ""), ano),
            "hora": hora, "utc_offset": off, "hora_txt": limpa(p.get("time", ""))[:40],
            "team1": limpa(p.get("team1", "")), "team2": limpa(p.get("team2", "")),
            "placar": limpa(p.get("score", "")), "cidade": limpa(p.get("location", "")),
            "estadio": limpa(p.get("stadium", "")), "publico": limpa(p.get("attendance", "")),
            "sumula": p.get("report", "").strip().split(" ")[0].strip("[]") if p.get("report") else "",
            "nota": limpa(p.get("note", ""))[:300],
        })
    return out


def eh_clube(nome, clube):
    n = nome.lower().replace("fc", "").strip()
    return any(n == a or n.startswith(a + " ") or n.endswith(" " + a) for a in CLUBE_ALIAS[clube]) \
        and not any(x in n for x in ("feminino", "women", "sub-"))


def identifica_clube(nome):
    for c in CLUBE_ALIAS:
        if eh_clube(nome, c):
            return c
    return None


# ---------------------------------------------------------------------------
def monta():
    man = json.load(open(os.path.join(WIKI, "manifesto.json"), encoding="utf-8"))
    linhas = []
    for lang, titulo, clube, ano, papel in PAGINAS:
        for r in partidas_da_pagina(lang, titulo, ano):
            r.update({"papel": papel, "clube_pagina": clube, "url_revisao": man.get(f"{lang}:{titulo}", {}).get("url")})
            linhas.append(r)
    todas = pd.DataFrame(linhas)
    todas["mandante"] = todas["team1"].map(identifica_clube)
    todas["visitante_clube_sp"] = todas["team2"].map(identifica_clube)
    todas.to_csv(os.path.join(WIKI, "partidas_temporadas.csv"), index=False)

    prim = todas[(todas["papel"] == "primaria") & (todas["mandante"] == todas["clube_pagina"])
                 & todas["mandante"].isin(CLUBES_CAPITAL)].copy()
    prim = prim[prim["data"].between("2022-01-01", "2023-12-31")]
    return todas, prim


def cidade_capital(c):
    c = (c or "").lower()
    return c.startswith("são paulo") or c.startswith("sao paulo")


def complementares(prim, todas):
    comp = prim[prim["competicao_secao"].isin(COMPETICOES_ALVO)].copy()
    comp["horario_confirmado"] = comp["hora"].notna() & (comp["utc_offset"] == -3)
    comp["fora_da_capital"] = ~comp["cidade"].map(cidade_capital)
    comp["inicio_br"] = pd.to_datetime(comp["data"].dt.strftime("%Y-%m-%d") + " " + comp["hora"].fillna("00:00"))
    comp.loc[~comp["horario_confirmado"], "inicio_br"] = pd.NaT

    # conferencia contra paginas de edicao (mesma data + mesmo mandante)
    conf = todas[todas["papel"] == "conferencia"].dropna(subset=["data"]).copy()
    conf = conf[conf["mandante"].notna()]
    chave = conf.set_index([conf["data"].dt.date, conf["mandante"]])
    res = []
    for i, r in comp.iterrows():
        k = (r["data"].date(), r["mandante"])
        if k in chave.index:
            c = chave.loc[[k]].iloc[0]
            res.append({"idx": i, "conf_pagina": c["pagina"], "conf_hora": c["hora"], "conf_offset": c["utc_offset"],
                        "conf_estadio": c["estadio"], "conf_cidade": c["cidade"]})
    conf_df = pd.DataFrame(res).set_index("idx") if res else pd.DataFrame()
    comp = comp.join(conf_df)
    comp["conferido_edicao"] = comp.get("conf_pagina").notna() if "conf_pagina" in comp else False
    comp["hora_diverge_edicao"] = comp["conferido_edicao"] & comp["conf_hora"].notna() & \
        (comp["conf_hora"] != comp["hora"]) & ~((comp["conf_offset"].notna()) & (comp["conf_offset"] != -3))
    return comp


def confere_137(prim):
    """Compara os 137 jogos do BR-Football-Dataset (apos correcao de fuso) com as paginas."""
    # monta os 137 direto do bronze com a mesma funcao do 31 (sem depender da saida do 31)
    import importlib
    sys.path.insert(0, os.path.join(BASE, "scripts"))
    j = importlib.import_module("31_jogos_horarios").carrega_jogos(so_base_original=True)
    j["data_br"] = pd.to_datetime(j["data_br"])
    w = prim[prim["competicao_secao"].isin(["Serie A", "Copa do Brasil"])].copy()
    w["chave"] = w["data"].dt.strftime("%Y-%m-%d") + "_" + w["mandante"]
    j["chave"] = j["data_br"].dt.strftime("%Y-%m-%d") + "_" + j["mandante"]
    m = j.merge(w[["chave", "competicao_secao", "team2", "hora", "utc_offset", "cidade", "estadio", "url_revisao",
                   "publico", "nota"]],
                on="chave", how="left")
    m["achou_na_wiki"] = m["hora"].notna() | m["cidade"].notna()
    m["hora_br_base"] = m["inicio_br"].dt.strftime("%H:%M")
    m["hora_bate"] = m["hora"] == m["hora_br_base"]
    m["fora_da_capital"] = m["achou_na_wiki"] & ~m["cidade"].map(cidade_capital)
    # e o inverso: jogos em casa de Serie A/Copa do Brasil na wiki que nao estao na base
    falta = w[~w["chave"].isin(j["chave"])]
    return m, falta


# ---------------------------------------------------------------------------
# publico
# ---------------------------------------------------------------------------
def publico_status(publico_txt, nota):
    """-> (publico numerico ou NaN, status). Ausente = NaN, nunca zero. 0 so com portoes fechados."""
    import numpy as np
    n = (nota or "").lower()
    m = re.search(r"(\d[\d,.]*)", str(publico_txt or "").replace(" ", ""))
    val = float(re.sub(r"[,.]", "", m[1])) if m else np.nan
    fechado = any(k in n for k in ("closed doors", "behind closed", "without fans", "without spectators",
                                   "no fans", "portões fechados"))
    restrito = any(k in n for k in ("% stadium capacity", "capacity due", "limited capacity", "reduced capacity",
                                    "restricted"))
    if fechado:
        return (0.0 if (val == 0 or np.isnan(val)) else val), "portoes_fechados"
    if np.isnan(val):
        return np.nan, "ausente"
    if val == 0:
        return np.nan, "zero_sem_explicacao"
    return val, ("capacidade_restrita" if restrito else "ok")


# ---------------------------------------------------------------------------
# todos os jogos oficiais dos 4 times (para janela_fora_capital e jogos na capital sem mandante da capital)
# ---------------------------------------------------------------------------
def _norm_time(nome):
    c = identifica_clube(nome)
    if c:
        return c
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFKD", nome.lower()) if not unicodedata.combining(ch)).strip()


# Horarios em que a pagina de temporada DIVERGIU da fonte independente (BR-Football-Dataset ou pagina
# de edicao) e uma 3a fonte confirmou a fonte independente -> corrige (horario de Brasilia) com URL.
CORRECAO_HORARIO = {
    ("2023-10-18", "goias"): ("21:30", "https://br.soccerway.com/noticias/futebol-serie-a-goias-x-sao-paulo-onde-assistir-times-e-tudo-sobre-o-jogo-da-27-rodada-do-brasileirao/0dqPi8rg"),
    ("2023-11-06", "Santos"): ("21:00", "https://www.lance.com.br/santos/santos-x-cuiaba-onde-assistir-ao-vivo-horario-e-provaveis-escalacoes-do-jogo-pelo-brasileirao.html"),
    ("2023-11-29", "bahia"): ("20:00", "https://olhardigital.com.br/2023/11/29/internet-e-redes-sociais/bahia-x-sao-paulo-onde-assistir-horario-e-escalacoes-da-partida-do-brasileirao/"),
    # conflito entre paginas (Santos: 16:00; Corinthians: 20:00) -> BR-Football (00:00 UK/BST = 20:00 BRT) desempata
    ("2023-06-21", "Santos"): ("20:00", "https://en.wikipedia.org/w/index.php?title=2023_Sport_Club_Corinthians_Paulista_season&oldid=1385354030 + BR-Football-Dataset"),
    ("2023-06-06", "Santos"): ("21:30", "https://www.90min.com/pt-br/posts/santos-x-newell-s-old-boys-onde-assistir-ao-vivo-na-tv-horario-provavel-escalacao-ultimas-noticias-e-palpite-sul-americana-06-06-2023"),
}


def todos_os_jogos(todas):
    """1 linha por partida oficial dos 4 times (dedup entre paginas), horario convertido para Brasilia
    com o fuso indicado na propria pagina: inicio_br = hora_local + (-3 - utc_offset) h."""
    t = todas[(todas["papel"] == "primaria") & todas["data"].notna()].copy()
    t["comp_ok"] = t["competicao_secao"].isin(COMPETICOES_OFICIAIS)
    n_amistosos = int((t["competicao_secao"] == "Amistoso").sum())
    t = t[t["comp_ok"]]
    t["chave"] = t["data"].dt.strftime("%Y-%m-%d") + "|" + t["team1"].map(_norm_time) + "|" + t["team2"].map(_norm_time)
    # conflito de horario/fuso entre paginas do mesmo jogo
    g = t.groupby("chave").agg(n_paginas=("pagina", "nunique"), n_horas=("hora", "nunique"),
                               n_offsets=("utc_offset", "nunique"))
    t = t.sort_values(["chave", "utc_offset"], na_position="last").drop_duplicates("chave").set_index("chave")
    t = t.join(g).reset_index()
    t["horario_confirmado"] = t["hora"].notna() & t["utc_offset"].notna() & (t["n_horas"] <= 1) & (t["n_offsets"] <= 1)
    loc = pd.to_datetime(t["data"].dt.strftime("%Y-%m-%d") + " " + t["hora"].fillna("00:00"))
    t["inicio_br"] = (loc + pd.to_timedelta(-3 - t["utc_offset"].fillna(-3), unit="h")).where(t["horario_confirmado"])
    t["horario_corrigido_fonte"] = None
    for (d, mand), (hh, url) in CORRECAO_HORARIO.items():
        mk = (t["data"].dt.strftime("%Y-%m-%d") == d) & (t["team1"].map(_norm_time) == mand)
        assert mk.sum() == 1, (d, mand, mk.sum())
        t.loc[mk, "inicio_br"] = pd.Timestamp(f"{d} {hh}")
        t.loc[mk, "horario_corrigido_fonte"] = url
        t.loc[mk, "horario_confirmado"] = True
    t["data_br"] = t["inicio_br"].dt.date
    t["em_capital"] = t["cidade"].map(cidade_capital)
    cid = t["cidade"].str.split(",").str[0].str.strip()
    t["cidade1"] = cid
    t["regiao_metropolitana_sp"] = cid.str.lower().isin(RMSP)
    t["times_monitorados"] = [
        "+".join(sorted({x for x in (identifica_clube(a), identifica_clube(b)) if x}))
        for a, b in zip(t["team1"], t["team2"])]
    t["mandante_monitorado"] = t["team1"].map(identifica_clube)
    t = t[(t["inicio_br"].isna() & t["data"].between("2022-01-01", "2023-12-31"))
          | t["inicio_br"].between("2022-01-01", "2024-01-01")]
    return t, n_amistosos


def valida_fora(fc, todas):
    """Validacao independente da conversao de fuso dos jogos fora da capital:
    (a) Serie A / Copa do Brasil vs BR-Football-Dataset (horario UK -> Brasilia, fonte independente);
    (b) Libertadores / Sul-Americana / Recopa vs paginas de EDICAO (horario local + fuso local)."""
    import unicodedata

    def sa(x):
        return "".join(c for c in unicodedata.normalize("NFKD", str(x).lower()) if not unicodedata.combining(c))

    linhas = []
    # (a) BR-Football
    bf = pd.read_csv(os.path.join(BRONZE, "BR-Football-Dataset.csv"))
    ts = pd.to_datetime(bf["date"] + " " + bf["time"], format="%Y-%m-%d %H:%M:%S")
    bf["inicio_br_bf"] = ts.dt.tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT") \
        .dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None).dt.round("30min")
    bf["d"] = bf["inicio_br_bf"].dt.date
    for _, r in fc[fc["competicao"].isin(["Serie A", "Copa do Brasil"]) & fc["horario_confirmado"]].iterrows():
        mons = r["times_monitorados"].split("+")
        cand = bf[(bf["d"] == r["data_br"]) &
                  (bf["home"].map(sa).str.contains(sa(r["mandante"])[:5], regex=False)
                   | bf["away"].map(sa).str.contains(sa(r["visitante"])[:5], regex=False))]
        cand = cand[cand["home"].map(sa).apply(lambda h: any(sa(m)[:5] in h for m in mons))
                    | cand["away"].map(sa).apply(lambda h: any(sa(m)[:5] in h for m in mons))]
        if len(cand) == 0:
            # tenta data vizinha (jogo noturno perto da meia-noite)
            linhas.append({"fonte_conf": "br_football", "competicao": r["competicao"], "data_br": r["data_br"],
                           "mandante": r["mandante"], "visitante": r["visitante"], "cidade": r["cidade"],
                           "inicio_br_wiki": r["inicio_br"], "inicio_br_conf": pd.NaT, "achou": False})
            continue
        c = cand.iloc[0]
        linhas.append({"fonte_conf": "br_football", "competicao": r["competicao"], "data_br": r["data_br"],
                       "mandante": r["mandante"], "visitante": r["visitante"], "cidade": r["cidade"],
                       "inicio_br_wiki": r["inicio_br"], "inicio_br_conf": c["inicio_br_bf"], "achou": True})
    # (b) paginas de edicao (CONMEBOL)
    conf = todas[(todas["papel"] == "conferencia") & todas["data"].notna() & todas["hora"].notna()
                 & todas["utc_offset"].notna()].copy()
    conf["ini"] = pd.to_datetime(conf["data"].dt.strftime("%Y-%m-%d") + " " + conf["hora"]) \
        + pd.to_timedelta(-3 - conf["utc_offset"], unit="h")
    conf["k1"], conf["k2"] = conf["team1"].map(_norm_time), conf["team2"].map(_norm_time)
    for _, r in fc[fc["competicao"].isin(["Copa Libertadores", "Copa Sudamericana", "Recopa Sudamericana"])
                   & fc["horario_confirmado"]].iterrows():
        k1, k2 = _norm_time(r["mandante"]), _norm_time(r["visitante"])
        cand = conf[(conf["k1"] == k1) & (conf["k2"] == k2)
                    & ((conf["ini"] - r["inicio_br"]).abs() < pd.Timedelta(days=2))]
        linhas.append({"fonte_conf": "pagina_edicao", "competicao": r["competicao"], "data_br": r["data_br"],
                       "mandante": r["mandante"], "visitante": r["visitante"], "cidade": r["local_txt"],
                       "inicio_br_wiki": r["inicio_br"],
                       "inicio_br_conf": cand["ini"].iloc[0] if len(cand) else pd.NaT, "achou": len(cand) > 0,
                       "offset_local_edicao": cand["utc_offset"].iloc[0] if len(cand) else None})
    v = pd.DataFrame(linhas)
    v["diff_min"] = (v["inicio_br_wiki"] - v["inicio_br_conf"]).dt.total_seconds() / 60
    v["bate"] = v["achou"] & (v["diff_min"].abs() <= 15)
    v.to_csv(os.path.join(TAB, "conferencia_fuso_jogos_fora_capital.csv"), index=False)
    return v


def grava_fora_capital(tj):
    f = tj[~tj["em_capital"]].copy()
    pub = [publico_status(a, b) for a, b in zip(f["publico"], f["nota"])]
    out = pd.DataFrame({
        "data_local": f["data"].dt.date, "hora_local": f["hora"], "utc_offset_local": f["utc_offset"],
        "inicio_br": f["inicio_br"], "data_br": f["data_br"], "horario_confirmado": f["horario_confirmado"],
        "times_monitorados": f["times_monitorados"], "mandante": f["team1"], "visitante": f["team2"],
        "mandante_monitorado": f["mandante_monitorado"], "competicao": f["competicao_secao"],
        "fase": (f["secao"].fillna("") + " " + f["rodada"].fillna("").astype(str)).str.strip(),
        "cidade": f["cidade1"], "local_txt": f["cidade"], "estadio": f["estadio"],
        "regiao_metropolitana_sp": f["regiao_metropolitana_sp"],
        "mando_proprio_fora_capital": f["mandante_monitorado"].isin(CLUBES_CAPITAL),
        "publico_estadio_nao_usado": [x[0] for x in pub],
        "fonte_jogo": f["url_revisao"], "fonte_sumula": f["sumula"],
        "n_paginas_fonte": f["n_paginas"], "horario_corrigido_fonte": f["horario_corrigido_fonte"],
    }).sort_values("inicio_br").reset_index(drop=True)
    out.to_csv(os.path.join(BRONZE, "jogos_fora_capital.csv"), index=False)
    return out


def capital_sem_mandante_capital(tj):
    """Jogos na capital cujo mandante NAO e Corinthians/Palmeiras/Sao Paulo (ex.: Santos mandante na capital)."""
    c = tj[tj["em_capital"] & ~tj["team1"].map(identifica_clube).isin(CLUBES_CAPITAL)].copy()
    return c


# Segunda fonte (busca manual em 2026-11-15) para os casos em que a Wikipedia indicou
# mando fora do estadio habitual -- os mais suscetiveis a erro. Chave = data_mandante.
CONFERENCIA_EXTRA = {
    "2022-04-23_Palmeiras": "https://www.campograndenews.com.br/esportes/palmeiras-e-melhor-e-vence-derby-por-3-a-0-em-barueri",
    "2022-05-12_Sao Paulo": "https://www.gazetaesportiva.com/?p=3196232",
    "2023-10-08_Palmeiras": "https://www.abola.pt/noticias/the-weekend-despeja-palmeiras-e-abel-pode-ter-novembro-complicado-2023100621514310770",
    "2023-11-04_Palmeiras": "https://www.tribunadosertao.com.br/esportes/2023/11/08/556621-por-que-palmeiras-e-sao-paulo-nao-jogarao-em-seus-respectivos-estadios-no-brasileirao-entenda",
    "2023-11-11_Palmeiras": "https://www.tribunadosertao.com.br/esportes/2023/11/08/556621-por-que-palmeiras-e-sao-paulo-nao-jogarao-em-seus-respectivos-estadios-no-brasileirao-entenda",
    "2023-11-08_Sao Paulo": "https://www.itatiaia.com.br/editorias/saopaulo/2023/11/09/sao-paulo-vence-na-vila-e-impede-bragantino-de-assumir-lideranca-do-brasileiro/",
    "2023-03-13_Sao Paulo": "https://www.gazetaesportiva.com/?p=3323102",
    # jogo da Serie A ausente do BR-Football-Dataset (lacuna da base) -- data/hora/estadio conferidos:
    "2023-05-13_Palmeiras": "https://www.opovo.com.br/esportes/futebol/2023/05/13/palmeiras-x-rb-bragantino-ao-vivo-onde-assistir-escalacao-provavel-e-horario.html",
}
ESTADIOS_CAPITAL = {"neo química arena": "Neo Quimica Arena", "arena corinthians": "Neo Quimica Arena",
                    "allianz parque": "Allianz Parque", "morumbi": "Morumbi", "estádio do morumbi": "Morumbi",
                    "morumbis": "Morumbi", "estádio cícero pompeu de toledo": "Morumbi"}


def normaliza_estadio(e):
    e0 = (e or "").split(",")[0].strip()
    return ESTADIOS_CAPITAL.get(e0.lower(), e0)


def data_da_sumula(url):
    """Data contida no link da sumula do ge (dd-mm-aaaa) -- conferencia independente da data."""
    m = re.search(r"/jogo/(\d{2})-(\d{2})-(\d{4})/", url or "")
    return pd.Timestamp(int(m[3]), int(m[2]), int(m[1])) if m else pd.NaT


def grava_saidas(comp, m137, falta, extra_capital=None):
    """data/bronze/jogos_complementares.csv = 4 competicoes + jogos de Serie A/Copa do Brasil que a
    Wikipedia tem e o BR-Football-Dataset nao (lacuna da base). Supercopa (Brasilia) fica de fora."""
    falta = falta[falta["competicao_secao"].isin(["Serie A", "Copa do Brasil"])].copy()
    falta["horario_confirmado"] = falta["hora"].notna() & (falta["utc_offset"] == -3)
    falta["fora_da_capital"] = ~falta["cidade"].map(cidade_capital)
    falta["origem"] = "lacuna_br_football_dataset"
    comp = comp.copy()
    comp["origem"] = "competicao_ausente_da_base"
    partes = [comp, falta]
    if extra_capital is not None and len(extra_capital):
        e = extra_capital.copy()
        e["origem"] = "mandante_fora_da_capital_jogando_na_capital"
        e["fora_da_capital"] = False
        e["mandante"] = e["team1"].map(lambda x: identifica_clube(x) or x)
        partes.append(e)
    allj = pd.concat(partes, ignore_index=True)
    pub = [publico_status(a, b) for a, b in zip(allj["publico"], allj["nota"])]
    allj["chave"] = allj["data"].dt.strftime("%Y-%m-%d") + "_" + allj["mandante"]
    sum_dt = allj["sumula"].map(data_da_sumula)
    out = pd.DataFrame({
        "data_br": allj["data"].dt.date,
        "horario_br": allj["hora"].where(allj["horario_confirmado"]),
        "horario_confirmado": allj["horario_confirmado"],
        "horario_fonte_txt": allj["hora_txt"],
        "mandante": allj["mandante"], "visitante": allj["team2"],
        "competicao": allj["competicao_secao"],
        "fase": (allj["secao"].fillna("") + " " + allj["rodada"].fillna("").astype(str)).str.strip(),
        "placar": allj["placar"].str.replace("–", "-"),
        "estadio": allj["estadio"].map(normaliza_estadio), "cidade": allj["cidade"].str.split(",").str[0],
        "fora_da_capital": allj["fora_da_capital"],
        "incluir_analise": allj["horario_confirmado"] & ~allj["fora_da_capital"],
        "publico_wiki": allj["publico"],
        "publico": [x[0] for x in pub], "publico_status": [x[1] for x in pub], "nota_fonte": allj["nota"],
        "origem": allj["origem"],
        "fonte_jogo": allj["url_revisao"],
        "fonte_sumula": allj["sumula"],
        "data_sumula_confere": (sum_dt.isna() | (sum_dt == allj["data"])),
        "conferido_pagina_edicao": allj["conferido_edicao"].eq(True) if "conferido_edicao" in allj else False,
        "fonte_conferencia": allj.get("conf_pagina"),
        "fonte_extra": allj["chave"].map(CONFERENCIA_EXTRA),
    }).sort_values(["data_br", "horario_br"]).reset_index(drop=True)
    out.to_csv(os.path.join(BRONZE, "jogos_complementares.csv"), index=False)

    m = m137.copy()
    m["chave2"] = m["data_br"].dt.strftime("%Y-%m-%d") + "_" + m["mandante"]
    base = pd.DataFrame({
        "jogo_id": m["jogo_id"], "estadio_real": m["estadio_y"].map(normaliza_estadio),
        "cidade_real": m["cidade"].str.split(",").str[0], "fora_da_capital": m["fora_da_capital"],
        "hora_wiki": m["hora"], "hora_bate_wiki": m["hora_bate"], "fonte_jogo": m["url_revisao_y"]
        if "url_revisao_y" in m else m["url_revisao"],
        "fonte_extra": m["chave2"].map(CONFERENCIA_EXTRA),
        "publico": [publico_status(a, b)[0] for a, b in zip(m["publico"], m["nota"])],
        "publico_status": [publico_status(a, b)[1] for a, b in zip(m["publico"], m["nota"])],
        "nota_fonte": m["nota"],
    })
    base.to_csv(os.path.join(BRONZE, "jogos_base_conferencia_wikipedia.csv"), index=False)
    return out, base


if __name__ == "__main__":
    if "--baixar" in sys.argv or not os.path.exists(os.path.join(WIKI, "manifesto.json")):
        print("Baixando snapshots da Wikipedia (so os que faltam; --forcar rebaixa todos)")
        baixar(forcar="--forcar" in sys.argv)
    todas, prim = monta()
    print(f"  partidas lidas: {len(todas)} | em casa (paginas de temporada, 2022-2023): {len(prim)}")
    print(prim.groupby(["competicao_secao", "mandante"]).size().unstack(fill_value=0))
    comp = complementares(prim, todas)
    cols = ["competicao_secao", "secao", "rodada", "data", "hora", "utc_offset", "horario_confirmado", "mandante",
            "team2", "placar", "cidade", "estadio", "fora_da_capital", "publico", "conferido_edicao",
            "conf_hora", "conf_estadio", "hora_diverge_edicao", "sumula", "url_revisao"]
    comp[[c for c in cols if c in comp]].to_csv(os.path.join(TAB, "conferencia_complementares_bruto.csv"), index=False)
    m137, falta = confere_137(prim)
    m137.to_csv(os.path.join(TAB, "conferencia_137_jogos_wikipedia.csv"), index=False)
    falta.to_csv(os.path.join(TAB, "conferencia_jogos_wiki_fora_da_base.csv"), index=False)
    print(f"  complementares: {len(comp)} | sem horario confirmado: {(~comp['horario_confirmado']).sum()} "
          f"| fora da capital: {comp['fora_da_capital'].sum()} | conferidos em pag. de edicao: "
          f"{comp['conferido_edicao'].sum()} | hora diverge: {comp['hora_diverge_edicao'].sum()}")
    print(f"  137 originais: achados na wiki {m137['achou_na_wiki'].sum()} | hora bate "
          f"{m137['hora_bate'].sum()} | fora da capital {m137['fora_da_capital'].sum()} "
          f"| jogos wiki ausentes da base: {len(falta)}")
    tj, n_amist = todos_os_jogos(todas)
    tj.to_csv(os.path.join(WIKI, "jogos_4_times_dedup.csv"), index=False)
    extra = capital_sem_mandante_capital(tj)
    print(f"  jogos oficiais dos 4 times (dedup): {len(tj)} | amistosos fora: {n_amist} | na capital: "
          f"{tj['em_capital'].sum()} | capital sem mandante da capital: {len(extra)} | sem horario confirmado: "
          f"{(~tj['horario_confirmado']).sum()}")
    if len(extra):
        print(extra[["data", "hora", "team1", "team2", "competicao_secao", "estadio"]].to_string(index=False))
    fc = grava_fora_capital(tj)
    print(f"  [ok] data/bronze/jogos_fora_capital.csv: {len(fc)} jogos | horario confirmado "
          f"{fc['horario_confirmado'].sum()} | RMSP {fc['regiao_metropolitana_sp'].sum()} | offsets "
          f"{fc['utc_offset_local'].value_counts(dropna=False).to_dict()}")
    v = valida_fora(fc, todas)
    for fonte, g in v.groupby("fonte_conf"):
        print(f"  conferencia fuso fora ({fonte}): {len(g)} jogos | achados {g['achou'].sum()} | batem (<=15 min) "
              f"{g['bate'].sum()} | divergem {(g['achou'] & ~g['bate']).sum()}")
    out, base = grava_saidas(comp, m137, falta, extra)
    print(f"  [ok] data/bronze/jogos_complementares.csv: {len(out)} jogos | incluir_analise "
          f"{out['incluir_analise'].sum()} | por origem {out['origem'].value_counts().to_dict()} "
          f"| data da sumula diverge: {(~out['data_sumula_confere']).sum()}")
    print(f"  [ok] data/bronze/jogos_base_conferencia_wikipedia.csv: fora da capital {base['fora_da_capital'].sum()}")
