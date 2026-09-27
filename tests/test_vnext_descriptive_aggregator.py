from pathlib import Path

import pandas as pd

from meningites.operational_queue.descriptive_aggregator import (
    descriptive_snapshots,
    merge_snapshots,
)
from meningites.operational_queue.legacy_aggregator import aggregate_artifacts


def test_imports_v25_score_as_descriptive_context(tmp_path: Path):
    pd.DataFrame([{
        "codigo_municipio_v17": "5103403",
        "municipio_v17": "Cuiabá",
        "dm_lab_90d": 2,
        "dm_90d": 3,
        "score_risco_nt154_v25": 52.5,
        "prioridade": "Alta",
        "norma": "NT 154/2024",
    }]).to_csv(tmp_path / "score_risco_municipal_nt154_v25.csv", index=False, encoding="utf-8-sig")

    snapshots = descriptive_snapshots(tmp_path)
    assert snapshots[0].metrics["v25_score_risco_nt154_v25"] == 52.5
    assert snapshots[0].evidence[0].metadata["kind"] == "descriptive"


def test_cipv_uses_latest_year_and_labels_doses_not_coverage(tmp_path: Path):
    pd.DataFrame([
        {"ano_dose_v34": 2025, "codigo_municipio_v34": "5103403", "municipio_v34": "Cuiabá", "imuno_grupo_v34": "MenC", "n_doses": 10},
        {"ano_dose_v34": 2026, "codigo_municipio_v34": "5103403", "municipio_v34": "Cuiabá", "imuno_grupo_v34": "MenC", "n_doses": 7},
        {"ano_dose_v34": 2026, "codigo_municipio_v34": "5103403", "municipio_v34": "Cuiabá", "imuno_grupo_v34": "Hib", "n_doses": 5},
    ]).to_csv(tmp_path / "cipv_doses_agregadas_v34.csv", index=False, encoding="utf-8-sig")

    snapshot = descriptive_snapshots(tmp_path)[0]
    assert snapshot.metrics["cipv_ano_mais_recente"] == 2026
    assert snapshot.metrics["cipv_doses_ano_mais_recente"] == 12
    assert "não é cobertura" in snapshot.evidence[0].metadata["note"].lower()


def test_merge_preserves_operational_and_descriptive_metrics(tmp_path: Path):
    pd.DataFrame([{
        "codigo_municipio_v33": "5103403",
        "municipio_v33": "Cuiabá",
    }]).to_csv(tmp_path / "sih_fila_investigacao_v33.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{
        "codigo_municipio_v17": "5103403",
        "municipio_v17": "Cuiabá",
        "score_risco_nt154_v25": 25,
    }]).to_csv(tmp_path / "score_risco_municipal_nt154_v25.csv", index=False, encoding="utf-8-sig")

    merged = merge_snapshots(aggregate_artifacts(tmp_path), descriptive_snapshots(tmp_path))
    assert len(merged) == 1
    assert merged[0].metrics["sih_sem_sinan_n"] == 1
    assert merged[0].metrics["v25_score_risco_nt154_v25"] == 25
