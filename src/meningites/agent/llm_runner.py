"""Execução opcional LLM com validação obrigatória."""
from __future__ import annotations

import json
from pathlib import Path

from meningites.agent.llm_client import OptionalLLMClient
from meningites.agent.response_validator import validate_llm_response


def run_validated_llm(
    package: dict,
    prompt: str,
    *,
    client: OptionalLLMClient | None = None,
) -> dict:
    llm = (client or OptionalLLMClient()).complete(prompt)
    if llm.get("status") != "ok":
        return {
            "status": llm.get("status"),
            "provider": llm.get("provider"),
            "model": llm.get("model"),
            "accepted": False,
            "issues": [llm.get("error") or "LLM indisponível"],
            "response": "",
            "requires_human_review": True,
        }

    validation = validate_llm_response(package, llm.get("text", ""))
    return {
        "status": "validated" if validation.accepted else "rejected",
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "accepted": validation.accepted,
        "issues": list(validation.issues),
        "response": llm.get("text", ""),
        "requires_human_review": validation.requires_human_review,
    }


def publish_llm_validation_templates(outdir: str | Path, rag_packages_path: str | Path) -> Path:
    root = Path(outdir)
    packages = json.loads(Path(rag_packages_path).read_text(encoding="utf-8"))
    template = {
        key: {
            "status": "not_executed",
            "accepted": False,
            "issues": ["Executar somente com credencial local e validação pós-resposta."],
            "requires_human_review": True,
            "package_schema": pkg.get("schema_version"),
        }
        for key, pkg in packages.items()
    }
    path = root / "agente_llm_validacao_vnext.json"
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
