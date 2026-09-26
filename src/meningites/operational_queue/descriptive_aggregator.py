"""Agregadores descritivos municipais.

Essas métricas enriquecem a situação municipal, mas não criam sinais por si só.
Isso evita converter score legado, volume de doses ou outros contextos em novas
regras de decisão sem validação epidemiológica explícita.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites.domain.contracts import Evidence
from meningites.operational_queue.legacy_aggregator import _norm_code
from meningites.operational_queue.municipal_engine import MunicipalSnapshot


def _score_v25(root: Path, generated_at: datetime | None) -> list[MunicipalSnapshot]:
    path = root / "score_risco_municipal_nt154_v25.csv"
    if not path.exists() or path.stat().st_size == 0:
        return []
    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    if frame.empty or "codigo_municipio_v17" not in frame.columns:
        return []

    metric_cols = [
        c for c in [
            "dm_lab_90d",
            "dm_90d",
            "pct_sorogrupo_dm_90d",
            "pct_quimio_dm_90d",
            "incidencia_dm_90d_100mil",
            "score_risco_nt154_v25",
            "prioridade",
            "norma",
        ] if c in frame.columns
    ]
    out = []
    for _, row in frame.iterrows():
        code = _norm_code(row["codigo_municipio_v17"])
        if not code:
            continue
        out.append(
            MunicipalSnapshot(
                municipality_code=code,
                municipality_name=str(row.get("municipio_v17", "") or "").strip(),
                metrics={f"v25_{c}": row[c] for c in metric_cols},
                evidence=(
                    Evidence(
                        source=path.name,
                        observed_at=generated_at,
                        reference=str(path),
                        metadata={
                            "kind": "descriptive",
                            "note": "Score e prioridade reproduzidos do módulo 26; não constituem nova regra VNext.",
                        },
                    ),
                ),
            )
        )
    return out


def _cipv_v34(root: Path, generated_at: datetime | None) -> list[MunicipalSnapshot]:
    path = root / "cipv_doses_agregadas_v34.csv"
    if not path.exists() or path.stat().st_size == 0:
        return []
    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    required = {"codigo_municipio_v34", "ano_dose_v34", "n_doses"}
    if frame.empty or not required.issubset(frame.columns):
        return []

    frame["ano_dose_v34"] = pd.to_numeric(frame["ano_dose_v34"], errors="coerce")
    frame["n_doses"] = pd.to_numeric(frame["n_doses"], errors="coerce").fillna(0)
    latest = frame["ano_dose_v34"].dropna().max()
    if pd.isna(latest):
        return []
    current = frame[frame["ano_dose_v34"].eq(latest)].copy()

    rows = []
    for code_raw, group in current.groupby("codigo_municipio_v34", dropna=False):
        code = _norm_code(code_raw)
        if not code:
            continue
        name = ""
        if "municipio_v34" in group.columns:
            names = group["municipio_v34"].dropna().astype(str).str.strip()
            names = names[~names.str.lower().isin({"", "nan", "none", "<na>"})]
            if not names.empty:
                name = names.iloc[0]
        metrics = {
            "cipv_ano_mais_recente": int(latest),
            "cipv_doses_ano_mais_recente": float(group["n_doses"].sum()),
        }
        if "imuno_grupo_v34" in group.columns:
            for imuno, sub in group.groupby("imuno_grupo_v34", dropna=False):
                key = str(imuno).strip().lower().replace(" ", "_").replace("/", "_")
                if key and key not in {"nan", "none", "<na>"}:
                    metrics[f"cipv_doses_{key}_ano_mais_recente"] = float(sub["n_doses"].sum())
        rows.append(
            MunicipalSnapshot(
                municipality_code=code,
                municipality_name=name,
                metrics=metrics,
                evidence=(
                    Evidence(
                        source=path.name,
                        observed_at=generated_at,
                        reference=str(path),
                        metadata={
                            "kind": "descriptive",
                            "year": int(latest),
                            "note": "Número de doses; não é cobertura populacional.",
                        },
                    ),
                ),
            )
        )
    return rows


def descriptive_snapshots(
    outdir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> list[MunicipalSnapshot]:
    root = Path(outdir)
    return [*_score_v25(root, generated_at), *_cipv_v34(root, generated_at)]


def merge_snapshots(*collections: list[MunicipalSnapshot]) -> list[MunicipalSnapshot]:
    merged: dict[str, dict] = {}
    for collection in collections:
        for snapshot in collection:
            item = merged.setdefault(
                snapshot.municipality_code,
                {"name": snapshot.municipality_name, "metrics": {}, "evidence": []},
            )
            if not item["name"] and snapshot.municipality_name:
                item["name"] = snapshot.municipality_name
            item["metrics"].update(snapshot.metrics)
            item["evidence"].extend(snapshot.evidence)
    return [
        MunicipalSnapshot(
            municipality_code=code,
            municipality_name=data["name"],
            metrics=data["metrics"],
            evidence=tuple(data["evidence"]),
        )
        for code, data in sorted(merged.items())
    ]
