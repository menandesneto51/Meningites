"""CLI de consulta do agente epidemiológico VNext."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from meningites.agent.query_service import query_agent, save_query_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Consulta o agente epidemiológico Meningites VNext.")
    parser.add_argument("question", help="Pergunta para o agente.")
    parser.add_argument("--outdir", default="saida_meningites_v17")
    parser.add_argument("--scope", default="Mato Grosso", help="Mato Grosso, regional, município ou código municipal.")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "state", "regional", "municipality", "gaps", "rag"],
    )
    parser.add_argument("--llm", action="store_true", help="Executa LLM opcional com validação pós-resposta.")
    parser.add_argument("--save", default="", help="Caminho opcional para salvar o JSON da consulta.")
    args = parser.parse_args()

    root = Path(args.outdir)
    result = query_agent(
        context_path=root / "agente_epidemiologico_contexto_vnext.json",
        kb_path=root / "assistente_kb_docs_ms_v27.csv",
        question=args.question,
        scope=args.scope,
        mode=args.mode,
        use_llm=args.llm,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if args.save:
        save_query_result(result, args.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
