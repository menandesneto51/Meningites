"""Gera relatório executivo de release readiness do VNext."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.validation.release_readiness import publish_release_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera release readiness do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--ci-status", default="unknown")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--commit", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    paths = publish_release_readiness(
        Path(args.outdir),
        ci_status=args.ci_status,
        ci_run=args.ci_run,
        commit_sha=args.commit,
    )
    report = json.loads(paths["release_readiness_json"].read_text(encoding="utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_merge_review"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
