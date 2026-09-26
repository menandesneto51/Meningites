import json
from pathlib import Path

from meningites.agent.operational_agent import EpidemiologicalAgent
from meningites.agent.publisher import publish_agent_outputs


def _context():
    return {
        "schema_version": "agent-context-vnext-1",
        "guardrails": {
            "may_create_clinical_rules": False,
        },
        "state_summary": [{
            "municipios_com_contexto_n": 2,
            "municipios_com_sinal_n": 1,
            "sinais_n": 2,
            "sinais_alta_ou_critica_n": 1,
        }],
        "regional_summary": [{
            "regional": "Baixada Cuiabana",
            "municipios_com_sinal_n": 1,
            "sinais_n": 2,
            "sinais_alta_ou_critica_n": 1,
            "fila_cievs_n": 2,
            "gal_tipagem_pendente_n": 1,
            "sih_sem_sinan_n": 1,
            "redcap_sem_sinan_n": 0,
        }],
        "municipalities": [{
            "codigo_municipio": "5103403",
            "municipio": "Cuiabá",
            "facts": {"fontes": "fonte.csv"},
            "signals": [{
                "titulo": "Pendência",
                "prioridade": "alta",
                "rule_id": "teste",
                "valor": 1,
                "fontes": "fonte.csv",
            }],
            "indicators": [{"indicador": "x"}],
        }],
    }


def test_agent_generates_deterministic_state_and_municipal_outputs():
    agent = EpidemiologicalAgent(_context())
    state = agent.state_briefing()
    municipal = agent.municipality_explanation("5103403")

    assert "2 municípios com contexto" in state.text
    assert "regra teste" in municipal.text
    assert municipal.evidence


def test_agent_refuses_context_that_allows_clinical_rule_creation():
    ctx = _context()
    ctx["guardrails"]["may_create_clinical_rules"] = True
    try:
        EpidemiologicalAgent(ctx)
        assert False, "deveria falhar"
    except ValueError as exc:
        assert "may_create_clinical_rules" in str(exc)


def test_agent_publisher_writes_auditable_outputs(tmp_path: Path):
    context_path = tmp_path / "ctx.json"
    context_path.write_text(json.dumps(_context(), ensure_ascii=False), encoding="utf-8")
    paths = publish_agent_outputs(tmp_path, context_path)

    assert all(path.exists() for path in paths.values())
    briefing = paths["state_briefing"].read_text(encoding="utf-8")
    assert "Briefing Epidemiológico Estadual" in briefing
    assert "não cria definição de caso" in briefing
