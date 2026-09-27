import importlib.util
import os
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
