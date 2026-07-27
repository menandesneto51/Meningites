# -*- coding: utf-8 -*-
"""
03_surtos_canal_endemico_meningites_v17.py
Alertas de surtos por município + semana + classificação agrupada e canal endêmico.
"""

from datetime import timedelta
import numpy as np
import pandas as pd
from meningites_v17_common import *

def classificar(row):
    score = 0; motivos = []
    casos = row.get("casos_semana", 0)
    conf = row.get("confirmados_semana", 0)
    ob = row.get("obitos_semana", 0)
    c14 = row.get("casos_14d_mesma_classificacao", 0)
    limite = row.get("limite_historico", np.nan)
    media2dp = row.get("media_mais_2dp", np.nan)
    clas = str(row.get("classificacao_agrupada_v17", ""))

    if pd.notna(limite) and casos > limite and casos >= 2:
        score += 2; motivos.append("acima do limite histórico da mesma classificação")
    if pd.notna(media2dp) and casos > media2dp and casos >= 2:
        score += 2; motivos.append("acima da média histórica + 2DP")
    if c14 >= 2:
        score += 2; motivos.append("agregado de ≥2 casos da mesma classificação em 14 dias")
    if conf >= 2:
        score += 1; motivos.append("≥2 confirmados da mesma classificação na semana")
    if ob > 0:
        score += 2; motivos.append("óbito por meningite na semana")
    if clas == "Doença meningocócica" and casos >= 1:
        score += 1; motivos.append("doença meningocócica exige resposta sensível")

    classe = "Crítico" if score >= 5 else "Alto" if score >= 3 else "Atenção" if score >= 1 else "Rotina"
    return pd.Series({"pontuacao_alerta": score, "classe_alerta": classe, "motivos": "; ".join(motivos) if motivos else "sem sinal"})

def recomendacao(row):
    clas = str(row.get("classificacao_agrupada_v17", ""))
    risco = str(row.get("classe_alerta", "Rotina"))
    if risco == "Rotina":
        return "Manter monitoramento de rotina e qualificação da completude."
    if clas == "Meningite viral/asséptica":
        return "Verificar vínculo epidemiológico, escolas/creches/unidades, oportunidade de coleta de líquor e agregados em 14 dias. Não acionar análise vacinal como explicação."
    if clas == "Doença meningocócica":
        return "Priorizar investigação imediata, contatos, quimioprofilaxia quando indicada, vacinação meningocócica, comunicação rápida à regional e confirmação laboratorial."
    if clas in ["Meningite pneumocócica", "Meningite por Hib/Hemófilo"]:
        return "Verificar estado vacinal, faixa etária, fatores de risco, oportunidade de diagnóstico, coleta laboratorial e completude dos campos vacinais."
    if clas == "Meningite tuberculosa":
        return "Investigar vínculo com TB, vulnerabilidade, contatos, oportunidade diagnóstica, BCG quando aplicável e rede assistencial."
    return "Revisar agregação territorial, duplicidades, confirmação laboratorial, oportunidade de notificação e evolução clínica."

def main():
    df = load_base_v17()
    for c in ["ano_epi_v17", "semana_epi_v17", "caso_v17", "confirmado_v17", "hospitalizacao_v17", "obito_meningite_v17"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    max_date = df["data_ref_v17"].max()
    closed_date = max_date - timedelta(days=7)
    iso = closed_date.isocalendar()
    cur_year, cur_week = int(iso.year), int(iso.week)

    weekly = df.groupby(["ano_epi_v17", "semana_epi_v17", "codigo_municipio_v17", "municipio_v17", "regional_v17", "classificacao_agrupada_v17"], dropna=False).agg(
        casos_semana=("caso_v17", "sum"),
        confirmados_semana=("confirmado_v17", "sum"),
        hospitalizacoes_semana=("hospitalizacao_v17", "sum"),
        obitos_semana=("obito_meningite_v17", "sum"),
    ).reset_index()

    hist = weekly[weekly["ano_epi_v17"] < cur_year].groupby(["semana_epi_v17", "codigo_municipio_v17", "classificacao_agrupada_v17"], dropna=False).agg(
        media_hist=("casos_semana", "mean"),
        dp_hist=("casos_semana", "std"),
        max_hist=("casos_semana", "max"),
        q95_hist=("casos_semana", lambda x: np.nanpercentile(x, 95) if len(x) else np.nan),
    ).reset_index()
    hist["dp_hist"] = hist["dp_hist"].fillna(0)
    hist["media_mais_2dp"] = hist["media_hist"] + 2 * hist["dp_hist"]
    hist["limite_historico"] = hist[["max_hist", "q95_hist", "media_mais_2dp"]].max(axis=1)

    current = weekly[(weekly["ano_epi_v17"] == cur_year) & (weekly["semana_epi_v17"] == cur_week)].copy()
    current = current.merge(hist, on=["semana_epi_v17", "codigo_municipio_v17", "classificacao_agrupada_v17"], how="left")

    recent14 = df[df["data_ref_v17"].between(max_date - timedelta(days=13), max_date)]
    c14 = recent14.groupby(["codigo_municipio_v17", "classificacao_agrupada_v17"], dropna=False).agg(
        casos_14d_mesma_classificacao=("caso_v17", "sum"),
        confirmados_14d_mesma_classificacao=("confirmado_v17", "sum"),
        obitos_14d_mesma_classificacao=("obito_meningite_v17", "sum"),
    ).reset_index()
    current = current.merge(c14, on=["codigo_municipio_v17", "classificacao_agrupada_v17"], how="left")
    for c in ["casos_14d_mesma_classificacao", "confirmados_14d_mesma_classificacao", "obitos_14d_mesma_classificacao"]:
        current[c] = current[c].fillna(0)

    scored = pd.concat([current, current.apply(classificar, axis=1)], axis=1)
    scored["recomendacao_vigilancia"] = scored.apply(recomendacao, axis=1)
    ordem = {"Crítico": 4, "Alto": 3, "Atenção": 2, "Rotina": 1}
    scored["classe_ordem"] = scored["classe_alerta"].map(ordem).fillna(0)
    scored = scored.sort_values(["classe_ordem", "pontuacao_alerta", "casos_semana"], ascending=False)

    wk = df.groupby(["ano_epi_v17", "semana_epi_v17", "classificacao_agrupada_v17"], dropna=False).agg(casos=("caso_v17", "sum")).reset_index()
    cur = int(wk["ano_epi_v17"].max())
    hist_ch = wk[wk["ano_epi_v17"] < cur].groupby(["semana_epi_v17", "classificacao_agrupada_v17"])["casos"].agg(
        minimo="min",
        q25=lambda x: np.percentile(x, 25) if len(x) else np.nan,
        media="mean",
        mediana="median",
        q75=lambda x: np.percentile(x, 75) if len(x) else np.nan,
        maximo="max",
        p95=lambda x: np.percentile(x, 95) if len(x) else np.nan,
    ).reset_index()
    obs = wk[wk["ano_epi_v17"] == cur][["semana_epi_v17", "classificacao_agrupada_v17", "casos"]].rename(columns={"casos": "observado"})
    canal = hist_ch.merge(obs, on=["semana_epi_v17", "classificacao_agrupada_v17"], how="left")
    canal["observado"] = canal["observado"].fillna(0)
    canal["ano_observado"] = cur

    scored.to_csv(OUT / "alerta_surtos_classificacao_agrupada_v17.csv", index=False, encoding="utf-8-sig")
    scored[scored["classe_alerta"].ne("Rotina")].to_csv(OUT / "top_alertas_surtos_v17.csv", index=False, encoding="utf-8-sig")
    canal.to_csv(OUT / "canal_endemico_classificacao_agrupada_v17.csv", index=False, encoding="utf-8-sig")
    print("[OK] Surtos e canal endêmico V17 gerados.")

if __name__ == "__main__":
    main()
