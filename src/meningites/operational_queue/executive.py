"""Visão executiva regional e estadual do Meningites VNext.

Agrega somente fatos já publicados pelo VNext. Não cria novos limiares.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


PRIORITY_WEIGHT = {"crítica": 4, "critica": 4, "alta": 3, "moderada": 2, "atenção": 2, "atencao": 2, "informativa": 1}


def _municipality_region_map(indicators: pd.DataFrame) -> pd.DataFrame:
    if indicators.empty or not {"codigo_municipio", "regional"}.issubset(indicators.columns):
        return pd.DataFrame(columns=["codigo_municipio", "regional"])
    m = indicators[["codigo_municipio", "regional"]].copy()
    m["codigo_municipio"] = m["codigo_municipio"].astype(str)
    m["regional"] = m["regional"].fillna("").astype(str).str.strip()
    m = m[~m["regional"].str.lower().isin({"", "nan", "none", "<na>"})]
    if m.empty:
        return pd.DataFrame(columns=["codigo_municipio", "regional"])
    return (
        m.groupby("codigo_municipio", as_index=False)["regional"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
    )


def build_executive_views(
    situation: pd.DataFrame,
    signals: pd.DataFrame,
    indicators: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    region_map = _municipality_region_map(indicators)
    sit = situation.copy()
    if not sit.empty:
        sit["codigo_municipio"] = sit["codigo_municipio"].astype(str)
        sit = sit.merge(region_map, on="codigo_municipio", how="left")
        sit["regional"] = sit["regional"].fillna("Sem regional")

    sig = signals.copy()
    if not sig.empty:
        sig["codigo_municipio"] = sig["codigo_municipio"].astype(str)
        sig = sig.merge(region_map, on="codigo_municipio", how="left")
        sig["regional"] = sig["regional"].fillna("Sem regional")
        sig["peso_prioridade"] = sig["prioridade"].astype(str).str.lower().map(PRIORITY_WEIGHT).fillna(0)

    regional_rows = []
    regionals = sorted(set(sit["regional"])) if not sit.empty else []
    for regional in regionals:
        sreg = sit[sit["regional"].eq(regional)]
        greg = sig[sig["regional"].eq(regional)] if not sig.empty else pd.DataFrame()
        regional_rows.append({
            "regional": regional,
            "municipios_com_contexto_n": int(sreg["codigo_municipio"].nunique()),
            "municipios_com_sinal_n": int(greg["codigo_municipio"].nunique()) if not greg.empty else 0,
            "sinais_n": int(len(greg)),
            "sinais_alta_ou_critica_n": int((greg["peso_prioridade"] >= 3).sum()) if not greg.empty else 0,
            "fila_cievs_n": float(pd.to_numeric(sreg.get("fila_cievs_n"), errors="coerce").fillna(0).sum()) if "fila_cievs_n" in sreg else 0,
            "gal_tipagem_pendente_n": float(pd.to_numeric(sreg.get("gal_tipagem_pendente_n"), errors="coerce").fillna(0).sum()) if "gal_tipagem_pendente_n" in sreg else 0,
            "sih_sem_sinan_n": float(pd.to_numeric(sreg.get("sih_sem_sinan_n"), errors="coerce").fillna(0).sum()) if "sih_sem_sinan_n" in sreg else 0,
            "redcap_sem_sinan_n": float(pd.to_numeric(sreg.get("redcap_sem_sinan_n"), errors="coerce").fillna(0).sum()) if "redcap_sem_sinan_n" in sreg else 0,
        })

    regional = pd.DataFrame(regional_rows)
    state = pd.DataFrame([{
        "escopo": "Mato Grosso",
        "municipios_com_contexto_n": int(sit["codigo_municipio"].nunique()) if not sit.empty else 0,
        "municipios_com_sinal_n": int(sig["codigo_municipio"].nunique()) if not sig.empty else 0,
        "sinais_n": int(len(sig)),
        "sinais_alta_ou_critica_n": int((sig["peso_prioridade"] >= 3).sum()) if not sig.empty else 0,
        "regionais_com_sinal_n": int(sig["regional"].nunique()) if not sig.empty else 0,
        "regionais_sem_mapeamento_n": int((regional["regional"] == "Sem regional").sum()) if not regional.empty else 0,
    }])
    return regional, state
