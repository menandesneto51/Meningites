# -*- coding: utf-8 -*-
"""
29_procedencia_artefatos_v28.py
Selo de procedência dos artefatos do pipeline de meningites (CIEVS-MT).

Varre `saida_meningites_v17/` e `relatorios/` e grava
`saida_meningites_v17/procedencia_artefatos_v28.csv` com o contrato:

    arquivo | modulo_origem | gerado_em | idade_horas | linhas | status

Regra de `status` (limiar documentado aqui e replicado no CSV):
  - `fresco`   -> artefato existe e foi gerado há no máximo LIMIAR_FRESCO_HORAS (48h);
  - `atrasado` -> artefato existe mas é mais antigo que o limiar, OU o passo que o
                  produz falhou/foi pulado na última execução do pipeline e o
                  arquivo é anterior a essa execução (dado velho sendo servido);
  - `ausente`  -> artefato esperado pelo mapa de módulos e não encontrado em disco.

Complemento: quando `saida_meningites_v17/pipeline_execucao_v28.json` existe
(gravado pelo orquestrador), o resultado do último passo de cada módulo é
incorporado nas colunas `execucao_status`, `execucao_erro`, `execucao_duracao_s`
e `execucao_obrigatorio`, para que uma aba vazia no painel possa dizer QUAL
passo falhou em vez de apenas "rode o pipeline".

Uso:
    py -3.13 29_procedencia_artefatos_v28.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, REL

MODULO = "29_procedencia_artefatos_v28.py"

# Artefato com até 48h é considerado fresco: a rotina operacional do CIEVS é
# semanal, mas roda em dias consecutivos durante a checagem da SE corrente.
LIMIAR_FRESCO_HORAS = 48.0

EXEC_JSON = "pipeline_execucao_v28.json"
SAIDA_CSV = "procedencia_artefatos_v28.csv"

EXTENSOES = {".csv", ".json", ".md", ".parquet", ".txt", ".xlsx", ".gpkg"}

# Mapa nome-de-arquivo -> módulo que o produz. Serve para (a) detectar artefato
# ausente e (b) inferir a origem quando o próprio arquivo não traz a coluna
# `modulo_origem`.
MAPA_ARTEFATOS: dict[str, str] = {
    # 00 — base única
    "base_unica_meningites_v17.csv": "00_base_unica_meningites_v17.py",
    "base_unica_meningites_v17.parquet": "00_base_unica_meningites_v17.py",
    "serie_semanal_v17.csv": "00_base_unica_meningites_v17.py",
    "serie_diaria_v17.csv": "00_base_unica_meningites_v17.py",
    "serie_semanal_classificacao_agrupada_v17.csv": "00_base_unica_meningites_v17.py",
    "indicadores_municipio_ano_v17.csv": "00_base_unica_meningites_v17.py",
    "indicadores_municipio_ano_classificacao_agrupada_v17.csv": "00_base_unica_meningites_v17.py",
    "dicionario_classificacao_agrupada_v17.csv": "00_base_unica_meningites_v17.py",
    "auditoria_sinan_fonte_v23.json": "00_base_unica_meningites_v17.py",
    # 01 — KPIs semanais
    "kpis_semanais_v17.csv": "01_kpis_semanais_meningites_v17.py",
    "resumo_semanal_v17.csv": "01_kpis_semanais_meningites_v17.py",
    # 02 — odds ratio
    "odds_ratios_clinicos_classificacao_v17.csv": "02_estatisticas_or_meningites_v17.py",
    "testes_comparativos_v17.csv": "02_estatisticas_or_meningites_v17.py",
    "odds_classificacao_desfechos_v20.csv": "02b_odds_classificacao_desfechos_v20.py",
    "odds_ratio_clinico_socio_comorb_v21.csv": "02c_odds_clinico_socio_comorb_v21.py",
    # 03 — canal endêmico
    "canal_endemico_classificacao_agrupada_v17.csv": "03_surtos_canal_endemico_meningites_v17.py",
    "alerta_surtos_classificacao_agrupada_v17.csv": "03_surtos_canal_endemico_meningites_v17.py",
    "top_alertas_surtos_v17.csv": "03_surtos_canal_endemico_meningites_v17.py",
    # 04 — nowcast/forecast clássico
    "nowcasting_v17.csv": "04_nowcasting_forecasting_meningites_v17.py",
    "forecasting_7_15_30_45_v17.csv": "04_nowcasting_forecasting_meningites_v17.py",
    "forecasting_resumo_v17.csv": "04_nowcasting_forecasting_meningites_v17.py",
    "nowcasting_desfechos_v21.csv": "04b_nowcasting_desfechos_v21.py",
    # 05 — geoespacial
    "moran_global_v17.csv": "05_geoespacial_moran_distancia_laboratorio_v20.py",
    "lisa_clusters_v17.csv": "05_geoespacial_moran_distancia_laboratorio_v20.py",
    "geoespacial_laboratorio_distancia_v20.csv": "05_geoespacial_moran_distancia_laboratorio_v20.py",
    "correlacao_distancia_laboratorio_v20.csv": "05_geoespacial_moran_distancia_laboratorio_v20.py",
    "ranking_risco_territorial_v17.csv": "05_geoespacial_moran_distancia_laboratorio_v20.py",
    # 06 — série ambiental do agravo
    "correlacao_clima_casos_v17.csv": "06_clima_casos_meningites_v17.py",
    "correlacao_clima_desfechos_top_v17.csv": "06_clima_casos_meningites_v17.py",
    # 07 — laboratório
    "indicadores_laboratoriais_metodos_v20.csv": "07_laboratorio_qualidade_meningites_v20.py",
    "indicadores_laboratoriais_classificacao_v20.csv": "07_laboratorio_qualidade_meningites_v20.py",
    "laboratorio_kpis_v20.csv": "07_laboratorio_qualidade_meningites_v20.py",
    "criterio_confirmacao_v20.csv": "07_laboratorio_qualidade_meningites_v20.py",
    # 08 — vacina/etiologia
    "efetividade_vacinal_etiologia_coerente_v17.csv": "08_vacina_etiologia_or_meningites_v17.py",
    "mapa_vacina_etiologia_v17.csv": "08_vacina_etiologia_or_meningites_v17.py",
    # 10/11 — comorbidades e qualidade
    "associacoes_comorbidades_quiquadrado_v18.csv": "10_comorbidades_associacoes_v18.py",
    "associacoes_comorbidades_detalhe_v18.csv": "10_comorbidades_associacoes_v18.py",
    "qualidade_score_v20.csv": "11_qualidade_score_v20.py",
    "qualidade_score_resumo_v20.csv": "11_qualidade_score_v20.py",
    # 12 — indicadores MS (cópia canônica intocada)
    "indicadores_ms_operacionais_base_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    "indicadores_ms_operacionais_resumo_base_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    "indicadores_ms_operacionais_ano_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    "indicadores_ms_operacionais_regional_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    "indicadores_ms_operacionais_municipio_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    # arquivos servidos ao painel: escritos por 12 e sobrescritos por 26.
    # A origem real vem da coluna `modulo_origem` dentro do próprio CSV.
    "indicadores_ms_operacionais_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    "indicadores_ms_operacionais_resumo_v23.csv": "12_indicadores_ms_operacionais_v23.py",
    # 13 — alertas inteligentes
    "alertas_inteligentes_casos_v23.csv": "13_alertas_inteligentes_v23.py",
    "alertas_inteligentes_resumo_v23.csv": "13_alertas_inteligentes_v23.py",
    "alertas_inteligentes_surtos_nt154_v23.csv": "13_alertas_inteligentes_v23.py",
    "alertas_inteligentes_surtos_nt97_v23.csv": "13_alertas_inteligentes_v23.py",
    # 14 — painel epidemiológico
    "painel_epi_resumo_ano_v23.csv": "14_painel_epidemiologico_ms_v23.py",
    "painel_epi_etiologia_ano_v23.csv": "14_painel_epidemiologico_ms_v23.py",
    "painel_epi_snapshot_etiologia_v23.csv": "14_painel_epidemiologico_ms_v23.py",
    "painel_epi_municipio_ano_v23.csv": "14_painel_epidemiologico_ms_v23.py",
    "painel_epi_meta_v23.csv": "14_painel_epidemiologico_ms_v23.py",
    # 15/16/27 — boletim, assistente e RAG
    "boletim_semanal_rascunho_v23.md": "15_boletim_semanal_rascunho_v23.py",
    "assistente_kb_documentos_v23.csv": "16_assistente_cievs_v23.py",
    "assistente_meta_v23.json": "16_assistente_cievs_v23.py",
    "assistente_kb_docs_ms_v27.csv": "27_ingestao_docs_ms_rag_v27.py",
    "assistente_kb_docs_ms_meta_v27.json": "27_ingestao_docs_ms_rag_v27.py",
    # 17 — linkage
    "linkage_matches_gal_v23.csv": "17_linkage_gal_lacen_sim_v23.py",
    "linkage_matches_sim_v23.csv": "17_linkage_gal_lacen_sim_v23.py",
    "linkage_matches_todos_v23.csv": "17_linkage_gal_lacen_sim_v23.py",
    "linkage_prontidao_v23.csv": "17_linkage_gal_lacen_sim_v23.py",
    "linkage_proxy_interno_resumo_v23.csv": "17_linkage_gal_lacen_sim_v23.py",
    # 19 — descoberta DW
    "dw_descoberta_resumo_v23.json": "19_dw_descobrir_e_extrair_v23.py",
    "dw_objetos_descobertos_v23.csv": "19_dw_descobrir_e_extrair_v23.py",
    # 20 — enriquecimento DW / fila CIEVS / mortalidade SIM
    "enriquecimento_casos_dw_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "enriquecimento_dw_resumo_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "alertas_linkage_dw_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "alertas_qualidade_sinan_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "fila_cievs_unificada_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "alertas_inteligentes_fila_cievs_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "desfechos_mortalidade_sim_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    "mortalidade_sinan_sim_resumo_v23.csv": "20_enriquecimento_dw_fila_cievs_v23.py",
    # 21/22 — sazonalidade e nowcast refinado
    "sazonalidade_resumo_v23.csv": "21_sazonalidade_meningites_v23.py",
    "sazonalidade_indice_mensal_v23.csv": "21_sazonalidade_meningites_v23.py",
    "sazonalidade_indice_regional_v23.csv": "21_sazonalidade_meningites_v23.py",
    "nowcast_forecast_resumo_v23.csv": "22_nowcast_forecast_refinado_v23.py",
    "forecasting_semanal_ensemble_v23.csv": "22_nowcast_forecast_refinado_v23.py",
    "nowcast_serie_semanal_casos_v23.csv": "22_nowcast_forecast_refinado_v23.py",
    # 23 — alertas personalizados
    "alertas_personalizados_indice_v23.csv": "23_alertas_personalizados_ia_v23.py",
    "alertas_personalizados_resumo_v23.csv": "23_alertas_personalizados_ia_v23.py",
    # 24 — nowcast operacional / gestão
    "indicadores_gestao_semana_v24.csv": "24_nowcast_operacional_gestao_v24.py",
    "nowcast_operacional_resumo_v24.csv": "24_nowcast_operacional_gestao_v24.py",
    "nowcasting_operacional_v24.csv": "24_nowcast_operacional_gestao_v24.py",
    "forecasting_operacional_v24.csv": "24_nowcast_operacional_gestao_v24.py",
    "nowcast_regionais_ranking_v24.csv": "24_nowcast_operacional_gestao_v24.py",
    # 26 — indicadores operacionais avançados (NT 154/2024)
    "indicadores_ms_operacionais_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "indicadores_ms_operacionais_resumo_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "backlog_operacional_resumo_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "backlog_operacional_regional_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "linkage_completude_kpis_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "sorogrupos_dm_tendencia_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "sorogrupos_dm_alertas_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "score_risco_municipal_nt154_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "score_risco_municipal_nt97_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "indicadores_pl_lab_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "indicadores_vacina_elegiveis_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "gravidade_letalidade_se_corrente_v25.csv": "26_indicadores_ops_avancados_v25.py",
    "indicadores_gestao_extras_v25.csv": "26_indicadores_ops_avancados_v25.py",
    # 28 — indicadores novos
    "indicadores_novos_resumo_v28.csv": "28_indicadores_novos_v28.py",
    "oportunidade_coleta_liquor_v28.csv": "28_indicadores_novos_v28.py",
    "tempo_quimioprofilaxia_v28.csv": "28_indicadores_novos_v28.py",
    "cobertura_sorogrupo_dm_v28.csv": "28_indicadores_novos_v28.py",
    "subnotificacao_mortalidade_v28.csv": "28_indicadores_novos_v28.py",
    "oportunidade_deteccao_v28.csv": "28_indicadores_novos_v28.py",
    "completude_essenciais_regional_v28.csv": "28_indicadores_novos_v28.py",
    "completude_essenciais_municipio_v28.csv": "28_indicadores_novos_v28.py",
    "contatos_por_caso_dm_v28.csv": "28_indicadores_novos_v28.py",
    "casos_sem_denominador_populacional_v28.csv": "28_indicadores_novos_v28.py",
    "letalidade_padronizada_idade_v28.csv": "28_indicadores_novos_v28.py",
    "letalidade_populacao_padrao_v28.csv": "28_indicadores_novos_v28.py",
    "aglomerado_espaco_temporal_v28.csv": "28_indicadores_novos_v28.py",
    # 29 — este selo de procedência
    SAIDA_CSV: MODULO,
    EXEC_JSON: "pipeline_meningites_v23_indicadores_ms.py",
}

# Relatórios em markdown acompanhados (pasta relatorios/)
MAPA_RELATORIOS: dict[str, str] = {
    "BOLETIM_SEMANAL_MENINGITES_V23_RASCUNHO.md": "15_boletim_semanal_rascunho_v23.py",
    "BOLETIM_CIEVS_MENINGITES_ENVIO_V25.md": "26_indicadores_ops_avancados_v25.py",
    "FILA_CIEVS_UNIFICADA_V23.md": "20_enriquecimento_dw_fila_cievs_v23.py",
    "LINKAGE_GAL_LACEN_SIM_V23.md": "17_linkage_gal_lacen_sim_v23.py",
    "NOWCAST_OPERACIONAL_GESTAO_V24.md": "24_nowcast_operacional_gestao_v24.py",
    "INDICADORES_NOVOS_V28.md": "28_indicadores_novos_v28.py",
}


def _contar_linhas(path: Path) -> float:
    """Linhas de dados (CSV sem cabeçalho) ou linhas de texto; NaN se não aplicável."""
    suf = path.suffix.lower()
    if suf not in {".csv", ".md", ".txt"}:
        return float("nan")
    try:
        total = 0
        with path.open("rb") as fh:
            for bloco in iter(lambda: fh.read(1 << 20), b""):
                total += bloco.count(b"\n")
        if suf == ".csv":
            return float(max(total - 1, 0))
        return float(total)
    except Exception:
        return float("nan")


def _origem_declarada(path: Path) -> str:
    """Lê a coluna `modulo_origem` do próprio CSV, quando existir."""
    # O CSV deste módulo tem uma coluna `modulo_origem` que descreve OUTROS
    # arquivos; ler a si mesmo devolveria a origem da primeira linha.
    if path.suffix.lower() != ".csv" or path.name == SAIDA_CSV:
        return ""
    try:
        head = pd.read_csv(path, nrows=1, encoding="utf-8-sig")
    except Exception:
        return ""
    if "modulo_origem" not in head.columns or head.empty:
        return ""
    val = head["modulo_origem"].iloc[0]
    return "" if pd.isna(val) else str(val).strip()


def _gerado_em_declarado(path: Path) -> pd.Timestamp | None:
    if path.suffix.lower() != ".csv" or path.name == SAIDA_CSV:
        return None
    try:
        head = pd.read_csv(path, nrows=1, encoding="utf-8-sig")
    except Exception:
        return None
    if "gerado_em" not in head.columns or head.empty:
        return None
    ts = pd.to_datetime(head["gerado_em"].iloc[0], errors="coerce")
    return None if pd.isna(ts) else ts


def carregar_execucao() -> tuple[dict[str, dict], pd.Timestamp | None]:
    """Último resultado por script + horário de início do pipeline."""
    path = OUT / EXEC_JSON
    if not path.exists():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, None
    por_script: dict[str, dict] = {}
    for passo in data.get("passos", []):
        script = str(passo.get("script", "")).strip()
        if script:
            por_script[script] = passo
    inicio = pd.to_datetime(data.get("inicio"), errors="coerce")
    return por_script, (None if pd.isna(inicio) else inicio)


def _inventario() -> list[tuple[str, Path, str]]:
    """(rótulo do arquivo, caminho, módulo esperado) — esperados + presentes."""
    itens: dict[str, tuple[Path, str]] = {}

    for nome, modulo in MAPA_ARTEFATOS.items():
        itens[nome] = (OUT / nome, modulo)
    for nome, modulo in MAPA_RELATORIOS.items():
        itens[f"relatorios/{nome}"] = (REL / nome, modulo)

    for pasta, prefixo in ((OUT, ""), (REL, "relatorios/")):
        if not pasta.exists():
            continue
        for p in sorted(pasta.iterdir()):
            if not p.is_file() or p.suffix.lower() not in EXTENSOES:
                continue
            rotulo = f"{prefixo}{p.name}"
            if rotulo not in itens:
                itens[rotulo] = (p, "")

    return [(rotulo, caminho, modulo) for rotulo, (caminho, modulo) in sorted(itens.items())]


def montar_procedencia(agora: datetime | None = None) -> pd.DataFrame:
    agora_ts = pd.Timestamp(agora or datetime.now())
    execucao, inicio_run = carregar_execucao()

    linhas_out = []
    for rotulo, caminho, modulo_esperado in _inventario():
        existe = caminho.exists()
        modulo = ""
        gerado_em = ""
        idade_h = float("nan")
        n_linhas = float("nan")
        status = "ausente"
        ts = None

        if existe:
            modulo = _origem_declarada(caminho) or modulo_esperado
            ts = _gerado_em_declarado(caminho)
            if ts is None:
                ts = pd.Timestamp(datetime.fromtimestamp(caminho.stat().st_mtime))
            gerado_em = ts.isoformat(timespec="seconds")
            idade_h = round((agora_ts - ts).total_seconds() / 3600.0, 2)
            n_linhas = _contar_linhas(caminho)
            status = "fresco" if idade_h <= LIMIAR_FRESCO_HORAS else "atrasado"
        else:
            modulo = modulo_esperado

        passo = execucao.get(modulo, {})
        exec_status = str(passo.get("status", "")) if passo else ""
        exec_erro = str(passo.get("erro", "") or "") if passo else ""

        # Passo quebrado na última execução e artefato anterior a ela = dado velho
        if (
            existe
            and exec_status in {"falhou", "pulado"}
            and inicio_run is not None
            and ts is not None
            and ts < inicio_run
        ):
            status = "atrasado"

        linhas_out.append({
            "arquivo": rotulo,
            "modulo_origem": modulo or "desconhecido",
            "gerado_em": gerado_em,
            "idade_horas": idade_h,
            "linhas": n_linhas,
            "status": status,
            "execucao_status": exec_status,
            "execucao_obrigatorio": bool(passo.get("obrigatorio")) if passo else "",
            "execucao_duracao_s": passo.get("duracao_s", "") if passo else "",
            "execucao_erro": exec_erro[:300],
            "limiar_fresco_horas": LIMIAR_FRESCO_HORAS,
            "verificado_em": agora_ts.isoformat(timespec="seconds"),
        })

    return pd.DataFrame(linhas_out)


def main():
    df = montar_procedencia()
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / SAIDA_CSV, index=False, encoding="utf-8-sig")

    contagem = df["status"].value_counts().to_dict()
    print("[OK] Selo de procedência dos artefatos V28 gerado.")
    print(f"     Arquivo: {OUT / SAIDA_CSV}")
    print(f"     Limiar de frescor: {LIMIAR_FRESCO_HORAS:.0f}h")
    print(
        "     fresco={} · atrasado={} · ausente={}".format(
            contagem.get("fresco", 0), contagem.get("atrasado", 0), contagem.get("ausente", 0)
        )
    )
    problemas = df[df["status"].isin(["atrasado", "ausente"])]
    if not problemas.empty:
        print(problemas[["arquivo", "modulo_origem", "status", "idade_horas", "execucao_status"]].head(25).to_string(index=False))


if __name__ == "__main__":
    main()
