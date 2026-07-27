from __future__ import annotations

import numpy as np
import pandas as pd


def survival_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo de sobrevivência: tempo dos primeiros sintomas até evolução/desfecho.

    Usa lifelines se disponível; caso contrário, devolve estratos e medianas.
    """
    if "tempo_sintomas_evolucao_dias" not in df.columns:
        return pd.DataFrame({"erro": ["tempo_sintomas_evolucao_dias não disponível"]})

    d = df.copy()
    d = d[d["tempo_sintomas_evolucao_dias"].notna() & (d["tempo_sintomas_evolucao_dias"] >= 0)]
    if d.empty:
        return pd.DataFrame({"erro": ["Sem tempo válido entre sintomas e evolução."]})

    rows = []
    for strat in ["ClassificacaoMeningite", "FaixaEtaria", "SexoPaciente"]:
        if strat not in d.columns:
            continue
        tmp = d.groupby(strat, dropna=False).agg(
            n=("tempo_sintomas_evolucao_dias", "size"),
            obitos=("obito_meningite", "sum"),
            mediana_tempo=("tempo_sintomas_evolucao_dias", "median"),
            p75_tempo=("tempo_sintomas_evolucao_dias", lambda s: s.quantile(0.75)),
        ).reset_index()
        tmp["estrato"] = strat
        tmp = tmp.rename(columns={strat: "categoria"})
        rows.append(tmp)

    base = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    try:
        from lifelines import CoxPHFitter
        cox_df = d[["tempo_sintomas_evolucao_dias", "obito_meningite", "idade_anos", "hospitalizado"]].dropna()
        if len(cox_df) > 50 and cox_df["obito_meningite"].sum() > 10:
            cph = CoxPHFitter()
            cph.fit(cox_df, duration_col="tempo_sintomas_evolucao_dias", event_col="obito_meningite")
            summ = cph.summary.reset_index().rename(columns={"index": "variavel"})
            summ["estrato"] = "cox_model"
            summ["categoria"] = summ["covariate"] if "covariate" in summ.columns else summ.get("variavel", "")
            return pd.concat([base, summ], ignore_index=True, sort=False)
    except Exception:
        pass

    return base
