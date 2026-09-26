import json
from pathlib import Path

from meningites.validation.health import load_validation_health, important_checks


def test_health_is_blocking_before_validation(tmp_path: Path):
    health = load_validation_health(tmp_path)
    assert health["overall_status"] == "not_validated"
    assert health["blocking"] is True


def test_health_reads_pass_report(tmp_path: Path):
    (tmp_path / "validacao_vnext.json").write_text(json.dumps({
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
        "checks": [{"check_id": "x", "status": "pass", "detail": "ok"}],
    }), encoding="utf-8")

    health = load_validation_health(tmp_path)
    assert health["overall_status"] == "pass"
    assert health["blocking"] is False
    assert health["fail_n"] == 0


def test_health_reads_fail_report_and_prioritizes_failures(tmp_path: Path):
    (tmp_path / "validacao_vnext.json").write_text(json.dumps({
        "overall_status": "fail",
        "fail_n": 1,
        "attention_n": 1,
        "checks": [
            {"check_id": "ok", "status": "pass", "detail": "ok"},
            {"check_id": "warn", "status": "attention", "detail": "atenção"},
            {"check_id": "bad", "status": "fail", "detail": "falha"},
        ],
    }), encoding="utf-8")

    health = load_validation_health(tmp_path)
    checks = important_checks(health)
    assert health["blocking"] is True
    assert checks[0]["check_id"] == "bad"


def test_health_handles_invalid_json(tmp_path: Path):
    (tmp_path / "validacao_vnext.json").write_text("{invalid", encoding="utf-8")
    health = load_validation_health(tmp_path)
    assert health["overall_status"] == "invalid_report"
    assert health["blocking"] is True
