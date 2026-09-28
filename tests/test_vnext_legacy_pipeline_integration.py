import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPT = Path("pipeline_meningites_v23_indicadores_ms.py").resolve()
_SPEC = importlib.util.spec_from_file_location("legacy_pipeline_vnext_test", _SCRIPT)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)


class _Proc:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def _patch_vnext_modules(monkeypatch, *, publish, validate):
    import meningites.operational_queue.publisher as publisher
    import meningites.validation.reconcile as reconcile

    monkeypatch.setattr(publisher, "publish_municipal_vnext", publish)
    monkeypatch.setattr(reconcile, "publish_validation_report", validate)
    monkeypatch.setitem(sys.modules, "meningites.operational_queue.publisher", publisher)
    monkeypatch.setitem(sys.modules, "meningites.validation.reconcile", reconcile)


def test_vnext_ops_gate_publishes_and_passes(monkeypatch, tmp_path):
    _MOD.EXECUCAO.clear()
    monkeypatch.setattr(_MOD, "ROOT", tmp_path)
    out = tmp_path / "saida_meningites_v17"
    out.mkdir()
    report_path = out / "validacao_vnext.json"
    report_path.write_text(
        '{"overall_status":"pass","fail_n":0}',
        encoding="utf-8",
    )

    calls = {"publish": 0, "validate": 0}

    def fake_publish(path):
        calls["publish"] += 1
        assert Path(path) == out

    def fake_validate(path):
        calls["validate"] += 1
        assert Path(path) == out
        return {"validation_json": report_path}

    _patch_vnext_modules(monkeypatch, publish=fake_publish, validate=fake_validate)
    _MOD.run_vnext_ops_gate()

    assert calls["publish"] == 1
    assert calls["validate"] == 1
    assert _MOD.EXECUCAO[-1]["script"] == "pipelines/vnext_ops_gate"
    assert _MOD.EXECUCAO[-1]["status"] == "ok"
    assert _MOD.EXECUCAO[-1]["obrigatorio"] is True


def test_vnext_ops_gate_is_fail_closed_on_fail(monkeypatch, tmp_path):
    _MOD.EXECUCAO.clear()
    monkeypatch.setattr(_MOD, "ROOT", tmp_path)
    out = tmp_path / "saida_meningites_v17"
    out.mkdir()
    report_path = out / "validacao_vnext.json"
    report_path.write_text(
        '{"overall_status":"fail","fail_n":1}',
        encoding="utf-8",
    )

    _patch_vnext_modules(
        monkeypatch,
        publish=lambda path: None,
        validate=lambda path: {"validation_json": report_path},
    )
    monkeypatch.setattr(
        _MOD,
        "_abortar",
        lambda code: (_ for _ in ()).throw(SystemExit(code)),
    )

    with pytest.raises(SystemExit) as exc:
        _MOD.run_vnext_ops_gate()

    assert exc.value.code == 2
    assert _MOD.EXECUCAO[-1]["status"] == "falhou"
    assert "overall_status=fail" in _MOD.EXECUCAO[-1]["erro"]


def test_vnext_pipeline_validation_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MENINGITES_VNEXT_PIPELINE_VALIDATE", raising=False)
    called = {"run": False}

    def fake_run(*args, **kwargs):
        called["run"] = True
        return _Proc(0)

    monkeypatch.setattr(_MOD.subprocess, "run", fake_run)
    _MOD.run_vnext_preflight()
    assert called["run"] is False


def test_vnext_pipeline_validation_uses_git_head_and_src_pythonpath(monkeypatch):
    monkeypatch.setenv("MENINGITES_VNEXT_PIPELINE_VALIDATE", "true")
    monkeypatch.setattr(_MOD, "_git_head", lambda: "abc123")
    _MOD.EXECUCAO.clear()

    captured = {}

    def fake_run(cmd, cwd=None, env=None, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        return _Proc(0)

    monkeypatch.setattr(_MOD.subprocess, "run", fake_run)

    _MOD.run_vnext_preflight()

    assert "--commit" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--commit") + 1] == "abc123"
    assert "--skip-module12" in captured["cmd"]
    assert str(_MOD.ROOT / "src") in captured["env"]["PYTHONPATH"]
    assert _MOD.EXECUCAO[-1]["script"] == "pipelines/vnext_preflight.py"
    assert _MOD.EXECUCAO[-1]["status"] == "ok"
    assert _MOD.EXECUCAO[-1]["obrigatorio"] is True


def test_vnext_pipeline_validation_is_fail_closed_when_enabled(monkeypatch):
    monkeypatch.setenv("MENINGITES_VNEXT_PIPELINE_VALIDATE", "1")
    monkeypatch.setattr(_MOD, "_git_head", lambda: "abc123")
    _MOD.EXECUCAO.clear()

    monkeypatch.setattr(
        _MOD.subprocess,
        "run",
        lambda *args, **kwargs: _Proc(2),
    )
    monkeypatch.setattr(
        _MOD,
        "_abortar",
        lambda code: (_ for _ in ()).throw(SystemExit(code)),
    )

    with pytest.raises(SystemExit) as exc:
        _MOD.run_vnext_preflight()

    assert exc.value.code == 2
    assert _MOD.EXECUCAO[-1]["script"] == "pipelines/vnext_preflight.py"
    assert _MOD.EXECUCAO[-1]["status"] == "falhou"
    assert _MOD.EXECUCAO[-1]["obrigatorio"] is True


def test_vnext_pipeline_validation_blocks_when_git_head_is_unavailable(monkeypatch):
    monkeypatch.setenv("MENINGITES_VNEXT_PIPELINE_VALIDATE", "yes")
    monkeypatch.setattr(_MOD, "_git_head", lambda: "")
    _MOD.EXECUCAO.clear()
    monkeypatch.setattr(
        _MOD,
        "_abortar",
        lambda code: (_ for _ in ()).throw(SystemExit(code)),
    )

    with pytest.raises(SystemExit) as exc:
        _MOD.run_vnext_preflight()

    assert exc.value.code == 2
    assert "HEAD Git" in _MOD.EXECUCAO[-1]["erro"]
