# -*- coding: utf-8 -*-
"""
pipeline_meningites_v23_indicadores_ms.py
Orquestrador V23/V24: ops semanal, pesquisa completa e validação estrita.
"""

from datetime import datetime
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent

PROCEDENCIA_STEP = "29_procedencia_artefatos_v28.py"
EXEC_JSON = ROOT / "saida_meningites_v17" / "pipeline_execucao_v28.json"

# Registro da execução corrente: cada passo vira uma linha do JSON lido pelo
# módulo 29 e pelo painel, para que uma falha silenciosa fique visível.
EXECUCAO: list[dict] = []
EXEC_INICIO = datetime.now()
EXEC_ROTINA = "indefinida"


def _registrar(script: str, obrigatorio: bool, status: str, duracao_s: float, erro: str = ""):
    EXECUCAO.append({
        "ordem": len(EXECUCAO) + 1,
        "script": script,
        "obrigatorio": bool(obrigatorio),
        "status": status,
        "duracao_s": round(float(duracao_s), 2),
        "erro": erro,
        "fim": datetime.now().isoformat(timespec="seconds"),
    })


def _falhas_obrigatorias() -> list[dict]:
    return [p for p in EXECUCAO if p["obrigatorio"] and p["status"] != "ok"]


def gravar_execucao(rotina: str | None = None) -> Path:
    payload = {
        "rotina": rotina or EXEC_ROTINA,
        "inicio": EXEC_INICIO.isoformat(timespec="seconds"),
        "fim": datetime.now().isoformat(timespec="seconds"),
        "python": sys.executable,
        "passos": EXECUCAO,
        "resumo": {
            "total": len(EXECUCAO),
            "ok": sum(1 for p in EXECUCAO if p["status"] == "ok"),
            "falhou": sum(1 for p in EXECUCAO if p["status"] == "falhou"),
            "pulado": sum(1 for p in EXECUCAO if p["status"] == "pulado"),
            "obrigatorios_falhos": len(_falhas_obrigatorias()),
        },
    }
    EXEC_JSON.parent.mkdir(exist_ok=True)
    EXEC_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return EXEC_JSON


def imprimir_resumo_execucao():
    problemas = [p for p in EXECUCAO if p["status"] != "ok"]
    print("\n" + "=" * 90)
    print("RESUMO DA EXECUÇÃO DO PIPELINE")
    print("=" * 90)
    print(
        f"Passos: {len(EXECUCAO)} · ok={sum(1 for p in EXECUCAO if p['status'] == 'ok')} "
        f"· falhou={sum(1 for p in EXECUCAO if p['status'] == 'falhou')} "
        f"· pulado={sum(1 for p in EXECUCAO if p['status'] == 'pulado')}"
    )
    if not problemas:
        print("[OK] Nenhum passo com problema.")
    for p in problemas:
        marca = "OBRIGATÓRIO" if p["obrigatorio"] else "opcional"
        print(f"  [{p['status'].upper():7}] {p['script']} ({marca}) — {p['erro'] or 'sem detalhe'}")
    print(f"Registro: {EXEC_JSON}")
    print("=" * 90)


def _abortar(codigo: int):
    gravar_execucao()
    imprimir_resumo_execucao()
    raise SystemExit(codigo)


def run(script: str, allow_fail: bool = False):
    obrigatorio = not allow_fail
    p = ROOT / script
    if not p.exists():
        print("[AUSENTE]", script)
        _registrar(script, obrigatorio, "pulado", 0.0, "script não encontrado no diretório")
        if allow_fail:
            return
        _abortar(2)
    print("\n" + "=" * 90)
    print("[CMD]", sys.executable, script)
    print("=" * 90)
    t0 = time.perf_counter()
    proc = subprocess.run([sys.executable, script], cwd=str(ROOT))
    dur = time.perf_counter() - t0
    if proc.returncode != 0:
        _registrar(script, obrigatorio, "falhou", dur, f"código de saída {proc.returncode}")
        if allow_fail:
            print(f"[AVISO] {script} falhou; continuando.")
            return
        _abortar(proc.returncode)
    _registrar(script, obrigatorio, "ok", dur)


def finalizar(rotina: str):
    """Grava o JSON, roda o selo de procedência por último e imprime o resumo."""
    global EXEC_ROTINA
    EXEC_ROTINA = rotina
    gravar_execucao(rotina)
    # O 29 precisa enxergar o resultado dos demais passos, por isso roda depois
    # do JSON já existir; o próprio passo 29 é anexado ao registro em seguida.
    run(PROCEDENCIA_STEP, allow_fail=True)
    gravar_execucao(rotina)
    imprimir_resumo_execucao()
    if _falhas_obrigatorias():
        raise SystemExit(1)


def research_steps(rebuild_base: bool = False, from_dw: bool = False):
    """Pipeline completo: OR, Moran, clima, lab, vacina + V23/V24."""
    if from_dw:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        rebuild_base = True
    if rebuild_base:
        run("00_base_unica_meningites_v17.py")

    # Linkage/SIM antes dos OR de mortalidade
    hard = from_dw
    run("17_linkage_gal_lacen_sim_v23.py", allow_fail=not hard)
    run("20_enriquecimento_dw_fila_cievs_v23.py", allow_fail=not hard)

    run("01_kpis_semanais_meningites_v17.py", allow_fail=True)
    run("02_estatisticas_or_meningites_v17.py", allow_fail=True)
    run("02b_odds_classificacao_desfechos_v20.py", allow_fail=True)
    run("02c_odds_clinico_socio_comorb_v21.py", allow_fail=True)
    run("03_surtos_canal_endemico_meningites_v17.py", allow_fail=True)
    run("04_nowcasting_forecasting_meningites_v17.py", allow_fail=True)
    run("04b_nowcasting_desfechos_v21.py", allow_fail=True)
    run("05_geoespacial_moran_distancia_laboratorio_v20.py", allow_fail=True)
    run("06_clima_casos_meningites_v17.py", allow_fail=True)
    run("07_laboratorio_qualidade_meningites_v20.py", allow_fail=True)
    run("08_vacina_etiologia_or_meningites_v17.py", allow_fail=True)
    run("10_comorbidades_associacoes_v18.py", allow_fail=True)
    run("11_qualidade_score_v20.py", allow_fail=True)
    run("09_relatorio_tecnico_meningites_v20.py", allow_fail=True)
    ops_steps(
        from_dw=False,
        skip_dw_extract=True,
        skip_linkage=True,
        fail_closed=False,
        finalizar_execucao=False,
    )
    print("\n[OK] Pipeline pesquisa (--research / --all) concluído.")
    finalizar("research")


def ops_steps(
    from_dw: bool = False,
    skip_dw_extract: bool = False,
    skip_linkage: bool = False,
    fail_closed: bool = False,
    finalizar_execucao: bool = True,
):
    """Rotina operacional: MS, alertas, fila, nowcast/gestão V24."""
    if from_dw and not skip_dw_extract:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        run("00_base_unica_meningites_v17.py", allow_fail=False)

    hard = fail_closed or from_dw

    run("12_indicadores_ms_operacionais_v23.py", allow_fail=False)
    run("13_alertas_inteligentes_v23.py", allow_fail=False)
    run("14_painel_epidemiologico_ms_v23.py", allow_fail=False)
    run("11_qualidade_score_v20.py", allow_fail=True)
    run("15_boletim_semanal_rascunho_v23.py", allow_fail=True)
    run("27_ingestao_docs_ms_rag_v27.py", allow_fail=True)
    run("16_assistente_cievs_v23.py", allow_fail=True)
    if not from_dw and not skip_dw_extract:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=True)
    if not skip_linkage:
        run("17_linkage_gal_lacen_sim_v23.py", allow_fail=not hard)
        run("20_enriquecimento_dw_fila_cievs_v23.py", allow_fail=not hard)
        # Recalcula OR de mortalidade com SINAN∪SIM após enriquecimento
        run("02b_odds_classificacao_desfechos_v20.py", allow_fail=True)
        run("02c_odds_clinico_socio_comorb_v21.py", allow_fail=True)
    run("21_sazonalidade_meningites_v23.py", allow_fail=True)
    run("22_nowcast_forecast_refinado_v23.py", allow_fail=True)
    run("26_indicadores_ops_avancados_v25.py", allow_fail=True)
    run("24_nowcast_operacional_gestao_v24.py", allow_fail=False)
    run("23_alertas_personalizados_ia_v23.py", allow_fail=True)
    run("28_indicadores_novos_v28.py", allow_fail=True)
    run("30_cnes_sinasc_enriquecimento_v30.py", allow_fail=True)
    print("\n[OK] Pipeline operacional (--ops) concluído.")
    if finalizar_execucao:
        finalizar("ops")


# Compatibilidade com nomes antigos
all_steps = research_steps
only_v23 = ops_steps


def open_dashboard():
    dash = "dashboard_meningites_v22_refinado.py"
    port = "8510"
    print(f"\n[DASHBOARD] Meningites em http://localhost:{port}")
    print("            (porta 8501 é reservada ao Clima-Saúde — não misturar)")
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run", dash,
            "--server.port", port,
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(ROOT),
    )


def validate(strict: bool = True) -> int:
    """Retorna 0 se críticos ok; 1 se faltar artefato obrigatório."""
    required = [
        "saida_meningites_v17/base_unica_meningites_v17.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_v23.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_resumo_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_casos_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_surtos_nt154_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_fila_cievs_v23.csv",
        "saida_meningites_v17/painel_epi_resumo_ano_v23.csv",
        "saida_meningites_v17/painel_epi_etiologia_ano_v23.csv",
        "saida_meningites_v17/painel_epi_snapshot_etiologia_v23.csv",
        "saida_meningites_v17/fila_cievs_unificada_v23.csv",
        "saida_meningites_v17/indicadores_gestao_semana_v24.csv",
        "saida_meningites_v17/nowcast_operacional_resumo_v24.csv",
        "saida_meningites_v17/auditoria_sinan_fonte_v23.json",
        "LEIA-ME_V23.md",
    ]
    optional = [
        "relatorios/BOLETIM_SEMANAL_MENINGITES_V23_RASCUNHO.md",
        "saida_meningites_v17/assistente_kb_documentos_v23.csv",
        "relatorios/BOLETIM_SEMANAL_MENINGITES_V23_NARRATIVA_IA.md",
        "saida_meningites_v17/linkage_prontidao_v23.csv",
        "saida_meningites_v17/linkage_proxy_interno_resumo_v23.csv",
        "relatorios/LINKAGE_GAL_LACEN_SIM_V23.md",
        "relatorios/DW_EXTRACAO_MENINGITES_V23.md",
        "saida_meningites_v17/dw_descoberta_resumo_v23.json",
        "relatorios/BASE_UNICA_FONTE_DW_V23.md",
        "saida_meningites_v17/enriquecimento_dw_resumo_v23.csv",
        "relatorios/FILA_CIEVS_UNIFICADA_V23.md",
        "relatorios/NOWCAST_OPERACIONAL_GESTAO_V24.md",
        "saida_meningites_v17/sazonalidade_resumo_v23.csv",
        "saida_meningites_v17/nowcast_forecast_resumo_v23.csv",
        "saida_meningites_v17/correlacao_clima_casos_v17.csv",
        "saida_meningites_v17/moran_global_v17.csv",
        "demo_cloud/geo/MT_Municipios_simplificado.geojson",
        "saida_meningites_v17/desfechos_mortalidade_sim_v23.csv",
        "saida_meningites_v17/mortalidade_sinan_sim_resumo_v23.csv",
        "saida_meningites_v17/backlog_operacional_resumo_v25.csv",
        "saida_meningites_v17/linkage_completude_kpis_v25.csv",
        "saida_meningites_v17/score_risco_municipal_nt97_v25.csv",
        "relatorios/BOLETIM_CIEVS_MENINGITES_ENVIO_V25.md",
        # V28 — procedência/execução e nomes alinhados à NT 154/2024
        "saida_meningites_v17/pipeline_execucao_v28.json",
        "saida_meningites_v17/procedencia_artefatos_v28.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_base_v23.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_v25.csv",
        "saida_meningites_v17/score_risco_municipal_nt154_v25.csv",
        # aliases legados NT 97 mantidos enquanto o painel não migrar
        "saida_meningites_v17/alertas_inteligentes_surtos_nt97_v23.csv",
        "saida_meningites_v17/score_risco_municipal_nt97_v25.csv",
        # V30 — CNES / SINASC
        "saida_meningites_v17/cnes_perfil_unidade_notificante_v30.csv",
        "saida_meningites_v17/cnes_acesso_complexidade_regional_v30.csv",
        "relatorios/CNES_SINASC_ENRIQUECIMENTO_V30.md",
    ]
    print("\nVALIDAÇÃO OPERACIONAL V23/V24")
    print("=" * 90)
    missing_req = []
    for i in required:
        ok = (ROOT / i).exists()
        print(("[OK]      " if ok else "[AUSENTE*] "), i)
        if not ok:
            missing_req.append(i)
    print("-" * 90)
    missing_opt = []
    for i in optional:
        ok = (ROOT / i).exists()
        print(("[OK]      " if ok else "[AUSENTE]  "), i)
        if not ok:
            missing_opt.append(i)
    print("=" * 90)
    print(f"Críticos ausentes: {len(missing_req)} | Opcionais ausentes: {len(missing_opt)}")
    if missing_req and strict:
        print("[FALHA] Validação estrita — rode ATUALIZAR_MENINGITES.bat")
        return 1
    print("[OK] Validação concluída.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", action="store_true", help="Rotina operacional (MS/alertas/fila/V24)")
    ap.add_argument("--research", action="store_true", help="Pipeline completo pesquisa (OR/Moran/clima+V23)")
    ap.add_argument("--all", action="store_true", help="Alias de --research")
    ap.add_argument("--all-open", action="store_true")
    ap.add_argument("--rebuild-base", action="store_true", help="Regenera base única antes do pipeline")
    ap.add_argument("--from-dw", action="store_true", help="Extrai DW e regenera base única")
    ap.add_argument("--only-v23", action="store_true", help="Alias de --ops")
    ap.add_argument("--open-dashboard", action="store_true")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    want_ops = args.ops or args.only_v23
    want_research = args.research or args.all or args.all_open

    if want_ops and not want_research:
        ops_steps(from_dw=args.from_dw, fail_closed=args.from_dw)
        if args.open_dashboard or args.all_open:
            open_dashboard()
        return
    if want_research:
        research_steps(rebuild_base=args.rebuild_base, from_dw=args.from_dw)
        if args.all_open:
            open_dashboard()
        return
    if args.from_dw:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        run("00_base_unica_meningites_v17.py", allow_fail=False)
        finalizar("extracao_dw")
        if args.open_dashboard:
            open_dashboard()
        return
    if args.validate:
        raise SystemExit(validate(strict=True))
    if args.open_dashboard:
        open_dashboard()
        return
    print("Use:")
    print("  ATUALIZAR_MENINGITES.bat")
    print("  python pipeline_meningites_v23_indicadores_ms.py --ops --from-dw")
    print("  python pipeline_meningites_v23_indicadores_ms.py --research --from-dw")
    print("  python pipeline_meningites_v23_indicadores_ms.py --validate")


if __name__ == "__main__":
    main()
