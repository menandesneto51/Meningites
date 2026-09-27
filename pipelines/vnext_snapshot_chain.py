"""Publica a cadeia de custódia do snapshot VNext."""
from __future__ import annotations

import argparse
from pathlib import Path

from meningites.validation.snapshot_chain import publish_snapshot_chain


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera cadeia de custódia do snapshot VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    args = parser.parse_args()
    paths = publish_snapshot_chain(Path(args.outdir))
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
