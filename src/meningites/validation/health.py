"""Resumo de saúde operacional do VNext a partir do gate publicado."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meningites.domain.schema_registry import require_schema


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

    try:
        require_schema(payload, "validation")
        schema_compatible = True
    except (ValueError, KeyError) as exc:
        return {
            "available": True,
            "overall_status": "incompatible_schema",
            "fail_n": int(payload.get("fail_n", 0) or 0),
            "attention_n": int(payload.get("attention_n", 0) or 0),
            "checks": payload.get("checks") or [],
            "blocking": True,
            "schema_compatible": False,
            "detail": f"Schema de validação incompatível: {exc}",
        }

    checks = payload.get("checks")
    if not isinstance(checks, list):
        return {
            "available": True,
            "overall_status": "invalid_report",
            "fail_n": None,
            "attention_n": None,
            "checks": [],
            "blocking": True,
            "schema_compatible": schema_compatible,
            "counts_consistent": False,
            "detail": "Relatório de validação inválido: checks deve ser uma lista.",
        }

    try:
        fail_n = int(payload.get("fail_n", 0) or 0)
        attention_n = int(payload.get("attention_n", 0) or 0)
    except (TypeError, ValueError):
        return {
            "available": True,
            "overall_status": "invalid_report",
            "fail_n": None,
            "attention_n": None,
            "checks": checks,
            "blocking": True,
            "schema_compatible": schema_compatible,
            "counts_consistent": False,
            "detail": "Relatório de validação inválido: contagens não numéricas.",
        }

    actual_fail_n = sum(1 for item in checks if str(item.get("status", "")).lower() == "fail")
    actual_attention_n = sum(
        1 for item in checks if str(item.get("status", "")).lower() == "attention"
    )
    expected_status = (
        "fail"
        if actual_fail_n
        else ("attention" if actual_attention_n else "pass")
    )
    status = str(payload.get("overall_status") or "unknown").lower()
    counts_consistent = (
        fail_n == actual_fail_n
        and attention_n == actual_attention_n
        and status == expected_status
    )
    if not counts_consistent:
        return {
            "available": True,
            "overall_status": "inconsistent_report",
            "fail_n": fail_n,
            "attention_n": attention_n,
            "checks": checks,
            "blocking": True,
            "schema_compatible": schema_compatible,
            "counts_consistent": False,
            "detail": (
                "Relatório inconsistente: "
                f"declarado status={status}, fail_n={fail_n}, attention_n={attention_n}; "
                f"calculado status={expected_status}, fail_n={actual_fail_n}, "
                f"attention_n={actual_attention_n}."
            ),
        }

    return {
        "available": True,
        "overall_status": status,
        "fail_n": fail_n,
        "attention_n": attention_n,
        "checks": checks,
        "blocking": status != "pass",
        "schema_compatible": schema_compatible,
        "counts_consistent": True,
        "detail": "Gate aprovado." if status == "pass" else "Gate exige revisão antes de ativação permanente.",
    }


def important_checks(health: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    checks = health.get("checks") or []
    ordered = sorted(
        checks,
        key=lambda item: {"fail": 0, "attention": 1, "pass": 2}.get(str(item.get("status")), 3),
    )
    return ordered[:limit]
