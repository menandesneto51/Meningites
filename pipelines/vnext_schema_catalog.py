"""Publica catálogo de schemas VNext."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.domain.schema_registry import schema_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica catálogo de contratos/schema do Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    args = parser.parse_args()

    root = Path(args.outdir)
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "vnext-schema-catalog-1",
        "contracts": schema_catalog(),
    }
    path = root / "catalogo_schemas_vnext.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
