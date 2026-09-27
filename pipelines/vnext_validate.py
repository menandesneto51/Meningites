"""Executa reconciliação/gate de validação do Meningites VNext."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.validation.reconcile import publish_validation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida artefatos reais do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--strict", action="store_true", help="Retorna exit code 2 se houver FAIL.")
    args = parser.parse_args()

    paths = publish_validation_report(Path(args.outdir))
    for name, path in paths.items():
        print(f"{name}: {path}")

    report = json.loads(paths["validation_json"].read_text(encoding="utf-8"))
    print(f"overall_status: {report['overall_status']}")
    if args.strict and report["overall_status"] == "fail":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
