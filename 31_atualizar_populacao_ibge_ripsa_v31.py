# -*- coding: utf-8 -*-
"""
31_atualizar_populacao_ibge_ripsa_v31.py
Completa `populacao_padronizada_mt.csv` com estimativas municipais 2010–2019
(RIPSA / CGIAE-SVSA-MS via repositório popBR_mun), sem sobrescrever 2020–2025
já usados no painel.

Fonte pública (formato longo):
  https://raw.githubusercontent.com/lsbastos/popBR_mun/refs/heads/master/popBR2000-2024.long.csv
Origem dos dados brutos: estimativas CGI Demográfico/RIPSA e CGIAE/SVSA/MS
(ftp DATASUS POPSVS / TabNet).

Não inventa 2026: se IBGE/TCU ainda não publicou, o ano fica sem denominador
(transparência V28).

Uso:
  py -3.13 31_atualizar_populacao_ibge_ripsa_v31.py
  py -3.13 00_base_unica_meningites_v17.py
  py -3.13 28_indicadores_novos_v28.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, REL, ROOT

URL_POP_LONG = (
    "https://raw.githubusercontent.com/lsbastos/popBR_mun/refs/heads/master/"
    "popBR2000-2024.long.csv"
)
OUT_CSV = ROOT / "populacao_padronizada_mt.csv"
META_JSON = OUT / "populacao_fonte_meta_v31.json"
BACKUP = ROOT / "populacao_padronizada_mt_backup_antes_v31.csv"

ANOS_COMPLETAR = list(range(2010, 2020))  # 2010–2019


def _cod6(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(r"\D", "", regex=True)
    s = s.str.zfill(6).str[:6]
    return s


def load_local() -> pd.DataFrame:
    if not OUT_CSV.exists():
        return pd.DataFrame(columns=["codigo_municipio", "ano", "populacao"])
    df = pd.read_csv(OUT_CSV, dtype={"codigo_municipio": str})
    df["codigo_municipio"] = _cod6(df["codigo_municipio"])
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
    return df.dropna(subset=["codigo_municipio", "ano", "populacao"])


def fetch_ripsa_mt() -> pd.DataFrame:
    raw = pd.read_csv(URL_POP_LONG, dtype={"MUNCOD": str})
    raw["codigo_municipio"] = _cod6(raw["MUNCOD"])
    mt = raw[raw["codigo_municipio"].str.startswith("51")].copy()
    mt["ano"] = pd.to_numeric(mt["Ano"], errors="coerce").astype("Int64")
    mt["populacao"] = pd.to_numeric(mt["POP"], errors="coerce")
    mt = mt.dropna(subset=["codigo_municipio", "ano", "populacao"])
    mt = mt[mt["ano"].isin(ANOS_COMPLETAR)]
    return (
        mt[["codigo_municipio", "ano", "populacao"]]
        .drop_duplicates(["codigo_municipio", "ano"], keep="last")
        .astype({"populacao": int})
    )


def main() -> int:
    OUT.mkdir(exist_ok=True)
    REL.mkdir(exist_ok=True)

    local = load_local()
    if not local.empty:
        local.to_csv(BACKUP, index=False, encoding="utf-8-sig")
        print(f"[OK] Backup: {BACKUP.name} ({len(local)} linhas)")

    print(f"[INFO] Baixando estimativas RIPSA/MS …")
    ripsa = fetch_ripsa_mt()
    print(
        f"[OK] RIPSA MT 2010–2019: {len(ripsa)} linhas · "
        f"{ripsa['codigo_municipio'].nunique()} municípios"
    )

    # Preserva anos já existentes no arquivo local (não sobrescreve 2020–2025)
    anos_local = set(local["ano"].dropna().astype(int).tolist()) if not local.empty else set()
    add = ripsa[~ripsa["ano"].isin(anos_local)].copy()
    if not local.empty:
        merged = pd.concat([local, add], ignore_index=True)
    else:
        merged = add.copy()

    merged = (
        merged.drop_duplicates(["codigo_municipio", "ano"], keep="first")
        .sort_values(["codigo_municipio", "ano"])
        .reset_index(drop=True)
    )
    merged["populacao"] = merged["populacao"].astype(int)
    merged.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    anos = sorted(merged["ano"].dropna().astype(int).unique().tolist())
    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "arquivo": OUT_CSV.name,
        "n_linhas": int(len(merged)),
        "n_municipios": int(merged["codigo_municipio"].nunique()),
        "anos": anos,
        "anos_adicionados_ripsa": sorted(add["ano"].dropna().astype(int).unique().tolist()),
        "anos_preservados_locais": sorted(anos_local),
        "fonte_ripsa_url": URL_POP_LONG,
        "fonte_ripsa_descricao": (
            "Estimativas populacionais municipais CGI Demográfico/RIPSA e "
            "CGIAE/SVSA/MS (popBR_mun / DATASUS POPSVS)."
        ),
        "politica": (
            "Anos já presentes em populacao_padronizada_mt.csv não são sobrescritos. "
            "2026 não é inventado."
        ),
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# População municipal MT — atualização V31",
        "",
        f"**Gerado em:** {meta['gerado_em']}",
        "",
        f"- Arquivo: `{OUT_CSV.name}`",
        f"- Municípios: **{meta['n_municipios']}** · Linhas: **{meta['n_linhas']}**",
        f"- Anos cobertos: **{anos[0]}–{anos[-1]}**" if anos else "- Anos: —",
        f"- Anos adicionados (RIPSA/MS): {meta['anos_adicionados_ripsa']}",
        f"- Anos preservados (arquivo local): {meta['anos_preservados_locais']}",
        "",
        "## Próximo passo",
        "",
        "```bat",
        "py -3.13 00_base_unica_meningites_v17.py",
        "py -3.13 28_indicadores_novos_v28.py",
        "```",
        "",
    ]
    (REL / "POPULACAO_IBGE_RIPSA_V31.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[OK] {OUT_CSV} · anos={anos}")
    print(f"[OK] Meta: {META_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
