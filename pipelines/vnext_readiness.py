"""Publica o gate de prontidão do VNext."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.validation.readiness import publish_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Avalia prontidão do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    paths = publish_readiness(Path(args.outdir))
    report = json.loads(paths["readiness_json"].read_text(encoding="utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
