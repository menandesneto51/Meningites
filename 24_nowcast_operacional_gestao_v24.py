# -*- coding: utf-8 -*-
"""
24_nowcast_operacional_gestao_v24.py
Nowcasting operacional para gestão CIEVS-MT.

Sem DT_DIGITA no VW_SINAN_MENINGITE atual — usa atraso epidemiológico clássico:
  semana de início de sintomas (ou data_ref) → semana de notificação.

Produz:
  - CDF de atraso em semanas (e dias, complementar)
  - Nowcast das últimas 6 SE: estadual, DM e por regional
  - Intervalo de incerteza (bootstrap do atraso)
  - Forecast 8 SE a partir da série corrigida
  - Backtest + indicadores de gestão da semana
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, load_base_v17

MAX_DELAY_WEEKS = 12
N_NOWCAST_SE = 6
N_BOOT = 200
HORIZON = 8
DM_LABEL = "Doença meningocócica"


def _iso_parts(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    s = pd.to_datetime(s, errors="coerce")
    iso = s.dt.isocalendar()
    return iso.year.astype("Int64"), iso.week.astype("Int64")


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = d[pd.to_numeric(d.get("ano_evento_v17"), errors="coerce") >= 2007].copy()
    onset = pd.to_datetime(d.get("data_sintomas_v17"), errors="coerce")
    onset = onset.fillna(pd.to_datetime(d.get("data_ref_v17"), errors="coerce"))
    notif = pd.to_datetime(d.get("data_notificacao_v17"), errors="coerce")
    notif = notif.fillna(onset)
    d["data_onset_nc"] = onset
    d["data_report_nc"] = notif
    d = d.dropna(subset=["data_onset_nc"]).copy()
    d["ano_onset"], d["se_onset"] = _iso_parts(d["data_onset_nc"])
    d["ano_report"], d["se_report"] = _iso_parts(d["data_report_nc"])
    # atraso em semanas ISO aproximado
    d["atraso_semanas"] = (
        (pd.to_numeric(d["ano_report"], errors="coerce") - pd.to_numeric(d["ano_onset"], errors="coerce")) * 52
        + (pd.to_numeric(d["se_report"], errors="coerce") - pd.to_numeric(d["se_onset"], errors="coerce"))
    )
    d["atraso_semanas"] = pd.to_numeric(d["atraso_semanas"], errors="coerce")
    d.loc[d["atraso_semanas"] < 0, "atraso_semanas"] = 0
    d.loc[d["atraso_semanas"] > 52, "atraso_semanas"] = np.nan
    d["lt_dias_report"] = (d["data_report_nc"] - d["data_onset_nc"]).dt.days
    d["is_dm"] = d.get("classificacao_agrupada_v17", pd.Series(index=d.index)).astype(str).eq(DM_LABEL)
    d["regional_v17"] = d.get("regional_v17", pd.Series(index=d.index)).astype(str).str.strip()
    d["caso_v17"] = 1
    return d


def delay_cdf_weeks(d: pd.DataFrame, max_w: int = MAX_DELAY_WEEKS) -> pd.DataFrame:
    lt = pd.to_numeric(d["atraso_semanas"], errors="coerce")
    lt = lt[(lt >= 0) & (lt <= 52)].dropna()
    weeks = np.arange(0, max_w + 1)
    if lt.empty:
        # fallback: ~60% na SE0–1, ~90% até SE4
        cdf = np.minimum(1.0, 0.35 + 0.65 * (1 - np.exp(-weeks / 2.5)))
        return pd.DataFrame({"atraso_semanas": weeks, "cdf_reportado": cdf, "n_obs": 0, "fonte": "fallback"})
    cdf = np.array([(lt <= w).mean() for w in weeks], dtype=float)
    cdf = np.maximum.accumulate(cdf)
    cdf = np.clip(cdf, 0.08, 1.0)
    return pd.DataFrame({
        "atraso_semanas": weeks,
        "cdf_reportado": cdf,
        "n_obs": int(len(lt)),
        "fonte": "sintomas_para_notificacao_se",
    })


def delay_cdf_days(d: pd.DataFrame, max_days: int = 60) -> pd.DataFrame:
    lt = pd.to_numeric(d["lt_dias_report"], errors="coerce")
    lt = lt[(lt >= 0) & (lt <= 365)].dropna()
    days = np.arange(0, max_days + 1)
    if lt.empty:
        cdf = np.minimum(1.0, 0.15 + 0.85 * (1 - np.exp(-days / 10)))
        return pd.DataFrame({"atraso_dias": days, "cdf_reportado": cdf, "n_obs": 0})
    cdf = np.array([(lt <= x).mean() for x in days], dtype=float)
    cdf = np.maximum.accumulate(np.clip(cdf, 0.05, 1.0))
    return pd.DataFrame({"atraso_dias": days, "cdf_reportado": cdf, "n_obs": int(len(lt))})


def weekly_onset(d: pd.DataFrame, fill_to_today: bool = True) -> pd.DataFrame:
    g = (
        d.dropna(subset=["ano_onset", "se_onset"])
        .groupby(["ano_onset", "se_onset"], as_index=False)
        .agg(y=("caso_v17", "sum"))
        .sort_values(["ano_onset", "se_onset"])
    )
    g = g.rename(columns={"ano_onset": "ano_epi_v17", "se_onset": "semana_epi_v17"})
    if fill_to_today and not g.empty:
        hoje = pd.Timestamp.today().normalize()
        iso = hoje.isocalendar()
        ano_h, se_h = int(iso.year), int(iso.week)
        # preenche semanas faltantes até hoje (zeros) — essencial para nowcast da SE corrente
        idx = []
        a0 = int(g["ano_epi_v17"].iloc[0])
        s0 = int(g["semana_epi_v17"].iloc[0])
        a, s = a0, s0
        while (a < ano_h) or (a == ano_h and s <= se_h):
            idx.append((a, s))
            s += 1
            if s > 52:
                s = 1
                a += 1
            if len(idx) > 1200:
                break
        full = pd.DataFrame(idx, columns=["ano_epi_v17", "semana_epi_v17"])
        g = full.merge(g, on=["ano_epi_v17", "semana_epi_v17"], how="left")
        g["y"] = g["y"].fillna(0.0)
    g["periodo"] = (
        g["ano_epi_v17"].astype(int).astype(str)
        + "-S"
        + g["semana_epi_v17"].astype(int).astype(str).str.zfill(2)
    )
    return g.reset_index(drop=True)


def _p_reported(cdf: pd.DataFrame, lag_weeks: int) -> float:
    lag = int(np.clip(lag_weeks, 0, int(cdf["atraso_semanas"].max())))
    return float(cdf.loc[cdf["atraso_semanas"] == lag, "cdf_reportado"].iloc[0])


def _bootstrap_p(delays: np.ndarray, lag: int, n_boot: int = N_BOOT) -> tuple[float, float, float]:
    if delays.size < 30:
        return np.nan, np.nan, np.nan
    lag = int(max(0, lag))
    ps = []
    rng = np.random.default_rng(42)
    for _ in range(n_boot):
        sample = rng.choice(delays, size=len(delays), replace=True)
        ps.append(float(np.mean(sample <= lag)))
    ps = np.clip(np.array(ps), 0.08, 1.0)
    return float(np.quantile(ps, 0.1)), float(np.quantile(ps, 0.5)), float(np.quantile(ps, 0.9))


def nowcast_recent(
    weekly: pd.DataFrame,
    cdf: pd.DataFrame,
    delays: np.ndarray,
    strata: str,
    n_se: int = N_NOWCAST_SE,
) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame()
    hoje = pd.Timestamp.today().normalize()
    rows = []
    for _, r in weekly.tail(n_se).iterrows():
        ano, se = int(r["ano_epi_v17"]), int(r["semana_epi_v17"])
        try:
            fim_se = pd.Timestamp.fromisocalendar(ano, min(se, 52), 7)
        except Exception:
            fim_se = hoje
        lag_days = max(0, int((hoje - fim_se).days))
        lag_w = min(MAX_DELAY_WEEKS, lag_days // 7)
        p = _p_reported(cdf, lag_w)
        obs = float(r["y"])
        nc = obs / p if p > 0 else obs
        p10, p50, p90 = _bootstrap_p(delays, lag_w)
        if np.isnan(p50):
            lo, hi = nc * 0.85, nc * 1.25
        else:
            lo = obs / p90 if p90 > 0 else nc
            hi = obs / p10 if p10 > 0 else nc
            # p10 da CDF ⇒ maior incompleteness ⇒ upper; p90 ⇒ lower
        rows.append({
            "estrato": strata,
            "ano_epi_v17": ano,
            "semana_epi_v17": se,
            "periodo": r["periodo"],
            "observado": obs,
            "atraso_semanas_proxy": lag_w,
            "prob_ja_notificado": p,
            "nowcast": nc,
            "nowcast_p10": float(min(lo, hi)),
            "nowcast_p90": float(max(lo, hi)),
            "incremento_estimado": max(0.0, nc - obs),
            "metodo_atraso": "SE_sintomas_para_SE_notificacao",
        })
    return pd.DataFrame(rows)


def ensemble_forecast(weekly: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    y = weekly["y"].astype(float).values
    if len(y) < 8:
        return pd.DataFrame()
    last = weekly.iloc[-1]
    ano, se = int(last["ano_epi_v17"]), int(last["semana_epi_v17"])
    rows = []
    hist = list(y)
    for h in range(1, horizon + 1):
        se2, ano2 = se + h, ano
        while se2 > 52:
            se2 -= 52
            ano2 += 1
        ma4 = float(np.mean(hist[-4:]))
        ma8 = float(np.mean(hist[-8:]))
        seasonal = float(hist[-52]) if len(hist) >= 52 else ma8
        if len(hist) >= 6:
            coef = np.polyfit(np.arange(6), hist[-6:], 1)
            trend = float(coef[0] * 6 + coef[1])
        else:
            trend = ma4
        preds = np.array([ma4, ma8, seasonal, max(0.0, trend)])
        mean = float(preds.mean())
        sd = float(preds.std(ddof=0)) + float(np.std(hist[-12:])) * 0.3
        rows.append({
            "horizonte_se": h,
            "ano_epi_v17": ano2,
            "semana_epi_v17": se2,
            "periodo": f"{ano2}-S{se2:02d}",
            "pred": max(0.0, mean),
            "lower_80": max(0.0, mean - 1.28 * sd),
            "upper_80": mean + 1.28 * sd,
            "modelo_ma4": ma4,
            "modelo_ma8": ma8,
            "modelo_sazonal_52": seasonal,
            "modelo_tendencia": max(0.0, trend),
        })
        hist.append(mean)
    return pd.DataFrame(rows)


def apply_nowcast_to_series(weekly: pd.DataFrame, nc: pd.DataFrame) -> pd.DataFrame:
    """Substitui y das SE recentes pelo nowcast (ponto) para alimentar o forecast."""
    w = weekly.copy()
    if nc.empty:
        return w
    m = nc.set_index("periodo")["nowcast"].to_dict()
    w["y_corrigido"] = w.apply(lambda r: float(m.get(r["periodo"], r["y"])), axis=1)
    out = w.copy()
    out["y"] = out["y_corrigido"]
    return out.drop(columns=["y_corrigido"])


def backtest(weekly: pd.DataFrame, n_hold: int = 8) -> pd.DataFrame:
    if len(weekly) < n_hold + 12:
        return pd.DataFrame()
    rows = []
    for i in range(n_hold, 0, -1):
        train = weekly.iloc[:-i]
        real = float(weekly.iloc[-i]["y"])
        fc = ensemble_forecast(train, horizon=1)
        if fc.empty:
            continue
        pred = float(fc.iloc[0]["pred"])
        rows.append({
            "periodo": weekly.iloc[-i]["periodo"],
            "observado": real,
            "previsto": pred,
            "erro_abs": abs(pred - real),
            "erro_pct": abs(pred - real) / real * 100 if real > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def pick_ref_row(nc: pd.DataFrame):
    """SE de referência: última com observado>0 nas últimas 12 SE; senão a mais recente."""
    if nc is None or nc.empty:
        return None
    win = nc.tail(max(N_NOWCAST_SE, 12))
    with_obs = win[pd.to_numeric(win["observado"], errors="coerce").fillna(0) > 0]
    if not with_obs.empty:
        return with_obs.iloc[-1]
    return nc.iloc[-1]


def seasonal_alert(nc_row: pd.Series) -> tuple[str, str]:
    perfil = OUT / "sazonalidade_perfil_semana_epi_v23.csv"
    if not perfil.exists() or nc_row is None:
        return "sem_perfil", "Perfil sazonal indisponível (rode módulo 21)."
    p = pd.read_csv(perfil)
    se = int(nc_row["semana_epi_v17"])
    rowp = p[p["semana_epi"] == se]
    if rowp.empty:
        return "sem_perfil", f"SE {se} sem perfil histórico."
    p75 = float(rowp.iloc[0]["p75_casos"])
    p95 = float(rowp.iloc[0].get("p95_casos", p75 * 1.3))
    val = float(nc_row["nowcast"])
    if val > p95:
        return "acima_p95_sazonal", f"Nowcast SE{se}={val:.1f} > P95 histórico {p95:.1f}"
    if val > p75:
        return "acima_p75_sazonal", f"Nowcast SE{se}={val:.1f} > P75 histórico {p75:.1f}"
    return "rotina", f"Nowcast SE{se}={val:.1f} ≤ P75 histórico {p75:.1f}"


def run_stratum(d: pd.DataFrame, strata: str, min_weeks_with_cases: int = 16) -> dict:
    delays = pd.to_numeric(d["atraso_semanas"], errors="coerce")
    delays = delays[(delays >= 0) & (delays <= 52)].dropna().to_numpy()
    cdf = delay_cdf_weeks(d)
    weekly = weekly_onset(d)
    if weekly.empty or (weekly["y"] > 0).sum() < min_weeks_with_cases:
        return {"ok": False, "strata": strata, "motivo": "série insuficiente"}
    nc = nowcast_recent(weekly, cdf, delays, strata)
    w_corr = apply_nowcast_to_series(weekly, nc)
    fc = ensemble_forecast(w_corr, horizon=HORIZON)
    bt = backtest(weekly, n_hold=8)
    alerta, detalhe = seasonal_alert(pick_ref_row(nc))
    return {
        "ok": True,
        "strata": strata,
        "cdf": cdf,
        "weekly": weekly,
        "nc": nc,
        "fc": fc,
        "bt": bt,
        "alerta": alerta,
        "detalhe": detalhe,
        "ref": pick_ref_row(nc),
    }


def gestao_semana(d: pd.DataFrame, nc_est: pd.DataFrame, nc_dm: pd.DataFrame, alerta: str, detalhe: str) -> pd.DataFrame:
    """Indicadores de gestão da semana — apoio à decisão CIEVS."""
    ms = OUT / "indicadores_ms_operacionais_resumo_v23.csv"
    fila = OUT / "fila_cievs_unificada_v23.csv"
    if not fila.exists():
        fila = OUT / "alertas_inteligentes_fila_cievs_v23.csv"
    ms_row = pd.read_csv(ms).iloc[0].to_dict() if ms.exists() else {}
    backlog_path = OUT / "backlog_operacional_resumo_v25.csv"
    backlog_row = pd.read_csv(backlog_path).iloc[0].to_dict() if backlog_path.exists() else {}
    n_fila = 0
    n_crit = 0
    if fila.exists():
        f = pd.read_csv(fila)
        n_fila = len(f)
        col_prio = next((c for c in f.columns if "prioridade" in c.lower() or "prio" in c.lower()), None)
        if col_prio:
            n_crit = int(f[col_prio].astype(str).str.contains("Crítico|critico|CRIT", case=False, na=False).sum())
        elif "nivel" in f.columns:
            n_crit = int(f["nivel"].astype(str).str.contains("Crítico|critico", case=False, na=False).sum())

    # atraso digitação/proxy: P50/P90 do lead time sintomas→notif (dias)
    lt = pd.to_numeric(d["lt_dias_report"], errors="coerce")
    lt = lt[(lt >= 0) & (lt <= 365)]
    ref_est = pick_ref_row(nc_est)
    ref_dm = pick_ref_row(nc_dm)
    se_atual = int(ref_est["semana_epi_v17"]) if ref_est is not None else np.nan
    obs = float(ref_est["observado"]) if ref_est is not None else np.nan
    nc = float(ref_est["nowcast"]) if ref_est is not None else np.nan
    # delta vs SE anterior na série completa
    delta = np.nan
    if ref_est is not None and not nc_est.empty:
        pos = nc_est.index.get_loc(ref_est.name) if ref_est.name in nc_est.index else None
        if isinstance(pos, int) and pos > 0:
            delta = float(ref_est["nowcast"]) - float(nc_est.iloc[pos - 1]["nowcast"])
        elif len(nc_est) >= 2:
            # fallback: penúltima com obs > 0 antes da ref
            before = nc_est.loc[: ref_est.name].iloc[:-1] if ref_est.name in nc_est.index else nc_est.iloc[:-1]
            before = before[pd.to_numeric(before["observado"], errors="coerce").fillna(0) >= 0]
            if len(before):
                delta = float(ref_est["nowcast"]) - float(before.iloc[-1]["nowcast"])
    dm_nc = float(ref_dm["nowcast"]) if ref_dm is not None else np.nan
    dm_obs = float(ref_dm["observado"]) if ref_dm is not None else np.nan
    se_cal = pd.Timestamp.today().isocalendar()

    # regionais acima do P75 do próprio histórico (última SE com casos na regional)
    reg_alerta = 0
    for reg, g in d.groupby("regional_v17"):
        if not reg or reg.lower() in {"nan", "none", ""}:
            continue
        w = weekly_onset(g)
        if len(w) < 20:
            continue
        hist = w[w["y"] > 0]
        if hist.empty:
            continue
        p75 = float(hist["y"].tail(52).quantile(0.75)) if len(hist) >= 8 else float(hist["y"].quantile(0.75))
        last = float(hist.iloc[-1]["y"])
        # só conta se a última SE com casos está nas últimas 6 SE do calendário
        last_se = int(hist.iloc[-1]["semana_epi_v17"])
        last_ano = int(hist.iloc[-1]["ano_epi_v17"])
        recent = w.tail(6)
        in_window = ((recent["ano_epi_v17"] == last_ano) & (recent["semana_epi_v17"] == last_se)).any()
        if in_window and last > p75 and p75 > 0:
            reg_alerta += 1

    row = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "semana_epi_ref": se_atual,
        "semana_calendario": int(se_cal.week),
        "ano_calendario": int(se_cal.year),
        "casos_observados_se": obs,
        "casos_nowcast_se": nc,
        "delta_nowcast_vs_se_anterior": delta,
        "dm_observados_se": dm_obs,
        "dm_nowcast_se": dm_nc,
        "status_sazonal": alerta,
        "status_detalhe": detalhe,
        "pct_confirmacao_laboratorial": ms_row.get("pct_confirmacao_laboratorial_pcr_cultura"),
        "pct_investigados_48h": ms_row.get("pct_investigados_48h"),
        "pct_encerrados_60d": ms_row.get("pct_encerrados_60d"),
        "pct_quimioprofilaxia_dm_48h": ms_row.get("pct_quimioprofilaxia_dm_48h"),
        "pct_quimioprofilaxia_hib_48h": ms_row.get("pct_quimioprofilaxia_hib_48h"),
        "pct_sorogrupo_dm": ms_row.get("pct_sorogrupo_identificado_dm"),
        "pct_notificacao_24h": ms_row.get("pct_notificacao_24h"),
        "backlog_abertos": backlog_row.get("casos_abertos"),
        "backlog_inv_atrasada": backlog_row.get("investigacao_atrasada"),
        "backlog_quimio_pendente": backlog_row.get("quimio_pendente_dm_hib"),
        "fila_cievs_n": n_fila,
        "fila_cievs_criticos_n": n_crit,
        "atraso_notif_p50_dias": float(lt.median()) if len(lt) else np.nan,
        "atraso_notif_p90_dias": float(lt.quantile(0.9)) if len(lt) else np.nan,
        "regionais_acima_p75_prox": reg_alerta,
        "nota_metodo": (
            "Nowcast por atraso SE sintomas→notificação. "
            "DT_DIGITA ausente no VW_SINAN_MENINGITE — quando disponível, passa a ser o evento de reporte."
        ),
        "acao_sugerida": (
            "Revisar fila crítica e DM; reforçar digitação/investigação se nowcast > P75; "
            "monitorar regionais acima do P75."
            if alerta.startswith("acima")
            else "Manter rotina: acompanhar fila CIEVS e indicadores MS em vermelho."
        ),
    }
    return pd.DataFrame([row])


def main():
    raw = load_base_v17()
    d = _prepare(raw)

    cdf_w = delay_cdf_weeks(d)
    cdf_d = delay_cdf_days(d)
    cdf_w.to_csv(OUT / "nowcast_atraso_semanas_cdf_v24.csv", index=False, encoding="utf-8-sig")
    cdf_d.to_csv(OUT / "nowcast_atraso_dias_cdf_v24.csv", index=False, encoding="utf-8-sig")

    results_nc = []
    results_fc = []
    results_bt = []
    results_weekly = []
    resumo_rows = []

    # ESTADUAL
    r_est = run_stratum(d, "ESTADUAL", min_weeks_with_cases=20)
    # DM
    r_dm = run_stratum(d[d["is_dm"]].copy(), "DM", min_weeks_with_cases=12)

    strata_runs = [r_est, r_dm]
    # Regionais com volume mínimo
    for reg, g in d.groupby("regional_v17"):
        if not reg or str(reg).lower() in {"nan", "none", ""}:
            continue
        rr = run_stratum(g.copy(), f"REGIONAL::{reg}", min_weeks_with_cases=12)
        if rr.get("ok"):
            strata_runs.append(rr)

    for r in strata_runs:
        if not r.get("ok"):
            resumo_rows.append({
                "estrato": r.get("strata"),
                "status": "insuficiente",
                "motivo": r.get("motivo", ""),
            })
            continue
        results_nc.append(r["nc"])
        if not r["fc"].empty:
            fc = r["fc"].copy()
            fc.insert(0, "estrato", r["strata"])
            results_fc.append(fc)
        if not r["bt"].empty:
            bt = r["bt"].copy()
            bt.insert(0, "estrato", r["strata"])
            results_bt.append(bt)
        w = r["weekly"].copy()
        w.insert(0, "estrato", r["strata"])
        results_weekly.append(w)
        mae = float(r["bt"]["erro_abs"].mean()) if not r["bt"].empty else np.nan
        mape = float(r["bt"]["erro_pct"].mean()) if not r["bt"].empty else np.nan
        nc_last = r.get("ref")
        if nc_last is None and not r["nc"].empty:
            nc_last = r["nc"].iloc[-1]
        if nc_last is None:
            continue
        resumo_rows.append({
            "estrato": r["strata"],
            "status": "ok",
            "n_semanas_serie": len(r["weekly"]),
            "observado_se_atual": float(nc_last["observado"]),
            "nowcast_se_atual": float(nc_last["nowcast"]),
            "nowcast_p10": float(nc_last["nowcast_p10"]),
            "nowcast_p90": float(nc_last["nowcast_p90"]),
            "incremento_atraso_estimado": float(nc_last["incremento_estimado"]),
            "semana_epi_ref": int(nc_last["semana_epi_v17"]),
            "forecast_se1": float(r["fc"].iloc[0]["pred"]) if not r["fc"].empty else np.nan,
            "forecast_se4": float(r["fc"].iloc[3]["pred"]) if len(r["fc"]) >= 4 else np.nan,
            "backtest_mae": mae,
            "backtest_mape_pct": mape,
            "qualidade_forecast": (
                "publicavel" if pd.notna(mape) and mape <= 60 else
                "cautela" if pd.notna(mape) and mape <= 100 else
                "nao_publicavel"
            ),
            "alerta_nowcast": r["alerta"],
            "alerta_detalhe": r["detalhe"],
            "n_obs_atraso": int(r["cdf"]["n_obs"].iloc[0]) if not r["cdf"].empty else 0,
            "metodo": "SE_sintomas_para_SE_notificacao",
        })

    nc_all = pd.concat(results_nc, ignore_index=True) if results_nc else pd.DataFrame()
    fc_all = pd.concat(results_fc, ignore_index=True) if results_fc else pd.DataFrame()
    bt_all = pd.concat(results_bt, ignore_index=True) if results_bt else pd.DataFrame()
    wk_all = pd.concat(results_weekly, ignore_index=True) if results_weekly else pd.DataFrame()
    resumo = pd.DataFrame(resumo_rows)

    nc_all.to_csv(OUT / "nowcasting_operacional_v24.csv", index=False, encoding="utf-8-sig")
    fc_all.to_csv(OUT / "forecasting_operacional_v24.csv", index=False, encoding="utf-8-sig")
    bt_all.to_csv(OUT / "forecasting_backtest_v24.csv", index=False, encoding="utf-8-sig")
    wk_all.to_csv(OUT / "nowcast_serie_semanal_v24.csv", index=False, encoding="utf-8-sig")
    resumo.to_csv(OUT / "nowcast_operacional_resumo_v24.csv", index=False, encoding="utf-8-sig")

    nc_est = nc_all[nc_all["estrato"] == "ESTADUAL"] if not nc_all.empty else pd.DataFrame()
    nc_dm = nc_all[nc_all["estrato"] == "DM"] if not nc_all.empty else pd.DataFrame()
    alerta = "rotina"
    detalhe = ""
    if not resumo.empty and (resumo["estrato"] == "ESTADUAL").any():
        re = resumo[resumo["estrato"] == "ESTADUAL"].iloc[0]
        alerta, detalhe = str(re.get("alerta_nowcast", "rotina")), str(re.get("alerta_detalhe", ""))

    gest = gestao_semana(d, nc_est, nc_dm, alerta, detalhe)
    gest.to_csv(OUT / "indicadores_gestao_semana_v24.csv", index=False, encoding="utf-8-sig")

    # regionais ranking por nowcast
    reg_nc = resumo[resumo["estrato"].astype(str).str.startswith("REGIONAL::")].copy()
    if not reg_nc.empty:
        reg_nc["regional_v17"] = reg_nc["estrato"].str.replace("REGIONAL::", "", regex=False)
        reg_nc = reg_nc.sort_values("nowcast_se_atual", ascending=False)
        reg_nc.to_csv(OUT / "nowcast_regionais_ranking_v24.csv", index=False, encoding="utf-8-sig")

    g0 = gest.iloc[0]
    md = [
        "# Nowcast operacional + gestão — Meningites V24",
        "",
        f"**Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Método",
        "",
        "- Evento de início: sintomas (fallback `data_ref`).",
        "- Evento de reporte: **notificação** (DT_DIGITA ainda não disponível no VW).",
        "- Nowcast: `observado / P(atraso_SE ≤ lag)` com banda bootstrap P10–P90.",
        "- Estratos: ESTADUAL, DM, regionais com série suficiente.",
        "",
        "## Semana CIEVS (gestão)",
        "",
        f"- SE ref: **{g0.get('semana_epi_ref')}**",
        f"- Nowcast estadual: **{g0.get('casos_nowcast_se')}** (obs {g0.get('casos_observados_se')}; Δ {g0.get('delta_nowcast_vs_se_anterior')})",
        f"- Nowcast DM: **{g0.get('dm_nowcast_se')}** (obs {g0.get('dm_observados_se')})",
        f"- Status sazonal: **{g0.get('status_sazonal')}** — {g0.get('status_detalhe')}",
        f"- Fila CIEVS: {g0.get('fila_cievs_n')} (críticos {g0.get('fila_cievs_criticos_n')})",
        f"- Atraso notif P50/P90 (dias): {g0.get('atraso_notif_p50_dias')} / {g0.get('atraso_notif_p90_dias')}",
        f"- Ação sugerida: {g0.get('acao_sugerida')}",
        "",
        "## Resumo por estrato",
        "",
    ]
    if not resumo.empty:
        show = resumo[resumo["status"] == "ok"][
            ["estrato", "observado_se_atual", "nowcast_se_atual", "forecast_se1", "backtest_mape_pct", "qualidade_forecast", "alerta_nowcast"]
        ].head(25)
        try:
            md.append(show.to_markdown(index=False))
        except Exception:
            md.append("```\n" + show.to_string(index=False) + "\n```")
    (REL / "NOWCAST_OPERACIONAL_GESTAO_V24.md").write_text("\n".join(md), encoding="utf-8")

    print("[OK] Nowcast operacional V24 + indicadores de gestão.")
    print(gest.to_string(index=False))
    if not resumo.empty:
        print(resumo[resumo["status"] == "ok"].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
