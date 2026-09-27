"""Cadeia de custódia do snapshot VNext."""
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


def build_snapshot_chain(outdir: str | Path) -> dict[str, Any]:
    root = Path(outdir)
    evidence = _load(root / "evidencia_validacao_vnext.json")
    preflight = _load(root / "preflight_vnext.json")
    visual = _load(root / "REVISAO_VISUAL_VNEXT.json")
    readiness = _load(root / "prontidao_vnext.json")
    release = _load(root / "release_readiness_vnext.json")

    items = [
        ("evidence", evidence, "validation_evidence"),
        ("preflight", preflight, "preflight"),
        ("visual_review", visual, "visual_review"),
        ("readiness", readiness, "readiness"),
    ]
    compatibility: dict[str, bool] = {}
    for name, payload, contract in items:
        if not payload:
            compatibility[name] = False
            continue
        try:
            require_schema(payload, contract)
            compatibility[name] = True
        except ValueError:
            compatibility[name] = False

    commits = {
        "evidence": str((evidence or {}).get("commit_sha", "") or ""),
        "preflight": str((preflight or {}).get("commit_sha", "") or ""),
        "visual_review": str((visual or {}).get("commit_sha", "") or ""),
        "readiness": str((readiness or {}).get("snapshot_commit", "") or ""),
        "release_requested": str((release or {}).get("commit_sha", "") or ""),
    }
    required_commit_values = [commits[k] for k in ("evidence", "preflight", "visual_review", "readiness")]
    snapshot_consistent = all(required_commit_values) and len(set(required_commit_values)) == 1
    snapshot_commit = required_commit_values[0] if snapshot_consistent else ""

    artifacts = []
    for item in (evidence or {}).get("artifacts", []):
        artifacts.append({
            "arquivo": item.get("arquivo"),
            "sha256": item.get("sha256"),
            "bytes": item.get("bytes"),
        })

    custody_ok = (
        all(compatibility.values())
        and snapshot_consistent
        and bool(artifacts)
        and bool((visual or {}).get("approved"))
        and bool((visual or {}).get("reviewer"))
        and bool((readiness or {}).get("ready"))
    )

    return {
        "schema_version": "vnext-snapshot-chain-1",
        "custody_ok": custody_ok,
        "snapshot_commit": snapshot_commit,
        "commits": commits,
        "schema_compatibility": compatibility,
        "review": {
            "approved": bool((visual or {}).get("approved")),
            "reviewer": (visual or {}).get("reviewer"),
            "reviewed_at": (visual or {}).get("reviewed_at"),
            "notes": (visual or {}).get("notes"),
        },
        "validation_evidence": {
            "captured_at": (evidence or {}).get("captured_at"),
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        },
        "readiness": {
            "status": (readiness or {}).get("status", "not_evaluated"),
            "ready": bool((readiness or {}).get("ready")),
        },
        "release_readiness": {
            "status": (release or {}).get("status", "not_evaluated"),
            "ready_for_merge_review": bool((release or {}).get("ready_for_merge_review")),
        },
        "human_review_required": True,
    }


def publish_snapshot_chain(outdir: str | Path) -> dict[str, Path]:
    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    payload = build_snapshot_chain(root)
    json_path = root / "cadeia_custodia_vnext.json"
    md_path = root / "CADEIA_CUSTODIA_VNEXT.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Cadeia de Custódia — Meningites VNext",
        "",
        f"- Integridade da cadeia: **{payload['custody_ok']}**",
        f"- Snapshot commit: `{payload['snapshot_commit'] or 'N/D'}`",
        f"- Revisor: {payload['review']['reviewer'] or 'N/D'}",
        f"- Artefatos hashados: {payload['validation_evidence']['artifact_count']}",
        "",
        "## Artefatos",
        "",
    ]
    for item in payload["validation_evidence"]["artifacts"]:
        lines.append(f"- `{item['arquivo']}` — `{item['sha256']}` ({item['bytes']} bytes)")
    lines += ["", "> Registro derivado; não substitui os gates nem a revisão humana."]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"chain_json": json_path, "chain_md": md_path}
