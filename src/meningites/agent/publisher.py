"""Exporta produtos determinísticos do agente epidemiológico VNext."""
from __future__ import annotations

import json
from pathlib import Path

from meningites.agent.operational_agent import EpidemiologicalAgent


def publish_agent_outputs(outdir: str | Path, context_path: str | Path) -> dict[str, Path]:
    root = Path(outdir)
    agent = EpidemiologicalAgent.from_file(context_path)

    state = agent.state_briefing()
    gaps = agent.data_gaps()

    regional = []
    for row in agent.context.get("regional_summary", []):
        regional.append(agent.regional_briefing(str(row.get("regional", ""))))

    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "state_briefing": root / "agente_briefing_estadual_vnext.md",
        "regional_briefings": root / "agente_briefings_regionais_vnext.json",
        "data_gaps": root / "agente_lacunas_dados_vnext.json",
    }

    state_lines = [
        "# Briefing Epidemiológico Estadual — Meningites VNext",
        "",
        state.text,
        "",
        "## Ressalvas",
        "",
        *[f"- {c}" for c in state.caveats],
    ]
    paths["state_briefing"].write_text("\n".join(state_lines), encoding="utf-8")
    paths["regional_briefings"].write_text(
        json.dumps([r.__dict__ for r in regional], ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    paths["data_gaps"].write_text(
        json.dumps(gaps.__dict__, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return paths
