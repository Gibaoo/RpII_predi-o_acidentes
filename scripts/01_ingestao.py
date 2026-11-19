"""
01_ingestao.py
Camada BRONZE - le as fontes brutas e materializa copias locais em data/bronze/.
Nao faz nenhuma limpeza, harmonizacao ou filtro aqui - so garante que os dados
brutos estao acessiveis em formato tabular.

Reprodutibilidade: se os CSVs de criminalidade ja existirem em data/bronze/,
a conversao (que streama os .xlsx via openpyxl em read_only) e pulada. Rodando
do zero, o script refaz a conversao a partir dos .xlsx originais.
"""
import os
import csv
import time
from openpyxl import load_workbook

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")  # pasta com os arquivos brutos originais
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
os.makedirs(BRONZE_DIR, exist_ok=True)


def convert_xlsx_sheet_to_csv(xlsx_path, sheet_name, out_csv_path):
    """Converte uma aba de um .xlsx grande para CSV via streaming (openpyxl read_only).
    Evita carregar o arquivo inteiro na memoria - necessario para os ~200MB por ano
    da base SPDadosCriminais."""
    if os.path.exists(out_csv_path):
        print(f"  [cache] {out_csv_path} ja existe, pulando conversao")
        return out_csv_path

    t0 = time.time()
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    n = 0
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in ws.iter_rows(values_only=True):
            writer.writerow(row)
            n += 1
    wb.close()
    print(f"  [convertido] {out_csv_path}: {n} linhas em {time.time()-t0:.1f}s")
    return out_csv_path


def ingest_crime():
    """Fonte: SPDadosCriminais 2022/2023 (SSP-SP / Dados Abertos SP).
    Cada ano tem 2 abas (semestres). Retorna a lista dos 4 CSVs bronze."""
    print("Ingestao: criminalidade (SPDadosCriminais)")
    jobs = [
        ("SPDadosCriminais_2022.xlsx", "JAN-JUN_2022", "crime_2022_jan_jun.csv"),
        ("SPDadosCriminais_2022.xlsx", "JUL-DEZ_2022", "crime_2022_jul_dez.csv"),
        ("SPDadosCriminais_2023.xlsx", "JAN-JUN_2023", "crime_2023_jan_jun.csv"),
        ("SPDadosCriminais_2023.xlsx", "JUL-DEZ_2023", "crime_2023_jul_dez.csv"),
    ]
    out_paths = []
    for xlsx_name, sheet, out_name in jobs:
        xlsx_path = os.path.join(UPLOADS_DIR, xlsx_name)
        out_csv = os.path.join(BRONZE_DIR, out_name)
        out_paths.append(convert_xlsx_sheet_to_csv(xlsx_path, sheet, out_csv))
    return out_paths


def ingest_football():
    """Fonte: BR-Football-Dataset.csv (upload do usuario). Ja esta em CSV,
    so garantimos a copia em bronze/."""
    print("Ingestao: futebol (BR-Football-Dataset)")
    src = os.path.join(UPLOADS_DIR, "BR-Football-Dataset.csv")
    dst = os.path.join(BRONZE_DIR, "BR-Football-Dataset.csv")
    if not os.path.exists(dst):
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
    print(f"  [ok] {dst}")
    return dst


def ingest_weather():
    """Fonte: INMET, estacao A701 Sao Paulo - Mirante. Usamos 2022 e 2023
    (janela de sobreposicao com crime e futebol). 2020/2021 tambem foram
    enviados e ficam disponiveis em uploads/ para uma janela historica maior,
    caso o modelo final precise de mais anos de clima como baseline."""
    print("Ingestao: clima (INMET)")
    out_paths = []
    for year in (2022, 2023):
        src = os.path.join(
            UPLOADS_DIR,
            f"INMET_SE_SP_A701_SAO PAULO - MIRANTE_01-01-{year}_A_31-12-{year}.CSV",
        )
        dst = os.path.join(BRONZE_DIR, f"inmet_{year}.csv")
        if not os.path.exists(dst):
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
        print(f"  [ok] {dst}")
        out_paths.append(dst)
    return out_paths


def ingest_accidents():
    """Fonte: Infosiga SP (Detran-SP), arquivos anuais 'sinistros_AAAA.csv'
    baixados manualmente pelo usuario (o endpoint de ZIP consolidado do
    Detran retornava 'nao autorizado' via download automatizado) e enviados
    por upload. Copiamos para bronze/ sem nenhuma transformacao."""
    print("Ingestao: acidentes (Infosiga SP)")
    out_paths = []
    for year in (2022, 2023):
        src = os.path.join(UPLOADS_DIR, f"sinistros_{year}.csv")
        dst = os.path.join(BRONZE_DIR, f"sinistros_{year}.csv")
        if not os.path.exists(dst) and os.path.exists(src):
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
        print(f"  [ok] {dst}")
        out_paths.append(dst)
    return out_paths


def ingest_external_notice():
    """Fontes externas identificadas na Etapa 2 que ainda EXIGEM acesso a
    internet (Kaggle - publico pagante, BrasilAPI) nao foram baixadas
    automaticamente (sandbox sem rede). Feriados nacionais/estaduais/
    municipais foram calculados localmente (algoritmo de Meeus/Jones/Butcher
    para a Pascoa) em 02_limpeza.py - nao dependem de rede."""
    print("Aviso: Kaggle (publico pagante) ainda nao foi baixado (opcional).")


def main():
    ingest_crime()
    ingest_football()
    ingest_weather()
    ingest_accidents()
    ingest_external_notice()
    print("\nBronze materializado em:", BRONZE_DIR)
    print(os.listdir(BRONZE_DIR))


if __name__ == "__main__":
    main()
