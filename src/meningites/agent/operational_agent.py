"""Agente epidemiológico operacional VNext.

Opera exclusivamente sobre o contexto canônico já publicado. As respostas
determinísticas servem como baseline auditável e podem ser enriquecidas por
RAG/LLM em camada posterior, sem alterar os fatos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentResponse:
    task: str
    scope: str
    text: str
    evidence: tuple[dict[str, Any], ...]
    caveats: tuple[str, ...]


class EpidemiologicalAgent:
    def __init__(self, context: dict[str, Any]):
        self.context = context
        self._validate_context()

    @classmethod
    def from_file(cls, path: str | Path) -> "EpidemiologicalAgent":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def _validate_context(self) -> None:
        required = {"schema_version", "guardrails", "state_summary", "regional_summary", "municipalities"}
        missing = required.difference(self.context)
        if missing:
            raise ValueError(f"Contexto do agente incompleto: {sorted(missing)}")
        if self.context.get("guardrails", {}).get("may_create_clinical_rules") is not False:
            raise ValueError("Guardrail may_create_clinical_rules deve permanecer False.")

    def state_briefing(self) -> AgentResponse:
        summary = (self.context.get("state_summary") or [{}])[0]
        text = (
            "Mato Grosso — síntese operacional VNext: "
            f"{int(summary.get('municipios_com_contexto_n', 0) or 0)} municípios com contexto; "
            f"{int(summary.get('municipios_com_sinal_n', 0) or 0)} municípios com sinais; "
            f"{int(summary.get('sinais_n', 0) or 0)} sinais no total; "
            f"{int(summary.get('sinais_alta_ou_critica_n', 0) or 0)} sinais de prioridade alta/crítica. "
            "A síntese agrega sinais já classificados pelo sistema e não cria nova classificação epidemiológica."
        )
        return AgentResponse(
            task="state_briefing",
            scope="Mato Grosso",
            text=text,
            evidence=(summary,),
            caveats=self._default_caveats(),
        )

    def regional_briefing(self, regional: str) -> AgentResponse:
        row = next(
            (r for r in self.context.get("regional_summary", []) if str(r.get("regional", "")).casefold() == regional.casefold()),
            None,
        )
        if row is None:
            return AgentResponse(
                task="regional_briefing",
                scope=regional,
                text=f"Não há resumo regional VNext disponível para {regional}.",
                evidence=(),
                caveats=("Ausência de resumo não equivale a ausência de risco ou de eventos.",),
            )
        text = (
            f"{row.get('regional')} — {int(row.get('municipios_com_sinal_n', 0) or 0)} municípios com sinais; "
            f"{int(row.get('sinais_n', 0) or 0)} sinais; "
            f"{int(row.get('sinais_alta_ou_critica_n', 0) or 0)} de prioridade alta/crítica; "
            f"fila CIEVS={int(row.get('fila_cievs_n', 0) or 0)}, "
            f"GAL/tipagem={int(row.get('gal_tipagem_pendente_n', 0) or 0)}, "
            f"SIH sem SINAN={int(row.get('sih_sem_sinan_n', 0) or 0)}, "
            f"RedCap sem SINAN={int(row.get('redcap_sem_sinan_n', 0) or 0)}."
        )
        return AgentResponse(
            task="regional_briefing",
            scope=str(row.get("regional")),
            text=text,
            evidence=(row,),
            caveats=self._default_caveats(),
        )

    def municipality_explanation(self, municipality_code: str) -> AgentResponse:
        mun = next(
            (m for m in self.context.get("municipalities", []) if str(m.get("codigo_municipio")) == str(municipality_code)),
            None,
        )
        if mun is None:
            return AgentResponse(
                task="municipality_explanation",
                scope=str(municipality_code),
                text="Município não encontrado no contexto VNext publicado.",
                evidence=(),
                caveats=("Ausência no contexto não equivale a ausência de casos, sinais ou necessidade de investigação.",),
            )

        signals = mun.get("signals") or []
        indicators = mun.get("indicators") or []
        lines = [
            f"{mun.get('municipio') or municipality_code}: {len(signals)} sinal(is) VNext ativo(s)."
        ]
        for signal in signals:
            lines.append(
                f"- {signal.get('titulo')}: prioridade {signal.get('prioridade')}; "
                f"regra {signal.get('rule_id')}; valor={signal.get('valor')}; "
                f"fonte={signal.get('fontes')}."
            )
        if indicators:
            lines.append(f"Indicadores municipais publicados: {len(indicators)}.")
        else:
            lines.append("Indicadores municipais do módulo 12 não disponíveis neste contexto.")

        evidence = tuple(signals) + tuple(indicators[:8])
        return AgentResponse(
            task="municipality_explanation",
            scope=str(mun.get("municipio") or municipality_code),
            text="\n".join(lines),
            evidence=evidence,
            caveats=self._default_caveats(),
        )

    def data_gaps(self) -> AgentResponse:
        gaps = []
        for mun in self.context.get("municipalities", []):
            facts = mun.get("facts") or {}
            if not facts.get("fontes"):
                gaps.append({
                    "codigo_municipio": mun.get("codigo_municipio"),
                    "municipio": mun.get("municipio"),
                    "lacuna": "sem_fontes_listadas",
                })
            if not mun.get("indicators"):
                gaps.append({
                    "codigo_municipio": mun.get("codigo_municipio"),
                    "municipio": mun.get("municipio"),
                    "lacuna": "sem_indicadores_municipais",
                })
        return AgentResponse(
            task="data_gaps",
            scope="Mato Grosso",
            text=f"Foram identificadas {len(gaps)} lacunas explícitas no contexto publicado.",
            evidence=tuple(gaps),
            caveats=("A lista cobre apenas lacunas observáveis no contrato VNext atual.",),
        )

    def _default_caveats(self) -> tuple[str, ...]:
        return (
            "Confirmar dados-fonte antes de decisão operacional.",
            "O agente não cria definição de caso, surto, tratamento ou profilaxia.",
            "Interpretações normativas devem ser vinculadas ao corpus oficial vigente.",
        )
