from __future__ import annotations

from pathlib import Path
import pandas as pd


def safe_to_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df is None:
        df = pd.DataFrame()
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_executive_summary(df: pd.DataFrame, indicators: pd.DataFrame, tests: pd.DataFrame, forecasts: pd.DataFrame, outpath: Path) -> None:
    n = len(df)
    confirmed = int(df["confirmado"].sum()) if "confirmado" in df.columns else 0
    deaths = int(df["obito_meningite"].sum()) if "obito_meningite" in df.columns else 0
    hosp = int(df["hospitalizado"].sum()) if "hospitalizado" in df.columns else 0
    lethality = 100 * deaths / confirmed if confirmed else 0

    period = ""
    if "data_evento" in df.columns:
        period = f"{df['data_evento'].min().date()} a {df['data_evento'].max().date()}"

    top_tests = ""
    if tests is not None and not tests.empty and "p_value" in tests.columns:
        tt = tests.dropna(subset=["p_value"]).head(10)
        top_tests = "\n".join([f"- {r['desfecho']} ~ {r['variavel']}: p={r['p_value']:.4g}; {r.get('interpretacao','')}" for _, r in tt.iterrows()])

    models = ""
    if forecasts is not None and not forecasts.empty:
        n_models = forecasts["n_models"].max() if "n_models" in forecasts.columns else "NA"
        models = f"Ensemble gerado com até {n_models} modelos disponíveis no ambiente."

    text = f"""# Sumário executivo — Robô Meningites

## Escopo
Período analisado: {period}  
Registros analisados: {n}

## Indicadores centrais
- Casos confirmados: {confirmed}
- Internações registradas: {hosp}
- Óbitos por meningite: {deaths}
- Letalidade bruta entre confirmados: {lethality:.2f}%

## Achados estatísticos prioritários
{top_tests if top_tests else "- Não houve testes estatísticos suficientes ou o módulo ainda não foi executado."}

## Séries temporais
{models if models else "Predição não gerada ou dependente de dados insuficientes."}

## Leitura para tomada de decisão
1. Priorizar correção de duplicidades e incompletude de campos críticos antes de inferências causais.
2. Interpretar OR como associação ajustada, não causalidade direta.
3. Integrar população IBGE e shapefile municipal para incidência, mortalidade, Moran e municípios silenciosos.
4. Utilizar canal endêmico e ensemble preditivo como triagem operacional, com validação epidemiológica antes de alertas formais.
"""
    outpath.write_text(text, encoding="utf-8")
