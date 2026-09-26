from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from meningites.operational_queue.executive import build_executive_views
from meningites.operational_queue.agent_context import build_agent_context


def _frames():
    situation = pd.DataFrame([
        {"codigo_municipio": "5103403", "municipio": "Cuiabá", "sih_sem_sinan_n": 2},
        {"codigo_municipio": "5108402", "municipio": "Várzea Grande", "sih_sem_sinan_n": 1},
    ])
    signals = pd.DataFrame([
        {"codigo_municipio": "5103403", "municipio": "Cuiabá", "prioridade": "alta", "rule_id": "sih-sem-sinan"},
        {"codigo_municipio": "5108402", "municipio": "Várzea Grande", "prioridade": "moderada", "rule_id": "fila-cievs-presente"},
    ])
    indicators = pd.DataFrame([
        {"codigo_municipio": "5103403", "regional": "Baixada Cuiabana", "indicador": "x"},
        {"codigo_municipio": "5108402", "regional": "Baixada Cuiabana", "indicador": "x"},
    ])
    return situation, signals, indicators


def test_executive_views_aggregate_without_creating_new_thresholds():
    situation, signals, indicators = _frames()
    regional, state = build_executive_views(situation, signals, indicators)

    assert len(regional) == 1
    assert regional.iloc[0]["municipios_com_sinal_n"] == 2
    assert regional.iloc[0]["sinais_alta_ou_critica_n"] == 1
    assert state.iloc[0]["sinais_n"] == 2


def test_agent_context_contains_guardrails_and_source_facts(tmp_path: Path):
    situation, signals, indicators = _frames()
    regional, state = build_executive_views(situation, signals, indicators)
    path = build_agent_context(
        tmp_path,
        situation,
        signals,
        indicators,
        regional,
        state,
        generated_at=datetime(2026, 9, 26, 22, 0, tzinfo=timezone.utc),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["guardrails"]["may_create_clinical_rules"] is False
    assert payload["guardrails"]["must_cite_source_and_rule_for_operational_claim"] is True
    assert len(payload["municipalities"]) == 2
    assert payload["municipalities"][0]["signals"]
