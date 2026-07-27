from __future__ import annotations

import pandas as pd
import numpy as np


def duplicate_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Detecção de duplicidades exatas e prováveis.

    Estratégia:
    1. Exata por NumeroNotificacao.
    2. Bloqueio por data de nascimento + sexo + município + data de sintomas.
    3. Se recordlinkage estiver instalado, pode ser expandido posteriormente para similaridade textual.
    """
    rows = []

    if "NumeroNotificacao" in df.columns:
        dup = df[df["NumeroNotificacao"].duplicated(keep=False)].copy()
        for _, r in dup.iterrows():
            rows.append({
                "tipo": "exata_numero_notificacao",
                "NumeroNotificacao": r.get("NumeroNotificacao"),
                "indice": int(r.name),
                "score": 1.0,
            })

    block_cols = [c for c in ["DataNascimento", "SexoPaciente", "CodigoMunicipioResidencia", "DataPrimeirosSintomas"] if c in df.columns]
    if len(block_cols) >= 3:
        sizes = df.groupby(block_cols, dropna=False).size().reset_index(name="n")
        suspicious = sizes[sizes["n"] > 1]
        if not suspicious.empty:
            flagged = df.merge(suspicious[block_cols], on=block_cols, how="inner")
            for _, r in flagged.iterrows():
                rows.append({
                    "tipo": "provavel_bloco_demografico_temporal",
                    "NumeroNotificacao": r.get("NumeroNotificacao"),
                    "indice": int(r.name) if isinstance(r.name, int) else None,
                    "score": 0.85,
                })

    return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame(columns=["tipo", "NumeroNotificacao", "indice", "score"])
