# -*- coding: utf-8 -*-
"""
06_clima_casos_meningites_v17.py
Correlação clima-casos com Pearson, Spearman e R² por lag.
"""

import re
import numpy as np
import pandas as pd
from meningites_v17_common import *

def read_climate(path):
    last = None
    for enc in ["latin1", "cp1252", "utf-8-sig", "utf-8"]:
        for sep in [";", ",", "\t", "|"]:
            try:
                d = pd.read_csv(path, sep=sep, encoding=enc, low_memory=False)
                if d.shape[1] > 5:
                    return d, enc, sep
            except Exception as e:
                last = e
    raise ValueError(f"Não foi possível ler clima: {last}")

def main():
    df = load_base_v17()
    clim_file = find_file(["historico_clima_10_anos*.csv", "*clima*.csv"])
    if clim_file is None:
        (OUT / "diagnostico_clima_v17.txt").write_text("Arquivo climático não encontrado.", encoding="utf-8")
        print("[AVISO] Arquivo climático não encontrado.")
        return
    clim, enc, sep = read_climate(clim_file)
    clim.columns = [strip_accents(c).strip().lower().replace(" ", "_") for c in clim.columns]
    if "data" not in clim.columns:
        dc = next((c for c in clim.columns if "data" in c or "date" in c), None)
        if dc: clim = clim.rename(columns={dc: "data"})
    clim["data"] = pd.to_datetime(clim["data"], errors="coerce")

    nums = ["temperatura_media","temperatura_maxima","temperatura_minima","chuva_mm","umidade_relativa","indice_calor_maximo","horas_calor_critico"]
    for c in nums:
        if c in clim.columns:
            clim[c] = pd.to_numeric(clim[c], errors="coerce")
    for c in ["temperatura_media","temperatura_maxima","temperatura_minima"]:
        if c in clim.columns:
            clim.loc[(clim[c] < -10) | (clim[c] > 55), c] = np.nan
    if "chuva_mm" in clim.columns:
        clim.loc[(clim["chuva_mm"] < 0) | (clim["chuva_mm"] > 500), "chuva_mm"] = np.nan
    if "umidade_relativa" in clim.columns:
        clim.loc[(clim["umidade_relativa"] < 0) | (clim["umidade_relativa"] > 100), "umidade_relativa"] = np.nan

    cases = df.groupby("data_ref_v17").agg(casos=("caso_v17","sum")).reset_index().rename(columns={"data_ref_v17":"data"})
    clima_state = clim.groupby("data").agg({c:"mean" for c in nums if c in clim.columns}).reset_index()
    daily = clima_state.merge(cases, on="data", how="left").fillna({"casos":0}).sort_values("data")

    rows = []
    vars_clima = [c for c in nums if c in daily.columns]
    for var in vars_clima:
        for lag in range(0, 31):
            temp = daily[["data","casos",var]].copy()
            temp[f"{var}_lag{lag}"] = temp[var].shift(lag)
            ok = temp[f"{var}_lag{lag}"].notna() & temp["casos"].notna()
            if ok.sum() >= 30:
                pear = temp.loc[ok, f"{var}_lag{lag}"].corr(temp.loc[ok, "casos"], method="pearson")
                spear = temp.loc[ok, f"{var}_lag{lag}"].corr(temp.loc[ok, "casos"], method="spearman")
                r2 = pear**2 if pd.notna(pear) else np.nan
            else:
                pear = spear = r2 = np.nan
            rows.append({
                "variavel_climatica": var, "lag_dias": lag, "pearson": pear, "spearman": spear, "r2": r2,
                "n_dias_validos": int(ok.sum()),
                "nota_tecnica": "R² é exploratório e não implica causalidade; correlação ecológica deve ser interpretada com cautela."
            })

    daily.to_csv(OUT / "clima_casos_diario_v17.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows).to_csv(OUT / "correlacao_clima_casos_v17.csv", index=False, encoding="utf-8-sig")
    (OUT / "diagnostico_clima_v17.txt").write_text(
        f"Arquivo: {clim_file.name}\nEncoding: {enc}\nSeparador: {repr(sep)}\nVariáveis: {', '.join(vars_clima)}\nValores sentinela foram removidos.",
        encoding="utf-8"
    )
    print("[OK] Clima-casos V17 gerado.")

if __name__ == "__main__":
    main()
