import json
from pathlib import Path

from meningites.validation.readiness import publish_readiness
from meningites.validation.release_readiness import publish_release_readiness
from meningites.validation.snapshot_chain import publish_snapshot_chain


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def test_end_to_end_snapshot_flow(tmp_path: Path):
    commit = "abc123"
    _write(tmp_path, "validacao_vnext.json", {
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
    })
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "missing_artifacts_n": 0,
            "has_blocking_divergences": False,
        },
    })
    _write(tmp_path, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "commit_sha": commit,
        "status": "pass",
    })
    _write(tmp_path, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "commit_sha": commit,
        "captured_at": "2026-09-26T00:00:00+00:00",
        "validation_status": "pass",
        "artifact_count": 1,
        "artifacts": [{
            "arquivo": "situacao_municipal_vnext.csv",
            "sha256": "a" * 64,
            "bytes": 100,
        }],
    })
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "commit_sha": commit,
        "approved": True,
        "reviewer": "Menandes",
        "reviewed_at": "2026-09-26T00:10:00+00:00",
        "notes": "Revisado.",
    })

    readiness_paths = publish_readiness(tmp_path)
    readiness = json.loads(readiness_paths["readiness_json"].read_text(encoding="utf-8"))
    assert readiness["ready"] is True
    assert readiness["snapshot_commit"] == commit

    release_paths = publish_release_readiness(
        tmp_path,
        ci_status="success",
        ci_run="151",
        commit_sha=commit,
    )
    release = json.loads(release_paths["release_readiness_json"].read_text(encoding="utf-8"))
    assert release["ready_for_merge_review"] is True

    chain_paths = publish_snapshot_chain(tmp_path)
    chain = json.loads(chain_paths["chain_json"].read_text(encoding="utf-8"))
    assert chain["custody_ok"] is True
    assert chain["snapshot_commit"] == commit
    assert chain["release_readiness"]["ready_for_merge_review"] is True


def test_end_to_end_snapshot_flow_blocks_mixed_review_commit(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
    })
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        },
    })
    _write(tmp_path, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "commit_sha": "abc",
        "status": "pass",
    })
    _write(tmp_path, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "commit_sha": "abc",
        "validation_status": "pass",
        "artifact_count": 1,
        "artifacts": [{"arquivo": "x", "sha256": "b" * 64, "bytes": 1}],
    })
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "commit_sha": "def",
        "approved": True,
        "reviewer": "Menandes",
    })

    readiness = json.loads(publish_readiness(tmp_path)["readiness_json"].read_text(encoding="utf-8"))
    assert readiness["ready"] is False
    assert readiness["snapshot_commit"] == ""
