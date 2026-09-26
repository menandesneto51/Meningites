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
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "preflight_vnext.json", {"status": "pass"})

    report = build_readiness(tmp_path)
    assert report["ready"] is False
    assert any(c["id"] == "visual_review" and not c["ok"] for c in report["checks"])


def test_readiness_becomes_ready_only_with_all_requirements(tmp_path: Path):
    _write(tmp_path, "validacao_vnext.json", {"overall_status": "pass"})
    _write(tmp_path, "evidencia_validacao_vnext.json", {"validation_status": "pass", "artifact_count": 6})
    _write(tmp_path, "preflight_vnext.json", {"status": "pass"})
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", {"approved": True, "reviewer": "Menandes"})

    report = build_readiness(tmp_path)
    assert report["ready"] is True
    assert report["status"] == "ready"


def test_publish_readiness_writes_json_and_markdown(tmp_path: Path):
    paths = publish_readiness(tmp_path)
    assert paths["readiness_json"].exists()
    assert paths["readiness_md"].exists()
