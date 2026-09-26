"""Validador de reconciliação local do Meningites VNext."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from meningites.domain.territory import normalize_municipality_code


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _issue(check_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"check_id": check_id, "status": status, "detail": detail, **extra}


def validate_territorial_uniqueness(outdir: str | Path) -> list[dict[str, Any]]:
    root = Path(outdir)
    issues = []
    for filename, code_col in [
        ("situacao_municipal_vnext.csv", "codigo_municipio"),
        ("indicadores_municipais_vnext.csv", "codigo_municipio"),
        ("cards_municipais_vnext_index.csv", "codigo_municipio"),
    ]:
        frame = _read_csv(root / filename)
        if frame.empty or code_col not in frame.columns:
            issues.append(_issue(f"territory:{filename}", "attention", "Arquivo ausente/vazio ou sem chave territorial."))
            continue
        codes = frame[code_col].map(normalize_municipality_code)
        invalid = int((codes == "").sum())
        raw_unique = frame[code_col].astype(str).nunique()
        normalized_unique = codes[codes != ""].nunique()
        if invalid:
            issues.append(_issue(f"territory:{filename}", "fail", f"{invalid} registro(s) com código municipal inválido.", invalid_n=invalid))
        elif raw_unique != normalized_unique and filename != "indicadores_municipais_vnext.csv":
            issues.append(_issue(
                f"territory:{filename}", "fail",
                "Mais de uma representação territorial converge para a mesma chave IBGE-6.",
                raw_unique=int(raw_unique), normalized_unique=int(normalized_unique),
            ))
        else:
            issues.append(_issue(
                f"territory:{filename}", "pass",
                f"Chaves territoriais válidas; {normalized_unique} município(s) normalizado(s).",
            ))
    return issues


def validate_module12_indicators(outdir: str | Path) -> list[dict[str, Any]]:
    root = Path(outdir)
    legacy = _read_csv(root / "indicadores_ms_operacionais_municipio_v23.csv")
    vnext = _read_csv(root / "indicadores_municipais_vnext.csv")
    if legacy.empty:
        return [_issue("module12:source", "attention", "Artefato municipal do módulo 12 ausente ou vazio.")]
    if vnext.empty:
        return [_issue("module12:vnext", "fail", "indicadores_municipais_vnext.csv ausente ou vazio.")]

    metric_map = {
        "pct_confirmacao_laboratorial_pcr_cultura": ("bact_lab_informe_pcr_cultura", "bact_confirmadas"),
        "pct_investigados_48h": ("investigados_48h", "total_notificacoes"),
        "pct_encerrados_60d": ("encerrados_60d", "total_notificacoes"),
        "pct_quimioprofilaxia_dm_48h": ("dm_quimio_48h", "dm_casos"),
    }
    legacy = legacy.copy()
    legacy["_code"] = legacy["codigo_municipio_v17"].map(normalize_municipality_code)
    vnext = vnext.copy()
    vnext["_code"] = vnext["codigo_municipio"].map(normalize_municipality_code)

    compared = 0
    mismatches = []
    for _, row in legacy.iterrows():
        code = row["_code"]
        if not code:
            continue
        for metric, pair in metric_map.items():
            num_col, den_col = pair
            if metric not in legacy.columns:
                continue
            sub = vnext[(vnext["_code"] == code) & (vnext["indicador"] == metric)]
            if sub.empty:
                mismatches.append({"code": code, "metric": metric, "type": "missing_vnext"})
                continue
            target = sub.iloc[0]
            compared += 1
            for source_col, target_col in [(metric, "valor_pct"), (num_col, "numerador"), (den_col, "denominador")]:
                if source_col not in legacy.columns:
                    continue
                a = row.get(source_col)
                b = target.get(target_col)
                if pd.isna(a) and pd.isna(b):
                    continue
                try:
                    equal = abs(float(a) - float(b)) < 1e-9
                except Exception:
                    equal = str(a) == str(b)
                if not equal:
                    mismatches.append({
                        "code": code, "metric": metric, "type": target_col,
                        "source": None if pd.isna(a) else a,
                        "vnext": None if pd.isna(b) else b,
                    })

    if mismatches:
        return [_issue(
            "module12:reconciliation", "fail",
            f"{len(mismatches)} divergência(s) entre módulo 12 e VNext.",
            compared_n=compared, mismatches=mismatches[:100],
        )]
    return [_issue(
        "module12:reconciliation", "pass",
        f"{compared} combinação(ões) município×indicador reconciliada(s) sem divergência.",
        compared_n=compared,
    )]


def validate_signals(outdir: str | Path) -> list[dict[str, Any]]:
    root = Path(outdir)
    signals = _read_csv(root / "sinais_municipais_vnext.csv")
    if signals.empty:
        return [_issue("signals", "attention", "Nenhum sinal VNext publicado.")]
    required = {"codigo_municipio", "rule_id", "valor", "fontes"}
    missing = sorted(required.difference(signals.columns))
    if missing:
        return [_issue("signals", "fail", f"Colunas obrigatórias ausentes: {missing}")]
    bad_source = signals["fontes"].fillna("").astype(str).str.strip().eq("")
    bad_rule = signals["rule_id"].fillna("").astype(str).str.strip().eq("")
    bad_code = signals["codigo_municipio"].map(normalize_municipality_code).eq("")
    bad_n = int((bad_source | bad_rule | bad_code).sum())
    if bad_n:
        return [_issue("signals", "fail", f"{bad_n} sinal(is) sem fonte, regra ou chave territorial válida.")]
    return [_issue("signals", "pass", f"{len(signals)} sinal(is) com regra, fonte e chave territorial.")]


def validate_artifact_divergences(outdir: str | Path) -> list[dict[str, Any]]:
    root = Path(outdir)
    frame = _read_csv(root / "divergencias_vnext.csv")
    if frame.empty:
        return [_issue("artifacts", "attention", "divergencias_vnext.csv ausente ou vazio.")]
    blocking = {"erro_leitura", "sem_chave_territorial", "vazio"}
    bad = frame[frame["status"].astype(str).isin(blocking)] if "status" in frame.columns else pd.DataFrame()
    if not bad.empty:
        return [_issue(
            "artifacts", "fail",
            f"{len(bad)} artefato(s) com divergência bloqueante.",
            rows=bad.to_dict(orient="records"),
        )]
    absent = int((frame["status"].astype(str) == "ausente").sum()) if "status" in frame.columns else 0
    status = "attention" if absent else "pass"
    detail = f"{absent} artefato(s) opcional(is)/esperado(s) ausente(s)." if absent else "Sem divergências bloqueantes."
    return [_issue("artifacts", status, detail)]


def build_validation_report(outdir: str | Path) -> dict[str, Any]:
    checks = []
    checks.extend(validate_territorial_uniqueness(outdir))
    checks.extend(validate_module12_indicators(outdir))
    checks.extend(validate_signals(outdir))
    checks.extend(validate_artifact_divergences(outdir))
    fail_n = sum(1 for c in checks if c["status"] == "fail")
    attention_n = sum(1 for c in checks if c["status"] == "attention")
    overall = "fail" if fail_n else ("attention" if attention_n else "pass")
    return {
        "schema_version": "vnext-validation-1",
        "overall_status": overall,
        "fail_n": fail_n,
        "attention_n": attention_n,
        "checks": checks,
    }


def publish_validation_report(outdir: str | Path) -> dict[str, Path]:
    root = Path(outdir)
    report = build_validation_report(root)
    json_path = root / "validacao_vnext.json"
    md_path = root / "VALIDACAO_VNEXT.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Validação Meningites VNext",
        "",
        f"**Status geral:** {report['overall_status'].upper()}",
        f"**Falhas:** {report['fail_n']} · **Atenções:** {report['attention_n']}",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"- **{check['status'].upper()}** · {check['check_id']} — {check['detail']}")
    lines += [
        "",
        "## Gate",
        "",
        "- PASS: apto a avançar tecnicamente, ainda sujeito à revisão humana.",
        "- ATTENTION: revisar pendências antes de ativação permanente.",
        "- FAIL: não integrar ao pipeline principal/produção.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"validation_json": json_path, "validation_md": md_path}
