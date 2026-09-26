import json
from pathlib import Path

from meningites.validation.operational_manifest import build_operational_manifest, publish_operational_manifest


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def test_manifest_blocks_llm_without_context(tmp_path: Path):
    manifest = build_operational_manifest(tmp_path)
    assert manifest["execution_policy"]["llm_allowed"] is False


def test_manifest_allows_llm_only_with_pass_and_safe_quality(tmp_path: Path):
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "missing_artifacts_n": 0,
            "has_blocking_divergences": False,
        },
    })
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    manifest = build_operational_manifest(tmp_path)
    assert manifest["execution_policy"]["llm_allowed"] is True
    assert manifest["normative_policy"]["unknown_vigency_is_current"] is False


def test_manifest_blocks_llm_on_data_quality(tmp_path: Path):
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 1,
            "missing_artifacts_n": 0,
            "has_blocking_divergences": True,
        },
    })
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    manifest = build_operational_manifest(tmp_path)
    assert manifest["execution_policy"]["llm_allowed"] is False


def test_publish_manifest_writes_json_and_markdown(tmp_path: Path):
    paths = publish_operational_manifest(tmp_path)
    assert paths["manifest_json"].exists()
    assert paths["manifest_md"].exists()
