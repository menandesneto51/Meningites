import json
from pathlib import Path

import pandas as pd

from meningites.agent.query_service import query_agent, save_query_result


def _write_context(path: Path):
    path.write_text(json.dumps({
        "schema_version": "agent-context-vnext-1",
        "guardrails": {
            "may_create_clinical_rules": False,
            "may_infer_missing_numerators": False,
            "may_treat_vaccine_doses_as_coverage": False,
            "must_cite_source_and_rule_for_operational_claim": True,
            "must_distinguish_fact_from_interpretation": True,
            "must_surface_missing_or_divergent_data": True,
        },
        "state_summary": [{
            "municipios_com_contexto_n": 2,
            "municipios_com_sinal_n": 1,
            "sinais_n": 1,
            "sinais_alta_ou_critica_n": 1,
        }],
        "regional_summary": [{
            "regional": "Baixada Cuiabana",
            "municipios_com_sinal_n": 1,
            "sinais_n": 1,
            "sinais_alta_ou_critica_n": 1,
            "fila_cievs_n": 1,
            "gal_tipagem_pendente_n": 0,
            "sih_sem_sinan_n": 1,
            "redcap_sem_sinan_n": 0,
        }],
        "municipalities": [{
            "codigo_municipio": "5103403",
            "municipio": "Cuiabá",
            "facts": {"fontes": "fonte.csv"},
            "signals": [{
                "titulo": "Pendência SIH",
                "prioridade": "alta",
                "rule_id": "sih-sem-sinan",
                "valor": 1,
                "fontes": "sih.csv",
            }],
            "indicators": [],
        }],
    }, ensure_ascii=False), encoding="utf-8")


def _write_kb(path: Path):
    pd.DataFrame([{
        "id": "nt154",
        "titulo": "NT 154/2024",
        "fonte": "Ministério da Saúde",
        "texto": "Orientações para vigilância de meningites.",
        "vigente": True,
        "prioridade": 100,
        "arquivo": "vigentes/01_nt154.md",
        "tags": "vigilancia meningites",
        "tema": "norma",
    }]).to_csv(path, index=False, encoding="utf-8-sig")


def test_auto_mode_resolves_municipality_by_name(tmp_path: Path):
    ctx = tmp_path / "ctx.json"
    kb = tmp_path / "kb.csv"
    _write_context(ctx)
    _write_kb(kb)

    result = query_agent(
        context_path=ctx,
        kb_path=kb,
        question="Qual a situação de Cuiabá?",
        scope="Cuiabá",
        mode="auto",
        use_llm=False,
    )

    assert result["mode"] == "municipality"
    assert result["deterministic"]["scope"] == "Cuiabá"
    assert "sih-sem-sinan" in result["deterministic"]["text"]
    assert result["llm"]["executed"] is False


def test_auto_mode_resolves_regional(tmp_path: Path):
    ctx = tmp_path / "ctx.json"
    kb = tmp_path / "kb.csv"
    _write_context(ctx)
    _write_kb(kb)

    result = query_agent(
        context_path=ctx,
        kb_path=kb,
        question="Quais as pendências?",
        scope="Baixada Cuiabana",
    )

    assert result["mode"] == "regional"
    assert result["deterministic"]["scope"] == "Baixada Cuiabana"


def test_query_can_be_saved_without_llm(tmp_path: Path):
    ctx = tmp_path / "ctx.json"
    kb = tmp_path / "kb.csv"
    _write_context(ctx)
    _write_kb(kb)

    result = query_agent(
        context_path=ctx,
        kb_path=kb,
        question="Situação estadual",
        scope="Mato Grosso",
    )
    path = save_query_result(result, tmp_path / "consulta.json")

    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["human_validation_required"] is True
