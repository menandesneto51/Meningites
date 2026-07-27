# -*- coding: utf-8 -*-
"""
01_kpis_semanais_meningites_v17.py
KPIs da semana fechada, semáforo e comparação com semana anterior.
"""

from datetime import date, timedelta
import numpy as np
import pandas as pd
from meningites_v17_common import *

def previous_epi_week(ano, semana):
    monday = date.fromisocalendar(int(ano), int(semana), 1)
    prev = monday - timedelta(days=7)
    iso = prev.isocalendar()
    return int(iso.year), int(iso.week)

def closed_week(df):
    max_date = df["data_ref_v17"].max()
    ref = max_date - pd.Timedelta(days=7)
    iso = ref.isocalendar()
    return int(iso.year), int(iso.week)

def pct(a, b):
    if pd.isna(b) or b == 0:
        return np.nan if a != 0 else 0.0
    return (a - b) / b * 100

def semaforo(var):
    if pd.isna(var):
        return "Cinza"
    if var > 5:
        return "Vermelho"
    if var < -5:
        return "Verde"
    return "Amarelo"

def main():
    df = load_base_v17()
    for c in ["ano_epi_v17", "semana_epi_v17", "caso_v17", "confirmado_v17", "hospitalizacao_v17", "obito_meningite_v17", "alta_v17"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    wk = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        altas=("alta_v17", "sum"),
    ).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])
    wk["letalidade_confirmados"] = wk["obitos_meningite"] / wk["confirmados"].replace(0, np.nan) * 100

    ano, se = closed_week(df)
    ap, sp = previous_epi_week(ano, se)
    cur = wk[(wk["ano_epi_v17"] == ano) & (wk["semana_epi_v17"] == se)]
    prev = wk[(wk["ano_epi_v17"] == ap) & (wk["semana_epi_v17"] == sp)]
    cur = cur.iloc[0].to_dict() if not cur.empty else {}
    prev = prev.iloc[0].to_dict() if not prev.empty else {}

    labels = {
        "casos": "Casos",
        "confirmados": "Confirmados",
        "hospitalizacoes": "Hospitalizações",
        "obitos_meningite": "Óbitos por meningite",
        "altas": "Altas",
        "letalidade_confirmados": "Letalidade entre confirmados (%)",
    }
    rows = []
    for m, lab in labels.items():
        a = float(cur.get(m, np.nan))
        b = float(prev.get(m, np.nan))
        v = pct(a, b)
        rows.append({
            "ano_epi_atual_fechado": ano,
            "semana_epi_atual_fechada": se,
            "ano_epi_semana_anterior": ap,
            "semana_epi_anterior": sp,
            "indicador": m,
            "indicador_rotulo": lab,
            "valor_atual_fechado": a,
            "valor_semana_anterior": b,
            "variacao_absoluta": a - b if pd.notna(a) and pd.notna(b) else np.nan,
            "variacao_percentual": v,
            "semaforo": semaforo(v),
            "interpretacao": f"{lab}: {semaforo(v).lower()} ({fmt_num(v)}% vs semana anterior)."
        })
    out = pd.DataFrame(rows)
    wk.to_csv(OUT / "resumo_semanal_v17.csv", index=False, encoding="utf-8-sig")
    out.to_csv(OUT / "kpis_semanais_v17.csv", index=False, encoding="utf-8-sig")
    print("[OK] KPIs V17 gerados.")
    print(out.to_string(index=False))

if __name__ == "__main__":
    main()
