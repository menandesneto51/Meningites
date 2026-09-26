"""Normalização dos indicadores municipais do módulo 12.

Não reconstrói numeradores ausentes a partir de percentuais arredondados.
A referência/vigência é lida do artefato canônico estadual do próprio módulo.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from meningites.operational_queue.legacy_aggregator import _norm_code


INDICATOR_SPECS = (
    ("pct_confirmacao_laboratorial_pcr_cultura", "bact_lab_informe_pcr_cultura", "bact_confirmadas", "Confirmação laboratorial PCR/cultura"),
    ("pct_investigados_48h", "investigados_48h", "total_notificacoes", "Investigados em até 48h"),
    ("pct_encerrados_60d", "encerrados_60d", "total_notificacoes", "Encerrados em até 60 dias"),
    ("pct_quimioprofilaxia_dm_48h", "dm_quimio_48h", "dm_casos", "DM com quimioprofilaxia em até 48h"),
)


def _reference_metadata(root: Path) -> dict:
    for filename in (
        "indicadores_ms_operacionais_base_v23.csv",
        "indicadores_ms_operacionais_v23.csv",
    ):
        path = root / filename
        if not path.exists() or path.stat().st_size == 0:
            continue
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        if frame.empty:
            continue
        row = frame.iloc[0]
        return {
            "referencia_ano": row.get("referencia_ano"),
            "referencia_periodo": row.get("referencia_periodo"),
            "referencia_fonte": row.get("referencia_fonte"),
            "referencia_vigencia_desde": row.get("referencia_vigencia_desde"),
            "referencia_artefato": filename,
        }
    return {
        "referencia_ano": None,
        "referencia_periodo": None,
        "referencia_fonte": None,
        "referencia_vigencia_desde": None,
        "referencia_artefato": None,
    }


def municipal_indicator_frame(outdir: str | Path) -> pd.DataFrame:
    root = Path(outdir)
    path = root / "indicadores_ms_operacionais_municipio_v23.csv"
    columns = [
        "codigo_municipio", "municipio", "regional", "indicador", "indicador_rotulo",
        "valor_pct", "numerador", "denominador", "numerador_status", "denominador_status",
        "referencia_ano", "referencia_periodo", "referencia_fonte",
        "referencia_vigencia_desde", "fonte_artefato", "referencia_artefato",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    if frame.empty or "codigo_municipio_v17" not in frame.columns:
        return pd.DataFrame(columns=columns)

    ref = _reference_metadata(root)
    rows = []
    for _, source in frame.iterrows():
        code = _norm_code(source.get("codigo_municipio_v17"))
        if not code:
            continue
        for metric, numerator_col, denominator_col, label in INDICATOR_SPECS:
            if metric not in frame.columns:
                continue
            numerator_available = numerator_col in frame.columns
            denominator_available = denominator_col in frame.columns
            rows.append({
                "codigo_municipio": code,
                "municipio": source.get("municipio_v17", ""),
                "regional": source.get("regional_v17", ""),
                "indicador": metric,
                "indicador_rotulo": label,
                "valor_pct": source.get(metric),
                "numerador": source.get(numerator_col) if numerator_available else None,
                "denominador": source.get(denominator_col) if denominator_available else None,
                "numerador_status": "ok" if numerator_available else "nao_exportado_pelo_modulo_12_municipal",
                "denominador_status": "ok" if denominator_available else "nao_exportado_pelo_modulo_12_municipal",
                **ref,
                "fonte_artefato": path.name,
            })
    return pd.DataFrame(rows, columns=columns)
