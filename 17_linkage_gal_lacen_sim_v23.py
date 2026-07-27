# -*- coding: utf-8 -*-
"""
17_linkage_gal_lacen_sim_v23.py
Preparação e linkage probabilístico SINAN ↔ GAL/LACEN/SIM.

- Procura arquivos em entradas_linkage/ (e raiz) com padrões flexíveis.
- Se não houver fonte externa, gera templates + relatório de prontidão e
  um enriquecimento interno (proxy) com campos laboratoriais/evolução do SINAN.
- Não exige nome do paciente (base MT pode estar sem identificadores nominais).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, ROOT, MISSING, fmt_num, load_base_v17, text_key

ENTRADAS = ROOT / "entradas_linkage"
ENTRADAS.mkdir(exist_ok=True)

# Preferência: extratos do DW SES/MT (módulo 19)
PREFERRED = {
    "gal": ["gal_lacen_meningites.csv", "gal_lacen_meningites.parquet"],
    "lacen": ["gal_lacen_meningites.csv", "gal_lacen_meningites.parquet"],  # LACEN via VW_GAL
    "sim": ["sim_obitos_meningites.csv", "sim_obitos_meningites.parquet"],
}

PATTERNS = {
    "gal": ["*gal*.csv", "*GAL*.csv", "*gal*.xlsx", "*resultado*lab*.csv"],
    "lacen": ["*lacen*.csv", "*LACEN*.csv", "*lacen*.xlsx"],
    "sim": ["*sim_obito*.csv", "*obito*.csv", "*mortalidade*.csv", "*sim*.xlsx"],
}

EXCLUDE_NAME = re.compile(r"(sinasc|sinan|cnes|template_|dw_schema|dw_meta)", re.I)

# Campos candidatos por domínio (inclui nomes do DW SES/MT)
MAP_CANDIDATES = {
    "numero_notificacao": [
        "numeronotificacao", "numnotificacaosinan", "num_notificacao_sinan",
        "nu_notificacao", "nnotif", "id_sinan", "numero",
    ],
    "data_nascimento": [
        "datanascimento", "datanascimentopaciente", "data_nascimento_paciente",
        "data_nascimento_paciente_dt", "dt_nasc", "dn", "nascimento",
    ],
    "sexo": ["sexo", "sexopaciente", "sexo_paciente", "tp_sexo"],
    "municipio": [
        "municipio", "municipioresidencia", "municipioresidenciapaciente",
        "nm_municipio", "mun_res",
    ],
    "codigo_municipio": [
        "codigomunicipio", "codigomunicipioresidencia",
        "ibgemunicipioresidenciapaciente", "ibge_municipio_residencia_paciente",
        "cod_mun", "co_municipio", "ibge", "codibge",
    ],
    "data_coleta": ["datacoleta", "data_coleta", "data_coleta_dt", "dt_coleta", "data_exame", "dt_exame"],
    "data_resultado": [
        "dataresultado", "dataliberacao", "data_liberacao", "data_liberacao_dt",
        "dt_resultado", "data_liberacao",
    ],
    "metodo": ["metodo", "metodologia", "exame", "procedimento", "tipo_exame"],
    "resultado": [
        "resultado", "resultadoexame", "camporesultado1", "campo_resultado_1",
        "ds_resultado", "observacaoresultado",
    ],
    "agente": ["agente", "microorganismo", "etiologia", "germe", "agravogal", "agravo_gal"],
    "data_obito": ["dataobito", "dt_obito", "dtobit"],
    "cid": ["cid", "causabasica", "causabas", "causa_basica", "cid10", "cid_agravo_gal"],
}


def _norm_col(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text_key(c).lower().replace(" ", ""))


def read_any_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        for sep in [";", ",", "\t", "|"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                if df.shape[1] > 1:
                    return df
            except Exception:
                pass
    return pd.read_csv(path, low_memory=False)


def find_sources() -> dict[str, Path | None]:
    found = {}
    for kind, pats in PATTERNS.items():
        hit = None
        # 1) arquivos preferenciais do DW
        for base in [ENTRADAS, ROOT]:
            for name in PREFERRED.get(kind, []):
                p = base / name
                if p.exists() and p.is_file():
                    hit = p
                    break
            if hit:
                break
        # 2) padrões flexíveis
        if hit is None:
            for base in [ENTRADAS, ROOT]:
                for pat in pats:
                    hits = sorted(base.glob(pat))
                    hits = [
                        h for h in hits
                        if "saida_" not in str(h)
                        and "_arquivo" not in str(h)
                        and not h.name.upper().startswith("TEMPLATE_")
                        and not EXCLUDE_NAME.search(h.name)
                    ]
                    if hits:
                        hit = hits[0]
                        break
                if hit:
                    break
        found[kind] = hit
    return found


def map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cols = {_norm_col(c): c for c in df.columns}
    mapping = {}
    out = df.copy()
    for canon, cands in MAP_CANDIDATES.items():
        for cand in cands:
            key = _norm_col(cand)
            if key in cols:
                mapping[canon] = cols[key]
                out[canon] = df[cols[key]]
                break
    return out, mapping


def write_templates():
    gal = pd.DataFrame([{
        "NumeroNotificacao": "",
        "DataNascimento": "2000-01-15",
        "Sexo": "M",
        "CodigoMunicipio": "510340",
        "Municipio": "CUIABA",
        "DataColeta": "2024-03-01",
        "DataResultado": "2024-03-03",
        "Metodo": "PCR",
        "Resultado": "POSITIVO",
        "Agente": "Neisseria meningitidis",
    }])
    lacen = gal.copy()
    sim = pd.DataFrame([{
        "DataNascimento": "2000-01-15",
        "Sexo": "M",
        "CodigoMunicipio": "510340",
        "Municipio": "CUIABA",
        "DataObito": "2024-03-10",
        "CID": "A39",
        "NumeroNotificacao": "",
    }])
    gal.to_csv(ENTRADAS / "TEMPLATE_gal_resultados.csv", index=False, encoding="utf-8-sig")
    lacen.to_csv(ENTRADAS / "TEMPLATE_lacen_resultados.csv", index=False, encoding="utf-8-sig")
    sim.to_csv(ENTRADAS / "TEMPLATE_sim_obitos.csv", index=False, encoding="utf-8-sig")
    readme = """# Entradas de linkage (GAL / LACEN / SIM / CNES / SINASC)

## Preferencial — extrair do Data Warehouse SES/MT

```bat
py -3.13 19_dw_descobrir_e_extrair_v23.py
```

Gera automaticamente (quando a rede SES estiver disponível):
- `gal_lacen_meningites.csv` ← `dbo.VW_GAL`
- `sim_obitos_meningites.csv` ← `dbo.SIM` (CIDs A39/G00–G03/A87)
- `sinan_meningites_dw.csv` ← `dbo.VW_SINAN_MENINGITE`
- `sinasc_dw.csv` ← `dbo.SINASC` / `VW_SINASC`
- `cnes_estabelecimentos.csv` ← `dbo.CNES_ESTABELECIMENTOS`

Credenciais: reutiliza `.env` de Ondas de calor / Clima-Saúde (ver `.env.example`).

## Alternativa — depositar exportações manuais
- `*gal*.csv` / `*lacen*.csv` / `*sim_obito*.csv`

Após os arquivos, rode:
```
py -3.13 17_linkage_gal_lacen_sim_v23.py
```
"""
    (ENTRADAS / "README_LINKAGE.md").write_text(readme, encoding="utf-8")


def parse_dates_smart(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    s = series
    sample = s.dropna().astype(str).str.strip()
    sample = sample[~sample.str.lower().isin({"", "nan", "none", "*em branco", "null"})].head(80)
    if len(sample) == 0:
        return pd.to_datetime(s, errors="coerce")
    iso_like = float(sample.str.match(r"^\d{4}-\d{2}-\d{2}").mean())
    if iso_like >= 0.5:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def prepare_sinan(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["_sid"] = np.arange(len(d))
    d["numero_notificacao"] = d.get("NumeroNotificacao", pd.Series(index=d.index)).astype(str).str.strip()
    d["data_nascimento"] = parse_dates_smart(d.get("DataNascimento"))
    d["sexo"] = d.get("SexoPaciente", pd.Series(index=d.index)).map(lambda x: text_key(x)[:1] if pd.notna(x) else "")
    d["sexo"] = d["sexo"].replace({"MASCULINO": "M", "FEMININO": "F", "1": "M", "2": "F"})
    d["codigo_municipio"] = d.get("codigo_municipio_v17", d.get("CodigoMunicipioResidencia")).astype(str).str.extract(r"(\d{6})", expand=False)
    d["data_evento"] = pd.to_datetime(d.get("data_ref_v17"), errors="coerce")
    d["ano_nasc"] = d["data_nascimento"].dt.year
    return d


def prepare_external(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    mapped, mapping = map_columns(df)
    mapped["_eid"] = np.arange(len(mapped))
    mapped["_fonte"] = kind
    mapped["_mapping"] = str(mapping)
    if "data_nascimento" in mapped.columns:
        mapped["data_nascimento"] = parse_dates_smart(mapped["data_nascimento"])
        mapped["ano_nasc"] = mapped["data_nascimento"].dt.year
    else:
        mapped["ano_nasc"] = np.nan
    if "sexo" in mapped.columns:
        mapped["sexo"] = mapped["sexo"].map(lambda x: text_key(x)[:1] if pd.notna(x) else "")
        mapped["sexo"] = mapped["sexo"].replace({"MASCULINO": "M", "FEMININO": "F", "1": "M", "2": "F"})
    else:
        mapped["sexo"] = ""
    if "codigo_municipio" in mapped.columns:
        mapped["codigo_municipio"] = mapped["codigo_municipio"].astype(str).str.extract(r"(\d{6})", expand=False)
    elif "municipio" in mapped.columns:
        mapped["codigo_municipio"] = np.nan
        mapped["municipio_key"] = mapped["municipio"].map(text_key)
    if "numero_notificacao" in mapped.columns:
        mapped["numero_notificacao"] = mapped["numero_notificacao"].astype(str).str.strip()
    for c in ["data_coleta", "data_resultado", "data_obito"]:
        if c in mapped.columns:
            mapped[c] = parse_dates_smart(mapped[c])
    return mapped


def score_pair(srow, erow) -> tuple[float, list[str]]:
    score = 0.0
    motivos = []
    # Notificação idêntica = quase certeza
    sn = str(srow.get("numero_notificacao", "")).strip()
    en = str(erow.get("numero_notificacao", "")).strip()
    if sn and en and sn not in {"nan", "None", ""} and sn == en:
        return 1.0, ["numero_notificacao_igual"]

    if pd.notna(srow.get("data_nascimento")) and pd.notna(erow.get("data_nascimento")):
        if srow["data_nascimento"] == erow["data_nascimento"]:
            score += 0.45
            motivos.append("data_nascimento")
        elif abs((srow["data_nascimento"] - erow["data_nascimento"]).days) <= 1:
            score += 0.30
            motivos.append("data_nascimento_aprox")

    if srow.get("sexo") and erow.get("sexo") and srow["sexo"] == erow["sexo"]:
        score += 0.15
        motivos.append("sexo")

    sc = str(srow.get("codigo_municipio", ""))
    ec = str(erow.get("codigo_municipio", ""))
    if sc and ec and sc == ec and sc not in {"nan", "None"}:
        score += 0.25
        motivos.append("codigo_municipio")

    # Proximidade temporal evento ↔ coleta/óbito
    sev = srow.get("data_evento")
    for dc in ["data_coleta", "data_resultado", "data_obito"]:
        if pd.notna(sev) and pd.notna(erow.get(dc)):
            delta = abs((sev - erow[dc]).days)
            if delta <= 15:
                score += 0.15
                motivos.append(f"{dc}_15d")
                break
            if delta <= 45:
                score += 0.08
                motivos.append(f"{dc}_45d")
                break
    return min(score, 0.99), motivos


def link_source(sinan: pd.DataFrame, ext: pd.DataFrame, kind: str, min_score: float = 0.55) -> pd.DataFrame:
    if ext.empty:
        return pd.DataFrame()
    rows = []
    # Blocking: sexo + ano nasc, ou município
    sinan = sinan.copy()
    ext = ext.copy()

    # Match por número de notificação (vetorizado)
    if "numero_notificacao" in ext.columns:
        s = sinan[sinan["numero_notificacao"].notna() & ~sinan["numero_notificacao"].isin(["", "nan", "None"])]
        e = ext[ext["numero_notificacao"].notna() & ~ext["numero_notificacao"].isin(["", "nan", "None"])]
        m = s.merge(e, on="numero_notificacao", how="inner", suffixes=("_sinan", "_ext"))
        for _, r in m.iterrows():
            rows.append({
                "fonte": kind,
                "sid": r.get("_sid"),
                "eid": r.get("_eid"),
                "score": 1.0,
                "motivos": "numero_notificacao_igual",
                "numero_notificacao": r.get("numero_notificacao"),
                "metodo": r.get("metodo", ""),
                "resultado": r.get("resultado", ""),
                "agente": r.get("agente", ""),
                "cid": r.get("cid", ""),
                "data_obito": r.get("data_obito", pd.NaT),
            })

    # Blocking probabilístico (amostra controlada por blocos)
    for keys in [["sexo", "ano_nasc"], ["codigo_municipio", "sexo"]]:
        if not all(k in sinan.columns and k in ext.columns for k in keys):
            continue
        sg = sinan.dropna(subset=[k for k in keys if k != "sexo"]).groupby(keys, dropna=False)
        eg = ext.dropna(subset=[k for k in keys if k != "sexo"]).groupby(keys, dropna=False)
        common = set(sg.groups) & set(eg.groups)
        for blk in list(common)[:5000]:
            sblk = sg.get_group(blk)
            eblk = eg.get_group(blk)
            # limita explosão
            if len(sblk) * len(eblk) > 2000:
                sblk = sblk.head(40)
                eblk = eblk.head(40)
            for _, srow in sblk.iterrows():
                best = (0.0, None, [])
                for _, erow in eblk.iterrows():
                    sc, mot = score_pair(srow, erow)
                    if sc > best[0]:
                        best = (sc, erow, mot)
                if best[1] is not None and best[0] >= min_score:
                    erow = best[1]
                    rows.append({
                        "fonte": kind,
                        "sid": srow["_sid"],
                        "eid": erow["_eid"],
                        "score": best[0],
                        "motivos": ";".join(best[2]),
                        "numero_notificacao": srow.get("numero_notificacao", ""),
                        "metodo": erow.get("metodo", ""),
                        "resultado": erow.get("resultado", ""),
                        "agente": erow.get("agente", ""),
                        "cid": erow.get("cid", ""),
                        "data_obito": erow.get("data_obito", pd.NaT),
                    })

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    # Melhor match por sid
    out = out.sort_values(["sid", "score"], ascending=[True, False]).drop_duplicates("sid", keep="first")
    return out


def enrich_internal_proxy(sinan: pd.DataFrame) -> pd.DataFrame:
    """Proxy interno enquanto GAL/LACEN/SIM não estão disponíveis."""
    from importlib import import_module
    try:
        labmod = import_module("07_laboratorio_qualidade_meningites_v20")
        lab_code = labmod.lab_code
        result_cols = [c for c in getattr(labmod, "RESULT_COLS", []) if c in sinan.columns]
    except Exception:
        lab_code = None
        result_cols = [c for c in sinan.columns if c.startswith("Resultado") and any(x in c for x in ["PCR", "Cultura", "Latex", "CIE"])]

    d = sinan.copy()
    any_lab = pd.Series(False, index=d.index)
    for c in result_cols:
        if lab_code is not None:
            parsed = d[c].map(lab_code)
            any_lab = any_lab | (parsed == 1)
        else:
            s = d[c].astype(str).map(text_key)
            any_lab = any_lab | s.str.contains("POSIT|DETECT|ISOLAD|REAGEN", na=False) | s.str.fullmatch(r"1|1 0", na=False)

    d["proxy_gal_lacen_positivo_v23"] = any_lab.astype(int)
    d["proxy_sim_obito_sinan_v23"] = pd.to_numeric(d.get("obito_meningite_v17"), errors="coerce").fillna(0).astype(int)
    d["proxy_elegivel_revisao_lab_v23"] = (
        (pd.to_numeric(d.get("confirmado_v17"), errors="coerce").fillna(0) == 1)
        & (~any_lab)
    ).astype(int)
    resumo = pd.DataFrame([{
        "n_casos": len(d),
        "proxy_lab_positivo": int(d["proxy_gal_lacen_positivo_v23"].sum()),
        "proxy_lab_positivo_pct": d["proxy_gal_lacen_positivo_v23"].mean() * 100,
        "proxy_obitos_sinan": int(d["proxy_sim_obito_sinan_v23"].sum()),
        "confirmados_sem_lab_positivo_proxy": int(d["proxy_elegivel_revisao_lab_v23"].sum()),
        "interpretacao": (
            "Proxy interno a partir do SINAN (PCR/cultura/látex/CIE e evolução). "
            "Substituído/complementado quando GAL/LACEN/SIM forem linkados."
        ),
    }])
    return d, resumo


def main():
    write_templates()
    sources = find_sources()
    sinan_raw = load_base_v17()
    sinan = prepare_sinan(sinan_raw)

    status_rows = []
    matches_all = []
    seen_paths: set[str] = set()
    for kind, path in sources.items():
        if path is None:
            status_rows.append({
                "fonte": kind,
                "status": "AUSENTE",
                "arquivo": "",
                "n_registros": 0,
                "n_matches": 0,
                "acao": f"Depositar arquivo em {ENTRADAS.name}/ (ver TEMPLATE_{kind}*.csv)",
            })
            continue
        # Evita linkar 2x o mesmo extrato DW (GAL = LACEN via VW_GAL)
        key = str(path.resolve()).lower()
        if key in seen_paths and kind == "lacen":
            status_rows.append({
                "fonte": kind,
                "status": "OK_MESMO_ARQUIVO_GAL",
                "arquivo": path.name,
                "n_registros": 0,
                "n_matches": 0,
                "acao": "LACEN já coberto por gal_lacen_meningites (VW_GAL); matches em linkage_matches_gal_v23.csv",
            })
            continue
        seen_paths.add(key)
        try:
            raw = read_any_table(path)
            ext = prepare_external(raw, kind)
            linked = link_source(sinan, ext, kind)
            status_rows.append({
                "fonte": kind,
                "status": "OK",
                "arquivo": path.name,
                "n_registros": len(ext),
                "n_matches": len(linked),
                "acao": "Usar matches em alertas/confirmacao laboratorial/obitos",
            })
            if not linked.empty:
                matches_all.append(linked)
                linked.to_csv(OUT / f"linkage_matches_{kind}_v23.csv", index=False, encoding="utf-8-sig")
        except Exception as e:
            status_rows.append({
                "fonte": kind,
                "status": "ERRO",
                "arquivo": path.name if path else "",
                "n_registros": 0,
                "n_matches": 0,
                "acao": str(e),
            })

    status = pd.DataFrame(status_rows)
    status.to_csv(OUT / "linkage_prontidao_v23.csv", index=False, encoding="utf-8-sig")

    if matches_all:
        allm = pd.concat(matches_all, ignore_index=True)
        allm.to_csv(OUT / "linkage_matches_todos_v23.csv", index=False, encoding="utf-8-sig")
    else:
        allm = pd.DataFrame()
        pd.DataFrame(columns=["fonte", "sid", "score", "motivos"]).to_csv(
            OUT / "linkage_matches_todos_v23.csv", index=False, encoding="utf-8-sig"
        )

    enriched, proxy_resumo = enrich_internal_proxy(sinan_raw)
    # Não regrava base completa (OneDrive); exporta colunas proxy + chaves
    keep = [c for c in [
        "NumeroNotificacao", "codigo_municipio_v17", "municipio_v17", "data_ref_v17",
        "confirmado_v17", "classificacao_agrupada_v17", "obito_meningite_v17",
        "proxy_gal_lacen_positivo_v23", "proxy_sim_obito_sinan_v23", "proxy_elegivel_revisao_lab_v23",
    ] if c in enriched.columns]
    enriched[keep].to_csv(OUT / "linkage_proxy_interno_casos_v23.csv", index=False, encoding="utf-8-sig")
    proxy_resumo.to_csv(OUT / "linkage_proxy_interno_resumo_v23.csv", index=False, encoding="utf-8-sig")

    # Casos prioritários para busca ativa em GAL/LACEN
    prior = enriched[enriched.get("proxy_elegivel_revisao_lab_v23", 0) == 1].copy() if "proxy_elegivel_revisao_lab_v23" in enriched.columns else pd.DataFrame()
    if not prior.empty:
        cols = [c for c in keep if c in prior.columns]
        prior[cols].head(500).to_csv(OUT / "linkage_fila_busca_gal_lacen_v23.csv", index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame().to_csv(OUT / "linkage_fila_busca_gal_lacen_v23.csv", index=False, encoding="utf-8-sig")

    # Relatório
    status_txt = status.to_string(index=False)
    proxy_txt = proxy_resumo.to_string(index=False)
    body = "\n".join([
        "# Relatório de linkage GAL / LACEN / SIM — V23",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Prontidão das fontes",
        "",
        "```",
        status_txt,
        "```",
        "",
        "## Proxy interno (SINAN)",
        "",
        "```",
        proxy_txt,
        "```",
        "",
        f"- Matches externos totais: **{len(allm)}**",
        f"- Pasta de entrada: `{ENTRADAS}`",
        "",
        "## Próximos passos",
        "",
        "1. Atualizar extratos DW: `py -3.13 19_dw_descobrir_e_extrair_v23.py`.",
        "2. Rodar novamente `17_linkage_gal_lacen_sim_v23.py`.",
        "3. Usar `linkage_matches_*` para reforçar confirmação laboratorial e óbitos.",
        "",
    ])
    (OUT / "linkage_relatorio_v23.md").write_text(body, encoding="utf-8")
    (ROOT / "relatorios" / "LINKAGE_GAL_LACEN_SIM_V23.md").write_text(body, encoding="utf-8")

    print("[OK] Linkage V23 concluído.")
    print(status.to_string(index=False))
    print(proxy_resumo.to_string(index=False))
    print(f"Templates/README em: {ENTRADAS}")


if __name__ == "__main__":
    main()
