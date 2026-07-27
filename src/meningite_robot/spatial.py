from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np


def spatial_pipeline(df: pd.DataFrame, shapefile: str, population: pd.DataFrame | None, outdir: Path) -> None:
    """Gera camada geoespacial municipal, Moran e municípios silenciosos quando dependências estiverem disponíveis."""
    try:
        import geopandas as gpd
    except Exception as exc:
        (outdir / "spatial_error.txt").write_text(f"GeoPandas indisponível: {exc}", encoding="utf-8")
        return

    gdf = gpd.read_file(shapefile)
    # Detecta coluna de código municipal.
    code_candidates = [c for c in gdf.columns if "CD_MUN" in c.upper() or "COD" in c.upper() and "MUN" in c.upper()]
    if not code_candidates:
        (outdir / "spatial_error.txt").write_text("Não foi possível identificar coluna de código municipal no shapefile.", encoding="utf-8")
        return
    shp_code = code_candidates[0]
    gdf[shp_code] = pd.to_numeric(gdf[shp_code], errors="coerce").astype("Int64")

    agg = df.groupby("CodigoMunicipioResidencia", dropna=False).agg(
        casos=("NumeroCasos", "size"),
        confirmados=("confirmado", "sum"),
        obitos=("obito_meningite", "sum"),
        internacoes=("hospitalizado", "sum"),
    ).reset_index()
    agg["CodigoMunicipioResidencia"] = pd.to_numeric(agg["CodigoMunicipioResidencia"], errors="coerce").astype("Int64")

    layer = gdf.merge(agg, left_on=shp_code, right_on="CodigoMunicipioResidencia", how="left")
    for c in ["casos", "confirmados", "obitos", "internacoes"]:
        layer[c] = layer[c].fillna(0)

    if population is not None:
        pop_latest = population.sort_values("ano").groupby("codigo_municipio").tail(1)
        layer = layer.merge(pop_latest[["codigo_municipio", "populacao"]], left_on=shp_code, right_on="codigo_municipio", how="left")
        layer["incidencia_100mil"] = 100_000 * layer["confirmados"] / layer["populacao"].replace(0, np.nan)

    # Municípios silenciosos: sem casos notificados no período.
    layer["municipio_silencioso"] = layer["casos"].eq(0)

    # Moran global opcional.
    try:
        from libpysal.weights import Queen
        from esda.moran import Moran
        w = Queen.from_dataframe(layer)
        w.transform = "r"
        y = layer["incidencia_100mil"].fillna(0) if "incidencia_100mil" in layer.columns else layer["confirmados"].fillna(0)
        moran = Moran(y.values, w)
        pd.DataFrame([{
            "moran_I": moran.I,
            "p_sim": moran.p_sim,
            "interpretacao": "Autocorrelação espacial positiva" if moran.I > 0 else "Sem padrão positivo evidente",
        }]).to_csv(outdir / "moran_global.csv", index=False, encoding="utf-8-sig")
    except Exception as exc:
        (outdir / "moran_error.txt").write_text(str(exc), encoding="utf-8")

    layer.to_file(outdir / "spatial_indicators.gpkg", driver="GPKG")
