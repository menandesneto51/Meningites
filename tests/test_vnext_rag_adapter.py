import json
from pathlib import Path

import pandas as pd

from meningites.agent.operational_agent import EpidemiologicalAgent
from meningites.agent.rag_adapter import NormativeRetriever, build_grounded_request, render_prompt
from meningites.agent.rag_publisher import publish_rag_packages


def _context():
    return {
        "schema_version": "agent-context-vnext-1",
        "guardrails": {
            "may_create_clinical_rules": False,
            "may_infer_missing_numerators": False,
            "may_treat_vaccine_doses_as_coverage": False,
            "must_cite_source_and_rule_for_operational_claim": True,
            "must_distinguish_fact_from_interpretation": True,
            "must_surface_missing_or_divergent_data": True,
        },
        "state_summary": [{"sinais_n": 2}],
        "regional_summary": [],
        "municipalities": [],
    }


def _kb(path: Path):
    pd.DataFrame([
        {
            "id": "vigente",
            "titulo": "NT 154/2024",
            "fonte": "Ministério da Saúde",
            "texto": "Orientações para quimioprofilaxia e vigilância de doença meningocócica.",
            "vigente": True,
            "prioridade": 100,
            "arquivo": "vigentes/01_nt154.md",
            "tags": "quimioprofilaxia meningococica",
            "tema": "norma",
        },
        {
            "id": "revogada",
            "titulo": "NT 97/2024",
            "fonte": "Ministério da Saúde",
            "texto": "Documento histórico sobre quimioprofilaxia.",
            "vigente": False,
            "prioridade": 10,
            "arquivo": "historicos/00_nt97.md",
            "tags": "quimioprofilaxia",
            "tema": "historico",
        },
    ]).to_csv(path, index=False, encoding="utf-8-sig")


def test_retriever_excludes_revoked_documents_by_default(tmp_path: Path):
    kb = tmp_path / "kb.csv"
    _kb(kb)
    hits = NormativeRetriever.from_csv(kb).retrieve("quimioprofilaxia meningocócica")
    assert hits
    assert all(hit.valid for hit in hits)
    assert all("97" not in hit.title for hit in hits)


def test_grounded_request_separates_facts_and_normative_evidence(tmp_path: Path):
    kb = tmp_path / "kb.csv"
    _kb(kb)
    agent = EpidemiologicalAgent(_context())
    package = build_grounded_request(
        "quimioprofilaxia meningocócica",
        agent,
        NormativeRetriever.from_csv(kb),
    )
    assert package["canonical_facts"]["state_summary"][0]["sinais_n"] == 2
    assert package["normative_evidence"][0]["vigente"] is True
    assert package["response_contract"]["preserve_canonical_facts"] is True
    prompt = render_prompt(package)
    assert "Não recalcule indicadores" in prompt
    assert "A validação humana é obrigatória" in prompt


def test_rag_publisher_generates_packages_without_calling_llm(tmp_path: Path):
    context_path = tmp_path / "ctx.json"
    context_path.write_text(json.dumps(_context(), ensure_ascii=False), encoding="utf-8")
    kb_path = tmp_path / "kb.csv"
    _kb(kb_path)

    paths = publish_rag_packages(tmp_path, context_path, kb_path)
    assert all(path.exists() for path in paths.values())
    payload = json.loads(paths["rag_packages"].read_text(encoding="utf-8"))
    assert "estadual" in payload
