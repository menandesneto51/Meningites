# -*- coding: utf-8 -*-
"""
33_sih_subnotificacao_v33.py
Sinal de subnotificação e gravidade hospitalar: SIH (VW_INTERNACAO) × SINAN meningite.

Entrada: entradas_linkage/sih_internacoes_meningite.csv (módulo 19)
Saídas (saida_meningites_v17/):
  - sih_internacoes_prep_v33.csv
  - sih_sinan_linkage_v33.csv
  - sih_fila_investigacao_v33.csv  (SIH sem par SINAN — lista acionável)
  - sih_kpis_subnotificacao_v33.csv
  - sih_contagens_ano_mun_v33.csv
  - sih_fonte_meta_v33.json
  - relatorios/SIH_SUBNOTIFICACAO_V33.md

Linkage (heurístico — sem chave AIH↔NU_NOTIFICACAO no extrato DW):
  1. Município IBGE-6: CodigoMunicipioResidencia (fallback Ocorrencia) × codigo_municipio_v17
  2. Sexo normalizado (M/F)
  3. Idade em anos ±1
  4. Janela temporal: data_internacao_v17 (fallback data_ref_v17) vs âncora SIH
     (dia 15 do mês AnoInternacao/MesInternacao) ± JANELA_DIAS (padrão 30)

A view pode vir agregada (NumeroInternacoes > 1): cada unidade de internação
vira um "slot" no matching guloso. Não inventa chaves nominais.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, ROOT, load_base_v17, norm_code6, text_key

ENTRADAS = ROOT / "entradas_linkage"
SIH_PATH = ENTRADAS / "sih_internacoes_meningite.csv"
JANELA_DIAS = 30
IDADE_TOL = 1

CID_PREFIXES = ("A39", "G00", "G01", "G02", "G03", "A87")


def _pct(num, den) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return float("nan")
    return float(num) / float(den) * 100.0


def _read_sih() -> pd.DataFrame:
    if not SIH_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(SIH_PATH, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(SIH_PATH, encoding="latin1", low_memory=False)


def cid_meningite(serie: pd.Series) -> pd.Series:
    s = serie.fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    return s.map(lambda x: any(x.startswith(p) for p in CID_PREFIXES))


def _norm_sexo(x) -> str:
    t = text_key(x)
    if not t:
        return ""
    if t.startswith("M") or t in {"1", "MASCULINO"}:
        return "M"
    if t.startswith("F") or t in {"2", "FEMININO"}:
        return "F"
    return t[:1]


def _parse_idade_anos(x) -> float:
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x) if float(x) >= 0 else np.nan
    s = str(x).strip()
    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not m:
        return np.nan
    return float(m.group(1).replace(",", "."))


def _mes_num(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x)
    m = re.search(r"(\d{1,2})", s)
    if m:
        v = int(m.group(1))
        return float(v) if 1 <= v <= 12 else np.nan
    mapa = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }
    t = text_key(s)[:3]
    return float(mapa[t]) if t in mapa else np.nan


def _bin_flag(x) -> int:
    t = text_key(x)
    if t in {"1", "SIM", "S", "TRUE", "VERDADEIRO"}:
        return 1
    if t in {"0", "2", "NAO", "N", "FALSE", "FALSO"}:
        return 0
    try:
        v = float(str(x).replace(",", "."))
        if v > 0:
            return 1
    except Exception:
        pass
    return 0


def preparar_sih(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    d = raw.copy()
    # Filtro CID defensivo (caso extrato venha amplo)
    diag = d["DiagnosticoPrincipal"] if "DiagnosticoPrincipal" in d.columns else pd.Series("", index=d.index)
    cod = d["CodigoDiagnosticoPrincipal"] if "CodigoDiagnosticoPrincipal" in d.columns else pd.Series("", index=d.index)
    mask = cid_meningite(diag) | cid_meningite(cod)
    if mask.any():
        d = d.loc[mask].copy()
    d = d.reset_index(drop=True)
    diag = d["DiagnosticoPrincipal"] if "DiagnosticoPrincipal" in d.columns else pd.Series("", index=d.index)
    cod = d["CodigoDiagnosticoPrincipal"] if "CodigoDiagnosticoPrincipal" in d.columns else pd.Series("", index=d.index)
    cid = cod.fillna(diag).astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    d["cid_principal_v33"] = cid.where(cid.ne(""), diag.astype(str))

    cod_res = d["CodigoMunicipioResidencia"] if "CodigoMunicipioResidencia" in d.columns else pd.Series(np.nan, index=d.index)
    cod_ocr = d["CodigoMunicipioOcorrencia"] if "CodigoMunicipioOcorrencia" in d.columns else pd.Series(np.nan, index=d.index)
    d["codigo_municipio_v33"] = cod_res.map(norm_code6)
    d["codigo_municipio_v33"] = d["codigo_municipio_v33"].fillna(cod_ocr.map(norm_code6))
    mun_res = d["MunicipioResidencia"] if "MunicipioResidencia" in d.columns else pd.Series("", index=d.index)
    mun_ocr = d["MunicipioOcorrencia"] if "MunicipioOcorrencia" in d.columns else pd.Series("", index=d.index)
    d["municipio_v33"] = mun_res.where(mun_res.notna() & (mun_res.astype(str).str.strip() != ""), mun_ocr)
    d["municipio_key_v33"] = d["municipio_v33"].map(text_key)

    d["sexo_v33"] = d["Sexo"].map(_norm_sexo) if "Sexo" in d.columns else ""
    d["idade_anos_v33"] = d["Idade"].map(_parse_idade_anos) if "Idade" in d.columns else np.nan
    d["ano_internacao_v33"] = pd.to_numeric(d["AnoInternacao"], errors="coerce") if "AnoInternacao" in d.columns else np.nan
    d["mes_internacao_v33"] = d["MesInternacao"].map(_mes_num) if "MesInternacao" in d.columns else np.nan
    anos = d["ano_internacao_v33"].fillna(2000).astype(int).clip(1900, 2100)
    meses = d["mes_internacao_v33"].fillna(6).astype(int).clip(1, 12)
    d["data_ancora_sih_v33"] = pd.to_datetime(
        {"year": anos, "month": meses, "day": 15},
        errors="coerce",
    )
    d.loc[d["ano_internacao_v33"].isna(), "data_ancora_sih_v33"] = pd.NaT

    if "NumeroInternacoes" in d.columns:
        n_int = pd.to_numeric(d["NumeroInternacoes"], errors="coerce")
    else:
        n_int = pd.Series(np.nan, index=d.index)
    d["n_internacoes_v33"] = n_int.fillna(1).clip(lower=1).astype(int)
    d["teve_uti_v33"] = d["TeveDiariasUTI"].map(_bin_flag) if "TeveDiariasUTI" in d.columns else 0
    if "DiariasUTI" in d.columns:
        diarias = pd.to_numeric(d["DiariasUTI"], errors="coerce").fillna(0)
        d["teve_uti_v33"] = ((d["teve_uti_v33"] == 1) | (diarias > 0)).astype(int)
    d["obito_hospitalar_v33"] = d["FoiAObito"].map(_bin_flag) if "FoiAObito" in d.columns else 0
    if "NumeroObitos" in d.columns:
        nob = pd.to_numeric(d["NumeroObitos"], errors="coerce").fillna(0)
        d["obito_hospitalar_v33"] = ((d["obito_hospitalar_v33"] == 1) | (nob > 0)).astype(int)
    if "PermanenciaDias" in d.columns:
        d["permanencia_dias_v33"] = pd.to_numeric(d["PermanenciaDias"], errors="coerce")
    elif "DiasDePermanencia" in d.columns:
        d["permanencia_dias_v33"] = pd.to_numeric(d["DiasDePermanencia"], errors="coerce")
    else:
        d["permanencia_dias_v33"] = np.nan
    d["sih_row_id_v33"] = np.arange(len(d), dtype=int)
    return d


def preparar_sinan(base: pd.DataFrame) -> pd.DataFrame:
    if base is None or base.empty:
        return pd.DataFrame()
    d = base.copy()
    d["codigo_municipio_v33"] = d.get("codigo_municipio_v17", d.get("CodigoMunicipioResidencia")).map(norm_code6)
    d["sexo_v33"] = d["SexoPaciente"].map(_norm_sexo) if "SexoPaciente" in d.columns else ""
    d["idade_anos_v33"] = d["IdadePaciente"].map(_parse_idade_anos) if "IdadePaciente" in d.columns else np.nan
    di = pd.to_datetime(d["data_internacao_v17"], errors="coerce") if "data_internacao_v17" in d.columns else pd.Series(pd.NaT, index=d.index)
    dr = pd.to_datetime(d["data_ref_v17"], errors="coerce") if "data_ref_v17" in d.columns else pd.Series(pd.NaT, index=d.index)
    d["data_ancora_sinan_v33"] = di.fillna(dr)
    d["ano_evento_v33"] = pd.to_numeric(d.get("ano_evento_v17"), errors="coerce")
    d["municipio_v33"] = d.get("municipio_v17", d.get("MunicipioResidencia"))
    keep = [
        "NumeroNotificacao", "codigo_municipio_v33", "municipio_v33", "sexo_v33",
        "idade_anos_v33", "data_ancora_sinan_v33", "ano_evento_v33",
        "classificacao_agrupada_v17", "regional_v17",
    ]
    keep = [c for c in keep if c in d.columns]
    out = d[keep].copy()
    out["sinan_row_id_v33"] = np.arange(len(out), dtype=int)
    return out


def expandir_slots_sih(sih: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por unidade de internação (respeita NumeroInternacoes)."""
    if sih.empty:
        return sih
    reps = sih["n_internacoes_v33"].astype(int).clip(lower=1)
    if int(reps.sum()) > 500_000:
        print("[AVISO] NumeroInternacoes muito alto — usando 1 slot por linha agregada.")
        slots = sih.copy()
        slots["slot_ix_v33"] = 0
        slots["sih_slot_id_v33"] = slots["sih_row_id_v33"].astype(str) + "_0"
        return slots.reset_index(drop=True)
    slots = sih.loc[sih.index.repeat(reps)].copy().reset_index(drop=True)
    slots["slot_ix_v33"] = slots.groupby("sih_row_id_v33").cumcount()
    slots["sih_slot_id_v33"] = (
        slots["sih_row_id_v33"].astype(str) + "_" + slots["slot_ix_v33"].astype(str)
    )
    return slots


def linkage_sih_sinan(
    sih_slots: pd.DataFrame,
    sinan: pd.DataFrame,
    janela_dias: int = JANELA_DIAS,
    idade_tol: int = IDADE_TOL,
) -> pd.DataFrame:
    """
    Matching guloso por bloco município+sexo.
    Score: idade compatível + proximidade temporal (menor delta ganha).
    """
    if sih_slots.empty:
        return pd.DataFrame()
    cols_out = list(sih_slots.columns) + [
        "match_sinan_v33", "NumeroNotificacao_match", "sinan_row_id_match",
        "delta_dias_v33", "motivo_match_v33",
    ]
    if sinan.empty:
        out = sih_slots.copy()
        out["match_sinan_v33"] = 0
        out["NumeroNotificacao_match"] = pd.NA
        out["sinan_row_id_match"] = pd.NA
        out["delta_dias_v33"] = np.nan
        out["motivo_match_v33"] = "sem_base_sinan"
        return out[cols_out] if set(cols_out).issubset(out.columns) else out

    used_sinan: set[int] = set()
    rows = []
    # blocos
    sih_slots = sih_slots.copy()
    sih_slots["_blk"] = (
        sih_slots["codigo_municipio_v33"].fillna("").astype(str)
        + "|"
        + sih_slots["sexo_v33"].fillna("").astype(str)
    )
    sinan = sinan.copy()
    sinan["_blk"] = (
        sinan["codigo_municipio_v33"].fillna("").astype(str)
        + "|"
        + sinan["sexo_v33"].fillna("").astype(str)
    )
    sinan_by = {k: g for k, g in sinan.groupby("_blk", sort=False)}

    for _, srow in sih_slots.iterrows():
        blk = srow["_blk"]
        cand = sinan_by.get(blk)
        best = None
        best_delta = None
        motivo = ""
        if cand is not None and srow.get("codigo_municipio_v33") and srow.get("sexo_v33"):
            for _, crow in cand.iterrows():
                sid = int(crow["sinan_row_id_v33"])
                if sid in used_sinan:
                    continue
                idade_ok = True
                if pd.notna(srow.get("idade_anos_v33")) and pd.notna(crow.get("idade_anos_v33")):
                    idade_ok = abs(float(srow["idade_anos_v33"]) - float(crow["idade_anos_v33"])) <= idade_tol
                else:
                    idade_ok = False
                if not idade_ok:
                    continue
                ds = srow.get("data_ancora_sih_v33")
                dn = crow.get("data_ancora_sinan_v33")
                if pd.isna(ds) or pd.isna(dn):
                    continue
                delta = abs((pd.Timestamp(ds) - pd.Timestamp(dn)).days)
                if delta > janela_dias:
                    continue
                if best is None or delta < best_delta:
                    best = crow
                    best_delta = delta
                    motivo = f"mun+sexo+idade±{idade_tol}+janela{janela_dias}d"
        rec = srow.drop(labels=["_blk"]).to_dict()
        if best is not None:
            used_sinan.add(int(best["sinan_row_id_v33"]))
            rec["match_sinan_v33"] = 1
            rec["NumeroNotificacao_match"] = best.get("NumeroNotificacao")
            rec["sinan_row_id_match"] = int(best["sinan_row_id_v33"])
            rec["delta_dias_v33"] = float(best_delta)
            rec["motivo_match_v33"] = motivo
        else:
            rec["match_sinan_v33"] = 0
            rec["NumeroNotificacao_match"] = pd.NA
            rec["sinan_row_id_match"] = pd.NA
            rec["delta_dias_v33"] = np.nan
            rec["motivo_match_v33"] = "sem_par_sinan"
        rows.append(rec)
    return pd.DataFrame(rows)


def kpis(link: pd.DataFrame, sinan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if link.empty:
        return pd.DataFrame()
    n_sih = int(len(link))
    n_match = int(link["match_sinan_v33"].sum())
    n_sem = n_sih - n_match
    n_uti = int(link["teve_uti_v33"].sum()) if "teve_uti_v33" in link.columns else 0
    n_obito = int(link["obito_hospitalar_v33"].sum()) if "obito_hospitalar_v33" in link.columns else 0
    rows.append({
        "escopo": "ESTADUAL",
        "recorte": "MT",
        "n_internacoes_sih": n_sih,
        "n_match_sinan": n_match,
        "n_sih_sem_sinan": n_sem,
        "pct_sih_sem_sinan": _pct(n_sem, n_sih),
        "pct_match_sinan": _pct(n_match, n_sih),
        "n_com_uti": n_uti,
        "pct_uti": _pct(n_uti, n_sih),
        "n_obito_hospitalar": n_obito,
        "pct_obito_hospitalar": _pct(n_obito, n_sih),
        "n_casos_sinan": int(len(sinan)) if sinan is not None else 0,
        "janela_dias": JANELA_DIAS,
        "idade_tol": IDADE_TOL,
    })
    # por ano
    if "ano_internacao_v33" in link.columns:
        for ano, g in link.groupby(link["ano_internacao_v33"].dropna().astype(int)):
            ns = int(len(g))
            nm = int(g["match_sinan_v33"].sum())
            rows.append({
                "escopo": "ANO",
                "recorte": str(int(ano)),
                "n_internacoes_sih": ns,
                "n_match_sinan": nm,
                "n_sih_sem_sinan": ns - nm,
                "pct_sih_sem_sinan": _pct(ns - nm, ns),
                "pct_match_sinan": _pct(nm, ns),
                "n_com_uti": int(g["teve_uti_v33"].sum()) if "teve_uti_v33" in g.columns else 0,
                "pct_uti": _pct(int(g["teve_uti_v33"].sum()), ns) if "teve_uti_v33" in g.columns else np.nan,
                "n_obito_hospitalar": int(g["obito_hospitalar_v33"].sum()) if "obito_hospitalar_v33" in g.columns else 0,
                "pct_obito_hospitalar": _pct(int(g["obito_hospitalar_v33"].sum()), ns) if "obito_hospitalar_v33" in g.columns else np.nan,
                "n_casos_sinan": np.nan,
                "janela_dias": JANELA_DIAS,
                "idade_tol": IDADE_TOL,
            })
    return pd.DataFrame(rows)


def contagens_ano_mun(link: pd.DataFrame) -> pd.DataFrame:
    if link.empty:
        return pd.DataFrame()
    gcols = ["ano_internacao_v33", "codigo_municipio_v33", "municipio_v33"]
    gcols = [c for c in gcols if c in link.columns]
    if not gcols:
        return pd.DataFrame()
    cnt_col = "sih_slot_id_v33" if "sih_slot_id_v33" in link.columns else "sih_row_id_v33"
    agg = (
        link.groupby(gcols, dropna=False)
        .agg(
            n_internacoes_sih=(cnt_col, "count"),
            n_match_sinan=("match_sinan_v33", "sum"),
            n_com_uti=("teve_uti_v33", "sum"),
            n_obito_hospitalar=("obito_hospitalar_v33", "sum"),
        )
        .reset_index()
    )
    agg["n_sih_sem_sinan"] = agg["n_internacoes_sih"] - agg["n_match_sinan"]
    agg["pct_sih_sem_sinan"] = [
        _pct(a, b) for a, b in zip(agg["n_sih_sem_sinan"], agg["n_internacoes_sih"])
    ]
    sort_cols = [c for c in ["ano_internacao_v33", "n_sih_sem_sinan"] if c in agg.columns]
    return agg.sort_values(sort_cols, ascending=[False, False]) if sort_cols else agg


def write_meta(sih_raw_n: int, prep_n: int, slots_n: int, kpis_df: pd.DataFrame, disponivel: bool, msg: str) -> Path:
    meta = {
        "modulo": "33_sih_subnotificacao_v33.py",
        "fonte_extrato": str(SIH_PATH.name),
        "disponivel": disponivel,
        "mensagem": msg,
        "n_linhas_extrato": int(sih_raw_n),
        "n_linhas_prep": int(prep_n),
        "n_slots_internacao": int(slots_n),
        "janela_dias": JANELA_DIAS,
        "idade_tol": IDADE_TOL,
        "cids": list(CID_PREFIXES),
        "linkage": (
            "Heurístico mun(IBGE-6)+sexo+idade±1+janela dias em torno de "
            "AnoInternacao/MesInternacao (dia 15) × data_internacao_v17/data_ref_v17. "
            "Sem chave AIH↔notificação."
        ),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
    if not kpis_df.empty:
        est = kpis_df[kpis_df["escopo"].astype(str).eq("ESTADUAL")]
        if not est.empty:
            meta["kpis_estaduais"] = {k: (None if pd.isna(v) else v) for k, v in est.iloc[0].to_dict().items()}
    path = OUT / "sih_fonte_meta_v33.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def write_report(kpis_df: pd.DataFrame, cont: pd.DataFrame, disponivel: bool, msg: str) -> Path:
    REL.mkdir(exist_ok=True)
    lines = [
        "# SIH × SINAN — subnotificação hospitalar V33",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Sinal de vigilância: internações SIH com CID de meningite "
        "(A39/G00–G03/A87) confrontadas ao SINAN por heurística "
        "(município + sexo + idade ±1 + janela temporal). "
        "**Não substitui** investigação caso a caso; não há chave AIH↔NU_NOTIFICACAO no extrato.",
        "",
        f"**Status:** {'disponível' if disponivel else 'indisponível'} — {msg}",
        "",
    ]
    if not kpis_df.empty:
        est = kpis_df[kpis_df["escopo"].astype(str).eq("ESTADUAL")]
        lines += ["## KPIs estaduais", "", est.to_string(index=False), ""]
        anos = kpis_df[kpis_df["escopo"].astype(str).eq("ANO")]
        if not anos.empty:
            lines += ["## Por ano", "", anos.to_string(index=False), ""]
    if not cont.empty:
        lines += [
            "## Top municípios (SIH sem par SINAN)",
            "",
            cont.head(20).to_string(index=False),
            "",
        ]
    lines += [
        "## Como regenerar",
        "",
        "```bat",
        "py -3.13 19_dw_descobrir_e_extrair_v23.py",
        "py -3.13 33_sih_subnotificacao_v33.py",
        "```",
        "",
    ]
    path = REL / "SIH_SUBNOTIFICACAO_V33.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(exist_ok=True)
    REL.mkdir(exist_ok=True)
    raw = _read_sih()
    if raw.empty:
        msg = (
            f"{SIH_PATH.name} ausente — rode o módulo 19 com DW "
            "(VW_INTERNACAO / SIH_DW_*) para extrair."
        )
        print(f"[INFO] {msg}")
        vazios = {
            "sih_internacoes_prep_v33.csv": [
                "cid_principal_v33", "codigo_municipio_v33", "municipio_v33",
                "sexo_v33", "idade_anos_v33", "ano_internacao_v33",
                "teve_uti_v33", "obito_hospitalar_v33",
            ],
            "sih_sinan_linkage_v33.csv": [
                "sih_slot_id_v33", "match_sinan_v33", "NumeroNotificacao_match",
                "delta_dias_v33", "motivo_match_v33",
            ],
            "sih_fila_investigacao_v33.csv": [
                "sih_slot_id_v33", "codigo_municipio_v33", "municipio_v33",
                "sexo_v33", "idade_anos_v33", "ano_internacao_v33",
                "teve_uti_v33", "obito_hospitalar_v33", "cid_principal_v33",
                "motivo_match_v33", "acao_sugerida_v33",
            ],
            "sih_kpis_subnotificacao_v33.csv": [
                "escopo", "recorte", "n_internacoes_sih", "n_match_sinan",
                "n_sih_sem_sinan", "pct_sih_sem_sinan", "pct_match_sinan",
                "n_com_uti", "pct_uti", "n_obito_hospitalar", "pct_obito_hospitalar",
                "n_casos_sinan", "janela_dias", "idade_tol",
            ],
            "sih_contagens_ano_mun_v33.csv": [
                "ano_internacao_v33", "codigo_municipio_v33", "municipio_v33",
                "n_internacoes_sih", "n_match_sinan", "n_sih_sem_sinan",
                "pct_sih_sem_sinan", "n_com_uti", "n_obito_hospitalar",
            ],
        }
        for nome, cols in vazios.items():
            pd.DataFrame(columns=cols).to_csv(OUT / nome, index=False, encoding="utf-8-sig")
        write_meta(0, 0, 0, pd.DataFrame(), disponivel=False, msg=msg)
        write_report(pd.DataFrame(), pd.DataFrame(), disponivel=False, msg=msg)
        return 0

    prep = preparar_sih(raw)
    slots = expandir_slots_sih(prep)
    try:
        base = load_base_v17()
    except Exception as e:
        print(f"[AVISO] Base SINAN indisponível ({e}); linkage só com SIH.")
        base = pd.DataFrame()
    sinan = preparar_sinan(base)
    link = linkage_sih_sinan(slots, sinan)
    kdf = kpis(link, sinan)
    cont = contagens_ano_mun(link)

    # export sem colunas nominais óbvias
    drop_pii = [c for c in prep.columns if re.search(r"nome|cns|mae|endereco|telefone|doc_|bairro|cep", c, re.I)]
    prep.drop(columns=drop_pii, errors="ignore").to_csv(
        OUT / "sih_internacoes_prep_v33.csv", index=False, encoding="utf-8-sig"
    )
    link_drop = [c for c in link.columns if re.search(r"nome|cns|mae|endereco|telefone|doc_|bairro|cep", c, re.I)]
    link_clean = link.drop(columns=link_drop, errors="ignore")
    link_clean.to_csv(OUT / "sih_sinan_linkage_v33.csv", index=False, encoding="utf-8-sig")

    # Lista operacional: SIH sem par heurístico no SINAN (investigação de subnotificação)
    fila_cols = [
        c for c in [
            "sih_slot_id_v33", "codigo_municipio_v33", "municipio_v33",
            "sexo_v33", "idade_anos_v33", "ano_internacao_v33",
            "data_ancora_sih_v33", "teve_uti_v33", "obito_hospitalar_v33",
            "cid_principal_v33", "motivo_match_v33",
        ] if c in link_clean.columns
    ]
    if "match_sinan_v33" in link_clean.columns:
        fila = link_clean.loc[
            pd.to_numeric(link_clean["match_sinan_v33"], errors="coerce").fillna(0).astype(int).eq(0),
            fila_cols,
        ].copy()
    else:
        fila = pd.DataFrame(columns=fila_cols)
    fila["acao_sugerida_v33"] = "Investigar notificação SINAN / revisão ficha hospitalar"
    sort_keys = [c for c in ["ano_internacao_v33", "obito_hospitalar_v33", "teve_uti_v33", "municipio_v33"] if c in fila.columns]
    if sort_keys and not fila.empty:
        fila = fila.sort_values(
            sort_keys,
            ascending=[False if c != "municipio_v33" else True for c in sort_keys],
        )
    fila.to_csv(OUT / "sih_fila_investigacao_v33.csv", index=False, encoding="utf-8-sig")

    kdf.to_csv(OUT / "sih_kpis_subnotificacao_v33.csv", index=False, encoding="utf-8-sig")
    cont.to_csv(OUT / "sih_contagens_ano_mun_v33.csv", index=False, encoding="utf-8-sig")
    msg = f"Extrato com {len(raw)} linhas · {len(slots)} slots de internação · fila SIH-sem-SINAN={len(fila)}"
    write_meta(len(raw), len(prep), len(slots), kdf, disponivel=True, msg=msg)
    write_report(kdf, cont, disponivel=True, msg=msg)

    print(
        f"[OK] SIH×SINAN V33: {len(slots)} internações · "
        f"match={int(link['match_sinan_v33'].sum())} · fila_investigacao={len(fila)}"
    )
    if not kdf.empty:
        print(kdf[kdf["escopo"].astype(str).eq("ESTADUAL")].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
