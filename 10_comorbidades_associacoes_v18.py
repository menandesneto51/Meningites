# -*- coding: utf-8 -*-
"""
10_comorbidades_associacoes_v18.py
Associa comorbidades preexistentes com evolução e classificação final.
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
    "DoencasPreexistentesOutrasEspecificar",
]

OUTCOMES = {
    "evolucao_padronizada_v17": "Evolução",
    "classificacao_caso_padronizada_v17": "Classificação final",
}


def chi2(tab):
    if stats is None:
        return np.nan, np.nan, np.nan
    try:
        chi, p, dof, exp = stats.chi2_contingency(tab)
        n = tab.sum().sum()
        r, k = tab.shape
        cramer = math.sqrt((chi / n) / max(1, min(k - 1, r - 1))) if n > 0 else np.nan
        return chi, p, cramer
    except Exception:
        return np.nan, np.nan, np.nan


def main():
    df = load_base_v17().copy()
    if df.empty:
        raise SystemExit("Base ausente.")

    for col in COMORB_COLS:
        if col in df.columns and f"{col}_bin_v17" not in df.columns:
            df[f"{col}_bin_v17"] = df[col].map(simnao_bin)

    rows = []
    detail = []
    for rawcol in COMORB_COLS:
        col = f"{rawcol}_bin_v17" if f"{rawcol}_bin_v17" in df.columns else rawcol
        if col not in df.columns:
            continue
        dfx = df.copy()
        if rawcol.endswith("Especificar"):
            dfx[col] = (dfx[rawcol].notna() & dfx[rawcol].astype(str).str.strip().ne("")).astype(int)

        for outcol, outlabel in OUTCOMES.items():
            if outcol not in dfx.columns:
                continue
            d = dfx[[col, outcol]].dropna().copy()
            d[col] = pd.to_numeric(d[col], errors="coerce")
            d = d.dropna()
            d = d[d[col].isin([0, 1])]
            if len(d) < 10 or d[col].nunique() < 2 or d[outcol].nunique() < 2:
                continue
            tab = pd.crosstab(d[col], d[outcol])
            chi, p, cv = chi2(tab)
            rows.append({
                "variavel": rawcol,
                "desfecho": outlabel,
                "n": len(d),
                "categorias_desfecho": int(d[outcol].nunique()),
                "chi2": chi,
                "p_value": p,
                "cramers_v": cv,
                "interpretacao_estatistica": interpret_p(p),
                "relevancia_pratica": "Associação fraca" if pd.notna(cv) and cv < 0.1 else "Associação moderada/forte" if pd.notna(cv) and cv >= 0.1 else "Indeterminada",
            })
            exp_total = int((d[col] == 1).sum())
            nexp_total = int((d[col] == 0).sum())
            s_out = d[outcol].astype(str)
            for category in sorted(s_out.unique()):
                a = int(((d[col] == 1) & s_out.eq(category)).sum())
                c = int(((d[col] == 0) & s_out.eq(category)).sum())
                detail.append({
                    "variavel": rawcol,
                    "desfecho": outlabel,
                    "categoria_desfecho": category,
                    "expostos_n": exp_total,
                    "nao_expostos_n": nexp_total,
                    "eventos_expostos": a,
                    "eventos_nao_expostos": c,
                    "percentual_expostos": a / exp_total * 100 if exp_total else np.nan,
                    "percentual_nao_expostos": c / nexp_total * 100 if nexp_total else np.nan,
                })

    pd.DataFrame(rows).to_csv(OUT / "associacoes_comorbidades_quiquadrado_v18.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(detail).to_csv(OUT / "associacoes_comorbidades_detalhe_v18.csv", index=False, encoding="utf-8-sig")
    print("[OK] Associações de comorbidades V18 geradas.")


if __name__ == "__main__":
    main()
