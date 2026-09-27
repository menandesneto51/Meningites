"""Interface de consulta auditável do agente epidemiológico VNext."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from meningites.agent.operational_agent import EpidemiologicalAgent
from meningites.agent.rag_adapter import NormativeRetriever, build_grounded_request, render_prompt
from meningites.agent.llm_runner import run_validated_llm
from meningites.domain.territory import normalize_municipality_code


def _resolve_municipality(agent: EpidemiologicalAgent, value: str) -> dict[str, Any] | None:
    target = value.strip().casefold()
    target_code = normalize_municipality_code(value)
    for row in agent.context.get("municipalities", []):
        row_code = normalize_municipality_code(row.get("codigo_municipio", ""))
        if target_code and row_code == target_code:
            return row
        if str(row.get("municipio", "")).strip().casefold() == target:
            return row
    return None


def _llm_safety(agent: EpidemiologicalAgent) -> dict[str, Any]:
    quality = agent.context.get("data_quality")
    if not isinstance(quality, dict):
        return {
            "allowed": False,
            "reason": "data_quality_ausente",
            "blocking_divergences_n": None,
        }
    blocking_n = int(quality.get("blocking_divergences_n", 0) or 0)
    has_blocking = bool(quality.get("has_blocking_divergences")) or blocking_n > 0
    return {
        "allowed": not has_blocking,
        "reason": "" if not has_blocking else "data_quality_bloqueante",
        "blocking_divergences_n": blocking_n,
    }


def query_agent(
    *,
    context_path: str | Path,
    kb_path: str | Path,
    question: str,
    scope: str = "Mato Grosso",
    mode: str = "auto",
    use_llm: bool = False,
) -> dict[str, Any]:
    agent = EpidemiologicalAgent.from_file(context_path)
    retriever = NormativeRetriever.from_csv(kb_path)

    resolved_mode = mode
    deterministic = None
    municipality = _resolve_municipality(agent, scope)

    if mode == "auto":
        if scope.casefold() in {"mt", "mato grosso", "estadual"}:
            resolved_mode = "state"
        elif municipality is not None:
            resolved_mode = "municipality"
        elif any(str(r.get("regional", "")).casefold() == scope.casefold() for r in agent.context.get("regional_summary", [])):
            resolved_mode = "regional"
        else:
            resolved_mode = "rag"

    if resolved_mode == "state":
        deterministic = agent.state_briefing()
    elif resolved_mode == "regional":
        deterministic = agent.regional_briefing(scope)
    elif resolved_mode == "municipality":
        if municipality is None:
            deterministic = agent.municipality_explanation(scope)
        else:
            deterministic = agent.municipality_explanation(str(municipality.get("codigo_municipio")))
    elif resolved_mode == "gaps":
        deterministic = agent.data_gaps()
    elif resolved_mode != "rag":
        raise ValueError(f"Modo inválido: {resolved_mode}")

    package = build_grounded_request(question, agent, retriever, scope=scope)
    prompt = render_prompt(package)

    llm_safety = _llm_safety(agent)

    output: dict[str, Any] = {
        "schema_version": "agent-query-vnext-1",
        "question": question,
        "scope": scope,
        "mode": resolved_mode,
        "deterministic": asdict(deterministic) if deterministic is not None else None,
        "rag": {
            "evidence_n": len(package.get("normative_evidence", [])),
            "package": package,
        },
        "llm": {
            "requested": bool(use_llm),
            "executed": False,
            "blocked": bool(use_llm) and not llm_safety["allowed"],
            "block_reason": llm_safety["reason"] if bool(use_llm) and not llm_safety["allowed"] else "",
            "safety": llm_safety,
            "result": None,
        },
        "human_validation_required": True,
    }

    if use_llm and llm_safety["allowed"]:
        output["llm"]["executed"] = True
        output["llm"]["result"] = run_validated_llm(package, prompt)

    return output


def save_query_result(result: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return target
