import pandas as pd
from pathlib import Path

pastas = [
    Path("saida_meningites_2020_2025"),
    Path("saida_meningites_2010_2026"),
]

for pasta in pastas:
    print("\n" + "=" * 80)
    print(f"PASTA: {pasta}")
    print("=" * 80)

    ind_path = pasta / "indicators.csv"
    pred_path = pasta / "timeseries_forecasts.csv"
    qual_path = pasta / "quality_report.csv"
    stat_path = pasta / "statistical_tests.csv"

    if ind_path.exists():
        ind = pd.read_csv(ind_path)
        print(f"[INDICADORES] Linhas: {len(ind)}")
        for col in ["populacao", "incidencia_100mil", "mortalidade_100mil"]:
            if col in ind.columns:
                print(f"  {col}: preenchidos={ind[col].notna().sum()} | ausentes={ind[col].isna().sum()}")

        if "casos" in ind.columns:
            print(f"  Total de casos nos indicadores: {ind['casos'].sum()}")

        if "obitos" in ind.columns:
            print(f"  Total de óbitos nos indicadores: {ind['obitos'].sum()}")

    if pred_path.exists():
        pred = pd.read_csv(pred_path)
        print(f"[PREDIÇÕES] Linhas: {len(pred)}")
        if "horizon" in pred.columns:
            print(f"  Horizontes: {sorted(pred['horizon'].dropna().unique().tolist())}")
        if "n_models" in pred.columns:
            print(f"  Modelos no ensemble: {sorted(pred['n_models'].dropna().unique().tolist())}")

    if qual_path.exists():
        qual = pd.read_csv(qual_path)
        print(f"[QUALIDADE] Linhas: {len(qual)}")

    if stat_path.exists():
        stat = pd.read_csv(stat_path)
        print(f"[TESTES] Linhas: {len(stat)}")
        if "p_value" in stat.columns:
            sig = (pd.to_numeric(stat["p_value"], errors="coerce") < 0.05).sum()
            print(f"  Testes significativos p<0,05: {sig}")

print("\n[OK] Auditoria concluída.")