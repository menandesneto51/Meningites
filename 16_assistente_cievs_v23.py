# -*- coding: utf-8 -*-
"""
16_assistente_cievs_v23.py
Assistente CIEVS: recuperação normativa (RAG local) + narrativa do boletim.
Funciona offline; se OPENAI_API_KEY estiver definida, enriquece com LLM opcional.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from conhecimento_ms_meningites_v23 import DOCS, FAQ_RAPIDO
from meningites_v17_common import OUT, REL, fmt_num

KB_PATH = OUT / "assistente_kb_documentos_v23.csv"
QA_PATH = OUT / "assistente_faq_exemplos_v23.csv"
NARR_PATH = OUT / "assistente_narrativa_boletim_v23.md"
NARR_REL = REL / "BOLETIM_SEMANAL_MENINGITES_V23_NARRATIVA_IA.md"
META_PATH = OUT / "assistente_meta_v23.json"


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]+", " ", s.lower()).strip()


def _tokens(s: str) -> set[str]:
    stop = {
        "de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com", "por",
        "um", "uma", "os", "as", "no", "na", "que", "se", "ao", "ou", "como",
        "quais", "qual", "quando", "onde", "sobre", "mais", "menos",
    }
    out = set()
    for t in _strip(s).split():
        if len(t) <= 2 or t in stop:
            continue
        out.add(t)
        # singular/plural leve
        if t.endswith("s") and len(t) > 4:
            out.add(t[:-1])
        else:
            out.add(t + "s")
    return out


def score_doc(query: str, doc: dict) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    title = _tokens(doc.get("titulo", ""))
    tags = _tokens(doc.get("tags", ""))
    tema = _tokens(doc.get("tema", ""))
    body = _tokens(doc.get("texto", ""))
    blob = title | tags | tema | body
    if not blob:
        return 0.0
    inter = q & blob
    jacc = len(inter) / len(q | blob)
    cov = len(inter) / len(q)
    # Bônus se a query acerta título/tags/tema (mais específico que o corpo)
    bonus = 0.0
    if q & title:
        bonus += 0.25 * (len(q & title) / len(q))
    if q & tags:
        bonus += 0.20 * (len(q & tags) / len(q))
    if q & tema:
        bonus += 0.15 * (len(q & tema) / len(q))
    return min(1.0, 0.30 * jacc + 0.45 * cov + bonus)


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    ranked = sorted(
        ({**d, "score": score_doc(query, d)} for d in DOCS),
        key=lambda x: x["score"],
        reverse=True,
    )
    return [r for r in ranked if r["score"] > 0][:top_k]


def answer_offline(query: str, contexto_dados: str = "") -> dict:
    hits = retrieve(query, top_k=4)
    if not hits:
        return {
            "modo": "offline",
            "pergunta": query,
            "resposta": (
                "Não encontrei trecho normativo correspondente na base local. "
                "Reformule a pergunta (ex.: quimioprofilaxia, surto NT 97, indicadores MS) "
                "ou consulte o Guia de Vigilância / NT 97/2024."
            ),
            "fontes": [],
            "scores": [],
        }

    partes = []
    fontes = []
    for h in hits:
        partes.append(f"**{h['titulo']}** ({h['fonte']}):\n{h['texto']}")
        fontes.append({"id": h["id"], "titulo": h["titulo"], "fonte": h["fonte"], "score": round(h["score"], 3)})

    resposta = (
        f"Com base nas normas indexadas para a pergunta «{query}»:\n\n"
        + "\n\n".join(partes)
    )
    if contexto_dados:
        resposta += (
            "\n\n---\n**Contexto operacional do MT (dados do sistema):**\n"
            + contexto_dados
            + "\n\n_Validar com a equipe CIEVS antes de comunicação oficial._"
        )
    else:
        resposta += "\n\n_Validar com a equipe CIEVS antes de comunicação oficial._"

    return {
        "modo": "offline",
        "pergunta": query,
        "resposta": resposta,
        "fontes": fontes,
        "scores": [f["score"] for f in fontes],
    }


def _openai_enrich(prompt: str) -> str | None:
    """Chamada opcional LLM (OpenAI ou Gemini OpenAI-compatible)."""
    try:
        from meningites_env import load_meningites_env
        load_meningites_env()
    except Exception:
        pass

    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("MENINGITES_OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    if not api_key:
        return None

    url = (
        os.environ.get("LLM_API_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1/chat/completions"
    )
    model = (
        os.environ.get("LLM_MODEL")
        or os.environ.get("GEMINI_MODEL")
        or os.environ.get("MENINGITES_OPENAI_MODEL")
        or "gpt-4o-mini"
    )
    # Gemini 2.0-flash foi descontinuado na API; mapear para modelo atual.
    if model.strip().lower() in {"gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"}:
        model = "gemini-2.5-flash"

    try:
        import urllib.request

        body = json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é assistente do CIEVS-MT para vigilância de meningites. "
                        "Responda em português do Brasil, de forma técnica e objetiva. "
                        "Cite a norma quando houver. Não invente números. "
                        "Se o contexto for insuficiente, diga o que falta. "
                        "Sempre remarque que a validação humana é obrigatória."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM indisponível: {e}]"


def answer(query: str, contexto_dados: str = "", use_llm: bool = True) -> dict:
    base = answer_offline(query, contexto_dados=contexto_dados)
    if not use_llm:
        return base
    hits = retrieve(query, top_k=4)
    fontes_txt = "\n\n".join(f"- {h['titulo']} ({h['fonte']}): {h['texto']}" for h in hits)
    prompt = (
        f"Pergunta da vigilância: {query}\n\n"
        f"Trechos normativos recuperados:\n{fontes_txt}\n\n"
        f"Dados operacionais do sistema (se houver):\n{contexto_dados or 'nenhum'}\n\n"
        "Elabore resposta acionável para o CIEVS, com passos e prazos quando couber."
    )
    llm = _openai_enrich(prompt)
    if llm and not llm.startswith("[LLM indisponível"):
        base["modo"] = "offline+llm"
        base["resposta_llm"] = llm
        base["resposta"] = llm + "\n\n---\n**Fontes recuperadas:**\n" + "\n".join(
            f"- {f['titulo']} — {f['fonte']}" for f in base["fontes"]
        )
    elif llm:
        base["aviso_llm"] = llm
    return base


def _read_csv(name: str) -> pd.DataFrame:
    p = OUT / name
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.DataFrame()


def build_contexto_operacional() -> str:
    lines = []
    ms = _read_csv("indicadores_ms_operacionais_v23.csv")
    if not ms.empty:
        lines.append("Indicadores MS (MT):")
        for _, r in ms.iterrows():
            if "caderno" in str(r.get("indicador", "")).lower():
                continue
            lines.append(
                f"- {r.get('indicador_rotulo')}: {fmt_num(r.get('valor_pct'))}% "
                f"(ref BR {fmt_num(r.get('referencia_brasil_2024'))}; {r.get('semaforo')})"
            )
    epi = _read_csv("painel_epi_resumo_ano_v23.csv")
    meta = _read_csv("painel_epi_meta_v23.csv")
    if not epi.empty:
        ano = int(meta.iloc[0]["ano_referencia"]) if not meta.empty else int(epi["ano_evento_v17"].max())
        row = epi[epi["ano_evento_v17"] == ano]
        if row.empty:
            row = epi.tail(1)
        r = row.iloc[0]
        lines.append(
            f"Epidemiologia {int(r['ano_evento_v17'])}: confirmados={fmt_num(r.get('confirmados'),0)}; "
            f"incidência={fmt_num(r.get('incidencia_100mil'))}/100 mil; "
            f"letalidade={fmt_num(r.get('letalidade_pct'))}%; "
            f"óbitos={fmt_num(r.get('obitos_meningite'),0)}"
        )
    resumo = _read_csv("alertas_inteligentes_resumo_v23.csv")
    if not resumo.empty:
        top = resumo.head(5)
        lines.append("Principais alertas: " + "; ".join(
            f"{r.get('tipo_alerta')} ({r.get('severidade')}) n={fmt_num(r.get('n'),0)}" for _, r in top.iterrows()
        ))
    fila = _read_csv("alertas_inteligentes_fila_cievs_v23.csv")
    if not fila.empty:
        lines.append(f"Fila CIEVS: {len(fila)} itens prioritários.")
    return "\n".join(lines)


def narrativa_boletim() -> str:
    ctx = build_contexto_operacional()
    ms = _read_csv("indicadores_ms_operacionais_v23.csv")
    pontos_fortes, pontos_atencao = [], []
    if not ms.empty:
        for _, r in ms.iterrows():
            if "caderno" in str(r.get("indicador", "")).lower():
                continue
            lab = str(r.get("indicador_rotulo", ""))
            sem = str(r.get("semaforo", ""))
            val = fmt_num(r.get("valor_pct"))
            if sem == "Verde":
                pontos_fortes.append(f"{lab} em {val}% (acima ou alinhado à referência nacional).")
            elif sem in {"Vermelho", "Amarelo"}:
                pontos_atencao.append(f"{lab} em {val}% ({sem.lower()} vs referência Brasil).")

    hits_enc = retrieve("encerramento 60 dias oportunidade investigação", top_k=2)
    hits_q = retrieve("quimioprofilaxia doença meningocócica prazo", top_k=1)

    lines = [
        "# Narrativa assistida — Boletim Meningites CIEVS-MT",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "**Modo:** recuperação normativa local (RAG) + síntese operacional",
        "",
        "> Texto de apoio. Revisar e validar antes de divulgação oficial.",
        "",
        "## Síntese executiva",
        "",
    ]

    if pontos_fortes:
        lines.append("**Pontos favoráveis**")
        lines += [f"- {p}" for p in pontos_fortes]
        lines.append("")
    if pontos_atencao:
        lines.append("**Pontos que exigem ação**")
        lines += [f"- {p}" for p in pontos_atencao]
        lines.append("")

    lines += ["## Leitura normativa aplicada", ""]
    if hits_enc:
        h = hits_enc[0]
        lines.append(f"Conforme {h['fonte']}: {h['texto'][:420]}...")
        lines.append("")
    if hits_q:
        h = hits_q[0]
        lines.append(f"Sobre quimioprofilaxia ({h['fonte']}): {h['texto'][:420]}...")
        lines.append("")

    lines += [
        "## Prioridades sugeridas para a semana",
        "",
        "1. Reduzir backlog de **encerramento >60 dias** e **investigação >48h** (indicadores MS).",
        "2. Garantir **quimioprofilaxia oportuna** em DM/Hib e auditar quimio em etiologias não elegíveis.",
        "3. Buscar **cultura/PCR** em bacterianas confirmadas sem critério laboratorial.",
        "4. Manter vigilância de **aglomerados DM** (mesmo sorogrupo, ≤90 dias) segundo NT 97/2024.",
        "",
        "## Contexto de dados usado",
        "",
        "```",
        ctx or "(indisponível — rode o pipeline V23)",
        "```",
        "",
        "---",
        "*Gerado por 16_assistente_cievs_v23.py — CIEVS-MT*",
    ]

    # Enriquecimento LLM opcional
    llm = _openai_enrich(
        "Com base no contexto abaixo, escreva um parágrafo executivo (8–12 linhas) "
        "para abertura de boletim estadual de meningites, em tom técnico CIEVS:\n\n" + ctx
    )
    if llm and not llm.startswith("[LLM indisponível"):
        lines.insert(8, "## Parágrafo executivo (LLM)\n\n" + llm + "\n")

    return "\n".join(lines)


def export_kb():
    pd.DataFrame(DOCS).to_csv(KB_PATH, index=False, encoding="utf-8-sig")
    rows = []
    ctx = build_contexto_operacional()
    for faq in FAQ_RAPIDO:
        ans = answer_offline(faq["pergunta"], contexto_dados=ctx)
        rows.append({
            "pergunta": faq["pergunta"],
            "doc_ids": "|".join(faq["doc_ids"]),
            "resposta_resumo": ans["resposta"][:500],
            "n_fontes": len(ans["fontes"]),
        })
    pd.DataFrame(rows).to_csv(QA_PATH, index=False, encoding="utf-8-sig")


def main():
    OUT.mkdir(exist_ok=True)
    REL.mkdir(exist_ok=True)
    export_kb()
    narr = narrativa_boletim()
    NARR_PATH.write_text(narr, encoding="utf-8")
    NARR_REL.write_text(narr, encoding="utf-8")

    # Smoke test de algumas perguntas
    testes = [
        "quando fazer quimioprofilaxia?",
        "como definir surto comunitário de doença meningocócica?",
        "quais indicadores o ministério da saúde monitora?",
    ]
    resultados = []
    ctx = build_contexto_operacional()
    for q in testes:
        r = answer(q, contexto_dados=ctx, use_llm=False)
        resultados.append({
            "pergunta": q,
            "n_fontes": len(r["fontes"]),
            "top_fonte": r["fontes"][0]["titulo"] if r["fontes"] else "",
            "top_score": r["scores"][0] if r["scores"] else 0,
        })
    pd.DataFrame(resultados).to_csv(OUT / "assistente_smoke_test_v23.csv", index=False, encoding="utf-8-sig")

    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "n_documentos_kb": len(DOCS),
        "llm_disponivel": bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("MENINGITES_OPENAI_API_KEY")),
        "arquivos": [str(KB_PATH.name), str(NARR_PATH.name), str(NARR_REL.name)],
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] Assistente CIEVS V23 gerado.")
    print(f"  KB: {len(DOCS)} docs | LLM: {meta['llm_disponivel']}")
    print(f"  Narrativa: {NARR_REL}")
    for r in resultados:
        print(f"  Q: {r['pergunta'][:50]}... -> {r['top_fonte']} ({r['top_score']})")


if __name__ == "__main__":
    main()
