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

# Ordem operacional das ações no digest (menor = mais urgente operacionalmente dentro da severidade)
ACAO_ORDEM = {
    "quimio": 1,
    "lab": 2,
    "tipagem": 3,
    "encerramento": 4,
    "investigacao": 5,
    "outro": 9,
}


def classificar_acao(tipo: object, acao: object = "") -> str:
    t = f"{tipo} {acao}".lower()
    if "quimio" in t:
        return "quimio"
    if "tipagem" in t or "sorogrupo" in t:
        return "tipagem"
    if "gal" in t or "lacen" in t or "laborat" in t or "pcr" in t or "cultura" in t:
        return "lab"
    if "encerr" in t:
        return "encerramento"
    if "investiga" in t:
        return "investigacao"
    return "outro"


def priorizar_fila(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena por severidade e depois por família de ação (quimio → lab/tipagem → encerramento)."""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    out = df.copy()
    sev_map = {"Crítico": 4, "Alto": 3, "Atenção": 2, "Informativo": 1}
    tipo_c = "tipo" if "tipo" in out.columns else ("tipo_alerta" if "tipo_alerta" in out.columns else None)
    acao_c = "acao" if "acao" in out.columns else ("acao_recomendada" if "acao_recomendada" in out.columns else None)
    tipos = out[tipo_c] if tipo_c else ""
    acoes = out[acao_c] if acao_c else ""
    out["_familia_acao"] = [
        classificar_acao(t, a) for t, a in zip(tipos.astype(str), acoes.astype(str))
    ]
    pri = out.get("prioridade", out.get("severidade", pd.Series(["Atenção"] * len(out))))
    out["_sev"] = pri.map(sev_map).fillna(0)
    out["_acao_ord"] = out["_familia_acao"].map(ACAO_ORDEM).fillna(9)
    return out.sort_values(["_sev", "_acao_ord"], ascending=[False, True]).drop(
        columns=["_sev", "_acao_ord"], errors="ignore"
    )


def _linha_caso(r: pd.Series) -> str:
    """Linha de digest com link textual ao caso (NU_NOTIFICACAO / id)."""
    sev = r.get("prioridade", r.get("severidade", ""))
    tipo = r.get("tipo", r.get("tipo_alerta", ""))
    terr = str(r.get("territorio", r.get("municipio_v17", "")) or "")
    acao = r.get("acao", r.get("acao_recomendada", ""))
    id_caso = str(r.get("id_caso", "") or "").strip()
    if "| caso " in terr:
        mun, _, resto = terr.partition("| caso ")
        terr = mun.strip()
        if not id_caso:
            id_caso = resto.strip()
    caso_txt = f" · caso `{id_caso}`" if id_caso else ""
    return f"- **{sev}** · {tipo} · {terr}{caso_txt} — {str(acao)[:100]}"


def _bloco_por_acao(src: pd.DataFrame, limite: int = 20) -> list[str]:
    """Agrupa a fila em seções quimio / lab / tipagem / encerramento / investigação."""
    if src is None or src.empty:
        return ["(sem itens na fila local)"]
    use = priorizar_fila(src).head(limite)
    labels = {
        "quimio": "Quimioprofilaxia",
        "lab": "Laboratório / GAL",
        "tipagem": "Tipagem / sorogrupo",
        "encerramento": "Encerramento",
        "investigacao": "Investigação",
        "outro": "Outros",
    }
    lines: list[str] = []
    familia = use["_familia_acao"] if "_familia_acao" in use.columns else pd.Series([""] * len(use), index=use.index)
    for fam in ["quimio", "lab", "tipagem", "encerramento", "investigacao", "outro"]:
        g = use[familia.astype(str).eq(fam)]
        if g.empty:
            continue
        lines.append(f"### {labels.get(fam, fam)} ({len(g)})")
        lines.append("")
        for _, r in g.iterrows():
            lines.append(_linha_caso(r))
        lines.append("")
    return lines if lines else ["(sem itens na fila local)"]


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
        lines_est.append("### Top da fila (por severidade × ação)")
        lines_est.append("")
        lines_est += _bloco_por_acao(crit, limite=25)
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
            "Prioridade: **quimio → lab/tipagem → encerramento → investigação** (dentro da severidade).",
            "",
        ]
        src = freg if not freg.empty else creg
        if not src.empty:
            lines += _bloco_por_acao(src, limite=20)
        if not lreg.empty:
            lines += ["", f"## Linkage DW ({len(lreg)})", ""]
            lprio = priorizar_fila(lreg)
            for _, r in lprio.head(10).iterrows():
                idc = r.get("id_caso", "")
                lines.append(
                    f"- {r.get('tipo_alerta')} · caso `{idc}` — {str(r.get('evidencia', ''))[:100]}"
                )

        lines += [
            "",
            "## Ações sugeridas (meningites / MS)",
            "1. Resolver quimioprofilaxia DM/Hib pendente (≤48h).",
            "2. Atualizar sorogrupo SINAN quando houver tipagem GAL.",
            "3. Encerrar casos próximos/além de 60 dias.",
            "4. Buscar resultado GAL/LACEN quando lab fraco ou match DW positivo.",
            "5. Completar investigação ≤48h.",
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

    # Perfil lab — tipagem + GAL positivo
    lab_fila = pd.DataFrame()
    if not link.empty:
        lab_fila = link[link["tipo_alerta"].astype(str).str.contains(
            "GAL|lab|Lab|SINAN|tipagem|sorogrupo", case=False, na=False
        )]
    tip_fila = _read("gal_fila_tipagem_sinan_v32.csv")
    if lab_fila.empty and not casos.empty:
        lab_fila = casos[casos["tipo_alerta"].astype(str).str.contains("laboratorial|GAL|tipagem|sorogrupo", case=False, na=False)]
    if not tip_fila.empty:
        tip_as_alert = tip_fila.rename(columns={
            "NumeroNotificacao": "id_caso",
            "acao_sugerida_v32": "acao_recomendada",
        }).copy()
        tip_as_alert["tipo_alerta"] = "Tipagem GAL — atualizar sorogrupo no SINAN"
        tip_as_alert["evidencia"] = (
            "GAL=" + tip_as_alert.get("gal_sorogrupo_nm", pd.Series(dtype=str)).astype(str)
        )
        lab_fila = pd.concat([lab_fila, tip_as_alert], ignore_index=True, sort=False)
    lab_fila = priorizar_fila(lab_fila) if not lab_fila.empty else lab_fila
    lines_lab = [
        "# Digest Laboratório / LACEN — Meningites",
        f"**Perfil:** LAB_REFERENCIA · **Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        f"Itens: **{len(lab_fila)}** (inclui tipagem GAL→SINAN quando disponível)",
        "",
    ]
    lines_lab += _bloco_por_acao(lab_fila, limite=40) if not lab_fila.empty else ["(sem itens)"]
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
            q = "Quais ações prioritárias do CIEVS para meningites conforme Informe MS e NT 154?"
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
