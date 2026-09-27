"""Servidor HTTP opcional para o agente epidemiológico VNext."""
from __future__ import annotations

import argparse
import os


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a API HTTP opcional do agente Meningites VNext.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Instale requirements-api.txt para executar a API.") from exc

    from meningites.agent.http_api import create_app, validate_api_bind
    api_token = os.environ.get("MENINGITES_API_TOKEN", "")
    try:
        validate_api_bind(args.host, api_token)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    uvicorn.run(
        create_app(outdir=args.outdir, api_token=api_token or None),
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
