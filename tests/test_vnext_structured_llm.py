from meningites.agent.llm_runner import run_validated_llm
from meningites.agent.structured_response import (
    parse_structured_response,
    validate_structured_llm_response,
)


class FakeClient:
    def __init__(self, text):
        self.text = text
    def complete(self, prompt):
        return {"status": "ok", "provider": "fake", "model": "fake", "text": self.text, "error": ""}


def _package():
    return {
        "canonical_facts": {
            "state_summary": [{"sinais_n": 2, "municipios_com_sinal_n": 1}]
        },
        "normative_evidence": [{
            "id": "nt154",
            "fonte": "Ministério da Saúde",
            "titulo": "NT 154/2024",
            "texto": "Orientação normativa vigente.",
        }],
    }


def _response():
    return """{
  "schema_version": "llm-response-vnext-2",
  "facts": [
    {"text": "Há sinais operacionais publicados.", "fact_refs": ["state_summary.0.sinais_n"]}
  ],
  "interpretations": [
    {"text": "Há pendência operacional que exige revisão.", "fact_refs": ["state_summary.0.sinais_n"]}
  ],
  "recommendations": [
    {
      "text": "Revisar a pendência conforme a evidência normativa disponível.",
      "fact_refs": ["state_summary.0.sinais_n"],
      "normative_evidence_ids": ["nt154"]
    }
  ],
  "limitations": ["Revisão humana obrigatória."],
  "human_validation_required": true
}"""


def test_structured_response_is_parsed_and_accepted():
    parsed = parse_structured_response(_response())
    assert parsed is not None
    result = validate_structured_llm_response(_package(), _response())
    assert result.accepted is True
    assert result.requires_human_review is True


def test_structured_response_rejects_unknown_fact_ref():
    text = _response().replace("state_summary.0.sinais_n", "state_summary.0.inexistente")
    result = validate_structured_llm_response(_package(), text)
    assert result.accepted is False
    assert any("fact_ref_desconhecido" in issue for issue in result.issues)


def test_structured_response_rejects_unknown_normative_id():
    text = _response().replace("nt154", "inventado")
    result = validate_structured_llm_response(_package(), text)
    assert result.accepted is False
    assert any("normative_id_desconhecido" in issue for issue in result.issues)


def test_runner_prefers_structured_v2():
    result = run_validated_llm(
        _package(),
        "prompt",
        client=FakeClient(_response()),
    )
    assert result["accepted"] is True
    assert result["response_format"] == "structured_v2"
    assert result["structured_response"]["schema_version"] == "llm-response-vnext-2"


def test_runner_keeps_legacy_fallback():
    legacy = """FATOS
Há 2 sinais em 1 município.

INTERPRETAÇÃO
Os dados indicam pendências operacionais.

RECOMENDAÇÕES FUNDAMENTADAS
Conforme Ministério da Saúde, revisar a orientação normativa vigente.

LIMITAÇÕES
A validação humana é obrigatória.
"""
    result = run_validated_llm(
        _package(),
        "prompt",
        client=FakeClient(legacy),
    )
    assert result["response_format"] == "legacy_text"
    assert result["accepted"] is True
