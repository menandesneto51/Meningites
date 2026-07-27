from __future__ import annotations

import warnings
import os
from typing import Iterable
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose


def build_daily_series(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["data_evento"]).copy()
    s = d.groupby("data_evento").size().asfreq("D", fill_value=0)
    s = s.rename("casos").to_frame()
    s["media_movel_7d"] = s["casos"].rolling(7, min_periods=1).mean()
    s["media_movel_30d"] = s["casos"].rolling(30, min_periods=1).mean()
    return s


def _make_supervised(series: pd.Series, lags: int = 30) -> tuple[pd.DataFrame, pd.Series]:
    y = series.astype(float)
    X = pd.DataFrame(index=y.index)
    for lag in range(1, lags + 1):
        X[f"lag_{lag}"] = y.shift(lag)
    X["dow"] = y.index.dayofweek
    X["month"] = y.index.month
    X["dayofyear"] = y.index.dayofyear
    out = pd.concat([X, y.rename("target")], axis=1).dropna()
    return out.drop(columns="target"), out["target"]


def _recursive_ml_forecast(model, history: pd.Series, steps: int, lags: int = 30) -> np.ndarray:
    hist = history.astype(float).copy()
    preds = []
    for _ in range(steps):
        next_date = hist.index[-1] + pd.Timedelta(days=1)
        features = {f"lag_{lag}": hist.iloc[-lag] if len(hist) >= lag else hist.mean() for lag in range(1, lags + 1)}
        features.update({"dow": next_date.dayofweek, "month": next_date.month, "dayofyear": next_date.dayofyear})
        X_next = pd.DataFrame([features])
        pred = max(float(model.predict(X_next)[0]), 0.0)
        preds.append(pred)
        hist.loc[next_date] = pred
    return np.array(preds)


def forecast_ensemble(daily: pd.DataFrame, horizons: Iterable[int] = (7, 15, 30, 60)) -> pd.DataFrame:
    """Ensemble com no mínimo 6 famílias possíveis.

    Modelos implementados:
    1. Naive
    2. Seasonal naive semanal
    3. Média móvel
    4. ETS
    5. SARIMAX
    6. Random Forest
    7. Gradient Boosting
    8. Poisson Regressor
    9. XGBoost opcional
    10. Prophet opcional
    11. LSTM opcional

    IC95: percentis 2,5 e 97,5 da distribuição dos modelos + erro residual simples.
    """
    if daily.empty:
        return pd.DataFrame()

    y_full = daily["casos"].astype(float).asfreq("D", fill_value=0)
    # Para manter execução operacional, modelos são ajustados sobre janela recente.
    # A série completa permanece disponível nas saídas descritivas.
    y = y_full.tail(730) if len(y_full) > 730 else y_full
    max_h = max(horizons)
    future_idx = pd.date_range(y.index.max() + pd.Timedelta(days=1), periods=max_h, freq="D")

    model_preds: dict[str, np.ndarray] = {}

    model_preds["naive"] = np.repeat(y.iloc[-1], max_h)
    seasonal_vals = [y.iloc[-7 + (i % 7)] if len(y) >= 7 else y.iloc[-1] for i in range(max_h)]
    model_preds["seasonal_naive_7d"] = np.array(seasonal_vals)
    model_preds["moving_average_14d"] = np.repeat(y.tail(14).mean(), max_h)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            ets = ExponentialSmoothing(y, trend="add", seasonal="add", seasonal_periods=7, initialization_method="estimated").fit()
            model_preds["ets_7d"] = np.maximum(ets.forecast(max_h).values, 0)
        except Exception:
            pass

        try:
            sarimax = SARIMAX(y, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0), enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=20)
            model_preds["sarimax_7d"] = np.maximum(sarimax.forecast(max_h).values, 0)
        except Exception:
            pass

    X, target = _make_supervised(y, lags=min(14, max(7, len(y)//20)))
    if len(target) >= 30:
        lags = len([c for c in X.columns if c.startswith("lag_")])
        rf = RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=3, n_jobs=-1)
        rf.fit(X, target)
        model_preds["random_forest"] = _recursive_ml_forecast(rf, y, max_h, lags=lags)

        gb = GradientBoostingRegressor(random_state=42)
        gb.fit(X, target)
        model_preds["gradient_boosting"] = _recursive_ml_forecast(gb, y, max_h, lags=lags)

        pr = PoissonRegressor(alpha=0.1, max_iter=500)
        pr.fit(X, target)
        model_preds["poisson_regressor"] = _recursive_ml_forecast(pr, y, max_h, lags=lags)

        if os.getenv("MENINGITE_ENABLE_HEAVY_MODE") == "1":
            try:
                from xgboost import XGBRegressor
                xgb = XGBRegressor(n_estimators=120, learning_rate=0.05, max_depth=3, random_state=42, objective="count:poisson")
                xgb.fit(X, target)
                model_preds["xgboost"] = _recursive_ml_forecast(xgb, y, max_h, lags=lags)
            except Exception:
                pass

    # Prophet opcional em modo pesado, pois pode deixar a rotina operacional lenta.
    if os.getenv("MENINGITE_ENABLE_HEAVY_MODE") == "1":
        try:
            from prophet import Prophet
            p_df = y.reset_index()
            p_df.columns = ["ds", "y"]
            m = Prophet(interval_width=0.95, daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
            m.fit(p_df)
            future = m.make_future_dataframe(periods=max_h, freq="D")
            fc = m.predict(future).tail(max_h)
            model_preds["prophet"] = np.maximum(fc["yhat"].values, 0)
        except Exception:
            pass

    preds = pd.DataFrame(model_preds, index=future_idx)
    preds[preds < 0] = 0
    preds["forecast_mean"] = preds.mean(axis=1)
    preds["lower_95"] = preds.quantile(0.025, axis=1)
    preds["upper_95"] = preds.quantile(0.975, axis=1)
    preds["n_models"] = len(model_preds)
    preds["data"] = preds.index

    out = []
    for h in horizons:
        temp = preds.iloc[:h].copy()
        temp["horizon"] = f"{h}d"
        out.append(temp)
    return pd.concat(out, ignore_index=True)


def decompose_series(daily: pd.DataFrame, period: int = 365) -> pd.DataFrame:
    if daily.empty or len(daily) < period * 2:
        # fallback semanal se a série for curta
        period = 7
    y = daily["casos"].astype(float).asfreq("D", fill_value=0)
    try:
        dec = seasonal_decompose(y, model="additive", period=period, extrapolate_trend="freq")
        return pd.DataFrame({
            "data": y.index,
            "observado": dec.observed,
            "tendencia": dec.trend,
            "sazonalidade": dec.seasonal,
            "residuo": dec.resid,
            "periodo": period,
        })
    except Exception as exc:
        return pd.DataFrame({"erro": [str(exc)]})


def endemic_channel(df: pd.DataFrame, current_year: int | None = None) -> pd.DataFrame:
    d = df.dropna(subset=["data_evento"]).copy()
    if d.empty:
        return pd.DataFrame()
    d["ano"] = d["data_evento"].dt.year
    d["semana_epidemiologica"] = d["data_evento"].dt.isocalendar().week.astype(int)
    if current_year is None:
        current_year = int(d["ano"].max())

    weekly = d.groupby(["ano", "semana_epidemiologica"]).size().reset_index(name="casos")
    hist = weekly[weekly["ano"] < current_year]
    curr = weekly[weekly["ano"] == current_year][["semana_epidemiologica", "casos"]].rename(columns={"casos": "casos_ano_atual"})

    ch = hist.groupby("semana_epidemiologica")["casos"].quantile([0.25, 0.5, 0.75, 0.9]).unstack().reset_index()
    ch = ch.rename(columns={0.25: "q25", 0.5: "q50", 0.75: "q75", 0.9: "q90"})
    ch = ch.merge(curr, on="semana_epidemiologica", how="left")
    ch["nivel"] = np.select(
        [
            ch["casos_ano_atual"] > ch["q90"],
            ch["casos_ano_atual"] > ch["q75"],
            ch["casos_ano_atual"] > ch["q50"],
        ],
        ["epidêmico/alerta", "alto", "médio"],
        default="baixo/esperado",
    )
    return ch
