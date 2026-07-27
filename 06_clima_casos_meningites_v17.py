# -*- coding: utf-8 -*-
"""
06_clima_casos_meningites_v17.py
Correlação exploratória clima × casos / evolução / desfechos (lags 0–30 dias).
Não implica causalidade. Não é o SIS Clima-Saúde.
"""

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


def _corr_block(daily: pd.DataFrame, outcome: str, vars_clima: list) -> list:
    rows = []
    if outcome not in daily.columns:
        return rows
    for var in vars_clima:
        for lag in range(0, 31):
            temp = daily[["data", outcome, var]].copy()
            temp[f"{var}_lag{lag}"] = temp[var].shift(lag)
            ok = temp[f"{var}_lag{lag}"].notna() & temp[outcome].notna()
            if ok.sum() >= 30:
                pear = temp.loc[ok, f"{var}_lag{lag}"].corr(temp.loc[ok, outcome], method="pearson")
                spear = temp.loc[ok, f"{var}_lag{lag}"].corr(temp.loc[ok, outcome], method="spearman")
                r2 = pear**2 if pd.notna(pear) else np.nan
            else:
                pear = spear = r2 = np.nan
            rows.append({
                "desfecho": outcome,
                "variavel_climatica": var,
                "lag_dias": lag,
                "pearson": pear,
                "spearman": spear,
                "r2": r2,
                "n_dias_validos": int(ok.sum()),
                "nota_tecnica": (
                    "Correlação ecológica exploratória — não implica causalidade. "
                    "Validar sazonalidade e atraso de notificação."
                ),
            })
    return rows


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
        if dc:
            clim = clim.rename(columns={dc: "data"})
    clim["data"] = pd.to_datetime(clim["data"], errors="coerce")

    nums = [
        "temperatura_media", "temperatura_maxima", "temperatura_minima",
        "chuva_mm", "umidade_relativa", "indice_calor_maximo", "horas_calor_critico",
    ]
    for c in nums:
        if c in clim.columns:
            clim[c] = pd.to_numeric(clim[c], errors="coerce")
    for c in ["temperatura_media", "temperatura_maxima", "temperatura_minima"]:
        if c in clim.columns:
            clim.loc[(clim[c] < -10) | (clim[c] > 55), c] = np.nan
    if "chuva_mm" in clim.columns:
        clim.loc[(clim["chuva_mm"] < 0) | (clim["chuva_mm"] > 500), "chuva_mm"] = np.nan
    if "umidade_relativa" in clim.columns:
        clim.loc[(clim["umidade_relativa"] < 0) | (clim["umidade_relativa"] > 100), "umidade_relativa"] = np.nan

    g = df.groupby("data_ref_v17").agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos=("obito_meningite_v17", "sum"),
        altas=("alta_v17", "sum"),
    ).reset_index().rename(columns={"data_ref_v17": "data"})

    clima_state = clim.groupby("data").agg({c: "mean" for c in nums if c in clim.columns}).reset_index()
    daily = clima_state.merge(g, on="data", how="left")
    for c in ["casos", "confirmados", "hospitalizacoes", "obitos", "altas"]:
        if c in daily.columns:
            daily[c] = daily[c].fillna(0)
    daily = daily.sort_values("data")

    vars_clima = [c for c in nums if c in daily.columns]
    outcomes = [c for c in ["casos", "confirmados", "hospitalizacoes", "obitos", "altas"] if c in daily.columns]

    rows = []
    for outcome in outcomes:
        rows.extend(_corr_block(daily, outcome, vars_clima))

    daily.to_csv(OUT / "clima_casos_diario_v17.csv", index=False, encoding="utf-8-sig")
    corr = pd.DataFrame(rows)
    corr.to_csv(OUT / "correlacao_clima_casos_v17.csv", index=False, encoding="utf-8-sig")

    if not corr.empty and "spearman" in corr.columns:
        corr["abs_r"] = pd.to_numeric(corr["spearman"], errors="coerce").abs()
        best = (
            corr.sort_values("abs_r", ascending=False)
            .groupby("desfecho", as_index=False)
            .head(8)
        )
        best.to_csv(OUT / "correlacao_clima_desfechos_top_v17.csv", index=False, encoding="utf-8-sig")

    (OUT / "diagnostico_clima_v17.txt").write_text(
        f"Arquivo: {clim_file.name}\nEncoding: {enc}\nSeparador: {repr(sep)}\n"
        f"Variáveis: {', '.join(vars_clima)}\nDesfechos: {', '.join(outcomes)}\n"
        "Correlação exploratória clima×meningites (não é o SIS Clima-Saúde).",
        encoding="utf-8",
    )
    print("[OK] Clima-casos/desfechos V17 gerado.")


if __name__ == "__main__":
    main()
