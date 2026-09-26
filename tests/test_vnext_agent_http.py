import json
from pathlib import Path

from meningites.agent.http_api import handle_query_payload


def _context(path: Path):
    path.write_text(json.dumps({
        "schema_version": "agent-context-vnext-1",
        "guardrails": {"may_create_clinical_rules": False},
        "state_summary": [{
            "municipios_com_contexto_n": 1,
            "municipios_com_sinal_n": 0,
            "sinais_n": 0,
            "sinais_alta_ou_critica_n": 0,
        }],
        "regional_summary": [],
        "municipalities": [],
    }), encoding="utf-8")


def test_http_handler_requires_question(tmp_path: Path):
    result = handle_query_payload({}, outdir=tmp_path)
    assert result["ok"] is False
    assert result["status_code"] == 400


def test_http_handler_requires_published_context(tmp_path: Path):
    result = handle_query_payload({"question": "Situação estadual"}, outdir=tmp_path)
    assert result["ok"] is False
    assert result["status_code"] == 503


def test_http_handler_returns_query_without_fastapi_dependency(tmp_path: Path):
    _context(tmp_path / "agente_epidemiologico_contexto_vnext.json")
    result = handle_query_payload(
        {"question": "Situação estadual", "scope": "Mato Grosso"},
        outdir=tmp_path,
    )
    assert result["ok"] is True
    assert result["data"]["mode"] == "state"
    assert result["data"]["human_validation_required"] is True
