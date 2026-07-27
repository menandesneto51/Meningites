# -*- coding: utf-8 -*-
"""
00_base_unica_meningites_v17.py
Cria base única V17 sem perda de colunas originais e com nomenclatura:
"Classificação agrupada".

Fonte SINAN (prioridade):
  1) entradas_linkage/sinan_meningites_dw.csv  ← dbo.VW_SINAN_MENINGITE (DW SES/MT)
  2) meningite.csv / meningite_*_mt.csv        ← exportação local legada

Env:
  MENINGITES_SINAN_SOURCE=auto|dw|local   (default: auto)
"""

from pathlib import Path
import json
import os
import re
from datetime import datetime
import numpy as np
import pandas as pd
from meningites_v17_common import *

DW_SINAN = ROOT / "entradas_linkage" / "sinan_meningites_dw.csv"


def resolve_sinan_source() -> tuple[Path, str]:
    """Retorna (path, rotulo_fonte)."""
    mode = (os.getenv("MENINGITES_SINAN_SOURCE") or "auto").strip().lower()
    local = find_file(["meningite.csv", "meningite_2010_2026_mt.csv", "meningite_2020_2025_mt.csv"])

    if mode == "dw":
        if not DW_SINAN.exists():
            raise FileNotFoundError(
                f"MENINGITES_SINAN_SOURCE=dw mas não existe {DW_SINAN}. "
                "Rode: py -3.13 19_dw_descobrir_e_extrair_v23.py"
            )
        return DW_SINAN, "DW_VW_SINAN_MENINGITE"
    if mode == "local":
        if local is None:
            raise FileNotFoundError("MENINGITES_SINAN_SOURCE=local: meningite.csv não encontrado.")
        return local, "LOCAL_CSV"

    # auto: preferir DW se existir
    if DW_SINAN.exists():
        return DW_SINAN, "DW_VW_SINAN_MENINGITE"
    if local is not None:
        return local, "LOCAL_CSV"
    raise FileNotFoundError(
        "Não encontrei sinan_meningites_dw.csv (DW) nem meningite.csv. "
        "Rode 19_dw_descobrir_e_extrair_v23.py ou deposite meningite.csv."
    )


def audit_local_vs_dw(chosen: Path, fonte: str) -> dict:
    """Compara DW × local quando ambos existem (não altera a base)."""
    local = find_file(["meningite.csv", "meningite_2010_2026_mt.csv", "meningite_2020_2025_mt.csv"])
    res = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "fonte_escolhida": fonte,
        "arquivo_escolhido": chosen.name,
        "modo": os.getenv("MENINGITES_SINAN_SOURCE") or "auto",
    }
    if not DW_SINAN.exists() or local is None:
        res["comparacao"] = "parcial (só uma fonte disponível)"
        return res

    dw = read_csv_smart(DW_SINAN)
    loc = read_csv_smart(local)
    a = set(loc.get("NumeroNotificacao", pd.Series(dtype=object)).astype(str))
    b = set(dw.get("NumeroNotificacao", pd.Series(dtype=object)).astype(str))
    a.discard("nan")
    b.discard("nan")
    res["comparacao"] = {
        "local_arquivo": local.name,
        "local_n": int(len(loc)),
        "local_unique_notif": len(a),
        "dw_n": int(len(dw)),
        "dw_unique_notif": len(b),
        "overlap": len(a & b),
        "somente_local": len(a - b),
        "somente_dw": len(b - a),
        "ganho_dw_vs_local": len(b - a) - len(a - b),
    }
    only_dw = sorted(b - a)[:200]
    pd.DataFrame({"NumeroNotificacao": only_dw}).to_csv(
        OUT / "auditoria_sinan_somente_dw_v23.csv", index=False, encoding="utf-8-sig"
    )
    only_loc = sorted(a - b)[:200]
    pd.DataFrame({"NumeroNotificacao": only_loc}).to_csv(
        OUT / "auditoria_sinan_somente_local_v23.csv", index=False, encoding="utf-8-sig"
    )
    return res


def parse_dates_smart(series: pd.Series) -> pd.Series:
    """DW usa ISO (YYYY-MM-DD); CSV legado pode vir DD/MM/YYYY.

    Nunca usar dayfirst=True em série predominantemente ISO — o pandas
    inverte mês/dia (ex.: 2026-06-12 → 2026-12-06).
    """
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    s = series
    sample = s.dropna().astype(str).str.strip()
    sample = sample[~sample.str.lower().isin({"", "nan", "none", "*em branco", "null"})].head(120)
    if len(sample) == 0:
        return pd.to_datetime(s, errors="coerce")
    iso_like = float(sample.str.match(r"^\d{4}-\d{2}-\d{2}").mean())
    br_like = float(sample.str.match(r"^\d{1,2}/\d{1,2}/\d{4}").mean())
    if iso_like >= 0.5 or iso_like >= br_like:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def load_population():
    pad = ROOT / "populacao_padronizada_mt.csv"
    if pad.exists():
        pop = read_csv_smart(pad)
        pop.columns = [strip_accents(c).lower().replace(" ", "_") for c in pop.columns]
        if {"codigo_municipio", "ano", "populacao"}.issubset(pop.columns):
            return pop[["codigo_municipio", "ano", "populacao"]].assign(
                codigo_municipio=lambda d: d["codigo_municipio"].astype(str).str.extract(r"(\d{6})", expand=False),
                ano=lambda d: pd.to_numeric(d["ano"], errors="coerce").astype("Int64"),
                populacao=lambda d: pd.to_numeric(d["populacao"], errors="coerce")
            )
    pop_file = find_file(["População Municípios Brasil 2020-2025*.csv", "Populacao Municipios Brasil 2020-2025*.csv", "populacao*.csv"])
    if pop_file is None:
        return pd.DataFrame(columns=["codigo_municipio", "ano", "populacao"])
    p = read_csv_smart(pop_file)
    p.columns = [strip_accents(c).replace("Cód.", "cod_").replace("Cód", "cod").replace(".", "").replace(" ", "_").lower() for c in p.columns]
    code_col = next((c for c in p.columns if "ibge_6" in c or c in {"cod_ibge_6", "codigo_municipio"}), None)
    uf_col = next((c for c in p.columns if c == "uf"), None)
    if code_col is None:
        return pd.DataFrame(columns=["codigo_municipio", "ano", "populacao"])
    if uf_col:
        p = p[p[uf_col].astype(str).str.upper().eq("MT")].copy()
    else:
        p = p[p[code_col].astype(str).str.startswith("510")].copy()
    years = [c for c in p.columns if re.fullmatch(r"20\d{2}", str(c))]
    rows = []
    for _, r in p.iterrows():
        code = norm_code6(r.get(code_col))
        for y in years:
            val = str(r[y]).replace("'", "").replace(".", "").replace(",", ".")
            rows.append({"codigo_municipio": code, "ano": int(y), "populacao": pd.to_numeric(val, errors="coerce")})
    return pd.DataFrame(rows)


def main():
    src, fonte = resolve_sinan_source()
    audit = audit_local_vs_dw(src, fonte)
    (OUT / "auditoria_sinan_fonte_v23.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[FONTE] {fonte} ← {src}")
    if isinstance(audit.get("comparacao"), dict):
        c = audit["comparacao"]
        print(
            f"[AUDITORIA] local={c['local_n']} dw={c['dw_n']} "
            f"overlap={c['overlap']} só_DW={c['somente_dw']} só_local={c['somente_local']}"
        )

    df = read_csv_smart(src)
    df["arquivo_origem_v17"] = src.name
    df["fonte_sinan_v23"] = fonte

    if "UfResidencia" in df.columns:
        antes = len(df)
        df = df[df["UfResidencia"].astype(str).str.upper().str.strip().eq("MT")].copy()
        print(f"[INFO] Filtro residentes MT: {antes} -> {len(df)}")

    sint = parse_dates_smart(df.get("DataPrimeirosSintomas"))
    notif = parse_dates_smart(df.get("DataNotificacao"))
    investig = parse_dates_smart(df.get("DataInvestigacao"))
    intern = parse_dates_smart(df.get("DataInternacao"))
    puncao = parse_dates_smart(df.get("DataPuncaoLombar"))
    qpx = parse_dates_smart(df.get("DataRealizacaoQuimioprofilaxiaComunicantes"))
    evol = parse_dates_smart(df.get("DataEvolucao"))
    enc = parse_dates_smart(df.get("DataEncerramento"))

    df["data_ref_v17"] = sint.fillna(notif)
    df["data_notificacao_v17"] = notif
    df["data_sintomas_v17"] = sint
    df["data_investigacao_v17"] = investig
    df["data_internacao_v17"] = intern
    df["data_puncao_lombar_v17"] = puncao
    df["data_quimioprofilaxia_v17"] = qpx
    df["data_evolucao_ref_v17"] = evol.fillna(enc)
    df["data_encerramento_v17"] = enc
    df = df.dropna(subset=["data_ref_v17"]).copy()

    df["ano_evento_v17"] = df["data_ref_v17"].dt.year
    df["mes_evento_v17"] = df["data_ref_v17"].dt.month
    iso = df["data_ref_v17"].dt.isocalendar()
    df["ano_epi_v17"] = iso.year.astype("Int64")
    df["semana_epi_v17"] = iso.week.astype("Int64")

    df["codigo_municipio_v17"] = df.get("CodigoMunicipioResidencia").map(norm_code6)
    df["municipio_v17"] = df.get("MunicipioResidencia").astype(str).str.strip()
    df["municipio_key_v17"] = df["municipio_v17"].map(text_key)
    df["regional_v17"] = df.get("RegionalResidencia", df.get("RegionalNotificacao", "")).astype(str).str.strip()

    df["evolucao_padronizada_v17"] = df.get("EvolucaoCaso").map(lambda x: decode_basic(x, EVOLUCAO_MAP))
    df["classificacao_caso_padronizada_v17"] = df.get("ClassificacaoCaso").map(lambda x: decode_basic(x, CLASS_CASO_MAP))

    class_code = df.get("ClassificacaoMeningite", df.get("EspecificacaoMeningite", pd.Series(index=df.index, dtype=object)))
    espec = df.get("EspecificacaoMeningite", pd.Series(index=df.index, dtype=object))
    df["classificacao_meningite_detalhada_v17"] = class_code.map(class_detalhada)
    df["classificacao_agrupada_v17"] = [class_agrupada(x, e) for x, e in zip(class_code, espec)]

    df["caso_v17"] = 1
    df["confirmado_v17"] = df["classificacao_caso_padronizada_v17"].eq("Confirmado").astype(int)
    df["obito_meningite_v17"] = df["evolucao_padronizada_v17"].eq("Óbito por meningite").astype(int)
    df["obito_total_v17"] = df["evolucao_padronizada_v17"].isin(["Óbito por meningite", "Óbito por outra causa"]).astype(int)
    df["alta_v17"] = df["evolucao_padronizada_v17"].eq("Alta").astype(int)
    df["hospitalizacao_v17"] = df.get("OcorreuHospitalizacao", pd.Series(index=df.index, dtype=object)).map(simnao_bin).fillna(0).astype(int)

    df["lt_sintomas_notificacao_dias_v17"] = (df["data_notificacao_v17"] - df["data_sintomas_v17"]).dt.days
    df["lt_notificacao_investigacao_dias_v17"] = (df["data_investigacao_v17"] - df["data_notificacao_v17"]).dt.days
    df["lt_sintomas_coleta_dias_v17"] = (df["data_puncao_lombar_v17"] - df["data_sintomas_v17"]).dt.days
    df["lt_notificacao_encerramento_dias_v17"] = (df["data_encerramento_v17"] - df["data_notificacao_v17"]).dt.days
    df["lt_notificacao_quimioprofilaxia_dias_v17"] = (df["data_quimioprofilaxia_v17"] - df["data_notificacao_v17"]).dt.days

    for c in list(df.columns):
        if c.startswith("SinaisESintomas") or c.startswith("DoencasPreexistentes") or c.startswith("Vacina"):
            if not c.endswith("_bin_v17"):
                df[c + "_bin_v17"] = df[c].map(simnao_bin)

    pop = load_population()
    df = df.merge(pop, left_on=["codigo_municipio_v17", "ano_evento_v17"], right_on=["codigo_municipio", "ano"], how="left")
    df = df.drop(columns=["codigo_municipio", "ano"], errors="ignore")
    df = df.rename(columns={"populacao": "populacao_v17"})
    df["tem_denominador_populacional_v17"] = df["populacao_v17"].notna()

    df.to_csv(OUT / "base_unica_meningites_v17.csv", index=False, encoding="utf-8-sig")
    try:
        df.to_parquet(OUT / "base_unica_meningites_v17.parquet", index=False)
    except Exception as e:
        (OUT / "AVISO_PARQUET.txt").write_text(f"Parquet não gerado: {e}", encoding="utf-8")

    dic = pd.DataFrame([
        {"codigo": "1", "classificacao_original": "Meningococcemia", "classificacao_agrupada": "Doença meningocócica"},
        {"codigo": "2", "classificacao_original": "Meningite meningocócica", "classificacao_agrupada": "Doença meningocócica"},
        {"codigo": "3", "classificacao_original": "Meningite meningocócica com meningococcemia", "classificacao_agrupada": "Doença meningocócica"},
        {"codigo": "4", "classificacao_original": "Meningite tuberculosa", "classificacao_agrupada": "Meningite tuberculosa"},
        {"codigo": "5", "classificacao_original": "Meningite por outras bactérias", "classificacao_agrupada": "Meningite bacteriana/outras bactérias"},
        {"codigo": "6", "classificacao_original": "Meningite não especificada", "classificacao_agrupada": "Meningite não especificada"},
        {"codigo": "7", "classificacao_original": "Meningite asséptica", "classificacao_agrupada": "Meningite viral/asséptica"},
        {"codigo": "8", "classificacao_original": "Meningite por outra etiologia", "classificacao_agrupada": "Outras etiologias"},
        {"codigo": "9", "classificacao_original": "Meningite por Hemófilo", "classificacao_agrupada": "Meningite por Hib/Hemófilo"},
        {"codigo": "10", "classificacao_original": "Meningite por Pneumococo", "classificacao_agrupada": "Meningite pneumocócica"},
    ])
    dic.to_csv(OUT / "dicionario_classificacao_agrupada_v17.csv", index=False, encoding="utf-8-sig")

    df.groupby("data_ref_v17").agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
    ).reset_index().sort_values("data_ref_v17").to_csv(OUT / "serie_diaria_v17.csv", index=False, encoding="utf-8-sig")

    semanal = df.groupby(["ano_epi_v17", "semana_epi_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        altas=("alta_v17", "sum"),
    ).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17"])
    semanal["letalidade_confirmados"] = semanal["obitos_meningite"] / semanal["confirmados"].replace(0, np.nan) * 100
    semanal.to_csv(OUT / "serie_semanal_v17.csv", index=False, encoding="utf-8-sig")

    df.groupby(["ano_epi_v17", "semana_epi_v17", "classificacao_agrupada_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        altas=("alta_v17", "sum"),
    ).reset_index().sort_values(["ano_epi_v17", "semana_epi_v17", "classificacao_agrupada_v17"]).to_csv(
        OUT / "serie_semanal_classificacao_agrupada_v17.csv", index=False, encoding="utf-8-sig"
    )

    ind = df.groupby(["ano_evento_v17", "codigo_municipio_v17", "municipio_v17", "regional_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        populacao=("populacao_v17", "max"),
    ).reset_index()
    ind["incidencia_100mil"] = ind["casos"] / ind["populacao"] * 100000
    ind["mortalidade_100mil"] = ind["obitos_meningite"] / ind["populacao"] * 100000
    ind["letalidade_confirmados"] = ind["obitos_meningite"] / ind["confirmados"].replace(0, np.nan) * 100
    ind.to_csv(OUT / "indicadores_municipio_ano_v17.csv", index=False, encoding="utf-8-sig")

    indc = df.groupby(["ano_evento_v17", "codigo_municipio_v17", "municipio_v17", "regional_v17", "classificacao_agrupada_v17"]).agg(
        casos=("caso_v17", "sum"),
        confirmados=("confirmado_v17", "sum"),
        hospitalizacoes=("hospitalizacao_v17", "sum"),
        obitos_meningite=("obito_meningite_v17", "sum"),
        populacao=("populacao_v17", "max"),
    ).reset_index()
    indc["incidencia_100mil"] = indc["casos"] / indc["populacao"] * 100000
    indc["mortalidade_100mil"] = indc["obitos_meningite"] / indc["populacao"] * 100000
    indc["letalidade_confirmados"] = indc["obitos_meningite"] / indc["confirmados"].replace(0, np.nan) * 100
    indc.to_csv(OUT / "indicadores_municipio_ano_classificacao_agrupada_v17.csv", index=False, encoding="utf-8-sig")

    cmp = audit.get("comparacao") if isinstance(audit.get("comparacao"), dict) else {}
    lines = [
        "# Base única SINAN — fonte DW V23",
        "",
        f"**Fonte:** `{fonte}` ← `{src.name}`",
        f"**Residentes MT:** {len(df)} casos | **Colunas:** {df.shape[1]}",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
    ]
    if cmp:
        lines += [
            "## Auditoria DW × local",
            "",
            f"- Local (`{cmp.get('local_arquivo')}`): {cmp.get('local_n')} linhas",
            f"- DW (`VW_SINAN_MENINGITE`): {cmp.get('dw_n')} linhas",
            f"- Overlap notificações: {cmp.get('overlap')}",
            f"- Somente no DW: **{cmp.get('somente_dw')}** (ver `auditoria_sinan_somente_dw_v23.csv`)",
            f"- Somente no local: {cmp.get('somente_local')}",
            "",
        ]
    lines += [
        "## Como forçar fonte",
        "",
        "```powershell",
        "$env:MENINGITES_SINAN_SOURCE='dw'     # só DW",
        "$env:MENINGITES_SINAN_SOURCE='local'  # só CSV legado",
        "$env:MENINGITES_SINAN_SOURCE='auto'   # DW se existir (padrão)",
        "py -3.13 00_base_unica_meningites_v17.py",
        "```",
        "",
    ]
    (REL / "BASE_UNICA_FONTE_DW_V23.md").write_text("\n".join(lines), encoding="utf-8")

    print("[OK] Base única V17 gerada.")
    print("[INFO] Linhas:", len(df), "| Colunas:", df.shape[1])
    print(df["classificacao_agrupada_v17"].value_counts().to_string())


if __name__ == "__main__":
    main()
