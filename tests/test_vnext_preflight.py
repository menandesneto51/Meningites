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
