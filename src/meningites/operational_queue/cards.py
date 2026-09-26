"""Cards municipais VNext em Markdown + índice estruturado."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


def _safe(value, fallback="N/D"):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "<na>"} else fallback


def _fmt_num(value):
    if value is None or pd.isna(value):
        return "N/D"
    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return f"{number:.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(value)


def build_municipal_cards(
    outdir: str | Path,
    situation: pd.DataFrame,
    signals: pd.DataFrame,
    indicators: pd.DataFrame,
) -> tuple[Path, Path]:
    root = Path(outdir)
    cards_dir = root / "cards_municipais_vnext"
    cards_dir.mkdir(parents=True, exist_ok=True)
    index_rows = []

    for _, row in situation.iterrows():
        code = str(row["codigo_municipio"])
        name = _safe(row.get("municipio"), code)
        sig = signals[signals["codigo_municipio"].astype(str).eq(code)] if not signals.empty else pd.DataFrame()
        ind = indicators[indicators["codigo_municipio"].astype(str).eq(code)] if not indicators.empty else pd.DataFrame()

        lines = [
            "# Meningites — Situação Municipal VNext",
            "",
            f"**Município:** {name}  ",
            f"**Código:** {code}",
            "",
            "## Síntese operacional",
            "",
            f"- Sinais ativos: **{len(sig)}**",
            f"- Itens fila CIEVS: **{_fmt_num(row.get('fila_cievs_n'))}**",
            f"- Pendências GAL/tipagem: **{_fmt_num(row.get('gal_tipagem_pendente_n'))}**",
            f"- SIH sem vínculo SINAN: **{_fmt_num(row.get('sih_sem_sinan_n'))}**",
            f"- RedCap sem vínculo SINAN: **{_fmt_num(row.get('redcap_sem_sinan_n'))}**",
        ]

        if "v25_score_risco_nt154_v25" in row.index and pd.notna(row.get("v25_score_risco_nt154_v25")):
            lines += [
                "",
                "## Contexto do módulo 26",
                "",
                f"- Score V25: **{_fmt_num(row.get('v25_score_risco_nt154_v25'))}**",
                f"- Prioridade V25: **{_safe(row.get('v25_prioridade'))}**",
                f"- DM 90 dias: **{_fmt_num(row.get('v25_dm_90d'))}**",
                f"- DM laboratorial 90 dias: **{_fmt_num(row.get('v25_dm_lab_90d'))}**",
                "",
                "> Contexto reproduzido do módulo 26; não constitui novo gatilho VNext.",
            ]

        if "cipv_doses_ano_mais_recente" in row.index and pd.notna(row.get("cipv_doses_ano_mais_recente")):
            lines += [
                "",
                "## Imunização — contexto CIPV",
                "",
                f"- Ano mais recente disponível: **{_fmt_num(row.get('cipv_ano_mais_recente'))}**",
                f"- Doses registradas no ano: **{_fmt_num(row.get('cipv_doses_ano_mais_recente'))}**",
                "",
                "> Número de doses registradas; não equivale a cobertura populacional.",
            ]

        lines += ["", "## Indicadores operacionais municipais", ""]
        if ind.empty:
            lines.append("Indicadores municipais do módulo 12 não disponíveis para este município.")
        else:
            for _, indicator in ind.iterrows():
                denom = _fmt_num(indicator.get("denominador"))
                value = _fmt_num(indicator.get("valor_pct"))
                lines.append(f"- **{indicator['indicador_rotulo']}**: {value}% (denominador: {denom})")
            first = ind.iloc[0]
            lines += [
                "",
                f"Referência: {_safe(first.get('referencia_periodo'))} — {_safe(first.get('referencia_fonte'))}.",
                f"Vigência registrada desde: {_safe(first.get('referencia_vigencia_desde'))}.",
                "",
                "> O módulo municipal atual não exporta todos os numeradores; o VNext não os reconstrói por arredondamento.",
            ]

        lines += ["", "## Sinais e ações", ""]
        if sig.empty:
            lines.append("Nenhum sinal VNext ativo nas fontes integradas.")
        else:
            for _, signal in sig.iterrows():
                lines += [
                    f"### {signal['titulo']}",
                    f"- Prioridade: **{signal['prioridade']}**",
                    f"- Regra: {signal['rule_id']}",
                    f"- Valor / limiar: {_fmt_num(signal.get('valor'))} / {_fmt_num(signal.get('limiar'))}",
                    f"- Fonte(s): {_safe(signal.get('fontes'))}",
                    f"- Ação sugerida: {_safe(signal.get('acoes_sugeridas'))}",
                    "",
                ]

        lines += [
            "## Procedência",
            "",
            f"Fontes integradas: {_safe(row.get('fontes'))}.",
            "",
            "_Card derivado automaticamente. Confirmar dados-fonte antes de decisão operacional._",
        ]

        filename = re.sub(r"[^0-9A-Za-z_-]+", "_", code) + ".md"
        path = cards_dir / filename
        path.write_text("\n".join(lines), encoding="utf-8")
        index_rows.append({
            "codigo_municipio": code,
            "municipio": name,
            "arquivo": str(path.relative_to(root)),
            "sinais_n": int(len(sig)),
            "indicadores_n": int(len(ind)),
        })

    index_path = root / "cards_municipais_vnext_index.csv"
    pd.DataFrame(index_rows).to_csv(index_path, index=False, encoding="utf-8-sig")
    manifest_path = root / "cards_municipais_vnext_manifest.json"
    manifest_path.write_text(
        json.dumps(index_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index_path, manifest_path
