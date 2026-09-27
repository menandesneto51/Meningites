from datetime import datetime

import pytest

from meningites.domain.contracts import Evidence
from meningites.operational_queue.municipal_engine import (
    MunicipalSituationEngine,
    MunicipalSnapshot,
    SignalRule,
)


def _snapshot(**metrics):
    return MunicipalSnapshot(
        municipality_code="5103403",
        municipality_name="Cuiabá",
        metrics=metrics,
        evidence=(Evidence(source="artefato-teste", observed_at=datetime(2026, 9, 26)),),
    )


def test_engine_emits_explainable_signal_only_when_rule_matches():
    rule = SignalRule(
        rule_id="gal-tipagem-pendente",
        metric="gal_tipagem_pendente_n",
        title="Tipagem laboratorial pendente",
        category="laboratorio",
        priority="alta",
        operator="gt",
        threshold=0,
        description="Há registros na fila de tipagem.",
        suggested_actions=("Revisar a fila laboratorial correspondente.",),
        normative_reference="Referência oficial versionada pelo corpus do projeto",
        normative_validity="validar no índice de vigência",
    )
    engine = MunicipalSituationEngine([rule])

    signals = engine.evaluate(_snapshot(gal_tipagem_pendente_n=2))

    assert len(signals) == 1
    assert signals[0].trigger.value == 2
    assert signals[0].trigger.threshold == 0
    assert len(signals[0].evidence) == 2
    assert signals[0].suggested_actions


def test_engine_does_not_emit_when_rule_does_not_match():
    rule = SignalRule(
        rule_id="backlog",
        metric="backlog_n",
        title="Backlog",
        category="oportunidade",
        priority="moderada",
        operator="gt",
        threshold=0,
        description="Há backlog operacional.",
    )
    assert MunicipalSituationEngine([rule]).evaluate(_snapshot(backlog_n=0)) == []


def test_engine_rejects_snapshot_without_provenance():
    engine = MunicipalSituationEngine([])
    with pytest.raises(ValueError, match="evidência"):
        engine.evaluate(
            MunicipalSnapshot(
                municipality_code="5103403",
                municipality_name="Cuiabá",
                metrics={},
                evidence=(),
            )
        )


def test_engine_rejects_duplicate_rule_ids():
    rule = SignalRule(
        rule_id="duplicada",
        metric="x",
        title="x",
        category="qualidade",
        priority="moderada",
        operator="gt",
        threshold=0,
        description="teste",
    )
    with pytest.raises(ValueError, match="único"):
        MunicipalSituationEngine([rule, rule])
