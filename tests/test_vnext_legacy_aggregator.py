from pathlib import Path

import pandas as pd

from meningites.operational_queue.legacy_aggregator import aggregate_artifacts
from meningites.operational_queue.municipal_engine import MunicipalSituationEngine
from meningites.operational_queue.rules_catalog import PRODUCTION_RULES


def test_aggregates_actionable_legacy_queues_by_municipality(tmp_path: Path):
    pd.DataFrame([
        {"codigo_municipio_v33": "5103403", "municipio_v33": "Cuiabá", "x": 1},
        {"codigo_municipio_v33": "5103403", "municipio_v33": "Cuiabá", "x": 2},
        {"codigo_municipio_v33": "5108402", "municipio_v33": "Várzea Grande", "x": 3},
    ]).to_csv(tmp_path / "sih_fila_investigacao_v33.csv", index=False, encoding="utf-8-sig")

    snapshots = aggregate_artifacts(tmp_path)
    by_code = {s.municipality_code: s for s in snapshots}

    assert by_code["510340"].metrics["sih_sem_sinan_n"] == 2
    assert by_code["510840"].metrics["sih_sem_sinan_n"] == 1
    assert by_code["510340"].evidence[0].metadata["rows"] == 2


def test_catalog_turns_existing_queue_into_explainable_signal(tmp_path: Path):
    pd.DataFrame([
        {"codigo_municipio_v17": "5103403", "municipio_v17": "Cuiabá"},
    ]).to_csv(tmp_path / "gal_fila_tipagem_sinan_v32.csv", index=False, encoding="utf-8-sig")

    snapshot = aggregate_artifacts(tmp_path)[0]
    signals = MunicipalSituationEngine(PRODUCTION_RULES).evaluate(snapshot)

    assert any(s.trigger.rule_id == "gal-tipagem-pendente" for s in signals)
    signal = next(s for s in signals if s.trigger.rule_id == "gal-tipagem-pendente")
    assert signal.trigger.value == 1
    assert signal.evidence[0].source == "gal_fila_tipagem_sinan_v32.csv"


def test_missing_artifacts_do_not_create_synthetic_signals(tmp_path: Path):
    assert aggregate_artifacts(tmp_path) == []


def test_merges_six_and_seven_digit_codes_into_one_municipality(tmp_path: Path):
    pd.DataFrame([
        {"codigo_municipio_v33": "510340", "municipio_v33": "Cuiabá"},
    ]).to_csv(tmp_path / "sih_fila_investigacao_v33.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"codigo_municipio_v17": "5103403", "municipio_v17": "Cuiabá"},
    ]).to_csv(tmp_path / "gal_fila_tipagem_sinan_v32.csv", index=False, encoding="utf-8-sig")

    snapshots = aggregate_artifacts(tmp_path)
    assert len(snapshots) == 1
    assert snapshots[0].municipality_code == "510340"
    assert snapshots[0].metrics["sih_sem_sinan_n"] == 1
    assert snapshots[0].metrics["gal_tipagem_pendente_n"] == 1
