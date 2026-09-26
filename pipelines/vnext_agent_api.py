"""Servidor HTTP opcional para o agente epidemiológico VNext."""
from __future__ import annotations

import argparse


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

    from meningites.agent.http_api import create_app
    uvicorn.run(create_app(outdir=args.outdir), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
