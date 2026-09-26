"""Registro central de schemas e compatibilidade do Meningites VNext."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaContract:
    artifact: str
    current: str
    accepted: tuple[str, ...]


SCHEMAS = {
    "agent_context": SchemaContract("agent_context", "agent-context-vnext-1", ("agent-context-vnext-1",)),
    "rag_request": SchemaContract("rag_request", "rag-request-vnext-1", ("rag-request-vnext-1",)),
    "llm_response": SchemaContract("llm_response", "llm-response-vnext-2", ("llm-response-vnext-2",)),
    "validation": SchemaContract("validation", "vnext-validation-1", ("vnext-validation-1",)),
    "validation_evidence": SchemaContract("validation_evidence", "vnext-validation-evidence-1", ("vnext-validation-evidence-1",)),
    "preflight": SchemaContract("preflight", "vnext-preflight-1", ("vnext-preflight-1",)),
    "readiness": SchemaContract("readiness", "vnext-readiness-1", ("vnext-readiness-1",)),
    "release_readiness": SchemaContract("release_readiness", "vnext-release-readiness-1", ("vnext-release-readiness-1",)),
    "operational_manifest": SchemaContract("operational_manifest", "vnext-operational-manifest-1", ("vnext-operational-manifest-1",)),
}


def require_schema(payload: dict[str, Any], contract_name: str) -> str:
    if contract_name not in SCHEMAS:
        raise KeyError(f"Contrato desconhecido: {contract_name}")
    contract = SCHEMAS[contract_name]
    found = str(payload.get("schema_version", "") or "")
    if found not in contract.accepted:
        raise ValueError(
            f"Schema incompatível para {contract.artifact}: {found or '<ausente>'}. "
            f"Aceitos: {list(contract.accepted)}"
        )
    return found


def schema_catalog() -> dict[str, dict[str, Any]]:
    return {
        key: {
            "artifact": contract.artifact,
            "current": contract.current,
            "accepted": list(contract.accepted),
        }
        for key, contract in SCHEMAS.items()
    }
