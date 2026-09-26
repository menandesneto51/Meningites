"""Contrato estruturado de contexto para o agente epidemiológico.

O agente recebe fatos publicados, sinais e referências. Não recebe autorização
para criar novas regras clínicas/epidemiológicas.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def build_agent_context(
    outdir: str | Path,
    situation: pd.DataFrame,
    signals: pd.DataFrame,
    indicators: pd.DataFrame,
    regional: pd.DataFrame,
    state: pd.DataFrame,
    *,
    generated_at: datetime,
) -> Path:
    root = Path(outdir)
    municipalities = []
    for _, row in situation.iterrows():
        code = str(row["codigo_municipio"])
        sig = signals[signals["codigo_municipio"].astype(str).eq(code)] if not signals.empty else pd.DataFrame()
        ind = indicators[indicators["codigo_municipio"].astype(str).eq(code)] if not indicators.empty else pd.DataFrame()

        municipalities.append({
            "codigo_municipio": code,
            "municipio": row.get("municipio"),
            "facts": {
                k: (None if pd.isna(v) else v)
                for k, v in row.to_dict().items()
                if k not in {"codigo_municipio", "municipio"}
            },
            "signals": sig.to_dict(orient="records"),
            "indicators": ind.to_dict(orient="records"),
        })

    payload = {
        "schema_version": "agent-context-vnext-1",
        "generated_at": generated_at.isoformat(),
        "guardrails": {
            "may_create_clinical_rules": False,
            "may_infer_missing_numerators": False,
            "may_treat_vaccine_doses_as_coverage": False,
            "must_cite_source_and_rule_for_operational_claim": True,
            "must_distinguish_fact_from_interpretation": True,
            "must_surface_missing_or_divergent_data": True,
        },
        "state_summary": state.to_dict(orient="records"),
        "regional_summary": regional.to_dict(orient="records"),
        "municipalities": municipalities,
        "allowed_tasks": [
            "resumir situação epidemiológica e operacional",
            "explicar sinais já existentes",
            "priorizar leitura de filas já classificadas pelo sistema",
            "apontar lacunas de dados e procedência",
            "gerar minuta de briefing baseada nos fatos publicados",
        ],
        "forbidden_tasks": [
            "inventar definição de caso, surto, tratamento ou profilaxia",
            "criar limiar epidemiológico sem fonte validada",
            "converter ausência de dado em zero",
            "substituir decisão sanitária humana",
        ],
    }
    path = root / "agente_epidemiologico_contexto_vnext.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
