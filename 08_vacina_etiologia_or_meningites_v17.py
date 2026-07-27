# -*- coding: utf-8 -*-
"""
08_vacina_etiologia_or_meningites_v17.py
OR/efetividade vacinal apenas para pares vacina-etiologia coerentes.
"""

import math
import numpy as np
import pandas as pd
from meningites_v17_common import *

try:
    from scipy import stats
except Exception:
    stats = None

DESFECHOS = {
    "confirmado_v17": "Confirmação do caso",
    "hospitalizacao_v17": "Hospitalização",
    "obito_meningite_uniao_v23": "Óbito (SINAN∪SIM)",
    "obito_meningite_v17": "Óbito SINAN (EvolucaoCaso)",
}

def fisher_p(a, b, c, d):
    if stats is None:
        return np.nan
    try:
        _, p = stats.fisher_exact([[a, b], [c, d]])
        return p
    except Exception:
        return np.nan

def calc_or(g, vac, des):
    d = g[[vac, des]].copy()
    d[vac] = pd.to_numeric(d[vac], errors="coerce")
    d[des] = pd.to_numeric(d[des], errors="coerce")
    d = d.dropna()
    if len(d) < 20 or d[vac].nunique() < 2 or d[des].nunique() < 2:
        return None
    tab = pd.crosstab(d[vac], d[des])
    a = int(tab.loc[1,1]) if 1 in tab.index and 1 in tab.columns else 0
    b = int(tab.loc[1,0]) if 1 in tab.index and 0 in tab.columns else 0
    c = int(tab.loc[0,1]) if 0 in tab.index and 1 in tab.columns else 0
    e = int(tab.loc[0,0]) if 0 in tab.index and 0 in tab.columns else 0
    aa,bb,cc,ee = map(float, [a,b,c,e])
    if min(aa,bb,cc,ee) == 0:
        aa += 0.5; bb += 0.5; cc += 0.5; ee += 0.5
    orv = (aa*ee)/(bb*cc)
    se = math.sqrt(1/aa + 1/bb + 1/cc + 1/ee)
    lcl = math.exp(math.log(orv) - 1.96*se)
    ucl = math.exp(math.log(orv) + 1.96*se)
    p = fisher_p(a,b,c,e)
    ev = (1-orv)*100 if orv < 1 else 0.0
    ev_l = (1-ucl)*100 if orv < 1 else np.nan
    ev_u = (1-lcl)*100 if orv < 1 else np.nan
    if orv < 1 and pd.notna(p) and p < 0.05 and ucl < 1:
        interp = "Compatível com proteção observacional para etiologia-alvo; IC95% abaixo de 1."
        alerta = "Proteção observacional coerente"
    elif orv < 1:
        interp = "OR<1 sugere proteção observacional, mas IC95%/p-valor exigem cautela."
        alerta = "Sugere proteção; cautela"
    elif orv >= 1 and pd.notna(p) and p < 0.05 and lcl > 1:
        interp = "Maior chance observada; investigar confundimento, viés e preenchimento."
        alerta = "Investigar viés/confundimento"
    else:
        interp = "Sem evidência robusta de proteção observacional."
        alerta = "Sem evidência robusta"
    return {
        "n_analisado": len(d), "vacinados": int((d[vac] == 1).sum()), "nao_vacinados": int((d[vac] == 0).sum()),
        "eventos_vacinados": a, "nao_eventos_vacinados": b, "eventos_nao_vacinados": c, "nao_eventos_nao_vacinados": e,
        "or": orv, "ic95_or_inferior": lcl, "ic95_or_superior": ucl, "p_value": p,
        "efetividade_vacinal_estimada_pct": ev, "ev_ic95_inferior_pct": ev_l, "ev_ic95_superior_pct": ev_u,
        "interpretacao_estatistica": interpret_p(p), "interpretacao": interp, "relevancia_pratica": practical_or(orv),
        "alerta_vigilancia": alerta
    }

def main():
    df = load_base_v17()
    for c in list(VACINA_ETIOLOGIA.keys()) + list(DESFECHOS.keys()):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    mapa = pd.DataFrame([
        {"campo_vacinal": vac, "vacina": nome, "etiologias_alvo": "; ".join(alvos) if alvos else "Não aplicável para efetividade etiológica",
         "usar_para_efetividade": bool(alvos),
         "observacao": "Meningite viral/asséptica não possui vacina correspondente nos campos analisados."}
        for vac, (nome, alvos) in VACINA_ETIOLOGIA.items()
    ])
    rows, na = [], []
    for (reg, etio), g in df.groupby(["regional_v17", "classificacao_agrupada_v17"], dropna=False):
        for vac_col, (vac_nome, alvos) in VACINA_ETIOLOGIA.items():
            if vac_col not in g.columns:
                continue
            if not alvos or etio not in alvos:
                na.append({
                    "regional_v17": reg, "classificacao_agrupada_v17": etio, "vacina": vac_nome,
                    "campo_vacinal": vac_col, "status": "Não aplicável etiologicamente",
                    "motivo": "Não há vacina correspondente para esta classificação; viral/asséptica não entra em EV vacinal."
                              if str(etio) == "Meningite viral/asséptica"
                              else f"{vac_nome} é aplicável a {', '.join(alvos) if alvos else 'nenhuma etiologia alvo direta'}, não a {etio}.",
                    "n_registros_no_estrato": len(g), "registros_com_campo_vacinal": int(g[vac_col].notna().sum())
                })
                continue
            prop = (g[vac_col] == 1).sum() / g[vac_col].notna().sum() * 100 if g[vac_col].notna().sum() else np.nan
            for des_col, des_nome in DESFECHOS.items():
                res = calc_or(g, vac_col, des_col)
                base = {"regional_v17": reg, "classificacao_agrupada_v17": etio, "vacina": vac_nome, "campo_vacinal": vac_col,
                        "desfecho": des_nome, "total_casos_no_estrato": len(g), "proporcao_vacinados_pct": prop}
                if res is None:
                    rows.append({**base, "status": "Aplicável, mas insuficiente para OR",
                                 "motivo": "Estrato pequeno, sem grupo comparador, sem evento ou campo incompleto."})
                else:
                    rows.append({**base, "status": "Aplicável etiologicamente", "motivo": "Par vacina-etiologia coerente.", **res})
    out = pd.DataFrame(rows)
    na_df = pd.DataFrame(na)
    mapa.to_csv(OUT / "mapa_vacina_etiologia_v17.csv", index=False, encoding="utf-8-sig")
    out.to_csv(OUT / "efetividade_vacinal_etiologia_coerente_v17.csv", index=False, encoding="utf-8-sig")
    na_df.to_csv(OUT / "pares_nao_aplicaveis_vacina_etiologia_v17.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT / "resumo_vacina_etiologia_v17.xlsx", engine="openpyxl") as writer:
        mapa.to_excel(writer, sheet_name="Mapa_vacina_etiologia", index=False)
        out.to_excel(writer, sheet_name="OR_EV_coerente", index=False)
        na_df.to_excel(writer, sheet_name="Nao_aplicaveis", index=False)
    print("[OK] Vacina x etiologia V17 gerado.")

if __name__ == "__main__":
    main()
