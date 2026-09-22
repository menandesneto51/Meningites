# -*- coding: utf-8 -*-
"""
32_gal_laboratorio_detalhado_v32.py
Enriquece a vigilância com resultados laboratoriais do GAL (além do match binário).

Entrada: entradas_linkage/gal_lacen_meningites.csv (já extraído pelo módulo 19)
Saídas:
  - gal_exames_meningite_v32.csv          (exames filtrados + flags)
  - gal_tipagem_nm_hib_v32.csv            (tipagem Nm/Hi por notificação)
  - gal_kpis_laboratorio_v32.csv          (KPIs estaduais/regionais)
  - gal_sinan_concordancia_lab_v32.csv    (SINAN × GAL por caso)
  - gal_tempo_coleta_liberacao_v32.csv    (oportunidade lab)
  - gal_fila_tipagem_sinan_v32.csv        (tipagem GAL → atualizar sorogrupo SINAN)
  - relatorios/GAL_LABORATORIO_DETALHADO_V32.md

Âncora: Informe Meningites (confirmação lab) + NT 154/2024 (sorogrupo para surto).
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, ROOT, load_base_v17, text_key

ENTRADAS = ROOT / "entradas_linkage"
GAL_PATH = ENTRADAS / "gal_lacen_meningites.csv"

EXAME_MENING = re.compile(
    r"meningite|neisseria|haemophilus|liquor|lcr|pneumoniae.*mening|"
    r"bact[eé]rias.*cultura|bact[eé]rias.*identific",
    re.I,
)
METODO_PCR = re.compile(r"pcr|biologia molecular|rt-?pcr", re.I)
METODO_CULTURA = re.compile(r"cultura", re.I)
METODO_LATEX = re.compile(r"l[aá]tex", re.I)


def _read_gal() -> pd.DataFrame:
    if not GAL_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(GAL_PATH, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(GAL_PATH, encoding="latin1", low_memory=False)


def _join_resultados(row: pd.Series) -> str:
    parts = []
    for c in [
        "Campo_Resultado_1", "Campo_Resultado_2", "Campo_Resultado_3",
        "Campo_Resultado_4", "Campo_Resultado_5", "Campo_Resultado_6",
        "Observacao_Resultado",
    ]:
        if c in row.index and pd.notna(row[c]):
            parts.append(str(row[c]))
    return " | ".join(parts)


def _parse_flags(texto: str) -> dict:
    t = texto or ""
    tl = t.lower()
    detect_nm = bool(re.search(r"neisseria meningitidis:\s*detect", tl))
    nao_nm = bool(re.search(r"neisseria meningitidis:\s*n[aã]o detect", tl))
    detect_hi = bool(re.search(r"haemophilus influenzae:\s*detect", tl))
    nao_hi = bool(re.search(r"haemophilus influenzae:\s*n[aã]o detect", tl))
    m_grupo = re.search(r"grupo\s*[–\-—]?\s*neisseria meningitidis:\s*([a-zwy/?]+)", tl)
    sorogrupo = m_grupo.group(1).strip().upper() if m_grupo else ""
    if sorogrupo in {"", "NAN", "NONE"}:
        sorogrupo = ""
    # positivo lab amplo
    positivo = False
    if detect_nm or detect_hi:
        positivo = True
    if re.search(r"microrganismo isolado:\s*\S+", tl) and "isolado:  " not in tl:
        if not re.search(r"n[aã]o\s+isolado|sem crescimento", tl):
            positivo = True
    if "detectável" in tl and "não detectável" not in tl and "nao detectavel" not in tl:
        positivo = True
    if "houve crescimento" in tl and "microbiota habitual" not in tl:
        positivo = True
    return {
        "gal_nm_detectavel_v32": int(detect_nm),
        "gal_nm_nao_detectavel_v32": int(nao_nm),
        "gal_hi_detectavel_v32": int(detect_hi),
        "gal_hi_nao_detectavel_v32": int(nao_hi),
        "gal_sorogrupo_nm_v32": sorogrupo,
        "gal_lab_positivo_v32": int(positivo),
    }


def preparar_exames(gal: pd.DataFrame) -> pd.DataFrame:
    g = gal.copy()
    g["exame_txt"] = g["Exame"].map(lambda x: "" if pd.isna(x) else str(x)) if "Exame" in g.columns else ""
    g["metodologia_txt"] = g["Metodologia"].map(lambda x: "" if pd.isna(x) else str(x)) if "Metodologia" in g.columns else ""
    g["status_txt"] = g["Status_Exame"].map(lambda x: "" if pd.isna(x) else str(x)) if "Status_Exame" in g.columns else ""
    g["meningite_relevante_v32"] = g["exame_txt"].map(lambda x: bool(EXAME_MENING.search(str(x or ""))))
    g = g[g["meningite_relevante_v32"]].copy()
    if g.empty:
        return g

    g["resultado_texto_v32"] = g.apply(_join_resultados, axis=1)
    flags = g["resultado_texto_v32"].map(_parse_flags).apply(pd.Series)
    for c in flags.columns:
        g[c] = flags[c].fillna(0).values if c.startswith("gal_") and c != "gal_sorogrupo_nm_v32" else flags[c].fillna("").values
    if "gal_sorogrupo_nm_v32" in g.columns:
        g["gal_sorogrupo_nm_v32"] = g["gal_sorogrupo_nm_v32"].fillna("").astype(str)
    for c in [
        "gal_nm_detectavel_v32", "gal_nm_nao_detectavel_v32",
        "gal_hi_detectavel_v32", "gal_hi_nao_detectavel_v32", "gal_lab_positivo_v32",
    ]:
        if c in g.columns:
            g[c] = pd.to_numeric(g[c], errors="coerce").fillna(0).astype(int)

    g["gal_pcr_v32"] = g["metodologia_txt"].map(lambda x: int(bool(METODO_PCR.search(str(x or "")))))
    g["gal_cultura_v32"] = g["metodologia_txt"].map(lambda x: int(bool(METODO_CULTURA.search(str(x or "")))))
    g["gal_latex_v32"] = g["metodologia_txt"].map(lambda x: int(bool(METODO_LATEX.search(str(x or "")))))
    g["gal_liberado_v32"] = g["status_txt"].map(
        lambda x: int("LIBERADO" in text_key(str(x or "")))
    )

    for c in ["Data_Coleta_dt", "Data_Coleta", "Data_Liberacao_dt", "Data_Liberacao"]:
        if c in g.columns:
            g[c] = pd.to_datetime(g[c], errors="coerce", dayfirst=True)
    col_c = "Data_Coleta_dt" if "Data_Coleta_dt" in g.columns else "Data_Coleta"
    col_l = "Data_Liberacao_dt" if "Data_Liberacao_dt" in g.columns else "Data_Liberacao"
    if col_c in g.columns and col_l in g.columns:
        g["lt_coleta_liberacao_dias_v32"] = (g[col_l] - g[col_c]).dt.days
    else:
        g["lt_coleta_liberacao_dias_v32"] = np.nan

    if "Num_Notificacao_Sinan" in g.columns:
        g["numero_notificacao"] = (
            g["Num_Notificacao_Sinan"].astype(str).str.replace(r"\D", "", regex=True)
        )
        g.loc[g["numero_notificacao"].isin({"", "nan", "None"}), "numero_notificacao"] = np.nan
    else:
        g["numero_notificacao"] = np.nan

    return g


def tipagem_por_notificacao(ex: pd.DataFrame) -> pd.DataFrame:
    if ex.empty or "numero_notificacao" not in ex.columns:
        return pd.DataFrame()
    d = ex.dropna(subset=["numero_notificacao"]).copy()
    if d.empty:
        return pd.DataFrame()

    rows = []
    for notif, g in d.groupby("numero_notificacao"):
        soros = [s for s in g["gal_sorogrupo_nm_v32"].astype(str) if s and s not in {"nan", ""}]
        rows.append({
            "numero_notificacao": notif,
            "n_exames_gal": len(g),
            "gal_pcr_qualquer": int(pd.to_numeric(g["gal_pcr_v32"], errors="coerce").fillna(0).max()),
            "gal_cultura_qualquer": int(pd.to_numeric(g["gal_cultura_v32"], errors="coerce").fillna(0).max()),
            "gal_lab_positivo": int(pd.to_numeric(g["gal_lab_positivo_v32"], errors="coerce").fillna(0).max()),
            "gal_nm_detectavel": int(pd.to_numeric(g["gal_nm_detectavel_v32"], errors="coerce").fillna(0).max()),
            "gal_hi_detectavel": int(pd.to_numeric(g["gal_hi_detectavel_v32"], errors="coerce").fillna(0).max()),
            "gal_sorogrupo_nm": soros[0] if soros else "",
            "gal_liberado_n": int(pd.to_numeric(g["gal_liberado_v32"], errors="coerce").fillna(0).sum()),
            "lt_coleta_liberacao_mediana": float(g["lt_coleta_liberacao_dias_v32"].median())
            if g["lt_coleta_liberacao_dias_v32"].notna().any() else np.nan,
        })
    return pd.DataFrame(rows)


def concordancia_sinan(tip: pd.DataFrame, base: pd.DataFrame, ex: pd.DataFrame | None = None) -> pd.DataFrame:
    if base.empty:
        return pd.DataFrame()
    b = base.copy()
    b["_sid"] = range(len(b))
    keep = [
        c for c in [
            "_sid", "NumeroNotificacao", "municipio_v17", "regional_v17",
            "classificacao_agrupada_v17", "ano_evento_v17",
            "SeNMeningiditisEspecificarSorogrupo",
        ] if c in b.columns or c == "_sid"
    ]
    base_k = b[keep].copy()
    if "NumeroNotificacao" in base_k.columns:
        base_k["numero_notificacao"] = (
            base_k["NumeroNotificacao"].astype(str).str.replace(r"\D", "", regex=True)
        )

    # Preferência: linkage_matches_gal (sid SINAN × eid GAL)
    link_path = OUT / "linkage_matches_gal_v23.csv"
    gal_by_sid = pd.DataFrame()
    if link_path.exists() and ex is not None and not ex.empty:
        try:
            link = pd.read_csv(link_path, encoding="utf-8-sig", low_memory=False)
        except Exception:
            link = pd.DataFrame()
        if {"sid", "eid"}.issubset(link.columns):
            ex2 = ex.reset_index(drop=True).copy()
            ex2["_eid"] = ex2.index
            # tipagem flags já estão em ex
            cols_flag = [
                c for c in [
                    "gal_pcr_v32", "gal_cultura_v32", "gal_lab_positivo_v32",
                    "gal_nm_detectavel_v32", "gal_hi_detectavel_v32",
                    "gal_sorogrupo_nm_v32", "gal_liberado_v32",
                    "lt_coleta_liberacao_dias_v32",
                ] if c in ex2.columns
            ]
            j = link[["sid", "eid"]].dropna().copy()
            j["sid"] = pd.to_numeric(j["sid"], errors="coerce")
            j["eid"] = pd.to_numeric(j["eid"], errors="coerce")
            j = j.dropna()
            j = j.merge(ex2[["_eid"] + cols_flag], left_on="eid", right_on="_eid", how="inner")
            if not j.empty:
                rows = []
                for sid, g in j.groupby("sid"):
                    soros = [
                        s for s in g.get("gal_sorogrupo_nm_v32", pd.Series(dtype=str)).astype(str)
                        if s and s not in {"nan", ""}
                    ]
                    rows.append({
                        "_sid": int(sid),
                        "n_exames_gal": len(g),
                        "gal_pcr_qualquer": int(pd.to_numeric(g["gal_pcr_v32"], errors="coerce").fillna(0).max()) if "gal_pcr_v32" in g else 0,
                        "gal_cultura_qualquer": int(pd.to_numeric(g["gal_cultura_v32"], errors="coerce").fillna(0).max()) if "gal_cultura_v32" in g else 0,
                        "gal_lab_positivo": int(pd.to_numeric(g["gal_lab_positivo_v32"], errors="coerce").fillna(0).max()) if "gal_lab_positivo_v32" in g else 0,
                        "gal_nm_detectavel": int(pd.to_numeric(g["gal_nm_detectavel_v32"], errors="coerce").fillna(0).max()) if "gal_nm_detectavel_v32" in g else 0,
                        "gal_hi_detectavel": int(pd.to_numeric(g["gal_hi_detectavel_v32"], errors="coerce").fillna(0).max()) if "gal_hi_detectavel_v32" in g else 0,
                        "gal_sorogrupo_nm": soros[0] if soros else "",
                        "gal_liberado_n": int(pd.to_numeric(g["gal_liberado_v32"], errors="coerce").fillna(0).sum()) if "gal_liberado_v32" in g else 0,
                    })
                gal_by_sid = pd.DataFrame(rows)
                print(f"[INFO] Concordância via linkage sid×eid: {len(gal_by_sid)} casos SINAN com GAL")

    if not gal_by_sid.empty:
        m = base_k.merge(gal_by_sid, on="_sid", how="left")
    elif tip is not None and not tip.empty and "numero_notificacao" in base_k.columns:
        m = base_k.merge(tip, on="numero_notificacao", how="left")
        print(f"[INFO] Concordância via Num_Notificacao_Sinan: {int(m['n_exames_gal'].notna().sum())} matches")
    else:
        m = base_k.copy()
        m["n_exames_gal"] = np.nan

    m["tem_gal_v32"] = m["n_exames_gal"].fillna(0).gt(0).astype(int)
    m["sinan_sorogrupo"] = (
        m["SeNMeningiditisEspecificarSorogrupo"].astype(str).str.strip()
        if "SeNMeningiditisEspecificarSorogrupo" in m.columns else ""
    )
    m["sinan_sorogrupo"] = m["sinan_sorogrupo"].replace({"nan": "", "None": "", "NaN": ""})
    # SINAN usa "*Em Branco" / "Ignorado" como ausência
    blank = m["sinan_sorogrupo"].astype(str).str.upper().str.contains(
        r"EM BRANCO|IGNORADO|NAO SE APLICA|NÃO SE APLICA|^\s*$|^\*$",
        regex=True,
        na=True,
    )
    m.loc[blank, "sinan_sorogrupo"] = ""
    if "gal_sorogrupo_nm" not in m.columns:
        m["gal_sorogrupo_nm"] = ""
    m["gal_sorogrupo_nm"] = m["gal_sorogrupo_nm"].fillna("").astype(str)
    m["sorogrupo_uniao_v32"] = np.where(
        m["sinan_sorogrupo"].astype(str).str.len() > 0,
        m["sinan_sorogrupo"],
        m["gal_sorogrupo_nm"],
    )
    m["sorogrupo_so_gal_v32"] = (
        (m["sinan_sorogrupo"].astype(str).str.len() == 0)
        & (m["gal_sorogrupo_nm"].astype(str).str.len() > 0)
    ).astype(int)
    return m


def fila_tipagem_sinan(conc: pd.DataFrame) -> pd.DataFrame:
    """
    Lista acionável para fechar lacuna de sorogrupo DM (~30% preenchido):
      1) Tipagem Nm já no GAL e campo SINAN em branco (atualizar ficha)
      2) DM com GAL vinculado mas sem tipagem Nm nem sorogrupo SINAN (buscar tipagem)
    """
    cols = [
        "NumeroNotificacao", "municipio_v17", "regional_v17", "classificacao_agrupada_v17",
        "ano_evento_v17", "sinan_sorogrupo", "gal_sorogrupo_nm", "sorogrupo_uniao_v32",
        "sorogrupo_so_gal_v32", "tem_gal_v32", "motivo_fila_v32", "acao_sugerida_v32",
    ]
    if conc is None or conc.empty:
        return pd.DataFrame(columns=cols)
    d = conc.copy()
    is_dm = d.get("classificacao_agrupada_v17", pd.Series("", index=d.index)).astype(str).str.contains(
        "meningoc", case=False, na=False
    )
    sinan_vazio = d.get("sinan_sorogrupo", pd.Series("", index=d.index)).astype(str).str.len().eq(0)
    gal_soro = d.get("gal_sorogrupo_nm", pd.Series("", index=d.index)).astype(str)
    gal_tem_soro = gal_soro.str.len().gt(0) & ~gal_soro.isin({"nan", "None", ""})
    tem_gal = pd.to_numeric(d.get("tem_gal_v32"), errors="coerce").fillna(0).astype(int).eq(1)
    so_gal = pd.to_numeric(d.get("sorogrupo_so_gal_v32"), errors="coerce").fillna(0).astype(int).eq(1)

    # 1) tipagem no GAL → atualizar SINAN
    m1 = so_gal | (sinan_vazio & gal_tem_soro)
    # 2) DM sem sorogrupo + tem GAL sem tipagem Nm
    m2 = is_dm & sinan_vazio & tem_gal & ~gal_tem_soro
    # 3) DM sem sorogrupo e sem GAL (ainda vale listar, prioridade menor)
    m3 = is_dm & sinan_vazio & ~tem_gal

    d["_motivo"] = ""
    d.loc[m1, "_motivo"] = "tipagem_gal_atualizar_sinan"
    d.loc[m2 & ~m1, "_motivo"] = "dm_com_gal_sem_tipagem"
    d.loc[m3 & ~m1 & ~m2, "_motivo"] = "dm_sem_sorogrupo_sem_gal"

    mask = m1 | m2 | m3
    fila = d.loc[mask].copy()
    if fila.empty:
        return pd.DataFrame(columns=cols)

    prio_map = {
        "tipagem_gal_atualizar_sinan": 0,
        "dm_com_gal_sem_tipagem": 1,
        "dm_sem_sorogrupo_sem_gal": 2,
    }
    acao_map = {
        "tipagem_gal_atualizar_sinan": "Atualizar SeNMeningiditisEspecificarSorogrupo no SINAN com tipagem GAL",
        "dm_com_gal_sem_tipagem": "Localizar tipagem Nm no GAL/LACEN e completar sorogrupo no SINAN",
        "dm_sem_sorogrupo_sem_gal": "Articular LACEN/GAL para tipagem e preencher sorogrupo DM no SINAN",
    }
    fila["motivo_fila_v32"] = fila["_motivo"]
    fila["acao_sugerida_v32"] = fila["_motivo"].map(acao_map)
    fila["_prio"] = fila["_motivo"].map(prio_map).fillna(9)
    if "sorogrupo_so_gal_v32" not in fila.columns:
        fila["sorogrupo_so_gal_v32"] = m1.loc[fila.index].astype(int)
    sort_cols = [c for c in ["_prio", "regional_v17", "municipio_v17", "ano_evento_v17"] if c in fila.columns]
    if sort_cols:
        fila = fila.sort_values(sort_cols, ascending=[True] * len(sort_cols))
    for c in cols:
        if c not in fila.columns:
            fila[c] = ""
    return fila[cols].reset_index(drop=True)


def kpis(ex: pd.DataFrame, conc: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(escopo, recorte, **kw):
        rows.append({"escopo": escopo, "recorte": recorte, **kw})

    if not ex.empty:
        lib = ex[ex["gal_liberado_v32"] == 1]
        add(
            "ESTADUAL", "MT",
            n_exames=int(len(ex)),
            n_exames_liberados=int(len(lib)),
            pct_pcr=float(ex["gal_pcr_v32"].mean() * 100),
            pct_cultura=float(ex["gal_cultura_v32"].mean() * 100),
            pct_lab_positivo_liberados=float(lib["gal_lab_positivo_v32"].mean() * 100) if len(lib) else np.nan,
            n_nm_detectavel=int(ex["gal_nm_detectavel_v32"].sum()),
            n_hi_detectavel=int(ex["gal_hi_detectavel_v32"].sum()),
            n_com_sorogrupo_gal=int((ex["gal_sorogrupo_nm_v32"].astype(str).str.len() > 0).sum()),
            mediana_dias_coleta_liberacao=float(ex["lt_coleta_liberacao_dias_v32"].median())
            if ex["lt_coleta_liberacao_dias_v32"].notna().any() else np.nan,
        )

    if not conc.empty:
        dm = conc
        if "classificacao_agrupada_v17" in conc.columns:
            dm = conc[
                conc["classificacao_agrupada_v17"].astype(str).str.contains(
                    "meningoc", case=False, na=False
                )
            ]
        n_dm = len(dm)
        add(
            "ESTADUAL", "MT_casos_SINAN_com_chave",
            n_casos_sinan=int(len(conc)),
            pct_casos_com_gal=float(conc["tem_gal_v32"].mean() * 100),
            n_dm=int(n_dm),
            pct_dm_com_gal=float(dm["tem_gal_v32"].mean() * 100) if n_dm else np.nan,
            pct_dm_sorogrupo_sinan=float((dm["sinan_sorogrupo"].astype(str).str.len() > 0).mean() * 100) if n_dm else np.nan,
            pct_dm_sorogrupo_uniao=float((dm["sorogrupo_uniao_v32"].astype(str).str.len() > 0).mean() * 100) if n_dm else np.nan,
            n_dm_sorogrupo_so_gal=int(dm["sorogrupo_so_gal_v32"].sum()) if n_dm else 0,
        )
        if "regional_v17" in conc.columns:
            for reg, g in conc.groupby(conc["regional_v17"].fillna("Sem regional").astype(str)):
                add(
                    "REGIONAL", reg,
                    n_casos_sinan=int(len(g)),
                    pct_casos_com_gal=float(g["tem_gal_v32"].mean() * 100),
                    n_dm_sorogrupo_so_gal=int(g["sorogrupo_so_gal_v32"].sum()),
                )
    return pd.DataFrame(rows)


def tempo_lab(ex: pd.DataFrame) -> pd.DataFrame:
    if ex.empty or "lt_coleta_liberacao_dias_v32" not in ex.columns:
        return pd.DataFrame()
    d = ex[ex["gal_liberado_v32"] == 1].copy()
    d = d[d["lt_coleta_liberacao_dias_v32"].notna() & (d["lt_coleta_liberacao_dias_v32"] >= 0)]
    if d.empty:
        return pd.DataFrame()
    rows = [{
        "escopo": "ESTADUAL",
        "recorte": "MT",
        "n": int(len(d)),
        "mediana_dias": float(d["lt_coleta_liberacao_dias_v32"].median()),
        "p90_dias": float(d["lt_coleta_liberacao_dias_v32"].quantile(0.9)),
        "pct_liberado_48h": float((d["lt_coleta_liberacao_dias_v32"] <= 2).mean() * 100),
        "pct_liberado_7d": float((d["lt_coleta_liberacao_dias_v32"] <= 7).mean() * 100),
    }]
    return pd.DataFrame(rows)


def write_report(kpis_df: pd.DataFrame, tip: pd.DataFrame, tempo: pd.DataFrame) -> None:
    REL.mkdir(exist_ok=True)
    lines = [
        "# GAL laboratório detalhado V32",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Usa o extrato `gal_lacen_meningites.csv` (VW_GAL) com resultados por exame,",
        "metodologia, tipagem Nm/Hi e tempo coleta→liberação — além do match binário do módulo 17.",
        "",
    ]
    if not kpis_df.empty:
        est = kpis_df[kpis_df["escopo"].eq("ESTADUAL")]
        lines.append("## KPIs")
        lines.append("")
        lines.append(est.to_string(index=False))
        lines.append("")
    if not tip.empty:
        com_soro = tip[tip["gal_sorogrupo_nm"].astype(str).str.len() > 0]
        lines += [
            f"- Notificações com tipagem Nm no GAL: **{len(com_soro)}**",
            f"- Nm detectável (agregado): **{int(tip['gal_nm_detectavel'].sum())}**",
            f"- Hi detectável (agregado): **{int(tip['gal_hi_detectavel'].sum())}**",
            "",
        ]
    if not tempo.empty:
        r = tempo.iloc[0]
        lines += [
            "## Oportunidade laboratorial",
            "",
            f"- Mediana coleta→liberação: **{r['mediana_dias']:.1f} dias** (P90={r['p90_dias']:.1f})",
            f"- Liberados ≤48h: **{r['pct_liberado_48h']:.1f}%** · ≤7d: **{r['pct_liberado_7d']:.1f}%**",
            "",
        ]
    (REL / "GAL_LABORATORIO_DETALHADO_V32.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    gal = _read_gal()
    if gal.empty:
        print("[INFO] gal_lacen_meningites.csv ausente — módulo 32 encerrado sem erro.")
        for nome in [
            "gal_exames_meningite_v32.csv",
            "gal_tipagem_nm_hib_v32.csv",
            "gal_kpis_laboratorio_v32.csv",
            "gal_sinan_concordancia_lab_v32.csv",
            "gal_tempo_coleta_liberacao_v32.csv",
            "gal_fila_tipagem_sinan_v32.csv",
        ]:
            pd.DataFrame().to_csv(OUT / nome, index=False, encoding="utf-8-sig")
        return 0

    ex = preparar_exames(gal)
    tip = tipagem_por_notificacao(ex)
    try:
        base = load_base_v17()
    except Exception:
        base = pd.DataFrame()
    conc = concordancia_sinan(tip, base, ex)
    kdf = kpis(ex, conc)
    tempo = tempo_lab(ex)
    fila_tip = fila_tipagem_sinan(conc)

    # export exames (colunas úteis, sem nominais)
    drop_pii = [
        c for c in ex.columns
        if re.search(r"nome|cns|mae|endereco|telefone|doc_|bairro|cep", c, re.I)
    ]
    ex_out = ex.drop(columns=drop_pii, errors="ignore")
    ex_out.to_csv(OUT / "gal_exames_meningite_v32.csv", index=False, encoding="utf-8-sig")
    tip.to_csv(OUT / "gal_tipagem_nm_hib_v32.csv", index=False, encoding="utf-8-sig")
    kdf.to_csv(OUT / "gal_kpis_laboratorio_v32.csv", index=False, encoding="utf-8-sig")
    conc.to_csv(OUT / "gal_sinan_concordancia_lab_v32.csv", index=False, encoding="utf-8-sig")
    tempo.to_csv(OUT / "gal_tempo_coleta_liberacao_v32.csv", index=False, encoding="utf-8-sig")
    fila_tip.to_csv(OUT / "gal_fila_tipagem_sinan_v32.csv", index=False, encoding="utf-8-sig")
    write_report(kdf, tip, tempo)

    print(
        f"[OK] GAL detalhado: {len(ex)} exames meningite · {len(tip)} notificações tipadas · "
        f"fila_tipagem_sinan={len(fila_tip)}"
    )
    if not kdf.empty:
        print(kdf[kdf["escopo"].eq("ESTADUAL")].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
