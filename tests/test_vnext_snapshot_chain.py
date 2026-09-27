import json
from pathlib import Path

from meningites.validation.snapshot_chain import build_snapshot_chain, publish_snapshot_chain


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def _valid_snapshot(root: Path):
    _write(root, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "commit_sha": "abc",
        "captured_at": "2026-09-26T00:00:00+00:00",
        "validation_status": "pass",
        "artifacts": [{"arquivo": "x.csv", "sha256": "a" * 64, "bytes": 1}],
        "artifact_count": 1,
    })
    _write(root, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "commit_sha": "abc",
        "status": "pass",
    })
    _write(root, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "commit_sha": "abc",
        "approved": True,
        "reviewer": "Menandes",
    })
    _write(root, "prontidao_vnext.json", {
        "schema_version": "vnext-readiness-1",
        "snapshot_commit": "abc",
        "ready": True,
        "status": "ready",
    })


def test_snapshot_chain_is_valid_for_same_commit(tmp_path: Path):
    _valid_snapshot(tmp_path)
    chain = build_snapshot_chain(tmp_path)
    assert chain["custody_ok"] is True
    assert chain["snapshot_commit"] == "abc"


def test_snapshot_chain_blocks_mixed_commits(tmp_path: Path):
    _valid_snapshot(tmp_path)
    visual = json.loads((tmp_path / "REVISAO_VISUAL_VNEXT.json").read_text())
    visual["commit_sha"] = "def"
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", visual)
    chain = build_snapshot_chain(tmp_path)
    assert chain["custody_ok"] is False
    assert chain["snapshot_commit"] == ""


def test_publish_snapshot_chain_writes_outputs(tmp_path: Path):
    _valid_snapshot(tmp_path)
    paths = publish_snapshot_chain(tmp_path)
    assert paths["chain_json"].exists()
    assert paths["chain_md"].exists()
