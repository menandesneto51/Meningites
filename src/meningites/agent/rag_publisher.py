"""Publicação de pacotes RAG prontos para uso pelo agente/LLM."""
from __future__ import annotations

import json
from pathlib import Path

from meningites.agent.operational_agent import EpidemiologicalAgent
from meningites.agent.rag_adapter import NormativeRetriever, build_grounded_request, render_prompt


DEFAULT_QUESTIONS = (
    ("estadual", "Quais são os principais sinais operacionais e lacunas que exigem revisão no estado?"),
    ("normativa", "Quais orientações normativas vigentes são pertinentes às pendências de investigação, laboratório e quimioprofilaxia?"),
)


def publish_rag_packages(
    outdir: str | Path,
    context_path: str | Path,
    kb_path: str | Path,
) -> dict[str, Path]:
    root = Path(outdir)
    agent = EpidemiologicalAgent.from_file(context_path)
    retriever = NormativeRetriever.from_csv(kb_path)

    packages = {}
    prompts = {}
    for key, question in DEFAULT_QUESTIONS:
        package = build_grounded_request(question, agent, retriever, scope="Mato Grosso")
        packages[key] = package
        prompts[key] = render_prompt(package)

    package_path = root / "agente_rag_pacotes_vnext.json"
    prompt_path = root / "agente_rag_prompts_vnext.json"
    package_path.write_text(json.dumps(packages, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    prompt_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rag_packages": package_path, "rag_prompts": prompt_path}
