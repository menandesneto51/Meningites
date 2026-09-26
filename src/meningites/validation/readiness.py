"""Gate de prontidão para merge/ativação do Meningites VNext."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_readiness(outdir: str | Path) -> dict[str, Any]:
    root = Path(outdir)
    checks = []

    validation_path = root / "validacao_vnext.json"
    if validation_path.exists():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        ok = str(validation.get("overall_status", "")).lower() == "pass"
        checks.append({
            "id": "validation_pass",
            "ok": ok,
            "detail": "overall_status=" + str(validation.get("overall_status")),
        })
    else:
        checks.append({"id": "validation_pass", "ok": False, "detail": "validacao_vnext.json ausente"})

    evidence_path = root / "evidencia_validacao_vnext.json"
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        ok = str(evidence.get("validation_status", "")).lower() == "pass" and int(evidence.get("artifact_count", 0)) > 0
        checks.append({
            "id": "evidence_captured",
            "ok": ok,
            "detail": "artifact_count=" + str(evidence.get("artifact_count", 0)),
        })
    else:
        checks.append({"id": "evidence_captured", "ok": False, "detail": "evidencia_validacao_vnext.json ausente"})

    preflight_path = root / "preflight_vnext.json"
    if preflight_path.exists():
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        ok = str(preflight.get("status", "")).lower() == "pass"
        checks.append({
            "id": "preflight_pass",
            "ok": ok,
            "detail": "status=" + str(preflight.get("status")),
        })
    else:
        checks.append({"id": "preflight_pass", "ok": False, "detail": "preflight_vnext.json ausente"})

    visual_path = root / "REVISAO_VISUAL_VNEXT.json"
    if visual_path.exists():
        visual = json.loads(visual_path.read_text(encoding="utf-8"))
        ok = bool(visual.get("approved")) and bool(visual.get("reviewer"))
        checks.append({
            "id": "visual_review",
            "ok": ok,
            "detail": "approved=" + str(visual.get("approved")) + " reviewer=" + str(visual.get("reviewer") or "N/D"),
        })
    else:
        checks.append({"id": "visual_review", "ok": False, "detail": "REVISAO_VISUAL_VNEXT.json ausente"})

    ready = all(item["ok"] for item in checks)
    return {
        "schema_version": "vnext-readiness-1",
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "checks": checks,
        "human_review_required": True,
    }


def publish_readiness(outdir: str | Path) -> dict[str, Path]:
    root = Path(outdir)
    report = build_readiness(root)
    json_path = root / "prontidao_vnext.json"
    md_path = root / "PRONTIDAO_VNEXT.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Prontidão Meningites VNext",
        "",
        "**Status:** " + report["status"].upper(),
        "",
        "## Requisitos",
        "",
    ]
    for item in report["checks"]:
        mark = "OK" if item["ok"] else "PENDENTE"
        lines.append("- **" + mark + "** · " + item["id"] + " — " + item["detail"])
    lines += [
        "",
        "> Estado READY não substitui a decisão humana de merge/ativação.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"readiness_json": json_path, "readiness_md": md_path}
