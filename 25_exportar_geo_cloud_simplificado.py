# -*- coding: utf-8 -*-
"""Gera malha municipal simplificada (GeoJSON) para Streamlit Cloud."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from meningites_v17_common import ROOT, find_file

DEST_DIR = ROOT / "demo_cloud" / "geo"
DEST = DEST_DIR / "MT_Municipios_simplificado.geojson"
TOLERANCE = 0.008  # graus ~ ~800m — leve o bastante para Cloud


def main() -> int:
    try:
        import geopandas as gpd
    except Exception as e:
        print(f"[AVISO] geopandas indisponível: {e}")
        return 1

    shp = find_file(["MT_Municipios_2024.shp", "*.shp"])
    if shp is None:
        print("[AVISO] Shapefile não encontrado.")
        return 1

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx"]:
            src = shp.with_suffix(ext)
            if src.exists():
                shutil.copy2(src, td / src.name)
        gdf = gpd.read_file(td / f"{shp.stem}.shp")

    code_col = next(
        (
            c
            for c in gdf.columns
            if str(c).upper() in {"CD_MUN", "COD_MUN", "GEOCODIGO", "CD_GEOCMU"}
            or "CD_MUN" in str(c).upper()
        ),
        None,
    )
    if code_col is None:
        print(f"[ERRO] Sem coluna de código. Colunas: {list(gdf.columns)}")
        return 1

    name_col = next(
        (c for c in gdf.columns if str(c).upper() in {"NM_MUN", "NM_MUNICIP", "NOME", "MUNICIPIO"}),
        None,
    )
    out = gdf[[code_col, "geometry"]].copy()
    if name_col:
        out["municipio_v17"] = gdf[name_col].astype(str)
    out["codigo_municipio_v17"] = (
        out[code_col].astype(str).str.replace(r"\D", "", regex=True).str[:6]
    )
    out = out.drop(columns=[code_col])
    if out.crs is not None:
        out = out.to_crs(epsg=4326)
    out["geometry"] = out.geometry.simplify(TOLERANCE, preserve_topology=True)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    # GeoJSON compacto
    geo = json.loads(out.to_json())
    DEST.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = DEST.stat().st_size / 1024
    print(f"[OK] {DEST.name}: {len(out)} municípios · {size_kb:.0f} KB → {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
