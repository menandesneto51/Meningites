"""Camada HTTP opcional do agente epidemiológico VNext.

A lógica permanece em query_agent(); FastAPI é somente um adapter de transporte.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from meningites.agent.query_service import query_agent
from meningites.validation.health import load_validation_health


def handle_query_payload(payload: dict[str, Any], *, outdir: str | Path) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        return {"ok": False, "status_code": 400, "error": "question é obrigatório."}

    scope = str(payload.get("scope") or "Mato Grosso")
    mode = str(payload.get("mode") or "auto")
    use_llm = bool(payload.get("use_llm", False))
    if mode not in {"auto", "state", "regional", "municipality", "gaps", "rag"}:
        return {"ok": False, "status_code": 400, "error": f"mode inválido: {mode}"}

    root = Path(outdir)
    validation = load_validation_health(root)
    if validation["blocking"]:
        return {
            "ok": False,
            "status_code": 503,
            "error": f"Gate VNext não aprovado: {validation['overall_status']}. Execute a validação antes da consulta operacional.",
        }

    context_path = root / "agente_epidemiologico_contexto_vnext.json"
    kb_path = root / "assistente_kb_docs_ms_v27.csv"
    if not context_path.exists():
        return {
            "ok": False,
            "status_code": 503,
            "error": "Contexto VNext não publicado. Execute pipelines/vnext_municipal.py primeiro.",
        }

    result = query_agent(
        context_path=context_path,
        kb_path=kb_path,
        question=question,
        scope=scope,
        mode=mode,
        use_llm=use_llm,
    )
    return {"ok": True, "status_code": 200, "data": result}


def create_app(*, outdir: str | Path = "saida_meningites_v17"):
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI não instalado. Instale requirements-api.txt para executar a camada HTTP."
        ) from exc

    app = FastAPI(
        title="Meningites VNext Agent API",
        version="vnext-1",
        description="API fina sobre o agente epidemiológico auditável do CIEVS-MT.",
    )

    @app.get("/health")
    def health():
        root = Path(outdir)
        validation = load_validation_health(root)
        return {
            "status": "ok" if validation["overall_status"] == "pass" else "degraded",
            "context_published": (root / "agente_epidemiologico_contexto_vnext.json").exists(),
            "validation": {
                "overall_status": validation["overall_status"],
                "fail_n": validation["fail_n"],
                "attention_n": validation["attention_n"],
                "blocking": validation["blocking"],
            },
            "llm_default": "disabled",
        }

    @app.post("/v1/query")
    def query(payload: dict[str, Any]):
        result = handle_query_payload(payload, outdir=outdir)
        if not result["ok"]:
            raise HTTPException(status_code=result["status_code"], detail=result["error"])
        return result["data"]

    return app
