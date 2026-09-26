"""Publica o manifesto operacional consolidado do VNext."""
from __future__ import annotations

import argparse
from pathlib import Path

from meningites.validation.operational_manifest import publish_operational_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera manifesto operacional do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    args = parser.parse_args()
    paths = publish_operational_manifest(Path(args.outdir))
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
