import json
from pathlib import Path

import pandas as pd

from meningites.validation.evidence import CANONICAL_ARTIFACTS


def test_preflight_contract_names_canonical_artifacts():
    assert "validacao_vnext.json" in CANONICAL_ARTIFACTS
    assert "situacao_municipal_vnext.csv" in CANONICAL_ARTIFACTS
    assert "sinais_municipais_vnext.csv" in CANONICAL_ARTIFACTS


def test_preflight_file_is_machine_readable_contract(tmp_path: Path):
    payload = {
        "schema_version": "vnext-preflight-1",
        "status": "pass",
        "detail": "ok",
        "outdir": str(tmp_path),
        "steps": [{"step": "validation", "status": "pass"}],
        "human_review_required": True,
    }
    path = tmp_path / "preflight_vnext.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["status"] == "pass"
    assert loaded["human_review_required"] is True


def test_run_preflight_pass_captures_evidence(tmp_path: Path, monkeypatch):
    import importlib.util
    import sys

    script = Path("pipelines/vnext_preflight.py").resolve()
    spec = importlib.util.spec_from_file_location("vnext_preflight_test", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    out = tmp_path / "saida"

    monkeypatch.setattr(mod, "publish_municipal_vnext", lambda root: {"x": root / "x"})
    def fake_validation(root):
        root.mkdir(parents=True, exist_ok=True)
        p = root / "validacao_vnext.json"
        p.write_text(json.dumps({
            "overall_status": "pass",
            "fail_n": 0,
            "attention_n": 0,
            "checks": [],
        }), encoding="utf-8")
        return {"validation_json": p, "validation_md": root / "VALIDACAO_VNEXT.md"}
    monkeypatch.setattr(mod, "publish_validation_report", fake_validation)

    called = {"evidence": False}
    def fake_evidence(root, commit_sha=None):
        called["evidence"] = True
        j = root / "evidencia_validacao_vnext.json"
        m = root / "EVIDENCIA_VALIDACAO_VNEXT.md"
        j.write_text("{}", encoding="utf-8")
        m.write_text("ok", encoding="utf-8")
        return {"evidence_json": j, "evidence_md": m}
    monkeypatch.setattr(mod, "publish_validation_evidence", fake_evidence)

    result = mod.run_preflight(
        repo_root=tmp_path,
        outdir=out,
        commit_sha="abc123",
        skip_module12=True,
    )
    assert result["status"] == "pass"
    assert called["evidence"] is True
    assert (out / "preflight_vnext.json").exists()


def test_run_preflight_fail_does_not_capture_evidence(tmp_path: Path, monkeypatch):
    import importlib.util

    script = Path("pipelines/vnext_preflight.py").resolve()
    spec = importlib.util.spec_from_file_location("vnext_preflight_fail_test", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    out = tmp_path / "saida"
    monkeypatch.setattr(mod, "publish_municipal_vnext", lambda root: {})

    def fake_validation(root):
        root.mkdir(parents=True, exist_ok=True)
        p = root / "validacao_vnext.json"
        p.write_text(json.dumps({
            "overall_status": "fail",
            "fail_n": 1,
            "attention_n": 0,
            "checks": [],
        }), encoding="utf-8")
        return {"validation_json": p, "validation_md": root / "VALIDACAO_VNEXT.md"}

    monkeypatch.setattr(mod, "publish_validation_report", fake_validation)
    monkeypatch.setattr(
        mod,
        "publish_validation_evidence",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria capturar evidência")),
    )

    result = mod.run_preflight(
        repo_root=tmp_path,
        outdir=out,
        skip_module12=True,
    )
    assert result["status"] == "fail"
    assert "evidência não será capturada" in result["detail"]
