from pathlib import Path

import pandas as pd

from meningites.validation.reconcile import build_validation_report, publish_validation_report


def _base_files(root: Path):
    pd.DataFrame([{
        "codigo_municipio_v17": "5103403",
        "municipio_v17": "Cuiabá",
        "regional_v17": "Baixada Cuiabana",
        "total_notificacoes": 20,
        "investigados_48h": 15,
        "pct_investigados_48h": 75.0,
    }]).to_csv(root / "indicadores_ms_operacionais_municipio_v23.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{
        "codigo_municipio": "510340",
        "municipio": "Cuiabá",
        "indicador": "pct_investigados_48h",
        "valor_pct": 75.0,
        "numerador": 15,
        "denominador": 20,
    }]).to_csv(root / "indicadores_municipais_vnext.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{
        "codigo_municipio": "510340",
        "municipio": "Cuiabá",
        "sih_sem_sinan_n": 1,
    }]).to_csv(root / "situacao_municipal_vnext.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{
        "codigo_municipio": "510340",
        "municipio": "Cuiabá",
        "rule_id": "sih-sem-sinan",
        "valor": 1,
        "fontes": "sih_fila_investigacao_v33.csv",
    }]).to_csv(root / "sinais_municipais_vnext.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{
        "codigo_municipio": "510340",
        "municipio": "Cuiabá",
        "arquivo": "cards_municipais_vnext/510340.md",
    }]).to_csv(root / "cards_municipais_vnext_index.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([
        {"arquivo": "sih_fila_investigacao_v33.csv", "status": "ok"},
    ]).to_csv(root / "divergencias_vnext.csv", index=False, encoding="utf-8-sig")


def test_validation_report_passes_reconciled_artifacts(tmp_path: Path):
    _base_files(tmp_path)
    report = build_validation_report(tmp_path)
    assert report["overall_status"] == "pass"
    assert report["fail_n"] == 0


def test_validation_report_fails_on_module12_mismatch(tmp_path: Path):
    _base_files(tmp_path)
    frame = pd.read_csv(tmp_path / "indicadores_municipais_vnext.csv", encoding="utf-8-sig")
    frame.loc[0, "numerador"] = 14
    frame.to_csv(tmp_path / "indicadores_municipais_vnext.csv", index=False, encoding="utf-8-sig")

    report = build_validation_report(tmp_path)
    assert report["overall_status"] == "fail"
    assert any(c["check_id"] == "module12:reconciliation" and c["status"] == "fail" for c in report["checks"])


def test_validation_report_is_published_as_json_and_markdown(tmp_path: Path):
    _base_files(tmp_path)
    paths = publish_validation_report(tmp_path)
    assert paths["validation_json"].exists()
    assert paths["validation_md"].exists()
    assert "Status geral" in paths["validation_md"].read_text(encoding="utf-8")
