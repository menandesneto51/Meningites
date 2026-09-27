"""Manifesto operacional consolidado do Meningites VNext."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meningites.domain.schema_registry import require_schema


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_operational_manifest(outdir: str | Path) -> dict[str, Any]:
    root = Path(outdir)
    context = _load(root / "agente_epidemiologico_contexto_vnext.json") or {}
    validation = _load(root / "validacao_vnext.json") or {}
    preflight = _load(root / "preflight_vnext.json") or {}
    evidence = _load(root / "evidencia_validacao_vnext.json") or {}
    readiness = _load(root / "prontidao_vnext.json") or {}
    release = _load(root / "release_readiness_vnext.json") or {}

    compatibility = {}
    for name, payload, contract in [
        ("context", context, "agent_context"),
        ("validation", validation, "validation"),
        ("preflight", preflight, "preflight"),
        ("evidence", evidence, "validation_evidence"),
        ("readiness", readiness, "readiness"),
        ("release_readiness", release, "release_readiness"),
    ]:
        if not payload:
            compatibility[name] = False
            continue
        try:
            require_schema(payload, contract)
            compatibility[name] = True
        except ValueError:
            compatibility[name] = False

    quality = context.get("data_quality") or {}
    validation_pass = str(validation.get("overall_status", "")).lower() == "pass"
    preflight_pass = str(preflight.get("status", "")).lower() == "pass"
    quality_safe = (
        not bool(quality.get("has_blocking_divergences"))
        and int(quality.get("blocking_divergences_n", 0) or 0) == 0
    )
    llm_allowed = (
        bool(context)
        and compatibility["context"]
        and compatibility["validation"]
        and validation_pass
        and quality_safe
    )

    artifacts = {
        "context": "agente_epidemiologico_contexto_vnext.json",
        "validation": "validacao_vnext.json",
        "preflight": "preflight_vnext.json",
        "evidence": "evidencia_validacao_vnext.json",
        "readiness": "prontidao_vnext.json",
        "release_readiness": "release_readiness_vnext.json",
    }

    return {
        "schema_version": "vnext-operational-manifest-1",
        "context_schema_version": context.get("schema_version"),
        "validation_status": validation.get("overall_status", "not_validated"),
        "preflight_status": preflight.get("status", "not_run"),
        "evidence_captured": bool(evidence),
        "readiness_status": readiness.get("status", "not_evaluated"),
        "release_readiness_status": release.get("status", "not_evaluated"),
        "data_quality": {
            "blocking_divergences_n": int(quality.get("blocking_divergences_n", 0) or 0),
            "missing_artifacts_n": int(quality.get("missing_artifacts_n", 0) or 0),
            "has_blocking_divergences": bool(quality.get("has_blocking_divergences")),
        },
        "execution_policy": {
            "deterministic_allowed": bool(context),
            "rag_allowed": bool(context),
            "llm_allowed": llm_allowed,
            "llm_requires_human_review": True,
            "api_external_bind_requires_token": True,
            "api_query_requires_pass_gate": True,
        },
        "normative_policy": {
            "current_only_default": True,
            "unknown_vigency_is_current": False,
            "structured_response_schema": "llm-response-vnext-2",
        },
        "artifacts": artifacts,
        "schema_compatibility": compatibility,
        "human_review_required": True,
    }


def publish_operational_manifest(outdir: str | Path) -> dict[str, Path]:
    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    payload = build_operational_manifest(root)
    json_path = root / "manifesto_operacional_vnext.json"
    md_path = root / "MANIFESTO_OPERACIONAL_VNEXT.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Manifesto Operacional — Meningites VNext",
        "",
        f"- Validação: **{str(payload['validation_status']).upper()}**",
        f"- Preflight: **{str(payload['preflight_status']).upper()}**",
        f"- Readiness: **{str(payload['readiness_status']).upper()}**",
        f"- Release readiness: **{str(payload['release_readiness_status']).upper()}**",
        f"- LLM permitido: **{payload['execution_policy']['llm_allowed']}**",
        f"- Divergências bloqueantes: **{payload['data_quality']['blocking_divergences_n']}**",
        "",
        "## Políticas",
        "",
        "- Vigência normativa desconhecida é fail-closed.",
        "- Resposta LLM estruturada usa llm-response-vnext-2.",
        "- Revisão humana é obrigatória.",
        "- Bind externo da API exige token.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"manifest_json": json_path, "manifest_md": md_path}
