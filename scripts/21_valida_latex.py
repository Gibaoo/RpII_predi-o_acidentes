r"""
21_valida_latex.py
Checagem de sintaxe LaTeX sem precisar de pdflatex/xelatex (nao disponivel
neste ambiente). Roda contra qualquer .tex do projeto -- resolve
\\input{...} de arquivos no mesmo diretorio antes de checar.

Verifica:
  - chaves balanceadas ({{ }})
  - todo \cite{} resolve a um \bibitem{} e vice-versa (nenhum \bibitem orfao)
  - todo \ref{} resolve a um \label{}
  - toda linha de dado em toda tabela tem o numero de colunas certo (conta
    '&' e compara com a especificacao do \begin{tabular}{...})
  - nenhum '%' cru (nao escapado) que cortaria o resto da linha como comentario

Uso:
    python 21_valida_latex.py docs/rpII_predicao_acidentes.tex
    python 21_valida_latex.py docs/rpII_predicao_acidentes_relatorio_completo.tex
"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_inputs(path):
    """Le o .tex e substitui \\input{nome} pelo conteudo de nome.tex no
    mesmo diretorio (uma vez, sem recursao -- suficiente para este projeto)."""
    d = os.path.dirname(path)
    s = open(path, encoding="utf-8").read()

    def sub(m):
        nome = m.group(1)
        alvo = os.path.join(d, nome if nome.endswith(".tex") else nome + ".tex")
        if os.path.exists(alvo):
            return open(alvo, encoding="utf-8").read()
        print(f"[aviso] \\input{{{nome}}} nao encontrado em {d}, mantendo como esta")
        return m.group(0)

    return re.sub(r"\\input\{([^}]*)\}", sub, s)


def find_spec(s, start):
    assert s[start] == "{"
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1 : i], i + 1
    raise ValueError("chave de \\begin{tabular}{...} sem fechamento")


def checa_tabelas(s):
    idx, n, erros = 0, 0, 0
    while True:
        m = re.search(r"\\begin\{tabular\}", s[idx:])
        if not m:
            break
        pos = idx + m.end()
        spec, after = find_spec(s, pos)
        end_m = re.search(r"\\end\{tabular\}", s[after:])
        if not end_m:
            print("[ERRO] \\begin{tabular} sem \\end{tabular} correspondente")
            break
        body = s[after : after + end_m.start()]
        ncols = len(re.findall(r"[lrc]", re.sub(r"@\{[^}]*\}", "", spec)))
        rows = [
            ln
            for ln in body.split("\\\\")
            if ln.strip() and not any(k in ln for k in ("toprule", "midrule", "bottomrule"))
        ]
        n += 1
        for r in rows:
            namps = r.count("&")
            if namps != ncols - 1:
                erros += 1
                print(
                    f"[ERRO] tabela #{n} (spec='{spec}', {ncols} cols): "
                    f"linha com {namps} '&' (esperado {ncols - 1}): {r.strip()[:80]}"
                )
        idx = after + end_m.end()
    print(f"[ok] {n} tabelas verificadas, {erros} linha(s) com número de colunas errado")
    return erros == 0


def checa_cites_refs(s):
    cites = set()
    for m in re.finditer(r"\\cite\{([^}]*)\}", s):
        cites.update(x.strip() for x in m.group(1).split(","))
    # aceita tambem \bibitem[rotulo]{chave} (thebibliography no estilo SBC, como no rp_ii)
    bibitems = set(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}", s))
    labels = set(re.findall(r"\\label\{([^}]*)\}", s))
    refs = set(re.findall(r"\\ref\{([^}]*)\}", s))

    ok = True
    orfaos_cite = cites - bibitems
    orfaos_ref = refs - labels
    nao_citados = bibitems - cites
    nao_referenciados = labels - refs
    if orfaos_cite:
        ok = False
        print(f"[ERRO] \\cite sem \\bibitem correspondente: {sorted(orfaos_cite)}")
    if orfaos_ref:
        ok = False
        print(f"[ERRO] \\ref sem \\label correspondente: {sorted(orfaos_ref)}")
    if nao_citados:
        print(f"[aviso] \\bibitem nunca citado no texto: {sorted(nao_citados)}")
    if nao_referenciados:
        print(f"[aviso] \\label nunca referenciado (\\ref) no texto: {sorted(nao_referenciados)}")
    if ok:
        print(f"[ok] {len(cites)} \\cite / {len(bibitems)} \\bibitem, "
             f"{len(refs)} \\ref / {len(labels)} \\label -- todos resolvem")
    return ok


def checa_percent_cru(s):
    """So sinaliza '%' cru NO MEIO de uma linha com conteudo real -- uma
    linha que e comentario puro (primeiro caractere nao-espaco = '%') e
    sintaxe LaTeX valida e intencional, nao um erro."""
    linhas = s.split("\n")
    erros = 0
    for i, ln in enumerate(linhas, 1):
        if ln.lstrip().startswith("%"):
            continue  # linha de comentario inteira, valida
        sem_escapados = ln.replace(r"\%", "")
        if "%" in sem_escapados:
            erros += 1
            print(f"[ERRO] linha {i}: '%' não escapado (vira comentário LaTeX): {ln.strip()[:80]}")
    print(f"[ok] checagem de '%' cru: {erros} problema(s)")
    return erros == 0


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    s = resolve_inputs(path)

    print(f"=== Validando {path} (com \\input resolvido) ===\n")
    ok_braces = s.count("{") == s.count("}")
    print(f"[{'ok' if ok_braces else 'ERRO'}] chaves: {{ ={s.count('{')} }} ={s.count('}')}")
    ok_tab = checa_tabelas(s)
    ok_cr = checa_cites_refs(s)
    ok_pc = checa_percent_cru(s)

    print()
    if all([ok_braces, ok_tab, ok_cr, ok_pc]):
        print("RESULTADO: nenhum problema estrutural encontrado (não substitui compilar de verdade).")
    else:
        print("RESULTADO: há problema(s) acima -- corrigir antes de considerar o arquivo pronto.")
        sys.exit(1)


if __name__ == "__main__":
    main()
