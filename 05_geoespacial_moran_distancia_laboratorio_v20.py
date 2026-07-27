# -*- coding: utf-8 -*-
"""
05_geoespacial_moran_distancia_laboratorio_v20.py
Corrige merge de códigos municipais, calcula Moran/LISA e adiciona distância de Cuiabá x uso do laboratório.
"""

import math
import numpy as np
import pandas as pd
from meningites_v17_common import *

RESULT_COLS = [
    "ResultadoCulturaLiquor",
    "ResultadoCulturaPetequias",
    "ResultadoCulturaSangueSoro",
    "ResultadoCulturaEscarro",
    "ResultadoBacterioscopiaLiquor",
    "ResultadoBacterioscopiaPetequias",
    "ResultadoBacterioscopiaSangueSoro",
    "ResultadoBacterioscopiaEscarro",
    "ResultadoCIELiquor",
    "ResultadoCIESangueSoro",
    "ResultadoAglutinacaoLatexLiquor",
    "ResultadoAglutinacaoLatexSangueSoro",
    "ResultadoIsolamentoViralLiquor",
    "ResultadoIsolamentoViralFezes",
    "ResultadoPCRLiquor",
    "ResultadoPCRPetequias",
    "ResultadoPCRSangueSoro",
    "ResultadoPCREscarro",
]

def lab_code(x):
    if pd.isna(x):
        return np.nan
    raw = str(x).strip()
    if raw == "" or raw.lower() in MISSING:
        return np.nan
    s = text_key(raw)
    if s.startswith("1"):
        return 1
    if s.startswith("2"):
        return 0
    if s.startswith("3"):
        return 2
    if s.startswith("4") or s.startswith("9"):
        return np.nan
    if any(t in s for t in ["POSITIVO", "REAGENTE", "DETECTADO", "ISOLADO", "IDENTIFICADO"]):
        return 1
    if any(t in s for t in ["NEGATIVO", "NAO REAGENTE", "NAO DETECTADO", "AUSENTE"]):
        return 0
    if any(t in s for t in ["INCONCLUSIVO", "INDETERMINADO", "INVALIDO"]):
        return 2
    return np.nan

def haversine(lat1, lon1, lat2=-15.601, lon2=-56.097):
    try:
        lat1, lon1 = float(lat1), float(lon1)
    except Exception:
        return np.nan
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def norm_coord_value(x, kind):
    """
    Normaliza coordenadas de MT em graus decimais.
    Corrige casos como -155555, -15555, -56.097, -560970 etc.
    """
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", ".").replace(" ", "")
    v = pd.to_numeric(s, errors="coerce")
    if pd.isna(v):
        return np.nan
    limit = 90 if kind == "lat" else 180
    candidates = [float(v)]
    for div in [10, 100, 1000, 10000, 100000, 1000000]:
        candidates.append(float(v) / div)
    valid = [c for c in candidates if abs(c) <= limit]
    if not valid:
        return np.nan
    if kind == "lat":
        mt = [c for c in valid if -19 <= c <= -7]
    else:
        mt = [c for c in valid if -63 <= c <= -50]
    if mt:
        return mt[0]
    return valid[0]

def load_latlong():
    hits = list(ROOT.glob("Municipios MT lat long*.csv")) + list(ROOT.glob("*lat*long*.csv")) + list(ROOT.glob("geo_social*.csv"))
    if not hits:
        return pd.DataFrame()
    p = hits[0]
    d = read_csv_smart(p)
    d.columns = [strip_accents(c).strip().lower().replace(" ", "_") for c in d.columns]
    mcol = next((c for c in d.columns if "municipio" in c), None)
    latcol = next((c for c in d.columns if c.startswith("lat")), None)
    loncol = next((c for c in d.columns if c.startswith("lon")), None)
    code_col = next((c for c in d.columns if "ibge" in c or "codigo" in c or c in {"cod", "cod_ibge_6", "cod_ibge_7"}), None)
    if not all([mcol, latcol, loncol]):
        return pd.DataFrame()

    out = pd.DataFrame({
        "municipio_v17": d[mcol].astype(str).str.strip(),
        "municipio_key_v17": d[mcol].map(text_key),
        "lat": d[latcol].map(lambda z: norm_coord_value(z, "lat")),
        "lon": d[loncol].map(lambda z: norm_coord_value(z, "lon")),
    })
    if code_col:
        out["codigo_municipio_v17"] = d[code_col].map(norm_code6).astype("string")
    return out.dropna(subset=["lat", "lon"])

def main():
    df = load_base_v17().copy()
    ind_path = OUT / "indicadores_municipio_ano_v17.csv"
    ind = pd.read_csv(ind_path, encoding="utf-8-sig", low_memory=False) if ind_path.exists() else pd.DataFrame()
    if ind.empty:
        print("[AVISO] Indicadores municipais ausentes.")
        return

    ind["codigo_municipio_v17"] = ind["codigo_municipio_v17"].map(norm_code6).astype("string")
    latest = pd.to_numeric(ind["ano_evento_v17"], errors="coerce").max()
    d = ind[pd.to_numeric(ind["ano_evento_v17"], errors="coerce").eq(latest)].copy()
    d["score_risco"] = (
        pd.to_numeric(d["incidencia_100mil"], errors="coerce").fillna(0).rank(pct=True)
        + pd.to_numeric(d["mortalidade_100mil"], errors="coerce").fillna(0).rank(pct=True)
        + pd.to_numeric(d["letalidade_confirmados"], errors="coerce").fillna(0).rank(pct=True)
    )
    d.to_csv(OUT / "ranking_risco_territorial_v17.csv", index=False, encoding="utf-8-sig")

    # Distância Cuiabá x laboratório
    df["codigo_municipio_v17"] = df["codigo_municipio_v17"].map(norm_code6).astype("string")
    valid_cols = [c for c in RESULT_COLS if c in df.columns]
    any_pos = pd.Series(False, index=df.index)
    any_conc = pd.Series(False, index=df.index)
    any_valid = pd.Series(False, index=df.index)
    for col in valid_cols:
        parsed = df[col].map(lab_code)
        any_pos = any_pos | (parsed == 1)
        any_conc = any_conc | parsed.isin([0, 1])
        any_valid = any_valid | parsed.isin([0, 1, 2])
    df["lab_resultado_valido_v20"] = any_valid.astype(int)
    df["lab_resultado_concludente_v20"] = any_conc.astype(int)
    df["lab_positivo_v20"] = any_pos.astype(int)
    munlab = df.groupby(["codigo_municipio_v17", "municipio_v17", "regional_v17"], dropna=False).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        com_resultado_laboratorial=("lab_resultado_valido_v20", "sum"),
        com_resultado_concludente=("lab_resultado_concludente_v20", "sum"),
        positivos_laboratoriais=("lab_positivo_v20", "sum"),
    ).reset_index()
    munlab["taxa_uso_laboratorio_pct"] = munlab["com_resultado_laboratorial"] / munlab["casos"].replace(0, np.nan) * 100
    munlab["taxa_positividade_real_pct"] = munlab["positivos_laboratoriais"] / munlab["com_resultado_concludente"].replace(0, np.nan) * 100

    lat = load_latlong()
    if not lat.empty:
        lat["codigo_municipio_v17"] = lat.get("codigo_municipio_v17", pd.Series(index=lat.index, dtype=object)).map(norm_code6).astype("string")
        if lat["codigo_municipio_v17"].notna().any():
            munlab = munlab.merge(lat[["codigo_municipio_v17", "lat", "lon"]].drop_duplicates("codigo_municipio_v17"), on="codigo_municipio_v17", how="left")
        else:
            munlab["municipio_key_v17"] = munlab["municipio_v17"].map(text_key)
            munlab = munlab.merge(lat[["municipio_key_v17", "lat", "lon"]].drop_duplicates("municipio_key_v17"), on="municipio_key_v17", how="left")
    munlab["distancia_cuiaba_km"] = [haversine(a, b) for a, b in zip(munlab.get("lat", np.nan), munlab.get("lon", np.nan))]
    munlab.loc[(munlab["distancia_cuiaba_km"] < 0) | (munlab["distancia_cuiaba_km"] > 2000), "distancia_cuiaba_km"] = np.nan
    munlab.to_csv(OUT / "geoespacial_laboratorio_distancia_v20.csv", index=False, encoding="utf-8-sig")

    corr_rows = []
    for metric in ["taxa_uso_laboratorio_pct", "taxa_positividade_real_pct", "casos", "incidencia_100mil"]:
        merged_metric = munlab.copy()
        if metric == "incidencia_100mil":
            merged_metric = merged_metric.merge(d[["codigo_municipio_v17", "incidencia_100mil"]], on="codigo_municipio_v17", how="left")
        if metric in merged_metric.columns:
            x = pd.to_numeric(merged_metric["distancia_cuiaba_km"], errors="coerce")
            y = pd.to_numeric(merged_metric[metric], errors="coerce")
            ok = x.notna() & y.notna()
            corr_rows.append({
                "variavel": metric,
                "n": int(ok.sum()),
                "pearson_distancia": x[ok].corr(y[ok], method="pearson") if ok.sum() >= 3 else np.nan,
                "spearman_distancia": x[ok].corr(y[ok], method="spearman") if ok.sum() >= 3 else np.nan,
                "interpretacao": "Correlação exploratória entre distância de Cuiabá e indicador; não implica causalidade."
            })
    pd.DataFrame(corr_rows).to_csv(OUT / "correlacao_distancia_laboratorio_v20.csv", index=False, encoding="utf-8-sig")

    # Moran/LISA robusto
    shp = find_file(["MT_Municipios_2024*.shp", "MT_Municipios_2024.shp", "*.shp"])
    if shp is None:
        (OUT / "moran_error_v17.txt").write_text("Shapefile não encontrado.", encoding="utf-8")
        pd.DataFrame([{"indicador": "score_risco", "moran_i": np.nan, "p_value": np.nan, "interpretacao": "Shapefile não encontrado."}]).to_csv(OUT / "moran_global_v17.csv", index=False, encoding="utf-8-sig")
        return

    try:
        import geopandas as gpd
        from libpysal.weights import Queen
        from esda.moran import Moran, Moran_Local

        gdf = gpd.read_file(shp)
        code_col = next((c for c in gdf.columns if "CD_MUN" in c.upper() or "GEOCOD" in c.upper() or "COD" in c.upper()), None)
        if code_col is None:
            raise ValueError("Não encontrei coluna de código municipal no shapefile.")
        gdf["codigo_municipio_v17"] = gdf[code_col].map(norm_code6).astype("string")
        d["codigo_municipio_v17"] = d["codigo_municipio_v17"].map(norm_code6).astype("string")

        merged = gdf.merge(d, on="codigo_municipio_v17", how="left")
        merged["score_risco"] = pd.to_numeric(merged["score_risco"], errors="coerce").fillna(0)

        w = Queen.from_dataframe(merged)
        w.transform = "r"
        y = merged["score_risco"].values
        mi = Moran(y, w, permutations=999)
        pd.DataFrame([{
            "indicador": "score_risco",
            "moran_i": mi.I,
            "p_value": mi.p_sim,
            "interpretacao": "Autocorrelação espacial significativa." if mi.p_sim < 0.05 else "Sem evidência robusta de autocorrelação espacial."
        }]).to_csv(OUT / "moran_global_v17.csv", index=False, encoding="utf-8-sig")

        lm = Moran_Local(y, w, permutations=999)
        merged["lisa_i"] = lm.Is
        merged["lisa_p"] = lm.p_sim
        merged["lisa_q"] = lm.q
        qmap = {1: "Alto-Alto", 2: "Baixo-Alto", 3: "Baixo-Baixo", 4: "Alto-Baixo"}
        merged["cluster_lisa"] = merged["lisa_q"].map(qmap)
        merged.loc[merged["lisa_p"] >= 0.05, "cluster_lisa"] = "Não significativo"
        keep = [c for c in ["codigo_municipio_v17", "municipio_v17", "regional_v17", "score_risco", "lisa_i", "lisa_p", "cluster_lisa"] if c in merged.columns]
        merged[keep].to_csv(OUT / "lisa_clusters_v17.csv", index=False, encoding="utf-8-sig")
        try:
            merged.to_file(OUT / "mapas_geoespaciais_v17.gpkg", driver="GPKG")
        except Exception as e:
            (OUT / "gpkg_error_v17.txt").write_text(str(e), encoding="utf-8")
        print("[OK] Geoespacial V20 gerado.")
    except Exception as e:
        (OUT / "moran_error_v17.txt").write_text(str(e), encoding="utf-8")
        pd.DataFrame([{"indicador": "score_risco", "moran_i": np.nan, "p_value": np.nan, "interpretacao": f"Autocorrelação indisponível: {e}"}]).to_csv(OUT / "moran_global_v17.csv", index=False, encoding="utf-8-sig")
        print("[AVISO] Moran indisponível:", e)

if __name__ == "__main__":
    main()
