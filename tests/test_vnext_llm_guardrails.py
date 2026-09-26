from meningites.agent.llm_client import LLMConfig, OptionalLLMClient
from meningites.agent.response_validator import validate_llm_response
from meningites.agent.llm_runner import run_validated_llm


class FakeClient:
    def __init__(self, text):
        self.text = text
    def complete(self, prompt):
        return {"status": "ok", "provider": "fake", "model": "fake", "text": self.text, "error": ""}


def _package():
    return {
        "canonical_facts": {"state_summary": [{"sinais_n": 2, "municipios_com_sinal_n": 1}]},
        "normative_evidence": [{
            "fonte": "Ministério da Saúde",
            "titulo": "NT 154/2024",
            "texto": "Orientação normativa vigente.",
        }],
    }


def test_validator_accepts_grounded_structured_response():
    text = """FATOS
Há 2 sinais em 1 município.

INTERPRETAÇÃO
Os dados indicam pendências operacionais.

RECOMENDAÇÕES FUNDAMENTADAS
Conforme Ministério da Saúde, revisar a orientação normativa vigente.

LIMITAÇÕES
A validação humana é obrigatória.
"""
    result = validate_llm_response(_package(), text)
    assert result.accepted is True
    assert result.requires_human_review is True


def test_validator_rejects_untracked_number():
    text = """FATOS
Há 2 sinais.

INTERPRETAÇÃO
Atenção.

RECOMENDAÇÕES
Ministério da Saúde: revisar.

LIMITAÇÕES
Há 99 casos adicionais.
"""
    result = validate_llm_response(_package(), text)
    assert result.accepted is False
    assert any(issue.startswith("numeros_nao_rastreados") for issue in result.issues)


def test_runner_rejects_bad_llm_output():
    response = run_validated_llm(
        _package(),
        "prompt",
        client=FakeClient("Resposta sem seções e com 77 casos."),
    )
    assert response["status"] == "rejected"
    assert response["accepted"] is False


def test_optional_client_is_safe_when_no_credentials():
    cfg = LLMConfig(api_key="", url="https://example.invalid", model="x", provider="fake", available=False)
    result = OptionalLLMClient(cfg).complete("x")
    assert result["status"] == "unavailable"
