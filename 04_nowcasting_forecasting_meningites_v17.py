# -*- coding: utf-8 -*-
"""
04_nowcasting_forecasting_meningites_v17.py
Nowcasting simples e forecasting ensemble para 7, 15, 30 e 45 dias.
"""

import numpy as np
import pandas as pd
from meningites_v17_common import *

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
except Exception:
    RandomForestRegressor = None
    GradientBoostingRegressor = None

def make_features(series):
    d = series.copy()
    d["t"] = np.arange(len(d))
    d["dow"] = d["data"].dt.dayofweek
    d["month"] = d["data"].dt.month
    d["lag1"] = d["y"].shift(1)
    d["lag7"] = d["y"].shift(7)
    d["ma7"] = d["y"].rolling(7, min_periods=1).mean()
    d["ma14"] = d["y"].rolling(14, min_periods=1).mean()
    return d

def forecast_one(series, horizon):
    series = series.sort_values("data").copy()
    y = series["y"].astype(float).values
    last_date = series["data"].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")

    preds = []
    # Modelo 1: média móvel 7
    ma7 = np.nanmean(y[-7:]) if len(y) else 0
    preds.append(np.repeat(ma7, horizon))
    # Modelo 2: média móvel 14
    ma14 = np.nanmean(y[-14:]) if len(y) else ma7
    preds.append(np.repeat(ma14, horizon))
    # Modelo 3: sazonal semanal
    if len(y) >= 14:
        seasonal = np.array([y[-7 + (i % 7)] for i in range(horizon)])
    else:
        seasonal = np.repeat(ma7, horizon)
    preds.append(seasonal)
    # Modelo 4/5: ML
    feat = make_features(series).dropna()
    if len(feat) >= 30 and RandomForestRegressor is not None:
        features = ["t", "dow", "month", "lag1", "lag7", "ma7", "ma14"]
        X = feat[features]
        Y = feat["y"]
        models = []
        try:
            models.append(RandomForestRegressor(n_estimators=200, random_state=17, min_samples_leaf=2).fit(X, Y))
        except Exception:
            pass
        if GradientBoostingRegressor is not None:
            try:
                models.append(GradientBoostingRegressor(random_state=17).fit(X, Y))
            except Exception:
                pass
        hist = series.copy()
        for model in models:
            vals = []
            tmp = hist.copy()
            for i, dt in enumerate(future_dates):
                tf = make_features(tmp).iloc[-1:].copy()
                row = {
                    "t": len(tmp),
                    "dow": dt.dayofweek,
                    "month": dt.month,
                    "lag1": tmp["y"].iloc[-1],
                    "lag7": tmp["y"].iloc[-7] if len(tmp) >= 7 else tmp["y"].mean(),
                    "ma7": tmp["y"].tail(7).mean(),
                    "ma14": tmp["y"].tail(14).mean(),
                }
                pred = max(0, float(model.predict(pd.DataFrame([row]))[0]))
                vals.append(pred)
                tmp = pd.concat([tmp, pd.DataFrame({"data":[dt], "y":[pred]})], ignore_index=True)
            preds.append(np.array(vals))
    arr = np.vstack(preds)
    mean = arr.mean(axis=0)
    # IC por dispersão entre modelos + resíduo histórico
    resid_sd = float(np.nanstd(y[-30:])) if len(y) >= 5 else 1.0
    model_sd = arr.std(axis=0)
    sd = np.sqrt(model_sd**2 + resid_sd**2)
    lo = np.maximum(0, mean - 1.96 * sd)
    hi = mean + 1.96 * sd
    return pd.DataFrame({"data_prevista": future_dates, "pred": mean, "lower_95": lo, "upper_95": hi, "modelos_no_ensemble": arr.shape[0]})

def main():
    df = load_base_v17()
    df["data_ref_v17"] = pd.to_datetime(df["data_ref_v17"], errors="coerce")
    desfechos = {
        "casos": "caso_v17",
        "hospitalizacoes": "hospitalizacao_v17",
        "obitos_meningite": "obito_meningite_v17",
    }
    rows = []
    for nome, col in desfechos.items():
        s = df.groupby("data_ref_v17")[col].sum().reset_index().rename(columns={"data_ref_v17": "data", col: "y"})
        full = pd.DataFrame({"data": pd.date_range(s["data"].min(), s["data"].max(), freq="D")}).merge(s, on="data", how="left").fillna({"y": 0})
        for h in [7, 15, 30, 45]:
            f = forecast_one(full, h)
            f["desfecho"] = nome
            f["horizonte_dias"] = h
            rows.append(f)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out.to_csv(OUT / "forecasting_7_15_30_45_v17.csv", index=False, encoding="utf-8-sig")

    # Agregado por horizonte
    agg = out.groupby(["desfecho", "horizonte_dias"]).agg(
        valor_previsto=("pred", "sum"),
        ic95_inferior=("lower_95", "sum"),
        ic95_superior=("upper_95", "sum"),
        modelos_no_ensemble=("modelos_no_ensemble", "max")
    ).reset_index()
    # Incidência prevista: usa população mais recente agregada, se houver.
    pop = pd.to_numeric(df["populacao_v17"], errors="coerce").dropna()
    pop_total = pop.groupby(df.loc[pop.index, "codigo_municipio_v17"]).max().sum() if len(pop) else np.nan
    casos_agg = agg[agg["desfecho"].eq("casos")].copy()
    casos_agg["desfecho"] = "incidencia"
    casos_agg["valor_previsto"] = casos_agg["valor_previsto"] / pop_total * 100000 if pd.notna(pop_total) and pop_total else np.nan
    casos_agg["ic95_inferior"] = casos_agg["ic95_inferior"] / pop_total * 100000 if pd.notna(pop_total) and pop_total else np.nan
    casos_agg["ic95_superior"] = casos_agg["ic95_superior"] / pop_total * 100000 if pd.notna(pop_total) and pop_total else np.nan
    agg = pd.concat([agg, casos_agg], ignore_index=True)
    agg.to_csv(OUT / "forecasting_resumo_v17.csv", index=False, encoding="utf-8-sig")

    # Nowcasting simples da última semana
    max_date = df["data_ref_v17"].max()
    recent = df[df["data_ref_v17"] >= max_date - pd.Timedelta(days=14)]
    obs7 = recent[recent["data_ref_v17"] >= max_date - pd.Timedelta(days=6)]["caso_v17"].sum()
    prev7 = recent[(recent["data_ref_v17"] < max_date - pd.Timedelta(days=6))]["caso_v17"].sum()
    fator = (prev7 / obs7) if obs7 > 0 and prev7 > 0 else 1.0
    now = pd.DataFrame([{
        "data_referencia": max_date,
        "observado_7d": obs7,
        "fator_correcao_atraso": fator,
        "nowcasting_7d": obs7 * fator,
        "atraso_estimado": obs7 * fator - obs7,
        "interpretacao": "Nowcasting operacional por fator simples de atraso recente; revisar quando houver data de digitação/encerramento."
    }])
    now.to_csv(OUT / "nowcasting_v17.csv", index=False, encoding="utf-8-sig")
    print("[OK] Forecasting/nowcasting V17 gerado.")

if __name__ == "__main__":
    main()
