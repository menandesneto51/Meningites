import json
from pathlib import Path

from meningites.validation.release_readiness import build_release_readiness


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def test_release_readiness_blocked_without_local_evidence(tmp_path: Path):
    report = build_release_readiness(
        tmp_path,
        ci_status="success",
        ci_run="95",
        commit_sha="abc",
    )
    assert report["ready_for_merge_review"] is False
    assert any(x["id"] == "validation" for x in report["blockers"])


def test_release_readiness_ready_when_all_requirements_exist(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"schema_version": "vnext-validation-1", "overall_status": "pass"})
    _write(tmp_path, "preflight_vnext.json", {"schema_version": "vnext-preflight-1", "status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"schema_version": "vnext-validation-evidence-1", "validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"schema_version": "vnext-visual-review-1", "approved": True, "reviewer": "Menandes"})
    _write(tmp_path, "prontidao_vnext.json", {"schema_version": "vnext-readiness-1", "ready": True, "status": "ready"})
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        }
    })

    report = build_release_readiness(
        tmp_path,
        ci_status="success",
        ci_run="95",
        commit_sha="abc",
    )
    assert report["ready_for_merge_review"] is True
    assert report["status"] == "ready_for_merge_review"


def test_release_readiness_stays_blocked_if_ci_fails(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"schema_version": "vnext-validation-1", "overall_status": "pass"})
    _write(tmp_path, "preflight_vnext.json", {"schema_version": "vnext-preflight-1", "status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"schema_version": "vnext-validation-evidence-1", "validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"schema_version": "vnext-visual-review-1", "approved": True, "reviewer": "Menandes"})
    _write(tmp_path, "prontidao_vnext.json", {"schema_version": "vnext-readiness-1", "ready": True, "status": "ready"})

    report = build_release_readiness(tmp_path, ci_status="failure")
    assert report["ready_for_merge_review"] is False
    assert any(x["id"] == "ci" for x in report["blockers"])


def test_release_readiness_blocks_on_data_quality_divergence(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    _write(tmp_path, "preflight_vnext.json", {"status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"approved": True, "reviewer": "Menandes"})
    _write(tmp_path, "prontidao_vnext.json", {"ready": True, "status": "ready"})
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 2,
            "has_blocking_divergences": True,
        }
    })

    report = build_release_readiness(tmp_path, ci_status="success")
    assert report["ready_for_merge_review"] is False
    assert any(x["id"] == "data_quality" for x in report["blockers"])


def test_release_readiness_blocks_on_incompatible_readiness_schema(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"schema_version": "vnext-validation-1", "overall_status": "pass"})
    _write(tmp_path, "preflight_vnext.json", {"schema_version": "vnext-preflight-1", "status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "validation_status": "pass",
        "artifact_count": 6,
    })
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "approved": True,
        "reviewer": "Menandes",
    })
    _write(tmp_path, "prontidao_vnext.json", {
        "schema_version": "vnext-readiness-99",
        "ready": True,
        "status": "ready",
    })
    _write(tmp_path, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "has_blocking_divergences": False,
        },
    })
    report = build_release_readiness(tmp_path, ci_status="success")
    assert report["ready_for_merge_review"] is False
    assert any(x["id"] == "readiness" for x in report["blockers"])
