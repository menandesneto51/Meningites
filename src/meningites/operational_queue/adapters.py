"""Adaptadores de artefatos legados para o modelo VNext.

A camada mantém o motor independente de pandas e dos nomes versionados.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from meningites.domain.contracts import Evidence
from meningites.operational_queue.municipal_engine import MunicipalSnapshot


def snapshots_from_csv(
    path: str | Path,
    *,
    municipality_code_col: str,
    municipality_name_col: str,
    metric_columns: Iterable[str],
    source: str,
    generated_at: datetime | None = None,
) -> list[MunicipalSnapshot]:
    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    required = {municipality_code_col, municipality_name_col, *metric_columns}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Contrato de entrada inválido; colunas ausentes: {missing}")

    metrics = tuple(metric_columns)
    snapshots: list[MunicipalSnapshot] = []
    for _, row in frame.iterrows():
        code = str(row[municipality_code_col]).strip()
        if not code or code.lower() in {"nan", "none", "<na>"}:
            continue
        snapshots.append(
            MunicipalSnapshot(
                municipality_code=code,
                municipality_name=str(row[municipality_name_col]).strip(),
                metrics={column: row[column] for column in metrics},
                evidence=(
                    Evidence(
                        source=source,
                        observed_at=generated_at,
                        reference=str(Path(path)),
                        metadata={"adapter": "csv"},
                    ),
                ),
            )
        )
    return snapshots
