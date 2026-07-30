# -*- coding: utf-8 -*-
"""
15_boletim_semanal_rascunho_v23.py
Gera rascunho de boletim semanal CIEVS a partir dos KPIs MS e alertas (sem LLM).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from meningites_v17_common import OUT, REL, fmt_num


def _read(name: str) -> pd.DataFrame:
    p = OUT / name
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def main():
    ms = _read("indicadores_ms_operacionais_v23.csv")
    fila = _read("alertas_inteligentes_fila_cievs_v23.csv")
    resumo_al = _read("alertas_inteligentes_resumo_v23.csv")
    surtos = _read("alertas_inteligentes_surtos_nt154_v23.csv")
    if surtos.empty:
        surtos = _read("alertas_inteligentes_surtos_nt97_v23.csv")
    kpis = _read("kpis_semanais_v17.csv")
    epi = _read("painel_epi_resumo_ano_v23.csv")
    meta = _read("painel_epi_meta_v23.csv")

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "# Boletim semanal — Meningites | CIEVS-MT (rascunho automático V23)",
        "",
        f"**Gerado em:** {hoje}",
        "**Fontes:** SINAN (base única), indicadores MS (Informe/Caderno), NT 154/2024, canal de alertas V23.",
        "",
        "> Documento de apoio à vigilância. Validar com a equipe antes de divulgação oficial.",
        "",
        "## 1. Indicadores operacionais (Ministério da Saúde)",
        "",
    ]

    if ms.empty:
        lines.append("_Indicadores MS indisponíveis. Rode `12_indicadores_ms_operacionais_v23.py`._")
    else:
        lines.append("| Indicador | MT (%) | Ref. Brasil 2024 | Semáforo |")
        lines.append("|---|---:|---:|---|")
        for _, r in ms.iterrows():
            if str(r.get("indicador", "")).startswith("pct_confirmacao_laboratorial_caderno"):
                continue
            ref = r.get("referencia_brasil_2024")
            ref_s = fmt_num(ref) if pd.notna(ref) else "—"
            lines.append(
                f"| {r.get('indicador_rotulo','')} | {fmt_num(r.get('valor_pct'))} | {ref_s} | {r.get('semaforo','—')} |"
            )
        lines.append("")

    lines += ["## 2. Situação epidemiológica (confirmados)", ""]
    if epi.empty:
        lines.append("_Painel epidemiológico indisponível. Rode `14_painel_epidemiologico_ms_v23.py`._")
    else:
        ano_ref = int(meta.iloc[0]["ano_referencia"]) if not meta.empty else int(epi["ano_evento_v17"].max())
        row = epi[epi["ano_evento_v17"] == ano_ref]
        if row.empty:
            row = epi.tail(1)
        r = row.iloc[0]
        lines.append(f"**Ano de referência:** {int(r['ano_evento_v17'])}")
        lines.append("")
        lines.append(f"- Confirmados: **{fmt_num(r.get('confirmados'), 0)}**")
        lines.append(f"- Óbitos por meningite: **{fmt_num(r.get('obitos_meningite'), 0)}**")
        lines.append(f"- Incidência: **{fmt_num(r.get('incidencia_100mil'))}** / 100 mil hab.")
        lines.append(f"- Mortalidade: **{fmt_num(r.get('mortalidade_100mil'))}** / 100 mil hab.")
        lines.append(f"- Letalidade: **{fmt_num(r.get('letalidade_pct'))}%**")
        lines.append(
            f"- Bacterianas — incidência {fmt_num(r.get('incidencia_bacteriana_100mil'))}/100 mil; "
            f"letalidade {fmt_num(r.get('letalidade_bacteriana_pct'))}%"
        )
        lines.append("")

    lines += ["## 3. KPIs da semana epidemiológica fechada", ""]
    if kpis.empty:
        lines.append("_KPIs semanais indisponíveis._")
    else:
        for _, r in kpis.iterrows():
            lines.append(
                f"- {r.get('indicador_rotulo')}: {fmt_num(r.get('valor_atual_fechado'))} "
                f"({r.get('semaforo')} vs semana anterior: {fmt_num(r.get('variacao_percentual'))}%)"
            )
        lines.append("")

    lines += ["## 4. Alertas e fila CIEVS", ""]
    if not surtos.empty and len(surtos) > 0:
        lines.append(f"**Sinais de surto NT 154/2024:** {len(surtos)}")
        for _, r in surtos.head(10).iterrows():
            lines.append(f"- [{r.get('severidade')}] {r.get('tipo_alerta')} — {r.get('municipio_v17')}: {r.get('evidencia')}")
        lines.append("")
    else:
        lines.append("Nenhum surto comunitário/institucional de DM detectado pelos critérios NT 154 nesta rodada.")
        lines.append("")

    if not resumo_al.empty:
        lines.append("### Volume de alertas")
        lines.append("")
        lines.append("| Tipo | Severidade | N |")
        lines.append("|---|---|---:|")
        for _, r in resumo_al.head(15).iterrows():
            lines.append(f"| {r.get('tipo_alerta')} | {r.get('severidade')} | {fmt_num(r.get('n'), 0)} |")
        lines.append("")

    if not fila.empty:
        lines.append("### Top 15 da fila prioritária")
        lines.append("")
        for i, r in fila.head(15).iterrows():
            lines.append(
                f"{i+1 if isinstance(i, int) else ''}. **{r.get('prioridade')}** — {r.get('tipo')} | "
                f"{r.get('territorio')} — {r.get('evidencia')} → _{r.get('acao')}_ (prazo: {r.get('prazo')})"
            )
        lines.append("")
    else:
        lines.append("Fila prioritária vazia ou não gerada.")
        lines.append("")

    backlog = _read("backlog_operacional_resumo_v25.csv")
    link = _read("linkage_completude_kpis_v25.csv")
    grav = _read("gravidade_letalidade_se_corrente_v25.csv")
    if not backlog.empty or not link.empty or not grav.empty:
        lines += ["## 4b. Operação avançada (V25)", ""]
        if not backlog.empty:
            r = backlog.iloc[0]
            lines.append(
                f"- Backlog: abertos **{fmt_num(r.get('casos_abertos'), 0)}**; "
                f"inv. atrasada **{fmt_num(r.get('investigacao_atrasada'), 0)}**; "
                f"quimio pendente DM/Hib **{fmt_num(r.get('quimio_pendente_dm_hib'), 0)}**"
            )
        if not link.empty:
            e = link[link["escopo"].astype(str).eq("ESTADUAL")]
            if not e.empty:
                r = e.iloc[0]
                lines.append(
                    f"- Linkage: GAL **{fmt_num(r.get('pct_match_gal'))}%**; "
                    f"discordância SIM **{fmt_num(r.get('n_discordancia_sim_sem_sinan'), 0)}**"
                )
        if not grav.empty:
            tot = grav[grav["classificacao_agrupada_v17"].astype(str).eq("TOTAL")]
            if not tot.empty:
                r = tot.iloc[0]
                lines.append(
                    f"- Gravidade SE {fmt_num(r.get('semana_epi'), 0)}/{fmt_num(r.get('ano'), 0)}: "
                    f"letalidade **{fmt_num(r.get('letalidade_pct'))}%**; "
                    f"óbitos <7d **{fmt_num(r.get('obitos_lt_7d'), 0)}**"
                )
        lines.append("")
        lines.append("Ver também `relatorios/BOLETIM_CIEVS_MENINGITES_ENVIO_V25.md`.")
        lines.append("")

    lines += [
        "## 5. Recomendações operacionais",
        "",
        "1. Priorizar casos com **encerramento >60 dias** e **investigação >48h** (indicadores MS).",
        "2. Para **doença meningocócica** sem quimioprofilaxia: aplicar NT 154/2024 (contatos próximos, ≤24–48h).",
        "3. Buscar resultado **cultura/PCR** em bacterianas confirmadas sem critério laboratorial.",
        "4. Monitorar canal endêmico e agregados territoriais na aba de surtos do dashboard.",
        "",
        "---",
        "*Rascunho gerado automaticamente pelo Robô de Meningites V23 — CIEVS-MT.*",
    ]

    text = "\n".join(lines)
    out_md = REL / "BOLETIM_SEMANAL_MENINGITES_V23_RASCUNHO.md"
    out_md.write_text(text, encoding="utf-8")
    (OUT / "boletim_semanal_rascunho_v23.md").write_text(text, encoding="utf-8")
    print(f"[OK] Boletim rascunho gerado: {out_md}")


if __name__ == "__main__":
    main()
