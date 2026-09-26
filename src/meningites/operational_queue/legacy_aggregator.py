"""Agregação municipal dos artefatos operacionais legados.

Normaliza contagens acionáveis sem recalcular definições epidemiológicas.
Cada métrica mantém a fonte de onde foi derivada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from meningites.domain.contracts import Evidence
from meningites.operational_queue.municipal_engine import MunicipalSnapshot


@dataclass(frozen=True)
class ArtifactSpec:
    filename: str
    metric: str
    municipality_code_candidates: tuple[str, ...]
    municipality_name_candidates: tuple[str, ...]
    row_filter_column: str | None = None
    row_filter_values: tuple[str, ...] = ()


DEFAULT_ARTIFACTS = (
    ArtifactSpec(
        "fila_cievs_unificada_v23.csv", "fila_cievs_n",
        ("codigo_municipio_v17", "codigo_municipio"), ("municipio_v17", "territorio", "municipio"),
    ),
    ArtifactSpec(
        "gal_fila_tipagem_sinan_v32.csv", "gal_tipagem_pendente_n",
        ("codigo_municipio_v17", "codigo_municipio"), ("municipio_v17", "municipio"),
    ),
    ArtifactSpec(
        "sih_fila_investigacao_v33.csv", "sih_sem_sinan_n",
        ("codigo_municipio_v33",), ("municipio_v33",),
    ),
    ArtifactSpec(
        "redcap_gap_sinan_v35.csv", "redcap_sem_sinan_n",
        ("codigo_municipio_v35",), ("municipio_v35",),
    ),
)


def _pick(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    return next((c for c in candidates if c in available), None)


def _norm_code(value) -> str:
    raw = str(value).strip()
    if raw.lower() in {"", "nan", "none", "<na>"}:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[:7] if digits else raw


def aggregate_artifacts(
    outdir: str | Path,
    specs: Iterable[ArtifactSpec] = DEFAULT_ARTIFACTS,
    *,
    generated_at: datetime | None = None,
) -> list[MunicipalSnapshot]:
    root = Path(outdir)
    municipalities: dict[str, dict] = {}

    for spec in specs:
        path = root / spec.filename
        if not path.exists() or path.stat().st_size == 0:
            continue
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        if frame.empty:
            continue

        code_col = _pick(frame.columns, spec.municipality_code_candidates)
        name_col = _pick(frame.columns, spec.municipality_name_candidates)
        if code_col is None:
            # Sem chave territorial confiável, não inferir município pelo texto.
            continue

        if spec.row_filter_column and spec.row_filter_column in frame.columns and spec.row_filter_values:
            allowed = {v.casefold() for v in spec.row_filter_values}
            frame = frame[
                frame[spec.row_filter_column].astype(str).str.strip().str.casefold().isin(allowed)
            ]

        for code, group in frame.groupby(frame[code_col].map(_norm_code), dropna=False):
            if not code:
                continue
            item = municipalities.setdefault(
                code,
                {"name": "", "metrics": {}, "evidence": []},
            )
            if name_col and not item["name"]:
                names = group[name_col].dropna().astype(str).str.strip()
                names = names[~names.str.lower().isin({"", "nan", "none", "<na>"})]
                if not names.empty:
                    item["name"] = names.iloc[0]
            item["metrics"][spec.metric] = int(len(group))
            item["evidence"].append(
                Evidence(
                    source=spec.filename,
                    observed_at=generated_at,
                    reference=str(path),
                    metadata={"metric": spec.metric, "rows": int(len(group))},
                )
            )

    return [
        MunicipalSnapshot(
            municipality_code=code,
            municipality_name=data["name"],
            metrics=data["metrics"],
            evidence=tuple(data["evidence"]),
        )
        for code, data in sorted(municipalities.items())
    ]
