# -*- coding: utf-8 -*-
"""
12_indicadores_ms_operacionais_v23.py
Indicadores oficiais de vigilância das meningites (MS / Informe / Caderno SINAN).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from meningites_v17_common import OUT, MISSING, fmt_num, load_base_v17, text_key

# Referências Brasil 2024 (Informe Meningites CGVDI/DPNI/SVSA — SE 1–36/2024)
REF_BRASIL_2024 = {
    "pct_confirmacao_laboratorial_pcr_cultura": 36.1,
    "pct_investigados_48h": 97.8,
    "pct_encerrados_60d": 94.4,
    "pct_quimioprofilaxia_dm_48h": 45.5,
}

BACTERIANAS = {
    "Doença meningocócica",
    "Meningite tuberculosa",
    "Meningite bacteriana/outras bactérias",
    "Meningite por Hib/Hemófilo",
    "Meningite pneumocócica",
}

DM_HIB = {"Doença meningocócica", "Meningite por Hib/Hemófilo"}

# Caderno SINAN: cultura, CIE, PCR, látex | Informe 2024: RT-qPCR e cultura
LAB_CADENO = {"CULTURA", "CIE", "PCR", "LATEX", "LATEX", "AGLUTINACAO", "RT QPCR", "RTQPCR"}
LAB_INFORME = {"CULTURA", "PCR", "RT QPCR", "RTQPCR"}


def _filled(s: pd.Series) -> pd.Series:
    return s.notna() & ~s.astype(str).str.strip().str.lower().isin(MISSING)


def _ensure_lead_times(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "lt_notificacao_quimioprofilaxia_dias_v17" not in d.columns:
        if {"data_quimioprofilaxia_v17", "data_notificacao_v17"}.issubset(d.columns):
            qpx = pd.to_datetime(d["data_quimioprofilaxia_v17"], errors="coerce")
            notif = pd.to_datetime(d["data_notificacao_v17"], errors="coerce")
            d["lt_notificacao_quimioprofilaxia_dias_v17"] = (qpx - notif).dt.days
        else:
            d["lt_notificacao_quimioprofilaxia_dias_v17"] = np.nan
    for c in [
        "lt_notificacao_investigacao_dias_v17",
        "lt_notificacao_encerramento_dias_v17",
        "lt_notificacao_quimioprofilaxia_dias_v17",
        "lt_sintomas_notificacao_dias_v17",
    ]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def _criterio_lab_flags(serie: pd.Series) -> pd.DataFrame:
    keys = serie.fillna("").map(text_key)
    caderno = keys.map(lambda s: any(t in s for t in LAB_CADENO) if s else False)
    informe = keys.map(lambda s: any(t in s for t in LAB_INFORME) if s else False)
    # Códigos SINAN numéricos comuns
    code = serie.astype(str).str.extract(r"^(\d+)", expand=False)
    caderno = caderno | code.isin(["1", "01", "2", "02", "3", "03", "9", "09"])
    informe = informe | code.isin(["1", "01", "9", "09"])
    return pd.DataFrame({"lab_caderno": caderno, "lab_informe": informe})


def _quimio_realizada(df: pd.DataFrame) -> pd.Series:
    """Quimioprofilaxia realizada: data preenchida e/ou campo sim/não."""
    has_date = pd.Series(False, index=df.index)
    if "data_quimioprofilaxia_v17" in df.columns:
        has_date = pd.to_datetime(df["data_quimioprofilaxia_v17"], errors="coerce").notna()
    if "lt_notificacao_quimioprofilaxia_dias_v17" in df.columns:
        has_date = has_date | pd.to_numeric(df["lt_notificacao_quimioprofilaxia_dias_v17"], errors="coerce").notna()

    # Campo SINAN explícito (nome observado na base MT)
    prefer = [c for c in ["RealizaQuimioprofilaxiaComunicantes", "RealizouQuimioprofilaxiaComunicantes"] if c in df.columns]
    col_candidates = prefer + [
        c for c in df.columns
        if "quimio" in c.lower()
        and not c.lower().startswith(("lt_", "data"))
        and "data" not in c.lower()
        and not c.endswith("_bin_v17")
        and c not in prefer
    ]
    bin_flag = pd.Series(False, index=df.index)
    for c in col_candidates:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            bin_flag = bin_flag | (pd.to_numeric(s, errors="coerce") == 1)
        else:
            k = s.astype(str).map(text_key)
            bin_flag = bin_flag | k.isin(["1", "1 0", "SIM", "S"])
    return has_date | bin_flag


def _pct(num, den):
    if den is None or den == 0 or pd.isna(den):
        return np.nan
    return float(num) / float(den) * 100


def _semaforo_vs_ref(valor, ref, higher_better=True, tol=5.0):
    if pd.isna(valor) or pd.isna(ref):
        return "Cinza"
    if higher_better:
        if valor >= ref:
            return "Verde"
        if valor >= ref - tol:
            return "Amarelo"
        return "Vermelho"
    if valor <= ref:
        return "Verde"
    if valor <= ref + tol:
        return "Amarelo"
    return "Vermelho"


def compute_ms_kpis(df: pd.DataFrame) -> dict:
    d = _ensure_lead_times(df)
    n = len(d)
    conf = pd.to_numeric(d.get("confirmado_v17", 0), errors="coerce").fillna(0).astype(int)
    clas = d.get("classificacao_agrupada_v17", pd.Series(index=d.index, dtype=object)).astype(str)

    # 1) Confirmação laboratorial (bacterianas confirmadas)
    bact_mask = (conf == 1) & clas.isin(BACTERIANAS)
    n_bact = int(bact_mask.sum())
    if "CriterioConfirmacao" in d.columns:
        flags = _criterio_lab_flags(d.loc[bact_mask, "CriterioConfirmacao"] if n_bact else pd.Series(dtype=object))
        n_lab_cad = int(flags["lab_caderno"].sum()) if n_bact else 0
        n_lab_inf = int(flags["lab_informe"].sum()) if n_bact else 0
    else:
        n_lab_cad = n_lab_inf = 0

    # 2) Investigação ≤48h
    lt_inv = pd.to_numeric(d.get("lt_notificacao_investigacao_dias_v17"), errors="coerce")
    inv_valid = lt_inv.notna() & (lt_inv >= 0) & (lt_inv < 365)
    n_inv48 = int((inv_valid & (lt_inv <= 2)).sum())
    n_inv_den = int(inv_valid.sum())  # entre os com data; também reportamos / total

    # 3) Encerramento ≤60d
    lt_enc = pd.to_numeric(d.get("lt_notificacao_encerramento_dias_v17"), errors="coerce")
    enc_valid = lt_enc.notna() & (lt_enc >= 0) & (lt_enc < 800)
    n_enc60 = int((enc_valid & (lt_enc <= 60)).sum())
    n_enc_den = int(enc_valid.sum())

    # 4) Quimioprofilaxia DM ≤48h
    dm = clas.eq("Doença meningocócica")
    n_dm = int(dm.sum())
    lt_q = pd.to_numeric(d.get("lt_notificacao_quimioprofilaxia_dias_v17"), errors="coerce")
    q_ok = dm & lt_q.notna() & (lt_q >= 0) & (lt_q <= 2)
    n_q48 = int(q_ok.sum())
    q_realizada = _quimio_realizada(d)
    n_q_any = int((dm & q_realizada).sum())

    # 4b) Quimioprofilaxia Hib ≤48h (NT 97)
    hib = clas.eq("Meningite por Hib/Hemófilo")
    n_hib = int(hib.sum())
    n_hib_q48 = int((hib & lt_q.notna() & (lt_q >= 0) & (lt_q <= 2)).sum())
    n_hib_q_any = int((hib & q_realizada).sum())

    # Extra: notificação ≤24h (compulsória imediata)
    lt_notif = pd.to_numeric(d.get("lt_sintomas_notificacao_dias_v17"), errors="coerce")
    notif_valid = lt_notif.notna() & (lt_notif >= 0) & (lt_notif < 365)
    n_notif24 = int((notif_valid & (lt_notif <= 1)).sum())

    # Extra: % sorogrupo identificado (DM)
    soro_col = next((c for c in d.columns if "sorogrupo" in c.lower() or "SeNMeningiditis" in c), None)
    n_soro = 0
    if soro_col and n_dm:
        s = d.loc[dm, soro_col].astype(str)
        filled = _filled(s) & ~s.map(text_key).isin(["", "IGNORADO", "IGNORADO SEM INFORMACAO", "9", "99"])
        n_soro = int(filled.sum())

    # Quimio indevida (fora DM/Hib)
    quimio_indevida = int((q_realizada & ~clas.isin(DM_HIB)).sum())

    return {
        "total_notificacoes": n,
        "total_confirmados": int(conf.sum()),
        "bact_confirmadas": n_bact,
        "bact_lab_caderno": n_lab_cad,
        "bact_lab_informe_pcr_cultura": n_lab_inf,
        "pct_confirmacao_laboratorial_caderno": _pct(n_lab_cad, n_bact),
        "pct_confirmacao_laboratorial_pcr_cultura": _pct(n_lab_inf, n_bact),
        "investigados_com_data": n_inv_den,
        "investigados_48h": n_inv48,
        "pct_investigados_48h_entre_com_data": _pct(n_inv48, n_inv_den),
        "pct_investigados_48h": _pct(n_inv48, n),
        "encerrados_com_data": n_enc_den,
        "encerrados_60d": n_enc60,
        "pct_encerrados_60d_entre_com_data": _pct(n_enc60, n_enc_den),
        "pct_encerrados_60d": _pct(n_enc60, n),
        "dm_casos": n_dm,
        "dm_quimio_qualquer": n_q_any,
        "dm_quimio_48h": n_q48,
        "pct_quimioprofilaxia_dm_48h": _pct(n_q48, n_dm),
        "pct_quimioprofilaxia_dm_qualquer": _pct(n_q_any, n_dm),
        "hib_casos": n_hib,
        "hib_quimio_48h": n_hib_q48,
        "hib_quimio_qualquer": n_hib_q_any,
        "pct_quimioprofilaxia_hib_48h": _pct(n_hib_q48, n_hib),
        "pct_notificacao_24h": _pct(n_notif24, int(notif_valid.sum()) or n),
        "pct_sorogrupo_identificado_dm": _pct(n_soro, n_dm),
        "quimioprofilaxia_indevida_n": quimio_indevida,
    }


def kpis_to_frame(kpis: dict) -> pd.DataFrame:
    rows = [
        {
            "indicador": "pct_confirmacao_laboratorial_pcr_cultura",
            "indicador_rotulo": "% confirmação laboratorial (PCR/cultura) — Informe MS",
            "numerador": kpis["bact_lab_informe_pcr_cultura"],
            "denominador": kpis["bact_confirmadas"],
            "valor_pct": kpis["pct_confirmacao_laboratorial_pcr_cultura"],
            "referencia_brasil_2024": REF_BRASIL_2024["pct_confirmacao_laboratorial_pcr_cultura"],
            "semaforo": _semaforo_vs_ref(
                kpis["pct_confirmacao_laboratorial_pcr_cultura"],
                REF_BRASIL_2024["pct_confirmacao_laboratorial_pcr_cultura"],
            ),
            "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS",
            "interpretacao": (
                f"{fmt_num(kpis['pct_confirmacao_laboratorial_pcr_cultura'])}% das meningites bacterianas "
                f"confirmadas encerradas com PCR ou cultura (ref. BR 36,1%)."
            ),
        },
        {
            "indicador": "pct_confirmacao_laboratorial_caderno",
            "indicador_rotulo": "% confirmação laboratorial (cultura/CIE/PCR/látex) — Caderno SINAN",
            "numerador": kpis["bact_lab_caderno"],
            "denominador": kpis["bact_confirmadas"],
            "valor_pct": kpis["pct_confirmacao_laboratorial_caderno"],
            "referencia_brasil_2024": np.nan,
            "semaforo": _semaforo_vs_ref(kpis["pct_confirmacao_laboratorial_caderno"], 70.0),
            "fonte": "Caderno de Análises SINAN — Meningites",
            "interpretacao": (
                f"{fmt_num(kpis['pct_confirmacao_laboratorial_caderno'])}% com critério laboratorial "
                f"ampliado (cultura/CIE/PCR/látex)."
            ),
        },
        {
            "indicador": "pct_investigados_48h",
            "indicador_rotulo": "% casos investigados em até 48h da notificação",
            "numerador": kpis["investigados_48h"],
            "denominador": kpis["total_notificacoes"],
            "valor_pct": kpis["pct_investigados_48h"],
            "referencia_brasil_2024": REF_BRASIL_2024["pct_investigados_48h"],
            "semaforo": _semaforo_vs_ref(
                kpis["pct_investigados_48h"], REF_BRASIL_2024["pct_investigados_48h"], tol=3.0
            ),
            "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS",
            "interpretacao": (
                f"{fmt_num(kpis['pct_investigados_48h'])}% investigados ≤48h "
                f"(entre com data: {fmt_num(kpis['pct_investigados_48h_entre_com_data'])}%)."
            ),
        },
        {
            "indicador": "pct_encerrados_60d",
            "indicador_rotulo": "% casos encerrados em até 60 dias da notificação",
            "numerador": kpis["encerrados_60d"],
            "denominador": kpis["total_notificacoes"],
            "valor_pct": kpis["pct_encerrados_60d"],
            "referencia_brasil_2024": REF_BRASIL_2024["pct_encerrados_60d"],
            "semaforo": _semaforo_vs_ref(
                kpis["pct_encerrados_60d"], REF_BRASIL_2024["pct_encerrados_60d"], tol=3.0
            ),
            "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS",
            "interpretacao": (
                f"{fmt_num(kpis['pct_encerrados_60d'])}% encerrados ≤60 dias "
                f"(entre com data: {fmt_num(kpis['pct_encerrados_60d_entre_com_data'])}%)."
            ),
        },
        {
            "indicador": "pct_quimioprofilaxia_dm_48h",
            "indicador_rotulo": "% doença meningocócica com quimioprofilaxia ≤48h",
            "numerador": kpis["dm_quimio_48h"],
            "denominador": kpis["dm_casos"],
            "valor_pct": kpis["pct_quimioprofilaxia_dm_48h"],
            "referencia_brasil_2024": REF_BRASIL_2024["pct_quimioprofilaxia_dm_48h"],
            "semaforo": _semaforo_vs_ref(
                kpis["pct_quimioprofilaxia_dm_48h"],
                REF_BRASIL_2024["pct_quimioprofilaxia_dm_48h"],
                tol=5.0,
            ),
            "fonte": "Informe Meningites 2024 — CGVDI/DPNI/SVSA/MS; NT 97/2024",
            "interpretacao": (
                f"{fmt_num(kpis['pct_quimioprofilaxia_dm_48h'])}% dos casos de DM com quimio ≤48h "
                f"(qualquer quimio registrada: {fmt_num(kpis['pct_quimioprofilaxia_dm_qualquer'])}%)."
            ),
        },
        {
            "indicador": "pct_quimioprofilaxia_hib_48h",
            "indicador_rotulo": "% meningite Hib/Hemófilo com quimioprofilaxia ≤48h",
            "numerador": kpis["hib_quimio_48h"],
            "denominador": kpis["hib_casos"],
            "valor_pct": kpis["pct_quimioprofilaxia_hib_48h"],
            "referencia_brasil_2024": np.nan,
            "semaforo": _semaforo_vs_ref(kpis["pct_quimioprofilaxia_hib_48h"], 45.5, tol=5.0) if kpis["hib_casos"] else "Cinza",
            "fonte": "NT 97/2024 — quimioprofilaxia em Hib",
            "interpretacao": (
                f"{fmt_num(kpis['pct_quimioprofilaxia_hib_48h'])}% dos casos Hib com quimio ≤48h "
                f"(n={kpis['hib_casos']}; qualquer quimio: {fmt_num(_pct(kpis['hib_quimio_qualquer'], kpis['hib_casos']))}%)."
            ),
        },
        {
            "indicador": "pct_sorogrupo_identificado_dm",
            "indicador_rotulo": "% DM com sorogrupo identificado",
            "numerador": int(round(kpis["pct_sorogrupo_identificado_dm"] / 100 * kpis["dm_casos"])) if kpis["dm_casos"] else 0,
            "denominador": kpis["dm_casos"],
            "valor_pct": kpis["pct_sorogrupo_identificado_dm"],
            "referencia_brasil_2024": np.nan,
            "semaforo": _semaforo_vs_ref(kpis["pct_sorogrupo_identificado_dm"], 70.0),
            "fonte": "Guia de Vigilância / monitoramento de sorogrupos",
            "interpretacao": f"Sorogrupo preenchido em {fmt_num(kpis['pct_sorogrupo_identificado_dm'])}% dos casos de DM.",
        },
        {
            "indicador": "pct_notificacao_24h",
            "indicador_rotulo": "% notificação em até 24h do início dos sintomas",
            "numerador": np.nan,
            "denominador": kpis["total_notificacoes"],
            "valor_pct": kpis["pct_notificacao_24h"],
            "referencia_brasil_2024": np.nan,
            "semaforo": _semaforo_vs_ref(kpis["pct_notificacao_24h"], 80.0),
            "fonte": "Notificação compulsória imediata (≤24h)",
            "interpretacao": f"{fmt_num(kpis['pct_notificacao_24h'])}% com lead time sintomas→notificação ≤1 dia.",
        },
    ]
    out = pd.DataFrame(rows)
    out["quimioprofilaxia_indevida_n"] = kpis["quimioprofilaxia_indevida_n"]
    return out


def by_geo(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    d = _ensure_lead_times(df)
    present = [k for k in keys if k in d.columns]
    if not present:
        return pd.DataFrame()
    rows = []
    for vals, g in d.groupby(present, dropna=False):
        if not isinstance(vals, tuple):
            vals = (vals,)
        kpis = compute_ms_kpis(g)
        row = {k: v for k, v in zip(present, vals)}
        row.update({
            "total_notificacoes": kpis["total_notificacoes"],
            "pct_confirmacao_laboratorial_pcr_cultura": kpis["pct_confirmacao_laboratorial_pcr_cultura"],
            "pct_investigados_48h": kpis["pct_investigados_48h"],
            "pct_encerrados_60d": kpis["pct_encerrados_60d"],
            "pct_quimioprofilaxia_dm_48h": kpis["pct_quimioprofilaxia_dm_48h"],
            "dm_casos": kpis["dm_casos"],
            "quimioprofilaxia_indevida_n": kpis["quimioprofilaxia_indevida_n"],
        })
        rows.append(row)
    return pd.DataFrame(rows)


def by_ano(df: pd.DataFrame) -> pd.DataFrame:
    if "ano_evento_v17" not in df.columns:
        return pd.DataFrame()
    rows = []
    for ano, g in df.groupby("ano_evento_v17", dropna=False):
        kpis = compute_ms_kpis(g)
        rows.append({
            "ano_evento_v17": ano,
            "total_notificacoes": kpis["total_notificacoes"],
            "pct_confirmacao_laboratorial_pcr_cultura": kpis["pct_confirmacao_laboratorial_pcr_cultura"],
            "pct_confirmacao_laboratorial_caderno": kpis["pct_confirmacao_laboratorial_caderno"],
            "pct_investigados_48h": kpis["pct_investigados_48h"],
            "pct_encerrados_60d": kpis["pct_encerrados_60d"],
            "pct_quimioprofilaxia_dm_48h": kpis["pct_quimioprofilaxia_dm_48h"],
            "pct_sorogrupo_identificado_dm": kpis["pct_sorogrupo_identificado_dm"],
            "pct_notificacao_24h": kpis["pct_notificacao_24h"],
            "dm_casos": kpis["dm_casos"],
        })
    return pd.DataFrame(rows).sort_values("ano_evento_v17")


def main():
    df = load_base_v17()
    if df.empty:
        raise SystemExit("Base ausente.")

    df = _ensure_lead_times(df)
    # Não regrava a base completa aqui (OneDrive/CSV grande). Lead time de quimio
    # é calculado em memória via _ensure_lead_times.

    kpis = compute_ms_kpis(df)
    painel = kpis_to_frame(kpis)
    painel.to_csv(OUT / "indicadores_ms_operacionais_v23.csv", index=False, encoding="utf-8-sig")

    resumo = pd.DataFrame([kpis])
    resumo.to_csv(OUT / "indicadores_ms_operacionais_resumo_v23.csv", index=False, encoding="utf-8-sig")

    by_ano(df).to_csv(OUT / "indicadores_ms_operacionais_ano_v23.csv", index=False, encoding="utf-8-sig")
    by_geo(df, ["regional_v17"]).to_csv(OUT / "indicadores_ms_operacionais_regional_v23.csv", index=False, encoding="utf-8-sig")
    by_geo(df, ["codigo_municipio_v17", "municipio_v17", "regional_v17"]).to_csv(
        OUT / "indicadores_ms_operacionais_municipio_v23.csv", index=False, encoding="utf-8-sig"
    )

    print("[OK] Indicadores MS operacionais V23 gerados.")
    print(painel[["indicador_rotulo", "valor_pct", "referencia_brasil_2024", "semaforo"]].to_string(index=False))


if __name__ == "__main__":
    main()
