"""Publicação dos artefatos municipais VNext.

Gera saídas derivadas e auditáveis sem substituir os arquivos legados.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from meningites.operational_queue.descriptive_aggregator import descriptive_snapshots, merge_snapshots
from meningites.operational_queue.legacy_aggregator import (
    ArtifactSpec,
    DEFAULT_ARTIFACTS,
    _pick,
    aggregate_artifacts,
)
from meningites.operational_queue.municipal_engine import MunicipalSituationEngine
from meningites.operational_queue.municipal_indicators import municipal_indicator_frame
from meningites.operational_queue.cards import build_municipal_cards
from meningites.operational_queue.rules_catalog import PRODUCTION_RULES


def inspect_artifacts(outdir: str | Path, specs: Iterable[ArtifactSpec] = DEFAULT_ARTIFACTS) -> pd.DataFrame:
    root = Path(outdir)
    rows: list[dict] = []
    for spec in specs:
        path = root / spec.filename
        row = {
            "arquivo": spec.filename,
            "metrica": spec.metric,
            "status": "ok",
            "linhas": 0,
            "coluna_codigo": "",
            "coluna_municipio": "",
            "detalhe": "",
        }
        if not path.exists():
            row.update(status="ausente", detalhe="Artefato não encontrado; métrica não será assumida como zero.")
            rows.append(row)
            continue
        if path.stat().st_size == 0:
            row.update(status="vazio", detalhe="Arquivo com zero bytes.")
            rows.append(row)
            continue
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        except Exception as exc:
            row.update(status="erro_leitura", detalhe=f"{type(exc).__name__}: {exc}")
            rows.append(row)
            continue
        row["linhas"] = int(len(frame))
        code_col = _pick(frame.columns, spec.municipality_code_candidates)
        name_col = _pick(frame.columns, spec.municipality_name_candidates)
        row["coluna_codigo"] = code_col or ""
        row["coluna_municipio"] = name_col or ""
        if code_col is None:
            row.update(
                status="sem_chave_territorial",
                detalhe="Nenhuma coluna de código municipal do contrato foi encontrada; agregação omitida para evitar inferência por nome.",
            )
        elif frame.empty:
            row.update(status="sem_registros", detalhe="Arquivo válido, sem registros acionáveis.")
        rows.append(row)
    return pd.DataFrame(rows)


def _situation_frame(snapshots) -> pd.DataFrame:
    metric_names = sorted({metric for snapshot in snapshots for metric in snapshot.metrics})
    rows = []
    for snapshot in snapshots:
        row = {
            "codigo_municipio": snapshot.municipality_code,
            "municipio": snapshot.municipality_name,
            "fontes_n": len(snapshot.evidence),
        }
        row.update({metric: snapshot.metrics.get(metric) for metric in metric_names})
        row["fontes"] = " | ".join(sorted({e.source for e in snapshot.evidence}))
        rows.append(row)
    columns = ["codigo_municipio", "municipio", *metric_names, "fontes_n", "fontes"]
    return pd.DataFrame(rows, columns=columns)


def _signals_frame(snapshots) -> pd.DataFrame:
    engine = MunicipalSituationEngine(PRODUCTION_RULES)
    rows = []
    for snapshot in snapshots:
        for signal in engine.evaluate(snapshot):
            rows.append({
                "signal_id": signal.signal_id,
                "codigo_municipio": signal.municipality_code,
                "municipio": snapshot.municipality_name,
                "titulo": signal.title,
                "categoria": signal.category,
                "prioridade": signal.priority,
                "rule_id": signal.trigger.rule_id,
                "descricao_gatilho": signal.trigger.description,
                "valor": signal.trigger.value,
                "limiar": signal.trigger.threshold,
                "acoes_sugeridas": " | ".join(signal.suggested_actions),
                "fontes": " | ".join(sorted({e.source for e in signal.evidence})),
            })
    return pd.DataFrame(rows)


def publish_municipal_vnext(
    outdir: str | Path,
    *,
    published_at: datetime | None = None,
) -> dict[str, Path]:
    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    now = published_at or datetime.now(timezone.utc)

    divergences = inspect_artifacts(root)
    operational = aggregate_artifacts(root, generated_at=now)
    descriptive = descriptive_snapshots(root, generated_at=now)
    snapshots = merge_snapshots(operational, descriptive)
    situation = _situation_frame(snapshots)
    signals = _signals_frame(snapshots)
    indicators = municipal_indicator_frame(root)

    paths = {
        "situation": root / "situacao_municipal_vnext.csv",
        "signals": root / "sinais_municipais_vnext.csv",
        "divergences": root / "divergencias_vnext.csv",
        "provenance": root / "procedencia_situacao_vnext.json",
        "indicators": root / "indicadores_municipais_vnext.csv",
    }
    situation.to_csv(paths["situation"], index=False, encoding="utf-8-sig")
    signals.to_csv(paths["signals"], index=False, encoding="utf-8-sig")
    divergences.to_csv(paths["divergences"], index=False, encoding="utf-8-sig")
    indicators.to_csv(paths["indicators"], index=False, encoding="utf-8-sig")
    cards_index, cards_manifest = build_municipal_cards(root, situation, signals, indicators)
    paths["cards_index"] = cards_index
    paths["cards_manifest"] = cards_manifest

    provenance = {
        "schema_version": "vnext-1",
        "generated_at": now.isoformat(),
        "engine": "MunicipalSituationEngine",
        "rules": [asdict(rule) for rule in PRODUCTION_RULES],
        "inputs": divergences.to_dict(orient="records"),
        "outputs": {key: path.name for key, path in paths.items() if key != "provenance"},
        "municipalities_n": int(len(situation)),
        "signals_n": int(len(signals)),
        "municipal_indicators_n": int(len(indicators)),
        "operational_snapshots_n": int(len(operational)),
        "descriptive_snapshots_n": int(len(descriptive)),
        "notes": [
            "Ausência de artefato não é convertida silenciosamente em zero.",
            "Ausência de chave territorial não é inferida a partir do nome do município.",
            "As regras atuais representam presença de filas operacionais já produzidas pelo legado.",
            "Score V25 e doses CIPV V34 entram apenas como contexto descritivo; não geram sinal VNext automaticamente.",
        ],
    }
    paths["provenance"].write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return paths
