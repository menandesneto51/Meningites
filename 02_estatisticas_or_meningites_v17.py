# -*- coding: utf-8 -*-
"""
02_estatisticas_or_meningites_v17.py
Análises comparativas e OR com p-valor, IC95% e interpretação.
"""

import math
import numpy as np
import pandas as pd
from meningites_v17_common import *

try:
    from scipy import stats
except Exception:
    stats = None

def fisher_p(a, b, c, d):
    if stats is None:
        return np.nan
    try:
        _, p = stats.fisher_exact([[a, b], [c, d]])
        return p
    except Exception:
        return np.nan

def chi2_p(table):
    if stats is None:
        return np.nan, np.nan, np.nan
    try:
        chi, p, dof, exp = stats.chi2_contingency(table)
        n = table.sum().sum()
        r, k = table.shape
        cramer = math.sqrt((chi / n) / max(1, min(k - 1, r - 1))) if n > 0 else np.nan
        return p, chi, cramer
    except Exception:
        return np.nan, np.nan, np.nan

def or_binary(df, exposure, outcome, label=None, outcome_label=None):
    d = df[[exposure, outcome]].copy()
    d[exposure] = pd.to_numeric(d[exposure], errors="coerce")
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.dropna()
    if len(d) < 10 or d[exposure].nunique() < 2 or d[outcome].nunique() < 2:
        return None
    tab = pd.crosstab(d[exposure], d[outcome])
    a = int(tab.loc[1, 1]) if 1 in tab.index and 1 in tab.columns else 0
    b = int(tab.loc[1, 0]) if 1 in tab.index and 0 in tab.columns else 0
    c = int(tab.loc[0, 1]) if 0 in tab.index and 1 in tab.columns else 0
    e = int(tab.loc[0, 0]) if 0 in tab.index and 0 in tab.columns else 0
    aa, bb, cc, ee = map(float, [a, b, c, e])
    if min(aa, bb, cc, ee) == 0:
        aa += 0.5; bb += 0.5; cc += 0.5; ee += 0.5
    orv = (aa * ee) / (bb * cc)
    se = math.sqrt(1/aa + 1/bb + 1/cc + 1/ee)
    lcl = math.exp(math.log(orv) - 1.96 * se)
    ucl = math.exp(math.log(orv) + 1.96 * se)
    p = fisher_p(a, b, c, e)
    return {
        "variavel": exposure,
        "exposicao": label or exposure,
        "desfecho": outcome_label or outcome,
        "n_analisado": len(d),
        "eventos_expostos": a,
        "nao_eventos_expostos": b,
        "eventos_nao_expostos": c,
        "nao_eventos_nao_expostos": e,
        "or": orv,
        "ic95_inferior": lcl,
        "ic95_superior": ucl,
        "p_value": p,
        "interpretacao_estatistica": interpret_p(p),
        "relevancia_pratica": practical_or(orv),
    }

def categorical_tests(df, var, outcome):
    d = df[[var, outcome]].dropna().copy()
    if len(d) < 10 or d[var].nunique() < 2 or d[outcome].nunique() < 2:
        return None
    tab = pd.crosstab(d[var], d[outcome])
    p, chi, cv = chi2_p(tab)
    return {
        "variavel": var,
        "desfecho": outcome,
        "n": len(d),
        "categorias": int(d[var].nunique()),
        "teste": "Qui-quadrado/Fisher conforme aplicável",
        "p_value": p,
        "estatistica_chi2": chi,
        "cramers_v": cv,
        "interpretacao_estatistica": interpret_p(p),
        "relevancia_pratica": "Cramér's V <0,1 fraco; 0,1–0,3 moderado; >0,3 forte.",
    }

def main():
    df = load_base_v17()
    outcomes = {
        "obito_meningite_uniao_v23": "Óbito (SINAN∪SIM)",
        "obito_meningite_v17": "Óbito SINAN (EvolucaoCaso)",
        "obito_sim_link_v23": "Óbito SIM (linkage)",
        "hospitalizacao_v17": "Hospitalização",
        "confirmado_v17": "Confirmação"
    }

    # OR por classificação agrupada: cada categoria vs demais
    rows = []
    for outcome, out_label in outcomes.items():
        for clas in sorted(df["classificacao_agrupada_v17"].dropna().astype(str).unique()):
            temp = df.copy()
            col = f"exp_class_{text_key(clas)[:30]}"
            temp[col] = temp["classificacao_agrupada_v17"].astype(str).eq(clas).astype(int)
            res = or_binary(temp, col, outcome, label=f"Classificação agrupada: {clas}", outcome_label=out_label)
            if res: rows.append({**res, "grupo_analise": "Classificação agrupada"})

    # OR por comorbidades e sintomas
    binary_cols = [c for c in df.columns if (c.startswith("DoencasPreexistentes") or c.startswith("SinaisESintomas")) and c.endswith("_bin_v17")]
    for outcome, out_label in outcomes.items():
        for col in binary_cols:
            res = or_binary(df, col, outcome, label=col.replace("_bin_v17", ""), outcome_label=out_label)
            if res: rows.append({**res, "grupo_analise": "Comorbidades/sinais/sintomas"})

    pd.DataFrame(rows).to_csv(OUT / "odds_ratios_clinicos_classificacao_v17.csv", index=False, encoding="utf-8-sig")

    # Testes categóricos
    tests = []
    for var in ["FaixaEtaria", "SexoPaciente", "RacaPaciente", "Escolaridade", "regional_v17", "classificacao_agrupada_v17"]:
        if var in df.columns:
            for outcome in outcomes:
                res = categorical_tests(df, var, outcome)
                if res: tests.append(res)
    pd.DataFrame(tests).to_csv(OUT / "testes_comparativos_v17.csv", index=False, encoding="utf-8-sig")

    print("[OK] Estatísticas e OR V17 gerados.")

if __name__ == "__main__":
    main()
