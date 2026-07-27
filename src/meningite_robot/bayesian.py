from __future__ import annotations

import pandas as pd


def bayesian_rate_model_placeholder(df: pd.DataFrame) -> pd.DataFrame:
    """Modelo bayesiano opcional.

    PyMC3 pode ser usado para suavização de risco municipal ou estimação de incidência latente.
    Este placeholder evita quebrar o pipeline em ambientes sem PyMC3.
    """
    try:
        import pymc3 as pm  # noqa: F401
    except Exception as exc:
        return pd.DataFrame({
            "status": ["pymc3_indisponivel"],
            "mensagem": [str(exc)],
            "uso_recomendado": ["suavização bayesiana de incidência municipal e modelos ecológicos com clima"],
        })

    return pd.DataFrame({
        "status": ["pymc3_disponivel"],
        "mensagem": ["Implementar modelo hierárquico municipal: casos ~ Poisson(população * risco), risco com efeito espacial/temporal."],
    })
