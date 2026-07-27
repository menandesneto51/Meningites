# -*- coding: utf-8 -*-
"""
13_alertas_inteligentes_v23.py
Alertas acionáveis alinhados ao Informe MS, Caderno SINAN e NT Conjunta 154/2024
(retifica/revoga a NT 97/2024).
"""

from __future__ import annotations

from datetime import timedelta
from importlib import import_module

import numpy as np
import pandas as pd
from meningites_v17_common import OUT, MISSING, load_base_v17, text_key

ms = import_module("12_indicadores_ms_operacionais_v23")

SEVERIDADE_ORDEM = {"Crítico": 4, "Alto": 3, "Atenção": 2, "Informativo": 1}
NORMA_NT154 = "NT Conjunta nº 154/2024-DPNI/SVSA/MS (retifica NT 97/2024)"


def _id_caso(df: pd.DataFrame) -> pd.Series:
    if "NumeroNotificacao" in df.columns:
        return df["NumeroNotificacao"].astype(str)
    return pd.Series([f"idx_{i}" for i in df.index], index=df.index)


def _append(rows, mask, base_cols, **kwargs):
    if not mask.any():
        return
    sub = base_cols.loc[mask].copy()
    for k, v in kwargs.items():
        sub[k] = v
    rows.append(sub)


def alertas_caso(df: pd.DataFrame) -> pd.DataFrame:
    d = ms._ensure_lead_times(df)
    hoje = pd.Timestamp.today().normalize()
    ids = _id_caso(d)
    clas = d.get("classificacao_agrupada_v17", pd.Series(index=d.index, dtype=object)).astype(str)
    conf = pd.to_numeric(d.get("confirmado_v17", 0), errors="coerce").fillna(0).astype(int)
    q_real = ms._quimio_realizada(d)
    notif = pd.to_datetime(d.get("data_notificacao_v17"), errors="coerce")
    dias_notif = (hoje - notif).dt.days

    base = pd.DataFrame({
        "id_caso": ids,
        "municipio_v17": d.get("municipio_v17", ""),
        "regional_v17": d.get("regional_v17", ""),
        "classificacao_agrupada_v17": clas,
    }, index=d.index)

    rows = []
    lt_inv = pd.to_numeric(d.get("lt_notificacao_investigacao_dias_v17"), errors="coerce")
    sem_inv = d.get("data_investigacao_v17").isna() if "data_investigacao_v17" in d.columns else pd.Series(True, index=d.index)
    m = sem_inv & notif.notna() & (dias_notif > 2)
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Investigação atrasada"
        sub["severidade"] = np.where(dias_notif.loc[m] > 7, "Alto", "Atenção")
        sub["evidencia"] = "Sem DataInvestigação; " + dias_notif.loc[m].astype(int).astype(str) + " dia(s) desde a notificação"
        sub["acao_recomendada"] = "Completar investigação epidemiológica e ficha SINAN (meta MS: ≤48h)."
        sub["prazo"] = "Imediato"
        sub["norma"] = "Informe Meningites 2024 — % investigados ≤48h"
        rows.append(sub)

    m = lt_inv.notna() & (lt_inv > 2)
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Investigação fora do prazo"
        sub["severidade"] = "Atenção"
        sub["evidencia"] = "Lead time investigação = " + lt_inv.loc[m].astype(int).astype(str) + " dia(s)"
        sub["acao_recomendada"] = "Revisar fluxo de investigação no município/regional."
        sub["prazo"] = "Semanal"
        sub["norma"] = "Informe Meningites 2024"
        rows.append(sub)

    lt_enc = pd.to_numeric(d.get("lt_notificacao_encerramento_dias_v17"), errors="coerce")
    sem_enc = d.get("data_encerramento_v17").isna() if "data_encerramento_v17" in d.columns else pd.Series(True, index=d.index)
    m = sem_enc & notif.notna() & (dias_notif >= 45)
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Encerramento em risco/atrasado"
        sub["severidade"] = np.where(dias_notif.loc[m] > 60, "Crítico", "Alto")
        sub["evidencia"] = "Caso aberto há " + dias_notif.loc[m].astype(int).astype(str) + " dia(s) (meta ≤60)"
        sub["acao_recomendada"] = "Priorizar encerramento com critério de confirmação e evolução preenchidos."
        sub["prazo"] = np.where(dias_notif.loc[m] <= 60, "Antes de D60", "Imediato")
        sub["norma"] = "Informe Meningites 2024 — % encerrados ≤60 dias"
        rows.append(sub)

    m = lt_enc.notna() & (lt_enc > 60)
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Encerramento fora do prazo"
        sub["severidade"] = "Atenção"
        sub["evidencia"] = "Lead time encerramento = " + lt_enc.loc[m].astype(int).astype(str) + " dia(s)"
        sub["acao_recomendada"] = "Avaliar causa do atraso e qualidade do encerramento."
        sub["prazo"] = "Mensal"
        sub["norma"] = "Informe Meningites 2024"
        rows.append(sub)

    # Quimio DM/Hib
    dm_hib = clas.isin(list(ms.DM_HIB))
    lt_q = pd.to_numeric(d.get("lt_notificacao_quimioprofilaxia_dias_v17"), errors="coerce")
    m = dm_hib & ~q_real
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Quimioprofilaxia ausente"
        sub["severidade"] = np.where(clas.loc[m].eq("Doença meningocócica"), "Crítico", "Alto")
        sub["evidencia"] = "Sem data/registro de quimioprofilaxia de comunicantes"
        sub["acao_recomendada"] = (
            "Identificar contatos próximos (NT 154/2024) e administrar quimioprofilaxia "
            "idealmente em ≤24–48h (rifampicina ou alternativa; Hib até 30 dias)."
        )
        sub["prazo"] = "≤24–48h"
        sub["norma"] = f"{NORMA_NT154}; Informe Meningites 2024"
        rows.append(sub)

    m = dm_hib & q_real & lt_q.notna() & (lt_q > 2)
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Quimioprofilaxia fora do prazo"
        sub["severidade"] = "Alto"
        sub["evidencia"] = "Quimio em " + lt_q.loc[m].astype(int).astype(str) + " dia(s) após notificação"
        sub["acao_recomendada"] = (
            "Revisar oportunidade; NT 154: valor limitado após 10 dias (DM); "
            "DIHib pode ir até 30 dias após exposição."
        )
        sub["prazo"] = "Imediato se ainda ≤10 dias da exposição (Hib ≤30d)"
        sub["norma"] = NORMA_NT154
        rows.append(sub)

    m = (~dm_hib) & q_real
    if m.any():
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Quimioprofilaxia inconsistente"
        sub["severidade"] = "Atenção"
        sub["evidencia"] = "Quimio registrada em etiologia sem indicação rotineira (só DM e Hib)"
        sub["acao_recomendada"] = "Auditar ficha SINAN — possível erro de classificação ou de quimio."
        sub["prazo"] = "Semanal"
        sub["norma"] = "Caderno de Análises SINAN — Meningites"
        rows.append(sub)

    # Vacinação complementar pós-DIHib (NT 154) — <2 anos
    hib = clas.eq("Meningite por Hib/Hemófilo")
    idade_raw = d.get("IdadePaciente", pd.Series(index=d.index, dtype=object)).astype(str)
    idade_anos = pd.Series(np.nan, index=d.index, dtype=float)
    m_a = idade_raw.str.contains(r"\d+\s*a", case=False, na=False)
    m_m = idade_raw.str.contains(r"\d+\s*m", case=False, na=False) & ~m_a
    m_d = idade_raw.str.contains(r"\d+\s*d", case=False, na=False) & ~m_a & ~m_m
    idade_anos.loc[m_a] = pd.to_numeric(idade_raw.loc[m_a].str.extract(r"(\d+)", expand=False), errors="coerce")
    idade_anos.loc[m_m] = pd.to_numeric(idade_raw.loc[m_m].str.extract(r"(\d+)", expand=False), errors="coerce") / 12.0
    idade_anos.loc[m_d] = pd.to_numeric(idade_raw.loc[m_d].str.extract(r"(\d+)", expand=False), errors="coerce") / 365.0
    m = hib & idade_anos.notna() & (idade_anos < 2)
    if m.any():
        vac = d.get("VacinaContraHemofilos", pd.Series(index=d.index, dtype=object)).astype(str)
        sub = base.loc[m].copy()
        sub["tipo_alerta"] = "Vacinação complementar pós-DIHib (<2 anos)"
        sub["severidade"] = np.where(
            vac.loc[m].str.lower().isin(["não", "nao", "não informado", "*em branco", "ignorado", "nan", ""]),
            "Alto",
            "Atenção",
        )
        sub["evidencia"] = (
            "DIHib em <2 anos (Idade=" + idade_raw.loc[m] + "; VacinaContraHemofilos=" + vac.loc[m] + ")"
        )
        sub["acao_recomendada"] = (
            "NT 154: iniciar/completar esquema Hib (penta/hexa) ou dose adicional se esquema completo "
            "(6m–<2a; intervalo ≥60d); iniciar ~30 dias após início da doença."
        )
        sub["prazo"] = "~30 dias após início da DIHib"
        sub["norma"] = NORMA_NT154
        rows.append(sub)

    # Lab fraco
    if "CriterioConfirmacao" in d.columns:
        flags = ms._criterio_lab_flags(d["CriterioConfirmacao"])
        m = (conf == 1) & clas.isin(list(ms.BACTERIANAS)) & ~flags["lab_informe"]
        if m.any():
            sub = base.loc[m].copy()
            sub["tipo_alerta"] = "Confirmação laboratorial fraca"
            sub["severidade"] = "Atenção"
            sub["evidencia"] = "CritérioConfirmacao=" + d.loc[m, "CriterioConfirmacao"].astype(str)
            sub["acao_recomendada"] = "Buscar resultado LACEN/GAL (cultura/PCR) e atualizar encerramento."
            sub["prazo"] = "Semanal"
            sub["norma"] = "Informe Meningites 2024 / Caderno SINAN"
            rows.append(sub)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["severidade_ordem"] = out["severidade"].map(SEVERIDADE_ORDEM).fillna(0)
    return out.sort_values(["severidade_ordem", "tipo_alerta", "municipio_v17"], ascending=[False, True, True])


def alertas_surto_nt97(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    clas = d.get("classificacao_agrupada_v17", pd.Series(dtype=object)).astype(str)
    dm = d[clas.eq("Doença meningocócica")].copy()
    if dm.empty:
        return pd.DataFrame()

    soro_col = next(
        (c for c in dm.columns if c == "SeNMeningiditisEspecificarSorogrupo" or "sorogrupo" in c.lower()),
        None,
    )
    if soro_col is None:
        dm["sorogrupo_alerta"] = "Não informado"
    else:
        dm["sorogrupo_alerta"] = dm[soro_col].fillna("Não informado").astype(str).str.strip()
        dm.loc[
            dm["sorogrupo_alerta"].str.lower().isin(MISSING) | (dm["sorogrupo_alerta"] == ""),
            "sorogrupo_alerta",
        ] = "Não informado"

    if "CriterioConfirmacao" in dm.columns:
        dm["lab_pcr_cultura"] = ms._criterio_lab_flags(dm["CriterioConfirmacao"])["lab_informe"].values
    else:
        dm["lab_pcr_cultura"] = False

    dm = dm[dm["lab_pcr_cultura"]].copy()
    if dm.empty:
        return pd.DataFrame()

    dm["data_ref_v17"] = pd.to_datetime(dm["data_ref_v17"], errors="coerce")
    dm = dm.dropna(subset=["data_ref_v17"])
    if dm.empty:
        return pd.DataFrame()

    max_date = dm["data_ref_v17"].max()
    recent = dm[dm["data_ref_v17"].between(max_date - timedelta(days=90), max_date)].copy()

    # Incidência esperada: média anual DM lab+ dos 5 anos anteriores (NT 154)
    pop_lookup = {}
    if "populacao_v17" in d.columns and "codigo_municipio_v17" in d.columns:
        tmp = d[["ano_evento_v17", "codigo_municipio_v17", "populacao_v17"]].copy()
        tmp["ano_evento_v17"] = pd.to_numeric(tmp["ano_evento_v17"], errors="coerce")
        tmp["populacao_v17"] = pd.to_numeric(tmp["populacao_v17"], errors="coerce")
        for (ano, cod), gpop in tmp.groupby(["ano_evento_v17", "codigo_municipio_v17"], dropna=False):
            popv = gpop["populacao_v17"].max()
            if pd.notna(ano) and pd.notna(popv) and popv > 0:
                pop_lookup[(int(ano), str(cod))] = float(popv)

    hist_years = list(range(int(max_date.year) - 5, int(max_date.year)))
    hist_dm = dm[dm["data_ref_v17"].dt.year.isin(hist_years)]
    if not hist_dm.empty:
        hist_counts = (
            hist_dm.groupby(["codigo_municipio_v17", hist_dm["data_ref_v17"].dt.year])
            .size()
            .rename("n")
            .reset_index()
        )
        hist_counts = hist_counts.rename(columns={hist_counts.columns[1]: "ano"})
    else:
        hist_counts = pd.DataFrame(columns=["codigo_municipio_v17", "ano", "n"])

    rows = []
    group_keys = [k for k in ["codigo_municipio_v17", "municipio_v17", "regional_v17", "sorogrupo_alerta"] if k in recent.columns]
    for keys, g in recent.groupby(group_keys, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n = len(g)
        if n < 3:
            continue
        meta = {k: v for k, v in zip(group_keys, keys)}
        soro = str(meta.get("sorogrupo_alerta", ""))
        cod = str(meta.get("codigo_municipio_v17", ""))

        pops = [pop_lookup.get((y, cod)) for y in hist_years if pop_lookup.get((y, cod))]
        pop_now = pop_lookup.get((int(max_date.year), cod))
        if pop_now is None and pops:
            pop_now = pops[-1]
        if hist_counts.empty:
            media_hist = np.nan
        else:
            subh = hist_counts[hist_counts["codigo_municipio_v17"].astype(str).eq(cod)]
            media_hist = float(subh["n"].mean()) if not subh.empty else 0.0
        inc_atual = (n / pop_now * 100000) if pop_now and pop_now > 0 else np.nan
        inc_esp = (media_hist / pop_now * 100000) if pop_now and pop_now > 0 and pd.notna(media_hist) else np.nan
        acima_esperado = pd.notna(inc_atual) and pd.notna(inc_esp) and inc_atual > inc_esp

        g2 = g.copy()
        g2["semana"] = g2["data_ref_v17"].dt.isocalendar().week.astype(int)
        sem = g2.groupby("semana").size()
        dobra = False
        if len(sem) >= 2:
            vals = sem.sort_index().values
            dobra = any(vals[i] >= 2 * vals[i - 1] and vals[i - 1] >= 1 for i in range(1, len(vals)))

        if soro.startswith("Não informado"):
            sev, tipo = "Atenção", "Aglomerado DM sem sorogrupo (avaliar NT 154)"
        elif acima_esperado or dobra or media_hist == 0:
            sev, tipo = "Crítico", "Surto comunitário DM — critério NT 154/2024"
        else:
            sev, tipo = "Alto", "Aglomerado DM lab+ (avaliar surto NT 154)"

        evidencia = (
            f"{n} casos DM lab+ (cultura/PCR), sorogrupo={soro}, janela ≤90 dias no mesmo município"
        )
        if pd.notna(inc_atual):
            evidencia += f"; incidência atual≈{inc_atual:.2f}/100 mil"
        if pd.notna(inc_esp):
            evidencia += f" vs esperada≈{inc_esp:.2f}/100 mil (média 5 anos)"
        if dobra:
            evidencia += "; sinal de duplicação semanal"

        rows.append({
            "tipo_alerta": tipo,
            "severidade": sev,
            "municipio_v17": meta.get("municipio_v17", ""),
            "regional_v17": meta.get("regional_v17", ""),
            "codigo_municipio_v17": cod,
            "sorogrupo": soro,
            "n_casos_90d_lab": n,
            "incidencia_atual_100mil": inc_atual,
            "incidencia_esperada_100mil": inc_esp,
            "acima_incidencia_esperada": bool(acima_esperado),
            "duplicacao_semanal": bool(dobra),
            "periodo_inicio": g["data_ref_v17"].min(),
            "periodo_fim": g["data_ref_v17"].max(),
            "evidencia": evidencia,
            "acao_recomendada": (
                "Discutir nos três níveis; avaliar incidência vs canal endêmico; "
                "considerar quimioprofilaxia ampliada e vacinação conforme GVS/NT 154."
            ),
            "prazo": "Imediato CIEVS",
            "norma": f"{NORMA_NT154} — surto comunitário DM",
        })

    inst_col = next(
        (c for c in dm.columns if any(x in c.lower() for x in ["institu", "escola", "creche"])),
        None,
    )
    if inst_col:
        recent2 = recent[recent[inst_col].notna() & ~recent[inst_col].astype(str).str.lower().isin(MISSING)]
        gk = [k for k in ["codigo_municipio_v17", "municipio_v17", inst_col, "sorogrupo_alerta"] if k in recent2.columns]
        for keys, g in recent2.groupby(gk, dropna=False):
            if len(g) < 2:
                continue
            if not isinstance(keys, tuple):
                keys = (keys,)
            meta = {k: v for k, v in zip(gk, keys)}
            rows.append({
                "tipo_alerta": "Surto institucional DM — critério NT 154/2024",
                "severidade": "Crítico",
                "municipio_v17": meta.get("municipio_v17", ""),
                "regional_v17": "",
                "codigo_municipio_v17": meta.get("codigo_municipio_v17", ""),
                "sorogrupo": meta.get("sorogrupo_alerta", ""),
                "n_casos_90d_lab": len(g),
                "incidencia_atual_100mil": np.nan,
                "incidencia_esperada_100mil": np.nan,
                "acima_incidencia_esperada": False,
                "duplicacao_semanal": False,
                "periodo_inicio": g["data_ref_v17"].min(),
                "periodo_fim": g["data_ref_v17"].max(),
                "evidencia": f"{len(g)} casos DM lab+ na instituição {meta.get(inst_col)} (≤90 dias)",
                "acao_recomendada": "Investigação institucional + quimioprofilaxia ampliada conforme NT 154.",
                "prazo": "Imediato CIEVS",
                "norma": f"{NORMA_NT154} — surto institucional DM",
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["severidade_ordem"] = out["severidade"].map(SEVERIDADE_ORDEM).fillna(0)
    return out.sort_values(["severidade_ordem", "n_casos_90d_lab"], ascending=[False, False])


def resumo_alertas(casos: pd.DataFrame, surtos: pd.DataFrame) -> pd.DataFrame:
    parts = []
    if not casos.empty:
        g = casos.groupby(["tipo_alerta", "severidade"], dropna=False).size().reset_index(name="n")
        g["origem"] = "caso"
        parts.append(g)
    if not surtos.empty:
        g = surtos.groupby(["tipo_alerta", "severidade"], dropna=False).size().reset_index(name="n")
        g["origem"] = "surto_nt154"
        parts.append(g)
    if not parts:
        return pd.DataFrame(columns=["origem", "tipo_alerta", "severidade", "n"])
    return pd.concat(parts, ignore_index=True).sort_values("n", ascending=False)


def main():
    df = load_base_v17()
    if df.empty:
        raise SystemExit("Base ausente.")

    casos = alertas_caso(df)
    surtos = alertas_surto_nt97(df)
    resumo = resumo_alertas(casos, surtos)

    casos.to_csv(OUT / "alertas_inteligentes_casos_v23.csv", index=False, encoding="utf-8-sig")
    if surtos.empty:
        surtos = pd.DataFrame(columns=[
            "tipo_alerta", "severidade", "municipio_v17", "regional_v17", "codigo_municipio_v17",
            "sorogrupo", "n_casos_90d_lab", "incidencia_atual_100mil", "incidencia_esperada_100mil",
            "acima_incidencia_esperada", "duplicacao_semanal", "periodo_inicio", "periodo_fim",
            "evidencia", "acao_recomendada", "prazo", "norma", "severidade_ordem",
        ])
    surtos.to_csv(OUT / "alertas_inteligentes_surtos_nt97_v23.csv", index=False, encoding="utf-8-sig")
    resumo.to_csv(OUT / "alertas_inteligentes_resumo_v23.csv", index=False, encoding="utf-8-sig")

    fila = []
    if not surtos.empty:
        for _, r in surtos.iterrows():
            fila.append({
                "prioridade": r["severidade"],
                "tipo": r["tipo_alerta"],
                "territorio": r.get("municipio_v17", ""),
                "evidencia": r.get("evidencia", ""),
                "acao": r.get("acao_recomendada", ""),
                "prazo": r.get("prazo", ""),
            })
    if not casos.empty:
        top = casos[casos["severidade"].isin(["Crítico", "Alto"])].head(200)
        for _, r in top.iterrows():
            fila.append({
                "prioridade": r["severidade"],
                "tipo": r["tipo_alerta"],
                "territorio": f"{r.get('municipio_v17', '')} | caso {r.get('id_caso', '')}",
                "evidencia": r.get("evidencia", ""),
                "acao": r.get("acao_recomendada", ""),
                "prazo": r.get("prazo", ""),
            })
    fila_df = pd.DataFrame(fila)
    if not fila_df.empty:
        fila_df["ordem"] = fila_df["prioridade"].map(SEVERIDADE_ORDEM).fillna(0)
        fila_df = fila_df.sort_values("ordem", ascending=False).drop(columns=["ordem"])
    fila_df.to_csv(OUT / "alertas_inteligentes_fila_cievs_v23.csv", index=False, encoding="utf-8-sig")

    print("[OK] Alertas inteligentes V23 gerados.")
    print(f"  Casos: {len(casos)} | Surtos NT154: {len(surtos)} | Fila CIEVS: {len(fila_df)}")
    if not resumo.empty:
        print(resumo.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
