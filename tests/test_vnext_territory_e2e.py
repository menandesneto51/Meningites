import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from meningites.operational_queue.publisher import publish_municipal_vnext


def test_territorial_normalization_is_consistent_end_to_end(tmp_path: Path):
    # Fila operacional já em IBGE-6.
    pd.DataFrame([
        {
            "codigo_municipio_v33": "510340",
            "municipio_v33": "Cuiabá",
        }
    ]).to_csv(
        tmp_path / "sih_fila_investigacao_v33.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Indicadores legados em IBGE-7.
    pd.DataFrame([
        {
            "codigo_municipio_v17": "5103403",
            "municipio_v17": "Cuiabá",
            "regional_v17": "Baixada Cuiabana",
            "total_notificacoes": 20,
            "investigados_48h": 15,
            "encerrados_60d": 16,
            "bact_confirmadas": 5,
            "bact_lab_informe_pcr_cultura": 2,
            "dm_casos": 4,
            "dm_quimio_48h": 2,
            "pct_investigados_48h": 75.0,
            "pct_encerrados_60d": 80.0,
            "pct_confirmacao_laboratorial_pcr_cultura": 40.0,
            "pct_quimioprofilaxia_dm_48h": 50.0,
        }
    ]).to_csv(
        tmp_path / "indicadores_ms_operacionais_municipio_v23.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame([
        {
            "referencia_ano": 2024,
            "referencia_periodo": "SE 1–36/2024",
            "referencia_fonte": "Informe Meningites CGVDI/DPNI/SVSA/MS",
            "referencia_vigencia_desde": "2024-10-01",
        }
    ]).to_csv(
        tmp_path / "indicadores_ms_operacionais_base_v23.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Contexto descritivo também em IBGE-7.
    pd.DataFrame([
        {
            "codigo_municipio_v17": "5103403",
            "municipio_v17": "Cuiabá",
            "score_risco_nt154_v25": 3,
            "prioridade": "alta",
            "dm_90d": 1,
            "dm_lab_90d": 1,
            "norma": "NT 154/2024",
        }
    ]).to_csv(
        tmp_path / "score_risco_municipal_nt154_v25.csv",
        index=False,
        encoding="utf-8-sig",
    )

    paths = publish_municipal_vnext(
        tmp_path,
        published_at=datetime(2026, 9, 26, 22, 0, tzinfo=timezone.utc),
    )

    situation = pd.read_csv(paths["situation"], encoding="utf-8-sig", dtype={"codigo_municipio": str})
    signals = pd.read_csv(paths["signals"], encoding="utf-8-sig", dtype={"codigo_municipio": str})
    indicators = pd.read_csv(paths["indicators"], encoding="utf-8-sig", dtype={"codigo_municipio": str})
    regional = pd.read_csv(paths["executive_regional"], encoding="utf-8-sig")
    cards_index = pd.read_csv(paths["cards_index"], encoding="utf-8-sig", dtype={"codigo_municipio": str})
    context = json.loads(paths["agent_context"].read_text(encoding="utf-8"))

    # Toda a cadeia deve convergir para um único IBGE-6.
    assert situation["codigo_municipio"].tolist() == ["510340"]
    assert set(signals["codigo_municipio"]) == {"510340"}
    assert set(indicators["codigo_municipio"]) == {"510340"}
    assert cards_index["codigo_municipio"].tolist() == ["510340"]

    assert len(context["municipalities"]) == 1
    municipality = context["municipalities"][0]
    assert municipality["codigo_municipio"] == "510340"
    assert municipality["municipio"] == "Cuiabá"
    assert municipality["signals"]
    assert municipality["indicators"]

    # O mapeamento regional vindo do artefato IBGE-7 deve se aplicar ao snapshot IBGE-6.
    assert len(regional) == 1
    assert regional.loc[0, "regional"] == "Baixada Cuiabana"
    assert int(regional.loc[0, "municipios_com_contexto_n"]) == 1
    assert int(regional.loc[0, "municipios_com_sinal_n"]) == 1

    # O contexto descritivo IBGE-7 deve ser fundido no mesmo snapshot, sem município duplicado.
    assert int(situation.loc[0, "sih_sem_sinan_n"]) == 1
    assert float(situation.loc[0, "v25_score_risco_nt154_v25"]) == 3

    card_path = tmp_path / cards_index.loc[0, "arquivo"]
    card = card_path.read_text(encoding="utf-8")
    assert "**Código:** 510340" in card
    assert "Investigados em até 48h" in card
    assert "sih-sem-sinan" in card

    manifest = json.loads(paths["cards_manifest"].read_text(encoding="utf-8"))
    assert len(manifest) == 1
    assert manifest[0]["codigo_municipio"] == "510340"
