# -*- coding: utf-8 -*-
"""
20_enriquecimento_dw_fila_cievs_v23.py
Une linkage GAL/SIM (DW) + qualidade SINAN + alertas de prazo em uma fila CIEVS.

Saídas:
  - enriquecimento_casos_dw_v23.csv
  - alertas_linkage_dw_v23.csv
  - alertas_qualidade_sinan_v23.csv
  - fila_cievs_unificada_v23.csv
  - relatorios/FILA_CIEVS_UNIFICADA_V23.md
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, MISSING, load_base_v17, text_key

SEVERIDADE_ORDEM = {"Crítico": 4, "Alto": 3, "Atenção": 2, "Informativo": 1}
MIN_SCORE = 0.75


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def gal_resultado_flag(resultado, metodo="") -> int:
    """1=positivo/detectável, 0=negativo, -1=inconclusivo."""
    t = text_key(f"{resultado} {metodo}")
    if not t or t.lower() in MISSING:
        return -1
    neg = (
        "NAO DETECT", "NAO HOUVE", "NEGATIV", "NAO REAGEN", "NAO FORAM",
        "NAO VISUALIZ", "SEM CRESCIMENTO", "NAO ISOLAD",
    )
    if any(x in t for x in neg):
        return 0
    pos = ("DETECTAVEL", "POSIT", "ISOLAD", "CRESCIMENTO", "REAGEN", "VIÁVEL", "VIAVEL")
    if any(x in t for x in pos):
        return 1
    return -1


def prepare_matches() -> tuple[pd.DataFrame, pd.DataFrame]:
    gal = _read(OUT / "linkage_matches_gal_v23.csv")
    sim = _read(OUT / "linkage_matches_sim_v23.csv")
    if not gal.empty:
        gal = gal[pd.to_numeric(gal.get("score"), errors="coerce").fillna(0) >= MIN_SCORE].copy()
        gal["gal_flag"] = [
            gal_resultado_flag(r, m)
            for r, m in zip(gal.get("resultado", ""), gal.get("metodo", ""))
        ]
    if not sim.empty:
        sim = sim[pd.to_numeric(sim.get("score"), errors="coerce").fillna(0) >= MIN_SCORE].copy()
    return gal, sim


def enrich_cases(df: pd.DataFrame, gal: pd.DataFrame, sim: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    out["_sid"] = np.arange(len(out))
    out["NumeroNotificacao"] = out.get("NumeroNotificacao", pd.Series(index=out.index)).astype(str)

    out["dw_gal_match_v23"] = 0
    out["dw_gal_score_v23"] = np.nan
    out["dw_gal_metodo_v23"] = ""
    out["dw_gal_resultado_v23"] = ""
    out["dw_gal_positivo_v23"] = 0
    out["dw_sim_match_v23"] = 0
    out["dw_sim_score_v23"] = np.nan
    out["dw_sim_cid_v23"] = ""

    def apply_gal(mask: pd.Series, row) -> None:
        if not mask.any():
            return
        out.loc[mask, "dw_gal_match_v23"] = 1
        out.loc[mask, "dw_gal_score_v23"] = row.get("score", np.nan)
        out.loc[mask, "dw_gal_metodo_v23"] = str(row.get("metodo", "") or "")[:120]
        out.loc[mask, "dw_gal_resultado_v23"] = str(row.get("resultado", "") or "")[:200]
        out.loc[mask, "dw_gal_positivo_v23"] = int(row.get("gal_flag", -1) == 1)

    if not gal.empty:
        # 1) por número de notificação (mais seguro)
        if "numero_notificacao" in gal.columns:
            g2 = gal.copy()
            g2["numero_notificacao"] = g2["numero_notificacao"].astype(str).str.strip()
            g2 = g2[~g2["numero_notificacao"].isin(["", "nan", "None"])]
            g2 = g2.sort_values("score", ascending=False).drop_duplicates("numero_notificacao")
            for _, row in g2.iterrows():
                apply_gal(out["NumeroNotificacao"] == str(row["numero_notificacao"]), row)
        # 2) fallback por sid (mesma ordem da base no momento do linkage)
        g = gal.sort_values("score", ascending=False).drop_duplicates("sid", keep="first")
        for _, row in g.iterrows():
            try:
                sid = int(row["sid"])
            except Exception:
                continue
            if sid < 0 or sid >= len(out):
                continue
            if out.at[sid, "dw_gal_match_v23"] == 1:
                continue
            apply_gal(out.index == sid, row)

    if not sim.empty:
        if "numero_notificacao" in sim.columns:
            s2 = sim.copy()
            s2["numero_notificacao"] = s2["numero_notificacao"].astype(str).str.strip()
            s2 = s2[~s2["numero_notificacao"].isin(["", "nan", "None"])]
            s2 = s2.sort_values("score", ascending=False).drop_duplicates("numero_notificacao")
            for _, row in s2.iterrows():
                m = out["NumeroNotificacao"] == str(row["numero_notificacao"])
                if m.any():
                    out.loc[m, "dw_sim_match_v23"] = 1
                    out.loc[m, "dw_sim_score_v23"] = row.get("score", np.nan)
                    out.loc[m, "dw_sim_cid_v23"] = str(row.get("cid", "") or "")[:20]
        s = sim.sort_values("score", ascending=False).drop_duplicates("sid", keep="first")
        for _, row in s.iterrows():
            try:
                sid = int(row["sid"])
            except Exception:
                continue
            if sid < 0 or sid >= len(out) or out.at[sid, "dw_sim_match_v23"] == 1:
                continue
            out.at[sid, "dw_sim_match_v23"] = 1
            out.at[sid, "dw_sim_score_v23"] = row.get("score", np.nan)
            out.at[sid, "dw_sim_cid_v23"] = str(row.get("cid", "") or "")[:20]

    return out


def alertas_linkage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base_cols = ["NumeroNotificacao", "municipio_v17", "regional_v17", "classificacao_agrupada_v17",
                 "confirmado_v17", "obito_meningite_v17", "data_ref_v17"]

    # GAL positivo e confirmação lab fraca no SINAN
    m = (df["dw_gal_positivo_v23"] == 1) & (pd.to_numeric(df.get("confirmado_v17"), errors="coerce").fillna(0) == 1)
    if "CriterioConfirmacao" in df.columns:
        crit = df["CriterioConfirmacao"].astype(str).map(text_key)
        lab_ok = crit.str.contains("PCR|CULTURA", na=False)
        m = m & ~lab_ok
    if m.any():
        sub = df.loc[m, base_cols].copy()
        sub["tipo_alerta"] = "GAL/LACEN positivo — atualizar SINAN"
        sub["severidade"] = "Alto"
        sub["evidencia"] = (
            "Match DW VW_GAL score≥" + str(MIN_SCORE) + "; método="
            + df.loc[m, "dw_gal_metodo_v23"].astype(str)
            + "; resultado=" + df.loc[m, "dw_gal_resultado_v23"].astype(str).str[:80]
        )
        sub["acao_recomendada"] = "Conferir GAL e atualizar CritérioConfirmacao / classificação no SINAN."
        sub["prazo"] = "Semanal"
        sub["norma"] = "Informe Meningites 2024 — confirmação laboratorial"
        rows.append(sub)

    # Óbito no SIM sem óbito meningite no SINAN
    m = (df["dw_sim_match_v23"] == 1) & (pd.to_numeric(df.get("obito_meningite_v17"), errors="coerce").fillna(0) == 0)
    if m.any():
        sub = df.loc[m, base_cols].copy()
        sub["tipo_alerta"] = "Óbito no SIM sem desfecho meningite no SINAN"
        sub["severidade"] = "Crítico"
        sub["evidencia"] = (
            "Match DW SIM score≥" + str(MIN_SCORE)
            + "; CID=" + df.loc[m, "dw_sim_cid_v23"].astype(str)
            + "; EvolucaoCaso/SINAN sem óbito por meningite"
        )
        sub["acao_recomendada"] = "Revisar evolução/encerramento no SINAN e causa básica no SIM."
        sub["prazo"] = "Imediato"
        sub["norma"] = "Linkage SIM × SINAN — vigilância de mortalidade"
        rows.append(sub)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out = out.rename(columns={"NumeroNotificacao": "id_caso"})
    out["severidade_ordem"] = out["severidade"].map(SEVERIDADE_ORDEM).fillna(0)
    return out.sort_values(["severidade_ordem"], ascending=False)


def alertas_qualidade(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = ["NumeroNotificacao", "municipio_v17", "regional_v17", "classificacao_agrupada_v17"]

    # Duplicidade de notificação
    n = df["NumeroNotificacao"].astype(str)
    dup = n.duplicated(keep=False) & ~n.isin(["", "nan", "None"])
    if dup.any():
        sub = df.loc[dup, base].copy()
        sub["tipo_alerta"] = "Duplicidade NumeroNotificacao"
        sub["severidade"] = "Atenção"
        sub["evidencia"] = "Mesmo número de notificação em mais de uma linha da base"
        sub["acao_recomendada"] = "Auditar e consolidar registros duplicados no SINAN/DW."
        sub["prazo"] = "Mensal"
        sub["norma"] = "Qualidade SINAN"
        rows.append(sub.drop_duplicates("NumeroNotificacao"))

    # ClassificacaoCaso com valor de etiologia (anomalia de campo)
    if "ClassificacaoCaso" in df.columns:
        cc = df["ClassificacaoCaso"].astype(str)
        anom = cc.str.contains("Meningite", case=False, na=False) & ~cc.str.contains(
            "Confirmado|Descartado|Suspeito|Ignorado", case=False, na=False
        )
        if anom.any():
            sub = df.loc[anom, base].copy()
            sub["tipo_alerta"] = "ClassificacaoCaso com valor atípico"
            sub["severidade"] = "Atenção"
            sub["evidencia"] = "Valor em ClassificacaoCaso parece etiologia: " + cc.loc[anom].astype(str).str[:60]
            sub["acao_recomendada"] = "Corrigir ficha — Classificação do caso ≠ Classificação da meningite."
            sub["prazo"] = "Mensal"
            sub["norma"] = "Caderno de Análises SINAN — Meningites"
            rows.append(sub)

    # Pré-2007 (possível erro de data/legado)
    ano = pd.to_numeric(df.get("ano_evento_v17"), errors="coerce")
    old = ano.notna() & (ano < 2007)
    if old.any():
        sub = df.loc[old, base].copy()
        sub["tipo_alerta"] = "Evento com ano < 2007"
        sub["severidade"] = "Informativo"
        sub["evidencia"] = "Ano do evento = " + ano.loc[old].astype(int).astype(str)
        sub["acao_recomendada"] = "Validar data de sintomas/notificação (legado ou erro)."
        sub["prazo"] = "Trimestral"
        sub["norma"] = "Qualidade da base"
        rows.append(sub)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True).rename(columns={"NumeroNotificacao": "id_caso"})
    out["severidade_ordem"] = out["severidade"].map(SEVERIDADE_ORDEM).fillna(0)
    return out


def build_fila_unificada(
    alertas_prazo: pd.DataFrame,
    surtos: pd.DataFrame,
    alertas_dw: pd.DataFrame,
    alertas_qual: pd.DataFrame,
) -> pd.DataFrame:
    fila = []

    def add_rows(src: pd.DataFrame, origem: str, id_col: str | None = "id_caso", limit: int | None = None):
        if src is None or src.empty:
            return
        use = src.copy()
        if "severidade" in use.columns:
            use = use[use["severidade"].isin(["Crítico", "Alto", "Atenção"])]
        if limit:
            use = use.head(limit)
        for _, r in use.iterrows():
            terr = str(r.get("municipio_v17", "") or "")
            if id_col and id_col in r and pd.notna(r.get(id_col)):
                terr = f"{terr} | caso {r.get(id_col)}"
            fila.append({
                "origem": origem,
                "prioridade": r.get("severidade", r.get("prioridade", "Atenção")),
                "tipo": r.get("tipo_alerta", r.get("tipo", "")),
                "territorio": terr,
                "regional_v17": r.get("regional_v17", ""),
                "evidencia": r.get("evidencia", ""),
                "acao": r.get("acao_recomendada", r.get("acao", "")),
                "prazo": r.get("prazo", ""),
                "norma": r.get("norma", ""),
            })

    add_rows(surtos, "surto_nt97", id_col=None)
    add_rows(alertas_dw, "linkage_dw", limit=150)
    if not alertas_prazo.empty:
        top = alertas_prazo[alertas_prazo["severidade"].isin(["Crítico", "Alto"])].head(200)
        add_rows(top, "prazo_ms")
    add_rows(alertas_qual, "qualidade", limit=80)

    out = pd.DataFrame(fila)
    if out.empty:
        return out
    out["ordem"] = out["prioridade"].map(SEVERIDADE_ORDEM).fillna(0)
    out = out.sort_values(["ordem", "origem", "tipo"], ascending=[False, True, True]).drop(columns=["ordem"])
    # dedup aproximado
    out = out.drop_duplicates(subset=["tipo", "territorio", "evidencia"], keep="first")
    return out.reset_index(drop=True)


def write_report(enr: pd.DataFrame, fila: pd.DataFrame, gal_n: int, sim_n: int, adw: pd.DataFrame, aq: pd.DataFrame):
    lines = [
        "# Fila CIEVS unificada — Meningites V23",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"**Matches usados (score ≥ {MIN_SCORE}):** GAL={gal_n} · SIM={sim_n}",
        "",
        "## Enriquecimento DW na base",
        "",
        f"- Casos com match GAL: **{int(enr['dw_gal_match_v23'].sum())}**",
        f"- Casos com GAL positivo: **{int(enr['dw_gal_positivo_v23'].sum())}**",
        f"- Casos com match SIM: **{int(enr['dw_sim_match_v23'].sum())}**",
        "",
        "## Mortalidade SINAN × SIM (para Odds Ratio)",
        "",
        f"- Óbitos SINAN (EvolucaoCaso): **{int(pd.to_numeric(enr.get('obito_meningite_v17'), errors='coerce').fillna(0).sum())}**",
        f"- Óbitos SIM (linkage ≥ {MIN_SCORE}): **{int(enr.get('obito_sim_link_v23', pd.Series(dtype=int)).sum()) if 'obito_sim_link_v23' in enr.columns else 0}**",
        f"- União SINAN∪SIM (desfecho padrão dos OR): **{int(enr.get('obito_meningite_uniao_v23', pd.Series(dtype=int)).sum()) if 'obito_meningite_uniao_v23' in enr.columns else 0}**",
        f"- SIM sem óbito meningite no SINAN: **{int(enr.get('obito_sim_sem_sinan_v23', pd.Series(dtype=int)).sum()) if 'obito_sim_sem_sinan_v23' in enr.columns else 0}**",
        "",
        "Arquivo: `desfechos_mortalidade_sim_v23.csv` · resumo: `mortalidade_sinan_sim_resumo_v23.csv`.",
        "",
        f"## Alertas linkage DW: {len(adw)}",
        f"## Alertas qualidade: {len(aq)}",
        f"## Fila unificada: {len(fila)} itens",
        "",
        "### Top 15 da fila",
        "",
    ]
    if not fila.empty:
        top = fila.head(15)
        for _, r in top.iterrows():
            lines.append(
                f"- **{r['prioridade']}** · {r['tipo']} · {r['territorio']} — {str(r['acao'])[:100]}"
            )
    lines += [
        "",
        "## Como atualizar",
        "",
        "```powershell",
        "py -3.13 19_dw_descobrir_e_extrair_v23.py",
        "py -3.13 17_linkage_gal_lacen_sim_v23.py",
        "py -3.13 13_alertas_inteligentes_v23.py",
        "py -3.13 20_enriquecimento_dw_fila_cievs_v23.py",
        "```",
        "",
    ]
    (REL / "FILA_CIEVS_UNIFICADA_V23.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "fila_cievs_unificada_v23.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    df = load_base_v17()
    gal, sim = prepare_matches()
    enr = enrich_cases(df, gal, sim)

    # Desfechos de mortalidade para OR / painel: SINAN, SIM (linkage) e união
    sinan_ob = pd.to_numeric(enr.get("obito_meningite_v17"), errors="coerce").fillna(0).astype(int)
    sim_ob = pd.to_numeric(enr.get("dw_sim_match_v23"), errors="coerce").fillna(0).astype(int)
    enr["obito_sim_link_v23"] = sim_ob
    enr["obito_meningite_uniao_v23"] = ((sinan_ob == 1) | (sim_ob == 1)).astype(int)
    enr["obito_sim_sem_sinan_v23"] = ((sim_ob == 1) & (sinan_ob == 0)).astype(int)

    mort_cols = [c for c in [
        "NumeroNotificacao",
        "obito_meningite_v17", "obito_sim_link_v23", "obito_meningite_uniao_v23", "obito_sim_sem_sinan_v23",
        "dw_sim_match_v23", "dw_sim_score_v23", "dw_sim_cid_v23",
    ] if c in enr.columns]
    enr[mort_cols].to_csv(OUT / "desfechos_mortalidade_sim_v23.csv", index=False, encoding="utf-8-sig")

    mort_resumo = pd.DataFrame([{
        "obitos_sinan_evolucao": int(sinan_ob.sum()),
        "obitos_sim_linkage": int(sim_ob.sum()),
        "obitos_uniao_sinan_sim": int(enr["obito_meningite_uniao_v23"].sum()),
        "obitos_sim_sem_sinan": int(enr["obito_sim_sem_sinan_v23"].sum()),
        "nota": (
            "OR de mortalidade deve usar obito_meningite_uniao_v23 (padrão). "
            "obito_meningite_v17 = só EvolucaoCaso SINAN; obito_sim_link_v23 = match SIM score≥0.75."
        ),
    }])
    mort_resumo.to_csv(OUT / "mortalidade_sinan_sim_resumo_v23.csv", index=False, encoding="utf-8-sig")

    keep = [c for c in [
        "NumeroNotificacao", "municipio_v17", "regional_v17", "data_ref_v17",
        "classificacao_agrupada_v17", "confirmado_v17", "obito_meningite_v17",
        "obito_sim_link_v23", "obito_meningite_uniao_v23", "obito_sim_sem_sinan_v23",
        "fonte_sinan_v23",
        "dw_gal_match_v23", "dw_gal_score_v23", "dw_gal_metodo_v23",
        "dw_gal_resultado_v23", "dw_gal_positivo_v23",
        "dw_sim_match_v23", "dw_sim_score_v23", "dw_sim_cid_v23",
    ] if c in enr.columns]
    enr[keep].to_csv(OUT / "enriquecimento_casos_dw_v23.csv", index=False, encoding="utf-8-sig")

    adw = alertas_linkage(enr)
    aq = alertas_qualidade(enr)
    adw.to_csv(OUT / "alertas_linkage_dw_v23.csv", index=False, encoding="utf-8-sig")
    aq.to_csv(OUT / "alertas_qualidade_sinan_v23.csv", index=False, encoding="utf-8-sig")

    prazo = _read(OUT / "alertas_inteligentes_casos_v23.csv")
    surtos = _read(OUT / "alertas_inteligentes_surtos_nt97_v23.csv")
    fila = build_fila_unificada(prazo, surtos, adw, aq)
    fila.to_csv(OUT / "fila_cievs_unificada_v23.csv", index=False, encoding="utf-8-sig")
    # Espelha na fila “oficial” usada pelo dashboard (mantém compatibilidade)
    fila_dash = fila.rename(columns={"origem": "fonte_alerta"}).copy()
    if not fila_dash.empty:
        fila_dash.to_csv(OUT / "alertas_inteligentes_fila_cievs_v23.csv", index=False, encoding="utf-8-sig")

    write_report(enr, fila, len(gal), len(sim), adw, aq)

    resumo = pd.DataFrame([{
        "n_base": len(enr),
        "gal_matches_usados": len(gal),
        "sim_matches_usados": len(sim),
        "casos_gal": int(enr["dw_gal_match_v23"].sum()),
        "casos_gal_positivo": int(enr["dw_gal_positivo_v23"].sum()),
        "casos_sim": int(enr["dw_sim_match_v23"].sum()),
        "obitos_sinan": int(pd.to_numeric(enr.get("obito_meningite_v17"), errors="coerce").fillna(0).sum()),
        "obitos_uniao_sinan_sim": int(enr["obito_meningite_uniao_v23"].sum()),
        "obitos_sim_sem_sinan": int(enr["obito_sim_sem_sinan_v23"].sum()),
        "alertas_linkage": len(adw),
        "alertas_qualidade": len(aq),
        "fila_unificada": len(fila),
        "min_score": MIN_SCORE,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }])
    resumo.to_csv(OUT / "enriquecimento_dw_resumo_v23.csv", index=False, encoding="utf-8-sig")

    print("[OK] Enriquecimento DW + fila CIEVS unificada.")
    print(resumo.to_string(index=False))
    if not fila.empty:
        print(fila["prioridade"].value_counts().to_string())
        print(fila["origem"].value_counts().to_string())


if __name__ == "__main__":
    main()
