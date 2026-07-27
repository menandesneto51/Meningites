# -*- coding: utf-8 -*-
"""
02c_odds_clinico_socio_comorb_v21.py
Odds Ratio separado por domínio: clínico, sociodemográfico e comorbidades.
"""

import math
import numpy as np
import pandas as pd
from meningites_v17_common import *

try:
    from scipy import stats
except Exception:
    stats = None

OUTCOMES = {
    "obito_meningite_uniao_v23": "Óbito (SINAN∪SIM)",
    "obito_meningite_v17": "Óbito SINAN (EvolucaoCaso)",
    "obito_sim_link_v23": "Óbito SIM (linkage)",
    "hospitalizacao_v17": "Internação/hospitalização",
    "confirmado_v17": "Confirmação"
}

SOCIO_COLS = ["FaixaEtaria", "SexoPaciente", "Gestante", "RacaPaciente", "Escolaridade"]
COMORB_PREFIX = "DoencasPreexistentes"
CLIN_PREFIX = "SinaisESintomas"

def fisher_p(a, b, c, d):
    if stats is None:
        return np.nan
    try:
        _, p = stats.fisher_exact([[a, b], [c, d]])
        return p
    except Exception:
        return np.nan

def calc_or(d, exposure_col, outcome_col, label, dominio, variavel):
    x = d[[exposure_col, outcome_col]].copy()
    x[exposure_col] = pd.to_numeric(x[exposure_col], errors="coerce")
    x[outcome_col] = pd.to_numeric(x[outcome_col], errors="coerce")
    x = x.dropna()
    x = x[x[exposure_col].isin([0, 1]) & x[outcome_col].isin([0, 1])]
    if len(x) < 10 or x[exposure_col].nunique() < 2 or x[outcome_col].nunique() < 2:
        return None

    tab = pd.crosstab(x[exposure_col], x[outcome_col])
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
        "dominio": dominio,
        "variavel": variavel,
        "exposicao": label,
        "desfecho": OUTCOMES.get(outcome_col, outcome_col),
        "n_analisado": int(len(x)),
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
        raise SystemExit("Base ausente.")

    rows = []

    # Clínico: sinais/sintomas
    clinical_raw = [c for c in df.columns if c.startswith(CLIN_PREFIX) and not c.endswith("_bin_v17") and not c.endswith("Especificar")]
    for col in clinical_raw:
        bcol = f"{col}_bin_v21"
        df[bcol] = df[col].map(simnao_bin)
        for out in OUTCOMES:
            if out in df.columns:
                res = calc_or(df, bcol, out, col, "Clínico", col)
                if res:
                    rows.append(res)

    # Comorbidades
    comorb_raw = [c for c in df.columns if c.startswith(COMORB_PREFIX) and not c.endswith("_bin_v17") and not c.endswith("Especificar")]
    for col in comorb_raw:
        bcol = f"{col}_bin_v21"
        df[bcol] = df[col].map(simnao_bin)
        for out in OUTCOMES:
            if out in df.columns:
                res = calc_or(df, bcol, out, col, "Comorbidades", col)
                if res:
                    rows.append(res)

    # Sociodemográfico: cada categoria vs demais
    for var in SOCIO_COLS:
        if var not in df.columns:
            continue
        s = df[var].fillna("Ignorado").astype(str).str.strip().replace({"": "Ignorado"})
        counts = s.value_counts(dropna=False)
        # Evita gerar centenas de categorias livres
        for cat in counts.head(12).index:
            if counts.loc[cat] < 10:
                continue
            bcol = f"exp_{text_key(var)[:12]}_{text_key(cat)[:18]}"
            df[bcol] = s.eq(cat).astype(int)
            for out in OUTCOMES:
                if out in df.columns:
                    res = calc_or(df, bcol, out, f"{var}: {cat}", "Sociodemográfico", var)
                    if res:
                        rows.append(res)

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "odds_ratio_clinico_socio_comorb_v21.csv", index=False, encoding="utf-8-sig")
    print("[OK] OR clínico/sociodemográfico/comorbidades V21 gerado.")

if __name__ == "__main__":
    main()
