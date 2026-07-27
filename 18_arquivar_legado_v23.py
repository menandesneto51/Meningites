# -*- coding: utf-8 -*-
"""
18_arquivar_legado_v23.py
Move scripts/pacotes antigos para _arquivo_legado/ (não apaga).
Mantém o stack V23 ativo na raiz.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from meningites_v17_common import ROOT

ARQ = ROOT / "_arquivo_legado"
MANIFEST = ARQ / "MANIFESTO_ARQUIVAMENTO.md"

# Padrões a arquivar (glob na raiz)
PATTERNS = [
    # dashboards antigos / backups
    "dashboard_meningites_abas*.py",
    "dashboard_meningites_semanal*.py",
    "dashboard_meningites_final.py",
    "dashboard_meningites_v16*.py",
    "dashboard_meningites_v17*.py",
    "dashboard_meningites_v18*.py",
    "dashboard_meningites_v19*.py",
    "dashboard_meningites_v20*.py",
    "dashboard_meningites_v21*.py",
    "dashboard_efetividade_vacinal*.py",
    "dashboard_vacina_etiologia*.py",
    "dashboard_streamlit.py",
    # orquestradores / pipelines antigos
    "orquestrador_*.py",
    "pipeline_meningites_v16*.py",
    "pipeline_meningites_v17*.py",
    "pipeline_meningites_v18*.py",
    "pipeline_meningites_v19*.py",
    "pipeline_meningites_v20*.py",
    "pipeline_meningites_v21*.py",
    "pipeline_meningites_v22*.py",
    "run_pipeline.py",
    "robo_meningites_pipeline*.py",
    # scripts de correção pontuais
    "corrigir_dashboard*.py",
    "inserir_kpis_semanais*.py",
    "analise_semanal*.py",
    "gerar_*.py",
    "00_preparar_base_unica_meningites_v15.py",
    "00_preparar_base_unica_meningites_v16.py",
    "01_kpis_semanais_meningites_v16.py",
    "02_clima_casos_meningites_v16.py",
    "03_alerta_surtos_classificacao_meningites_v16.py",
    "04_indicadores_laboratoriais_meningites_v16.py",
    "05_vacina_etiologia_efetividade_meningites_v16.py",
    "06_relatorio_tecnico_meningites_v16.py",
    "07_laboratorio_qualidade_meningites_v17.py",
    "09_relatorio_tecnico_meningites_v17.py",
    "09_relatorio_tecnico_meningites_v18.py",
    "09_relatorio_tecnico_meningites_v19.py",
    # zips / bats / readmes antigos
    "pacote_meningites*.zip",
    "pacote_completo*.zip",
    "orquestrador_*.zip",
    "dashboard_meningites_v*.zip",
    "correcao_*.zip",
    "abrir_dashboard*.bat",
    "rodar_orquestrador*.bat",
    "rodar_pipeline_meningites.bat",
    "MENU_MENINGITES*.bat",
    "README_*.md",
    "requirements_dashboard_relatorio.txt",
]

# Nunca arquivar
KEEP = {
    "pipeline_meningites_v23_indicadores_ms.py",
    "dashboard_meningites_v22_refinado.py",
    "meningites_v17_common.py",
    "conhecimento_ms_meningites_v23.py",
    "00_base_unica_meningites_v17.py",
    "01_kpis_semanais_meningites_v17.py",
    "02_estatisticas_or_meningites_v17.py",
    "02b_odds_classificacao_desfechos_v20.py",
    "02c_odds_clinico_socio_comorb_v21.py",
    "03_surtos_canal_endemico_meningites_v17.py",
    "04_nowcasting_forecasting_meningites_v17.py",
    "04b_nowcasting_desfechos_v21.py",
    "05_geoespacial_moran_distancia_laboratorio_v20.py",
    "05_geoespacial_moran_meningites_v17.py",
    "06_clima_casos_meningites_v17.py",
    "07_laboratorio_qualidade_meningites_v20.py",
    "08_vacina_etiologia_or_meningites_v17.py",
    "09_relatorio_tecnico_meningites_v20.py",
    "10_comorbidades_associacoes_v18.py",
    "11_qualidade_score_v20.py",
    "12_indicadores_ms_operacionais_v23.py",
    "13_alertas_inteligentes_v23.py",
    "14_painel_epidemiologico_ms_v23.py",
    "15_boletim_semanal_rascunho_v23.py",
    "16_assistente_cievs_v23.py",
    "17_linkage_gal_lacen_sim_v23.py",
    "18_arquivar_legado_v23.py",
    "19_dw_descobrir_e_extrair_v23.py",
    "20_enriquecimento_dw_fila_cievs_v23.py",
    "21_sazonalidade_meningites_v23.py",
    "22_nowcast_forecast_refinado_v23.py",
    "23_alertas_personalizados_ia_v23.py",
    "24_nowcast_operacional_gestao_v24.py",
    "LEIA-ME_V23.md",
    "RODAR_MENINGITES_V23.bat",
}


def collect_targets() -> list[Path]:
    targets = []
    for pat in PATTERNS:
        for p in ROOT.glob(pat):
            if not p.is_file():
                continue
            if p.name in KEEP:
                continue
            if p.name.startswith("LEIA-ME") or p.name.startswith("RODAR_MENINGITES"):
                continue
            targets.append(p)
    # pacote pasta antiga
    for dname in ["pacote_meningites_v7_laboratorio"]:
        d = ROOT / dname
        if d.is_dir():
            targets.append(d)
    # únicos
    uniq = []
    seen = set()
    for t in targets:
        if t.resolve() in seen:
            continue
        seen.add(t.resolve())
        uniq.append(t)
    return sorted(uniq, key=lambda x: x.name.lower())


def main(dry_run: bool = False):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Só lista o que seria movido")
    ap.add_argument("--apply", action="store_true", help="Move de fato para _arquivo_legado/")
    args = ap.parse_args()
    dry = args.dry_run or not args.apply

    targets = collect_targets()
    ARQ.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_root = ARQ / f"lote_{stamp}"
    if not dry:
        dest_root.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Manifesto de arquivamento — {stamp}",
        "",
        f"Modo: {'DRY-RUN' if dry else 'APPLY'}",
        f"Itens: {len(targets)}",
        "",
    ]
    print(f"[INFO] {len(targets)} itens para arquivar ({'dry-run' if dry else 'apply'})")
    for t in targets:
        lines.append(f"- `{t.name}`")
        print(" ", t.name)
        if not dry:
            dest = dest_root / t.name
            if t.is_dir():
                shutil.move(str(t), str(dest))
            else:
                shutil.move(str(t), str(dest))

    text = "\n".join(lines) + "\n"
    if dry:
        (ARQ / f"DRYRUN_{stamp}.md").write_text(text, encoding="utf-8")
        print(f"[OK] Dry-run salvo em {ARQ / f'DRYRUN_{stamp}.md'}")
        print("Para aplicar: py -3.13 18_arquivar_legado_v23.py --apply")
    else:
        MANIFEST.write_text(text, encoding="utf-8")
        (dest_root / "MANIFESTO.md").write_text(text, encoding="utf-8")
        print(f"[OK] Arquivado em {dest_root}")


if __name__ == "__main__":
    main()
