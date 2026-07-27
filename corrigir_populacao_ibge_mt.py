import pandas as pd
import re
from pathlib import Path

INPUT = Path("População Municípios Brasil 2020-2025.csv")
OUTPUT = Path("populacao_padronizada_mt.csv")

def norm_col(c):
    c = str(c).strip().lower()
    mapa = {
        "ç": "c", "ã": "a", "á": "a", "à": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o", "ô": "o",
        "õ": "o", "ú": "u"
    }
    for k, v in mapa.items():
        c = c.replace(k, v)
    c = re.sub(r"[^a-z0-9]+", "_", c)
    return c.strip("_")

def read_csv_smart(path):
    for sep in [",", ";", "\t", "|"]:
        for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
                if df.shape[1] > 1:
                    print(f"[OK] Lido com sep={sep!r}, encoding={enc}")
                    return df
            except Exception:
                pass
    raise RuntimeError("Não consegui ler o arquivo de população.")

def parse_pop(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s == "" or s.lower() in ["nan", "none", "null"]:
        return None

    s = re.sub(r"[,.]0$", "", s)
    s = re.sub(r"\D", "", s)

    if s == "":
        return None
    return int(s)

df = read_csv_smart(INPUT)
df.columns = [norm_col(c) for c in df.columns]

print("Colunas detectadas:")
print(df.columns.tolist())

if "uf" in df.columns:
    df["uf"] = df["uf"].astype(str).str.upper().str.strip()
    df = df[df["uf"].isin(["MT", "MATO GROSSO"])].copy()
    print(f"[OK] Filtrado para MT: {len(df)} municípios/linhas de origem")

if "cod_ibge_6" in df.columns:
    cod_col = "cod_ibge_6"
elif "codigo_municipio" in df.columns:
    cod_col = "codigo_municipio"
elif "cod_municipio" in df.columns:
    cod_col = "cod_municipio"
elif "cod_ibge" in df.columns:
    cod_col = "cod_ibge"
elif "cod_ibge_7" in df.columns:
    cod_col = "cod_ibge_7"
else:
    candidatos = [c for c in df.columns if "cod" in c or "ibge" in c]
    if not candidatos:
        raise ValueError("Não encontrei coluna de código municipal.")
    cod_col = candidatos[0]

year_cols = [c for c in df.columns if re.fullmatch(r"20[0-9]{2}", c)]

if not year_cols:
    raise ValueError("Não encontrei colunas de ano, como 2020, 2021, 2022, 2023, 2024, 2025.")

print(f"[OK] Coluna de código municipal: {cod_col}")
print(f"[OK] Anos detectados: {year_cols}")

out = df.melt(
    id_vars=[cod_col],
    value_vars=year_cols,
    var_name="ano",
    value_name="populacao"
)

out = out.rename(columns={cod_col: "codigo_municipio"})

out["codigo_municipio"] = (
    out["codigo_municipio"]
    .astype(str)
    .str.extract(r"(\d+)", expand=False)
)

out["codigo_municipio"] = out["codigo_municipio"].apply(
    lambda x: x[:6] if isinstance(x, str) and len(x) >= 7 else x
)

out["codigo_municipio"] = out["codigo_municipio"].str.zfill(6)
out["ano"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int64")
out["populacao"] = out["populacao"].apply(parse_pop)

out = out.dropna(subset=["codigo_municipio", "ano", "populacao"])
out["populacao"] = out["populacao"].astype(int)

out = out[["codigo_municipio", "ano", "populacao"]].drop_duplicates()
out = out.sort_values(["codigo_municipio", "ano"])

out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

print(f"[OK] Arquivo gerado: {OUTPUT.resolve()}")
print()
print(out.head(20))
print()
print(f"Municípios únicos: {out['codigo_municipio'].nunique()}")
print(f"Linhas: {len(out)}")
print(f"Anos: {sorted(out['ano'].dropna().unique().tolist())}")

if out["codigo_municipio"].nunique() < 130:
    print("[ATENÇÃO] Foram encontrados poucos municípios. Verifique se a coluna UF está como MT ou MATO GROSSO.")