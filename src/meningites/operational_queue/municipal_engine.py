"""Motor municipal determinístico e explicável.

Este módulo não define conduta clínica. Ele transforma métricas operacionais
já calculadas em sinais rastreáveis usando regras explicitamente configuradas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from meningites.domain.contracts import Evidence, OperationalSignal, Trigger


@dataclass(frozen=True)
class MunicipalSnapshot:
    municipality_code: str
    municipality_name: str
    metrics: Mapping[str, Any]
    evidence: Sequence[Evidence]


@dataclass(frozen=True)
class SignalRule:
    rule_id: str
    metric: str
    title: str
    category: str
    priority: str
    operator: str
    threshold: float
    description: str
    suggested_actions: Sequence[str] = ()
    normative_reference: str | None = None
    normative_validity: str | None = None

    def matches(self, value: Any) -> bool:
        if value is None:
            return False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        operations = {
            "gt": numeric > self.threshold,
            "gte": numeric >= self.threshold,
            "lt": numeric < self.threshold,
            "lte": numeric <= self.threshold,
            "eq": numeric == self.threshold,
        }
        if self.operator not in operations:
            raise ValueError(f"Operador não suportado: {self.operator}")
        return operations[self.operator]


class MunicipalSituationEngine:
    def __init__(self, rules: Iterable[SignalRule]):
        self.rules = tuple(rules)
        ids = [r.rule_id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rule_id deve ser único.")

    def evaluate(self, snapshot: MunicipalSnapshot) -> list[OperationalSignal]:
        if not snapshot.evidence:
            raise ValueError("Snapshot municipal exige evidência/procedência.")

        signals: list[OperationalSignal] = []
        for rule in self.rules:
            value = snapshot.metrics.get(rule.metric)
            if not rule.matches(value):
                continue

            evidence = list(snapshot.evidence)
            if rule.normative_reference:
                evidence.append(
                    Evidence(
                        source="normativa",
                        observed_at=datetime.now(),
                        reference=rule.normative_reference,
                        validity=rule.normative_validity,
                        metadata={"rule_id": rule.rule_id},
                    )
                )

            signals.append(
                OperationalSignal(
                    signal_id=f"{snapshot.municipality_code}:{rule.rule_id}",
                    municipality_code=snapshot.municipality_code,
                    title=rule.title,
                    category=rule.category,
                    priority=rule.priority,
                    trigger=Trigger(
                        rule_id=rule.rule_id,
                        description=rule.description,
                        value=value,
                        threshold=rule.threshold,
                    ),
                    evidence=tuple(evidence),
                    suggested_actions=tuple(rule.suggested_actions),
                )
            )
        return sorted(signals, key=_priority_key, reverse=True)


_PRIORITY = {"critica": 4, "crítica": 4, "alta": 3, "moderada": 2, "atencao": 2, "atenção": 2, "informativa": 1}


def _priority_key(signal: OperationalSignal) -> int:
    return _PRIORITY.get(signal.priority.strip().lower(), 0)
