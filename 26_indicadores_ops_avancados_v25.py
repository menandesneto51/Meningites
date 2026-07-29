# -*- coding: utf-8 -*-
"""
26_indicadores_ops_avancados_v25.py
Roadmap CIEVS-MT: quimio Hib, backlog, linkage, sorogrupos, score NT154,
PL/lab, vacinação elegíveis, gravidade SE, bloco boletim.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, MISSING, fmt_num, load_base_v17, text_key, simnao_bin
import importlib

ms = importlib.import_module("12_indicadores_ms_operacionais_v23")

MODULO = "26_indicadores_ops_avancados_v25.py"

BACT = ms.BACTERIANAS
DM = "Doença meningocócica"
HIB = "Meningite por Hib/Hemófilo"
PNEUMO = "Meningite pneumocócica"


def _filled(s: pd.Series) -> pd.Series:
    return s.notna() & ~s.astype(str).str.strip().str.lower().isin(MISSING)


def _pct(n, d):
    if d is None or d == 0 or pd.isna(d):
        return np.nan
    return float(n) / float(d) * 100


def _soro_col(df: pd.DataFrame) -> str | None:
    return next((c for c in df.columns if "sorogrupo" in c.lower() or "SeNMeningiditis" in c), None)


def _norm_soro(val) -> str:
    if pd.isna(val):
        return "Não informado"
    t = text_key(str(val))
    if not t or t in {"IGNORADO", "9", "99", "NAO INFORMADO", "SEM INFORMACAO"}:
        return "Não informado"
    for g in ["W135", "W", "Y", "C", "B", "A", "X"]:
        if t == g or t.startswith(g + " ") or f" {g} " in f" {t} " or t.endswith(g):
            if g == "W135":
                return "W"
            return g
    if "MENINGITIDIS" in t or "NEISSERIA" in t:
        return "Outro/esp."
    return str(val).strip()[:40] or "Não informado"


def _pl_realizada(df: pd.DataFrame) -> pd.Series:
    flag = pd.Series(False, index=df.index)
    if "data_puncao_lombar_v17" in df.columns:
        flag = flag | pd.to_datetime(df["data_puncao_lombar_v17"], errors="coerce").notna()
    if "PuncaoLombar" in df.columns:
        s = df["PuncaoLombar"]
        if pd.api.types.is_numeric_dtype(s):
            flag = flag | (pd.to_numeric(s, errors="coerce") == 1)
        else:
            k = s.astype(str).map(text_key)
            flag = flag | k.isin(["1", "SIM", "S", "REALIZADA"])
    return flag


def _lab_pendente(df: pd.DataFrame) -> pd.Series:
    """Resultado lab vazio em quem fez PL ou é bacteriana/DM."""
    result_cols = [
        c for c in df.columns
        if c.startswith("Resultado")
        and any(x in c for x in ("PCR", "Cultura", "CIE", "Latex", "Bacterioscopia"))
    ]
    if not result_cols:
        return pd.Series(False, index=df.index)
    any_filled = pd.Series(False, index=df.index)
    for c in result_cols:
        any_filled = any_filled | _filled(df[c])
    return ~any_filled


def build_hib_and_extend_ms(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores MS enriquecidos com o KPI Hib.

    Grava a versão própria do módulo 26 (`indicadores_ms_operacionais_v25.csv`)
    e mantém o nome legado (`..._v23.csv`) atualizado apenas para não quebrar o
    painel. A cópia canônica do módulo 12 (`..._base_v23.csv`) fica intocada,
    de modo que a divergência entre os dois módulos é sempre auditável pelas
    colunas `modulo_origem` / `gerado_em`.
    """
    d = ms._ensure_lead_times(df)
    clas = d["classificacao_agrupada_v17"].astype(str)
    hib = clas.eq(HIB)
    n_hib = int(hib.sum())
    lt_q = pd.to_numeric(d.get("lt_notificacao_quimioprofilaxia_dias_v17"), errors="coerce")
    q_real = ms._quimio_realizada(d)
    n_hib_48 = int((hib & lt_q.notna() & (lt_q >= 0) & (lt_q <= 2)).sum())
    n_hib_any = int((hib & q_real).sum())
    pct_hib = _pct(n_hib_48, n_hib)

    # reload current MS frame and append/replace Hib row
    painel = ms.kpis_to_frame(ms.compute_ms_kpis(d))
    hib_row = {
        "indicador": "pct_quimioprofilaxia_hib_48h",
        "indicador_rotulo": "% meningite Hib/Hemófilo com quimioprofilaxia ≤48h",
        "numerador": n_hib_48,
        "denominador": n_hib,
        "valor_pct": pct_hib,
        "referencia_brasil_2024": np.nan,
        "semaforo": ms._semaforo_vs_ref(pct_hib, 45.5, tol=5.0) if n_hib else "Cinza",
        "fonte": "NT 154/2024 — quimioprofilaxia em Hib",
        "interpretacao": (
            f"{fmt_num(pct_hib)}% dos casos Hib com quimio ≤48h "
            f"(qualquer quimio: {fmt_num(_pct(n_hib_any, n_hib))}%; n={n_hib})."
        ),
        "quimioprofilaxia_indevida_n": painel["quimioprofilaxia_indevida_n"].iloc[0] if len(painel) else 0,
    }
    painel = painel[painel["indicador"] != "pct_quimioprofilaxia_hib_48h"]
    painel = pd.concat([painel, pd.DataFrame([hib_row])], ignore_index=True)
    painel = ms.anotar_procedencia(ms.anotar_referencia(painel), MODULO)
    painel.to_csv(OUT / "indicadores_ms_operacionais_v25.csv", index=False, encoding="utf-8-sig")
    # Alias de compatibilidade do painel; pode ser removido quando o dashboard
    # passar a ler indicadores_ms_operacionais_v25.csv.
    painel.to_csv(OUT / "indicadores_ms_operacionais_v23.csv", index=False, encoding="utf-8-sig")

    base_resumo = OUT / "indicadores_ms_operacionais_resumo_base_v23.csv"
    legado_resumo = OUT / "indicadores_ms_operacionais_resumo_v23.csv"
    fonte_resumo = base_resumo if base_resumo.exists() else legado_resumo
    resumo = pd.read_csv(fonte_resumo) if fonte_resumo.exists() else pd.DataFrame([ms.compute_ms_kpis(d)])
    resumo["hib_casos"] = n_hib
    resumo["hib_quimio_48h"] = n_hib_48
    resumo["pct_quimioprofilaxia_hib_48h"] = pct_hib
    resumo = ms.anotar_procedencia(ms.anotar_referencia(resumo), MODULO)
    resumo.to_csv(OUT / "indicadores_ms_operacionais_resumo_v25.csv", index=False, encoding="utf-8-sig")
    resumo.to_csv(legado_resumo, index=False, encoding="utf-8-sig")
    return painel


def build_backlog(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = ms._ensure_lead_times(df)
    today = pd.Timestamp(datetime.now().date())
    notif = pd.to_datetime(d.get("data_notificacao_v17"), errors="coerce")
    idade = (today - notif).dt.days
    clas = d["classificacao_agrupada_v17"].astype(str)
    q_real = ms._quimio_realizada(d)
    lt_inv = pd.to_numeric(d.get("lt_notificacao_investigacao_dias_v17"), errors="coerce")
    lt_enc = pd.to_numeric(d.get("lt_notificacao_encerramento_dias_v17"), errors="coerce")
    sem_inv = lt_inv.isna() | (lt_inv > 2)
    # aberto: sem encerramento ou lead > 60 ainda aberto se sem data
    sem_enc = d["data_encerramento_v17"].isna() if "data_encerramento_v17" in d.columns else lt_enc.isna()
    abertos = sem_enc.fillna(True)
    inv_atrasada = abertos & sem_inv & idade.notna() & (idade >= 2)
    enc_risco = abertos & idade.notna() & (idade >= 45) & (idade <= 60)
    enc_atrasado = abertos & idade.notna() & (idade > 60)
    dm_hib = clas.isin([DM, HIB])
    quimio_pend = dm_hib & ~q_real & abertos

    d = d.copy()
    d["_inv_atrasada"] = inv_atrasada.astype(int)
    d["_enc_risco"] = enc_risco.astype(int)
    d["_enc_atrasado"] = enc_atrasado.astype(int)
    d["_quimio_pend"] = quimio_pend.astype(int)
    d["_aberto"] = abertos.astype(int)

    geo = "regional_v17" if "regional_v17" in d.columns else None
    if geo:
        g = d.groupby(geo, dropna=False).agg(
            casos_abertos=("_aberto", "sum"),
            investigacao_atrasada=("_inv_atrasada", "sum"),
            encerramento_d45_d60=("_enc_risco", "sum"),
            encerramento_gt60=("_enc_atrasado", "sum"),
            quimio_pendente_dm_hib=("_quimio_pend", "sum"),
        ).reset_index()
    else:
        g = pd.DataFrame([{
            "regional_v17": "ESTADUAL",
            "casos_abertos": int(abertos.sum()),
            "investigacao_atrasada": int(inv_atrasada.sum()),
            "encerramento_d45_d60": int(enc_risco.sum()),
            "encerramento_gt60": int(enc_atrasado.sum()),
            "quimio_pendente_dm_hib": int(quimio_pend.sum()),
        }])

    resumo = pd.DataFrame([{
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "casos_abertos": int(abertos.sum()),
        "investigacao_atrasada": int(inv_atrasada.sum()),
        "encerramento_d45_d60": int(enc_risco.sum()),
        "encerramento_gt60": int(enc_atrasado.sum()),
        "quimio_pendente_dm_hib": int(quimio_pend.sum()),
        "hib_sem_quimio": int((clas.eq(HIB) & ~q_real).sum()),
        "dm_sem_quimio": int((clas.eq(DM) & ~q_real).sum()),
    }])
    return g, resumo


def build_linkage_kpis(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # Prefer flags do enriquecimento DW (mais confiáveis que a base crua)
    enr_path = OUT / "enriquecimento_casos_dw_v23.csv"
    if enr_path.exists() and "NumeroNotificacao" in d.columns:
        try:
            enr = pd.read_csv(enr_path, encoding="utf-8-sig", low_memory=False)
            cols = [c for c in [
                "NumeroNotificacao", "dw_gal_match_v23", "dw_gal_positivo_v23",
                "dw_sim_match_v23", "obito_sim_link_v23", "obito_meningite_uniao_v23",
                "obito_sim_sem_sinan_v23",
            ] if c in enr.columns]
            if "NumeroNotificacao" in cols and len(cols) > 1:
                enr = enr[cols].drop_duplicates("NumeroNotificacao", keep="first")
                enr["NumeroNotificacao"] = enr["NumeroNotificacao"].astype(str).str.strip()
                d["NumeroNotificacao"] = d["NumeroNotificacao"].astype(str).str.strip()
                drop_cols = [c for c in cols if c != "NumeroNotificacao" and c in d.columns]
                if drop_cols:
                    d = d.drop(columns=drop_cols)
                d = d.merge(enr, on="NumeroNotificacao", how="left")
        except Exception:
            pass

    clas = d.get("classificacao_agrupada_v17", pd.Series(dtype=object)).astype(str)
    conf = pd.to_numeric(d.get("confirmado_v17"), errors="coerce").fillna(0).astype(int)
    gal = pd.to_numeric(d.get("dw_gal_match_v23"), errors="coerce").fillna(0).astype(int) if "dw_gal_match_v23" in d.columns else pd.Series(0, index=d.index)
    sim = pd.to_numeric(d.get("obito_sim_link_v23"), errors="coerce").fillna(0).astype(int) if "obito_sim_link_v23" in d.columns else (
        pd.to_numeric(d.get("dw_sim_match_v23"), errors="coerce").fillna(0).astype(int) if "dw_sim_match_v23" in d.columns else pd.Series(0, index=d.index)
    )
    sinan_ob = pd.to_numeric(d.get("obito_meningite_v17"), errors="coerce").fillna(0).astype(int)
    uniao = pd.to_numeric(d.get("obito_meningite_uniao_v23"), errors="coerce").fillna(0).astype(int) if "obito_meningite_uniao_v23" in d.columns else ((sinan_ob == 1) | (sim == 1)).astype(int)
    discord = (sim == 1) & (sinan_ob == 0)
    bact = clas.isin(BACT) & (conf == 1)

    rows = []
    def add(scope, mask):
        n = int(mask.sum())
        if n == 0 and scope != "ESTADUAL":
            return
        m = mask if scope != "ESTADUAL" else pd.Series(True, index=d.index)
        nn = int(m.sum())
        rows.append({
            "escopo": scope,
            "n_casos": nn,
            "pct_match_gal": _pct(int(gal[m].sum()), nn),
            "pct_bact_lab_com_gal": _pct(int((bact & (gal == 1) & m).sum()), int((bact & m).sum())),
            "pct_obitos_sim_sobre_uniao": _pct(int(sim[m].sum()), int(uniao[m].sum())),
            "pct_discordancia_sim_sem_sinan": _pct(int(discord[m].sum()), nn),
            "n_discordancia_sim_sem_sinan": int(discord[m].sum()),
            "n_sim_link": int(sim[m].sum()),
            "n_obitos_uniao": int(uniao[m].sum()),
        })

    add("ESTADUAL", pd.Series(True, index=d.index))
    if "regional_v17" in d.columns:
        for reg, g in d.groupby("regional_v17", dropna=False):
            add(str(reg), d.index.isin(g.index))
    return pd.DataFrame(rows)


def build_sorogrupos(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df.copy()
    dm = d["classificacao_agrupada_v17"].astype(str).eq(DM)
    col = _soro_col(d)
    if not dm.any() or col is None:
        empty = pd.DataFrame(columns=["ano_evento_v17", "semana_epi_v17", "sorogrupo", "casos"])
        return empty, pd.DataFrame([{"alerta": "Sem dados de sorogrupo DM"}])

    sub = d.loc[dm].copy()
    sub["sorogrupo_norm_v25"] = sub[col].map(_norm_soro)
    if "semana_epi_v17" not in sub.columns:
        sub["semana_epi_v17"] = pd.to_datetime(sub.get("data_ref_v17"), errors="coerce").dt.isocalendar().week
    if "ano_evento_v17" not in sub.columns:
        sub["ano_evento_v17"] = pd.to_datetime(sub.get("data_ref_v17"), errors="coerce").dt.year

    trend = (
        sub.groupby(["ano_evento_v17", "semana_epi_v17", "sorogrupo_norm_v25"], dropna=False)
        .size().reset_index(name="casos")
        .rename(columns={"sorogrupo_norm_v25": "sorogrupo"})
        .sort_values(["ano_evento_v17", "semana_epi_v17", "casos"], ascending=[True, True, False])
    )
    dist = sub["sorogrupo_norm_v25"].value_counts(dropna=False).rename_axis("sorogrupo").reset_index(name="casos")
    dist["pct"] = dist["casos"] / dist["casos"].sum() * 100

    # Alerta mudança: comparar último ano completo vs anterior na proporção do sorogrupo dominante
    alertas = []
    anos = sorted(pd.to_numeric(sub["ano_evento_v17"], errors="coerce").dropna().unique())
    if len(anos) >= 2:
        a1, a0 = int(anos[-1]), int(anos[-2])
        for a, label in [(a1, "atual"), (a0, "anterior")]:
            pass
        p1 = sub[sub["ano_evento_v17"] == a1]["sorogrupo_norm_v25"].value_counts(normalize=True)
        p0 = sub[sub["ano_evento_v17"] == a0]["sorogrupo_norm_v25"].value_counts(normalize=True)
        for soro in set(p1.index) | set(p0.index):
            if soro == "Não informado":
                continue
            dlt = float(p1.get(soro, 0) - p0.get(soro, 0))
            if abs(dlt) >= 0.10:
                alertas.append({
                    "tipo": "mudanca_perfil_sorogrupo",
                    "sorogrupo": soro,
                    "ano_atual": a1,
                    "ano_anterior": a0,
                    "pct_atual": float(p1.get(soro, 0) * 100),
                    "pct_anterior": float(p0.get(soro, 0) * 100),
                    "delta_pp": dlt * 100,
                    "alerta": f"Variação de {dlt*100:.1f} p.p. no sorogrupo {soro} ({a0}→{a1})",
                })
    if not alertas:
        alertas = [{"tipo": "estavel", "alerta": "Sem mudança ≥10 p.p. entre os dois últimos anos com DM"}]
    return trend, pd.DataFrame(alertas)


def build_score_nt154(df: pd.DataFrame) -> pd.DataFrame:
    """Score municipal de risco segundo a NT 154/2024 (revogou a NT 97/2024)."""
    d = ms._ensure_lead_times(df)
    ref = pd.to_datetime(d.get("data_ref_v17"), errors="coerce")
    corte = pd.Timestamp(datetime.now().date()) - timedelta(days=90)
    recent = ref >= corte
    clas = d["classificacao_agrupada_v17"].astype(str)
    conf = pd.to_numeric(d.get("confirmado_v17"), errors="coerce").fillna(0).astype(int)
    dm_lab = clas.eq(DM) & (conf == 1) & recent
    q_real = ms._quimio_realizada(d)
    col = _soro_col(d)
    soro_ok = pd.Series(False, index=d.index)
    if col:
        s = d[col].astype(str)
        soro_ok = _filled(s) & ~s.map(text_key).isin(["", "IGNORADO", "9", "99"])

    # incidência municipal aproximada: casos 90d / pop se existir
    pop_map = {}
    ind = OUT / "indicadores_municipio_ano_v17.csv"
    if ind.exists():
        try:
            im = pd.read_csv(ind, encoding="utf-8-sig", low_memory=False)
            if {"codigo_municipio_v17", "populacao"}.issubset(im.columns):
                latest = pd.to_numeric(im.get("ano_evento_v17"), errors="coerce").max()
                im2 = im[pd.to_numeric(im["ano_evento_v17"], errors="coerce") == latest] if "ano_evento_v17" in im.columns else im
                pop_map = im2.drop_duplicates("codigo_municipio_v17").set_index(
                    im2["codigo_municipio_v17"].astype(str).str[:6]
                )["populacao"].to_dict()
        except Exception:
            pass

    rows = []
    keys = [c for c in ["codigo_municipio_v17", "municipio_v17", "regional_v17"] if c in d.columns]
    if not keys:
        return pd.DataFrame()
    for vals, g in d.groupby(keys, dropna=False):
        if not isinstance(vals, tuple):
            vals = (vals,)
        idx = g.index
        n_dm90 = int(dm_lab.loc[idx].sum())
        n_dm = int((clas.loc[idx].eq(DM) & recent.loc[idx]).sum())
        pct_soro = _pct(int((clas.loc[idx].eq(DM) & recent.loc[idx] & soro_ok.loc[idx]).sum()), n_dm)
        pct_quimio = _pct(int((clas.loc[idx].eq(DM) & recent.loc[idx] & q_real.loc[idx]).sum()), n_dm)
        cod = str(vals[0])[:6] if keys[0] == "codigo_municipio_v17" else ""
        pop = float(pop_map.get(cod, np.nan)) if cod else np.nan
        inc = (n_dm90 / pop * 100000) if pop and pop > 0 else np.nan
        # score 0–100
        score = 0.0
        score += min(n_dm90 * 15, 45)  # volume DM lab+ 90d
        if pd.notna(pct_soro):
            score += max(0, (70 - pct_soro) / 70 * 20)  # falta sorogrupo
        if pd.notna(pct_quimio):
            score += max(0, (80 - pct_quimio) / 80 * 20)  # falta quimio
        if pd.notna(inc):
            score += min(inc * 2, 15)
        row = {k: v for k, v in zip(keys, vals)}
        row.update({
            "dm_lab_90d": n_dm90,
            "dm_90d": n_dm,
            "pct_sorogrupo_dm_90d": pct_soro,
            "pct_quimio_dm_90d": pct_quimio,
            "incidencia_dm_90d_100mil": inc,
            "score_risco_nt154_v25": round(min(score, 100), 1),
            # Coluna legada mantida para compatibilidade do painel/interpretações;
            # pode ser removida quando todos passarem a ler score_risco_nt154_v25.
            "score_risco_nt97_v25": round(min(score, 100), 1),
            "prioridade": "Alta" if score >= 50 else ("Média" if score >= 25 else "Baixa"),
            "norma": "NT 154/2024",
        })
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("score_risco_nt154_v25", ascending=False)
    return out


def build_pl_lab_vacina(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = ms._ensure_lead_times(df)
    clas = d["classificacao_agrupada_v17"].astype(str)
    conf = pd.to_numeric(d.get("confirmado_v17"), errors="coerce").fillna(0).astype(int)
    alvo = clas.isin(BACT) | clas.eq(DM)
    pl = _pl_realizada(d)
    pend = _lab_pendente(d)
    lt_pl = pd.to_numeric(d.get("lt_sintomas_coleta_dias_v17"), errors="coerce")
    lt_ok = lt_pl.notna() & (lt_pl >= 0) & (lt_pl < 365)

    lab_rows = [{
        "indicador": "pct_pl_realizada_bact_dm",
        "valor_pct": _pct(int((alvo & pl).sum()), int(alvo.sum())),
        "numerador": int((alvo & pl).sum()),
        "denominador": int(alvo.sum()),
        "nota": "PL realizada em bacterianas/DM",
    }, {
        "indicador": "pct_lab_pendente_bact_dm",
        "valor_pct": _pct(int((alvo & pend).sum()), int(alvo.sum())),
        "numerador": int((alvo & pend).sum()),
        "denominador": int(alvo.sum()),
        "nota": "Sem resultado PCR/cultura/CIE/látex/bacterioscopia preenchido",
    }, {
        "indicador": "p50_sintomas_pl_dias",
        "valor_pct": float(lt_pl[lt_ok].median()) if lt_ok.any() else np.nan,
        "numerador": int(lt_ok.sum()),
        "denominador": int(lt_ok.sum()),
        "nota": "P50 lead sintomas→PL (dias)",
    }, {
        "indicador": "p90_sintomas_pl_dias",
        "valor_pct": float(lt_pl[lt_ok].quantile(0.9)) if lt_ok.any() else np.nan,
        "numerador": int(lt_ok.sum()),
        "denominador": int(lt_ok.sum()),
        "nota": "P90 lead sintomas→PL (dias)",
    }]

    # Vacinação elegíveis
    def vac_bin(col):
        if col not in d.columns:
            return pd.Series(0, index=d.index)
        if col.endswith("_bin_v17"):
            return pd.to_numeric(d[col], errors="coerce").fillna(0).astype(int)
        return d[col].map(simnao_bin).fillna(0).astype(int)

    menc = vac_bin("VacinaConjugadaMeningoC_bin_v17") if "VacinaConjugadaMeningoC_bin_v17" in d.columns else vac_bin("VacinaConjugadaMeningoC")
    hibv = vac_bin("VacinaContraHemofilos_bin_v17") if "VacinaContraHemofilos_bin_v17" in d.columns else vac_bin("VacinaContraHemofilos")
    pnv = vac_bin("VacinaContraPneumococo_bin_v17") if "VacinaContraPneumococo_bin_v17" in d.columns else vac_bin("VacinaContraPneumococo")

    # elegíveis aproximados: DM → MenC; Hib → Hib; Pneumo → pneumo; preenchimento = 0/1 conhecido
    vac_rows = [{
        "indicador": "pct_menc_em_dm",
        "elegiveis": int(clas.eq(DM).sum()),
        "com_registro_sim": int((clas.eq(DM) & (menc == 1)).sum()),
        "valor_pct": _pct(int((clas.eq(DM) & (menc == 1)).sum()), int(clas.eq(DM).sum())),
        "nota": "DM com Vacina Conjugada Meningo C = Sim",
    }, {
        "indicador": "pct_hib_vac_em_hib",
        "elegiveis": int(clas.eq(HIB).sum()),
        "com_registro_sim": int((clas.eq(HIB) & (hibv == 1)).sum()),
        "valor_pct": _pct(int((clas.eq(HIB) & (hibv == 1)).sum()), int(clas.eq(HIB).sum())),
        "nota": "Hib etiológico com vacina Hib = Sim",
    }, {
        "indicador": "pct_pneumo_vac_em_pneumo",
        "elegiveis": int(clas.eq(PNEUMO).sum()),
        "com_registro_sim": int((clas.eq(PNEUMO) & (pnv == 1)).sum()),
        "valor_pct": _pct(int((clas.eq(PNEUMO) & (pnv == 1)).sum()), int(clas.eq(PNEUMO).sum())),
        "nota": "Pneumocócica etiológica com vacina pneumo = Sim",
    }]
    return pd.DataFrame(lab_rows), pd.DataFrame(vac_rows)


def build_gravidade_se(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    ref = pd.to_datetime(d.get("data_ref_v17"), errors="coerce")
    iso = ref.dt.isocalendar()
    d["_ano"] = iso.year.astype("Int64")
    d["_se"] = iso.week.astype("Int64")
    now = datetime.now().isocalendar()
    ano, se = int(now.year), int(now.week)
    # usa SE corrente; se vazio, última SE com dados
    cur = d[(d["_ano"] == ano) & (d["_se"] == se)]
    if cur.empty:
        last = d.dropna(subset=["_ano", "_se"]).sort_values(["_ano", "_se"]).tail(1)
        if last.empty:
            return pd.DataFrame()
        ano, se = int(last.iloc[0]["_ano"]), int(last.iloc[0]["_se"])
        cur = d[(d["_ano"] == ano) & (d["_se"] == se)]

    clas = cur["classificacao_agrupada_v17"].astype(str)
    conf = pd.to_numeric(cur.get("confirmado_v17"), errors="coerce").fillna(0)
    obito = pd.to_numeric(cur.get("obito_meningite_uniao_v23"), errors="coerce")
    if obito.isna().all():
        obito = pd.to_numeric(cur.get("obito_meningite_v17"), errors="coerce").fillna(0)
    else:
        obito = obito.fillna(0)
    hosp = pd.to_numeric(cur.get("hospitalizacao_v17"), errors="coerce").fillna(0)
    # óbito precoce <7d: sintomas→óbito approx via evolucao + data ref
    sint = pd.to_datetime(cur.get("data_sintomas_v17"), errors="coerce")
    early = (obito == 1) & sint.notna() & ((ref.loc[cur.index] - sint).dt.days <= 7)

    rows = []
    for et, g in cur.groupby(clas, dropna=False):
        n = len(g)
        c = int(conf.loc[g.index].sum())
        o = int(obito.loc[g.index].sum())
        rows.append({
            "ano": ano,
            "semana_epi": se,
            "classificacao_agrupada_v17": et,
            "casos": n,
            "confirmados": c,
            "obitos": o,
            "hospitalizacoes": int(hosp.loc[g.index].sum()),
            "obitos_lt_7d": int(early.loc[g.index].sum()),
            "letalidade_pct": _pct(o, c if c else n),
            "pct_hospitalizacao": _pct(int(hosp.loc[g.index].sum()), n),
            "pct_gravidade_proxy": _pct(int(((obito.loc[g.index] == 1) | (hosp.loc[g.index] == 1)).sum()), n),
        })
    # total
    rows.append({
        "ano": ano,
        "semana_epi": se,
        "classificacao_agrupada_v17": "TOTAL",
        "casos": len(cur),
        "confirmados": int(conf.sum()),
        "obitos": int(obito.sum()),
        "hospitalizacoes": int(hosp.sum()),
        "obitos_lt_7d": int(early.sum()),
        "letalidade_pct": _pct(int(obito.sum()), int(conf.sum()) or len(cur)),
        "pct_hospitalizacao": _pct(int(hosp.sum()), len(cur)),
        "pct_gravidade_proxy": _pct(int(((obito == 1) | (hosp == 1)).sum()), len(cur)),
    })
    return pd.DataFrame(rows)


def write_boletim_envio(
    backlog_resumo: pd.DataFrame,
    link: pd.DataFrame,
    soro_alert: pd.DataFrame,
    grav: pd.DataFrame,
    score: pd.DataFrame,
    lab: pd.DataFrame,
    vac: pd.DataFrame,
):
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "# Boletim CIEVS-MT — Meningites (pronta para envio)",
        "",
        f"**Gerado em:** {hoje}",
        "",
        "> Validar com a equipe antes de divulgação oficial.",
        "",
        "## Backlog operacional",
        "",
    ]
    if not backlog_resumo.empty:
        r = backlog_resumo.iloc[0]
        lines += [
            f"- Casos abertos: **{fmt_num(r.get('casos_abertos'), 0)}**",
            f"- Investigação atrasada (>48h): **{fmt_num(r.get('investigacao_atrasada'), 0)}**",
            f"- Encerramento D45–D60: **{fmt_num(r.get('encerramento_d45_d60'), 0)}**",
            f"- Encerramento >60d: **{fmt_num(r.get('encerramento_gt60'), 0)}**",
            f"- Quimio pendente (DM/Hib): **{fmt_num(r.get('quimio_pendente_dm_hib'), 0)}**",
            f"- Hib sem quimio: **{fmt_num(r.get('hib_sem_quimio'), 0)}**",
            "",
        ]
    lines += ["## Linkage GAL/SIM", ""]
    if not link.empty:
        e = link[link["escopo"].astype(str).eq("ESTADUAL")]
        if not e.empty:
            r = e.iloc[0]
            lines += [
                f"- Match GAL: **{fmt_num(r.get('pct_match_gal'))}%**",
                f"- Bacterianas lab+ com GAL: **{fmt_num(r.get('pct_bact_lab_com_gal'))}%**",
                f"- Discordância SIM sem óbito SINAN: **{fmt_num(r.get('n_discordancia_sim_sem_sinan'), 0)}** "
                f"({fmt_num(r.get('pct_discordancia_sim_sem_sinan'))}%)",
                "",
            ]
    lines += ["## Sorogrupos / NT 154", ""]
    if not soro_alert.empty:
        for _, r in soro_alert.head(5).iterrows():
            lines.append(f"- {r.get('alerta', '')}")
        lines.append("")
    if not score.empty:
        top = score.head(5)
        lines.append("### Municípios com maior score NT154 (90d)")
        for _, r in top.iterrows():
            lines.append(
                f"- {r.get('municipio_v17')} ({r.get('regional_v17')}): "
                f"score {fmt_num(r.get('score_risco_nt154_v25'))} · DM lab+ 90d={fmt_num(r.get('dm_lab_90d'), 0)}"
            )
        lines.append("")
    lines += ["## Gravidade SE corrente", ""]
    if not grav.empty:
        tot = grav[grav["classificacao_agrupada_v17"].astype(str).eq("TOTAL")]
        if not tot.empty:
            r = tot.iloc[0]
            lines += [
                f"- SE {int(r.get('semana_epi'))}/{int(r.get('ano'))}: "
                f"{fmt_num(r.get('casos'), 0)} casos · letalidade {fmt_num(r.get('letalidade_pct'))}% · "
                f"óbitos <7d {fmt_num(r.get('obitos_lt_7d'), 0)}",
                "",
            ]
    lines += ["## Laboratório e vacina (elegíveis)", ""]
    for frame in (lab, vac):
        if frame.empty:
            continue
        for _, r in frame.iterrows():
            lines.append(f"- {r.get('indicador')}: **{fmt_num(r.get('valor_pct'))}** — {r.get('nota', '')}")
    lines += [
        "",
        "## Como atualizar",
        "",
        "```bat",
        "ATUALIZAR_MENINGITES.bat",
        "py -3.13 26_indicadores_ops_avancados_v25.py",
        "```",
        "",
    ]
    text = "\n".join(lines)
    (REL / "BOLETIM_CIEVS_MENINGITES_ENVIO_V25.md").write_text(text, encoding="utf-8")
    (OUT / "boletim_envio_v25.md").write_text(text, encoding="utf-8")


def main():
    df = load_base_v17()
    if df.empty:
        raise SystemExit("Base ausente.")

    # Sprint A — Hib + backlog
    build_hib_and_extend_ms(df)
    backlog_geo, backlog_resumo = build_backlog(df)
    backlog_geo.to_csv(OUT / "backlog_operacional_regional_v25.csv", index=False, encoding="utf-8-sig")
    backlog_resumo.to_csv(OUT / "backlog_operacional_resumo_v25.csv", index=False, encoding="utf-8-sig")

    # Sprint B — linkage + discórdia
    link = build_linkage_kpis(df)
    link.to_csv(OUT / "linkage_completude_kpis_v25.csv", index=False, encoding="utf-8-sig")

    # Sprint C — sorogrupos + score NT 154/2024
    soro_trend, soro_alert = build_sorogrupos(df)
    soro_trend.to_csv(OUT / "sorogrupos_dm_tendencia_v25.csv", index=False, encoding="utf-8-sig")
    soro_alert.to_csv(OUT / "sorogrupos_dm_alertas_v25.csv", index=False, encoding="utf-8-sig")
    score = build_score_nt154(df)
    score.to_csv(OUT / "score_risco_municipal_nt154_v25.csv", index=False, encoding="utf-8-sig")
    # Alias de compatibilidade do painel (nome da NT 97/2024, revogada);
    # pode ser removido quando o dashboard ler o arquivo nt154.
    score.to_csv(OUT / "score_risco_municipal_nt97_v25.csv", index=False, encoding="utf-8-sig")

    # Sprint D — PL/lab + vacina
    lab, vac = build_pl_lab_vacina(df)
    lab.to_csv(OUT / "indicadores_pl_lab_v25.csv", index=False, encoding="utf-8-sig")
    vac.to_csv(OUT / "indicadores_vacina_elegiveis_v25.csv", index=False, encoding="utf-8-sig")

    # Sprint E — gravidade SE + boletim
    grav = build_gravidade_se(df)
    grav.to_csv(OUT / "gravidade_letalidade_se_corrente_v25.csv", index=False, encoding="utf-8-sig")
    write_boletim_envio(backlog_resumo, link, soro_alert, grav, score, lab, vac)

    # Espelho gestão
    gest_extra = {
        "pct_quimioprofilaxia_hib_48h": (
            float(pd.read_csv(OUT / "indicadores_ms_operacionais_resumo_v23.csv").iloc[0].get("pct_quimioprofilaxia_hib_48h", np.nan))
            if (OUT / "indicadores_ms_operacionais_resumo_v23.csv").exists() else np.nan
        ),
        "backlog_abertos": int(backlog_resumo.iloc[0]["casos_abertos"]),
        "backlog_quimio_pendente": int(backlog_resumo.iloc[0]["quimio_pendente_dm_hib"]),
        "discordancia_sim_n": int(link.iloc[0]["n_discordancia_sim_sem_sinan"]) if not link.empty else 0,
    }
    pd.DataFrame([gest_extra]).to_csv(OUT / "indicadores_gestao_extras_v25.csv", index=False, encoding="utf-8-sig")

    print("[OK] Indicadores operacionais avançados V25 gerados.")
    print(backlog_resumo.to_string(index=False))
    if not link.empty:
        print(link[link["escopo"] == "ESTADUAL"].to_string(index=False))


if __name__ == "__main__":
    main()
