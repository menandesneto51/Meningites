"""Captura evidência do gate VNext aprovado."""
from __future__ import annotations

import argparse
from pathlib import Path

from meningites.validation.evidence import publish_validation_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura evidência de validação PASS do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--commit", default="", help="SHA do commit validado.")
    args = parser.parse_args()

    try:
        paths = publish_validation_evidence(Path(args.outdir), commit_sha=args.commit or None)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[FAIL] {exc}")
        return 2

    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
