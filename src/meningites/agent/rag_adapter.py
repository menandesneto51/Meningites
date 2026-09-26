"""Adapter RAG do agente epidemiológico VNext.

Recupera trechos normativos já indexados e combina-os com fatos canônicos.
Não executa LLM por conta própria e não altera fatos publicados.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from meningites.agent.operational_agent import EpidemiologicalAgent


@dataclass(frozen=True)
class NormativeHit:
    id: str
    title: str
    source: str
    text: str
    valid: bool
    file: str
    score: float


def _strip(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    stop = {"de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com", "por", "um", "uma", "no", "na", "ao", "ou"}
    out = set()
    for token in _strip(text).split():
        if token in stop:
            continue
        if len(token) > 2 or token.isdigit():
            out.add(token)
    return out


class NormativeRetriever:
    def __init__(self, rows: Iterable[dict[str, Any]]):
        self.rows = tuple(rows)

    @classmethod
    def from_csv(cls, path: str | Path) -> "NormativeRetriever":
        p = Path(path)
        if not p.exists() or p.stat().st_size == 0:
            return cls(())
        frame = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
        return cls(frame.to_dict(orient="records"))

    def retrieve(self, query: str, top_k: int = 5, *, current_only: bool = True) -> list[NormativeHit]:
        q = _tokens(query)
        if not q:
            return []
        hits: list[NormativeHit] = []
        for row in self.rows:
            valid_raw = row.get("vigente", True)
            valid = (
                valid_raw.strip().lower() in {"1", "true", "sim", "yes"}
                if isinstance(valid_raw, str)
                else bool(valid_raw)
            )
            if current_only and not valid:
                continue
            title = str(row.get("titulo", ""))
            source = str(row.get("fonte", ""))
            text = str(row.get("texto", ""))
            tags = str(row.get("tags", ""))
            tema = str(row.get("tema", ""))
            blob = _tokens(" ".join([title, source, tags, tema, text]))
            if not blob:
                continue
            overlap = len(q & blob)
            if overlap == 0:
                continue
            coverage = overlap / max(1, len(q))
            priority = float(row.get("prioridade", 50) or 50)
            score = coverage + min(0.15, priority / 1000.0) + (0.1 if valid else 0)
            hits.append(
                NormativeHit(
                    id=str(row.get("id", "")),
                    title=title,
                    source=source,
                    text=text,
                    valid=valid,
                    file=str(row.get("arquivo", "")),
                    score=round(score, 4),
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]


def _select_operational_context(agent: EpidemiologicalAgent, scope: str | None) -> dict[str, Any]:
    if not scope or scope.casefold() in {"mt", "mato grosso", "estadual"}:
        return {"state_summary": agent.context.get("state_summary", [])}

    regional = [
        row for row in agent.context.get("regional_summary", [])
        if str(row.get("regional", "")).casefold() == scope.casefold()
    ]
    if regional:
        return {"regional_summary": regional}

    municipal = [
        row for row in agent.context.get("municipalities", [])
        if str(row.get("codigo_municipio", "")) == str(scope)
        or str(row.get("municipio", "")).casefold() == scope.casefold()
    ]
    if municipal:
        return {"municipalities": municipal}

    return {"context_missing_for_scope": scope}


def build_grounded_request(
    question: str,
    agent: EpidemiologicalAgent,
    retriever: NormativeRetriever,
    *,
    scope: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    facts = _select_operational_context(agent, scope)
    hits = retriever.retrieve(question, top_k=top_k, current_only=True)

    package = {
        "schema_version": "rag-request-vnext-1",
        "question": question,
        "scope": scope or "Mato Grosso",
        "guardrails": agent.context["guardrails"],
        "canonical_facts": facts,
        "normative_evidence": [
            {
                "id": h.id,
                "titulo": h.title,
                "fonte": h.source,
                "texto": h.text,
                "vigente": h.valid,
                "arquivo": h.file,
                "score": h.score,
            }
            for h in hits
        ],
        "response_contract": {
            "preserve_canonical_facts": True,
            "cite_normative_source_when_used": True,
            "state_when_normative_evidence_is_insufficient": True,
            "separate_fact_interpretation_recommendation": True,
            "human_validation_required": True,
        },
    }
    return package


def render_prompt(package: dict[str, Any]) -> str:
    return (
        "Você é o agente epidemiológico de meningites do CIEVS-MT.\n"
        "Use somente os fatos canônicos e as evidências normativas fornecidas abaixo.\n"
        "Não recalcule indicadores, não altere prioridades, não invente regras clínicas, "
        "não transforme ausência de dado em zero e não trate doses como cobertura sem denominador.\n"
        "Separe claramente: FATOS, INTERPRETAÇÃO, RECOMENDAÇÕES FUNDAMENTADAS e LIMITAÇÕES.\n"
        "Toda recomendação normativa deve citar a fonte correspondente.\n"
        "Se a evidência normativa for insuficiente, declare isso explicitamente.\n"
        "A validação humana é obrigatória.\n\n"
        + json.dumps(package, ensure_ascii=False, indent=2, default=str)
    )
