# -*- coding: utf-8 -*-
"""
04b_nowcasting_desfechos_v21.py
Nowcasting simples por desfecho: casos, hospitalizações e óbitos.
"""

import numpy as np
import pandas as pd
from meningites_v17_common import *

DESFECHOS = {
    "casos": "caso_v17",
    "hospitalizacoes": "hospitalizacao_v17",
    "obitos_meningite": "obito_meningite_v17",
}

def main():
    df = load_base_v17().copy()
    if df.empty or "ano_epi_v17" not in df.columns or "semana_epi_v17" not in df.columns:
        raise SystemExit("Base sem semana epidemiológica.")

    rows = []
    for nome, col in DESFECHOS.items():
        if col not in df.columns:
            continue
        wk = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(valor=(col, "sum")).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])
        if wk.empty:
            continue
        atual = wk.iloc[-1]
        historico = wk.iloc[:-1].tail(8)
        mediana_recente = float(historico["valor"].median()) if not historico.empty else float(atual["valor"])
        observado = float(atual["valor"])
        # Fator conservador: se a semana atual estiver abaixo da mediana recente, corrige parcialmente.
        esperado = max(observado, mediana_recente)
        fator = esperado / observado if observado > 0 else np.nan
        atraso = max(0, esperado - observado)
        rows.append({
            "desfecho": nome,
            "ano_epi": int(atual["ano_epi_v17"]) if pd.notna(atual["ano_epi_v17"]) else np.nan,
            "semana_epi": int(atual["semana_epi_v17"]) if pd.notna(atual["semana_epi_v17"]) else np.nan,
            "observado_ultima_semana": observado,
            "mediana_8_semanas_anteriores": mediana_recente,
            "nowcast": esperado,
            "atraso_estimado": atraso,
            "fator_correcao": fator,
            "interpretacao": "Nowcasting operacional simples: corrige a semana mais recente pela mediana das 8 semanas anteriores quando há possível atraso de entrada."
        })
    pd.DataFrame(rows).to_csv(OUT / "nowcasting_desfechos_v21.csv", index=False, encoding="utf-8-sig")
    print("[OK] Nowcasting por desfecho V21 gerado.")

if __name__ == "__main__":
    main()
