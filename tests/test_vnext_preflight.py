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
            "schema_version": "vnext-validation-1",
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
            "schema_version": "vnext-validation-1",
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


def test_run_preflight_rejects_incompatible_validation_schema(tmp_path: Path, monkeypatch):
    import importlib.util

    script = Path("pipelines/vnext_preflight.py").resolve()
    spec = importlib.util.spec_from_file_location("vnext_preflight_schema_test", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    out = tmp_path / "saida"
    monkeypatch.setattr(mod, "publish_municipal_vnext", lambda root: {})

    def fake_validation(root):
        root.mkdir(parents=True, exist_ok=True)
        p = root / "validacao_vnext.json"
        p.write_text(json.dumps({
            "schema_version": "vnext-validation-99",
            "overall_status": "pass",
            "fail_n": 0,
            "attention_n": 0,
            "checks": [],
        }), encoding="utf-8")
        return {"validation_json": p, "validation_md": root / "VALIDACAO_VNEXT.md"}

    monkeypatch.setattr(mod, "publish_validation_report", fake_validation)
    result = mod.run_preflight(repo_root=tmp_path, outdir=out, skip_module12=True)
    assert result["status"] == "fail"
    assert "Schema de validação incompatível" in result["detail"]


def _load_preflight_module(name: str):
    import importlib.util

    script = Path("pipelines/vnext_preflight.py").resolve()
    spec = importlib.util.spec_from_file_location(name, script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_run_preflight_persists_failure_when_publisher_raises(tmp_path: Path, monkeypatch):
    mod = _load_preflight_module("vnext_preflight_publisher_error_test")
    out = tmp_path / "saida"

    monkeypatch.setattr(
        mod,
        "publish_municipal_vnext",
        lambda root: (_ for _ in ()).throw(RuntimeError("publisher boom")),
    )

    result = mod.run_preflight(
        repo_root=tmp_path,
        outdir=out,
        commit_sha="abc",
        skip_module12=True,
    )
    assert result["status"] == "fail"
    assert result["steps"][-1]["step"] == "publisher"
    assert result["steps"][-1]["error_type"] == "RuntimeError"
    persisted = json.loads((out / "preflight_vnext.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "fail"


def test_run_preflight_persists_failure_when_validation_raises(tmp_path: Path, monkeypatch):
    mod = _load_preflight_module("vnext_preflight_validation_error_test")
    out = tmp_path / "saida"

    monkeypatch.setattr(mod, "publish_municipal_vnext", lambda root: {})
    monkeypatch.setattr(
        mod,
        "publish_validation_report",
        lambda root: (_ for _ in ()).throw(ValueError("validation boom")),
    )

    result = mod.run_preflight(
        repo_root=tmp_path,
        outdir=out,
        commit_sha="abc",
        skip_module12=True,
    )
    assert result["status"] == "fail"
    assert result["steps"][-1]["step"] == "validation"
    assert result["steps"][-1]["error_type"] == "ValueError"
    assert (out / "preflight_vnext.json").exists()


def test_run_preflight_persists_failure_when_evidence_raises(tmp_path: Path, monkeypatch):
    mod = _load_preflight_module("vnext_preflight_evidence_error_test")
    out = tmp_path / "saida"

    monkeypatch.setattr(mod, "publish_municipal_vnext", lambda root: {})

    def fake_validation(root):
        root.mkdir(parents=True, exist_ok=True)
        p = root / "validacao_vnext.json"
        p.write_text(json.dumps({
            "schema_version": "vnext-validation-1",
            "overall_status": "pass",
            "fail_n": 0,
            "attention_n": 0,
            "checks": [],
        }), encoding="utf-8")
        return {"validation_json": p, "validation_md": root / "VALIDACAO_VNEXT.md"}

    monkeypatch.setattr(mod, "publish_validation_report", fake_validation)
    monkeypatch.setattr(
        mod,
        "publish_validation_evidence",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("evidence boom")),
    )

    result = mod.run_preflight(
        repo_root=tmp_path,
        outdir=out,
        commit_sha="abc",
        skip_module12=True,
    )
    assert result["status"] == "fail"
    assert result["steps"][-1]["step"] == "evidence"
    assert result["steps"][-1]["error_type"] == "OSError"
    persisted = json.loads((out / "preflight_vnext.json").read_text(encoding="utf-8"))
    assert persisted["detail"].startswith("Captura de evidência falhou")
