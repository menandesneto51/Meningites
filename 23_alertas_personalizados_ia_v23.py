# -*- coding: utf-8 -*-
"""
23_alertas_personalizados_ia_v23.py
Alertas personalizados por regional + digests por perfil CIEVS + narrativa IA.

Perfis:
  - CIEVS_ESTADUAL: fila crítica estadual + MS + nowcast
  - COORD_REGIONAL: só a regional (prazos, quimio, linkage, qualidade)
  - LAB_REFERENCIA: confirmados sem lab / GAL positivo a atualizar

Não envia e-mail/WhatsApp automaticamente — gera pacotes prontos para disparo manual
ou automação futura.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, REL, load_base_v17, fmt_num

DIGEST_DIR = OUT / "digests_regionais_v23"
DIGEST_DIR.mkdir(exist_ok=True)


def _read(name: str) -> pd.DataFrame:
    p = OUT / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)


def regional_list(df: pd.DataFrame) -> list[str]:
    if "regional_v17" not in df.columns:
        return []
    return sorted(df["regional_v17"].dropna().astype(str).str.strip().unique())


def ms_por_regional(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores MS aproximados por regional (mesma lógica simplificada)."""
    try:
        ms = __import__("12_indicadores_ms_operacionais_v23")
    except Exception:
        return pd.DataFrame()
    rows = []
    for reg, g in df.groupby(df["regional_v17"].astype(str)):
        if not reg or reg.lower() in {"nan", "none", ""}:
            continue
        try:
            painel = ms.compute_indicators(g) if hasattr(ms, "compute_indicators") else None
        except Exception:
            painel = None
        if painel is None:
            # fallback leve
            n = len(g)
            conf = int(pd.to_numeric(g.get("confirmado_v17"), errors="coerce").fillna(0).sum())
            rows.append({
                "regional_v17": reg,
                "n_casos": n,
                "confirmados": conf,
                "pct_investigados_48h": None,
                "pct_encerrados_60d": None,
                "pct_quimioprofilaxia_dm_48h": None,
            })
            continue
        # se compute_indicators retorna DataFrame longo
        if isinstance(painel, pd.DataFrame) and "indicador" in painel.columns:
            m = {"regional_v17": reg, "n_casos": len(g)}
            for ind in [
                "pct_investigados_48h", "pct_encerrados_60d",
                "pct_quimioprofilaxia_dm_48h", "pct_confirmacao_laboratorial_pcr_cultura",
            ]:
                sub = painel[painel["indicador"] == ind]
                m[ind] = float(sub.iloc[0]["valor_pct"]) if not sub.empty else None
            rows.append(m)
        else:
            rows.append({"regional_v17": reg, "n_casos": len(g)})
    return pd.DataFrame(rows)


def build_digests(df: pd.DataFrame) -> pd.DataFrame:
    fila = _read("fila_cievs_unificada_v23.csv")
    if fila.empty:
        fila = _read("alertas_inteligentes_fila_cievs_v23.csv")
    casos = _read("alertas_inteligentes_casos_v23.csv")
    link = _read("alertas_linkage_dw_v23.csv")
    nc = _read("nowcast_forecast_resumo_v23.csv")
    saz = _read("sazonalidade_resumo_v23.csv")
    ms_reg = _read("indicadores_ms_por_regional_v23.csv")

    # Inferir regional na fila a partir de territorio ou coluna
    if not fila.empty and "regional_v17" not in fila.columns:
        fila["regional_v17"] = ""
    if not fila.empty and "territorio" in fila.columns:
        mun2reg = {}
        tmp = df[["municipio_v17", "regional_v17"]].dropna().copy()
        tmp["municipio_v17"] = tmp["municipio_v17"].astype(str).str.upper().str.strip()
        for _, r in tmp.drop_duplicates("municipio_v17").iterrows():
            mun2reg[str(r["municipio_v17"])] = r["regional_v17"]

        def guess_reg(terr):
            t = str(terr).upper()
            for mun, reg in mun2reg.items():
                if mun and mun in t:
                    return reg
            return ""

        # só preenche onde vazio
        mask = fila["regional_v17"].astype(str).str.strip().isin(["", "nan", "None"])
        fila.loc[mask, "regional_v17"] = fila.loc[mask, "territorio"].map(guess_reg)

    rows_idx = []
    regionais = regional_list(df)

    # Digest estadual
    crit = fila[fila.get("prioridade", pd.Series(dtype=str)).isin(["Crítico", "Alto"])] if not fila.empty else pd.DataFrame()
    lines_est = [
        f"# Digest CIEVS Estadual — Meningites",
        f"**Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Prioridades (Crítico/Alto)",
        f"- Itens na fila filtrada: **{len(crit)}**",
        "",
    ]
    if not nc.empty:
        r = nc.iloc[0]
        lines_est += [
            "## Nowcast / sazonalidade",
            f"- Nowcast SE: {r.get('nowcast_se_atual')} (obs {r.get('observado_se_atual')})",
            f"- Alerta: {r.get('alerta_nowcast')} — {r.get('alerta_detalhe')}",
            "",
        ]
    if not saz.empty:
        s = saz.iloc[0]
        lines_est += [
            f"- Pico sazonal típico: **{s.get('mes_pico_1_rotulo')}** (índice {s.get('indice_pico_1')})",
            "",
        ]
    if not crit.empty:
        lines_est.append("### Top 20 da fila")
        for _, r in crit.head(20).iterrows():
            lines_est.append(
                f"- **{r.get('prioridade')}** · {r.get('tipo')} · {r.get('territorio')} — {str(r.get('acao', ''))[:90]}"
            )
    path_est = DIGEST_DIR / "DIGEST_CIEVS_ESTADUAL.md"
    path_est.write_text("\n".join(lines_est), encoding="utf-8")
    rows_idx.append({
        "perfil": "CIEVS_ESTADUAL",
        "regional_v17": "ESTADO",
        "arquivo": path_est.name,
        "n_itens_criticos": len(crit),
        "canal_sugerido": "e-mail coordenação CIEVS / reunião diária",
    })

    # Por regional
    for reg in regionais:
        if not reg or reg.upper() in {"NAN", "NONE", "*EM BRANCO"}:
            continue
        freg = fila[fila["regional_v17"].astype(str) == reg] if not fila.empty and "regional_v17" in fila.columns else pd.DataFrame()
        creg = casos[casos.get("regional_v17", pd.Series(dtype=str)).astype(str) == reg] if not casos.empty and "regional_v17" in casos.columns else pd.DataFrame()
        lreg = link[link.get("regional_v17", pd.Series(dtype=str)).astype(str) == reg] if not link.empty and "regional_v17" in link.columns else pd.DataFrame()
        n_crit = 0
        if not freg.empty and "prioridade" in freg.columns:
            n_crit = int(freg["prioridade"].isin(["Crítico", "Alto"]).sum())
        elif not creg.empty and "severidade" in creg.columns:
            n_crit = int(creg["severidade"].isin(["Crítico", "Alto"]).sum())

        ms_line = ""
        if not ms_reg.empty:
            m = ms_reg[ms_reg["regional_v17"].astype(str) == reg]
            if not m.empty:
                mm = m.iloc[0]
                ms_line = (
                    f"Casos={mm.get('n_casos')} | inv48h={mm.get('pct_investigados_48h')}% | "
                    f"enc60d={mm.get('pct_encerrados_60d')}% | quimio={mm.get('pct_quimioprofilaxia_dm_48h')}%"
                )

        lines = [
            f"# Digest Regional — {reg}",
            f"**Perfil:** COORD_REGIONAL · **Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            "## Indicadores MS (regional)",
            ms_line or "(rode indicadores por regional se disponível)",
            "",
            f"## Fila local: {len(freg)} itens · Crítico/Alto: {n_crit}",
            "",
        ]
        src = freg if not freg.empty else creg
        if not src.empty:
            use = src.head(15)
            for _, r in use.iterrows():
                sev = r.get("prioridade", r.get("severidade", ""))
                tipo = r.get("tipo", r.get("tipo_alerta", ""))
                terr = r.get("territorio", r.get("municipio_v17", ""))
                acao = r.get("acao", r.get("acao_recomendada", ""))
                lines.append(f"- **{sev}** · {tipo} · {terr} — {str(acao)[:100]}")
        if not lreg.empty:
            lines += ["", f"## Linkage DW ({len(lreg)})", ""]
            for _, r in lreg.head(8).iterrows():
                lines.append(f"- {r.get('tipo_alerta')} · caso {r.get('id_caso')} — {str(r.get('evidencia', ''))[:100]}")

        lines += [
            "",
            "## Ações sugeridas (meningites / MS)",
            "1. Resolver quimioprofilaxia DM/Hib pendente (≤48h).",
            "2. Encerrar casos próximos/além de 60 dias.",
            "3. Buscar resultado GAL/LACEN quando lab fraco ou match DW positivo.",
            "4. Completar investigação ≤48h e sorogrupo em DM.",
            "",
        ]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in reg)[:60]
        path = DIGEST_DIR / f"DIGEST_{safe}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        rows_idx.append({
            "perfil": "COORD_REGIONAL",
            "regional_v17": reg,
            "arquivo": path.name,
            "n_itens_criticos": n_crit,
            "canal_sugerido": "e-mail / WhatsApp da regional de saúde",
        })

    # Perfil lab
    lab_fila = pd.DataFrame()
    if not link.empty:
        lab_fila = link[link["tipo_alerta"].astype(str).str.contains("GAL|lab|Lab|SINAN", case=False, na=False)]
    if lab_fila.empty and not casos.empty:
        lab_fila = casos[casos["tipo_alerta"].astype(str).str.contains("laboratorial|GAL", case=False, na=False)]
    lines_lab = [
        "# Digest Laboratório / LACEN — Meningites",
        f"**Perfil:** LAB_REFERENCIA · **Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        f"Itens: **{len(lab_fila)}**",
        "",
    ]
    for _, r in lab_fila.head(30).iterrows():
        lines_lab.append(
            f"- {r.get('tipo_alerta', r.get('tipo', ''))} · {r.get('municipio_v17', r.get('territorio', ''))} "
            f"· caso {r.get('id_caso', '')} — {str(r.get('evidencia', ''))[:120]}"
        )
    path_lab = DIGEST_DIR / "DIGEST_LAB_REFERENCIA.md"
    path_lab.write_text("\n".join(lines_lab), encoding="utf-8")
    rows_idx.append({
        "perfil": "LAB_REFERENCIA",
        "regional_v17": "LACEN/GAL",
        "arquivo": path_lab.name,
        "n_itens_criticos": len(lab_fila),
        "canal_sugerido": "e-mail LACEN / referência laboratorial",
    })

    idx = pd.DataFrame(rows_idx)
    idx.to_csv(OUT / "alertas_personalizados_indice_v23.csv", index=False, encoding="utf-8-sig")
    return idx, path_est


def narrativa_ia(idx: pd.DataFrame) -> str:
    """Narrativa local (RAG se disponível) sobre o pacote de alertas/sazonalidade."""
    partes = []
    nc = _read("nowcast_forecast_resumo_v23.csv")
    saz = _read("sazonalidade_resumo_v23.csv")
    fila_n = len(_read("fila_cievs_unificada_v23.csv"))
    partes.append("# Narrativa operacional — Meningites (IA assistida)")
    partes.append("")
    partes.append(f"**Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    partes.append("")
    partes.append("## Síntese")
    partes.append("")
    if not saz.empty:
        s = saz.iloc[0]
        partes.append(
            f"O padrão sazonal histórico aponta maior risco relativo em **{s.get('mes_pico_1_rotulo')}** "
            f"(índice {fmt_num(s.get('indice_pico_1'), 2)}). "
            f"Na SE {s.get('semana_epi_atual')}, a vigilância deve comparar o observado com a média/P75 do perfil semanal."
        )
    if not nc.empty:
        r = nc.iloc[0]
        partes.append(
            f" O nowcast corrigido por atraso estima **{fmt_num(r.get('nowcast_se_atual'), 1)}** casos "
            f"(observado {fmt_num(r.get('observado_se_atual'), 1)}), status **{r.get('alerta_nowcast')}**. "
            f"Projeção SE+1 ≈ {fmt_num(r.get('forecast_se1'), 1)}; backtest MAPE ≈ {fmt_num(r.get('backtest_mape_pct'), 1)}%."
        )
    partes.append(
        f" A fila unificada tem **{fila_n}** itens; foram gerados **{len(idx)}** digests personalizados "
        f"(estadual, regionais e laboratório) para disparo manual aos perfis CIEVS."
    )
    partes.append("")
    partes.append("## Recomendações alinhadas ao MS")
    partes.append("")
    partes.append(
        "1. Priorizar **quimioprofilaxia DM/Hib ≤48h** e **investigação ≤48h** (Informe Meningites 2024).\n"
        "2. Acelerar **encerramento ≤60 dias** e confirmação lab (PCR/cultura).\n"
        "3. Nos meses/SE de pico sazonal, reforçar busca ativa de resultados GAL e sorogrupo.\n"
        "4. Usar digests regionais na reunião de monitoramento semanal do CIEVS.\n"
    )
    partes.append("")
    partes.append("> Texto gerado localmente a partir dos módulos 21–23; validar clinicamente antes de divulgação externa.")
    partes.append("")

    # Tentar enriquecer com assistente RAG
    try:
        assist = __import__("16_assistente_cievs_v23")
        if hasattr(assist, "answer"):
            q = "Quais ações prioritárias do CIEVS para meningites conforme Informe MS e NT 97?"
            resp = assist.answer(q, use_llm=False)
            if isinstance(resp, dict) and resp.get("resposta"):
                partes += ["## Trecho normativo recuperado (RAG)", "", resp["resposta"][:1200], ""]
    except Exception:
        pass

    text = "\n".join(partes)
    (REL / "NARRATIVA_ALERTAS_SAZONALIDADE_V23.md").write_text(text, encoding="utf-8")
    (OUT / "narrativa_alertas_sazonalidade_v23.md").write_text(text, encoding="utf-8")
    return text


def compute_ms_regional_fallback(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores MS por regional sem depender de API interna do módulo 12."""
    from importlib import import_module
    try:
        ms = import_module("12_indicadores_ms_operacionais_v23")
    except Exception:
        ms = None
    rows = []
    for reg, g in df.groupby(df["regional_v17"].astype(str)):
        if not str(reg).strip() or str(reg).lower() in {"nan", "none"}:
            continue
        row = {"regional_v17": reg, "n_casos": len(g)}
        if ms is not None:
            try:
                d = ms._ensure_lead_times(g)
                lt_inv = pd.to_numeric(d.get("lt_notificacao_investigacao_dias_v17"), errors="coerce")
                lt_enc = pd.to_numeric(d.get("lt_notificacao_encerramento_dias_v17"), errors="coerce")
                row["pct_investigados_48h"] = round(float((lt_inv <= 2).sum() / max(lt_inv.notna().sum(), 1) * 100), 1)
                row["pct_encerrados_60d"] = round(float((lt_enc <= 60).sum() / max(lt_enc.notna().sum(), 1) * 100), 1)
                # quimio DM
                dm = d[d.get("classificacao_agrupada_v17", pd.Series(dtype=object)).astype(str).eq("Doença meningocócica")]
                if len(dm) and hasattr(ms, "_quimio_realizada"):
                    q = ms._quimio_realizada(dm)
                    lt_q = pd.to_numeric(dm.get("lt_notificacao_quimioprofilaxia_dias_v17"), errors="coerce")
                    row["pct_quimioprofilaxia_dm_48h"] = round(float(((q) & (lt_q <= 2)).sum() / max(len(dm), 1) * 100), 1)
                    row["dm_casos"] = len(dm)
                else:
                    row["pct_quimioprofilaxia_dm_48h"] = None
                    row["dm_casos"] = int((d.get("classificacao_agrupada_v17") == "Doença meningocócica").sum()) if "classificacao_agrupada_v17" in d.columns else 0
            except Exception:
                row["pct_investigados_48h"] = None
                row["pct_encerrados_60d"] = None
                row["pct_quimioprofilaxia_dm_48h"] = None
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("n_casos", ascending=False)
    out.to_csv(OUT / "indicadores_ms_por_regional_v23.csv", index=False, encoding="utf-8-sig")
    return out


def main():
    df = load_base_v17()
    compute_ms_regional_fallback(df)
    idx, path_est = build_digests(df)
    narr = narrativa_ia(idx)

    resumo = pd.DataFrame([{
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "n_digests": len(idx),
        "n_regionais": int((idx["perfil"] == "COORD_REGIONAL").sum()),
        "digest_estadual": path_est.name,
        "pasta": str(DIGEST_DIR),
        "narrativa": "NARRATIVA_ALERTAS_SAZONALIDADE_V23.md",
    }])
    resumo.to_csv(OUT / "alertas_personalizados_resumo_v23.csv", index=False, encoding="utf-8-sig")

    (REL / "ALERTAS_PERSONALIZADOS_V23.md").write_text(
        "\n".join([
            "# Alertas personalizados — Meningites V23",
            "",
            f"**Digests:** {len(idx)} · pasta `{DIGEST_DIR.name}/`",
            "",
            "```",
            idx.to_string(index=False),
            "```",
            "",
            "## Narrativa",
            "",
            narr[:2500],
            "",
        ]),
        encoding="utf-8",
    )

    print("[OK] Alertas personalizados + narrativa IA.")
    print(resumo.to_string(index=False))
    print(idx.to_string(index=False))


if __name__ == "__main__":
    main()
