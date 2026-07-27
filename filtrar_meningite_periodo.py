import pandas as pd
from pathlib import Path

INPUT = Path("meningite.csv")

# Defina aqui os recortes desejados
RECORTES = [
    (2010, 2026, "meningite_2010_2026_mt.csv"),
    (2020, 2025, "meningite_2020_2025_mt.csv"),
]

FILTRAR_APENAS_RESIDENTES_MT = True

df = pd.read_csv(INPUT, dtype=str, low_memory=False)

def parse_data(col):
    if col not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df[col], errors="coerce", dayfirst=True)

# Preferência epidemiológica:
# 1º Data dos primeiros sintomas
# 2º Data de notificação
data_sintomas = parse_data("DataPrimeirosSintomas")
data_notificacao = parse_data("DataNotificacao")

data_ref = data_sintomas.fillna(data_notificacao)

ano_ref = data_ref.dt.year

# Backup pelos campos de ano, caso alguma data não seja interpretada
if "AnoPrimeirosSintomas" in df.columns:
    ano_sintomas = pd.to_numeric(df["AnoPrimeirosSintomas"], errors="coerce")
    ano_ref = ano_ref.fillna(ano_sintomas)

if "AnoNotificacao" in df.columns:
    ano_notificacao = pd.to_numeric(df["AnoNotificacao"], errors="coerce")
    ano_ref = ano_ref.fillna(ano_notificacao)

df["_data_referencia_filtro"] = data_ref
df["_ano_referencia_filtro"] = ano_ref

# Corrige código municipal para evitar problema 510340.0 vs 510340
if "CodigoMunicipioResidencia" in df.columns:
    df["CodigoMunicipioResidencia"] = (
        df["CodigoMunicipioResidencia"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.extract(r"(\d+)", expand=False)
        .str.zfill(6)
    )

if FILTRAR_APENAS_RESIDENTES_MT and "UfResidencia" in df.columns:
    antes = len(df)
    df = df[df["UfResidencia"].astype(str).str.upper().str.strip().eq("MT")].copy()
    print(f"[OK] Filtro residentes MT: {antes} -> {len(df)} registros")

for inicio, fim, saida in RECORTES:
    sub = df[
        (df["_ano_referencia_filtro"] >= inicio)
        & (df["_ano_referencia_filtro"] <= fim)
    ].copy()

    sub = sub.drop(columns=["_data_referencia_filtro", "_ano_referencia_filtro"], errors="ignore")
    sub.to_csv(saida, index=False, encoding="utf-8-sig")

    print(f"[OK] {saida}: {len(sub)} registros | período {inicio}-{fim}")