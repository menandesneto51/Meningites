# -*- coding: utf-8 -*-
"""
11_qualidade_score_v20.py
Matriz de qualidade do banco com pontuação 0-20.
"""

import numpy as np
import pandas as pd
from meningites_v17_common import *

CRITICAL_FIELDS = [
    "DataNotificacao",
    "DataPrimeirosSintomas",
    "MunicipioResidencia",
    "CodigoMunicipioResidencia",
    "SexoPaciente",
    "IdadePaciente",
    "FaixaEtaria",
    "ClassificacaoCaso",
    "ClassificacaoMeningite",
    "EvolucaoCaso",
    "SeNMeningiditisEspecificarSorogrupo",
    "PuncaoLombar",
    "ResultadoPCRLiquor",
    "ResultadoCulturaLiquor",
    "CriterioConfirmacao",
    "DataEncerramento",
]

def score_by_threshold(value, good, moderate, higher_is_better=True):
    if pd.isna(value):
        return 0
    if higher_is_better:
        if value >= good:
            return 2
        if value >= moderate:
            return 1
        return 0
    else:
        if value <= good:
            return 2
        if value <= moderate:
            return 1
        return 0

def classify_total(total):
    if total >= 18:
        return "Excelente"
    if total >= 14:
        return "Boa"
    if total >= 10:
        return "Regular"
    if total >= 6:
        return "Ruim"
    return "Crítica"

def main():
    df = load_base_v17().copy()
    if df.empty:
        raise SystemExit("Base ausente.")

    rows = []

    # 1 Completude
    present = [c for c in CRITICAL_FIELDS if c in df.columns]
    vals = []
    for c in present:
        filled = df[c].notna() & ~df[c].astype(str).str.strip().str.lower().isin(MISSING)
        vals.append(filled.mean() * 100)
    comp = float(np.nanmean(vals)) if vals else np.nan
    rows.append({
        "criterio": "Completude",
        "indicador": comp,
        "pontuacao": score_by_threshold(comp, 95, 70, True),
        "interpretacao": f"Completude média dos campos críticos: {fmt_num(comp)}%."
    })

    # 2 Validade
    checks = []
    if "IdadePaciente" in df.columns:
        age = pd.to_numeric(df["IdadePaciente"], errors="coerce")
        checks.append((age.notna() & age.between(0, 120)).mean() * 100)
    if "SexoPaciente" in df.columns:
        sex = df["SexoPaciente"].astype(str).map(text_key)
        checks.append(sex.isin(["M", "F", "MASCULINO", "FEMININO", "IGNORADO", "I", "9", "1", "2"]).mean() * 100)
    for c in ["data_ref_v17", "data_notificacao_v17", "data_encerramento_v17"]:
        if c in df.columns:
            checks.append(pd.to_datetime(df[c], errors="coerce").notna().mean() * 100)
    val = float(np.nanmean(checks)) if checks else np.nan
    rows.append({
        "criterio": "Validade",
        "indicador": val,
        "pontuacao": score_by_threshold(val, 98, 95, True),
        "interpretacao": f"Valores válidos em regras básicas: {fmt_num(val)}%."
    })

    # 3 Consistência
    inconsist = pd.Series(False, index=df.index)
    if {"data_notificacao_v17", "data_sintomas_v17"}.issubset(df.columns):
        inconsist |= pd.to_datetime(df["data_notificacao_v17"], errors="coerce") < pd.to_datetime(df["data_sintomas_v17"], errors="coerce")
    if {"data_encerramento_v17", "data_notificacao_v17"}.issubset(df.columns):
        inconsist |= pd.to_datetime(df["data_encerramento_v17"], errors="coerce") < pd.to_datetime(df["data_notificacao_v17"], errors="coerce")
    if {"SexoPaciente", "Gestante"}.issubset(df.columns):
        sex = df["SexoPaciente"].astype(str).map(text_key)
        gest = df["Gestante"].map(simnao_bin)
        inconsist |= (sex.isin(["M", "MASCULINO", "1"]) & (gest == 1))
    inc_rate = inconsist.mean() * 100
    rows.append({
        "criterio": "Consistência",
        "indicador": 100 - inc_rate,
        "pontuacao": score_by_threshold(inc_rate, 1, 5, False),
        "interpretacao": f"Inconsistências lógicas estimadas: {fmt_num(inc_rate)}%."
    })

    # 4 Oportunidade (alinhada ao MS: investigação ≤48h + encerramento ≤60d + notificação ≤24h)
    op_parts = []
    if "lt_notificacao_investigacao_dias_v17" in df.columns:
        lt = pd.to_numeric(df["lt_notificacao_investigacao_dias_v17"], errors="coerce")
        valid = lt[(lt >= 0) & (lt < 365)]
        if len(valid):
            op_parts.append(float((valid <= 2).mean() * 100))
    if "lt_notificacao_encerramento_dias_v17" in df.columns:
        lt = pd.to_numeric(df["lt_notificacao_encerramento_dias_v17"], errors="coerce")
        valid = lt[(lt >= 0) & (lt < 800)]
        if len(valid):
            op_parts.append(float((valid <= 60).mean() * 100))
    if "lt_sintomas_notificacao_dias_v17" in df.columns:
        lt = pd.to_numeric(df["lt_sintomas_notificacao_dias_v17"], errors="coerce")
        valid = lt[(lt >= 0) & (lt < 365)]
        if len(valid):
            op_parts.append(float((valid <= 1).mean() * 100))
    timely = float(np.nanmean(op_parts)) if op_parts else np.nan
    rows.append({
        "criterio": "Oportunidade",
        "indicador": timely,
        "pontuacao": score_by_threshold(timely, 90, 70, True),
        "interpretacao": (
            f"Média dos % oportunos MS (invest.≤48h, encerr.≤60d, notif.≤24h): {fmt_num(timely)}%."
            if op_parts else "Lead times MS indisponíveis."
        ),
    })

    # 5 Duplicidade
    if "NumeroNotificacao" in df.columns:
        dup_rate = df["NumeroNotificacao"].duplicated(keep=False).mean() * 100
    else:
        keys = [c for c in ["DataNascimento", "SexoPaciente", "MunicipioResidencia", "DataPrimeirosSintomas"] if c in df.columns]
        dup_rate = df.duplicated(subset=keys, keep=False).mean() * 100 if keys else np.nan
    rows.append({
        "criterio": "Duplicidade",
        "indicador": 100 - dup_rate if pd.notna(dup_rate) else np.nan,
        "pontuacao": score_by_threshold(dup_rate, 1, 3, False),
        "interpretacao": f"Duplicidade estimada: {fmt_num(dup_rate)}%."
    })

    # 6 Acurácia (proxy)
    if "CriterioConfirmacao" in df.columns:
        acc_proxy = (df["CriterioConfirmacao"].notna() & ~df["CriterioConfirmacao"].astype(str).str.lower().isin(MISSING)).mean() * 100
    else:
        acc_proxy = np.nan
    rows.append({
        "criterio": "Acurácia",
        "indicador": acc_proxy,
        "pontuacao": 1 if pd.notna(acc_proxy) and acc_proxy >= 50 else 0,
        "interpretacao": "Proxy por critério de confirmação. Acurácia plena exige auditoria com ficha, prontuário, GAL/LACEN ou SIM."
    })

    # 7 Plausibilidade
    # Penaliza letalidade impossível, datas negativas e idades inválidas.
    plaus_bad = inconsist.copy()
    if "IdadePaciente" in df.columns:
        age = pd.to_numeric(df["IdadePaciente"], errors="coerce")
        plaus_bad |= age.notna() & ~age.between(0, 120)
    plaus = 100 - plaus_bad.mean() * 100
    rows.append({
        "criterio": "Plausibilidade",
        "indicador": plaus,
        "pontuacao": score_by_threshold(plaus, 98, 95, True),
        "interpretacao": f"Plausibilidade epidemiológica básica: {fmt_num(plaus)}%."
    })

    # 8 Representatividade
    mun_cases = df.get("codigo_municipio_v17", pd.Series(index=df.index, dtype=object)).dropna().astype(str).nunique()
    # MT tem 142 municípios na base populacional local.
    rep = mun_cases / 142 * 100 if mun_cases else np.nan
    rows.append({
        "criterio": "Representatividade",
        "indicador": rep,
        "pontuacao": score_by_threshold(rep, 90, 50, True),
        "interpretacao": f"Municípios com pelo menos um registro: {fmt_num(mun_cases,0)} de 142 ({fmt_num(rep)}%)."
    })

    # 9 Padronização
    has_codes = "codigo_municipio_v17" in df.columns and df["codigo_municipio_v17"].notna().mean() >= 0.9
    has_dates = "data_ref_v17" in df.columns and pd.to_datetime(df["data_ref_v17"], errors="coerce").notna().mean() >= 0.9
    has_class = "classificacao_agrupada_v17" in df.columns
    pad = 100 * np.mean([has_codes, has_dates, has_class])
    rows.append({
        "criterio": "Padronização",
        "indicador": pad,
        "pontuacao": score_by_threshold(pad, 95, 70, True),
        "interpretacao": "Avalia código IBGE, datas padronizadas e classificação agrupada."
    })

    # 10 Rastreabilidade
    rast_items = [
        "arquivo_origem_v17" in df.columns,
        (ROOT / "00_base_unica_meningites_v17.py").exists(),
        (OUT / "dicionario_classificacao_agrupada_v17.csv").exists(),
        (OUT / "base_unica_meningites_v17.csv").exists(),
    ]
    rast = 100 * np.mean(rast_items)
    rows.append({
        "criterio": "Rastreabilidade",
        "indicador": rast,
        "pontuacao": score_by_threshold(rast, 95, 50, True),
        "interpretacao": "Avalia fonte, script, dicionário e base versionada."
    })

    score = pd.DataFrame(rows)
    total = int(score["pontuacao"].sum())
    resumo = pd.DataFrame([{
        "pontuacao_total": total,
        "qualidade_banco": classify_total(total),
        "interpretacao": "Escala 0–20: 18–20 Excelente; 14–17 Boa; 10–13 Regular; 6–9 Ruim; 0–5 Crítica."
    }])

    score.to_csv(OUT / "qualidade_score_v20.csv", index=False, encoding="utf-8-sig")
    resumo.to_csv(OUT / "qualidade_score_resumo_v20.csv", index=False, encoding="utf-8-sig")
    print("[OK] Score de qualidade V20 gerado.")
    print(resumo.to_string(index=False))

if __name__ == "__main__":
    main()
