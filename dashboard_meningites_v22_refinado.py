# -*- coding: utf-8 -*-
"""
dashboard_meningites_v18_refinado.py
Dashboard V22 com alertas estatísticos, séries separadas, OR fixo à direita e distância geográfica corrigida.
"""

from pathlib import Path
import uuid
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from meningites_v17_common import *

st.set_page_config(
    page_title="Meningites CIEVS-MT",
    layout="wide",
    initial_sidebar_state="expanded",
)


def uid():
    return uuid.uuid4().hex


@st.cache_data(show_spinner=False)
def read_any(path):
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(p, encoding=enc, low_memory=False)
        except Exception:
            pass
    return pd.read_csv(p, low_memory=False)


@st.cache_data(show_spinner=False)
def load_base():
    p = OUT / "base_unica_meningites_v17.csv"
    if not p.exists():
        return pd.DataFrame()
    d = read_any(p)
    for c in ["data_ref_v17", "data_notificacao_v17", "data_puncao_lombar_v17", "data_encerramento_v17"]:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce")
    for c in ["ano_evento_v17", "semana_epi_v17", "ano_epi_v17", "confirmado_v17", "obito_meningite_v17", "hospitalizacao_v17", "alta_v17", "caso_v17"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    if "SeNMeningiditisEspecificarSorogrupo" not in d.columns:
        d["SeNMeningiditisEspecificarSorogrupo"] = "Ignorado/sem informação"
    d["sorogrupo_v18"] = d["SeNMeningiditisEspecificarSorogrupo"].fillna("Ignorado/sem informação").astype(str).str.strip().replace({"": "Ignorado/sem informação"})
    return d


@st.cache_data(show_spinner=False)
def load_latlong():
    hits = list(ROOT.glob("Municipios MT lat long*.csv")) + list(ROOT.glob("*lat*long*.csv")) + list(ROOT.glob("geo_social*.csv"))
    if not hits:
        return pd.DataFrame()
    p = hits[0]
    d = pd.DataFrame()
    for sep in [";", ","]:
        for enc in ["utf-8-sig", "latin1", "cp1252"]:
            try:
                d = pd.read_csv(p, sep=sep, encoding=enc, low_memory=False)
                if d.shape[1] >= 4:
                    break
            except Exception:
                d = pd.DataFrame()
        if not d.empty and d.shape[1] >= 4:
            break
    if d.empty:
        return d
    d.columns = [strip_accents(c).strip().lower().replace(" ", "_") for c in d.columns]
    mcol = next((c for c in d.columns if "municipio" in c), None)
    latcol = next((c for c in d.columns if c.startswith("lat")), None)
    loncol = next((c for c in d.columns if c.startswith("lon")), None)
    code_col = next((c for c in d.columns if "ibge" in c or "codigo" in c or c == "cod"), None)
    if not all([mcol, latcol, loncol]):
        return pd.DataFrame()

    def coord(x, kind):
        return norm_coord_value(x, kind)

    out = pd.DataFrame({
        "municipio_v17": d[mcol].astype(str),
        "municipio_key_v17": d[mcol].map(text_key),
        "lat": d[latcol].map(lambda x: coord(x, "lat")),
        "lon": d[loncol].map(lambda x: coord(x, "lon")),
    })
    if code_col is not None:
        out["codigo_municipio_v17"] = d[code_col].astype(str).str.extract(r"(\d{6})", expand=False)
    return out.dropna(subset=["lat", "lon"])


@st.cache_data(show_spinner="Carregando malha municipal (shapefile)…")
def load_shapefile():
    """Carrega MT_Municipios_2024 (ou *.shp) via cópia local — OneDrive trava leitura direta."""
    import json
    import shutil
    import tempfile
    import os

    shp = find_file(["MT_Municipios_2024.shp", "*.shp"])
    gpkg = ROOT / "saida_meningites_v17" / "mapas_geoespaciais_v17.gpkg"
    cache_dir = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "meningites_cievs_mt" / "geo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_pq = cache_dir / "MT_Municipios_2024_v23.parquet"
    cache_meta = cache_dir / "MT_Municipios_2024_v23.meta.json"

    try:
        import geopandas as gpd
    except Exception as e:
        st.warning(f"GeoPandas indisponível — mapas usarão pontos. ({e})")
        return None

    last_err = None

    def _norm_codes(gdf):
        code_col = next(
            (c for c in gdf.columns if str(c).upper() in {"CD_MUN", "COD_MUN", "GEOCODIGO", "CD_GEOCMU"}
             or "CD_MUN" in str(c).upper() or "GEOCOD" in str(c).upper()),
            None,
        )
        if code_col is None:
            code_col = next((c for c in gdf.columns if "COD" in str(c).upper() and "UF" not in str(c).upper()), None)
        if code_col is None:
            raise ValueError(f"Coluna de código municipal não encontrada. Colunas: {list(gdf.columns)}")
        gdf = gdf.copy()
        gdf["codigo_municipio_v17"] = (
            gdf[code_col].astype(str).str.replace(r"\D", "", regex=True).str[:6]
        )
        name_col = next((c for c in gdf.columns if str(c).upper() in {"NM_MUN", "NM_MUNICIP", "NOME", "MUNICIPIO"}), None)
        if name_col and "municipio_v17" not in gdf.columns:
            gdf["municipio_v17"] = gdf[name_col].astype(str)
        # simplifica geometria para o Plotly ficar responsivo
        try:
            gdf["geometry"] = gdf.geometry.simplify(0.005, preserve_topology=True)
        except Exception:
            pass
        if gdf.crs is not None:
            try:
                gdf = gdf.to_crs(epsg=4326)
            except Exception:
                pass
        return gdf

    # 0) GeoJSON simplificado (Cloud / demo)
    geojson_candidates = [
        ROOT / "demo_cloud" / "geo" / "MT_Municipios_simplificado.geojson",
        ROOT / "geo" / "MT_Municipios_simplificado.geojson",
    ]
    for gj in geojson_candidates:
        if not gj.exists():
            continue
        try:
            gdf = gpd.read_file(gj)
            if "codigo_municipio_v17" in gdf.columns and len(gdf) > 0:
                return gdf
            gdf = _norm_codes(gdf)
            return gdf
        except Exception as e:
            last_err = e

    # 1) cache parquet local (rápido)
    try:
        if cache_pq.exists():
            gdf = gpd.read_parquet(cache_pq)
            if "codigo_municipio_v17" in gdf.columns and len(gdf) > 0:
                return gdf
    except Exception:
        pass

    # 2) shapefile oficial (via TEMP — evita lock OneDrive)
    if shp is not None:
        try:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                stem = shp.stem
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx"]:
                    src = shp.with_suffix(ext)
                    if src.exists():
                        shutil.copy2(src, td / src.name)
                gdf = gpd.read_file(td / f"{stem}.shp")
                gdf = _norm_codes(gdf)
                try:
                    gdf.to_parquet(cache_pq, index=False)
                    cache_meta.write_text(
                        json.dumps({"fonte": str(shp), "n": len(gdf)}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                return gdf
        except Exception as e:
            last_err = e

    # 3) fallback GPKG gerado pelo pipeline
    if gpkg.exists():
        try:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                local = td / gpkg.name
                shutil.copy2(gpkg, local)
                gdf = gpd.read_file(local)
                gdf = _norm_codes(gdf)
                try:
                    gdf.to_parquet(cache_pq, index=False)
                except Exception:
                    pass
                return gdf
        except Exception as e:
            last_err = e

    st.warning(
        "Não foi possível carregar o shapefile municipal "
        f"(`MT_Municipios_2024.shp`). Mapas em modo pontos. Detalhe: {last_err}"
    )
    return None


def choropleth_or_points(ind, shapefile, latlon, metric, title):
    """Prioriza coroplético com shapefile; pontos só se a malha falhar.

    Sempre desenha TODOS os municípios da malha: quem não tem dado fica com 0
    (cor mais clara da escala), para não deixar buracos no mapa.
    """
    d = ind.copy()
    if "codigo_municipio_v17" not in d.columns:
        st.info(f"Mapa indisponível: {title}")
        return
    d["codigo_municipio_v17"] = (
        d["codigo_municipio_v17"].astype(str).str.replace(r"\D", "", regex=True).str[:6]
    )
    # agrega por município caso o indicador venha com linhas duplicadas
    value_cols = [
        c for c in [
            metric, "casos", "confirmados", "obitos_meningite", "hospitalizacoes",
            "incidencia_100mil", "mortalidade_100mil", "letalidade_confirmados", "score_risco",
        ]
        if c in d.columns
    ]
    for col in value_cols:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    name_col = "municipio_v17" if "municipio_v17" in d.columns else None
    if value_cols:
        agg = {c: "sum" for c in value_cols}
        # taxas/score: média se houver duplicata; contagens: soma
        for c in list(agg):
            if any(k in c for k in ("incidencia", "mortalidade", "letalidade", "score", "taxa", "pct")):
                agg[c] = "mean"
        if name_col:
            agg[name_col] = "first"
        d = d.groupby("codigo_municipio_v17", as_index=False).agg(agg)

    if shapefile is not None:
        try:
            g = shapefile.merge(d, on="codigo_municipio_v17", how="left", suffixes=("", "_dado"))
            if "municipio_v17" not in g.columns or g["municipio_v17"].isna().all():
                if "NM_MUN" in g.columns:
                    g["municipio_v17"] = g["NM_MUN"].astype(str)
                elif "municipio_v17_dado" in g.columns:
                    g["municipio_v17"] = g["municipio_v17_dado"]
            if "NM_MUN" in g.columns:
                g["municipio_v17"] = g["municipio_v17"].fillna(g["NM_MUN"]).astype(str)
            else:
                g["municipio_v17"] = g["municipio_v17"].fillna("").astype(str)
            # garante colunas e preenche NaN com 0 → todos os polígonos coloridos
            fill_cols = [
                metric, "casos", "confirmados", "obitos_meningite", "hospitalizacoes",
                "incidencia_100mil", "mortalidade_100mil", "letalidade_confirmados", "score_risco",
            ]
            for col in fill_cols:
                if col not in g.columns:
                    g[col] = 0.0
                else:
                    g[col] = pd.to_numeric(g[col], errors="coerce").fillna(0.0)
            g = g.reset_index(drop=True)
            g["_map_id"] = g.index.astype(str)
            zmax = float(pd.to_numeric(g[metric], errors="coerce").max() or 0)
            if zmax <= 0:
                zmax = 1.0
            geojson = __import__("json").loads(g.to_json())
            hover = {
                metric: ":.2f",
                "casos": ":.0f",
                "confirmados": ":.0f",
                "obitos_meningite": ":.0f",
                "_map_id": False,
            }
            plot_df = g.drop(columns=["geometry"], errors="ignore")
            fig = px.choropleth_mapbox(
                plot_df,
                geojson=geojson,
                locations="_map_id",
                featureidkey="properties._map_id",
                color=metric,
                hover_name="municipio_v17",
                hover_data=hover,
                color_continuous_scale="YlOrRd",
                range_color=(0, zmax),
                mapbox_style="carto-positron",
                center={"lat": -12.8, "lon": -55.8},
                zoom=4.5,
                opacity=0.85,
                height=560,
                title=title + " (shapefile municipal)",
            )
            fig.update_traces(
                marker_line_width=0.35,
                marker_line_color="#6b7280",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.caption(f"{len(g)} municípios na malha · valor 0 = sem registro no filtro (cor mais clara).")
            st.plotly_chart(fig, use_container_width=True, key=uid())
            return
        except Exception as e:
            st.warning(f"Falha no coroplético com shapefile ({title}): {e}. Tentando pontos…")

    if latlon.empty:
        st.info(f"Mapa indisponível (sem shapefile/coordenadas): {title}")
        return
    d["municipio_key_v17"] = d.get("municipio_v17", pd.Series(index=d.index)).map(text_key)
    d = d.merge(latlon[["municipio_key_v17", "lat", "lon"]], on="municipio_key_v17", how="left").dropna(subset=["lat", "lon"])
    if d.empty:
        st.info(f"Sem coordenadas disponíveis: {title}")
        return
    fig = px.scatter_mapbox(
        d,
        lat="lat",
        lon="lon",
        size=np.maximum(pd.to_numeric(d.get("casos"), errors="coerce").fillna(1), 1),
        color=metric,
        hover_name="municipio_v17",
        hover_data={"casos": True, "confirmados": True, "obitos_meningite": True},
        zoom=4.5,
        height=560,
        color_continuous_scale="YlOrRd",
        title=title + " (pontos — fallback)",
    )
    fig.update_layout(mapbox_style="carto-positron")
    st.plotly_chart(fig, use_container_width=True, key=uid())


def fmt(x, nd=1):
    try:
        if pd.isna(x):
            return "NA"
        if nd == 0:
            return f"{int(round(float(x))):,}".replace(",", ".")
        return f"{float(x):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)



def norm_coord_value(x, kind):
    """Normaliza coordenadas em graus decimais e corrige formatos escalados."""
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

    # Mato Grosso: lat aprox -17 a -7; lon aprox -62 a -50.
    if kind == "lat":
        mt = [c for c in valid if -19 <= c <= -7]
    else:
        mt = [c for c in valid if -63 <= c <= -50]
    if mt:
        return mt[0]
    return valid[0]


def significant_alerts_from_frames(frames, threshold=0.005, title="Achados estatisticamente significativos"):
    """
    Destaca achados p<threshold. Usado em múltiplas abas.
    frames = lista de tuplas (nome, dataframe).
    """
    rows = []
    for nome, df0 in frames:
        if df0 is None or df0.empty or "p_value" not in df0.columns:
            continue
        d = df0.copy()
        d["p_value"] = pd.to_numeric(d["p_value"], errors="coerce")
        d = d[d["p_value"].notna() & (d["p_value"] < threshold)].copy()
        if d.empty:
            continue
        for _, r in d.head(20).iterrows():
            label_parts = []
            for c in ["variavel", "exposicao", "classificacao_agrupada", "desfecho", "variavel_grupo", "desfecho_comparado"]:
                if c in d.columns and pd.notna(r.get(c)):
                    label_parts.append(str(r.get(c)))
            rows.append({
                "origem": nome,
                "achado": " | ".join(label_parts)[:180] if label_parts else nome,
                "p_value": r.get("p_value", np.nan),
                "or": r.get("or", np.nan),
                "ic95": f"{fmt(r.get('ic95_inferior', np.nan),2)}–{fmt(r.get('ic95_superior', np.nan),2)}" if "ic95_inferior" in d.columns else "",
                "interpretacao": r.get("interpretacao_estatistica", r.get("interpretacao", "")),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        st.caption(f"Sem achados com p < {threshold} nesta seleção.")
        return
    st.warning(f"{title}: {len(out)} achado(s) com p < {threshold}.")
    st.dataframe(out.sort_values("p_value"), use_container_width=True)

def inject_ui_css():
    """Visual / UX: tipografia, contraste, deltas e abas legíveis."""
    st.markdown(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700;800&display=swap');
  html, body, [class*="css"]  { font-family: 'Source Sans 3', 'Segoe UI', sans-serif; }
  .stApp { background: linear-gradient(165deg, #e8f2ec 0%, #f7faf8 180px, #ffffff 420px); }
  h1 { letter-spacing: -0.03em !important; color: #0a3326 !important; font-weight: 800 !important; }
  h2, h3 { color: #12352a !important; font-weight: 700 !important; }
  div[data-testid="stTabs"] button[role="tab"] {
    font-size: 0.9rem !important;
    white-space: nowrap !important;
    font-weight: 600 !important;
  }
  div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.2rem;
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    border-bottom: 2px solid #d7e5dd;
    padding-bottom: 2px;
  }
  div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #0b6e4f !important;
    border-bottom: 3px solid #0b6e4f !important;
  }
  .hero-band {
    background: linear-gradient(120deg, #0b6e4f 0%, #147a5a 45%, #1a8f6a 100%);
    color: #fff;
    border-radius: 16px;
    padding: 16px 20px;
    margin: 0 0 16px 0;
    box-shadow: 0 8px 24px rgba(11,110,79,.18);
  }
  .hero-band h1 { color: #fff !important; margin: 0 !important; font-size: 1.55rem !important; }
  .hero-band p { margin: 6px 0 0 0; opacity: .92; font-size: 0.95rem; }
  .kpi-card {
    background: #fff;
    border: 1px solid #d7e3dc;
    border-radius: 16px;
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(16,42,35,.06);
    min-height: 200px;
    transition: box-shadow .15s ease;
  }
  .kpi-label { font-size: 0.95rem; font-weight: 700; color: #374151; }
  .kpi-value { font-size: 2.05rem; font-weight: 800; color: #111827; line-height: 1.15; }
  .kpi-sub { font-size: 0.78rem; color: #6b7280; margin-top: 2px; }
  .kpi-line { font-size: 0.86rem; color: #374151; margin-top: 8px; }
  .kpi-delta { font-size: 1.15rem; font-weight: 800; margin-top: 8px; }
  .section-card {
    background: #fff;
    border: 1px solid #e5ebe7;
    border-left: 4px solid #0b6e4f;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(16,42,35,.04);
  }
  .guide-card {
    background: linear-gradient(135deg, #f0faf5 0%, #ffffff 70%);
    border: 1px solid #cfe3d7;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }
  .ai-box {
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 14px;
    padding: 16px 18px;
    margin-top: 10px;
    line-height: 1.55;
  }
  .ai-box strong { color: #6ee7b7; }
  div[data-testid="stMetricDelta"] svg { display: none !important; }
  div[data-testid="stMetricDelta"] { font-weight: 700 !important; }
  .block-container { padding-top: 1rem !important; max-width: 1420px; }
  [data-testid="stSidebar"] { background: #f3f8f5; }
</style>
        """,
        unsafe_allow_html=True,
    )


def trend_arrow_color(delta, *, higher_is_bad=True):
    """
    Seta segue a tendência (▲ aumento / ▼ queda).
    Cor epidemiológica padrão: aumento = vermelho, queda = verde.
    """
    if pd.isna(delta):
        return "→", "#6b7280"
    try:
        d = float(delta)
    except Exception:
        return "→", "#6b7280"
    if abs(d) < 1e-12:
        return "●", "#d97706"
    if d > 0:
        return "▲", ("#dc2626" if higher_is_bad else "#16a34a")
    return "▼", ("#16a34a" if higher_is_bad else "#dc2626")


def arrow_html(var):
    return trend_arrow_color(var, higher_is_bad=True)


SEMAFORO_COLORS = {
    "Verde": "#16a34a",
    "verde": "#16a34a",
    "Vermelho": "#dc2626",
    "vermelho": "#dc2626",
    "Amarelo": "#ca8a04",
    "amarelo": "#ca8a04",
    "Atenção": "#ca8a04",
    "Atencao": "#ca8a04",
    "Alto": "#ea580c",
    "Crítico": "#b91c1c",
    "Critico": "#b91c1c",
    "Rotina": "#64748b",
}


def semaforo_color(txt):
    s = str(txt or "").strip()
    if s in SEMAFORO_COLORS:
        return SEMAFORO_COLORS[s]
    low = s.lower()
    if "verde" in low:
        return "#16a34a"
    if "vermel" in low or "crít" in low or "crit" in low:
        return "#dc2626"
    if "amarelo" in low or "aten" in low:
        return "#ca8a04"
    if "alto" in low:
        return "#ea580c"
    return "#6b7280"


def semaforo_badge(txt):
    """Badge colorido — fonte/fundo seguem Verde/Vermelho/Amarelo (visível no Streamlit)."""
    label = str(txt or "—")
    c = semaforo_color(label)
    return (
        f'<span style="display:inline-block;background:{c};color:#ffffff !important;'
        f'padding:4px 12px;border-radius:999px;font-weight:800;font-size:0.9rem;'
        f'letter-spacing:0.02em;">{label}</span>'
    )


def plotly_semaforo_map(series=None):
    """Mapa de cores Plotly para coluna semaforo / classe_alerta."""
    base = {
        "Verde": "#16a34a",
        "Vermelho": "#dc2626",
        "Amarelo": "#eab308",
        "Atenção": "#eab308",
        "Alto": "#ea580c",
        "Crítico": "#b91c1c",
        "Rotina": "#94a3b8",
    }
    if series is not None:
        for v in pd.Series(series).dropna().astype(str).unique():
            if v not in base:
                base[v] = semaforo_color(v)
    return base


def kpi_delta_html(delta_pct, suffix="%", higher_is_bad=True):
    arrow, color = trend_arrow_color(delta_pct, higher_is_bad=higher_is_bad)
    if pd.isna(delta_pct):
        return f'<div class="kpi-delta" style="color:{color};">{arrow} NA</div>'
    return (
        f'<div class="kpi-delta" style="color:{color} !important;">'
        f"{arrow} {fmt(delta_pct, 1)}{suffix}</div>"
    )


def weekly_current_previous(df):
    needed = [c for c in ["ano_epi_v17","semana_epi_v17","caso_v17","confirmado_v17","hospitalizacao_v17","obito_meningite_v17","alta_v17"] if c in df.columns]
    if len(needed) < 3:
        return pd.DataFrame(), None, None
    w = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos=("obito_meningite_v17", "sum"),
        altas=("alta_v17", "sum"),
    ).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])
    if w.empty:
        return pd.DataFrame(), None, None
    cur = w.iloc[-1]
    prev = w.iloc[-2] if len(w) > 1 else None
    return w, cur, prev


def build_metric_cards(df):
    """
    KPI principal = total real do período selecionado.
    Abaixo: última semana, semana anterior e variação % com seta/cor coerentes.
    """
    if df.empty:
        st.info("Sem dados no período selecionado.")
        return

    totals = {
        "Casos": ("caso_v17", len(df)),
        "Confirmados": ("confirmado_v17", pd.to_numeric(df.get("confirmado_v17", 0), errors="coerce").sum()),
        "Hospitalizações": ("hospitalizacao_v17", pd.to_numeric(df.get("hospitalizacao_v17", 0), errors="coerce").sum()),
        "Óbitos": ("obito_meningite_v17", pd.to_numeric(df.get("obito_meningite_v17", 0), errors="coerce").sum()),
        "Altas": ("alta_v17", pd.to_numeric(df.get("alta_v17", 0), errors="coerce").sum()),
    }

    weekly = pd.DataFrame()
    if {"ano_epi_v17", "semana_epi_v17"}.issubset(df.columns):
        weekly = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(
            casos=("caso_v17", "sum"),
            confirmados=("confirmado_v17", "sum"),
            hospitalizacoes=("hospitalizacao_v17", "sum"),
            obitos=("obito_meningite_v17", "sum"),
            altas=("alta_v17", "sum"),
        ).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])

    week_map = {
        "Casos": "casos",
        "Confirmados": "confirmados",
        "Hospitalizações": "hospitalizacoes",
        "Óbitos": "obitos",
        "Altas": "altas",
    }

    cols = st.columns(len(totals))
    for colui, (label, (_, total_value)) in zip(cols, totals.items()):
        wk_col = week_map[label]
        # Altas: aumento é bom → higher_is_bad=False
        higher_is_bad = label != "Altas"
        if not weekly.empty and wk_col in weekly.columns:
            cur = weekly.iloc[-1]
            prev = weekly.iloc[-2] if len(weekly) > 1 else None
            curv = float(cur.get(wk_col, np.nan))
            prevv = float(prev.get(wk_col, np.nan)) if prev is not None else np.nan
            var = ((curv - prevv) / prevv * 100) if pd.notna(prevv) and prevv != 0 else (0 if curv == 0 else np.nan)
            semana_atual = f"SE {int(cur['semana_epi_v17'])}/{int(cur['ano_epi_v17'])}" if pd.notna(cur["semana_epi_v17"]) else "Última semana"
        else:
            curv = prevv = var = np.nan
            semana_atual = "Última semana"

        colui.markdown(
            f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{fmt(total_value, 0)}</div>
          <div class="kpi-sub">Total do período selecionado</div>
          <div class="kpi-line">{semana_atual}: <b>{fmt(curv, 0)}</b></div>
          <div class="kpi-line">Semana anterior: <b>{fmt(prevv, 0)}</b></div>
          {kpi_delta_html(var, higher_is_bad=higher_is_bad)}
        </div>
        """,
            unsafe_allow_html=True,
        )


def bar_with_labels(df, x, y, title, color=None, height=420, orient="v"):
    fig = px.bar(df, x=x, y=y, text=x if orient == "h" else y, color=color, orientation=orient, title=title)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=height, uniformtext_minsize=10, uniformtext_mode="hide")
    st.plotly_chart(fig, use_container_width=True, key=uid())


def timeseries_cases(df):
    if not {"ano_epi_v17","semana_epi_v17","caso_v17"}.issubset(df.columns):
        st.info("Série histórica indisponível.")
        return
    s = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(casos=("caso_v17", "sum")).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])
    s["periodo"] = s["ano_epi_v17"].astype("Int64").astype(str) + "-SE" + s["semana_epi_v17"].astype("Int64").astype(str)
    fig = px.line(s, x="periodo", y="casos", markers=True, title="Série histórica de casos por semana epidemiológica")
    fig.update_traces(text=s["casos"], textposition="top center")
    fig.update_layout(height=420, xaxis_title="Período", yaxis_title="Casos")
    st.plotly_chart(fig, use_container_width=True, key=uid())


def sorogrupos_plot(df):
    if "classificacao_agrupada_v17" not in df.columns:
        st.info("Análise de sorogrupos indisponível.")
        return
    x = df[df["classificacao_agrupada_v17"].astype(str).eq("Doença meningocócica")].copy()
    if x.empty:
        st.info("Sem registros de doença meningocócica para análise de sorogrupos.")
        return
    g = x.groupby(["ano_evento_v17", "sorogrupo_v18"]).size().reset_index(name="casos")
    fig = px.line(g, x="ano_evento_v17", y="casos", color="sorogrupo_v18", markers=True, title="Doença meningocócica por ano e sorogrupo")
    fig.update_layout(height=420, xaxis_title="Ano", yaxis_title="Nº de casos")
    st.plotly_chart(fig, use_container_width=True, key=uid())


def socio_profile(df):
    vars_ = ["FaixaEtaria", "SexoPaciente", "Gestante", "RacaPaciente", "Escolaridade"]
    present = [v for v in vars_ if v in df.columns]
    if not present:
        st.info("Sem variáveis sociodemográficas disponíveis.")
        return
    cols = st.columns(2)
    for i, var in enumerate(present):
        g = df[var].fillna("Ignorado").astype(str).value_counts().reset_index()
        g.columns = [var, "n"]
        with cols[i % 2]:
            bar_with_labels(g, "n", var, f"Perfil sociodemográfico — {var}", orient="h", height=360)



def chi_square_group_section(df):
    st.subheader("Análises comparativas dos grupos — Qui-quadrado e p-valor")
    st.caption("As análises abaixo comparam os grupos do período filtrado. p<0,05 sugere associação estatisticamente significativa; Cramér's V ajuda a avaliar a relevância prática.")
    try:
        from scipy import stats
    except Exception:
        stats = None

    vars_group = [v for v in ["FaixaEtaria", "SexoPaciente", "Gestante", "RacaPaciente", "Escolaridade"] if v in df.columns]
    outcomes = [v for v in ["evolucao_padronizada_v17", "classificacao_caso_padronizada_v17", "classificacao_agrupada_v17"] if v in df.columns]
    rows = []
    for var in vars_group:
        for out in outcomes:
            d = df[[var, out]].dropna().copy()
            if len(d) < 20 or d[var].nunique() < 2 or d[out].nunique() < 2:
                continue
            tab = pd.crosstab(d[var].astype(str), d[out].astype(str))
            if tab.shape[0] < 2 or tab.shape[1] < 2:
                continue
            if stats is not None:
                try:
                    chi, p, dof, exp = stats.chi2_contingency(tab)
                    n = tab.sum().sum()
                    cramer = np.sqrt((chi / n) / max(1, min(tab.shape[0] - 1, tab.shape[1] - 1))) if n else np.nan
                except Exception:
                    chi, p, cramer = np.nan, np.nan, np.nan
            else:
                chi, p, cramer = np.nan, np.nan, np.nan
            rows.append({
                "variavel_grupo": var,
                "desfecho_comparado": out,
                "n": int(len(d)),
                "p_value": p,
                "cramers_v": cramer,
                "interpretacao": "Associação estatisticamente significativa" if pd.notna(p) and p < 0.05 else "Sem evidência estatística de associação",
                "relevancia_pratica": "fraca" if pd.notna(cramer) and cramer < 0.1 else "moderada" if pd.notna(cramer) and cramer < 0.3 else "forte" if pd.notna(cramer) else "indeterminada",
            })
    res = pd.DataFrame(rows)
    if res.empty:
        st.info("Sem volume suficiente para testes de comparação entre grupos no filtro atual.")
        return
    fig = px.bar(
        res.sort_values("p_value").head(20),
        x="cramers_v",
        y="variavel_grupo",
        color="desfecho_comparado",
        orientation="h",
        text=[f"p={p:.4f}" if pd.notna(p) else "p=NA" for p in res.sort_values("p_value").head(20)["p_value"]],
        title="Força da associação entre perfil sociodemográfico e desfechos"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=520, xaxis_title="Cramér's V", yaxis_title="Variável")
    st.plotly_chart(fig, use_container_width=True, key=uid())
    st.dataframe(res.sort_values("p_value"), use_container_width=True)


def forest_plot_or_labeled(data, title, max_items=25):
    if data.empty:
        st.info(f"Sem dados para {title}.")
        return
    d = data.copy()
    for c in ["or", "ic95_inferior", "ic95_superior", "p_value"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["or", "ic95_inferior", "ic95_superior"])
    if d.empty:
        st.info(f"Sem OR calculável para {title}.")
        return

    d = d.sort_values(["p_value", "or"], ascending=[True, False]).head(max_items).copy()
    d["rotulo"] = d["exposicao"].astype(str).str.replace("_", " ").str[:78]
    d["interpretacao"] = d.apply(_or_interpret_row, axis=1)
    d["cor"] = d["or"].apply(lambda x: "#dc2626" if x > 1 else ("#16a34a" if x < 1 else "#64748b"))
    d["texto_or"] = d.apply(
        lambda r: f"OR {fmt(r['or'],2)} | IC95% {fmt(r['ic95_inferior'],2)}–{fmt(r['ic95_superior'],2)} | p={fmt(r.get('p_value', np.nan),4)} · {r['interpretacao']}",
        axis=1,
    )
    yvals = list(range(len(d)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["or"], y=yvals, mode="markers",
        marker=dict(size=12, color=d["cor"], line=dict(width=1, color="#111827")),
        customdata=np.stack([d["rotulo"], d["desfecho"], d["p_value"], d["texto_or"], d["interpretacao"]], axis=-1),
        hovertemplate="<b>%{customdata[0]}</b><br>Desfecho: %{customdata[1]}<br>%{customdata[3]}<extra></extra>",
        name="OR",
    ))
    for yi, (_, r) in zip(yvals, d.iterrows()):
        fig.add_shape(type="line", x0=r["ic95_inferior"], x1=r["ic95_superior"], y0=yi, y1=yi,
                      line=dict(width=2.2, color=r["cor"]))
        fig.add_annotation(
            xref="paper", x=1.01, y=yi, yref="y",
            text=r["texto_or"], showarrow=False,
            xanchor="left", align="left",
            font=dict(size=10, color=r["cor"]),
        )

    fig.add_vline(x=1, line_dash="dash", line_color="#111827")
    fig.update_layout(
        title=title,
        height=max(580, 36 * len(d) + 200),
        xaxis_title="Odds Ratio (escala log) — à direita de 1 = risco; à esquerda = proteção",
        yaxis=dict(tickmode="array", tickvals=yvals, ticktext=d["rotulo"]),
        xaxis_type="log",
        margin=dict(l=300, r=520, t=70, b=50),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())
    significant_alerts_from_frames([(title, d)], threshold=0.005, title=f"Destaques de {title}")


def _or_interpret_row(r):
    orv = float(r["or"]) if pd.notna(r.get("or")) else np.nan
    lo = float(r["ic95_inferior"]) if pd.notna(r.get("ic95_inferior")) else np.nan
    hi = float(r["ic95_superior"]) if pd.notna(r.get("ic95_superior")) else np.nan
    p = float(r["p_value"]) if pd.notna(r.get("p_value")) else np.nan
    if pd.isna(orv):
        return "sem interpretação"
    # IC cruza 1 → não significativo
    if pd.notna(lo) and pd.notna(hi) and lo <= 1 <= hi:
        return "sem evidência clara (IC cruza 1)"
    if pd.notna(p) and p >= 0.05:
        return "não significativo (p≥0,05)"
    if orv > 1:
        return "fator de RISCO (aumenta chance do desfecho)"
    if orv < 1:
        return "fator de PROTEÇÃO (reduz chance do desfecho)"
    return "neutro (OR≈1)"


def or_interpretation_guide():
    st.markdown(
        """
<div class="section-card">
<b>Como ler Odds Ratio (OR) — guia rápido</b><br/>
• <span style="color:#dc2626;font-weight:700;">OR &gt; 1 (vermelho)</span>: associação com <b>maior chance</b> do desfecho → <b>risco</b>.<br/>
• <span style="color:#16a34a;font-weight:700;">OR &lt; 1 (verde)</span>: associação com <b>menor chance</b> do desfecho → <b>proteção</b>.<br/>
• <b>OR ≈ 1</b> ou IC95% que passa por 1: sem evidência clara de associação.<br/>
• <b>p &lt; 0,05</b> (ou &lt; 0,005 nos destaques): associação estatisticamente relevante, mas <i>não prova causalidade</i>.<br/>
• Use o gráfico: pontos à <b>direita</b> da linha tracejada (1) = risco; à <b>esquerda</b> = proteção.<br/>
• <b>Mortalidade:</b> desfecho padrão <b>Óbito (SINAN∪SIM)</b> = EvolucaoCaso do SINAN <i>ou</i> match no SIM (CID meningite, score≥0,75).
  Mantém-se sensibilidade <b>só SINAN</b> e <b>só SIM</b>. KPIs MS de óbito no painel epi continuam no SINAN.
</div>
        """,
        unsafe_allow_html=True,
    )


def canal_plot_visual(d, clas):
    d = d[d["classificacao_agrupada_v17"].astype(str).eq(clas)].copy().sort_values("semana_epi_v17")
    if d.empty:
        return
    upper_col = "p95" if "p95" in d.columns else "maximo"
    lower_col = "q25" if "q25" in d.columns else "minimo"
    band_col = "q75" if "q75" in d.columns else upper_col
    if not {"semana_epi_v17", "media", "observado", upper_col}.issubset(d.columns):
        return

    d["observado"] = pd.to_numeric(d["observado"], errors="coerce").fillna(0)
    d["media"] = pd.to_numeric(d["media"], errors="coerce")
    d[upper_col] = pd.to_numeric(d[upper_col], errors="coerce")
    d["status"] = np.where(d["observado"] > d[upper_col], "Acima do limite superior", "Dentro do esperado")

    fig = go.Figure()
    if lower_col in d.columns and band_col in d.columns:
        fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d[band_col], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d[lower_col], mode="lines", fill="tonexty", line=dict(width=0), name="Faixa esperada"))

    fig.add_trace(go.Bar(
        x=d["semana_epi_v17"], y=d["observado"], name="Casos observados",
        text=d["observado"].astype(int), textposition="outside",
        customdata=d[["status"]],
        hovertemplate="SE %{x}<br>Observado: %{y}<br>%{customdata[0]}<extra></extra>",
        marker=dict(opacity=0.78)
    ))
    fig.add_trace(go.Scatter(
        x=d["semana_epi_v17"], y=d["media"], mode="lines+markers",
        name="Média histórica", line=dict(width=4)
    ))
    fig.add_trace(go.Scatter(
        x=d["semana_epi_v17"], y=d[upper_col], mode="lines+markers",
        name="Limite superior", line=dict(width=4, dash="dash")
    ))

    above = d[d["observado"] > d[upper_col]]
    if not above.empty:
        fig.add_trace(go.Scatter(
            x=above["semana_epi_v17"], y=above["observado"],
            mode="markers", marker=dict(size=14, symbol="x"),
            name="Alerta: acima do limite"
        ))

    fig.update_layout(
        title=f"Canal endêmico — {clas}",
        xaxis_title="Semana epidemiológica",
        yaxis_title="Casos",
        height=660,
        bargap=0.18,
        legend=dict(orientation="h", y=-0.18, x=0.05),
        margin=dict(l=55, r=40, t=70, b=100),
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())

    if not above.empty:
        st.warning(f"{clas}: {len(above)} semana(s) acima do limite superior. Recomenda-se verificar duplicidades, confirmação laboratorial, vínculo epidemiológico e distribuição municipal.")
    else:
        st.caption(f"{clas}: sem semanas acima do limite superior no canal exibido.")


def forecast_nowcast_visual(base, fc, nowdf, desfecho):
    col_map = {"casos": "caso_v17", "hospitalizacoes": "hospitalizacao_v17", "obitos_meningite": "obito_meningite_v17"}
    hist_col = col_map.get(desfecho)
    if hist_col not in base.columns:
        st.info(f"Histórico indisponível para {desfecho}.")
        return
    hist = base.groupby("data_ref_v17").agg(valor=(hist_col, "sum")).reset_index().sort_values("data_ref_v17").tail(120)
    if hist.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["data_ref_v17"], y=hist["valor"], mode="lines", line=dict(width=3), name="Histórico ajustado"))

    # Nowcasting
    if not nowdf.empty and "desfecho" in nowdf.columns:
        nrow = nowdf[nowdf["desfecho"].astype(str).eq(desfecho)]
        if not nrow.empty:
            r = nrow.iloc[0]
            x_now = hist["data_ref_v17"].max()
            fig.add_trace(go.Scatter(
                x=[x_now], y=[r["nowcast"]], mode="markers+text",
                text=[f"Nowcast: {fmt(r['nowcast'],1)}"], textposition="top center",
                marker=dict(size=13), name="Nowcasting"
            ))

    dfc = fc[fc["desfecho"].astype(str).eq(desfecho)].copy() if not fc.empty and "desfecho" in fc.columns else pd.DataFrame()
    if not dfc.empty and "data_prevista" in dfc.columns:
        dfc["data_prevista"] = pd.to_datetime(dfc["data_prevista"], errors="coerce")
        # Preferir 30 dias para visual semelhante à referência; senão, usa o maior horizonte disponível.
        h = 30 if (dfc["horizonte_dias"].astype(str).eq("30").any() or (pd.to_numeric(dfc["horizonte_dias"], errors="coerce") == 30).any()) else pd.to_numeric(dfc["horizonte_dias"], errors="coerce").max()
        s = dfc[pd.to_numeric(dfc["horizonte_dias"], errors="coerce").eq(float(h))].copy().sort_values("data_prevista")
        if not s.empty:
            x0, x1 = s["data_prevista"].min(), s["data_prevista"].max()
            fig.add_vrect(x0=x0, x1=x1, fillcolor="red", opacity=0.07, line_width=0, annotation_text="Janela preditiva", annotation_position="top left")
            if {"lower_95", "upper_95"}.issubset(s.columns):
                fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["upper_95"], mode="lines", line=dict(width=0), showlegend=False))
                fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["lower_95"], mode="lines", fill="tonexty", line=dict(width=0), name="IC95%"))
            fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["pred"], mode="lines+markers+text", line=dict(width=3, dash="dash"), text=[fmt(v,1) for v in s["pred"]], textposition="top center", name="Previsão ensemble"))

    fig.update_layout(
        title=f"Nowcasting e forecasting — {desfecho}",
        xaxis_title="Data",
        yaxis_title="Nº de casos" if desfecho == "casos" else "Nº de eventos",
        height=620,
        legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())


def climate_correlation_visual():
    diag = OUT / "diagnostico_clima_v17.txt"
    if diag.exists():
        st.info(diag.read_text(encoding="utf-8"))
    corr = read_any(OUT / "correlacao_clima_casos_v17.csv")
    daily = read_any(OUT / "clima_casos_diario_v17.csv")
    if corr.empty:
        st.info("Correlação clima-casos indisponível.")
        return
    for c in ["spearman", "pearson", "r2", "lag_dias"]:
        if c in corr.columns:
            corr[c] = pd.to_numeric(corr[c], errors="coerce")
    corr["abs_r"] = corr["spearman"].abs() if "spearman" in corr.columns else corr.get("pearson", pd.Series(dtype=float)).abs()
    best = corr.sort_values("abs_r", ascending=False).head(6).copy()
    if not best.empty:
        st.subheader("Resumo das maiores correlações clima-casos")
        figb = px.bar(best, x="abs_r", y="variavel_climatica", color="lag_dias" if "lag_dias" in best.columns else None,
                      orientation="h", text=[f"R²={fmt(v,3)}" for v in best.get("r2", pd.Series([np.nan]*len(best)))],
                      title="Correlação absoluta e R² por variável climática")
        figb.update_traces(textposition="outside")
        figb.update_layout(height=430, xaxis_title="|r|", yaxis_title="Variável climática")
        st.plotly_chart(figb, use_container_width=True, key=uid())
        st.dataframe(best, use_container_width=True)

    if daily.empty or "casos" not in daily.columns:
        return
    daily["data"] = pd.to_datetime(daily.get("data"), errors="coerce")
    top = best.head(3)
    cols = st.columns(len(top)) if len(top) > 0 else []
    for i, (_, r) in enumerate(top.iterrows()):
        var = r["variavel_climatica"]
        lag = int(r.get("lag_dias", 0)) if pd.notna(r.get("lag_dias", np.nan)) else 0
        if var not in daily.columns:
            continue
        dd = daily[[var, "casos"]].copy()
        dd[f"{var}_lag{lag}"] = dd[var].shift(lag) if lag > 0 else dd[var]
        xcol = f"{var}_lag{lag}"
        with cols[i]:
            fig = px.scatter(dd, x=xcol, y="casos", trendline="ols",
                             title=f"{var} lag {lag}d<br>r={fmt(r.get('spearman', np.nan),2)} | R²={fmt(r.get('r2', np.nan),3)}")
            fig.update_traces(marker=dict(size=7))
            fig.update_layout(height=420, xaxis_title=var, yaxis_title="Casos")
            st.plotly_chart(fig, use_container_width=True, key=uid())
    st.caption("Correlação ecológica: indica associação temporal exploratória, não causalidade individual.")


def _comorb_label(name: str) -> str:
    s = str(name or "")
    s = s.replace("DoencasPreexistentes", "").replace("_bin_v17", "")
    mapa = {
        "AIDS": "AIDS/HIV",
        "Imunodepressoras": "Doenças imunodepressoras",
        "IRA": "Infecção respiratória aguda (IRA)",
        "Tuberculose": "Tuberculose",
        "Traumatismo": "Traumatismo",
        "InfeccaoHospitalar": "Infecção hospitalar",
        "Outras": "Outras comorbidades",
    }
    return mapa.get(s, s)


def _comorb_hint(name: str) -> str:
    s = str(name or "").lower()
    if "aids" in s:
        return "Imunossupressão aumenta risco de infecções graves e pior evolução clínica."
    if "imuno" in s:
        return "Condições imunodepressoras elevam vulnerabilidade a infecções do SNC."
    if "ira" in s:
        return "IRA pode preceder/coexistir com meningite; avaliar via aérea e etiologia."
    if "tuber" in s:
        return "Relevante para meningite tuberculosa e investigação de contatos/TB."
    if "hospital" in s:
        return "Sugere gravidade, internação prolongada ou complicação hospitalar."
    if "trauma" in s:
        return "Trauma pode relacionar-se a falhas de barreira e infecção secundária."
    return "Avaliar plausibilidade clínica e qualidade do preenchimento SINAN."


def _cramer_nivel(v) -> tuple[str, str]:
    try:
        x = float(v)
    except Exception:
        return "—", "#64748b"
    if x >= 0.15:
        return "moderada/forte", "#b91c1c"
    if x >= 0.10:
        return "moderada", "#ea580c"
    if x >= 0.05:
        return "fraca–moderada", "#ca8a04"
    return "fraca", "#64748b"


def comorb_interpretation_guide():
    st.markdown(
        """
<div class="guide-card">
<b>Como ler esta aba (para gestores e vigilância)</b><br/><br/>
• <b>p-valor</b>: chance de o achado ser só “acaso”. Em geral, <b>p &lt; 0,05</b> sugere associação estatística;
  usamos também <b>p &lt; 0,005</b> para destacar achados mais robustos.<br/>
• <b>Cramér's V</b>: força da associação (0 a 1). Guia prático:
  &lt;0,05 fraca · 0,05–0,10 fraca–moderada · 0,10–0,15 moderada · ≥0,15 moderada/forte.<br/>
• <b>Não é causalidade</b>: associação entre comorbidade e evolução/classificação <i>não prova</i> que a comorbidade causou o desfecho.
  Pode haver idade, gravidade, acesso ao serviço e preenchimento incompleto.<br/>
• <b>Uso operacional</b>: priorizar investigação clínica, completar campos SINAN e discutir casos com pior evolução
  (óbito/grave) quando a comorbidade for frequente e significativa.
</div>
        """,
        unsafe_allow_html=True,
    )


def narrativa_comorbidades(com: pd.DataFrame, use_llm: bool = False) -> str:
    """Texto justificativo offline (+ LLM opcional via assistente)."""
    d = com.copy()
    for c in ["p_value", "cramers_v"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    top = d[d["p_value"] < 0.005].sort_values(["p_value", "cramers_v"], ascending=[True, False]).head(8)
    if top.empty:
        top = d.sort_values("p_value").head(5)

    bullets = []
    for _, r in top.iterrows():
        lab = _comorb_label(r.get("variavel"))
        nivel, _ = _cramer_nivel(r.get("cramers_v"))
        hint = _comorb_hint(str(r.get("variavel")))
        bullets.append(
            f"- **{lab}** × {r.get('desfecho')}: p={fmt(r.get('p_value'), 4)}, "
            f"Cramér's V={fmt(r.get('cramers_v'), 3)} ({nivel}). {hint}"
        )

    texto = [
        "### Leitura assistida dos achados de comorbidades",
        "",
        "Com base nos testes de associação (qui-quadrado / Cramér's V) da base SINAN de meningites do MT:",
        "",
        *bullets,
        "",
        "**Justificativa epidemiológica (síntese):** comorbidades que comprometem imunidade "
        "(HIV/AIDS, doenças imunodepressoras), infecção respiratória prévia e tuberculose "
        "são biologicamente plausíveis em meningites e devem orientar investigação clínica, "
        "oportunidade diagnóstica e completude da ficha. Infecção hospitalar associada à evolução "
        "pode indicar gravidade e necessidade de revisar cuidado hospitalar e notificação.",
        "",
        "> Texto de apoio à vigilância. **Validar com a equipe CIEVS** antes de comunicação oficial. "
        "Associação estatística ≠ causalidade.",
    ]
    base_txt = "\n".join(texto)

    # RAG normativo + LLM opcional
    try:
        assist = __import__("16_assistente_cievs_v23")
        ctx = "Achados de comorbidades (top):\n" + "\n".join(bullets[:6])
        q = (
            "Justifique epidemiologicamente associações entre comorbidades pré-existentes "
            "(HIV/AIDS, imunodepressão, IRA, tuberculose, infecção hospitalar) e evolução/desfecho "
            "em meningites, citando boas práticas de vigilância MS/CIEVS."
        )
        ans = assist.answer(q, contexto_dados=ctx, use_llm=use_llm)
        extra = ans.get("resposta_llm") or ""
        fontes = ans.get("fontes") or []
        if use_llm and extra:
            base_txt += "\n\n### Narrativa IA (revisar)\n\n" + extra
        elif fontes:
            base_txt += "\n\n### Apoio normativo recuperado\n\n"
            for f in fontes[:3]:
                base_txt += f"- {f.get('titulo')} — {f.get('fonte')}\n"
            # incluir trecho offline resumido
            offline = ans.get("resposta", "")
            if offline and not use_llm:
                base_txt += "\n" + offline[:1800]
    except Exception as e:
        base_txt += f"\n\n_Assistente indisponível: {e}_"
    return base_txt


def comorb_section_v21():
    com = read_any(OUT / "associacoes_comorbidades_quiquadrado_v18.csv")
    detail = read_any(OUT / "associacoes_comorbidades_detalhe_v18.csv")
    if com.empty:
        st.info("Rode o script 10_comorbidades_associacoes_v18.py para gerar esta aba.")
        return

    for c in ["p_value", "cramers_v"]:
        if c in com.columns:
            com[c] = pd.to_numeric(com[c], errors="coerce")

    st.caption("Associações entre doenças pré-existentes (SINAN) e evolução / classificação final do caso.")
    comorb_interpretation_guide()

    # KPIs resumidos
    n_sig = int((com["p_value"] < 0.05).sum()) if "p_value" in com.columns else 0
    n_strong = int((com["p_value"] < 0.005).sum()) if "p_value" in com.columns else 0
    k1, k2, k3 = st.columns(3)
    with k1:
        mini_metric_card("Testes analisados", fmt(len(com), 0))
    with k2:
        mini_metric_card("Assoc. p < 0,05", fmt(n_sig, 0))
    with k3:
        mini_metric_card("Destaques p < 0,005", fmt(n_strong, 0))

    significant_alerts_from_frames([("comorbidades", com)], threshold=0.005, title="Comorbidades com p < 0,005")

    # Narrativa IA / assistente
    st.subheader("Justificativa dos achados (assistente CIEVS)")
    usar_llm = st.checkbox(
        "Enriquecer com LLM (se OPENAI_API_KEY estiver configurada)",
        value=False,
        key="comorb_llm",
    )
    if st.button("Gerar / atualizar texto justificativo", key="btn_comorb_narr"):
        with st.spinner("Montando leitura assistida…"):
            narr = narrativa_comorbidades(com, use_llm=usar_llm)
            st.session_state["comorb_narrativa"] = narr
    narr = st.session_state.get("comorb_narrativa")
    if not narr:
        narr = narrativa_comorbidades(com, use_llm=False)
        st.session_state["comorb_narrativa"] = narr
    st.markdown(f'<div class="ai-box">{narr.replace(chr(10), "<br/>")}</div>', unsafe_allow_html=True)
    st.download_button(
        "Baixar justificativa (.md)",
        data=narr.encode("utf-8"),
        file_name="justificativa_comorbidades_cievs.md",
        mime="text/markdown",
        key="dl_comorb_narr",
    )

    for des in ["Evolução", "Classificação final"]:
        st.markdown("---")
        st.subheader(f"Comorbidades × {des}")
        sub = com[com["desfecho"].astype(str).eq(des)].copy()
        if sub.empty:
            st.info(f"Sem resultados para {des}.")
            continue
        sub = sub.sort_values("p_value")
        top = sub.head(20).copy()
        top["comorbidade"] = top["variavel"].map(_comorb_label)
        top["forca"] = top["cramers_v"].map(lambda v: _cramer_nivel(v)[0])
        top["cor"] = top["cramers_v"].map(lambda v: _cramer_nivel(v)[1])

        fig = go.Figure()
        fig.add_bar(
            x=pd.to_numeric(top["cramers_v"], errors="coerce"),
            y=top["comorbidade"],
            orientation="h",
            marker_color=top["cor"],
            text=[f"V={fmt(v,3)} · p={fmt(p,4)}" for v, p in zip(top["cramers_v"], top["p_value"])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Cramér's V=%{x:.3f}<extra></extra>",
        )
        fig.update_layout(
            title=f"Força da associação (Cramér's V) — {des}",
            height=max(420, 28 * len(top) + 120),
            xaxis_title="Cramér's V (0=sem associação · 1=máxima)",
            yaxis_title="",
            margin=dict(l=20, r=80, t=60, b=40),
        )
        st.plotly_chart(fig, use_container_width=True, key=uid())

        # Tabela amigável
        show = pd.DataFrame({
            "Comorbidade": top["comorbidade"].values,
            "Desfecho": top["desfecho"].values,
            "N": top["n"].values,
            "p-valor": top["p_value"].values,
            "Cramér's V": top["cramers_v"].values,
            "Força": top["forca"].values,
            "Leitura clínica/vigilância": [_comorb_hint(v) for v in top["variavel"]],
        })
        st.dataframe(show, use_container_width=True)

        if not detail.empty:
            det = detail[detail["desfecho"].astype(str).eq(des)]
            if not det.empty:
                with st.expander(f"Detalhamento dos grupos comparados — {des}"):
                    st.dataframe(det, use_container_width=True)

def indicators_by_year(ind):
    needed = {"ano_evento_v17","casos","obitos_meningite","confirmados","populacao"}
    if not needed.issubset(ind.columns):
        st.info("Indicadores históricos indisponíveis.")
        return
    agg_dict = {
        "casos": ("casos","sum"),
        "confirmados": ("confirmados","sum"),
        "obitos": ("obitos_meningite","sum"),
        "populacao": ("populacao","sum"),
    }
    if "hospitalizacoes" in ind.columns:
        agg_dict["hospitalizacoes"] = ("hospitalizacoes","sum")
    else:
        agg_dict["hospitalizacoes"] = ("casos","sum")
    hist = ind.groupby("ano_evento_v17").agg(**agg_dict).reset_index()
    hist["incidencia_100mil"] = hist["casos"] / hist["populacao"] * 100000
    hist["mortalidade_100mil"] = hist["obitos"] / hist["populacao"] * 100000
    hist["letalidade_confirmados"] = hist["obitos"] / hist["confirmados"].replace(0, np.nan) * 100

    indicadores = [
        ("casos", "Casos", "Nº de casos"),
        ("confirmados", "Confirmados", "Nº de confirmados"),
        ("hospitalizacoes", "Hospitalizações", "Nº de hospitalizações"),
        ("obitos", "Óbitos por meningite", "Nº de óbitos"),
        ("incidencia_100mil", "Incidência por 100 mil", "Coeficiente"),
        ("mortalidade_100mil", "Mortalidade por 100 mil", "Coeficiente"),
        ("letalidade_confirmados", "Letalidade entre confirmados (%)", "%"),
    ]
    for i in range(0, len(indicadores), 2):
        cols = st.columns(2)
        for j, (col, titulo, ytitle) in enumerate(indicadores[i:i+2]):
            if col not in hist.columns:
                continue
            with cols[j]:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist["ano_evento_v17"], y=hist[col],
                    mode="lines+markers+text",
                    text=[fmt(v, 2) for v in hist[col]],
                    textposition="top center",
                    name=titulo,
                    line=dict(width=3)
                ))
                fig.update_layout(title=f"Série histórica — {titulo}", height=420, xaxis_title="Ano", yaxis_title=ytitle, margin=dict(l=40, r=30, t=60, b=40))
                st.plotly_chart(fig, use_container_width=True, key=uid())


def outbreak_section():
    alerts = read_any(OUT / "alerta_surtos_classificacao_agrupada_v17.csv")
    nt97 = read_any(OUT / "alertas_inteligentes_surtos_nt97_v23.csv")

    st.markdown("### Critérios do Ministério da Saúde / CIEVS")
    st.markdown(
        """
**Doença meningocócica (NT nº 97/2024-DPNI/SVSA/MS)**  
- **Surto comunitário:** elevação de casos DM lab+ acima do esperado histórico no território (ex.: > média anual dos anos anteriores), com investigação de vínculo e resposta (quimioprofilaxia/vacinação conforme GVS).  
- **Surto institucional:** ≥2 casos DM associados a instituição (escola, creche, quartel, etc.) em janela epidemiológica.  
- **Resposta sensível:** 1 caso de DM já exige investigação de contatos e oportunidade de quimioprofilaxia.

**Demais etiologias (critério operacional CIEVS-MT no sistema)**  
- Acima do limite histórico / média+2DP da mesma classificação no município-SE  
- Agregado ≥2 casos da mesma classificação em 14 dias  
- ≥2 confirmados na semana · óbito por meningite · DM com peso adicional  

**Classes de alerta:**  
"""
        + f'{semaforo_badge("Atenção")} sinais iniciais · '
        + f'{semaforo_badge("Alto")} múltiplos critérios · '
        + f'{semaforo_badge("Crítico")} excedência/óbito/surto NT97',
        unsafe_allow_html=True,
    )

    if not nt97.empty:
        st.subheader("Surtos / aglomerados — critérios NT 97 (DM)")
        ycol = "municipio_v17" if "municipio_v17" in nt97.columns else nt97.columns[1]
        xcol = "n_casos_90d_lab" if "n_casos_90d_lab" in nt97.columns else (
            "n_casos" if "n_casos" in nt97.columns else nt97.select_dtypes("number").columns[0]
        )
        fig_nt = px.bar(
            nt97.head(40),
            x=xcol,
            y=ycol,
            color="severidade" if "severidade" in nt97.columns else None,
            color_discrete_map=plotly_semaforo_map(nt97.get("severidade")),
            orientation="h",
            title="Alertas NT 97 — doença meningocócica",
            hover_data=[c for c in ["tipo_alerta", "acao_recomendada", "norma", "evidencia"] if c in nt97.columns],
        )
        fig_nt.update_layout(
            height=max(420, 28 * min(len(nt97), 40) + 120),
            legend=dict(orientation="h", y=-0.15),
            margin=dict(b=80, t=60),
        )
        st.plotly_chart(fig_nt, use_container_width=True, key=uid())
        st.dataframe(nt97, use_container_width=True)

    if alerts.empty:
        st.info("Arquivo de alertas de surtos municipais não encontrado. Rode o módulo 03 do pipeline.")
        return
    alerts = alerts[alerts["classe_alerta"].astype(str).isin(["Atenção", "Alto", "Crítico"])].copy()
    if alerts.empty:
        st.success("Não há surtos municipais classificados no momento (fora de Rotina).")
        return

    st.subheader("Alertas municipais por classificação (canal + agregação)")
    fig = px.bar(
        alerts.sort_values(["classe_alerta", "pontuacao_alerta", "casos_semana"], ascending=[True, False, False]),
        x="casos_semana",
        y="municipio_v17",
        color="classe_alerta",
        text="casos_semana",
        orientation="h",
        color_discrete_map=plotly_semaforo_map(alerts.get("classe_alerta")),
        hover_data=["classificacao_agrupada_v17", "motivos", "recomendacao_vigilancia"]
        if {"motivos", "recomendacao_vigilancia"}.issubset(alerts.columns)
        else ["classificacao_agrupada_v17"],
        title="Eventos classificados como surtos/alertas acionáveis",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=max(480, 26 * len(alerts.head(50)) + 140),
        legend_title_text="Classe",
        legend=dict(orientation="h", y=-0.12),
        margin=dict(b=90, t=60, l=10, r=30),
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())
    keep = [c for c in ["municipio_v17","regional_v17","classificacao_agrupada_v17","casos_semana","confirmados_semana","obitos_semana","classe_alerta","motivos","recomendacao_vigilancia"] if c in alerts.columns]
    st.dataframe(alerts[keep] if keep else alerts, use_container_width=True)


def canal_plot(d, clas):
    d = d[d["classificacao_agrupada_v17"].astype(str).eq(clas)].copy().sort_values("semana_epi_v17")
    if d.empty:
        return
    fig = go.Figure()
    for col in ["minimo","maximo","q25","q75","media","p95","observado"]:
        if col not in d.columns:
            return
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["maximo"], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["minimo"], mode="lines", fill="tonexty", line=dict(width=0), name="Faixa total"))
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["q75"], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["q25"], mode="lines", fill="tonexty", line=dict(width=0), name="Faixa interquartil"))
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["media"], mode="lines+markers", name="Média histórica"))
    fig.add_trace(go.Scatter(x=d["semana_epi_v17"], y=d["p95"], mode="lines+markers", name="Limite/P95"))
    fig.add_trace(go.Bar(x=d["semana_epi_v17"], y=d["observado"], text=d["observado"], textposition="outside", name="Observado"))
    fig.update_layout(title=f"Canal endêmico — {clas}", xaxis_title="Semana epidemiológica", yaxis_title="Casos", height=580)
    st.plotly_chart(fig, use_container_width=True, key=uid())


def forecast_chart(base, fc, desfecho):
    col_map = {"casos": "caso_v17", "hospitalizacoes": "hospitalizacao_v17", "obitos_meningite": "obito_meningite_v17"}
    hist_col = col_map.get(desfecho)
    if hist_col not in base.columns or fc.empty:
        return
    hist = base.groupby("data_ref_v17").agg(valor=(hist_col, "sum")).reset_index().sort_values("data_ref_v17").tail(120)
    dfc = fc[fc["desfecho"].astype(str).eq(desfecho)].copy()
    if dfc.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["data_ref_v17"], y=hist["valor"], mode="lines+markers", text=hist["valor"], textposition="top center", name="Histórico"))
    for h in sorted(dfc["horizonte_dias"].dropna().unique()):
        s = dfc[dfc["horizonte_dias"].eq(h)].copy().sort_values("data_prevista")
        if not {"lower_95","upper_95","pred","data_prevista"}.issubset(s.columns):
            continue
        fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["upper_95"], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["lower_95"], mode="lines", fill="tonexty", line=dict(width=0), name=f"IC95% {int(h)}d"))
        fig.add_trace(go.Scatter(x=s["data_prevista"], y=s["pred"], mode="lines+markers+text", text=[fmt(v,1) for v in s["pred"]], textposition="top center", name=f"Previsão {int(h)}d"))
    fig.update_layout(title=f"Forecasting e IC95% — {desfecho}", height=560, xaxis_title="Data", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True, key=uid())


def nowcasting_chart(base, now):
    if now.empty or "data_ref_v17" not in base.columns:
        return
    hist = base.groupby("data_ref_v17").agg(casos=("caso_v17", "sum")).reset_index().sort_values("data_ref_v17").tail(30)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hist["data_ref_v17"], y=hist["casos"], text=hist["casos"], textposition="outside", name="Observado 30 dias"))
    r = now.iloc[0]
    if "data_referencia" in r.index and "nowcasting_7d" in r.index:
        fig.add_trace(go.Scatter(x=[pd.to_datetime(r["data_referencia"])], y=[r["nowcasting_7d"]], mode="markers+text", text=[f"Nowcasting {fmt(r['nowcasting_7d'])}"], textposition="top center", marker=dict(size=15), name="Nowcasting 7d"))
    fig.update_layout(title="Nowcasting operacional da última semana", height=450)
    st.plotly_chart(fig, use_container_width=True, key=uid())
    st.dataframe(now, use_container_width=True)


def climate_section():
    """Correlação exploratória clima × casos/desfechos (módulo 06). Não é o SIS Clima-Saúde."""
    st.caption(
        "Análise **exploratória** de associação temporal entre variáveis climáticas e meningites. "
        "Não implica causalidade e **não** substitui o SIS Integrado Clima-Saúde."
    )
    diag = OUT / "diagnostico_clima_v17.txt"
    if diag.exists():
        st.info(diag.read_text(encoding="utf-8"))
    corr = read_any(OUT / "correlacao_clima_casos_v17.csv")
    top = read_any(OUT / "correlacao_clima_desfechos_top_v17.csv")
    daily = read_any(OUT / "clima_casos_diario_v17.csv")
    if corr.empty:
        st.warning("Rode: py -3.13 06_clima_casos_meningites_v17.py")
        return

    for c in ["spearman", "pearson", "r2", "lag_dias"]:
        if c in corr.columns:
            corr[c] = pd.to_numeric(corr[c], errors="coerce")
    if "abs_r" not in corr.columns and "spearman" in corr.columns:
        corr["abs_r"] = corr["spearman"].abs()

    desfechos = sorted(corr["desfecho"].dropna().astype(str).unique()) if "desfecho" in corr.columns else ["casos"]
    escolha = st.selectbox("Desfecho", desfechos, index=0 if "casos" not in desfechos else desfechos.index("casos"))
    sub = corr[corr["desfecho"].astype(str).eq(escolha)].copy() if "desfecho" in corr.columns else corr.copy()
    best = sub.sort_values("abs_r", ascending=False).head(20) if "abs_r" in sub.columns else sub.head(20)

    st.subheader(f"Maiores |correlações| — {escolha}")
    if not best.empty:
        fig = px.bar(
            best,
            x="spearman",
            y="variavel_climatica",
            color="lag_dias" if "lag_dias" in best.columns else None,
            orientation="h",
            text=[fmt(v, 2) for v in best["spearman"]],
            title=f"Spearman clima × {escolha} (lags 0–30 dias)",
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(height=max(420, 26 * len(best) + 120), margin=dict(b=40, t=60))
        st.plotly_chart(fig, use_container_width=True, key=uid())
        st.dataframe(best, use_container_width=True)

    if not top.empty:
        with st.expander("Top correlações por desfecho"):
            st.dataframe(top, use_container_width=True)

    # Narrativa assistida
    st.subheader("Interpretação assistida (IA / RAG)")
    usar_llm = st.checkbox("Usar LLM (Gemini/OpenAI se configurado no .env)", value=False, key="clima_llm")
    if st.button("Gerar leitura dos achados climáticos", key="btn_clima_narr"):
        linhas = []
        for _, r in best.head(5).iterrows():
            linhas.append(
                f"- {r.get('variavel_climatica')} lag {r.get('lag_dias')}d: "
                f"Spearman={fmt(r.get('spearman'), 3)}, R²={fmt(r.get('r2'), 3)}"
            )
        ctx = f"Desfecho: {escolha}\n" + "\n".join(linhas)
        try:
            from meningites_env import load_meningites_env
            load_meningites_env()
            assist = __import__("16_assistente_cievs_v23")
            ans = assist.answer(
                "Interprete correlações ecológicas entre clima e meningites para o CIEVS. "
                "Enfatize que não há causalidade e que sazonalidade/atraso de notificação confundem.",
                contexto_dados=ctx,
                use_llm=usar_llm,
            )
            st.markdown(
                f'<div class="ai-box">{(ans.get("resposta") or "").replace(chr(10), "<br/>")}</div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.warning(f"Assistente indisponível: {e}")

    if not daily.empty and {"data", "casos"}.issubset(daily.columns):
        daily = daily.copy()
        daily["data"] = pd.to_datetime(daily["data"], errors="coerce")
        vars_ = [c for c in daily.columns if c not in ["data", "casos", "confirmados", "hospitalizacoes", "obitos", "altas"]
                 and pd.api.types.is_numeric_dtype(daily[c])]
        st.subheader("Dispersão exploratória (casos)")
        for var in vars_[:4]:
            fig = px.scatter(daily, x=var, y="casos", trendline="ols", title=f"Casos vs {var}")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True, key=uid())


def parse_positive(x):
    """
    Retorna:
    1 = positivo; 0 = negativo; 2 = inconclusivo/outro resultado válido; NaN = não realizado/ignorado/vazio.
    """
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
    if any(t in s for t in ["POSITIVO", "REAGENTE", "DETECTADO", "DETECTAVEL", "ISOLADO", "IDENTIFICADO"]):
        return 1
    if any(t in s for t in ["NEGATIVO", "NAO REAGENTE", "NAO DETECTADO", "NAO DETECTAVEL", "AUSENTE"]):
        return 0
    if any(t in s for t in ["INCONCLUSIVO", "INDETERMINADO", "INVALIDO", "PREJUDICADO"]):
        return 2
    return np.nan


def lab_section(df):
    lab_cols = [
        "PuncaoLombar", "DataPuncaoLombar", "AspectoLiquor", "ResultadoCulturaLiquor", "ResultadoCulturaPetequias",
        "ResultadoCulturaSangueSoro", "ResultadoCulturaEscarro", "ResultadoBacterioscopiaLiquor", "ResultadoBacterioscopiaPetequias",
        "ResultadoBacterioscopiaSangueSoro", "ResultadoBacterioscopiaEscarro", "ResultadoCIELiquor", "ResultadoCIESangueSoro",
        "ResultadoAglutinacaoLatexLiquor", "ResultadoAglutinacaoLatexSangueSoro", "ResultadoIsolamentoViralLiquor", "ResultadoIsolamentoViralFezes",
        "ResultadoPCRLiquor", "ResultadoPCRPetequias", "ResultadoPCRSangueSoro", "ResultadoPCREscarro"
    ]
    existing = [c for c in lab_cols if c in df.columns]
    total_not = len(df)
    total_conf = int(pd.to_numeric(df["confirmado_v17"], errors="coerce").sum()) if "confirmado_v17" in df.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de notificações", fmt(total_not, 0))
    c2.metric("Total de confirmados", fmt(total_conf, 0))
    crit = df.get("CriterioConfirmacao", pd.Series(index=df.index, dtype=object)).fillna("Ignorado").astype(str).value_counts().reset_index()
    crit.columns = ["Critério de confirmação", "n"]
    c3.metric("Critérios distintos", fmt(len(crit), 0))
    st.caption("Taxa de positividade real = positivos / resultados concludentes (positivo + negativo). Inconclusivos e não realizados não entram no denominador principal.")

    if existing:
        rows = []
        for c in existing:
            s = df[c].map(parse_positive) if c.startswith("Resultado") else pd.Series(np.where(df[c].notna(), 1, np.nan), index=df.index)
            realizado = int(s.notna().sum())
            positivo = int((s == 1).sum())
            rows.append({"metodologia": c, "realizados/preenchidos": realizado, "positivos": positivo, "taxa_positividade_pct": positivo / realizado * 100 if realizado else np.nan})
        labdf = pd.DataFrame(rows)
        bar_with_labels(labdf.sort_values("realizados/preenchidos", ascending=False).head(20), "realizados/preenchidos", "metodologia", "KPIs laboratoriais por metodologia", color="taxa_positividade_pct", orient="h", height=620)
        st.dataframe(labdf, use_container_width=True)

    result_cols = [c for c in existing if c.startswith("Resultado")]
    if result_cols and "classificacao_agrupada_v17" in df.columns:
        any_pos = pd.Series(False, index=df.index)
        any_done = pd.Series(False, index=df.index)
        for c in result_cols:
            parsed = df[c].map(parse_positive)
            any_pos = any_pos | (parsed == 1)
            any_done = any_done | parsed.notna()
        tmp = df.copy()
        tmp["any_lab_pos"] = any_pos.astype(int)
        tmp["any_lab_done"] = any_done.astype(int)
        g = tmp.groupby("classificacao_agrupada_v17").agg(total=("caso_v17", "sum"), com_resultado=("any_lab_done", "sum"), positivos=("any_lab_pos", "sum")).reset_index()
        g["taxa_positividade_pct"] = g["positivos"] / g["com_resultado"].replace(0, np.nan) * 100
        bar_with_labels(g, "taxa_positividade_pct", "classificacao_agrupada_v17", "Taxa de positividade por classificação agrupada", orient="h", height=420)
        st.dataframe(g, use_container_width=True)

    st.subheader("Critério de confirmação")
    bar_with_labels(crit, "n", "Critério de confirmação", "Distribuição do critério de confirmação", orient="h", height=400)
    st.dataframe(crit, use_container_width=True)


def vaccine_section(df):
    vac_cols = [
        "VacinaContraPolissacaridicaAC", "VacinaContraPolissacaridicaBC", "VacinaConjugadaMeningoC", "VacinaContraBCG",
        "VacinaContraTriplice", "VacinaContraHemofilos", "VacinaContraPneumococo", "VacinaOutras", "VacinaOutrasEspecificar"
    ]
    present = [c for c in vac_cols if c in df.columns]
    if not present:
        st.info("Sem variáveis vacinais disponíveis.")
        return
    rows = []
    for c in present:
        if c.endswith("Especificar"):
            informado = int((df[c].notna() & df[c].astype(str).str.strip().ne("")).sum())
            rows.append({"variavel_vacinal": c, "informado": informado, "vacinados_sim": np.nan})
        else:
            sim = df[c].map(simnao_bin)
            rows.append({"variavel_vacinal": c, "informado": int(sim.notna().sum()), "vacinados_sim": int((sim == 1).sum())})
    vacdf = pd.DataFrame(rows)
    bar_with_labels(vacdf.fillna(0), "vacinados_sim", "variavel_vacinal", "Registros vacinais — respostas positivas", orient="h", height=450)
    st.dataframe(vacdf, use_container_width=True)

    other = df.get("VacinaOutrasEspecificar", pd.Series(index=df.index, dtype=object)).dropna().astype(str).str.strip()
    if not other.empty:
        top = other[other.ne("")].value_counts().head(15).reset_index()
        top.columns = ["VacinaOutrasEspecificar", "n"]
        bar_with_labels(top, "n", "VacinaOutrasEspecificar", "Principais registros em VacinaOutrasEspecificar", orient="h", height=420)

    ev = read_any(OUT / "efetividade_vacinal_etiologia_coerente_v17.csv")
    if not ev.empty:
        st.subheader("Odds Ratio e análise de eficácia vacinal")
        ev["or"] = pd.to_numeric(ev.get("or"), errors="coerce")
        use = ev[ev["status"].astype(str).eq("Aplicável etiologicamente")].copy() if "status" in ev.columns else ev.copy()
        fig = px.scatter(use, x="or", y="vacina", color="desfecho" if "desfecho" in use.columns else None, size="n_analisado" if "n_analisado" in use.columns else None,
                         hover_data=[c for c in ["classificacao_agrupada_v17","p_value","efetividade_vacinal_estimada_pct","interpretacao"] if c in use.columns], title="OR bruto por vacina e desfecho")
        fig.add_vline(x=1, line_dash="dash")
        fig.update_layout(height=620, xaxis_title="Odds Ratio", yaxis_title="Vacina")
        st.plotly_chart(fig, use_container_width=True, key=uid())
        st.markdown("""
**Como interpretar o Odds Ratio (OR) neste contexto:**
- **OR < 1:** sugere efeito protetor observacional da vacinação para o desfecho analisado.
- **OR = 1:** ausência de diferença observável entre vacinados e não vacinados.
- **OR > 1:** sugere maior chance observada do desfecho; em vigilância, pode refletir confundimento, seleção, gravidade, viés de notificação ou diferença de composição dos grupos.
- A interpretação final **deve considerar IC95%, p-valor, tamanho amostral, coerência etiológica e relevância prática/clínica**.
""")
        st.dataframe(ev, use_container_width=True)


def comorb_section():
    com = read_any(OUT / "associacoes_comorbidades_quiquadrado_v18.csv")
    detail = read_any(OUT / "associacoes_comorbidades_detalhe_v18.csv")
    if com.empty:
        st.info("Rode o script 10_comorbidades_associacoes_v18.py para gerar esta aba.")
        return
    com["p_value"] = pd.to_numeric(com["p_value"], errors="coerce")
    com["cramers_v"] = pd.to_numeric(com["cramers_v"], errors="coerce")
    bar_with_labels(com.sort_values("p_value").head(20), "cramers_v", "variavel", "Comorbidades vs evolução/classificação final — força da associação", color="desfecho" if "desfecho" in com.columns else None, orient="h", height=600)
    st.dataframe(com, use_container_width=True)
    if not detail.empty:
        st.subheader("Detalhamento dos grupos comparados")
        st.dataframe(detail, use_container_width=True)


def sazonalidade_section():
    """Sazonalidade mensal + heatmap SE×ano (módulo 21)."""
    resumo = read_any(OUT / "sazonalidade_resumo_v23.csv")
    idx = read_any(OUT / "sazonalidade_indice_mensal_v23.csv")
    heat = read_any(OUT / "sazonalidade_heatmap_semana_ano_v23.csv")
    perfil = read_any(OUT / "sazonalidade_perfil_semana_epi_v23.csv")
    if resumo.empty and idx.empty:
        st.info("Rode: py -3.13 21_sazonalidade_meningites_v23.py")
        return
    st.caption("Sazonalidade de meningites (SE e mês) — apoio à vigilância MS / CIEVS. Sem misturar clima.")
    if not resumo.empty:
        r = resumo.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mês de pico", str(r.get("mes_pico_1_rotulo", "")))
        c2.metric("Índice sazonal pico", fmt(r.get("indice_pico_1")))
        c3.metric(f"Casos SE {int(r.get('semana_epi_atual') or 0)}", fmt(r.get("casos_se_atual"), 0))
        c4.metric("Média histórica SE", fmt(r.get("media_historica_se_atual")))
    if not idx.empty and {"mes_rotulo", "indice_sazonal"}.issubset(idx.columns):
        fig = px.bar(
            idx.sort_values("mes"),
            x="mes_rotulo", y="indice_sazonal",
            title="Índice sazonal mensal (1,0 = média do ano)",
            color="indice_sazonal",
        )
        fig.add_hline(y=1.0, line_dash="dash")
        fig.update_layout(height=420, xaxis_title="Mês", yaxis_title="Índice sazonal")
        st.plotly_chart(fig, use_container_width=True, key=uid())
    if not heat.empty and {"ano_epi", "semana_epi", "casos"}.issubset(heat.columns):
        piv = heat.pivot_table(index="ano_epi", columns="semana_epi", values="casos", aggfunc="sum")
        fig2 = px.imshow(
            piv, aspect="auto",
            title="Heatmap casos — ano epidemiológico × semana",
            labels={"x": "Semana epi", "y": "Ano epi", "color": "Casos"},
        )
        fig2.update_layout(height=480)
        st.plotly_chart(fig2, use_container_width=True, key=uid())
    if not perfil.empty:
        with st.expander("Perfil médio por semana epidemiológica"):
            st.dataframe(perfil, use_container_width=True)
    rel = REL / "SAZONALIDADE_MENINGITES_V23.md"
    if rel.exists():
        with st.expander("Relatório de sazonalidade"):
            st.markdown(rel.read_text(encoding="utf-8")[:5000])


def plot_nowcast_forecast_historico(estrato: str, nc24: pd.DataFrame, fc24: pd.DataFrame):
    """Série histórica + nowcast recente + forecast com IC 80%."""
    serie = read_any(OUT / "nowcast_serie_semanal_v24.csv")
    if serie.empty:
        serie = read_any(OUT / "nowcast_serie_semanal_casos_v23.csv")
        if not serie.empty and "estrato" not in serie.columns:
            serie = serie.copy()
            serie["estrato"] = "ESTADUAL"
            if "y" not in serie.columns and "casos" in serie.columns:
                serie = serie.rename(columns={"casos": "y"})

    fig = go.Figure()
    hist = pd.DataFrame()
    if not serie.empty and "estrato" in serie.columns:
        hist = serie[serie["estrato"].astype(str).eq(estrato)].copy()
    elif not serie.empty:
        hist = serie.copy()

    if not hist.empty and {"periodo", "y"}.issubset(hist.columns):
        hist = hist.sort_values(["ano_epi_v17", "semana_epi_v17"] if {"ano_epi_v17", "semana_epi_v17"}.issubset(hist.columns) else ["periodo"])
        hist = hist.tail(104)
        fig.add_trace(go.Scatter(
            x=hist["periodo"], y=pd.to_numeric(hist["y"], errors="coerce"),
            mode="lines", name="Histórico (casos/SE)",
            line=dict(color="#64748b", width=1.6),
        ))

    sub = nc24[nc24["estrato"].astype(str).eq(estrato)].copy() if not nc24.empty and "estrato" in nc24.columns else pd.DataFrame()
    if not sub.empty:
        fig.add_trace(go.Scatter(
            x=sub["periodo"], y=pd.to_numeric(sub["observado"], errors="coerce"),
            mode="markers+lines", name="Observado (recente)",
            marker=dict(size=9, color="#0f766e"), line=dict(color="#0f766e", width=2),
        ))
        y_nc = pd.to_numeric(sub["nowcast"], errors="coerce")
        fig.add_trace(go.Scatter(
            x=sub["periodo"], y=y_nc,
            mode="markers+lines", name="Nowcast",
            marker=dict(size=10, symbol="diamond", color="#c2410c"),
            line=dict(color="#c2410c", width=2, dash="dot"),
        ))
        if {"nowcast_p10", "nowcast_p90"}.issubset(sub.columns):
            fig.add_trace(go.Scatter(
                x=sub["periodo"], y=pd.to_numeric(sub["nowcast_p90"], errors="coerce"),
                mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=sub["periodo"], y=pd.to_numeric(sub["nowcast_p10"], errors="coerce"),
                mode="lines", fill="tonexty", name="IC nowcast",
                line=dict(width=0), fillcolor="rgba(194,65,12,0.18)",
            ))

    fc_sub = pd.DataFrame()
    if not fc24.empty:
        fc_sub = fc24[fc24["estrato"].astype(str).eq(estrato)].copy() if "estrato" in fc24.columns else fc24.copy()
    if not fc_sub.empty and "periodo" in fc_sub.columns:
        # amarra forecast ao último ponto histórico/nowcast
        fig.add_trace(go.Scatter(
            x=fc_sub["periodo"], y=pd.to_numeric(fc_sub["pred"], errors="coerce"),
            mode="lines+markers", name="Forecast",
            marker=dict(size=8, color="#1d4ed8"), line=dict(color="#1d4ed8", width=2.4),
        ))
        if {"lower_80", "upper_80"}.issubset(fc_sub.columns):
            fig.add_trace(go.Scatter(
                x=fc_sub["periodo"], y=pd.to_numeric(fc_sub["upper_80"], errors="coerce"),
                mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=fc_sub["periodo"], y=pd.to_numeric(fc_sub["lower_80"], errors="coerce"),
                mode="lines", fill="tonexty", name="IC 80% forecast",
                line=dict(width=0), fillcolor="rgba(29,78,216,0.16)",
            ))

    fig.update_layout(
        title=dict(text=f"Série histórica · nowcast · forecast — {estrato}", y=0.98),
        height=560,
        xaxis_title="Semana epidemiológica",
        yaxis_title="Casos",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            x=0,
            xanchor="left",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#e5e7eb",
            borderwidth=1,
        ),
        margin=dict(l=50, r=30, t=70, b=110),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())


def mini_metric_card(label, value, delta=None, higher_is_bad=True, semaforo=None):
    """Card compacto com delta colorido (fonte = cor semântica)."""
    extra = ""
    if semaforo is not None:
        extra = f'<div style="margin-top:8px;">{semaforo_badge(semaforo)}</div>'
    elif delta is not None:
        try:
            d = float(delta)
            extra = kpi_delta_html(d, suffix="", higher_is_bad=higher_is_bad)
        except Exception:
            arrow, color = trend_arrow_color(None)
            extra = f'<div class="kpi-delta" style="color:{color};">{delta}</div>'
    st.markdown(
        f"""
        <div class="kpi-card" style="min-height:120px;">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="font-size:1.65rem;">{value}</div>
          {extra}
        </div>
        """,
        unsafe_allow_html=True,
    )


def nowcast_refinado_section():
    """Nowcast operacional V24 (estadual/DM/regional) + legado V23."""
    gest = read_any(OUT / "indicadores_gestao_semana_v24.csv")
    resumo24 = read_any(OUT / "nowcast_operacional_resumo_v24.csv")
    nc24 = read_any(OUT / "nowcasting_operacional_v24.csv")
    fc24 = read_any(OUT / "forecasting_operacional_v24.csv")
    bt24 = read_any(OUT / "forecasting_backtest_v24.csv")
    rank = read_any(OUT / "nowcast_regionais_ranking_v24.csv")

    if not gest.empty or not resumo24.empty:
        st.caption(
            "Nowcast operacional V24: atraso SE sintomas→notificação "
            "(DT_DIGITA ainda ausente no VW). Estratos: estadual, DM e regionais."
        )
        if not gest.empty:
            g = gest.iloc[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                mini_metric_card("Nowcast SE (MT)", fmt(g.get("casos_nowcast_se")), g.get("delta_nowcast_vs_se_anterior"), True)
            with c2:
                mini_metric_card("Observado SE", fmt(g.get("casos_observados_se")))
            with c3:
                mini_metric_card("Nowcast DM", fmt(g.get("dm_nowcast_se")))
            with c4:
                mini_metric_card("Fila crítica", fmt(g.get("fila_cievs_criticos_n"), 0))
            with c5:
                mini_metric_card("Atraso notif P90 (d)", fmt(g.get("atraso_notif_p90_dias")))
            st.write(f"**Status sazonal:** {g.get('status_sazonal')} — {g.get('status_detalhe', '')}")
            st.info(f"Ação sugerida: {g.get('acao_sugerida', '')}")

        if not resumo24.empty:
            ok = resumo24[resumo24.get("status", "ok").astype(str).eq("ok")].copy() if "status" in resumo24.columns else resumo24
            est = ok[ok["estrato"].astype(str).eq("ESTADUAL")]
            if not est.empty:
                e = est.iloc[0]
                st.caption(
                    f"Forecast SE+1: {fmt(e.get('forecast_se1'))} · MAPE backtest: {fmt(e.get('backtest_mape_pct'))}% "
                    f"({e.get('qualidade_forecast', '')})"
                )

        if not nc24.empty or not fc24.empty:
            estratos = []
            if not nc24.empty and "estrato" in nc24.columns:
                estratos = sorted(nc24["estrato"].dropna().astype(str).unique().tolist())
            prefer = [e for e in ["ESTADUAL", "DM"] if e in estratos]
            outros = [e for e in estratos if e not in prefer]
            escolha = st.selectbox("Estrato do nowcast / forecast", prefer + outros or ["ESTADUAL"], key="nc24_estrato")
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            plot_nowcast_forecast_historico(escolha, nc24, fc24)
            st.markdown("</div>", unsafe_allow_html=True)

            sub = nc24[nc24["estrato"].astype(str).eq(escolha)].copy() if not nc24.empty and "estrato" in nc24.columns else pd.DataFrame()
            if not sub.empty:
                with st.expander("Tabela nowcast (últimas SE)", expanded=False):
                    st.dataframe(sub, use_container_width=True)
            if not fc24.empty:
                fc_sub = fc24[fc24["estrato"].astype(str).eq(escolha)].copy() if "estrato" in fc24.columns else fc24
                if not fc_sub.empty:
                    with st.expander("Tabela forecast 8 SE", expanded=False):
                        st.dataframe(fc_sub, use_container_width=True)

            if not rank.empty:
                with st.expander("Ranking nowcast por regional"):
                    st.dataframe(rank, use_container_width=True)
            if not bt24.empty:
                with st.expander("Backtest V24"):
                    st.dataframe(bt24[bt24["estrato"].astype(str).eq(escolha)] if "estrato" in bt24.columns else bt24,
                                 use_container_width=True)
        st.markdown("---")
        st.subheader("Legado V23 (série única estadual)")

    resumo = read_any(OUT / "nowcast_forecast_resumo_v23.csv")
    nc = read_any(OUT / "nowcasting_atraso_corrigido_v23.csv")
    fc = read_any(OUT / "forecasting_semanal_ensemble_v23.csv")
    bt = read_any(OUT / "forecasting_backtest_v23.csv")
    if resumo.empty and gest.empty and resumo24.empty:
        st.info("Rode: py -3.13 24_nowcast_operacional_gestao_v24.py")
        return
    if resumo.empty:
        return
    r = resumo.iloc[0]
    st.caption("Nowcast corrigido por atraso de notificação + forecast ensemble semanal (V23).")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        mini_metric_card("Observado SE", fmt(r.get("observado_se_atual")))
    with c2:
        mini_metric_card("Nowcast corrigido", fmt(r.get("nowcast_se_atual")), r.get("incremento_atraso_estimado"), True)
    with c3:
        mini_metric_card("Forecast SE+1", fmt(r.get("forecast_se1")))
    with c4:
        mini_metric_card("Backtest MAPE %", fmt(r.get("backtest_mape_pct")))
    st.write(f"Status vs sazonalidade: **{r.get('alerta_nowcast')}** — {r.get('alerta_detalhe', '')}")
    # gráfico legado amarrado à série V23
    if not nc.empty or not fc.empty:
        fake_nc = nc.copy()
        if not fake_nc.empty and "estrato" not in fake_nc.columns:
            fake_nc["estrato"] = "ESTADUAL"
        fake_fc = fc.copy()
        if not fake_fc.empty and "estrato" not in fake_fc.columns:
            fake_fc["estrato"] = "ESTADUAL"
        plot_nowcast_forecast_historico("ESTADUAL", fake_nc if not fake_nc.empty else pd.DataFrame(), fake_fc if not fake_fc.empty else pd.DataFrame())
    if not bt.empty:
        with st.expander("Backtest (8 SE) V23"):
            st.dataframe(bt, use_container_width=True)


def alertas_personalizados_section():
    """Digests por regional / perfil CIEVS (módulo 23)."""
    idx = read_any(OUT / "alertas_personalizados_indice_v23.csv")
    msreg = read_any(OUT / "indicadores_ms_por_regional_v23.csv")
    narr = REL / "NARRATIVA_ALERTAS_SAZONALIDADE_V23.md"
    if idx.empty:
        st.info("Rode: py -3.13 23_alertas_personalizados_ia_v23.py")
        return
    st.caption("Pacotes de alerta personalizados (estadual, regional, lab) — prontos para disparo manual.")
    c1, c2 = st.columns(2)
    c1.metric("Digests gerados", fmt(len(idx), 0))
    c2.metric("Regionais", fmt(int((idx.get("perfil") == "COORD_REGIONAL").sum()) if "perfil" in idx.columns else 0, 0))
    if not msreg.empty:
        st.subheader("Indicadores MS por regional")
        st.dataframe(msreg, use_container_width=True)
    st.subheader("Índice de digests")
    st.dataframe(idx, use_container_width=True)
    digest_dir = OUT / "digests_regionais_v23"
    if digest_dir.exists():
        files = sorted(digest_dir.glob("DIGEST_*.md"))
        if files:
            escolhido = st.selectbox("Abrir digest", [f.name for f in files])
            if escolhido:
                st.markdown((digest_dir / escolhido).read_text(encoding="utf-8")[:8000])
    if narr.exists():
        with st.expander("Narrativa IA (sazonalidade + alertas + MS)"):
            st.markdown(narr.read_text(encoding="utf-8")[:6000])


def quality_section():
    # Linkage / prontidão GAL-LACEN-SIM
    link = read_any(OUT / "linkage_prontidao_v23.csv")
    proxy = read_any(OUT / "linkage_proxy_interno_resumo_v23.csv")
    enr = read_any(OUT / "enriquecimento_dw_resumo_v23.csv")
    if not link.empty or not proxy.empty or not enr.empty:
        st.subheader("Linkage GAL / LACEN / SIM (DW)")
        st.caption("Extratos do Data Warehouse SES/MT (`VW_GAL`, `SIM`) + proxy SINAN.")
        if not enr.empty:
            r = enr.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Match GAL (score≥0,75)", fmt(r.get("casos_gal"), 0))
            c2.metric("GAL positivo", fmt(r.get("casos_gal_positivo"), 0))
            c3.metric("Match SIM", fmt(r.get("casos_sim"), 0))
            c4.metric("Fila unificada", fmt(r.get("fila_unificada"), 0))
        if not link.empty:
            st.dataframe(link, use_container_width=True)
        if not proxy.empty:
            r = proxy.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Proxy lab positivo", fmt(r.get("proxy_lab_positivo"), 0), f"{fmt(r.get('proxy_lab_positivo_pct'))}%")
            c2.metric("Óbitos SINAN (proxy SIM)", fmt(r.get("proxy_obitos_sinan"), 0))
            c3.metric("Confirmados sem lab+ (fila GAL)", fmt(r.get("confirmados_sem_lab_positivo_proxy"), 0))
        fila_gal = read_any(OUT / "linkage_fila_busca_gal_lacen_v23.csv")
        if not fila_gal.empty:
            with st.expander("Fila prioritária para busca em GAL/LACEN"):
                st.dataframe(fila_gal.head(100), use_container_width=True)
        adw = read_any(OUT / "alertas_linkage_dw_v23.csv")
        if not adw.empty:
            with st.expander(f"Alertas linkage DW ({len(adw)})"):
                st.dataframe(adw.head(200), use_container_width=True)
        rel_fila = REL / "FILA_CIEVS_UNIFICADA_V23.md"
        if rel_fila.exists():
            with st.expander("Fila CIEVS unificada"):
                st.markdown(rel_fila.read_text(encoding="utf-8")[:6000])
        rel_link = REL / "LINKAGE_GAL_LACEN_SIM_V23.md"
        if rel_link.exists():
            with st.expander("Relatório de linkage"):
                st.markdown(rel_link.read_text(encoding="utf-8")[:5000])
        st.markdown("---")

    resumo = read_any(OUT / "qualidade_score_resumo_v20.csv")
    score = read_any(OUT / "qualidade_score_v20.csv")
    if not resumo.empty:
        r = resumo.iloc[0]
        st.metric("Pontuação total de qualidade do banco", f"{int(r['pontuacao_total'])}/20", r.get("qualidade_banco", ""))
        st.caption("Classificação: 18–20 Excelente; 14–17 Boa; 10–13 Regular; 6–9 Ruim; 0–5 Crítica.")
    if not score.empty:
        figq = px.bar(score, x="pontuacao", y="criterio", orientation="h", text="pontuacao", color="pontuacao",
                      title="Matriz de qualidade do banco — pontuação 0 a 2 por critério")
        figq.update_traces(textposition="outside")
        figq.update_layout(height=520, xaxis_title="Pontuação", yaxis_title="Critério")
        st.plotly_chart(figq, use_container_width=True, key=uid())
        st.dataframe(score, use_container_width=True)

    comp = read_any(OUT / "data_quality_completude_v17.csv")
    inc = read_any(OUT / "data_quality_inconsistencias_v17.csv")
    val = read_any(OUT / "validade_vpp_v17.csv")
    if not comp.empty and {"campo","completude_pct"}.issubset(comp.columns):
        bar_with_labels(comp.sort_values("completude_pct"), "completude_pct", "campo", "Completude por campo", orient="h", height=560)
        st.dataframe(comp, use_container_width=True)
    if not inc.empty:
        st.subheader("Inconsistências")
        st.dataframe(inc, use_container_width=True)
    if not val.empty:
        st.subheader("Validade/VPP operacional")
        st.dataframe(val, use_container_width=True)


def ms_indicators_section():
    """Indicadores oficiais MS (Informe Meningites / Caderno SINAN)."""
    painel = read_any(OUT / "indicadores_ms_operacionais_v23.csv")
    if painel.empty:
        st.warning("Rode: python 12_indicadores_ms_operacionais_v23.py (ou pipeline V23 --only-v23)")
        return

    st.caption(
        "Indicadores alinhados ao Informe Meningites 2024 (CGVDI/DPNI/SVSA/MS), "
        "Caderno de Análises SINAN e notificação compulsória ≤24h. "
        "Referência Brasil = SE 1–36/2024."
    )

    # Cards dos 4 KPIs principais do Informe
    core = {
        "pct_confirmacao_laboratorial_pcr_cultura": "Confirmação lab. PCR/cultura",
        "pct_investigados_48h": "Investigados ≤48h",
        "pct_encerrados_60d": "Encerrados ≤60 dias",
        "pct_quimioprofilaxia_dm_48h": "Quimio DM ≤48h",
    }
    cols = st.columns(4)
    for i, (ind, label) in enumerate(core.items()):
        row = painel[painel["indicador"].astype(str).eq(ind)]
        with cols[i]:
            if row.empty:
                mini_metric_card(label, "NA")
                continue
            r = row.iloc[0]
            val = r.get("valor_pct", np.nan)
            ref = r.get("referencia_brasil_2024", np.nan)
            sem = r.get("semaforo", "—")
            # delta vs BR: valor acima da meta = bom → higher_is_bad=False
            delta_pp = (float(val) - float(ref)) if pd.notna(val) and pd.notna(ref) else None
            st.markdown(
                f"""
                <div class="kpi-card" style="min-height:140px;">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-value" style="font-size:1.7rem;">{fmt(val)}%</div>
                  <div class="kpi-sub">Ref. BR: {fmt(ref) if pd.notna(ref) else "—"}%</div>
                  {kpi_delta_html(delta_pp, suffix=" pp vs BR", higher_is_bad=False) if delta_pp is not None else ""}
                  <div style="margin-top:8px;">{semaforo_badge(sem)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    show = painel.copy()
    if "valor_pct" in show.columns:
        fig = px.bar(
            show,
            x="valor_pct",
            y="indicador_rotulo",
            orientation="h",
            text=[fmt(v) for v in show["valor_pct"]],
            color="semaforo" if "semaforo" in show.columns else None,
            color_discrete_map=plotly_semaforo_map(show.get("semaforo")) if "semaforo" in show.columns else None,
            title="Painel de indicadores operacionais MS (%)",
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=max(480, 48 * len(show) + 120),
            xaxis_title="Percentual (%)",
            yaxis_title="",
            legend_title_text="Semáforo",
            margin=dict(l=20, r=40, t=70, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig, use_container_width=True, key=uid())
    st.dataframe(painel, use_container_width=True)

    ano = read_any(OUT / "indicadores_ms_operacionais_ano_v23.csv")
    if not ano.empty:
        st.subheader("Série anual dos indicadores MS")
        melt_cols = [c for c in ano.columns if c.startswith("pct_")]
        if melt_cols:
            long = ano.melt(id_vars=["ano_evento_v17"], value_vars=melt_cols, var_name="indicador", value_name="valor_pct")
            fig2 = px.line(
                long, x="ano_evento_v17", y="valor_pct", color="indicador",
                markers=True, title="Evolução anual — indicadores MS"
            )
            fig2.update_layout(height=480, xaxis_title="Ano", yaxis_title="Percentual (%)")
            st.plotly_chart(fig2, use_container_width=True, key=uid())
        st.dataframe(ano, use_container_width=True)

    reg = read_any(OUT / "indicadores_ms_operacionais_regional_v23.csv")
    if not reg.empty:
        st.subheader("Indicadores MS por regional")
        st.dataframe(reg.sort_values("pct_investigados_48h", ascending=True) if "pct_investigados_48h" in reg.columns else reg, use_container_width=True)

    mun = read_any(OUT / "indicadores_ms_operacionais_municipio_v23.csv")
    if not mun.empty:
        st.subheader("Indicadores MS por município (ordenado por pior investigação ≤48h)")
        if "pct_investigados_48h" in mun.columns:
            st.dataframe(mun.sort_values("pct_investigados_48h", ascending=True).head(50), use_container_width=True)
        else:
            st.dataframe(mun.head(50), use_container_width=True)


def smart_alerts_section():
    """Fila CIEVS + alertas de prazo e surto NT 97/2024."""
    fila = read_any(OUT / "alertas_inteligentes_fila_cievs_v23.csv")
    resumo = read_any(OUT / "alertas_inteligentes_resumo_v23.csv")
    casos = read_any(OUT / "alertas_inteligentes_casos_v23.csv")
    surtos = read_any(OUT / "alertas_inteligentes_surtos_nt97_v23.csv")

    if fila.empty and casos.empty and surtos.empty:
        st.warning("Rode: python 13_alertas_inteligentes_v23.py (ou pipeline V23 --only-v23)")
        return

    st.caption(
        "Alertas baseados em prazos do Informe MS, quimioprofilaxia (NT 97/2024) e "
        "definição de surto comunitário/institucional de doença meningocócica."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Itens na fila CIEVS", fmt(len(fila), 0))
    c2.metric("Alertas de caso", fmt(len(casos), 0))
    c3.metric("Sinais de surto NT97", fmt(len(surtos), 0))

    if not resumo.empty:
        st.subheader("Resumo por tipo")
        if {"tipo_alerta", "n"}.issubset(resumo.columns):
            fig = px.bar(
                resumo.sort_values("n", ascending=True).tail(20),
                x="n", y="tipo_alerta", color="severidade" if "severidade" in resumo.columns else None,
                color_discrete_map=plotly_semaforo_map(resumo.get("severidade")) if "severidade" in resumo.columns else None,
                orientation="h", text="n", title="Volume de alertas por tipo"
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                height=520, xaxis_title="N", yaxis_title="",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(b=80, t=60),
            )
            st.plotly_chart(fig, use_container_width=True, key=uid())
        st.dataframe(resumo, use_container_width=True)

    st.markdown("---")
    st.subheader("Fila prioritária CIEVS")
    if fila.empty:
        st.success("Nenhum item crítico/alto na fila no momento.")
    else:
        st.dataframe(fila, use_container_width=True)

    if not surtos.empty:
        st.subheader("Surtos / aglomerados — NT 97/2024")
        st.dataframe(surtos, use_container_width=True)

    if not casos.empty:
        st.subheader("Alertas de caso (filtráveis)")
        tipos = sorted(casos["tipo_alerta"].dropna().astype(str).unique()) if "tipo_alerta" in casos.columns else []
        sevs = sorted(casos["severidade"].dropna().astype(str).unique()) if "severidade" in casos.columns else []
        f1, f2 = st.columns(2)
        tsel = f1.multiselect("Tipo de alerta", tipos, default=[])
        ssel = f2.multiselect("Severidade", sevs, default=[s for s in sevs if s in ["Crítico", "Alto"]])
        view = casos.copy()
        if tsel:
            view = view[view["tipo_alerta"].astype(str).isin(tsel)]
        if ssel:
            view = view[view["severidade"].astype(str).isin(ssel)]
        st.dataframe(view.head(500), use_container_width=True)
        st.caption(f"Exibindo até 500 de {len(view)} alertas filtrados.")


def epi_panel_section():
    """Painel epidemiológico estilo Informe MS."""
    meta = read_any(OUT / "painel_epi_meta_v23.csv")
    resumo = read_any(OUT / "painel_epi_resumo_ano_v23.csv")
    if resumo.empty:
        st.warning("Rode: python 14_painel_epidemiologico_ms_v23.py (ou pipeline V23 --only-v23)")
        return

    ano_ref = int(meta.iloc[0]["ano_referencia"]) if not meta.empty else int(pd.to_numeric(resumo["ano_evento_v17"], errors="coerce").max())
    st.caption(
        f"Confirmados SINAN · incidência/mortalidade ×100 mil · letalidade (%). "
        f"Snapshot de referência: {ano_ref}. População municipal com carry-forward quando necessário."
    )

    row = resumo[resumo["ano_evento_v17"] == ano_ref]
    if row.empty:
        row = resumo.tail(1)
    r = row.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Confirmados", fmt(r.get("confirmados"), 0))
    c2.metric("Óbitos", fmt(r.get("obitos_meningite"), 0))
    c3.metric("Incidência /100 mil", fmt(r.get("incidencia_100mil")))
    c4.metric("Mortalidade /100 mil", fmt(r.get("mortalidade_100mil")))
    c5.metric("Letalidade %", fmt(r.get("letalidade_pct")))

    st.markdown("---")
    st.subheader("Série anual — incidência e letalidade")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=resumo["ano_evento_v17"], y=resumo["incidencia_100mil"], name="Incidência /100 mil", text=[fmt(v) for v in resumo["incidencia_100mil"]], textposition="outside"))
    fig.add_trace(go.Scatter(x=resumo["ano_evento_v17"], y=resumo["letalidade_pct"], name="Letalidade %", yaxis="y2", mode="lines+markers"))
    fig.update_layout(
        height=480,
        xaxis_title="Ano",
        yaxis_title="Incidência por 100 mil",
        yaxis2=dict(title="Letalidade (%)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        title="Incidência e letalidade — casos confirmados",
    )
    st.plotly_chart(fig, use_container_width=True, key=uid())
    st.dataframe(resumo, use_container_width=True)

    st.subheader("Mapa municipal + nowcast / forecast")
    em1, em2 = st.columns(2)
    with em1:
        ind_mun = read_any(OUT / "indicadores_municipio_ano_v17.csv")
        shp = load_shapefile()
        ll = load_latlong()
        if not ind_mun.empty and shp is not None:
            m = ind_mun[pd.to_numeric(ind_mun.get("ano_evento_v17"), errors="coerce").eq(ano_ref)].copy()
            if m.empty:
                m = ind_mun.copy()
            metric = "incidencia_100mil" if "incidencia_100mil" in m.columns else "casos"
            if metric in m.columns:
                choropleth_or_points(m, shp, ll, metric, f"Mapa — {metric} ({ano_ref})")
            else:
                st.info("Sem coluna de incidência/casos para o mapa.")
        else:
            st.info("Shapefile ou indicadores municipais indisponíveis.")
    with em2:
        nc24 = read_any(OUT / "nowcasting_operacional_v24.csv")
        fc24 = read_any(OUT / "forecasting_operacional_v24.csv")
        if not nc24.empty or not fc24.empty:
            plot_nowcast_forecast_historico("ESTADUAL", nc24, fc24)
        else:
            st.info("Nowcast/forecast indisponíveis — rode o módulo 24.")

    snap_eti = read_any(OUT / "painel_epi_snapshot_etiologia_v23.csv")
    if not snap_eti.empty:
        st.subheader(f"Etiologia — {ano_ref}")
        fig2 = px.bar(
            snap_eti.sort_values("casos", ascending=True),
            x="casos", y="classificacao_agrupada_v17", orientation="h",
            text="casos", color="letalidade_pct",
            title=f"Casos confirmados e letalidade por etiologia ({ano_ref})",
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(height=520, xaxis_title="Casos confirmados", yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True, key=uid())
        st.dataframe(snap_eti.sort_values("casos", ascending=False), use_container_width=True)

    snap_bact = read_any(OUT / "painel_epi_snapshot_bacterianas_v23.csv")
    if not snap_bact.empty:
        st.subheader(f"Meningites bacterianas — {ano_ref}")
        st.dataframe(snap_bact.sort_values("casos", ascending=False), use_container_width=True)

    snap_faixa = read_any(OUT / "painel_epi_snapshot_faixa_v23.csv")
    if not snap_faixa.empty:
        st.subheader(f"Faixa etária (padrão Informe MS) — {ano_ref}")
        fig3 = px.bar(
            snap_faixa, x="faixa_informe_v23", y="incidencia_100mil",
            text=[fmt(v) for v in snap_faixa["incidencia_100mil"]],
            title=f"Incidência por faixa etária ({ano_ref})",
        )
        fig3.update_layout(height=480, xaxis_title="Faixa etária", yaxis_title="Incidência /100 mil")
        st.plotly_chart(fig3, use_container_width=True, key=uid())
        st.dataframe(snap_faixa, use_container_width=True)

    mun = read_any(OUT / "painel_epi_municipio_ano_v23.csv")
    if not mun.empty:
        st.subheader(f"Municípios — incidência ({ano_ref})")
        m = mun[mun["ano_evento_v17"] == ano_ref].copy()
        if not m.empty and "incidencia_100mil" in m.columns:
            st.dataframe(m.sort_values("incidencia_100mil", ascending=False).head(40), use_container_width=True)


def assistant_section():
    """Assistente normativo CIEVS (RAG local + LLM opcional)."""
    st.caption(
        "Perguntas respondidas com recuperação de trechos da NT 97/2024, Informe Meningites, "
        "Caderno SINAN e Guia de Vigilância. Sempre valide com a equipe antes de comunicação oficial. "
        "LLM opcional (Gemini/OpenAI) se as chaves estiverem no `.env` local."
    )
    try:
        from conhecimento_ms_meningites_v23 import FAQ_RAPIDO
        from importlib import import_module
        assist = import_module("16_assistente_cievs_v23")
    except Exception as e:
        st.error(f"Assistente indisponível: {e}. Rode python 16_assistente_cievs_v23.py")
        return

    meta_p = OUT / "assistente_meta_v23.json"
    if meta_p.exists():
        try:
            import json
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            st.info(
                f"Base local: {meta.get('n_documentos_kb', '?')} documentos · "
                f"LLM: {'disponível' if meta.get('llm_disponivel') else 'offline (só RAG local)'}"
            )
        except Exception:
            pass

    narr = REL / "BOLETIM_SEMANAL_MENINGITES_V23_NARRATIVA_IA.md"
    if narr.exists():
        with st.expander("Narrativa assistida do boletim", expanded=False):
            st.markdown(narr.read_text(encoding="utf-8")[:12000])
            with open(narr, "rb") as fp:
                st.download_button("Baixar narrativa (.md)", fp, file_name=narr.name)

    sugestoes = [f["pergunta"] for f in FAQ_RAPIDO]
    escolha = st.selectbox("Perguntas rápidas", ["(digitar livremente)"] + sugestoes)
    pergunta = st.text_area(
        "Pergunta para o assistente",
        value="" if escolha.startswith("(") else escolha,
        height=90,
        placeholder="Ex.: O que fazer em caso de DM em escola? Quando é surto comunitário?",
    )
    usar_llm = st.checkbox("Tentar enriquecer com LLM (Gemini/OpenAI do .env)", value=False)
    if st.button("Consultar normas", type="primary") and pergunta.strip():
        with st.spinner("Recuperando normas e montando resposta..."):
            ctx = assist.build_contexto_operacional()
            resp = assist.answer(pergunta.strip(), contexto_dados=ctx, use_llm=usar_llm)
        st.markdown(resp.get("resposta", ""))
        if resp.get("fontes"):
            st.subheader("Fontes recuperadas")
            st.dataframe(pd.DataFrame(resp["fontes"]), use_container_width=True)
        if resp.get("aviso_llm"):
            st.warning(resp["aviso_llm"])

    kb = read_any(OUT / "assistente_kb_documentos_v23.csv")
    if not kb.empty:
        st.markdown("---")
        st.subheader("Documentos indexados")
        cols = [c for c in ["id", "titulo", "tema", "fonte"] if c in kb.columns]
        st.dataframe(kb[cols] if cols else kb, use_container_width=True)


def report_section(df):
    narr = REL / "BOLETIM_SEMANAL_MENINGITES_V23_NARRATIVA_IA.md"
    boletim = REL / "BOLETIM_SEMANAL_MENINGITES_V23_RASCUNHO.md"
    if narr.exists() or boletim.exists():
        st.subheader("Boletins V23")
        c1, c2 = st.columns(2)
        if boletim.exists():
            with open(boletim, "rb") as fp:
                c1.download_button("Baixar boletim rascunho (.md)", fp, file_name=boletim.name)
        if narr.exists():
            with open(narr, "rb") as fp:
                c2.download_button("Baixar narrativa assistida (.md)", fp, file_name=narr.name)
        if narr.exists():
            with st.expander("Prévia da narrativa assistida"):
                st.markdown(narr.read_text(encoding="utf-8")[:6000])
        elif boletim.exists():
            st.markdown(boletim.read_text(encoding="utf-8")[:8000])
        st.markdown("---")

    pdocx = REL / "RELATORIO_TECNICO_MENINGITES_CIEVS_MT_V18.docx"
    pmd = REL / "RELATORIO_TECNICO_MENINGITES_CIEVS_MT_V18.md"
    if pdocx.exists():
        with open(pdocx, "rb") as fp:
            st.download_button("Baixar relatório Word V18", fp, file_name=pdocx.name)
    if pmd.exists():
        st.markdown(pmd.read_text(encoding="utf-8"))
    st.subheader("Base filtrada")
    st.write(f"Linhas: {len(df):,}".replace(",", "."))
    st.write(f"Colunas: {df.shape[1]}")
    st.dataframe(df.head(1000), use_container_width=True)


def main():
    try:
        from meningites_env import load_meningites_env
        load_meningites_env()
    except Exception:
        pass

    inject_ui_css()
    base = load_base()
    if base.empty:
        st.error("Base V17/V18 ausente. Rode o pipeline completo.")
        st.stop()
    latlon = load_latlong()
    shapefile = load_shapefile()

    st.markdown(
        """
<div class="hero-band">
  <h1>Robô de Meningites — CIEVS-MT</h1>
  <p>Vigilância de meningites · Indicadores MS · Alertas CIEVS (NT 97/2024) · Clima×casos exploratório · Nowcast/forecast.</p>
</div>
        """,
        unsafe_allow_html=True,
    )
    if "demo_cloud" in str(OUT).replace("\\", "/"):
        st.warning(
            "Modo **demonstração / Streamlit Cloud**: dados anonimizados, sem acesso ao DW da SES-MT. "
            "Para operação completa use o painel local (porta 8510) após o pipeline."
        )

    # Idade da extração / fonte SINAN
    try:
        import json
        audit_p = OUT / "auditoria_sinan_fonte_v23.json"
        dw_p = OUT / "dw_descoberta_resumo_v23.json"
        bits = []
        if audit_p.exists():
            aud = json.loads(audit_p.read_text(encoding="utf-8"))
            fonte = aud.get("fonte_escolhida") or aud.get("fonte") or "?"
            gerado = aud.get("gerado_em") or ""
            bits.append(f"Fonte SINAN: **{fonte}**" + (f" · gerado {gerado}" if gerado else ""))
        if dw_p.exists():
            dwm = json.loads(dw_p.read_text(encoding="utf-8"))
            conn = dwm.get("conectado_em") or ""
            n = (dwm.get("extracoes") or {}).get("sinan_meningites_dw", {}).get("n")
            if conn:
                bits.append(f"DW: {conn}" + (f" · {n} linhas SINAN" if n is not None else ""))
        if bits:
            st.caption(" · ".join(bits) + " · Atualizar: `ATUALIZAR_MENINGITES.bat`")
    except Exception:
        pass

    with st.sidebar:
        st.header("Filtros globais")
        try:
            import json
            audit_p = OUT / "auditoria_sinan_fonte_v23.json"
            if audit_p.exists():
                aud = json.loads(audit_p.read_text(encoding="utf-8"))
                st.info(
                    f"Fonte: {aud.get('fonte_escolhida') or aud.get('fonte') or '?'}\n\n"
                    f"{aud.get('gerado_em') or ''}"
                )
        except Exception:
            pass
        anos = sorted(pd.to_numeric(base["ano_evento_v17"], errors="coerce").dropna().astype(int).unique()) if "ano_evento_v17" in base.columns else []
        ano_sel = st.multiselect("Ano", anos, default=[max(anos)] if anos else [])
        reg_sel = st.multiselect("Regional de Saúde", sorted(base["regional_v17"].dropna().astype(str).unique()) if "regional_v17" in base.columns else [], default=[])
        mun_sel = st.multiselect("Município", sorted(base["municipio_v17"].dropna().astype(str).unique()) if "municipio_v17" in base.columns else [], default=[])
        clas_sel = st.multiselect("Classificação agrupada", sorted(base["classificacao_agrupada_v17"].dropna().astype(str).unique()) if "classificacao_agrupada_v17" in base.columns else [], default=[])
        evo_sel = st.multiselect("Evolução", sorted(base["evolucao_padronizada_v17"].dropna().astype(str).unique()) if "evolucao_padronizada_v17" in base.columns else [], default=[])
        case_sel = st.multiselect("Classificação final do caso", sorted(base["classificacao_caso_padronizada_v17"].dropna().astype(str).unique()) if "classificacao_caso_padronizada_v17" in base.columns else [], default=[])

    df = base.copy()
    if ano_sel and "ano_evento_v17" in df.columns:
        df = df[df["ano_evento_v17"].isin(ano_sel)]
    if reg_sel and "regional_v17" in df.columns:
        df = df[df["regional_v17"].astype(str).isin(reg_sel)]
    if mun_sel and "municipio_v17" in df.columns:
        df = df[df["municipio_v17"].astype(str).isin(mun_sel)]
    if clas_sel and "classificacao_agrupada_v17" in df.columns:
        df = df[df["classificacao_agrupada_v17"].astype(str).isin(clas_sel)]
    if evo_sel and "evolucao_padronizada_v17" in df.columns:
        df = df[df["evolucao_padronizada_v17"].astype(str).isin(evo_sel)]
    if case_sel and "classificacao_caso_padronizada_v17" in df.columns:
        df = df[df["classificacao_caso_padronizada_v17"].astype(str).isin(case_sel)]

    tabs = st.tabs([
        "01 Executivo", "02 Indicadores MS", "03 Alertas CIEVS", "04 Painel Epidemiológico",
        "05 Assistente IA", "06 Mapas", "07 Estatística/OR", "08 Surtos", "09 Sazonalidade/Canal",
        "10 Projeções", "11 Geoespacial", "12 Laboratório", "13 Vacina",
        "14 Comorbidades", "15 Qualidade", "16 Relatório/Base", "17 Clima×casos",
    ])

    with tabs[0]:
        build_metric_cards(df)
        gest = read_any(OUT / "indicadores_gestao_semana_v24.csv")
        if not gest.empty:
            g = gest.iloc[0]
            st.markdown("---")
            st.subheader("Decisão da semana (gestão V24)")
            gcols = st.columns(5)
            with gcols[0]:
                mini_metric_card("Nowcast SE", fmt(g.get("casos_nowcast_se")), g.get("delta_nowcast_vs_se_anterior"), True)
            with gcols[1]:
                mini_metric_card("Nowcast DM", fmt(g.get("dm_nowcast_se")))
            with gcols[2]:
                mini_metric_card("Fila crítica", fmt(g.get("fila_cievs_criticos_n"), 0))
            with gcols[3]:
                mini_metric_card("Inv. 48h %", fmt(g.get("pct_investigados_48h")))
            with gcols[4]:
                mini_metric_card("Enc. 60d %", fmt(g.get("pct_encerrados_60d")))
            st.caption(f"{g.get('status_sazonal')} — {g.get('status_detalhe', '')}")
            st.write(g.get("acao_sugerida", ""))

        # Mapa + nowcast/forecast no executivo
        st.markdown("---")
        st.subheader("Território e projeções")
        m1, m2 = st.columns([1.05, 1])
        with m1:
            ind_full = read_any(OUT / "indicadores_municipio_ano_v17.csv")
            if not ind_full.empty and shapefile is not None:
                ind_map = ind_full.copy()
                if ano_sel and "ano_evento_v17" in ind_map.columns:
                    ind_map = ind_map[ind_map["ano_evento_v17"].isin(ano_sel)]
                latest = pd.to_numeric(ind_map["ano_evento_v17"], errors="coerce").max() if "ano_evento_v17" in ind_map.columns else np.nan
                mdf = ind_map[pd.to_numeric(ind_map["ano_evento_v17"], errors="coerce").eq(latest)].copy() if "ano_evento_v17" in ind_map.columns else ind_map.copy()
                if "casos" in mdf.columns:
                    choropleth_or_points(mdf, shapefile, latlon, "casos", "Casos por município")
                else:
                    st.info("Indicador municipal de casos indisponível para o mapa.")
            elif shapefile is None:
                st.warning("Shapefile não carregado — veja aba 06 Mapas.")
            else:
                st.info("Indicadores municipais indisponíveis para o mapa.")
        with m2:
            nc24 = read_any(OUT / "nowcasting_operacional_v24.csv")
            fc24 = read_any(OUT / "forecasting_operacional_v24.csv")
            if not nc24.empty or not fc24.empty:
                plot_nowcast_forecast_historico("ESTADUAL", nc24, fc24)
                st.caption("Detalhes e outros estratos na aba **10 Projeções**.")
            else:
                timeseries_cases(df)

        # Destaque rápido MS + fila
        ms_resumo = read_any(OUT / "indicadores_ms_operacionais_v23.csv")
        fila_ex = read_any(OUT / "alertas_inteligentes_fila_cievs_v23.csv")
        epi_ex = read_any(OUT / "painel_epi_resumo_ano_v23.csv")
        if not ms_resumo.empty or not fila_ex.empty or not epi_ex.empty:
            st.markdown("---")
            st.subheader("Painel MS e fila CIEVS (V23)")
            if not ms_resumo.empty:
                top4 = ms_resumo[ms_resumo["indicador"].isin([
                    "pct_confirmacao_laboratorial_pcr_cultura",
                    "pct_investigados_48h",
                    "pct_encerrados_60d",
                    "pct_quimioprofilaxia_dm_48h",
                ])]
                mcols = st.columns(4)
                for i, (_, r) in enumerate(top4.iterrows()):
                    if i < 4:
                        with mcols[i]:
                            sem = r.get("semaforo", "—")
                            st.markdown(
                                f"""
                                <div class="kpi-card" style="min-height:130px;">
                                  <div class="kpi-label">{str(r.get('indicador_rotulo', ''))[:48]}</div>
                                  <div class="kpi-value" style="font-size:1.55rem;">{fmt(r.get('valor_pct'))}%</div>
                                  <div style="margin-top:8px;">{semaforo_badge(sem)}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            if not epi_ex.empty:
                meta = read_any(OUT / "painel_epi_meta_v23.csv")
                ano_ref = int(meta.iloc[0]["ano_referencia"]) if not meta.empty else int(epi_ex["ano_evento_v17"].max())
                er = epi_ex[epi_ex["ano_evento_v17"] == ano_ref]
                if not er.empty:
                    e = er.iloc[0]
                    ecols = st.columns(3)
                    ecols[0].metric(f"Incidência {ano_ref} /100 mil", fmt(e.get("incidencia_100mil")))
                    ecols[1].metric(f"Letalidade {ano_ref} %", fmt(e.get("letalidade_pct")))
                    ecols[2].metric(f"Confirmados {ano_ref}", fmt(e.get("confirmados"), 0))
            if not fila_ex.empty:
                st.warning(f"{len(fila_ex)} item(ns) na fila prioritária CIEVS — ver aba 03 Alertas CIEVS.")
                st.dataframe(fila_ex.head(10), use_container_width=True)
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            timeseries_cases(df)
        with c2:
            sorogrupos_plot(df)
        st.markdown("---")
        socio_profile(df)
        st.markdown("---")
        # Destaque geral p<0,005 na aba executiva
        significant_alerts_from_frames([
            ("testes comparativos", read_any(OUT / "testes_comparativos_v17.csv")),
            ("OR classificação", read_any(OUT / "odds_classificacao_desfechos_v20.csv")),
            ("OR domínios", read_any(OUT / "odds_ratio_clinico_socio_comorb_v21.csv")),
            ("comorbidades", read_any(OUT / "associacoes_comorbidades_quiquadrado_v18.csv")),
        ], threshold=0.005, title="Achados prioritários com significância estatística forte")

    with tabs[1]:
        ms_indicators_section()

    with tabs[2]:
        smart_alerts_section()
        st.markdown("---")
        st.subheader("Alertas personalizados por regional / perfil")
        alertas_personalizados_section()

    with tabs[3]:
        epi_panel_section()

    with tabs[4]:
        assistant_section()

    with tabs[5]:
        if shapefile is not None:
            st.success(
                f"Malha municipal ativa: **{len(shapefile)}** municípios "
                f"(fonte `MT_Municipios_2024.shp` · mapas coropléticos)."
            )
        else:
            st.error(
                "Shapefile municipal não carregado. Verifique `MT_Municipios_2024.shp` na pasta do projeto "
                "e pressione **C** no app para limpar o cache."
            )
        ind_full = read_any(OUT / "indicadores_municipio_ano_v17.csv")
        if not ind_full.empty:
            ind_map = ind_full.copy()
            if ano_sel and "ano_evento_v17" in ind_map.columns:
                ind_map = ind_map[ind_map["ano_evento_v17"].isin(ano_sel)]
            latest = pd.to_numeric(ind_map["ano_evento_v17"], errors="coerce").max() if "ano_evento_v17" in ind_map.columns else np.nan
            m = ind_map[pd.to_numeric(ind_map["ano_evento_v17"], errors="coerce").eq(latest)].copy() if "ano_evento_v17" in ind_map.columns else ind_map.copy()
            mapas = [
                ("casos", "Mapa coroplético — casos"),
                ("confirmados", "Mapa coroplético — confirmados"),
                ("hospitalizacoes", "Mapa coroplético — hospitalizações"),
                ("obitos_meningite", "Mapa coroplético — óbitos por meningite"),
                ("incidencia_100mil", "Mapa coroplético — incidência por 100 mil"),
                ("mortalidade_100mil", "Mapa coroplético — mortalidade por 100 mil"),
                ("letalidade_confirmados", "Mapa coroplético — letalidade"),
            ]
            for i in range(0, len(mapas), 2):
                cols = st.columns(2)
                for j, (metric, title) in enumerate(mapas[i:i+2]):
                    with cols[j]:
                        if metric in m.columns:
                            choropleth_or_points(m, shapefile, latlon, metric, title)
            st.markdown("---")
            st.subheader("Séries históricas — independentes do filtro de ano")
            indicators_by_year(ind_full)
        else:
            st.info("Indicadores municipais não disponíveis.")

    with tabs[6]:
        st.subheader("Odds Ratio separado por domínio analítico")
        or_interpretation_guide()
        mort = read_any(OUT / "mortalidade_sinan_sim_resumo_v23.csv")
        if not mort.empty:
            r = mort.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Óbitos SINAN", fmt(r.get("obitos_sinan_evolucao"), 0))
            c2.metric("Óbitos SIM (link)", fmt(r.get("obitos_sim_linkage"), 0))
            c3.metric("União SINAN∪SIM", fmt(r.get("obitos_uniao_sinan_sim"), 0))
            c4.metric("SIM sem SINAN", fmt(r.get("obitos_sim_sem_sinan"), 0))
            st.caption(str(r.get("nota") or ""))
        ors21 = read_any(OUT / "odds_ratio_clinico_socio_comorb_v21.csv")
        if not ors21.empty:
            for dominio, titulo in [
                ("Clínico", "ODDS RATIO clínico — sinais e sintomas"),
                ("Sociodemográfico", "ODDS RATIO sociodemográfico"),
                ("Comorbidades", "ODDS RATIO de comorbidades"),
            ]:
                st.markdown(f"### {titulo}")
                sub = ors21[ors21["dominio"].astype(str).eq(dominio)].copy()
                forest_plot_or_labeled(sub, titulo)
                st.dataframe(sub.sort_values(["desfecho", "p_value"]) if "p_value" in sub.columns else sub, use_container_width=True)
        else:
            st.warning("Arquivo odds_ratio_clinico_socio_comorb_v21.csv não encontrado. Rode o pipeline V21 completo.")

        st.markdown("---")
        st.subheader("OR por classificação agrupada: óbito, internação e presença de comorbidades")
        or_class = read_any(OUT / "odds_classificacao_desfechos_v20.csv")
        if not or_class.empty:
            forest_plot_or_labeled(
                or_class.rename(columns={"classificacao_agrupada": "exposicao"}),
                "OR por classificação agrupada"
            )
            st.dataframe(or_class, use_container_width=True)

        tests = read_any(OUT / "testes_comparativos_v17.csv")
        if not tests.empty:
            st.subheader("Testes comparativos entre grupos")
            st.dataframe(tests, use_container_width=True)

    with tabs[7]:
        outbreak_section()

    with tabs[8]:
        sazonalidade_section()
        st.markdown("---")
        st.subheader("Canal endêmico")
        canal = read_any(OUT / "canal_endemico_classificacao_agrupada_v17.csv")
        if canal.empty:
            st.info("Canal endêmico indisponível.")
        else:
            for clas in sorted(canal["classificacao_agrupada_v17"].dropna().astype(str).unique()):
                canal_plot_visual(canal, clas)

    with tabs[9]:
        nowcast_refinado_section()
        st.markdown("---")
        st.subheader("Projeções diárias (ensemble V17)")
        fc = read_any(OUT / "forecasting_7_15_30_45_v17.csv")
        now21 = read_any(OUT / "nowcasting_desfechos_v21.csv")
        if not fc.empty:
            if "data_prevista" in fc.columns:
                fc["data_prevista"] = pd.to_datetime(fc["data_prevista"], errors="coerce")
            for des in ["casos", "hospitalizacoes", "obitos_meningite"]:
                forecast_nowcast_visual(df, fc, now21, des)
            fs = read_any(OUT / "forecasting_resumo_v17.csv")
            if not fs.empty:
                st.subheader("Resumo das projeções diárias")
                st.dataframe(fs, use_container_width=True)
        if not now21.empty:
            st.subheader("Nowcasting por desfecho (V21)")
            st.dataframe(now21, use_container_width=True)

    with tabs[10]:
        moran = read_any(OUT / "moran_global_v17.csv")
        lisa = read_any(OUT / "lisa_clusters_v17.csv")
        rank = read_any(OUT / "ranking_risco_territorial_v17.csv")
        if not moran.empty:
            st.dataframe(moran, use_container_width=True)
        if not rank.empty:
            choropleth_or_points(rank, shapefile, latlon, "score_risco", "Score de risco territorial")
        if not lisa.empty:
            st.dataframe(lisa, use_container_width=True)
        dist = read_any(OUT / "geoespacial_laboratorio_distancia_v20.csv")
        corr_dist = read_any(OUT / "correlacao_distancia_laboratorio_v20.csv")
        if not dist.empty:
            if "distancia_cuiaba_km" in dist.columns:
                dist["distancia_cuiaba_km"] = pd.to_numeric(dist["distancia_cuiaba_km"], errors="coerce")
                dist.loc[(dist["distancia_cuiaba_km"] < 0) | (dist["distancia_cuiaba_km"] > 2000), "distancia_cuiaba_km"] = np.nan
            st.subheader("Distância de Cuiabá x uso do laboratório")
            if {"distancia_cuiaba_km", "taxa_uso_laboratorio_pct"}.issubset(dist.columns):
                figd = px.scatter(
                    dist,
                    x="distancia_cuiaba_km",
                    y="taxa_uso_laboratorio_pct",
                    size="casos",
                    color="taxa_positividade_real_pct" if "taxa_positividade_real_pct" in dist.columns else None,
                    hover_name="municipio_v17",
                    title="Distância de Cuiabá e uso laboratorial"
                )
                figd.update_layout(height=520, xaxis_title="Distância de Cuiabá (km)", yaxis_title="Uso laboratorial (%)")
                st.plotly_chart(figd, use_container_width=True, key=uid())
            st.dataframe(dist.sort_values("distancia_cuiaba_km", ascending=False) if "distancia_cuiaba_km" in dist.columns else dist, use_container_width=True)
        if not corr_dist.empty:
            st.subheader("Correlação exploratória distância x laboratório")
            st.dataframe(corr_dist, use_container_width=True)

    with tabs[11]:
        lab_section(df)

    with tabs[12]:
        vaccine_section(df)

    with tabs[13]:
        comorb_section_v21()

    with tabs[14]:
        quality_section()

    with tabs[15]:
        report_section(df)

    with tabs[16]:
        climate_section()


if __name__ == "__main__":
    main()
