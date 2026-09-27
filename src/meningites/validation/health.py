"""Resumo de saúde operacional do VNext a partir do gate publicado."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_validation_health(outdir: str | Path) -> dict[str, Any]:
    root = Path(outdir)
    path = root / "validacao_vnext.json"
    if not path.exists() or path.stat().st_size == 0:
        return {
            "available": False,
            "overall_status": "not_validated",
            "fail_n": None,
            "attention_n": None,
            "checks": [],
            "blocking": True,
            "detail": "Gate VNext ainda não executado.",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "available": True,
            "overall_status": "invalid_report",
            "fail_n": None,
            "attention_n": None,
            "checks": [],
            "blocking": True,
            "detail": f"Falha ao ler validacao_vnext.json: {type(exc).__name__}: {exc}",
        }

    status = str(payload.get("overall_status") or "unknown").lower()
    return {
        "available": True,
        "overall_status": status,
        "fail_n": int(payload.get("fail_n", 0) or 0),
        "attention_n": int(payload.get("attention_n", 0) or 0),
        "checks": payload.get("checks") or [],
        "blocking": status != "pass",
        "detail": "Gate aprovado." if status == "pass" else "Gate exige revisão antes de ativação permanente.",
    }


def important_checks(health: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    checks = health.get("checks") or []
    ordered = sorted(
        checks,
        key=lambda item: {"fail": 0, "attention": 1, "pass": 2}.get(str(item.get("status")), 3),
    )
    return ordered[:limit]
