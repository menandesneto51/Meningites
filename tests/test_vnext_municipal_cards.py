from pathlib import Path

import pandas as pd

from meningites.operational_queue.cards import build_municipal_cards
from meningites.operational_queue.municipal_indicators import municipal_indicator_frame


def test_municipal_indicators_keep_denominator_and_do_not_infer_numerator(tmp_path: Path):
    pd.DataFrame([{
        "codigo_municipio_v17": "5103403",
        "municipio_v17": "Cuiabá",
        "regional_v17": "Baixada Cuiabana",
        "total_notificacoes": 20,
        "pct_investigados_48h": 75.0,
        "pct_encerrados_60d": 80.0,
        "pct_confirmacao_laboratorial_pcr_cultura": 40.0,
        "pct_quimioprofilaxia_dm_48h": 50.0,
        "dm_casos": 4,
    }]).to_csv(tmp_path / "indicadores_ms_operacionais_municipio_v23.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{
        "referencia_ano": 2024,
        "referencia_periodo": "SE 1–36/2024",
        "referencia_fonte": "Informe Meningites CGVDI/DPNI/SVSA/MS",
        "referencia_vigencia_desde": "2024-10-01",
    }]).to_csv(tmp_path / "indicadores_ms_operacionais_base_v23.csv", index=False, encoding="utf-8-sig")

    frame = municipal_indicator_frame(tmp_path)
    inv = frame[frame["indicador"].eq("pct_investigados_48h")].iloc[0]

    assert inv["denominador"] == 20
    assert pd.isna(inv["numerador"])
    assert inv["numerador_status"] == "nao_exportado_pelo_modulo_12_municipal"
    assert inv["referencia_vigencia_desde"] == "2024-10-01"


def test_card_contains_operational_context_and_reference(tmp_path: Path):
    situation = pd.DataFrame([{
        "codigo_municipio": "5103403",
        "municipio": "Cuiabá",
        "sih_sem_sinan_n": 2,
        "fontes": "sih_fila_investigacao_v33.csv",
    }])
    signals = pd.DataFrame([{
        "codigo_municipio": "5103403",
        "titulo": "Internação compatível sem vínculo SINAN",
        "prioridade": "alta",
        "rule_id": "sih-sem-sinan",
        "valor": 2,
        "limiar": 0,
        "fontes": "sih_fila_investigacao_v33.csv",
        "acoes_sugeridas": "Revisar fila.",
    }])
    indicators = pd.DataFrame([{
        "codigo_municipio": "5103403",
        "indicador_rotulo": "Investigados em até 48h",
        "valor_pct": 75,
        "denominador": 20,
        "referencia_periodo": "SE 1–36/2024",
        "referencia_fonte": "Informe Meningites CGVDI/DPNI/SVSA/MS",
        "referencia_vigencia_desde": "2024-10-01",
    }])

    index_path, manifest_path = build_municipal_cards(tmp_path, situation, signals, indicators)
    card = (tmp_path / "cards_municipais_vnext" / "5103403.md").read_text(encoding="utf-8")

    assert index_path.exists()
    assert manifest_path.exists()
    assert "Investigados em até 48h" in card
    assert "denominador: 20" in card
    assert "sih-sem-sinan" in card
    assert "não exporta todos os numeradores" in card
