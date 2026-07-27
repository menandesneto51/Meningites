# -*- coding: utf-8 -*-
"""
05_geoespacial_moran_meningites_v17.py
Mapas, Moran global e LISA quando geopandas/esda/libpysal estiverem disponíveis.
"""

import numpy as np
import pandas as pd
from meningites_v17_common import *

def main():
    ind = pd.read_csv(OUT / "indicadores_municipio_ano_classificacao_agrupada_v17.csv", encoding="utf-8-sig", low_memory=False)
    if ind.empty:
        print("[AVISO] Indicadores ausentes.")
        return
    latest = pd.to_numeric(ind["ano_evento_v17"], errors="coerce").max()
    d = ind[pd.to_numeric(ind["ano_evento_v17"], errors="coerce").eq(latest)].copy()
    d["score_risco"] = (
        pd.to_numeric(d["incidencia_100mil"], errors="coerce").fillna(0).rank(pct=True) +
        pd.to_numeric(d["mortalidade_100mil"], errors="coerce").fillna(0).rank(pct=True) +
        pd.to_numeric(d["letalidade_confirmados"], errors="coerce").fillna(0).rank(pct=True)
    )
    d.to_csv(OUT / "ranking_risco_territorial_v17.csv", index=False, encoding="utf-8-sig")

    shp = find_file(["MT_Municipios_2024.shp", "*.shp"])
    moran_rows = []
    lisa_rows = []
    if shp is None:
        (OUT / "moran_error_v17.txt").write_text("Shapefile não encontrado.", encoding="utf-8")
        print("[AVISO] Shapefile não encontrado.")
        return
    try:
        import geopandas as gpd
        from libpysal.weights import Queen
        from esda.moran import Moran, Moran_Local

        gdf = gpd.read_file(shp)
        # Detecta coluna de código municipal
        code_col = next((c for c in gdf.columns if "CD_MUN" in c.upper() or "GEOCOD" in c.upper() or "COD" in c.upper()), None)
        if code_col is None:
            raise ValueError("Não encontrei coluna de código municipal no shapefile.")
        gdf["codigo_municipio_v17"] = gdf[code_col].astype(str).str.extract(r"(\d{6})", expand=False)
        merged = gdf.merge(d, on="codigo_municipio_v17", how="left")
        merged["score_risco"] = pd.to_numeric(merged["score_risco"], errors="coerce").fillna(0)
        # Queen weights
        w = Queen.from_dataframe(merged)
        w.transform = "r"
        y = merged["score_risco"].values
        mi = Moran(y, w, permutations=999)
        moran_rows.append({
            "indicador": "score_risco",
            "moran_i": mi.I,
            "p_value": mi.p_sim,
            "interpretacao": "Autocorrelação espacial significativa." if mi.p_sim < 0.05 else "Sem evidência robusta de autocorrelação espacial."
        })
        lm = Moran_Local(y, w, permutations=999)
        merged["lisa_i"] = lm.Is
        merged["lisa_p"] = lm.p_sim
        merged["lisa_q"] = lm.q
        qmap = {1:"Alto-Alto", 2:"Baixo-Alto", 3:"Baixo-Baixo", 4:"Alto-Baixo"}
        merged["cluster_lisa"] = merged["lisa_q"].map(qmap)
        merged.loc[merged["lisa_p"] >= 0.05, "cluster_lisa"] = "Não significativo"
        keep = [c for c in ["codigo_municipio_v17","municipio_v17","regional_v17","classificacao_agrupada_v17","score_risco","lisa_i","lisa_p","cluster_lisa"] if c in merged.columns]
        merged[keep].to_csv(OUT / "lisa_clusters_v17.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(moran_rows).to_csv(OUT / "moran_global_v17.csv", index=False, encoding="utf-8-sig")
        try:
            merged.to_file(OUT / "mapas_geoespaciais_v17.gpkg", driver="GPKG")
        except Exception as e:
            (OUT / "gpkg_error_v17.txt").write_text(str(e), encoding="utf-8")
        print("[OK] Moran/LISA V17 gerado.")
    except Exception as e:
        (OUT / "moran_error_v17.txt").write_text(str(e), encoding="utf-8")
        pd.DataFrame([{"indicador":"score_risco","moran_i":np.nan,"p_value":np.nan,"interpretacao":f"Autocorrelação indisponível: {e}"}]).to_csv(OUT / "moran_global_v17.csv", index=False, encoding="utf-8-sig")
        print("[AVISO] Moran indisponível:", e)

if __name__ == "__main__":
    main()
