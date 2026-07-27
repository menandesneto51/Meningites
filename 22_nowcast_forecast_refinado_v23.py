# -*- coding: utf-8 -*-
"""
22_nowcast_forecast_refinado_v23.py
Nowcasting com correção por atraso de notificação + forecasting semanal
e backtest — foco em meningites / operação CIEVS.

Método (transparente, sem caixa-preta obrigatória):
  1) Distribuição empírica do lead time sintomas→notificação
  2) Nowcast das últimas 4 SE: observa / P(já notificado até o atraso da SE)
  3) Forecast 4–8 SE: ensemble (média móvel, sazonal lag-52, tendência linear curta)
  4) Backtest rolling nas últimas 8 SE (MAE / MAPE)
  5) Alerta se nowcast da SE corrente > P75 do perfil sazonal
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, load_base_v17


def _weekly_series(df: pd.DataFrame, col: str = "caso_v17") -> pd.DataFrame:
    d = df.dropna(subset=["ano_epi_v17", "semana_epi_v17"]).copy()
    d["ano_epi_v17"] = pd.to_numeric(d["ano_epi_v17"], errors="coerce").astype("Int64")
    d["semana_epi_v17"] = pd.to_numeric(d["semana_epi_v17"], errors="coerce").astype("Int64")
    g = (
        d.groupby(["ano_epi_v17", "semana_epi_v17"], as_index=False)
        .agg(y=(col, "sum"))
        .dropna()
        .sort_values(["ano_epi_v17", "semana_epi_v17"])
    )
    g["periodo"] = g["ano_epi_v17"].astype(str) + "-S" + g["semana_epi_v17"].astype(int).astype(str).str.zfill(2)
    g["t"] = np.arange(len(g))
    return g.reset_index(drop=True)


def delay_cdf(df: pd.DataFrame, max_days: int = 60) -> pd.DataFrame:
    lt = pd.to_numeric(df.get("lt_sintomas_notificacao_dias_v17"), errors="coerce")
    lt = lt[(lt >= 0) & (lt <= 365)].dropna()
    if lt.empty:
        # fallback conservador
        days = np.arange(0, max_days + 1)
        # approx: 50% em 4d, 80% em 14d
        cdf = np.minimum(1.0, 0.15 + 0.85 * (1 - np.exp(-days / 10)))
        return pd.DataFrame({"atraso_dias": days, "cdf_reportado": cdf, "n_obs": 0})
    days = np.arange(0, max_days + 1)
    cdf = np.array([(lt <= d).mean() for d in days], dtype=float)
    cdf = np.maximum.accumulate(cdf)
    cdf = np.clip(cdf, 0.05, 1.0)  # evita divisão explosiva
    return pd.DataFrame({"atraso_dias": days, "cdf_reportado": cdf, "n_obs": int(len(lt))})


def nowcast_recent(weekly: pd.DataFrame, cdf: pd.DataFrame, n_se: int = 4) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame()
    hoje = pd.Timestamp.today().normalize()
    rows = []
    tail = weekly.tail(n_se).copy()
    for _, r in tail.iterrows():
        # proxy: centro da SE = quinta (ISO); atraso em dias desde o fim da SE
        ano, se = int(r["ano_epi_v17"]), int(r["semana_epi_v17"])
        try:
            fim_se = pd.Timestamp.fromisocalendar(ano, se, 7)
        except Exception:
            fim_se = hoje
        atraso = max(0, int((hoje - fim_se).days))
        atraso = min(atraso, int(cdf["atraso_dias"].max()))
        p = float(cdf.loc[cdf["atraso_dias"] == atraso, "cdf_reportado"].iloc[0])
        obs = float(r["y"])
        nc = obs / p if p > 0 else obs
        rows.append({
            "ano_epi_v17": ano,
            "semana_epi_v17": se,
            "periodo": r["periodo"],
            "observado": obs,
            "atraso_dias_proxy": atraso,
            "prob_ja_notificado": p,
            "nowcast": nc,
            "incremento_estimado": max(0.0, nc - obs),
        })
    return pd.DataFrame(rows)


def ensemble_forecast(weekly: pd.DataFrame, horizon: int = 8) -> pd.DataFrame:
    y = weekly["y"].astype(float).values
    if len(y) < 8:
        return pd.DataFrame()
    last = weekly.iloc[-1]
    ano, se = int(last["ano_epi_v17"]), int(last["semana_epi_v17"])
    rows = []
    hist = list(y)
    for h in range(1, horizon + 1):
        se2 = se + h
        ano2 = ano
        while se2 > 52:
            se2 -= 52
            ano2 += 1
        ma4 = float(np.mean(hist[-4:]))
        ma8 = float(np.mean(hist[-8:]))
        seasonal = float(hist[-52]) if len(hist) >= 52 else ma8
        # tendência curta
        if len(hist) >= 6:
            x = np.arange(6)
            coef = np.polyfit(x, hist[-6:], 1)
            trend = float(coef[0] * 6 + coef[1])
        else:
            trend = ma4
        preds = np.array([ma4, ma8, seasonal, max(0, trend)])
        mean = float(preds.mean())
        sd = float(preds.std(ddof=0)) + float(np.std(hist[-12:])) * 0.3
        rows.append({
            "horizonte_se": h,
            "ano_epi_v17": ano2,
            "semana_epi_v17": se2,
            "periodo": f"{ano2}-S{se2:02d}",
            "pred": max(0, mean),
            "lower_80": max(0, mean - 1.28 * sd),
            "upper_80": mean + 1.28 * sd,
            "modelo_ma4": ma4,
            "modelo_ma8": ma8,
            "modelo_sazonal_52": seasonal,
            "modelo_tendencia": max(0, trend),
        })
        hist.append(mean)
    return pd.DataFrame(rows)


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


def main():
    df = load_base_v17()
    df = df[pd.to_numeric(df.get("ano_evento_v17"), errors="coerce") >= 2007].copy()

    cdf = delay_cdf(df)
    cdf.to_csv(OUT / "nowcast_atraso_notificacao_cdf_v23.csv", index=False, encoding="utf-8-sig")

    weekly = _weekly_series(df, "caso_v17")
    weekly.to_csv(OUT / "nowcast_serie_semanal_casos_v23.csv", index=False, encoding="utf-8-sig")

    nc = nowcast_recent(weekly, cdf, n_se=4)
    nc.to_csv(OUT / "nowcasting_atraso_corrigido_v23.csv", index=False, encoding="utf-8-sig")

    fc = ensemble_forecast(weekly, horizon=8)
    fc.to_csv(OUT / "forecasting_semanal_ensemble_v23.csv", index=False, encoding="utf-8-sig")

    bt = backtest(weekly, n_hold=8)
    bt.to_csv(OUT / "forecasting_backtest_v23.csv", index=False, encoding="utf-8-sig")

    # Comparar com perfil sazonal (módulo 21, se existir)
    perfil = OUT / "sazonalidade_perfil_semana_epi_v23.csv"
    alerta_nc = "rotina"
    detalhe = ""
    if not nc.empty and perfil.exists():
        p = pd.read_csv(perfil)
        se = int(nc.iloc[-1]["semana_epi_v17"])
        rowp = p[p["semana_epi"] == se]
        if not rowp.empty:
            p75 = float(rowp.iloc[0]["p75_casos"])
            val = float(nc.iloc[-1]["nowcast"])
            if val > p75:
                alerta_nc = "acima_p75_sazonal"
                detalhe = f"Nowcast SE{se}={val:.1f} > P75 histórico {p75:.1f}"
            else:
                detalhe = f"Nowcast SE{se}={val:.1f} ≤ P75 histórico {p75:.1f}"

    mae = float(bt["erro_abs"].mean()) if not bt.empty else np.nan
    mape = float(bt["erro_pct"].mean()) if not bt.empty else np.nan
    resumo = pd.DataFrame([{
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "n_semanas_serie": len(weekly),
        "nowcast_se_atual": float(nc.iloc[-1]["nowcast"]) if not nc.empty else np.nan,
        "observado_se_atual": float(nc.iloc[-1]["observado"]) if not nc.empty else np.nan,
        "incremento_atraso_estimado": float(nc.iloc[-1]["incremento_estimado"]) if not nc.empty else np.nan,
        "forecast_se1": float(fc.iloc[0]["pred"]) if not fc.empty else np.nan,
        "forecast_se4": float(fc.iloc[3]["pred"]) if len(fc) >= 4 else np.nan,
        "backtest_mae": mae,
        "backtest_mape_pct": mape,
        "alerta_nowcast": alerta_nc,
        "alerta_detalhe": detalhe,
        "n_obs_atraso": int(cdf["n_obs"].iloc[0]) if not cdf.empty else 0,
    }])
    resumo.to_csv(OUT / "nowcast_forecast_resumo_v23.csv", index=False, encoding="utf-8-sig")

    r = resumo.iloc[0]
    md = [
        "# Nowcast / Forecast refinados — Meningites V23",
        "",
        f"**Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Nowcast (correção por atraso de notificação)",
        "",
        f"- Observado SE atual: **{r['observado_se_atual']:.1f}**",
        f"- Nowcast corrigido: **{r['nowcast_se_atual']:.1f}** (+{r['incremento_atraso_estimado']:.1f} estimados em atraso)",
        f"- Status vs sazonalidade: **{r['alerta_nowcast']}** — {r['alerta_detalhe']}",
        "",
        "## Forecast (próximas SE)",
        "",
        f"- SE+1: **{r['forecast_se1']:.1f}** · SE+4: **{r['forecast_se4']:.1f}**",
        "",
        "## Backtest (8 SE)",
        "",
        f"- MAE: **{r['backtest_mae']:.2f}** casos/SE · MAPE: **{r['backtest_mape_pct']:.1f}%**",
        "",
        "Método: CDF empírica de `lt_sintomas_notificacao`; ensemble MA4/MA8/sazonal-52/tendência.",
        "Complementa (não substitui) o forecasting diário V17 nem os indicadores oficiais do MS.",
        "",
    ]
    (REL / "NOWCAST_FORECAST_REFINADO_V23.md").write_text("\n".join(md), encoding="utf-8")

    print("[OK] Nowcast/forecast refinado V23.")
    print(resumo.to_string(index=False))
    if not nc.empty:
        print(nc.to_string(index=False))


if __name__ == "__main__":
    main()
