"""Entry point do Motor Municipal VNext."""
from __future__ import annotations

import argparse
from pathlib import Path

from meningites.operational_queue.publisher import publish_municipal_vnext


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica situação e sinais municipais do Meningites VNext.")
    parser.add_argument(
        "--outdir",
        default="saida_meningites_v17",
        help="Diretório que contém os artefatos operacionais legados e receberá as saídas VNext.",
    )
    args = parser.parse_args()
    paths = publish_municipal_vnext(Path(args.outdir))
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
