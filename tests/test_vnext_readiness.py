import json
from pathlib import Path

from meningites.validation.readiness import build_readiness, publish_readiness


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def test_readiness_is_blocked_without_artifacts(tmp_path: Path):
    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert report["status"] == "blocked"


def test_readiness_requires_human_visual_review(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"schema_version": "vnext-validation-1", "overall_status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"schema_version": "vnext-validation-evidence-1", "validation_status": "pass", "artifact_count": 6, "commit_sha": "abc123"})
    _write(tmp_path, "preflight_vnext.json", {"schema_version": "vnext-preflight-1", "status": "pass", "commit_sha": "abc123"})

    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert any(c["id"] == "visual_review" and not c["ok"] for c in report["checks"])


def test_readiness_becomes_ready_only_with_all_requirements(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"schema_version": "vnext-validation-1", "overall_status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"schema_version": "vnext-validation-evidence-1", "validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "preflight_vnext.json", {"schema_version": "vnext-preflight-1", "status": "pass"})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"schema_version": "vnext-visual-review-1", "approved": True, "reviewer": "Menandes", "commit_sha": "abc123"})
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        }
    })

    report = build_readiness(tmp_path)
    assert report["ready"] is True
    assert report["status"] == "ready"


def test_publish_readiness_writes_json_and_markdown(tmp_path: Path):
    paths = publish_readiness(tmp_path)
    assert paths["readiness_json"].exists()
    assert paths["readiness_md"].exists()


def test_readiness_blocks_on_data_quality_divergence(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "preflight_vnext.json", {"status": "pass"})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"schema_version": "vnext-visual-review-1", "approved": True, "reviewer": "Menandes"})
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 1,
            "has_blocking_divergences": True,
        }
    })

    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert any(
        item["id"] == "data_quality" and item["ok"] is False
        for item in report["checks"]
    )


def test_readiness_blocks_on_incompatible_schema(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {
        "schema_version": "vnext-validation-99",
        "overall_status": "pass",
    })
    _write(tmp_path, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "validation_status": "pass",
        "artifact_count": 6,
        "commit_sha": "abc123",
    })
    _write(tmp_path, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "status": "pass",
        "commit_sha": "abc123",
    })
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "approved": True,
        "reviewer": "Menandes",
        "commit_sha": "abc123",
    })
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        },
    })
    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert any(x["id"] == "validation_pass" and x["ok"] is False for x in report["checks"])


def test_readiness_blocks_when_visual_review_is_from_other_commit(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
    })
    _write(tmp_path, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "validation_status": "pass",
        "artifact_count": 6,
        "commit_sha": "abc123",
    })
    _write(tmp_path, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "status": "pass",
        "commit_sha": "abc123",
    })
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "approved": True,
        "reviewer": "Menandes",
        "commit_sha": "def456",
    })
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        },
    })

    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert any(
        item["id"] == "snapshot_consistency" and item["ok"] is False
        for item in report["checks"]
    )
