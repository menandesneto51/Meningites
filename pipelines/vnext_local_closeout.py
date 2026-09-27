"""Orquestrador local seguro do fechamento VNext.

Fase prepare:
- executa preflight para um commit explícito;
- exige PASS;
- publica instruções de revisão visual;
- não registra aprovação humana.

Fase finalize:
- exige revisão visual explícita do mesmo commit;
- publica readiness, release readiness, cadeia de custódia, manifesto e catálogo de schemas;
- falha se qualquer gate final não estiver aprovado.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.validation.readiness import publish_readiness
from meningites.validation.release_readiness import publish_release_readiness
from meningites.validation.snapshot_chain import publish_snapshot_chain
from meningites.validation.operational_manifest import publish_operational_manifest
from meningites.domain.schema_registry import schema_catalog


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_schema_catalog(root: Path) -> Path:
    path = root / "catalogo_schemas_vnext.json"
    path.write_text(json.dumps({
        "schema_version": "vnext-schema-catalog-1",
        "contracts": schema_catalog(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def finalize(
    *,
    outdir: str | Path,
    commit_sha: str,
    ci_status: str,
    ci_run: str,
) -> dict:
    root = Path(outdir)
    visual_path = root / "REVISAO_VISUAL_VNEXT.json"
    if not visual_path.exists():
        raise ValueError("Revisão visual ausente. Inspecione dashboard/cards e registre REVISAO_VISUAL_VNEXT.json.")
    visual = _load(visual_path)
    if not bool(visual.get("approved")):
        raise ValueError("Revisão visual não aprovada.")
    if str(visual.get("commit_sha", "")).strip() != str(commit_sha).strip():
        raise ValueError("Revisão visual pertence a outro commit.")

    readiness_paths = publish_readiness(root)
    readiness = _load(readiness_paths["readiness_json"])
    if not readiness.get("ready"):
        raise ValueError("Readiness bloqueado. Consulte prontidao_vnext.json.")

    release_paths = publish_release_readiness(
        root,
        ci_status=ci_status,
        ci_run=ci_run,
        commit_sha=commit_sha,
    )
    release = _load(release_paths["release_readiness_json"])
    if not release.get("ready_for_merge_review"):
        raise ValueError("Release readiness bloqueado. Consulte release_readiness_vnext.json.")

    chain_paths = publish_snapshot_chain(root)
    chain = _load(chain_paths["chain_json"])
    if not chain.get("custody_ok"):
        raise ValueError("Cadeia de custódia inconsistente.")

    manifest_paths = publish_operational_manifest(root)
    schema_path = _write_schema_catalog(root)

    result = {
        "schema_version": "vnext-local-closeout-1",
        "status": "ready_for_human_merge_review",
        "commit_sha": commit_sha,
        "ci_status": ci_status,
        "ci_run": ci_run,
        "snapshot_commit": readiness.get("snapshot_commit"),
        "ready": True,
        "human_merge_decision_required": True,
        "artifacts": {
            "readiness_json": str(readiness_paths["readiness_json"]),
            "release_readiness_json": str(release_paths["release_readiness_json"]),
            "chain_json": str(chain_paths["chain_json"]),
            "manifest_json": str(manifest_paths["manifest_json"]),
            "schema_catalog": str(schema_path),
        },
    }
    path = root / "fechamento_local_vnext.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestra fechamento local seguro do Meningites VNext.")
    parser.add_argument("--phase", choices=("prepare", "finalize"), required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-status", default="success")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--skip-module12", action="store_true")
    args = parser.parse_args()

    root = Path(args.outdir)
    if args.phase == "prepare":
        from pipelines.vnext_preflight import run_preflight

        result = run_preflight(
            repo_root=args.repo_root,
            outdir=args.outdir,
            commit_sha=args.commit,
            skip_module12=args.skip_module12,
        )
        if result.get("status") != "pass":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        instruction = {
            "schema_version": "vnext-local-closeout-1",
            "status": "awaiting_visual_review",
            "commit_sha": args.commit,
            "next_step": "Inspecione dashboard/cards e registre revisão visual para este mesmo commit antes de --phase finalize.",
            "human_review_required": True,
        }
        root.mkdir(parents=True, exist_ok=True)
        (root / "fechamento_local_vnext.json").write_text(
            json.dumps(instruction, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(instruction, ensure_ascii=False, indent=2))
        return 0

    try:
        result = finalize(
            outdir=args.outdir,
            commit_sha=args.commit,
            ci_status=args.ci_status,
            ci_run=args.ci_run,
        )
    except ValueError as exc:
        print(json.dumps({
            "status": "blocked",
            "error": str(exc),
            "human_review_required": True,
        }, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
