from __future__ import annotations

import numpy as np
import pandas as pd


def compute_epidemiological_indicators(df: pd.DataFrame, population: pd.DataFrame | None = None) -> pd.DataFrame:
    group_cols = ["ano_evento", "CodigoMunicipioResidencia", "MunicipioResidencia", "ClassificacaoMeningite"]
    group_cols = [c for c in group_cols if c in df.columns]

    g = (
        df.groupby(group_cols, dropna=False)
        .agg(
            casos=("NumeroCasos", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(1).sum())),
            confirmados=("confirmado", "sum"),
            obitos_meningite=("obito_meningite", "sum"),
            obitos_totais=("obito_total", "sum"),
            internacoes=("hospitalizado", "sum"),
        )
        .reset_index()
    )

    g["letalidade_confirmados_pct"] = 100 * g["obitos_meningite"] / g["confirmados"].replace(0, np.nan)
    g["proporcao_internacao_pct"] = 100 * g["internacoes"] / g["casos"].replace(0, np.nan)

    if population is not None and {"CodigoMunicipioResidencia", "ano_evento"}.issubset(g.columns):
        pop = population.rename(columns={"codigo_municipio": "CodigoMunicipioResidencia", "ano": "ano_evento"})
        g = g.merge(pop[["CodigoMunicipioResidencia", "ano_evento", "populacao"]], how="left",
                    on=["CodigoMunicipioResidencia", "ano_evento"])
        g["incidencia_100mil"] = 100_000 * g["confirmados"] / g["populacao"].replace(0, np.nan)
        g["mortalidade_100mil"] = 100_000 * g["obitos_meningite"] / g["populacao"].replace(0, np.nan)
    else:
        g["populacao"] = np.nan
        g["incidencia_100mil"] = np.nan
        g["mortalidade_100mil"] = np.nan

    return g
