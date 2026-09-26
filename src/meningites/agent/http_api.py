"""Camada HTTP opcional do agente epidemiológico VNext.

A lógica permanece em query_agent(); FastAPI é somente um adapter de transporte.
"""
from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from meningites.agent.query_service import query_agent
from meningites.validation.health import load_validation_health


MAX_QUESTION_CHARS = 4000
MAX_SCOPE_CHARS = 200
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def is_loopback_host(host: str) -> bool:
    return str(host).strip().casefold() in _LOOPBACK_HOSTS


def validate_api_bind(host: str, api_token: str | None) -> None:
    if is_loopback_host(host):
        return
    if not str(api_token or "").strip():
        raise ValueError(
            "Bind externo exige MENINGITES_API_TOKEN configurado. "
            "Use localhost enquanto autenticação/TLS institucional não estiverem configurados."
        )


def bearer_authorized(authorization: str | None, api_token: str | None) -> bool:
    token = str(api_token or "").strip()
    if not token:
        return True
    prefix = "Bearer "
    if not isinstance(authorization, str) or not authorization.startswith(prefix):
        return False
    supplied = authorization[len(prefix):].strip()
    return bool(supplied) and hmac.compare_digest(supplied, token)


def handle_query_payload(payload: dict[str, Any], *, outdir: str | Path) -> dict[str, Any]:
    raw_question = payload.get("question", "")
    if not isinstance(raw_question, str):
        return {"ok": False, "status_code": 400, "error": "question deve ser texto."}
    question = raw_question.strip()
    if not question:
        return {"ok": False, "status_code": 400, "error": "question é obrigatório."}
    if len(question) > MAX_QUESTION_CHARS:
        return {"ok": False, "status_code": 400, "error": f"question excede {MAX_QUESTION_CHARS} caracteres."}

    raw_scope = payload.get("scope", "Mato Grosso")
    if raw_scope is None:
        raw_scope = "Mato Grosso"
    if not isinstance(raw_scope, str):
        return {"ok": False, "status_code": 400, "error": "scope deve ser texto."}
    scope = raw_scope.strip() or "Mato Grosso"
    if len(scope) > MAX_SCOPE_CHARS:
        return {"ok": False, "status_code": 400, "error": f"scope excede {MAX_SCOPE_CHARS} caracteres."}

    raw_mode = payload.get("mode", "auto")
    if not isinstance(raw_mode, str):
        return {"ok": False, "status_code": 400, "error": "mode deve ser texto."}
    mode = raw_mode.strip() or "auto"

    raw_use_llm = payload.get("use_llm", False)
    if not isinstance(raw_use_llm, bool):
        return {"ok": False, "status_code": 400, "error": "use_llm deve ser booleano true/false."}
    use_llm = raw_use_llm
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


def create_app(*, outdir: str | Path = "saida_meningites_v17", api_token: str | None = None):
    try:
        from fastapi import FastAPI, Header, HTTPException
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
    def query(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        if not bearer_authorized(authorization, api_token):
            raise HTTPException(status_code=401, detail="Bearer token ausente ou inválido.")
        result = handle_query_payload(payload, outdir=outdir)
        if not result["ok"]:
            raise HTTPException(status_code=result["status_code"], detail=result["error"])
        return result["data"]

    return app
