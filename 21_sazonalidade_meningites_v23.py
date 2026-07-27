# -*- coding: utf-8 -*-
"""
21_sazonalidade_meningites_v23.py
Sazonalidade epidemiológica de meningites (foco MS / vigilância).

Entregas:
  - Índice sazonal mensal (estado e por etiologia agrupada)
  - Heatmap semana epidemiológica × ano
  - Picos sazonais e janela de maior risco
  - Série mensal 2007+
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, load_base_v17

MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def main():
    df = load_base_v17()
    df = df[pd.to_numeric(df.get("ano_evento_v17"), errors="coerce") >= 2007].copy()
    df["data_ref_v17"] = pd.to_datetime(df["data_ref_v17"], errors="coerce")
    df = df.dropna(subset=["data_ref_v17"])
    df["mes"] = df["data_ref_v17"].dt.month
    df["ano"] = df["data_ref_v17"].dt.year.astype(int)
    df["semana_epi"] = pd.to_numeric(df.get("semana_epi_v17"), errors="coerce")
    df["ano_epi"] = pd.to_numeric(df.get("ano_epi_v17"), errors="coerce")

    # --- Mensal estadual ---
    mensal = (
        df.groupby(["ano", "mes"], as_index=False)
        .agg(
            casos=("caso_v17", "sum"),
            confirmados=("confirmado_v17", "sum"),
            obitos=("obito_meningite_v17", "sum"),
            dm=("classificacao_agrupada_v17", lambda s: int((s == "Doença meningocócica").sum())),
        )
        .sort_values(["ano", "mes"])
    )
    mensal["mes_rotulo"] = mensal["mes"].map(MESES)
    mensal.to_csv(OUT / "sazonalidade_mensal_ano_v23.csv", index=False, encoding="utf-8-sig")

    # Índice sazonal = média do mês / média geral dos meses
    por_mes = mensal.groupby("mes", as_index=False).agg(
        media_casos=("casos", "mean"),
        mediana_casos=("casos", "median"),
        media_confirmados=("confirmados", "mean"),
        media_obitos=("obitos", "mean"),
        media_dm=("dm", "mean"),
    )
    media_geral = por_mes["media_casos"].mean()
    por_mes["indice_sazonal"] = por_mes["media_casos"] / media_geral if media_geral else np.nan
    por_mes["mes_rotulo"] = por_mes["mes"].map(MESES)
    por_mes["acima_media"] = por_mes["indice_sazonal"] > 1.0
    por_mes = por_mes.sort_values("mes")
    por_mes.to_csv(OUT / "sazonalidade_indice_mensal_v23.csv", index=False, encoding="utf-8-sig")

    # --- Por etiologia ---
    eti = (
        df.groupby(["mes", "classificacao_agrupada_v17"], as_index=False)
        .agg(casos=("caso_v17", "sum"))
    )
    tot_eti = eti.groupby("classificacao_agrupada_v17")["casos"].transform("sum")
    # média mensal relativa dentro da etiologia
    n_anos = max(df["ano"].nunique(), 1)
    eti["media_mensal"] = eti["casos"] / n_anos
    media_eti = eti.groupby("classificacao_agrupada_v17")["media_mensal"].transform("mean")
    eti["indice_sazonal"] = eti["media_mensal"] / media_eti.replace(0, np.nan)
    eti["mes_rotulo"] = eti["mes"].map(MESES)
    eti.to_csv(OUT / "sazonalidade_indice_etiologia_v23.csv", index=False, encoding="utf-8-sig")

    # --- Heatmap SE × ano ---
    heat = (
        df.dropna(subset=["semana_epi", "ano_epi"])
        .groupby(["ano_epi", "semana_epi"], as_index=False)
        .agg(casos=("caso_v17", "sum"), confirmados=("confirmado_v17", "sum"))
    )
    heat["ano_epi"] = heat["ano_epi"].astype(int)
    heat["semana_epi"] = heat["semana_epi"].astype(int)
    heat.to_csv(OUT / "sazonalidade_heatmap_semana_ano_v23.csv", index=False, encoding="utf-8-sig")

    # Perfil médio por SE (todas as temporadas)
    perfil_se = heat.groupby("semana_epi", as_index=False).agg(
        media_casos=("casos", "mean"),
        mediana_casos=("casos", "median"),
        p75_casos=("casos", lambda s: float(np.nanpercentile(s, 75))),
        p95_casos=("casos", lambda s: float(np.nanpercentile(s, 95))),
    )
    perfil_se.to_csv(OUT / "sazonalidade_perfil_semana_epi_v23.csv", index=False, encoding="utf-8-sig")

    # --- Por regional (índice mensal) ---
    reg = (
        df.groupby(["regional_v17", "mes"], as_index=False)
        .agg(casos=("caso_v17", "sum"))
    )
    reg["media_mensal"] = reg["casos"] / n_anos
    mreg = reg.groupby("regional_v17")["media_mensal"].transform("mean")
    reg["indice_sazonal"] = reg["media_mensal"] / mreg.replace(0, np.nan)
    reg["mes_rotulo"] = reg["mes"].map(MESES)
    reg.to_csv(OUT / "sazonalidade_indice_regional_v23.csv", index=False, encoding="utf-8-sig")

    # Picos
    top_meses = por_mes.sort_values("indice_sazonal", ascending=False).head(3)
    baixa = por_mes.sort_values("indice_sazonal", ascending=True).head(3)
    # SE atual vs perfil
    hoje = pd.Timestamp.today()
    se_atual = int(hoje.isocalendar().week)
    perfil_atual = perfil_se[perfil_se["semana_epi"] == se_atual]
    obs_ano = heat[heat["ano_epi"] == hoje.year]
    obs_se = obs_ano[obs_ano["semana_epi"] == se_atual]["casos"].sum() if not obs_ano.empty else np.nan

    resumo = pd.DataFrame([{
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "n_casos_base": int(len(df)),
        "anos": f"{df['ano'].min()}-{df['ano'].max()}",
        "mes_pico_1": int(top_meses.iloc[0]["mes"]) if len(top_meses) else None,
        "mes_pico_1_rotulo": top_meses.iloc[0]["mes_rotulo"] if len(top_meses) else "",
        "indice_pico_1": float(top_meses.iloc[0]["indice_sazonal"]) if len(top_meses) else np.nan,
        "mes_pico_2": int(top_meses.iloc[1]["mes"]) if len(top_meses) > 1 else None,
        "mes_pico_2_rotulo": top_meses.iloc[1]["mes_rotulo"] if len(top_meses) > 1 else "",
        "mes_baixa_1_rotulo": baixa.iloc[0]["mes_rotulo"] if len(baixa) else "",
        "semana_epi_atual": se_atual,
        "casos_se_atual": float(obs_se) if pd.notna(obs_se) else np.nan,
        "media_historica_se_atual": float(perfil_atual["media_casos"].iloc[0]) if not perfil_atual.empty else np.nan,
        "p75_historico_se_atual": float(perfil_atual["p75_casos"].iloc[0]) if not perfil_atual.empty else np.nan,
    }])
    resumo.to_csv(OUT / "sazonalidade_resumo_v23.csv", index=False, encoding="utf-8-sig")

    # Relatório
    r = resumo.iloc[0]
    acima = ""
    if pd.notna(r["casos_se_atual"]) and pd.notna(r["p75_historico_se_atual"]):
        if r["casos_se_atual"] > r["p75_historico_se_atual"]:
            acima = f"SE {se_atual} **acima do P75 histórico** ({r['casos_se_atual']:.0f} vs P75 {r['p75_historico_se_atual']:.1f})."
        else:
            acima = f"SE {se_atual} dentro do esperado histórico (obs {r['casos_se_atual']:.0f}; média {r['media_historica_se_atual']:.1f})."

    linhas = [
        "# Sazonalidade — Meningites MT V23",
        "",
        f"**Período:** {r['anos']} · **Casos:** {r['n_casos_base']} · **Gerado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Picos sazonais (índice mensal)",
        "",
        f"- Maior risco relativo: **{r['mes_pico_1_rotulo']}** (índice {r['indice_pico_1']:.2f})",
        f"- Segundo: **{r['mes_pico_2_rotulo']}**",
        f"- Menor: **{r['mes_baixa_1_rotulo']}**",
        "",
        "## Semana epidemiológica atual",
        "",
        acima or "(sem observação na SE atual)",
        "",
        "Arquivos: `sazonalidade_indice_mensal_v23.csv`, `sazonalidade_heatmap_semana_ano_v23.csv`,",
        "`sazonalidade_indice_etiologia_v23.csv`, `sazonalidade_indice_regional_v23.csv`.",
        "",
        "> Uso CIEVS: reforçar vigilância ativa e completude lab/quimio nos meses de pico;",
        "> comparar SE corrente com canal/perfil histórico antes de comunicar aumento.",
        "",
    ]
    (REL / "SAZONALIDADE_MENINGITES_V23.md").write_text("\n".join(linhas), encoding="utf-8")

    print("[OK] Sazonalidade V23 gerada.")
    print(por_mes[["mes_rotulo", "media_casos", "indice_sazonal"]].to_string(index=False))
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    main()
