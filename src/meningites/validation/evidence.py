"""Captura evidência imutável de uma validação VNext aprovada."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANONICAL_ARTIFACTS = (
    "validacao_vnext.json",
    "situacao_municipal_vnext.csv",
    "sinais_municipais_vnext.csv",
    "indicadores_municipais_vnext.csv",
    "procedencia_situacao_vnext.json",
    "resumo_executivo_estadual_vnext.csv",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_validation_evidence(
    outdir: str | Path,
    *,
    commit_sha: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    root = Path(outdir)
    validation_path = root / "validacao_vnext.json"
    if not validation_path.exists():
        raise FileNotFoundError("validacao_vnext.json não encontrado.")

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if str(validation.get("overall_status", "")).lower() != "pass":
        raise ValueError("Evidência só pode ser capturada quando overall_status=pass.")

    artifacts = []
    missing = []
    for name in CANONICAL_ARTIFACTS:
        path = root / name
        if not path.exists():
            missing.append(name)
            continue
        artifacts.append({
            "arquivo": name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })

    if missing:
        raise ValueError(f"Artefatos canônicos ausentes: {missing}")

    now = generated_at or datetime.now(timezone.utc)
    sha = commit_sha or os.environ.get("GITHUB_SHA") or os.environ.get("MENINGITES_GIT_SHA") or ""
    return {
        "schema_version": "vnext-validation-evidence-1",
        "captured_at": now.isoformat(),
        "commit_sha": sha,
        "validation_status": "pass",
        "validation_fail_n": int(validation.get("fail_n", 0) or 0),
        "validation_attention_n": int(validation.get("attention_n", 0) or 0),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "human_review_required": True,
    }


def publish_validation_evidence(
    outdir: str | Path,
    *,
    commit_sha: str | None = None,
) -> dict[str, Path]:
    root = Path(outdir)
    evidence = capture_validation_evidence(root, commit_sha=commit_sha)

    json_path = root / "evidencia_validacao_vnext.json"
    md_path = root / "EVIDENCIA_VALIDACAO_VNEXT.md"

    json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Evidência de Validação — Meningites VNext",
        "",
        f"- Status: **{evidence['validation_status'].upper()}**",
        f"- Commit: `{evidence['commit_sha'] or 'não informado'}`",
        f"- Capturado em: {evidence['captured_at']}",
        f"- Artefatos: {evidence['artifact_count']}",
        "",
        "## Hashes SHA-256",
        "",
    ]
    for item in evidence["artifacts"]:
        lines.append(f"- `{item['arquivo']}` — `{item['sha256']}` ({item['bytes']} bytes)")
    lines += [
        "",
        "> Esta evidência comprova a combinação código/artefatos validada. Revisão humana continua obrigatória.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"evidence_json": json_path, "evidence_md": md_path}
