import importlib.util
import json
from pathlib import Path

import pytest


_SCRIPT = Path("pipelines/vnext_local_closeout.py").resolve()
_SPEC = importlib.util.spec_from_file_location("vnext_local_closeout_test", _SCRIPT)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)
finalize = _MOD.finalize
verify_local_snapshot = _MOD.verify_local_snapshot


def _write(root: Path, name: str, payload: dict):
    (root / name).write_text(json.dumps(payload), encoding="utf-8")


def _snapshot(root: Path, commit: str = "abc"):
    _write(root, "validacao_vnext.json", {
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
    })
    _write(root, "agente_epidemiologico_contexto_vnext.json", {
        "schema_version": "agent-context-vnext-1",
        "data_quality": {
            "blocking_divergences_n": 0,
            "missing_artifacts_n": 0,
            "has_blocking_divergences": False,
        },
    })
    _write(root, "preflight_vnext.json", {
        "schema_version": "vnext-preflight-1",
        "commit_sha": commit,
        "status": "pass",
    })
    _write(root, "evidencia_validacao_vnext.json", {
        "schema_version": "vnext-validation-evidence-1",
        "commit_sha": commit,
        "captured_at": "2026-09-26T00:00:00+00:00",
        "validation_status": "pass",
        "artifact_count": 1,
        "artifacts": [{
            "arquivo": "situacao_municipal_vnext.csv",
            "sha256": "a" * 64,
            "bytes": 100,
        }],
    })
    _write(root, "REVISAO_VISUAL_VNEXT.json", {
        "schema_version": "vnext-visual-review-1",
        "commit_sha": commit,
        "approved": True,
        "reviewer": "Menandes",
        "reviewed_at": "2026-09-26T00:10:00+00:00",
        "notes": "Revisado.",
    })


def test_finalize_publishes_complete_closeout(tmp_path: Path):
    _snapshot(tmp_path)
    result = finalize(
        outdir=tmp_path,
        commit_sha="abc",
        ci_status="success",
        ci_run="154",
    )
    assert result["ready"] is True
    assert result["snapshot_commit"] == "abc"
    assert result["human_merge_decision_required"] is True
    assert (tmp_path / "fechamento_local_vnext.json").exists()
    assert (tmp_path / "cadeia_custodia_vnext.json").exists()
    assert (tmp_path / "manifesto_operacional_vnext.json").exists()
    assert (tmp_path / "catalogo_schemas_vnext.json").exists()


def test_finalize_blocks_visual_review_from_other_commit(tmp_path: Path):
    _snapshot(tmp_path, commit="abc")
    visual = json.loads((tmp_path / "REVISAO_VISUAL_VNEXT.json").read_text(encoding="utf-8"))
    visual["commit_sha"] = "def"
    _write(tmp_path, "REVISAO_VISUAL_VNEXT.json", visual)

    with pytest.raises(ValueError, match="outro commit"):
        finalize(
            outdir=tmp_path,
            commit_sha="abc",
            ci_status="success",
            ci_run="154",
        )


def test_finalize_blocks_failed_ci(tmp_path: Path):
    _snapshot(tmp_path)
    with pytest.raises(ValueError, match="Release readiness bloqueado"):
        finalize(
            outdir=tmp_path,
            commit_sha="abc",
            ci_status="failure",
            ci_run="154",
        )


def test_verify_local_snapshot_accepts_matching_clean_head(monkeypatch, tmp_path: Path):
    calls = []

    def fake_git(repo_root, *args):
        calls.append(args)
        class Result:
            returncode = 0
            stdout = "abc\n" if args == ("rev-parse", "HEAD") else ""
        return Result()

    monkeypatch.setattr(_MOD, "_git", fake_git)
    result = verify_local_snapshot(tmp_path, "abc", require_clean=True)
    assert result["head_commit"] == "abc"
    assert result["tracked_worktree_clean"] is True
    assert ("status", "--porcelain", "--untracked-files=no") in calls


def test_verify_local_snapshot_blocks_head_mismatch(monkeypatch, tmp_path: Path):
    def fake_git(repo_root, *args):
        class Result:
            returncode = 0
            stdout = "def\n"
        return Result()

    monkeypatch.setattr(_MOD, "_git", fake_git)
    with pytest.raises(ValueError, match="difere do commit solicitado"):
        verify_local_snapshot(tmp_path, "abc", require_clean=True)


def test_verify_local_snapshot_blocks_dirty_tracked_tree(monkeypatch, tmp_path: Path):
    def fake_git(repo_root, *args):
        class Result:
            returncode = 0
            stdout = "abc\n" if args == ("rev-parse", "HEAD") else " M pipelines/vnext_local_closeout.py\n"
        return Result()

    monkeypatch.setattr(_MOD, "_git", fake_git)
    with pytest.raises(ValueError, match="alterações locais rastreadas"):
        verify_local_snapshot(tmp_path, "abc", require_clean=True)
