"""Relatório executivo de release readiness do Meningites VNext."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meningites.domain.schema_registry import require_schema


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_release_readiness(
    outdir: str | Path,
    *,
    ci_status: str = "unknown",
    ci_run: str = "",
    commit_sha: str = "",
) -> dict[str, Any]:
    root = Path(outdir)
    validation = _load(root / "validacao_vnext.json")
    evidence = _load(root / "evidencia_validacao_vnext.json")
    preflight = _load(root / "preflight_vnext.json")
    readiness = _load(root / "prontidao_vnext.json")
    visual = _load(root / "REVISAO_VISUAL_VNEXT.json")
    context = _load(root / "agente_epidemiologico_contexto_vnext.json")

    schema_ok = {}
    for name, payload, contract in [
        ("validation", validation, "validation"),
        ("evidence", evidence, "validation_evidence"),
        ("preflight", preflight, "preflight"),
        ("readiness", readiness, "readiness"),
        ("visual_review", visual, "visual_review"),
        ("agent_context", context, "agent_context"),
    ]:
        if not payload:
            schema_ok[name] = False
            continue
        try:
            require_schema(payload, contract)
            schema_ok[name] = True
        except ValueError:
            schema_ok[name] = False

    requirements = [
        {
            "id": "ci",
            "ok": ci_status.lower() == "success",
            "detail": f"status={ci_status}" + (f" run={ci_run}" if ci_run else ""),
        },
        {
            "id": "validation",
            "ok": bool(validation) and schema_ok["validation"] and str(validation.get("overall_status", "")).lower() == "pass",
            "detail": "PASS local" if validation else "validacao_vnext.json ausente",
        },
        {
            "id": "preflight",
            "ok": bool(preflight) and schema_ok["preflight"] and str(preflight.get("status", "")).lower() == "pass",
            "detail": "PASS" if preflight else "preflight_vnext.json ausente",
        },
        {
            "id": "evidence",
            "ok": bool(evidence) and schema_ok["evidence"] and str(evidence.get("validation_status", "")).lower() == "pass",
            "detail": (
                f"artefatos={evidence.get('artifact_count', 0)}"
                if evidence else "evidencia_validacao_vnext.json ausente"
            ),
        },
        {
            "id": "visual_review",
            "ok": bool(visual) and schema_ok["visual_review"] and bool(visual.get("approved")) and bool(visual.get("reviewer")),
            "detail": (
                f"revisor={visual.get('reviewer')}"
                if visual else "REVISAO_VISUAL_VNEXT.json ausente"
            ),
        },
        {
            "id": "data_quality",
            "ok": bool(context)
            and schema_ok["agent_context"]
            and not bool((context.get("data_quality") or {}).get("has_blocking_divergences"))
            and int((context.get("data_quality") or {}).get("blocking_divergences_n", 0) or 0) == 0,
            "detail": (
                "blocking_divergences_n="
                + str((context.get("data_quality") or {}).get("blocking_divergences_n", 0))
                if context else "agente_epidemiologico_contexto_vnext.json ausente"
            ),
        },
        {
            "id": "snapshot_commit",
            "ok": bool(commit_sha)
            and bool(readiness)
            and schema_ok["readiness"]
            and str(readiness.get("snapshot_commit", "")) == str(commit_sha),
            "detail": (
                "requested=" + str(commit_sha or "<ausente>")
                + " readiness=" + str((readiness or {}).get("snapshot_commit", "") or "<ausente>")
            ),
        },
        {
            "id": "readiness",
            "ok": bool(readiness) and schema_ok["readiness"] and bool(readiness.get("ready")),
            "detail": (
                f"status={readiness.get('status')}"
                if readiness else "prontidao_vnext.json ausente"
            ),
        },
    ]

    blockers = [item for item in requirements if not item["ok"]]
    ready = not blockers

    return {
        "schema_version": "vnext-release-readiness-1",
        "commit_sha": commit_sha,
        "ci_run": ci_run,
        "ci_status": ci_status,
        "ready_for_merge_review": ready,
        "status": "ready_for_merge_review" if ready else "blocked",
        "requirements": requirements,
        "blockers": blockers,
        "human_merge_decision_required": True,
    }


def publish_release_readiness(
    outdir: str | Path,
    *,
    ci_status: str = "unknown",
    ci_run: str = "",
    commit_sha: str = "",
) -> dict[str, Path]:
    root = Path(outdir)
    report = build_release_readiness(
        root,
        ci_status=ci_status,
        ci_run=ci_run,
        commit_sha=commit_sha,
    )
    json_path = root / "release_readiness_vnext.json"
    md_path = root / "RELEASE_READINESS_VNEXT.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Release Readiness — Meningites VNext",
        "",
        f"**Status:** {report['status'].upper()}",
        f"**Commit:** {report['commit_sha'] or 'N/D'}",
        f"**CI:** {report['ci_status']} {report['ci_run']}".strip(),
        "",
        "## Requisitos",
        "",
    ]
    for item in report["requirements"]:
        mark = "OK" if item["ok"] else "PENDENTE"
        lines.append(f"- **{mark}** · {item['id']} — {item['detail']}")

    if report["blockers"]:
        lines += ["", "## Bloqueios", ""]
        for item in report["blockers"]:
            lines.append(f"- {item['id']}: {item['detail']}")

    lines += [
        "",
        "> Este relatório não autoriza merge automaticamente. A decisão final permanece humana.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"release_readiness_json": json_path, "release_readiness_md": md_path}
