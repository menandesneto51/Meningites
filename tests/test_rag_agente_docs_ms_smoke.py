# -*- coding: utf-8 -*-
"""Smoke test RAG + agente (LLM) após ingestão docs_ms."""
from importlib import import_module

a = import_module("16_assistente_cievs_v23")
a._KB_CACHE = None
kb = a.load_kb(force=True)
n_pdf = sum(1 for d in kb if str(d.get("arquivo", "")).lower().endswith(".pdf"))
n_md = sum(1 for d in kb if str(d.get("arquivo", "")).lower().endswith((".md", ".txt")))
n_cur = sum(1 for d in kb if str(d.get("origem", "")) == "curado")
print(f"KB total={len(kb)} | chunks PDF={n_pdf} | MD/TXT={n_md} | curados={n_cur}")

ctx = a.build_contexto_operacional()
perguntas = [
    "Qual a definicao de caso suspeito na NT 154?",
    "Quando caracterizar surto institucional de DM?",
    "Quimioprofilaxia e indicada para meningite viral?",
    "A NT 97 ainda esta vigente?",
    "O que e a vigilancia sentinela DIHi e DPI da NT 201?",
    "Quais indicadores operacionais o Informe Meningites monitora?",
]
print("\n--- RAG offline ---")
for q in perguntas:
    r = a.answer(q, contexto_dados=ctx, use_llm=False)
    top = r["fontes"][0] if r["fontes"] else {}
    print(f"Q: {q}")
    print(f"  top: {str(top.get('titulo', '?'))[:80]} ({top.get('score', '?')})")
    print(f"  fonte: {str(top.get('fonte', ''))[:75]}")

print("\n--- AGENTE LLM ---")
q = "Diante de um caso suspeito de DM em creche, quais passos a NT 154 indica?"
r = a.answer(q, contexto_dados=ctx, use_llm=True)
print("modo:", r.get("modo"))
print("fontes:", " | ".join(str(f["titulo"])[:45] for f in r.get("fontes", [])[:4]))
print("resposta:\n", (r.get("resposta") or "")[:1500])
if r.get("aviso_llm"):
    print("aviso:", r["aviso_llm"][:400])
