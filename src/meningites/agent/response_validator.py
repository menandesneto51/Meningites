"""Validação pós-resposta do LLM para o agente VNext."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    issues: tuple[str, ...]
    requires_human_review: bool


_REQUIRED_SECTIONS = ("FATOS", "INTERPRETAÇÃO", "RECOMENDAÇÕES", "LIMITAÇÕES")


def _extract_numbers(obj: Any) -> set[str]:
    text = json.dumps(obj, ensure_ascii=False, default=str)
    return set(re.findall(r"(?<!\w)\d+(?:[\.,]\d+)?", text))


def validate_llm_response(package: dict[str, Any], response_text: str) -> ValidationResult:
    issues: list[str] = []
    upper = response_text.upper()

    for section in _REQUIRED_SECTIONS:
        if section not in upper:
            issues.append(f"secao_ausente:{section.lower()}")

    canonical_numbers = _extract_numbers(package.get("canonical_facts", {}))
    response_numbers = _extract_numbers(response_text)
    normative_numbers = _extract_numbers(package.get("normative_evidence", []))
    allowed_numbers = canonical_numbers | normative_numbers
    invented_numbers = sorted(n for n in response_numbers if n not in allowed_numbers)
    if invented_numbers:
        issues.append("numeros_nao_rastreados:" + ",".join(invented_numbers[:10]))

    evidence = package.get("normative_evidence") or []
    if evidence:
        sources = [str(item.get("fonte", "")).strip() for item in evidence if str(item.get("fonte", "")).strip()]
        if sources and not any(source.casefold() in response_text.casefold() for source in sources):
            issues.append("fonte_normativa_nao_citada")
    else:
        insufficiency_terms = ("insuficiente", "não há evidência", "nao ha evidencia", "sem evidência", "sem evidencia")
        if not any(term in response_text.casefold() for term in insufficiency_terms):
            issues.append("evidencia_normativa_ausente_nao_declarada")

    prohibited = (
        "recomendo tratamento",
        "prescrever",
        "iniciar antibiótico",
        "iniciar antibiotico",
        "dispensar quimioprofilaxia",
    )
    if any(term in response_text.casefold() for term in prohibited):
        issues.append("conduta_clinica_nao_autorizada")

    return ValidationResult(
        accepted=not issues,
        issues=tuple(issues),
        requires_human_review=True,
    )
