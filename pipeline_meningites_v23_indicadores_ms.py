# -*- coding: utf-8 -*-
"""
pipeline_meningites_v23_indicadores_ms.py
Orquestrador V23: mantém V22 e adiciona indicadores MS + alertas inteligentes.
"""

from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(script: str, allow_fail: bool = False):
    p = ROOT / script
    if not p.exists():
        print("[AUSENTE]", script)
        if allow_fail:
            return
        raise SystemExit(2)
    print("\n" + "=" * 90)
    print("[CMD]", sys.executable, script)
    print("=" * 90)
    proc = subprocess.run([sys.executable, script], cwd=str(ROOT))
    if proc.returncode != 0:
        if allow_fail:
            print(f"[AVISO] {script} falhou; continuando.")
        else:
            raise SystemExit(proc.returncode)


def all_steps(rebuild_base: bool = False, from_dw: bool = False):
    if from_dw:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        rebuild_base = True
    if rebuild_base:
        run("00_base_unica_meningites_v17.py")
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

    # Novos módulos V23
    run("12_indicadores_ms_operacionais_v23.py", allow_fail=False)
    run("13_alertas_inteligentes_v23.py", allow_fail=False)
    run("14_painel_epidemiologico_ms_v23.py", allow_fail=False)
    run("15_boletim_semanal_rascunho_v23.py", allow_fail=True)
    run("16_assistente_cievs_v23.py", allow_fail=True)
    run("19_dw_descobrir_e_extrair_v23.py", allow_fail=True)
    run("17_linkage_gal_lacen_sim_v23.py", allow_fail=True)
    run("20_enriquecimento_dw_fila_cievs_v23.py", allow_fail=True)
    run("21_sazonalidade_meningites_v23.py", allow_fail=True)
    run("22_nowcast_forecast_refinado_v23.py", allow_fail=True)
    run("24_nowcast_operacional_gestao_v24.py", allow_fail=True)
    run("23_alertas_personalizados_ia_v23.py", allow_fail=True)
    print("\n[OK] Pipeline V23 concluído.")


def only_v23(from_dw: bool = False):
    if from_dw:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        run("00_base_unica_meningites_v17.py", allow_fail=False)
    run("12_indicadores_ms_operacionais_v23.py", allow_fail=False)
    run("13_alertas_inteligentes_v23.py", allow_fail=False)
    run("14_painel_epidemiologico_ms_v23.py", allow_fail=False)
    run("11_qualidade_score_v20.py", allow_fail=True)
    run("15_boletim_semanal_rascunho_v23.py", allow_fail=True)
    run("16_assistente_cievs_v23.py", allow_fail=True)
    if not from_dw:
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=True)
    run("17_linkage_gal_lacen_sim_v23.py", allow_fail=True)
    run("20_enriquecimento_dw_fila_cievs_v23.py", allow_fail=True)
    run("21_sazonalidade_meningites_v23.py", allow_fail=True)
    run("22_nowcast_forecast_refinado_v23.py", allow_fail=True)
    run("24_nowcast_operacional_gestao_v24.py", allow_fail=True)
    run("23_alertas_personalizados_ia_v23.py", allow_fail=True)
    print("\n[OK] Módulos V23 (MS + alertas + sazonalidade + nowcast + digests) concluídos.")


def open_dashboard():
    # Porta dedicada — NÃO usar 8501 (costuma ser o SIS Clima-Saúde).
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


def validate():
    items = [
        "saida_meningites_v17/base_unica_meningites_v17.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_v23.csv",
        "saida_meningites_v17/indicadores_ms_operacionais_resumo_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_casos_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_surtos_nt97_v23.csv",
        "saida_meningites_v17/alertas_inteligentes_fila_cievs_v23.csv",
        "saida_meningites_v17/painel_epi_resumo_ano_v23.csv",
        "saida_meningites_v17/painel_epi_etiologia_ano_v23.csv",
        "saida_meningites_v17/painel_epi_snapshot_etiologia_v23.csv",
        "relatorios/BOLETIM_SEMANAL_MENINGITES_V23_RASCUNHO.md",
        "saida_meningites_v17/assistente_kb_documentos_v23.csv",
        "relatorios/BOLETIM_SEMANAL_MENINGITES_V23_NARRATIVA_IA.md",
        "saida_meningites_v17/linkage_prontidao_v23.csv",
        "saida_meningites_v17/linkage_proxy_interno_resumo_v23.csv",
        "relatorios/LINKAGE_GAL_LACEN_SIM_V23.md",
        "relatorios/DW_EXTRACAO_MENINGITES_V23.md",
        "saida_meningites_v17/dw_descoberta_resumo_v23.json",
        "relatorios/BASE_UNICA_FONTE_DW_V23.md",
        "saida_meningites_v17/auditoria_sinan_fonte_v23.json",
        "saida_meningites_v17/enriquecimento_dw_resumo_v23.csv",
        "saida_meningites_v17/fila_cievs_unificada_v23.csv",
        "relatorios/FILA_CIEVS_UNIFICADA_V23.md",
        "saida_meningites_v17/indicadores_gestao_semana_v24.csv",
        "saida_meningites_v17/nowcast_operacional_resumo_v24.csv",
        "relatorios/NOWCAST_OPERACIONAL_GESTAO_V24.md",
        "LEIA-ME_V23.md",
    ]
    print("\nVALIDAÇÃO V23")
    print("=" * 90)
    for i in items:
        print(("[OK]      " if (ROOT / i).exists() else "[AUSENTE] "), i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Pipeline completo V22 + V23")
    ap.add_argument("--all-open", action="store_true")
    ap.add_argument("--rebuild-base", action="store_true", help="Regenera base única antes do pipeline")
    ap.add_argument("--from-dw", action="store_true", help="Extrai DW e regenera base única (VW_SINAN_MENINGITE)")
    ap.add_argument("--only-v23", action="store_true", help="Só indicadores MS + alertas")
    ap.add_argument("--open-dashboard", action="store_true")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    if args.only_v23:
        only_v23(from_dw=args.from_dw)
        if args.open_dashboard or args.all_open:
            open_dashboard()
        return
    if args.all or args.all_open:
        all_steps(rebuild_base=args.rebuild_base, from_dw=args.from_dw)
        if args.all_open:
            open_dashboard()
        return
    if args.from_dw and not (args.all or args.all_open or args.only_v23):
        run("19_dw_descobrir_e_extrair_v23.py", allow_fail=False)
        run("00_base_unica_meningites_v17.py", allow_fail=False)
        if args.open_dashboard:
            open_dashboard()
        return
    if args.validate:
        validate()
    if args.open_dashboard:
        open_dashboard()
    if not any(vars(args).values()):
        print("Use:")
        print("  python pipeline_meningites_v23_indicadores_ms.py --from-dw")
        print("  python pipeline_meningites_v23_indicadores_ms.py --only-v23 --from-dw")
        print("  python pipeline_meningites_v23_indicadores_ms.py --only-v23 --open-dashboard")
        print("  python pipeline_meningites_v23_indicadores_ms.py --all-open")
        print("  python pipeline_meningites_v23_indicadores_ms.py --only-v23 --open-dashboard")


if __name__ == "__main__":
    main()
