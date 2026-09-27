"""Contrato estruturado e validação de respostas LLM VNext."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from meningites.domain.schema_registry import require_schema


@dataclass(frozen=True)
class StructuredValidationResult:
    accepted: bool
    issues: tuple[str, ...]
    parsed: dict[str, Any] | None
    requires_human_review: bool


def _resolve_path(root: Any, path: str) -> tuple[bool, Any]:
    current = root
    for token in path.split("."):
        if token == "":
            return False, None
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
        elif isinstance(current, list):
            try:
                idx = int(token)
            except ValueError:
                return False, None
            if idx < 0 or idx >= len(current):
                return False, None
            current = current[idx]
        else:
            return False, None
    return True, current


def parse_structured_response(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        value = json.loads(raw)
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def validate_structured_llm_response(package: dict[str, Any], response_text: str) -> StructuredValidationResult:
    payload = parse_structured_response(response_text)
    if payload is None:
        return StructuredValidationResult(False, ("structured_json_invalido",), None, True)

    issues: list[str] = []
    try:
        require_schema(payload, "llm_response")
    except ValueError:
        issues.append("schema_version_invalido")

    for key in ("facts", "interpretations", "recommendations", "limitations"):
        if not isinstance(payload.get(key), list):
            issues.append("campo_invalido:" + key)

    if payload.get("human_validation_required") is not True:
        issues.append("human_validation_required_deve_ser_true")

    canonical = package.get("canonical_facts", {})
    evidence = package.get("normative_evidence") or []

    data_quality = canonical.get("data_quality", {}) if isinstance(canonical, dict) else {}
    if isinstance(data_quality, dict):
        blocking_n = int(data_quality.get("blocking_divergences_n", 0) or 0)
        if bool(data_quality.get("has_blocking_divergences")) or blocking_n > 0:
            issues.append("data_quality_bloqueante")
    evidence_ids = {str(item.get("id", "")) for item in evidence if str(item.get("id", "")).strip()}

    for section in ("facts", "interpretations"):
        rows = payload.get(section) if isinstance(payload.get(section), list) else []
        for idx, item in enumerate(rows):
            if not isinstance(item, dict):
                issues.append(f"{section}[{idx}]_invalido")
                continue
            if not str(item.get("text", "")).strip():
                issues.append(f"{section}[{idx}]_texto_ausente")
            refs = item.get("fact_refs")
            if not isinstance(refs, list) or not refs:
                issues.append(f"{section}[{idx}]_fact_refs_ausentes")
                continue
            for ref in refs:
                if not isinstance(ref, str):
                    issues.append(f"{section}[{idx}]_fact_ref_invalido")
                    continue
                ok, _ = _resolve_path(canonical, ref)
                if not ok:
                    issues.append(f"{section}[{idx}]_fact_ref_desconhecido:{ref}")

    recs = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else []
    for idx, item in enumerate(recs):
        if not isinstance(item, dict):
            issues.append(f"recommendations[{idx}]_invalido")
            continue
        if not str(item.get("text", "")).strip():
            issues.append(f"recommendations[{idx}]_texto_ausente")
        refs = item.get("fact_refs")
        if not isinstance(refs, list):
            issues.append(f"recommendations[{idx}]_fact_refs_invalido")
            refs = []
        elif not refs:
            issues.append(f"recommendations[{idx}]_fact_refs_ausentes")
        for ref in refs:
            if not isinstance(ref, str):
                issues.append(f"recommendations[{idx}]_fact_ref_invalido")
                continue
            ok, _ = _resolve_path(canonical, ref)
            if not ok:
                issues.append(f"recommendations[{idx}]_fact_ref_desconhecido:{ref}")
        normative_ids = item.get("normative_evidence_ids", [])
        if not isinstance(normative_ids, list):
            issues.append(f"recommendations[{idx}]_normative_ids_invalido")
            normative_ids = []
        if evidence and not normative_ids:
            issues.append(f"recommendations[{idx}]_sem_fundamentacao_normativa")
        for evidence_id in normative_ids:
            if str(evidence_id) not in evidence_ids:
                issues.append(f"recommendations[{idx}]_normative_id_desconhecido:{evidence_id}")

    limitations = payload.get("limitations") if isinstance(payload.get("limitations"), list) else []
    if not limitations:
        issues.append("limitations_vazio")

    return StructuredValidationResult(not issues, tuple(issues), payload, True)


def render_structured_response(payload: dict[str, Any]) -> str:
    sections = [
        ("FATOS", payload.get("facts") or []),
        ("INTERPRETAÇÃO", payload.get("interpretations") or []),
        ("RECOMENDAÇÕES FUNDAMENTADAS", payload.get("recommendations") or []),
    ]
    lines: list[str] = []
    for title, rows in sections:
        lines.append(title)
        if not rows:
            lines.append("- Nenhum item.")
        for item in rows:
            lines.append("- " + str(item.get("text", "")).strip())
        lines.append("")
    lines.append("LIMITAÇÕES")
    for item in payload.get("limitations") or []:
        lines.append("- " + str(item))
    return "\n".join(lines).strip()
