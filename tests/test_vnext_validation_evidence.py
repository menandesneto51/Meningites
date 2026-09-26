import json
from pathlib import Path

from meningites.validation.evidence import capture_validation_evidence, publish_validation_evidence


def _write_pass(root: Path):
    (root / "validacao_vnext.json").write_text(json.dumps({
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
    }), encoding="utf-8")
    for name in [
        "situacao_municipal_vnext.csv",
        "sinais_municipais_vnext.csv",
        "indicadores_municipais_vnext.csv",
        "procedencia_situacao_vnext.json",
        "resumo_executivo_estadual_vnext.csv",
    ]:
        (root / name).write_text("x", encoding="utf-8")


def test_evidence_requires_pass(tmp_path: Path):
    (tmp_path / "validacao_vnext.json").write_text(json.dumps({
        "overall_status": "fail",
        "fail_n": 1,
        "attention_n": 0,
    }), encoding="utf-8")
    try:
        capture_validation_evidence(tmp_path)
        assert False, "deveria falhar"
    except ValueError as exc:
        assert "overall_status=pass" in str(exc)


def test_evidence_hashes_canonical_artifacts(tmp_path: Path):
    _write_pass(tmp_path)
    evidence = capture_validation_evidence(tmp_path, commit_sha="abc123")
    assert evidence["commit_sha"] == "abc123"
    assert evidence["artifact_count"] == 6
    assert all(len(item["sha256"]) == 64 for item in evidence["artifacts"])


def test_publish_evidence_writes_json_and_markdown(tmp_path: Path):
    _write_pass(tmp_path)
    paths = publish_validation_evidence(tmp_path, commit_sha="abc123")
    assert paths["evidence_json"].exists()
    assert paths["evidence_md"].exists()
    assert "abc123" in paths["evidence_md"].read_text(encoding="utf-8")
