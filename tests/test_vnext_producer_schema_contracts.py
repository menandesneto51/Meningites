import ast
from pathlib import Path

import pytest

from meningites.domain.schema_registry import SCHEMAS


PRODUCER_SOURCES = {
    "agent_context": Path("src/meningites/operational_queue/agent_context.py"),
    "rag_request": Path("src/meningites/agent/rag_adapter.py"),
    "validation": Path("src/meningites/validation/reconcile.py"),
    "validation_evidence": Path("src/meningites/validation/evidence.py"),
    "preflight": Path("pipelines/vnext_preflight.py"),
    "readiness": Path("src/meningites/validation/readiness.py"),
    "release_readiness": Path("src/meningites/validation/release_readiness.py"),
    "operational_manifest": Path("src/meningites/validation/operational_manifest.py"),
    "visual_review": Path("pipelines/vnext_record_visual_review.py"),
    "schema_catalog": Path("pipelines/vnext_schema_catalog.py"),
    "snapshot_chain": Path("src/meningites/validation/snapshot_chain.py"),
    "local_closeout": Path("pipelines/vnext_local_closeout.py"),
}

# llm_response não tem produtor local determinístico: é resposta externa do modelo
# e é validado em structured_response.py por require_schema(payload, "llm_response").
EXTERNAL_PRODUCERS = {"llm_response"}


def _schema_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not (
                isinstance(key, ast.Constant)
                and key.value == "schema_version"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                continue
            found.add(value.value)
    return found


def test_every_registry_contract_has_a_producer_or_explicit_external_owner():
    covered = set(PRODUCER_SOURCES) | EXTERNAL_PRODUCERS
    assert covered == set(SCHEMAS)


@pytest.mark.parametrize("contract_name", sorted(PRODUCER_SOURCES))
def test_local_producer_declares_registry_current_schema(contract_name: str):
    path = PRODUCER_SOURCES[contract_name]
    assert path.exists(), f"Produtor ausente para {contract_name}: {path}"

    declared = _schema_literals(path)
    current = SCHEMAS[contract_name].current

    assert current in declared, (
        f"{contract_name}: produtor {path} não declara schema atual {current}. "
        f"Encontrados: {sorted(declared)}"
    )


def test_external_llm_response_is_schema_gated():
    path = Path("src/meningites/agent/structured_response.py")
    text = path.read_text(encoding="utf-8")
    assert 'require_schema(payload, "llm_response")' in text
    assert SCHEMAS["llm_response"].current == "llm-response-vnext-2"
