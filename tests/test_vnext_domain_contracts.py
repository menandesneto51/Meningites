from datetime import datetime

import pytest

from meningites.domain.contracts import Evidence, OperationalSignal, Trigger


def test_operational_signal_requires_evidence():
    with pytest.raises(ValueError, match="evidência"):
        OperationalSignal(
            signal_id="sig-1",
            municipality_code="5103403",
            title="Pendência laboratorial",
            category="laboratorio",
            priority="alta",
            trigger=Trigger(
                rule_id="lab-pending",
                description="Exemplo contratual sem regra clínica",
                value=1,
            ),
            evidence=[],
        )


def test_operational_signal_keeps_rule_and_provenance_together():
    signal = OperationalSignal(
        signal_id="sig-2",
        municipality_code="5103403",
        title="Sinal operacional de teste",
        category="qualidade",
        priority="moderada",
        trigger=Trigger(
            rule_id="quality-test",
            description="Regra técnica de teste",
            value=2,
            threshold=1,
        ),
        evidence=[
            Evidence(
                source="SINAN",
                observed_at=datetime(2026, 9, 26, 12, 0),
                reference="artefato-de-teste",
                validity="teste",
            )
        ],
        suggested_actions=("Validar o registro na fonte.",),
    )

    assert signal.trigger.rule_id == "quality-test"
    assert signal.evidence[0].source == "SINAN"
    assert signal.suggested_actions
