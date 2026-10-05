import json
from pathlib import Path

from meningites.agent.http_api import (
    bearer_authorized,
    handle_query_payload,
    is_loopback_host,
    validate_api_bind,
)


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


def _pass_gate(root: Path):
    (root / "validacao_vnext.json").write_text(json.dumps({
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
        "checks": [],
    }), encoding="utf-8")


def test_http_handler_blocks_query_without_pass_gate(tmp_path: Path):
    _context(tmp_path / "agente_epidemiologico_contexto_vnext.json")
    result = handle_query_payload(
        {"question": "Situação estadual", "scope": "Mato Grosso"},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 503
    assert "Gate VNext" in result["error"]


def test_http_handler_returns_query_without_fastapi_dependency(tmp_path: Path):
    _context(tmp_path / "agente_epidemiologico_contexto_vnext.json")
    _pass_gate(tmp_path)
    result = handle_query_payload(
        {"question": "Situação estadual", "scope": "Mato Grosso"},
        outdir=tmp_path,
    )
    assert result["ok"] is True
    assert result["data"]["mode"] == "state"
    assert result["data"]["human_validation_required"] is True


def test_http_handler_rejects_string_false_for_use_llm(tmp_path: Path):
    result = handle_query_payload(
        {"question": "Situação estadual", "use_llm": "false"},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 400
    assert "booleano" in result["error"]


def test_http_handler_rejects_non_text_question(tmp_path: Path):
    result = handle_query_payload(
        {"question": 123},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 400


def test_http_handler_rejects_question_above_limit(tmp_path: Path):
    result = handle_query_payload(
        {"question": "x" * 4001},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 400
    assert "4000" in result["error"]


def test_api_bind_allows_loopback_without_token():
    validate_api_bind("127.0.0.1", "")
    validate_api_bind("localhost", None)
    assert is_loopback_host("::1") is True


def test_api_bind_rejects_external_host_without_token():
    try:
        validate_api_bind("0.0.0.0", "")
        assert False, "deveria bloquear bind externo sem token"
    except ValueError as exc:
        assert "MENINGITES_API_TOKEN" in str(exc)


def test_api_bind_allows_external_host_with_token():
    validate_api_bind("0.0.0.0", "segredo")


def test_bearer_authorization_is_strict():
    assert bearer_authorized(None, None) is True
    assert bearer_authorized("Bearer segredo", "segredo") is True
    assert bearer_authorized("Bearer errado", "segredo") is False
    assert bearer_authorized("segredo", "segredo") is False


def test_http_handler_blocks_forged_pass_without_validation_schema(tmp_path: Path):
    _context(tmp_path / "agente_epidemiologico_contexto_vnext.json")
    (tmp_path / "validacao_vnext.json").write_text(json.dumps({
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
        "checks": [],
    }), encoding="utf-8")

    result = handle_query_payload(
        {"question": "Situação estadual", "scope": "Mato Grosso"},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 503


def test_http_handler_blocks_inconsistent_pass_even_with_valid_schema(tmp_path: Path):
    _context(tmp_path / "agente_epidemiologico_contexto_vnext.json")
    (tmp_path / "validacao_vnext.json").write_text(json.dumps({
        "schema_version": "vnext-validation-1",
        "overall_status": "pass",
        "fail_n": 0,
        "attention_n": 0,
        "checks": [
            {"check_id": "x", "status": "fail", "detail": "falha escondida"},
        ],
    }), encoding="utf-8")

    result = handle_query_payload(
        {"question": "Situação estadual", "scope": "Mato Grosso"},
        outdir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status_code"] == 503
