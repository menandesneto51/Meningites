"""Registra revisão visual humana do VNext."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Registra revisão visual humana do VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--notes", default="")
    parser.add_argument("--commit", required=True, help="SHA do commit efetivamente revisado.")
    args = parser.parse_args()

    payload = {
        "schema_version": "vnext-visual-review-1",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": args.commit.strip(),
        "reviewer": args.reviewer.strip(),
        "approved": bool(args.approved),
        "notes": args.notes.strip(),
        "human_attestation": True,
    }
    root = Path(args.outdir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "REVISAO_VISUAL_VNEXT.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0 if payload["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
