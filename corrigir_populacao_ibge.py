import pandas as pd
import re
from pathlib import Path

INPUT = Path("População Municípios Brasil 2020-2025.csv")
OUTPUT = Path("populacao_padronizada.csv")

def norm_col(c):
    c = str(c).strip().lower()
    c = (
        c.replace("ç", "c")
         .replace("ã", "a")
         .replace("á", "a")
         .replace("à", "a")
         .replace("â", "a")
         .replace("é", "e")
         .replace("ê", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ô", "o")
         .replace("õ", "o")
         .replace("ú", "u")
    )
    c = re.sub(r"[^a-z0-9]+", "_", c)
    return c.strip("_")

def read_csv_smart(path):
    for sep in [";", ",", "\t", "|"]:
        for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, low_memory=False)
                if df.shape[1] > 1:
                    print(f"[OK] Lido com sep={sep!r}, encoding={enc}")
                    return df
            except Exception:
                pass
    raise RuntimeError("Não consegui ler o arquivo de população.")

df = read_csv_smart(INPUT)
df.columns = [norm_col(c) for c in df.columns]

print("Colunas detectadas:")
print(df.columns.tolist())

# Detecta coluna de código municipal
possiveis_cod = [
    "codigo_municipio", "cod_municipio", "cod_mun", "cod_ibge",
    "codigo_ibge", "ibge", "geocodigo", "cd_mun", "id_municipio"
]

cod_col = None
for c in possiveis_cod:
    if c in df.columns:
        cod_col = c
        break

if cod_col is None:
    for c in df.columns:
        if "cod" in c or "ibge" in c or "geocod" in c:
            cod_col = c
            break

if cod_col is None:
    raise ValueError("Não encontrei coluna de código municipal/IBGE.")

# Detecta formato largo: colunas 2020, 2021, 2022...
year_cols = [c for c in df.columns if re.fullmatch(r"20[0-9]{2}", c)]

if year_cols:
    print(f"[OK] Formato largo detectado. Anos: {year_cols}")

    out = df.melt(
        id_vars=[cod_col],
        value_vars=year_cols,
        var_name="ano",
        value_name="populacao"
    )

else:
    # Detecta formato longo
    ano_col = None
    pop_col = None

    for c in df.columns:
        if c in ["ano", "year"]:
            ano_col = c
        if c in ["populacao", "pop", "pop_total", "habitantes", "valor"]:
            pop_col = c

    if ano_col is None:
        for c in df.columns:
            if "ano" in c:
                ano_col = c
                break

    if pop_col is None:
        for c in df.columns:
            if "pop" in c or "habit" in c or "valor" in c:
                pop_col = c
                break

    if ano_col is None or pop_col is None:
        raise ValueError(
            "Não encontrei colunas de ano/população. "
            "Verifique os nomes exibidos acima."
        )

    print(f"[OK] Formato longo detectado: codigo={cod_col}, ano={ano_col}, populacao={pop_col}")

    out = df[[cod_col, ano_col, pop_col]].copy()
    out.columns = ["codigo_municipio", "ano", "populacao"]

if year_cols:
    out = out.rename(columns={cod_col: "codigo_municipio"})

out["codigo_municipio"] = (
    out["codigo_municipio"]
    .astype(str)
    .str.extract(r"(\d+)", expand=False)
    .str.zfill(6)
)

out["ano"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int64")

out["populacao"] = (
    out["populacao"]
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)

out["populacao"] = pd.to_numeric(out["populacao"], errors="coerce")

out = out.dropna(subset=["codigo_municipio", "ano", "populacao"])
out = out[["codigo_municipio", "ano", "populacao"]].drop_duplicates()

out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

print(f"[OK] Arquivo gerado: {OUTPUT.resolve()}")
print(out.head())
print(f"Linhas: {len(out)}")