import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from meningites.operational_queue.publisher import publish_municipal_vnext


def test_publisher_generates_four_auditable_outputs(tmp_path: Path):
    pd.DataFrame([
        {"codigo_municipio_v33": "5103403", "municipio_v33": "Cuiabá"},
        {"codigo_municipio_v33": "5103403", "municipio_v33": "Cuiabá"},
    ]).to_csv(tmp_path / "sih_fila_investigacao_v33.csv", index=False, encoding="utf-8-sig")

    paths = publish_municipal_vnext(
        tmp_path,
        published_at=datetime(2026, 9, 26, 18, 0, tzinfo=timezone.utc),
    )

    assert all(path.exists() for path in paths.values())

    situation = pd.read_csv(paths["situation"], encoding="utf-8-sig")
    signals = pd.read_csv(paths["signals"], encoding="utf-8-sig")
    divergence = pd.read_csv(paths["divergences"], encoding="utf-8-sig")
    provenance = json.loads(paths["provenance"].read_text(encoding="utf-8"))

    assert int(situation.loc[0, "sih_sem_sinan_n"]) == 2
    assert "sih-sem-sinan" in set(signals["rule_id"])
    assert "ausente" in set(divergence["status"])
    assert provenance["municipalities_n"] == 1
    assert provenance["signals_n"] >= 1


def test_missing_municipality_key_is_reported_and_not_inferred(tmp_path: Path):
    pd.DataFrame([
        {"municipio_v17": "Cuiabá", "tipo": "teste"},
    ]).to_csv(tmp_path / "gal_fila_tipagem_sinan_v32.csv", index=False, encoding="utf-8-sig")

    paths = publish_municipal_vnext(tmp_path)
    divergence = pd.read_csv(paths["divergences"], encoding="utf-8-sig")
    row = divergence[divergence["arquivo"].eq("gal_fila_tipagem_sinan_v32.csv")].iloc[0]

    assert row["status"] == "sem_chave_territorial"
    situation = pd.read_csv(paths["situation"], encoding="utf-8-sig")
    assert situation.empty
