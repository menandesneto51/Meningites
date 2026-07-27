# -*- coding: utf-8 -*-
"""
interpretacoes_painel_v26.py
Guias de leitura + narrativas offline (RAG/LLM opcional) para todas as abas do painel.
Padrão alinhado a Comorbidades / Clima×casos / OR.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd


def _fmt(x, nd: int = 1) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        if pd.isna(x):
            return "—"
        if isinstance(x, (int, np.integer)) or (isinstance(x, float) and float(x).is_integer() and nd == 0):
            return f"{int(float(x)):,}".replace(",", ".")
        return f"{float(x):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)


def guide_card(titulo: str, bullets: list[str]) -> str:
    body = "<br/>".join(f"• {b}" for b in bullets)
    return f'<div class="guide-card"><b>{titulo}</b><br/><br/>{body}</div>'


def enrich_assistente(base_txt: str, pergunta: str, contexto: str, use_llm: bool = False) -> str:
    """Anexa RAG/LLM se o assistente estiver disponível; senão devolve o texto base."""
    try:
        try:
            from meningites_env import load_meningites_env
            load_meningites_env()
        except Exception:
            pass
        assist = __import__("16_assistente_cievs_v23")
        ans = assist.answer(pergunta, contexto_dados=contexto[:4000], use_llm=use_llm)
        extra = ans.get("resposta_llm") or ""
        fontes = ans.get("fontes") or []
        if use_llm and extra:
            return base_txt + "\n\n### Narrativa IA (revisar)\n\n" + extra
        if fontes:
            bloco = "\n\n### Apoio normativo recuperado\n\n"
            for f in fontes[:3]:
                bloco += f"- {f.get('titulo')} — {f.get('fonte')}\n"
            offline = ans.get("resposta") or ""
            if offline and not use_llm:
                bloco += "\n" + offline[:1600]
            return base_txt + bloco
        if ans.get("resposta") and not use_llm:
            return base_txt + "\n\n### Apoio do assistente (offline)\n\n" + str(ans.get("resposta"))[:1600]
    except Exception as e:
        return base_txt + f"\n\n_Assistente indisponível: {e}_"
    return base_txt


def _fecho(txt: str) -> str:
    return (
        txt
        + "\n\n> Texto de apoio à vigilância. **Validar com a equipe CIEVS** antes de comunicação oficial. "
        "Associação/correlação estatística ≠ causalidade."
    )


# ── Guias ────────────────────────────────────────────────────────────────────

GUIDE_EXECUTIVO = guide_card(
    "Como ler a aba Executivo",
    [
        "<b>Cards de KPI</b>: volume e tendência (semana atual vs anterior). Setas vermelhas/verdes "
        "indicam piora/melhora conforme o indicador (mais casos = pior; mais investigação ≤48h = melhor).",
        "<b>Decisão da semana (V24)</b>: nowcast corrige atraso de notificação; use junto com fila CIEVS "
        "e indicadores MS — não substituem investigação de caso/surto.",
        "<b>Backlog V25</b>: casos abertos, investigação atrasada, encerramento D45–60 e quimio pendente "
        "são fila operacional imediata.",
        "<b>Achados p&lt;0,005</b>: sinais estatísticos fortes para priorizar revisão; ainda não são causalidade.",
    ],
)

GUIDE_MS = guide_card(
    "Como ler Indicadores MS",
    [
        "<b>Semáforo</b>: compara o percentual estadual à referência Brasil (SE 1–36/2024 do Informe Meningites).",
        "<b>Verde</b> ≈ no nível ou acima da referência; <b>Amarelo/Atenção</b> e <b>Vermelho</b> pedem ação "
        "(fluxo, lab, quimio, encerramento).",
        "<b>Quatro núcleos do Informe</b>: confirmação lab PCR/cultura · investigados ≤48h · "
        "encerrados ≤60d · quimio DM ≤48h.",
        "<b>Ops V25</b> (abaixo): Hib, backlog, linkage, sorogrupos e score municipal NT 154 — "
        "complementam, não substituem, os KPIs MS.",
    ],
)

GUIDE_ALERTAS = guide_card(
    "Como ler Alertas CIEVS",
    [
        "<b>Fila prioritária</b>: itens Crítico/Alto para ação imediata (prazos MS + NT 154/2024).",
        "<b>Quimioprofilaxia</b>: ausente/atrasada em DM e Hib — contatos próximos ≤24–48h "
        "(Hib pode ir até 30 dias após exposição).",
        "<b>Vacinação pós-DIHib</b>: crianças &lt;2 anos com doença invasiva por Hib — dose/esquema complementar.",
        "<b>Surtos NT 154</b>: comunitário (≥3 DM lab+ mesmo sorogrupo ≤3 meses + incidência acima do esperado) "
        "ou institucional (≥2). Validar no território antes de comunicação.",
    ],
)

GUIDE_EPI = guide_card(
    "Como ler o Painel Epidemiológico",
    [
        "<b>Incidência / mortalidade</b>: por 100 mil habitantes (confirmados SINAN). "
        "Compare anos e municípios com cautela (população carry-forward).",
        "<b>Letalidade %</b>: óbitos / confirmados × 100 — sensível a classificação e à qualidade do encerramento.",
        "<b>Óbitos</b> neste painel seguem EvolucaoCaso SINAN (padrão Informe MS). "
        "União SINAN∪SIM aparece na aba Estatística/OR para análises de mortalidade.",
        "<b>Etiologia / faixa etária</b>: leitura estilo Informe — priorize bacterianas e DM para resposta.",
    ],
)

GUIDE_MAPAS = guide_card(
    "Como ler Mapas",
    [
        "<b>Coropléticos</b>: densidade territorial do indicador no ano filtrado (ou último disponível).",
        "<b>Score NT 154 (90d)</b>: priorização municipal exploratória (DM lab+, aglomerados, sinais de risco) — "
        "não é diagnóstico de surto sozinho.",
        "Municípios com poucos casos podem parecer extremos em incidência; cruze com denominador e qualidade.",
        "Use junto com Alertas CIEVS e canal endêmico para decidir investigação in loco.",
    ],
)

GUIDE_OR = guide_card(
    "Como ler Odds Ratio e testes",
    [
        "<b>OR &gt; 1</b>: maior chance do desfecho (risco observacional); <b>OR &lt; 1</b>: menor chance (proteção).",
        "<b>IC95% que cruza 1</b> ou p≥0,05: sem evidência clara de associação.",
        "<b>Domínios</b>: clínico, sociodemográfico e comorbidades — confundimento e seleção são frequentes.",
        "<b>Mortalidade</b>: desfecho padrão Óbito (SINAN∪SIM) aumenta sensibilidade; KPIs MS de óbito "
        "permanecem no SINAN.",
    ],
)

GUIDE_SURTOS = guide_card(
    "Como ler Surtos / canal",
    [
        "<b>NT 154 — DM</b>: surto comunitário/institucional com lab+ (cultura/PCR) e mesmo sorogrupo.",
        "<b>Demais etiologias</b>: critério operacional CIEVS (limite histórico, agregação 14d, óbito, etc.).",
        "<b>Classes</b>: Atenção → Alto → Crítico — priorize Crítico + DM + óbito.",
        "Sempre confirmar duplicidade, vínculo epidemiológico e resultado LACEN antes de declarar surto.",
    ],
)

GUIDE_SAZONAL = guide_card(
    "Como ler Sazonalidade e canal endêmico",
    [
        "<b>Índice sazonal</b>: 1,0 = média do ano; &gt;1 sugere mês/SE acima do esperado histórico.",
        "<b>Heatmap SE×ano</b>: padrões recorrentes e anos atípicos (ex.: pós-pandemia).",
        "<b>Canal endêmico</b>: observado vs média/limite superior — semanas acima do limite pedem verificação.",
        "Sazonalidade de meningites ≠ correlação climática (aba 17 é exploratória e separada).",
    ],
)

GUIDE_PROJECOES = guide_card(
    "Como ler Nowcast / Forecast",
    [
        "<b>Nowcast</b>: corrige atraso sintomas→notificação; o “observado” da SE corrente costuma estar incompleto.",
        "<b>Forecast</b>: projeção de curto prazo com incerteza (IC); MAPE alto = baixa confiança operacional.",
        "<b>Estratos</b>: ESTADUAL, DM e regionais — DM tem peso maior para resposta NT 154.",
        "Use para antecipar carga e priorizar; <b>não</b> substitui alerta de caso/surto nem investigação.",
    ],
)

GUIDE_GEO = guide_card(
    "Como ler Geoespacial",
    [
        "<b>Moran global</b>: autocorrelação espacial (I&gt;0 e p baixo → agrupamento territorial).",
        "<b>LISA</b>: clusters locais (alto-alto, baixo-baixo, outliers).",
        "<b>Score de risco</b>: ranking municipal composto — priorização, não causalidade.",
        "<b>Distância × lab</b>: associação exploratória acesso/uso laboratorial vs distância a Cuiabá.",
    ],
)

GUIDE_LAB = guide_card(
    "Como ler Laboratório",
    [
        "<b>Positividade</b>: positivos / (positivo+negativo). Inconclusivo e não realizado ficam de fora.",
        "<b>Critério de confirmação</b>: PCR/cultura elevam especificidade (meta Informe MS).",
        "<b>PL / lab pendente (V25)</b>: oportunidade de punção e resultados em aberto — fila LACEN/GAL.",
        "Baixa cobertura lab em bacterianas reduz capacidade de tipagem e resposta de controle.",
    ],
)

GUIDE_VACINA = guide_card(
    "Como ler Vacina",
    [
        "<b>Registros SINAN</b>: completude do campo vacinal ≠ cobertura populacional do PNI.",
        "<b>Elegíveis V25</b>: coerência vacina×etiologia (ex.: Hib, meningocócica) para qualidade da ficha.",
        "<b>OR vacinal</b>: observacional; confundimento por idade, acesso e gravidade é frequente.",
        "Pós-DIHib &lt;2 anos: ver NT 154 (dose adicional/esquema) — também gera alerta na fila CIEVS.",
    ],
)

GUIDE_QUALIDADE = guide_card(
    "Como ler Qualidade / linkage",
    [
        "<b>Score 0–20</b>: 18–20 Excelente · 14–17 Boa · 10–13 Regular · 6–9 Ruim · 0–5 Crítica.",
        "<b>Linkage GAL/LACEN/SIM</b>: match por score; discordancias SIM sem SINAN pedem busca ativa.",
        "<b>Inconsistências / VPP</b>: qualidade de preenchimento e valor preditivo operacional.",
        "Melhorar completude lab e datas (investigação, quimio, encerramento) melhora todos os KPIs MS.",
    ],
)

GUIDE_RELATORIO = guide_card(
    "Como ler Relatório / Base",
    [
        "Boletins são <b>rascunhos assistidos</b> — revisar números, nomes e recomendações antes do envio.",
        "A base filtrada segue os filtros da barra lateral (ano, regional, município, classificação).",
        "Narrativa IA/RAG usa a KB normativa (NT 154, Informe, Caderno SINAN) — validar clinicamente.",
        "Para atualizar dados: `ATUALIZAR_MENINGITES.bat` (local) e `--cloud` se for publicar no Streamlit Cloud.",
    ],
)

GUIDE_OPS = guide_card(
    "Como ler Operação avançada V25",
    [
        "<b>Backlog</b>: abertos, investigação atrasada, encerramento em risco, quimio pendente DM/Hib.",
        "<b>Linkage</b>: completude GAL/SIM e discordancias.",
        "<b>Sorogrupos / score NT 154</b>: tendência e priorização municipal em 90 dias.",
        "<b>PL / vacina / gravidade SE</b>: qualidade assistencial e carga da semana epidemiológica corrente.",
    ],
)


# ── Narrativas ───────────────────────────────────────────────────────────────

def narrativa_executivo(
    gest: Optional[pd.DataFrame] = None,
    backlog: Optional[pd.DataFrame] = None,
    fila: Optional[pd.DataFrame] = None,
    ms: Optional[pd.DataFrame] = None,
    use_llm: bool = False,
) -> str:
    bullets = []
    if gest is not None and not gest.empty:
        g = gest.iloc[0]
        bullets.append(
            f"- **Nowcast SE:** { _fmt(g.get('casos_nowcast_se'), 0) } "
            f"(Δ vs SE ant.: {_fmt(g.get('delta_nowcast_vs_se_anterior'))}) · "
            f"DM nowcast {_fmt(g.get('dm_nowcast_se'), 0)} · "
            f"status: {g.get('status_sazonal')} — {g.get('status_detalhe', '')}"
        )
        if g.get("acao_sugerida"):
            bullets.append(f"- **Ação sugerida (V24):** {g.get('acao_sugerida')}")
    if backlog is not None and not backlog.empty:
        r = backlog.iloc[0]
        bullets.append(
            f"- **Backlog:** abertos {_fmt(r.get('casos_abertos'), 0)} · "
            f"inv. atrasada {_fmt(r.get('investigacao_atrasada'), 0)} · "
            f"enc. &gt;60d {_fmt(r.get('encerramento_gt60'), 0)} · "
            f"quimio pend. DM/Hib {_fmt(r.get('quimio_pendente_dm_hib'), 0)}"
        )
    if fila is not None and not fila.empty:
        bullets.append(f"- **Fila CIEVS:** {_fmt(len(fila), 0)} itens prioritários (ver aba 03).")
    if ms is not None and not ms.empty and "valor_pct" in ms.columns:
        for ind in [
            "pct_investigados_48h",
            "pct_encerrados_60d",
            "pct_quimioprofilaxia_dm_48h",
            "pct_confirmacao_laboratorial_pcr_cultura",
        ]:
            row = ms[ms["indicador"].astype(str).eq(ind)]
            if row.empty:
                continue
            r = row.iloc[0]
            bullets.append(
                f"- **{r.get('indicador_rotulo')}:** {_fmt(r.get('valor_pct'))}% "
                f"(semáforo {r.get('semaforo', '—')}; ref. BR {_fmt(r.get('referencia_brasil_2024'))}%)"
            )
    if not bullets:
        bullets = ["- Sem arquivos de gestão/MS/fila nesta rodada — rode o pipeline operacional."]

    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Executivo CIEVS",
            "",
            "Síntese da semana para decisão rápida:",
            "",
            *bullets,
            "",
            "**Justificativa:** o executivo combina carga (nowcast), oportunidade MS e fila de alertas. "
            "Priorize DM/Hib com quimio pendente, investigação &gt;48h e municípios com score/alertas elevados.",
        ])
    )
    ctx = "\n".join(bullets)
    return enrich_assistente(
        txt,
        "Resuma prioridades operacionais da semana para meningites no CIEVS-MT "
        "(nowcast, indicadores MS, fila de alertas NT 154).",
        ctx,
        use_llm=use_llm,
    )


def narrativa_ms(painel: pd.DataFrame, use_llm: bool = False) -> str:
    d = painel.copy()
    bullets = []
    if not d.empty:
        for _, r in d.iterrows():
            bullets.append(
                f"- **{r.get('indicador_rotulo', r.get('indicador'))}:** "
                f"{_fmt(r.get('valor_pct'))}% · semáforo **{r.get('semaforo', '—')}** · "
                f"ref. BR {_fmt(r.get('referencia_brasil_2024'))}% · "
                f"n={_fmt(r.get('numerador'), 0)}/{_fmt(r.get('denominador'), 0)}"
            )
    vermelhos = d[d.get("semaforo", pd.Series(dtype=object)).astype(str).str.contains("Vermelho|Crítico|Alto", case=False, na=False)] if not d.empty and "semaforo" in d.columns else pd.DataFrame()
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Indicadores operacionais MS",
            "",
            f"Indicadores no painel: {_fmt(len(d), 0)}. "
            f"Com semáforo crítico/alto/vermelho: {_fmt(len(vermelhos), 0)}.",
            "",
            *bullets[:12],
            "",
            "**Justificativa:** gaps em investigação ≤48h, encerramento ≤60d, confirmação lab e quimio DM "
            "comprometem resposta a contatos (NT 154) e a qualidade do Informe. Regionais/municípios "
            "com pior % devem entrar na pauta da coordenação.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete indicadores operacionais de meningites do Informe MS "
        "(lab, investigação 48h, encerramento 60d, quimio DM) para o CIEVS.",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_alertas(
    fila: pd.DataFrame,
    resumo: pd.DataFrame,
    surtos: pd.DataFrame,
    use_llm: bool = False,
) -> str:
    bullets = []
    if not fila.empty:
        if "prioridade" in fila.columns:
            vc = fila["prioridade"].astype(str).value_counts()
            bullets.append(
                "- **Fila por prioridade:** "
                + ", ".join(f"{k}={v}" for k, v in vc.head(6).items())
            )
        if "tipo" in fila.columns:
            top = fila["tipo"].astype(str).value_counts().head(5)
            for t, n in top.items():
                bullets.append(f"- Tipo frequente na fila: **{t}** (n={n})")
    if not resumo.empty and {"tipo_alerta", "n"}.issubset(resumo.columns):
        for _, r in resumo.sort_values("n", ascending=False).head(8).iterrows():
            bullets.append(
                f"- **{r.get('tipo_alerta')}** [{r.get('severidade', '')}]: n={_fmt(r.get('n'), 0)}"
            )
    if surtos is not None and not surtos.empty:
        bullets.append(f"- **Sinais de surto NT 154:** {_fmt(len(surtos), 0)} município(s)/aglomerado(s).")
    elif surtos is not None:
        bullets.append("- Nenhum surto comunitário/institucional DM detectado pelos critérios NT 154 nesta rodada.")
    if not bullets:
        bullets = ["- Sem alertas gerados — rode o módulo 13."]

    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Alertas CIEVS",
            "",
            *bullets,
            "",
            "**Justificativa:** a fila traduz prazos do Informe e da NT 154 em ação (investigar, "
            "quimioprofilaxia, vacina pós-Hib, tipagem). Itens Crítico/Alto de DM têm precedência; "
            "sinais de surto exigem discussão nos três níveis.",
        ])
    )
    return enrich_assistente(
        txt,
        "Priorize a fila de alertas de meningites do CIEVS conforme NT 154 e Informe MS.",
        "\n".join(bullets[:10]),
        use_llm=use_llm,
    )


def narrativa_epi(resumo: pd.DataFrame, ano_ref: int, use_llm: bool = False) -> str:
    bullets = []
    if not resumo.empty:
        row = resumo[resumo["ano_evento_v17"] == ano_ref]
        if row.empty:
            row = resumo.tail(1)
        r = row.iloc[0]
        bullets.append(
            f"- **{int(r.get('ano_evento_v17'))}:** confirmados {_fmt(r.get('confirmados'), 0)}, "
            f"óbitos {_fmt(r.get('obitos_meningite'), 0)}, "
            f"incidência {_fmt(r.get('incidencia_100mil'))}/100 mil, "
            f"letalidade {_fmt(r.get('letalidade_pct'))}%"
        )
        if len(resumo) >= 2:
            prev = resumo.sort_values("ano_evento_v17").iloc[-2]
            bullets.append(
                f"- Comparativo ano anterior ({int(prev.get('ano_evento_v17'))}): "
                f"incidência {_fmt(prev.get('incidencia_100mil'))}, "
                f"letalidade {_fmt(prev.get('letalidade_pct'))}%"
            )
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Painel epidemiológico",
            "",
            f"Ano de referência do snapshot: **{ano_ref}**.",
            "",
            *bullets,
            "",
            "**Justificativa:** incidência e letalidade orientam comunicação e comparação temporal. "
            "Quedas/altas bruscas pedem checagem de população, classificação e atraso de digitação. "
            "Detalhe etiológico e territorial deve alimentar a fila CIEVS.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete incidência, mortalidade e letalidade de meningites confirmadas no estilo Informe MS.",
        "\n".join(bullets),
        use_llm=use_llm,
    )


def narrativa_mapas(ind: pd.DataFrame, score: Optional[pd.DataFrame] = None, use_llm: bool = False) -> str:
    bullets = []
    if ind is not None and not ind.empty and "casos" in ind.columns:
        top = ind.sort_values("casos", ascending=False).head(5)
        mun_col = "municipio_v17" if "municipio_v17" in top.columns else top.columns[0]
        for _, r in top.iterrows():
            extra = ""
            if "incidencia_100mil" in r.index:
                extra = f", incidência {_fmt(r.get('incidencia_100mil'))}"
            bullets.append(f"- **{r.get(mun_col)}:** {_fmt(r.get('casos'), 0)} casos{extra}")
    if score is not None and not score.empty and "score_risco_nt97_v25" in score.columns:
        s = score.sort_values("score_risco_nt97_v25", ascending=False).head(5)
        mun_col = "municipio_v17" if "municipio_v17" in s.columns else s.columns[0]
        for _, r in s.iterrows():
            bullets.append(
                f"- Score NT 154: **{r.get(mun_col)}** = {_fmt(r.get('score_risco_nt97_v25'))}"
            )
    if not bullets:
        bullets = ["- Sem indicadores municipais para resumir."]
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Mapas territoriais",
            "",
            *bullets,
            "",
            "**Justificativa:** concentração de casos/score indica onde reforçar investigação, lab e "
            "quimioprofilaxia. Incidência alta em município pequeno pode ser artefato de denominador.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete mapa de casos e score municipal de risco de meningites para priorização CIEVS.",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_or(ors21: pd.DataFrame, or_class: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    for name, df in [("domínios V21", ors21), ("classificação V20", or_class)]:
        if df is None or df.empty:
            continue
        d = df.copy()
        for c in ["or", "p_value", "ic95_inferior", "ic95_superior"]:
            if c in d.columns:
                d[c] = pd.to_numeric(d[c], errors="coerce")
        if "p_value" in d.columns:
            top = d[d["p_value"] < 0.05].sort_values("p_value").head(6)
            if top.empty:
                top = d.sort_values("p_value").head(4)
        else:
            top = d.head(4)
        for _, r in top.iterrows():
            exp = r.get("exposicao") or r.get("variavel") or r.get("classificacao_agrupada") or "?"
            bullets.append(
                f"- ({name}) **{exp}** × {r.get('desfecho', '')}: OR={_fmt(r.get('or'), 2)}, "
                f"p={_fmt(r.get('p_value'), 4)}"
            )
    if not bullets:
        bullets = ["- Sem ORs gerados nesta rodada."]
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Odds Ratio / testes",
            "",
            *bullets,
            "",
            "**Justificativa:** ORs observacionais apoiam hipóteses clínicas e de vigilância "
            "(sinais, comorbidades, classificação). Sempre ler IC95% e n; não inferir eficácia vacinal "
            "causal nem imputar culpa ao município.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete odds ratios clínicos/sociodemográficos/comorbidades em meningites para o CIEVS.",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_surtos(alerts: pd.DataFrame, nt: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if nt is not None and not nt.empty:
        bullets.append(f"- Sinais NT 154 (DM): {_fmt(len(nt), 0)}")
        for _, r in nt.head(5).iterrows():
            bullets.append(
                f"- **{r.get('municipio_v17', '')}**: {r.get('tipo_alerta', '')} "
                f"[{r.get('severidade', '')}] — n={_fmt(r.get('n_casos_90d_lab'), 0)}"
            )
    if alerts is not None and not alerts.empty and "classe_alerta" in alerts.columns:
        ativos = alerts[alerts["classe_alerta"].astype(str).isin(["Atenção", "Alto", "Crítico"])]
        vc = ativos["classe_alerta"].value_counts()
        bullets.append("- Alertas municipais (canal/agregação): " + ", ".join(f"{k}={v}" for k, v in vc.items()))
    if not bullets:
        bullets = ["- Sem surtos/alertas municipais ativos fora de Rotina."]
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Surtos",
            "",
            *bullets,
            "",
            "**Justificativa:** critérios NT 154 para DM e regras operacionais para demais etiologias. "
            "Confirmar lab, sorogrupo e vínculo antes de resposta ampliada/vacinação.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete alertas de surto de meningites e doença meningocócica conforme NT 154.",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_sazonal(resumo: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if resumo is not None and not resumo.empty:
        r = resumo.iloc[0]
        bullets.append(
            f"- Pico mensal: **{r.get('mes_pico_1_rotulo')}** (índice {_fmt(r.get('indice_pico_1'))})"
        )
        bullets.append(
            f"- SE atual { _fmt(r.get('semana_epi_atual'), 0) }: "
            f"{_fmt(r.get('casos_se_atual'), 0)} casos vs média histórica {_fmt(r.get('media_historica_se_atual'))}"
        )
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Sazonalidade",
            "",
            *(bullets if bullets else ["- Sem resumo sazonal gerado."]),
            "",
            "**Justificativa:** sazonalidade ajuda a interpretar nowcast e canal endêmico. "
            "Excedências fora do padrão histórico pedem investigação de surto/qualidade de dados.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete sazonalidade de meningites e relação com canal endêmico para o CIEVS.",
        "\n".join(bullets),
        use_llm=use_llm,
    )


def narrativa_projecoes(gest: pd.DataFrame, resumo24: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if gest is not None and not gest.empty:
        g = gest.iloc[0]
        bullets.append(
            f"- Nowcast SE {_fmt(g.get('casos_nowcast_se'), 0)} vs observado "
            f"{_fmt(g.get('casos_observados_se'), 0)} · P90 atraso {_fmt(g.get('atraso_notif_p90_dias'))}d"
        )
        bullets.append(f"- Status: {g.get('status_sazonal')} — {g.get('acao_sugerida', '')}")
    if resumo24 is not None and not resumo24.empty:
        est = resumo24[resumo24.get("estrato", pd.Series(dtype=object)).astype(str).eq("ESTADUAL")]
        if not est.empty:
            e = est.iloc[0]
            bullets.append(
                f"- Forecast SE+1: {_fmt(e.get('forecast_se1'))} · MAPE {_fmt(e.get('backtest_mape_pct'))}% "
                f"({e.get('qualidade_forecast', '')})"
            )
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Projeções",
            "",
            *(bullets if bullets else ["- Sem nowcast/forecast operacional nesta rodada."]),
            "",
            "**Justificativa:** nowcast reduz subnotificação aparente da SE corrente; forecast com MAPE "
            "alto deve ser lido só como tendência. Combine com alertas e indicadores MS.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete nowcast e forecast de meningites para decisão semanal do CIEVS.",
        "\n".join(bullets),
        use_llm=use_llm,
    )


def narrativa_geo(moran: pd.DataFrame, rank: pd.DataFrame, corr_dist: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if moran is not None and not moran.empty:
        r = moran.iloc[0]
        bullets.append(
            f"- Moran I={_fmt(r.get('I') if 'I' in moran.columns else r.get('moran_i'), 3)}, "
            f"p={_fmt(r.get('p_value') if 'p_value' in moran.columns else r.get('p'), 4)}"
        )
    if rank is not None and not rank.empty and "score_risco" in rank.columns:
        top = rank.sort_values("score_risco", ascending=False).head(5)
        mun = "municipio_v17" if "municipio_v17" in top.columns else top.columns[0]
        for _, row in top.iterrows():
            bullets.append(f"- Risco territorial: **{row.get(mun)}** score={_fmt(row.get('score_risco'))}")
    if corr_dist is not None and not corr_dist.empty:
        for _, row in corr_dist.head(4).iterrows():
            bullets.append(
                f"- Distância×lab: {row.to_dict()}"
            )
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Geoespacial",
            "",
            *(bullets if bullets else ["- Sem produtos Moran/LISA/ranking nesta rodada."]),
            "",
            "**Justificativa:** autocorrelação espacial e ranking apoiam priorização territorial. "
            "Associação distância–laboratório é exploratória (acesso, encaminhamento, gravidade).",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete Moran/LISA e risco territorial de meningites para o CIEVS-MT.",
        "\n".join(str(b) for b in bullets[:6]),
        use_llm=use_llm,
    )


def narrativa_lab(labdf: pd.DataFrame, crit: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if labdf is not None and not labdf.empty:
        top = labdf.sort_values("realizados/preenchidos", ascending=False).head(6)
        for _, r in top.iterrows():
            bullets.append(
                f"- **{r.get('metodologia')}:** realizados {_fmt(r.get('realizados/preenchidos'), 0)}, "
                f"positivos {_fmt(r.get('positivos'), 0)}, "
                f"positividade {_fmt(r.get('taxa_positividade_pct'))}%"
            )
    if crit is not None and not crit.empty:
        for _, r in crit.head(5).iterrows():
            bullets.append(f"- Critério **{r.iloc[0]}**: n={_fmt(r.iloc[1], 0)}")
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Laboratório",
            "",
            *(bullets if bullets else ["- Sem metodologias laboratoriais no recorte."]),
            "",
            "**Justificativa:** ampliar PCR/cultura em bacterianas melhora tipagem (sorogrupo/Hib) "
            "e a resposta NT 154. Positividade baixa com muitos 'não realizados' indica gap de oportunidade.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete indicadores laboratoriais de meningites (PCR, cultura, critério de confirmação).",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_vacina(vacdf: pd.DataFrame, ev: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if vacdf is not None and not vacdf.empty:
        for _, r in vacdf.sort_values("vacinados_sim", ascending=False).head(6).iterrows():
            bullets.append(
                f"- **{r.get('variavel_vacinal')}:** sim={_fmt(r.get('vacinados_sim'), 0)}, "
                f"informado={_fmt(r.get('informado'), 0)}"
            )
    if ev is not None and not ev.empty:
        d = ev.copy()
        if "status" in d.columns:
            d = d[d["status"].astype(str).str.contains("Aplicável", case=False, na=False)]
        for c in ["or", "p_value"]:
            if c in d.columns:
                d[c] = pd.to_numeric(d[c], errors="coerce")
        top = d.sort_values("p_value").head(5) if "p_value" in d.columns else d.head(5)
        for _, r in top.iterrows():
            bullets.append(
                f"- OR vacinal **{r.get('vacina')}** × {r.get('desfecho')}: "
                f"OR={_fmt(r.get('or'), 2)}, p={_fmt(r.get('p_value'), 4)}"
            )
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Vacina",
            "",
            *(bullets if bullets else ["- Sem variáveis vacinais no recorte."]),
            "",
            "**Justificativa:** campos SINAN medem qualidade de registro; ORs são observacionais. "
            "Para Hib &lt;2 anos, aplicar orientação de vacinação complementar da NT 154.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete registros vacinais e OR observacional de vacinas em meningites (NT 154 / PNI).",
        "\n".join(bullets[:8]),
        use_llm=use_llm,
    )


def narrativa_qualidade(
    resumo_q: pd.DataFrame,
    link: pd.DataFrame,
    enr: pd.DataFrame,
    use_llm: bool = False,
) -> str:
    bullets = []
    if resumo_q is not None and not resumo_q.empty:
        r = resumo_q.iloc[0]
        bullets.append(
            f"- Score qualidade: **{_fmt(r.get('pontuacao_total'), 0)}/20** ({r.get('qualidade_banco', '')})"
        )
    if enr is not None and not enr.empty:
        r = enr.iloc[0]
        bullets.append(
            f"- Linkage DW: GAL {_fmt(r.get('casos_gal'), 0)} · SIM {_fmt(r.get('casos_sim'), 0)} · "
            f"fila {_fmt(r.get('fila_unificada'), 0)}"
        )
    if link is not None and not link.empty:
        bullets.append(f"- KPIs linkage (linhas): {_fmt(len(link), 0)}")
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Qualidade e linkage",
            "",
            *(bullets if bullets else ["- Sem score/linkage nesta rodada."]),
            "",
            "**Justificativa:** qualidade do banco condiciona todos os indicadores. "
            "Busca ativa GAL/SIM reduz subnotificação de óbito e confirmação laboratorial.",
        ])
    )
    return enrich_assistente(
        txt,
        "Interprete qualidade do banco SINAN e linkage GAL/LACEN/SIM para meningites.",
        "\n".join(bullets),
        use_llm=use_llm,
    )


def narrativa_ops_v25(backlog: pd.DataFrame, score: pd.DataFrame, use_llm: bool = False) -> str:
    bullets = []
    if backlog is not None and not backlog.empty:
        r = backlog.iloc[0]
        for c in backlog.columns:
            if c == "gerado_em":
                continue
            bullets.append(f"- **{c}:** {_fmt(r.get(c), 0) if 'pct' not in c else _fmt(r.get(c))}")
    if score is not None and not score.empty and "score_risco_nt97_v25" in score.columns:
        top = score.sort_values("score_risco_nt97_v25", ascending=False).head(5)
        mun = "municipio_v17" if "municipio_v17" in top.columns else top.columns[0]
        for _, r in top.iterrows():
            bullets.append(f"- Score: **{r.get(mun)}**={_fmt(r.get('score_risco_nt97_v25'))}")
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Operação avançada V25",
            "",
            *((bullets[:14]) if bullets else ["- Sem indicadores V25."]),
            "",
            "**Justificativa:** V25 operacionaliza backlog, Hib, linkage e score NT 154 para a rotina "
            "semanal do CIEVS. Tratar como lista de trabalho, não como boletim final.",
        ])
    )
    return enrich_assistente(
        txt,
        "Priorize backlog operacional e score municipal NT 154 de meningites.",
        "\n".join(bullets[:10]),
        use_llm=use_llm,
    )


def narrativa_relatorio(use_llm: bool = False) -> str:
    txt = _fecho(
        "\n".join([
            "### Leitura assistida — Relatórios",
            "",
            "- Use o boletim V25 para envio após revisão humana.",
            "- A narrativa IA do boletim e do assistente recuperam NT 154 / Informe / Caderno SINAN.",
            "- A base filtrada reflete os filtros laterais — declare o recorte ao comunicar.",
            "",
            "**Justificativa:** produtos de comunicação precisam de validação CIEVS (números, "
            "municípios e recomendações de quimio/surto).",
        ])
    )
    return enrich_assistente(
        txt,
        "Oriente o uso de boletins e base filtrada de meningites no CIEVS-MT.",
        "Boletins rascunho + assistente normativo NT 154",
        use_llm=use_llm,
    )
