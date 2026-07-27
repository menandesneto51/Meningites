# -*- coding: utf-8 -*-
"""
07_laboratorio_qualidade_meningites_v20.py
Indicadores laboratoriais com taxa de positividade real.
"""

import numpy as np
import pandas as pd
from meningites_v17_common import *

RESULT_COLS = [
    "ResultadoCulturaLiquor",
    "ResultadoCulturaPetequias",
    "ResultadoCulturaSangueSoro",
    "ResultadoCulturaEscarro",
    "ResultadoBacterioscopiaLiquor",
    "ResultadoBacterioscopiaPetequias",
    "ResultadoBacterioscopiaSangueSoro",
    "ResultadoBacterioscopiaEscarro",
    "ResultadoCIELiquor",
    "ResultadoCIESangueSoro",
    "ResultadoAglutinacaoLatexLiquor",
    "ResultadoAglutinacaoLatexSangueSoro",
    "ResultadoIsolamentoViralLiquor",
    "ResultadoIsolamentoViralFezes",
    "ResultadoPCRLiquor",
    "ResultadoPCRPetequias",
    "ResultadoPCRSangueSoro",
    "ResultadoPCREscarro",
]
LAB_COLS_V20 = ["PuncaoLombar", "DataPuncaoLombar", "AspectoLiquor"] + RESULT_COLS

LABELS = {
    "ResultadoCulturaLiquor": "Cultura líquor",
    "ResultadoCulturaPetequias": "Cultura petequias",
    "ResultadoCulturaSangueSoro": "Cultura sangue/soro",
    "ResultadoCulturaEscarro": "Cultura escarro",
    "ResultadoBacterioscopiaLiquor": "Bacterioscopia líquor",
    "ResultadoBacterioscopiaPetequias": "Bacterioscopia petequias",
    "ResultadoBacterioscopiaSangueSoro": "Bacterioscopia sangue/soro",
    "ResultadoBacterioscopiaEscarro": "Bacterioscopia escarro",
    "ResultadoCIELiquor": "CIE líquor",
    "ResultadoCIESangueSoro": "CIE sangue/soro",
    "ResultadoAglutinacaoLatexLiquor": "Látex líquor",
    "ResultadoAglutinacaoLatexSangueSoro": "Látex sangue/soro",
    "ResultadoIsolamentoViralLiquor": "Isolamento viral líquor",
    "ResultadoIsolamentoViralFezes": "Isolamento viral fezes",
    "ResultadoPCRLiquor": "PCR líquor",
    "ResultadoPCRPetequias": "PCR petequias",
    "ResultadoPCRSangueSoro": "PCR sangue/soro",
    "ResultadoPCREscarro": "PCR escarro",
}

def lab_code(x):
    """
    Retorna:
    1 = positivo
    0 = negativo
    2 = inconclusivo/outro resultado válido
    NaN = não realizado / ignorado / vazio
    """
    if pd.isna(x):
        return np.nan
    raw = str(x).strip()
    if raw == "" or raw.lower() in MISSING:
        return np.nan
    s = text_key(raw)

    # Códigos SINAN comuns: 1 positivo, 2 negativo, 3 inconclusivo, 4 não realizado, 9 ignorado.
    if s.startswith("1"):
        return 1
    if s.startswith("2"):
        return 0
    if s.startswith("3"):
        return 2
    if s.startswith("4") or s.startswith("9"):
        return np.nan

    positive_terms = ["POSITIVO", "REAGENTE", "DETECTADO", "DETECTAVEL", "ISOLADO", "IDENTIFICADO"]
    negative_terms = ["NEGATIVO", "NAO REAGENTE", "NAO DETECTADO", "NAO DETECTAVEL", "N REAGENTE", "AUSENTE"]
    inconclusive_terms = ["INCONCLUSIVO", "INDETERMINADO", "INVALIDO", "PREJUDICADO"]

    if any(t in s for t in positive_terms):
        return 1
    if any(t in s for t in negative_terms):
        return 0
    if any(t in s for t in inconclusive_terms):
        return 2
    return np.nan

def main():
    df = load_base_v17().copy()
    if df.empty:
        raise SystemExit("Base ausente.")

    rows = []
    for col in RESULT_COLS:
        if col not in df.columns:
            continue
        parsed = df[col].map(lab_code)
        positivos = int((parsed == 1).sum())
        negativos = int((parsed == 0).sum())
        inconclusivos = int((parsed == 2).sum())
        realizados_validos = positivos + negativos + inconclusivos
        concludentes = positivos + negativos
        rows.append({
            "metodo": LABELS.get(col, col),
            "coluna": col,
            "resultados_validos": realizados_validos,
            "concludentes_pos_neg": concludentes,
            "positivos": positivos,
            "negativos": negativos,
            "inconclusivos": inconclusivos,
            "taxa_positividade_real_pct": positivos / concludentes * 100 if concludentes else np.nan,
            "taxa_positividade_inclui_inconclusivo_pct": positivos / realizados_validos * 100 if realizados_validos else np.nan,
            "cobertura_resultado_sobre_notificacoes_pct": realizados_validos / len(df) * 100 if len(df) else np.nan,
        })
    lab = pd.DataFrame(rows)
    lab.to_csv(OUT / "indicadores_laboratoriais_metodos_v17.csv", index=False, encoding="utf-8-sig")
    lab.to_csv(OUT / "indicadores_laboratoriais_metodos_v20.csv", index=False, encoding="utf-8-sig")

    # Any lab positivity
    present_cols = [c for c in RESULT_COLS if c in df.columns]
    any_pos = pd.Series(False, index=df.index)
    any_conc = pd.Series(False, index=df.index)
    any_valid = pd.Series(False, index=df.index)
    for col in present_cols:
        parsed = df[col].map(lab_code)
        any_pos = any_pos | (parsed == 1)
        any_conc = any_conc | parsed.isin([0, 1])
        any_valid = any_valid | parsed.isin([0, 1, 2])
    tmp = df.copy()
    tmp["lab_positivo_v20"] = any_pos.astype(int)
    tmp["lab_concludente_v20"] = any_conc.astype(int)
    tmp["lab_resultado_valido_v20"] = any_valid.astype(int)

    clas = tmp.groupby("classificacao_agrupada_v17", dropna=False).agg(
        notificacoes=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        com_resultado_valido=("lab_resultado_valido_v20", "sum"),
        com_resultado_concludente=("lab_concludente_v20", "sum"),
        positivos=("lab_positivo_v20", "sum"),
    ).reset_index()
    clas["taxa_positividade_real_pct"] = clas["positivos"] / clas["com_resultado_concludente"].replace(0, np.nan) * 100
    clas["cobertura_laboratorial_pct"] = clas["com_resultado_valido"] / clas["notificacoes"].replace(0, np.nan) * 100
    clas.to_csv(OUT / "indicadores_laboratoriais_classificacao_v17.csv", index=False, encoding="utf-8-sig")
    clas.to_csv(OUT / "indicadores_laboratoriais_classificacao_v20.csv", index=False, encoding="utf-8-sig")

    criterio = df.get("CriterioConfirmacao", pd.Series(index=df.index, dtype=object)).fillna("Ignorado/em branco").astype(str)
    crit = criterio.value_counts(dropna=False).reset_index()
    crit.columns = ["criterio_confirmacao", "n"]
    crit["percentual"] = crit["n"] / len(df) * 100 if len(df) else np.nan
    crit.to_csv(OUT / "criterio_confirmacao_v20.csv", index=False, encoding="utf-8-sig")

    kpis = pd.DataFrame([{
        "total_notificacoes": len(df),
        "total_confirmados": int(pd.to_numeric(df["confirmado_v17"], errors="coerce").sum()),
        "total_com_resultado_laboratorial_valido": int(any_valid.sum()),
        "total_com_resultado_laboratorial_concludente": int(any_conc.sum()),
        "total_laboratorial_positivo": int(any_pos.sum()),
        "taxa_positividade_real_pct": int(any_pos.sum()) / int(any_conc.sum()) * 100 if int(any_conc.sum()) else np.nan,
        "cobertura_laboratorial_pct": int(any_valid.sum()) / len(df) * 100 if len(df) else np.nan,
    }])
    kpis.to_csv(OUT / "laboratorio_kpis_v20.csv", index=False, encoding="utf-8-sig")

    print("[OK] Laboratório V20 com positividade real gerado.")

if __name__ == "__main__":
    main()
