"""Componente Streamlit opcional do agente epidemiológico VNext."""
from __future__ import annotations

from pathlib import Path

from meningites.agent.query_service import query_agent


def render_agent_panel(st, outdir: str | Path) -> None:
    root = Path(outdir)
    context_path = root / "agente_epidemiologico_contexto_vnext.json"
    kb_path = root / "assistente_kb_docs_ms_v27.csv"

    st.subheader("Agente epidemiológico VNext")
    st.caption(
        "Modo de desenvolvimento. Usa fatos canônicos publicados e RAG local. "
        "LLM é opcional e toda saída exige revisão humana."
    )

    if not context_path.exists():
        st.warning(
            "Contexto VNext ainda não publicado. Execute o publisher VNext antes de usar este componente."
        )
        return

    scope = st.text_input(
        "Escopo",
        value="Mato Grosso",
        help="Estado, regional, município ou código municipal.",
        key="vnext_agent_scope",
    )
    question = st.text_area(
        "Pergunta",
        value="Quais são os principais sinais e pendências deste escopo?",
        key="vnext_agent_question",
    )
    mode = st.selectbox(
        "Modo",
        ["auto", "state", "regional", "municipality", "gaps", "rag"],
        index=0,
        key="vnext_agent_mode",
    )
    use_llm = st.checkbox(
        "Usar LLM opcional validado",
        value=False,
        help="Só executa se houver credencial local configurada. A resposta passa por validação pós-LLM.",
        key="vnext_agent_llm",
    )

    if st.button("Consultar agente", key="vnext_agent_submit"):
        try:
            result = query_agent(
                context_path=context_path,
                kb_path=kb_path,
                question=question,
                scope=scope,
                mode=mode,
                use_llm=use_llm,
            )
        except Exception as exc:
            st.error(f"Falha na consulta VNext: {type(exc).__name__}: {exc}")
            return

        det = result.get("deterministic")
        if det:
            st.markdown("### Resposta determinística")
            st.write(det.get("text", ""))
            if det.get("caveats"):
                with st.expander("Ressalvas"):
                    for item in det["caveats"]:
                        st.write(f"- {item}")

        rag = result.get("rag") or {}
        st.caption(f"Evidências normativas recuperadas: {rag.get('evidence_n', 0)}")
        package = rag.get("package") or {}
        evidence = package.get("normative_evidence") or []
        if evidence:
            with st.expander("Evidências normativas"):
                for item in evidence:
                    st.markdown(
                        f"**{item.get('titulo') or 'Documento'}** — {item.get('fonte') or 'fonte não informada'}"
                    )
                    st.caption(
                        f"Arquivo: {item.get('arquivo') or 'N/D'} · vigente={item.get('vigente')} · score={item.get('score')}"
                    )
                    st.write(item.get("texto") or "")

        llm = result.get("llm") or {}
        if llm.get("executed"):
            st.markdown("### Resposta LLM validada")
            llm_result = llm.get("result") or {}
            if llm_result.get("accepted"):
                st.success("Resposta passou pelos gates automáticos. Revisão humana continua obrigatória.")
                st.write(llm_result.get("response") or "")
            else:
                st.error("Resposta rejeitada pelos gates automáticos.")
                issues = llm_result.get("issues") or []
                for issue in issues:
                    st.write(f"- {issue}")

        st.info("Validação humana obrigatória antes de qualquer uso operacional ou comunicação oficial.")
