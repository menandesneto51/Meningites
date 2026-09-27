"""Contratos centrais do Meningites VNext.

Primeira camada deliberadamente pequena: tipos estáveis para sinais explicáveis.
Não contém regras clínicas nem limiares.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Evidence:
    source: str
    observed_at: datetime | None = None
    reference: str | None = None
    validity: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trigger:
    rule_id: str
    description: str
    value: Any
    threshold: Any | None = None


@dataclass(frozen=True)
class OperationalSignal:
    signal_id: str
    municipality_code: str
    title: str
    category: str
    priority: str
    trigger: Trigger
    evidence: Sequence[Evidence]
    suggested_actions: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("OperationalSignal exige ao menos uma evidência.")
        if not self.municipality_code:
            raise ValueError("municipality_code é obrigatório.")
