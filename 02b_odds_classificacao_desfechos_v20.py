# -*- coding: utf-8 -*-
"""
02b_odds_classificacao_desfechos_v20.py
OR por classificação agrupada para óbito, internação e presença de comorbidades.
"""

import math
import numpy as np
import pandas as pd
from meningites_v17_common import *

try:
    from scipy import stats
except Exception:
    stats = None

COMORB_COLS = [
    "DoencasPreexistentesAIDS",
    "DoencasPreexistentesImunodepressoras",
    "DoencasPreexistentesIRA",
    "DoencasPreexistentesTuberculose",
    "DoencasPreexistentesTraumatismo",
    "DoencasPreexistentesInfeccaoHospitalar",
    "DoencasPreexistentesOutras",
]

def fisher_p(a, b, c, d):
    if stats is None:
        return np.nan
    try:
        _, p = stats.fisher_exact([[a, b], [c, d]])
        return p
    except Exception:
        return np.nan

def calc_or_binary(df, exposure_col, outcome_col, exposure_label, outcome_label):
    d = df[[exposure_col, outcome_col]].copy()
    d[exposure_col] = pd.to_numeric(d[exposure_col], errors="coerce")
    d[outcome_col] = pd.to_numeric(d[outcome_col], errors="coerce")
    d = d.dropna()
    d = d[d[exposure_col].isin([0, 1]) & d[outcome_col].isin([0, 1])]
    if len(d) < 10 or d[exposure_col].nunique() < 2 or d[outcome_col].nunique() < 2:
        return None
    tab = pd.crosstab(d[exposure_col], d[outcome_col])
    a = int(tab.loc[1, 1]) if 1 in tab.index and 1 in tab.columns else 0
    b = int(tab.loc[1, 0]) if 1 in tab.index and 0 in tab.columns else 0
    c = int(tab.loc[0, 1]) if 0 in tab.index and 1 in tab.columns else 0
    e = int(tab.loc[0, 0]) if 0 in tab.index and 0 in tab.columns else 0

    aa, bb, cc, ee = map(float, [a, b, c, e])
    if min(aa, bb, cc, ee) == 0:
        aa += 0.5
        bb += 0.5
        cc += 0.5
        ee += 0.5
    orv = (aa * ee) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / ee)
    lcl = math.exp(math.log(orv) - 1.96 * se)
    ucl = math.exp(math.log(orv) + 1.96 * se)
    p = fisher_p(a, b, c, e)

    return {
        "classificacao_agrupada": exposure_label,
        "desfecho": outcome_label,
        "n_analisado": int(len(d)),
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

def main():
    df = load_base_v17().copy()
    if df.empty:
        raise SystemExit("Base V17 ausente.")

    # Presença de comorbidade
    bins = []
    for c in COMORB_COLS:
        if c in df.columns:
            bc = c + "_bin_v17"
            if bc not in df.columns:
                df[bc] = df[c].map(simnao_bin)
            bins.append(bc)
    if "DoencasPreexistentesOutrasEspecificar" in df.columns:
        df["DoencasPreexistentesOutrasEspecificar_presente_v20"] = (
            df["DoencasPreexistentesOutrasEspecificar"].notna()
            & df["DoencasPreexistentesOutrasEspecificar"].astype(str).str.strip().ne("")
        ).astype(int)
        bins.append("DoencasPreexistentesOutrasEspecificar_presente_v20")

    if bins:
        df["possui_comorbidade_v20"] = (df[bins].apply(pd.to_numeric, errors="coerce").fillna(0).max(axis=1) > 0).astype(int)
    else:
        df["possui_comorbidade_v20"] = 0

    outcomes = {
        "obito_meningite_uniao_v23": "Óbito (SINAN∪SIM)",
        "obito_meningite_v17": "Óbito SINAN (EvolucaoCaso)",
        "obito_sim_link_v23": "Óbito SIM (linkage)",
        "hospitalizacao_v17": "Internação/hospitalização",
        "possui_comorbidade_v20": "Presença de comorbidades",
    }
    rows = []
    classes = sorted(df["classificacao_agrupada_v17"].dropna().astype(str).unique())
    for clas in classes:
        temp = df.copy()
        temp["exposicao_classificacao_v20"] = temp["classificacao_agrupada_v17"].astype(str).eq(clas).astype(int)
        for out_col, out_label in outcomes.items():
            if out_col not in temp.columns:
                continue
            res = calc_or_binary(temp, "exposicao_classificacao_v20", out_col, clas, out_label)
            if res:
                rows.append(res)

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "odds_classificacao_desfechos_v20.csv", index=False, encoding="utf-8-sig")
    print("[OK] OR por classificação agrupada V20 gerado.")

if __name__ == "__main__":
    main()
