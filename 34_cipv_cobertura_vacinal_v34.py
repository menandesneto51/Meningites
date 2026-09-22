# -*- coding: utf-8 -*-
"""
34_cipv_cobertura_vacinal_v34.py
Cobertura / status vacinal MenACWY–MenC / Hib para vigilância de meningites.

Fontes (offline-safe — ausência não derruba o pipeline):
  1) SINAN (base_unica) — campos vacinais já na ficha (sempre processado se base existir)
  2) CIPV / SI-PNI — entradas_linkage/cipv_doses_meningite.csv (módulo 19), se houver

Saídas (saida_meningites_v17/):
  - cipv_doses_agregadas_v34.csv      (só se extrato CIPV existir; sem PII)
  - cipv_doses_regional_ano_v34.csv   (MenC/MenACWY/Hib/Penta-Hexa por regional×ano)
  - cipv_sinan_status_vacinal_v34.csv (status vacinal SINAN por faixa/etiologia)
  - cipv_kpis_cobertura_v34.csv       (KPIs estaduais / por faixa / regional)
  - cipv_fonte_meta_v34.json
  - relatorios/CIPV_COBERTURA_VACINAL_V34.md

LGPD: nunca grava CPF/CNS/nome. Se o extrato CIPV trouxer documento residual,
a coluna é descartada (hash só se necessário para dedupe interno, não exportado).

Nota: completude do campo vacinal no SINAN ≠ cobertura populacional do PNI.
Cobertura CIPV agregada só aparece quando o extrato DW/CSV estiver disponível —
não inventamos doses.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import (
    OUT,
    REL,
    ROOT,
    load_base_v17,
    norm_code6,
    simnao_bin,
    text_key,
)

ENTRADAS = ROOT / "entradas_linkage"
CIPV_PATH = ENTRADAS / "cipv_doses_meningite.csv"

DM = "Doença meningocócica"
HIB = "Meningite por Hib/Hemófilo"

VACINA_RE = re.compile(
    r"mening|menacwy|menac|menc\b|acwy|haemoph|hemofil|hib\b|penta|hexa",
    re.I,
)


def _pct(num, den) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return float("nan")
    return float(num) / float(den) * 100.0


def _read_cipv() -> pd.DataFrame:
    if not CIPV_PATH.exists() or CIPV_PATH.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(CIPV_PATH, encoding="utf-8-sig", low_memory=False)
    except Exception:
        try:
            return pd.read_csv(CIPV_PATH, encoding="latin1", low_memory=False)
        except Exception:
            return pd.DataFrame()


def _drop_pii(df: pd.DataFrame) -> pd.DataFrame:
    """Remove PII; preserva nomes de vacina/imunobiológico (não são identificadores)."""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    drop = []
    for c in df.columns:
        cl = str(c).lower()
        if re.search(r"vacina|imuno|produto|imunobiolog", cl):
            continue  # NomeVacina / nome_imuno etc.
        if re.search(
            r"nomepaciente|nome_paciente|nomemae|nome_mae|nomepai|nome_pai|"
            r"nomeobito|nome_obito|^nome$|cpf|cns|cartaosus|cartao_sus|"
            r"endereco|logradouro|bairro|cep|telefone|email|doc_|rg\b",
            cl,
            re.I,
        ):
            drop.append(c)
    return df.drop(columns=drop, errors="ignore")


def parse_idade_anos(idade) -> float:
    """Converte idade SINAN (ex.: 011a, 004m, 015d) ou numérica para anos."""
    if pd.isna(idade):
        return np.nan
    if isinstance(idade, (int, float, np.integer, np.floating)):
        v = float(idade)
        return v if v >= 0 else np.nan
    s = str(idade).strip().lower().replace(",", ".")
    if not s or s in {"nan", "none", "<na>"}:
        return np.nan
    m = re.fullmatch(r"(\d+)\s*([amdh])?", s)
    if m:
        n = float(m.group(1))
        u = m.group(2) or "a"
        if u == "a":
            return n
        if u == "m":
            return n / 12.0
        if u in {"d", "h"}:
            return n / 365.25
    m2 = re.search(r"(\d+(?:\.\d+)?)", s)
    if m2:
        return float(m2.group(1))
    return np.nan


def faixa_risco_idade(idade) -> str:
    a = parse_idade_anos(idade)
    if pd.isna(a) or a < 0:
        return "Ignorado"
    if a < 1:
        return "<1 ano"
    if a < 5:
        return "1 a 4 anos"
    if a < 11:
        return "5 a 10 anos"
    if a < 15:
        return "11 a 14 anos"
    if a < 20:
        return "15 a 19 anos"
    return "20+ anos"


# Códigos DATASUS (VW_Vacinas_PNI.co_vacina) → grupo operacional.
SIPNI_CODE_IMUNO = {
    "9": "Hib",
    "17": "Penta/Hexa (Hib)",
    "29": "MenC",
    "42": "Meningocócica (outra)",  # MenB
    "46": "Penta/Hexa (Hib)",
    "73": "MenC",
    "93": "Penta/Hexa (Hib)",
    "102": "MenC",
    "103": "MenACWY",
    "114": "MenACWY",
}


def classificar_imuno(texto: object) -> str:
    if pd.isna(texto):
        return "Outro/ignorado"
    digits = "".join(ch for ch in str(texto) if ch.isdigit())
    if digits:
        code = digits.lstrip("0") or "0"
        if code in SIPNI_CODE_IMUNO:
            return SIPNI_CODE_IMUNO[code]
    t = text_key(texto)
    if not t:
        return "Outro/ignorado"
    if re.search(r"MENACWY|ACWY|TETRAVALENTE.*MENING|MENING.*ACWY", t):
        return "MenACWY"
    if re.search(r"MENING.*C|MENC|CONJUGADA.*MENING|MENINGOCOCICA C", t):
        return "MenC"
    if re.search(r"HIB|HAEMOPH|HEMOFIL", t):
        return "Hib"
    if re.search(r"PENTA|HEXA", t):
        return "Penta/Hexa (Hib)"
    if re.search(r"MENING", t):
        return "Meningocócica (outra)"
    return "Outro/ignorado"


def _pick_col(df: pd.DataFrame, patterns: list[str]) -> str | None:
    for pat in patterns:
        for c in df.columns:
            if re.search(pat, str(c), re.I):
                return str(c)
    return None


def preparar_cipv(raw: pd.DataFrame) -> pd.DataFrame:
    """Normaliza extrato CIPV flexível → colunas canônicas agregáveis."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = _drop_pii(raw).copy()
    vac_c = _pick_col(df, [r"co_vacina", r"sg_vacina", r"ds_vacina", r"vacina", r"imuno", r"produto", r"imunobiolog"])
    mun_c = _pick_col(df, [r"co_municipio", r"codigo.?municipio|ibge|cod_mun|municipio_ibge|cd_mun"])
    mun_nome = _pick_col(df, [r"^municipio$|nome_municipio|municipio_resid"])
    ano_c = _pick_col(df, [r"^ano$|ano_aplic|anoaplic|ano_dose"])
    data_c = _pick_col(df, [r"dt_vacina|data_aplic|dt_aplic|data_dose|dt_dose|data_vacin"])
    dose_c = _pick_col(df, [r"n_doses", r"co_dose", r"dose|nr_dose|numero_dose"])
    ndose_c = _pick_col(df, [r"^n_doses$"])
    idade_c = _pick_col(df, [r"idade|idade_anos|nu_idade"])

    out = pd.DataFrame(index=df.index)
    out["imuno_raw_v34"] = df[vac_c].astype(str) if vac_c else ""
    out["imuno_grupo_v34"] = out["imuno_raw_v34"].map(classificar_imuno)
    if mun_c:
        out["codigo_municipio_v34"] = df[mun_c].map(norm_code6)
    else:
        out["codigo_municipio_v34"] = np.nan
    out["municipio_v34"] = df[mun_nome].astype(str) if mun_nome else ""
    if ano_c:
        out["ano_dose_v34"] = pd.to_numeric(df[ano_c], errors="coerce")
    elif data_c:
        out["ano_dose_v34"] = pd.to_datetime(df[data_c], errors="coerce").dt.year
    else:
        out["ano_dose_v34"] = np.nan
    if ndose_c:
        out["n_doses"] = pd.to_numeric(df[ndose_c], errors="coerce").fillna(1.0)
    else:
        out["n_doses"] = 1.0
    out["dose_v34"] = df[dose_c].astype(str) if dose_c and dose_c != ndose_c else ""
    if idade_c:
        out["idade_anos_v34"] = pd.to_numeric(df[idade_c], errors="coerce")
    else:
        out["idade_anos_v34"] = np.nan
    out["faixa_risco_v34"] = out["idade_anos_v34"].map(faixa_risco_idade)

    # mantém só imunobiológicos de interesse
    keep = out["imuno_grupo_v34"].isin(
        {"MenACWY", "MenC", "Hib", "Penta/Hexa (Hib)", "Meningocócica (outra)"}
    )
    # se o extrato já veio filtrado sem coluna de vacina, mantém tudo
    if vac_c and keep.any():
        out = out.loc[keep].copy()
    elif vac_c:
        # coluna existe mas nada casou — tenta regex na raw
        mask = out["imuno_raw_v34"].str.contains(VACINA_RE, na=False)
        out = out.loc[mask].copy() if mask.any() else out.iloc[0:0].copy()
    return out.reset_index(drop=True)


def mapa_municipio_regional(base: pd.DataFrame) -> pd.DataFrame:
    """Tabela codigo_municipio → regional a partir da base SINAN (sem inventar regionais)."""
    if base is None or base.empty:
        return pd.DataFrame(columns=["codigo_municipio_v34", "regional_v34"])
    mun_c = "codigo_municipio_v17" if "codigo_municipio_v17" in base.columns else None
    reg_c = "regional_v17" if "regional_v17" in base.columns else None
    if not mun_c or not reg_c:
        return pd.DataFrame(columns=["codigo_municipio_v34", "regional_v34"])
    m = base[[mun_c, reg_c]].copy()
    m["codigo_municipio_v34"] = m[mun_c].map(norm_code6)
    m["regional_v34"] = m[reg_c].astype(str).str.strip()
    m = m.dropna(subset=["codigo_municipio_v34"])
    m = m[m["codigo_municipio_v34"].astype(str).str.len() > 0]
    # moda da regional por município (estável)
    modo = (
        m.groupby("codigo_municipio_v34", dropna=False)["regional_v34"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else (s.dropna().iloc[0] if s.dropna().shape[0] else ""))
        .reset_index()
    )
    return modo


def anexar_regional(prep: pd.DataFrame, mapa: pd.DataFrame) -> pd.DataFrame:
    if prep is None or prep.empty:
        return prep if prep is not None else pd.DataFrame()
    out = prep.copy()
    if mapa is None or mapa.empty or "codigo_municipio_v34" not in out.columns:
        out["regional_v34"] = ""
        return out
    out = out.merge(mapa, on="codigo_municipio_v34", how="left")
    out["regional_v34"] = out["regional_v34"].fillna("").astype(str)
    out.loc[out["regional_v34"].isin({"", "nan", "None", "<NA>"}), "regional_v34"] = "Sem regional"
    return out


def agregar_doses_cipv(prep: pd.DataFrame) -> pd.DataFrame:
    if prep is None or prep.empty:
        return pd.DataFrame(columns=[
            "ano_dose_v34", "codigo_municipio_v34", "municipio_v34", "regional_v34",
            "imuno_grupo_v34", "faixa_risco_v34", "n_doses",
        ])
    gcols = [
        c for c in [
            "ano_dose_v34", "codigo_municipio_v34", "municipio_v34", "regional_v34",
            "imuno_grupo_v34", "faixa_risco_v34",
        ] if c in prep.columns
    ]
    peso = "n_doses" if "n_doses" in prep.columns else None
    if peso:
        agg = (
            prep.groupby(gcols, dropna=False)[peso]
            .sum()
            .reset_index(name="n_doses")
        )
    else:
        agg = (
            prep.groupby(gcols, dropna=False)
            .size()
            .reset_index(name="n_doses")
        )
    return agg.sort_values(
        ["ano_dose_v34", "imuno_grupo_v34", "n_doses"],
        ascending=[False, True, False],
    )


def agregar_doses_regional_ano(prep: pd.DataFrame) -> pd.DataFrame:
    """Doses MenC / MenACWY / Hib / Penta-Hexa por regional × ano (painel operacional)."""
    cols = ["ano_dose_v34", "regional_v34", "imuno_grupo_v34", "n_doses"]
    if prep is None or prep.empty:
        return pd.DataFrame(columns=cols)
    d = prep.copy()
    if "regional_v34" not in d.columns:
        d["regional_v34"] = "Sem regional"
    imunos = {"MenACWY", "MenC", "Hib", "Penta/Hexa (Hib)", "Meningocócica (outra)"}
    if "imuno_grupo_v34" in d.columns:
        d = d[d["imuno_grupo_v34"].isin(imunos)].copy()
    peso = "n_doses" if "n_doses" in d.columns else None
    gcols = ["ano_dose_v34", "regional_v34", "imuno_grupo_v34"]
    if peso:
        agg = d.groupby(gcols, dropna=False)[peso].sum().reset_index(name="n_doses")
    else:
        agg = d.groupby(gcols, dropna=False).size().reset_index(name="n_doses")
    return agg.sort_values(
        ["ano_dose_v34", "regional_v34", "n_doses"],
        ascending=[False, True, False],
    )


def _vac_bin_series(d: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for col in candidates:
        if col in d.columns:
            if col.endswith("_bin_v17"):
                return pd.to_numeric(d[col], errors="coerce")
            return d[col].map(simnao_bin)
    return pd.Series(np.nan, index=d.index)


def status_vacinal_sinan(base: pd.DataFrame) -> pd.DataFrame:
    """Status vacinal SINAN por etiologia × faixa de risco (sem PII)."""
    if base is None or base.empty:
        return pd.DataFrame()
    d = base.copy()
    if "IdadePaciente" in d.columns:
        idade = d["IdadePaciente"].map(parse_idade_anos)
    elif "idade_anos_v17" in d.columns:
        idade = d["idade_anos_v17"].map(parse_idade_anos)
    else:
        idade = pd.Series(np.nan, index=d.index)
    d["faixa_risco_v34"] = idade.map(faixa_risco_idade)
    clas = d.get("classificacao_agrupada_v17", pd.Series("", index=d.index)).astype(str)

    menc = _vac_bin_series(d, ["VacinaConjugadaMeningoC_bin_v17", "VacinaConjugadaMeningoC"])
    hibv = _vac_bin_series(d, ["VacinaContraHemofilos_bin_v17", "VacinaContraHemofilos"])
    ac = _vac_bin_series(d, ["VacinaContraPolissacaridicaAC_bin_v17", "VacinaContraPolissacaridicaAC"])

    rows = []
    recortes = [
        ("DM", clas.eq(DM), "MenC (SINAN)", menc),
        ("DM", clas.eq(DM), "MenAC (polissacarídica A/C SINAN)", ac),
        ("Hib", clas.eq(HIB), "Hib (SINAN)", hibv),
        ("DM <1–4a", clas.eq(DM) & idade.lt(5), "MenC (SINAN)", menc),
        ("DM 11–14a", clas.eq(DM) & idade.ge(11) & idade.lt(15), "MenC (SINAN)", menc),
        ("Hib <5a", clas.eq(HIB) & idade.lt(5), "Hib (SINAN)", hibv),
    ]
    for escopo, mask, vacina, serie in recortes:
        m = mask.fillna(False)
        n = int(m.sum())
        conhecidos = serie.loc[m].notna()
        n_conhec = int(conhecidos.sum())
        n_sim = int((serie.loc[m] == 1).sum())
        n_nao = int((serie.loc[m] == 0).sum())
        rows.append({
            "escopo": escopo,
            "vacina": vacina,
            "fonte": "SINAN",
            "n_casos": n,
            "n_campo_preenchido": n_conhec,
            "pct_completude": _pct(n_conhec, n),
            "n_vacinados_sim": n_sim,
            "n_vacinados_nao": n_nao,
            "pct_vacinados_entre_preenchidos": _pct(n_sim, n_conhec),
            "pct_vacinados_entre_casos": _pct(n_sim, n),
            "nota": "Campo vacinal da ficha SINAN — não é cobertura populacional PNI",
        })

    # detalhe por faixa (DM + Hib)
    for etiq, mask_et, vacina, serie in [
        ("DM", clas.eq(DM), "MenC (SINAN)", menc),
        ("Hib", clas.eq(HIB), "Hib (SINAN)", hibv),
    ]:
        sub = d.loc[mask_et.fillna(False)].copy()
        if sub.empty:
            continue
        s = serie.loc[sub.index]
        for fx, gidx in sub.groupby("faixa_risco_v34", dropna=False).groups.items():
            n = len(gidx)
            conhecidos = s.loc[gidx].notna()
            n_conhec = int(conhecidos.sum())
            n_sim = int((s.loc[gidx] == 1).sum())
            rows.append({
                "escopo": f"{etiq}|faixa={fx}",
                "vacina": vacina,
                "fonte": "SINAN",
                "n_casos": n,
                "n_campo_preenchido": n_conhec,
                "pct_completude": _pct(n_conhec, n),
                "n_vacinados_sim": n_sim,
                "n_vacinados_nao": int((s.loc[gidx] == 0).sum()),
                "pct_vacinados_entre_preenchidos": _pct(n_sim, n_conhec),
                "pct_vacinados_entre_casos": _pct(n_sim, n),
                "nota": "Campo vacinal da ficha SINAN — não é cobertura populacional PNI",
            })
    return pd.DataFrame(rows)


def kpis_cobertura(
    status: pd.DataFrame,
    doses_agg: pd.DataFrame,
    cipv_disponivel: bool,
) -> pd.DataFrame:
    rows = []
    if status is not None and not status.empty:
        for _, r in status[status["escopo"].isin(
            ["DM", "Hib", "DM <1–4a", "DM 11–14a", "Hib <5a"]
        )].iterrows():
            rows.append({
                "escopo": "SINAN|" + str(r["escopo"]),
                "indicador": str(r["vacina"]),
                "n_casos": int(r["n_casos"]),
                "n_doses_cipv": np.nan,
                "pct_completude_sinan": r["pct_completude"],
                "pct_vacinados_sinan": r["pct_vacinados_entre_preenchidos"],
                "fonte_cipv": "ausente",
            })

    if cipv_disponivel and doses_agg is not None and not doses_agg.empty:
        total = int(doses_agg["n_doses"].sum())
        rows.append({
            "escopo": "CIPV|ESTADUAL",
            "indicador": "doses_meningo_hib_total",
            "n_casos": np.nan,
            "n_doses_cipv": total,
            "pct_completude_sinan": np.nan,
            "pct_vacinados_sinan": np.nan,
            "fonte_cipv": "cipv_doses_meningite.csv",
        })
        for imuno, g in doses_agg.groupby("imuno_grupo_v34", dropna=False):
            rows.append({
                "escopo": "CIPV|IMUNO",
                "indicador": str(imuno),
                "n_casos": np.nan,
                "n_doses_cipv": int(g["n_doses"].sum()),
                "pct_completude_sinan": np.nan,
                "pct_vacinados_sinan": np.nan,
                "fonte_cipv": "cipv_doses_meningite.csv",
            })
        if "regional_v34" in doses_agg.columns:
            for (reg, imuno), g in doses_agg.groupby(["regional_v34", "imuno_grupo_v34"], dropna=False):
                rows.append({
                    "escopo": f"CIPV|REGIONAL|{reg}",
                    "indicador": str(imuno),
                    "n_casos": np.nan,
                    "n_doses_cipv": int(g["n_doses"].sum()),
                    "pct_completude_sinan": np.nan,
                    "pct_vacinados_sinan": np.nan,
                    "fonte_cipv": "cipv_doses_meningite.csv",
                })
    else:
        rows.append({
            "escopo": "CIPV|ESTADUAL",
            "indicador": "doses_meningo_hib_total",
            "n_casos": np.nan,
            "n_doses_cipv": 0,
            "pct_completude_sinan": np.nan,
            "pct_vacinados_sinan": np.nan,
            "fonte_cipv": "ausente",
        })
    return pd.DataFrame(rows)


def write_meta(
    n_cipv_raw: int,
    n_cipv_prep: int,
    n_sinan: int,
    kdf: pd.DataFrame,
    *,
    cipv_disponivel: bool,
    sinan_disponivel: bool,
    msg: str,
    sipni_modo: str | None = None,
    n_doses_total: float | None = None,
) -> Path:
    meta = {
        "modulo": "34_cipv_cobertura_vacinal_v34",
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "cipv_disponivel": bool(cipv_disponivel),
        "sinan_disponivel": bool(sinan_disponivel),
        "entrada_cipv": str(CIPV_PATH.name),
        "n_linhas_cipv_raw": int(n_cipv_raw),
        "n_linhas_cipv_prep": int(n_cipv_prep),
        "n_casos_sinan": int(n_sinan),
        "sipni_modo_extracao": sipni_modo or None,
        "n_doses_total": (
            float(n_doses_total) if n_doses_total is not None and pd.notna(n_doses_total) else None
        ),
        "lgpd": {
            "cpf_cns_nome_exportados": False,
            "politica": "scrub de colunas nominais/documento; agregados apenas",
        },
        "imunos_alvo": ["MenACWY", "MenC", "Hib", "Penta/Hexa (Hib)"],
        "nota": (
            "Completude vacinal SINAN ≠ cobertura populacional PNI. "
            "Doses SI-PNI preferem agregado município×ano×código (módulo 19 / SIPNI_MSSQL_*)."
        ),
        "mensagem": msg,
        "kpis_resumo": (
            kdf.head(12).fillna("").astype(str).to_dict(orient="records")
            if kdf is not None and not kdf.empty else []
        ),
    }
    path = OUT / "cipv_fonte_meta_v34.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _sipni_meta_extrato() -> tuple[str | None, float | None]:
    """Lê modo de extração gravado pelo módulo 19 (dw_meta_cipv_doses_meningite.json)."""
    for cand in (
        OUT / "dw_meta_cipv_doses_meningite.json",
        ROOT / "saida_meningites_v17" / "dw_meta_cipv_doses_meningite.json",
    ):
        if not cand.exists():
            continue
        try:
            m = json.loads(cand.read_text(encoding="utf-8"))
            return m.get("sipni_modo_extracao"), m.get("n_doses_total")
        except Exception:
            continue
    return None, None


def write_report(
    status: pd.DataFrame,
    doses_agg: pd.DataFrame,
    kdf: pd.DataFrame,
    *,
    cipv_disponivel: bool,
    msg: str,
) -> Path:
    lines = [
        "# CIPV / SI-PNI × SINAN — cobertura vacinal V34",
        "",
        f"**Gerado em:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Status:** {msg}",
        "",
        "## Escopo",
        "",
        "- Imunobiológicos: MenACWY, MenC, Hib / Penta-Hexa (componente Hib).",
        "- SINAN: status vacinal entre casos notificados (campo da ficha).",
        "- CIPV/SI-PNI: doses agregadas quando `cipv_doses_meningite.csv` existir.",
        "- LGPD: sem CPF/CNS/nome nos artefatos.",
        "",
        f"**Extrato CIPV disponível:** {'sim' if cipv_disponivel else 'não'}",
        "",
    ]
    if status is not None and not status.empty:
        lines += ["## Status vacinal SINAN (recortes principais)", ""]
        main = status[status["escopo"].isin(
            ["DM", "Hib", "DM <1–4a", "DM 11–14a", "Hib <5a"]
        )]
        for _, r in main.iterrows():
            lines.append(
                f"- **{r['escopo']}** / {r['vacina']}: "
                f"{int(r['n_vacinados_sim'])}/{int(r['n_campo_preenchido'])} "
                f"vacinados entre preenchidos "
                f"({_pct(r['n_vacinados_sim'], r['n_campo_preenchido']):.1f}%) · "
                f"n={int(r['n_casos'])} · completude={_pct(r['n_campo_preenchido'], r['n_casos']):.1f}%"
            )
        lines.append("")
    if cipv_disponivel and doses_agg is not None and not doses_agg.empty:
        lines += ["## Doses CIPV agregadas (top imunobiológicos)", ""]
        by_imuno = doses_agg.groupby("imuno_grupo_v34", dropna=False)["n_doses"].sum().sort_values(ascending=False)
        for imuno, n in by_imuno.items():
            lines.append(f"- **{imuno}**: {int(n)} doses")
        lines.append("")
        if "regional_v34" in doses_agg.columns:
            lines += ["## Doses por regional (top 12)", ""]
            by_reg = (
                doses_agg.groupby("regional_v34", dropna=False)["n_doses"]
                .sum()
                .sort_values(ascending=False)
                .head(12)
            )
            for reg, n in by_reg.items():
                lines.append(f"- **{reg}**: {int(n)} doses")
            lines.append("")
    else:
        lines += [
            "## CIPV ausente",
            "",
            "Para ativar doses populacionais:",
            "",
            "1. Defina `CIPV_DW_TABLE` (e opcionalmente `CIPV_DW_SCHEMA`) no `.env`",
            "2. Rode `py -3.13 19_dw_descobrir_e_extrair_v23.py`",
            "3. Rode novamente este módulo",
            "",
            "Alternativa: depositar CSV agregado (sem PII) em "
            "`entradas_linkage/cipv_doses_meningite.csv`.",
            "",
        ]
    lines += [
        "## Interpretação",
        "",
        "- Use SINAN para qualidade do registro vacinal nos casos.",
        "- Use CIPV para volume de doses aplicadas (quando a fonte existir).",
        "- Não misturar os dois como se fossem a mesma taxa de cobertura.",
        "",
    ]
    path = REL / "CIPV_COBERTURA_VACINAL_V34.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(exist_ok=True)
    REL.mkdir(exist_ok=True)

    raw = _read_cipv()
    cipv_disponivel = not raw.empty
    prep = preparar_cipv(raw) if cipv_disponivel else pd.DataFrame()

    try:
        base = load_base_v17()
        sinan_ok = base is not None and not base.empty
    except Exception as e:
        print(f"[AVISO] Base SINAN indisponível ({e})")
        base = pd.DataFrame()
        sinan_ok = False

    mapa_reg = mapa_municipio_regional(base) if sinan_ok else pd.DataFrame()
    if not prep.empty:
        prep = anexar_regional(prep, mapa_reg)

    doses_agg = agregar_doses_cipv(prep) if not prep.empty else pd.DataFrame(
        columns=[
            "ano_dose_v34", "codigo_municipio_v34", "municipio_v34", "regional_v34",
            "imuno_grupo_v34", "faixa_risco_v34", "n_doses",
        ]
    )
    doses_reg = agregar_doses_regional_ano(prep) if not prep.empty else pd.DataFrame(
        columns=["ano_dose_v34", "regional_v34", "imuno_grupo_v34", "n_doses"]
    )

    status = status_vacinal_sinan(base) if sinan_ok else pd.DataFrame()
    kdf = kpis_cobertura(status, doses_agg, cipv_disponivel=cipv_disponivel and not prep.empty)

    # cabeçalhos vazios seguros
    if status.empty:
        status = pd.DataFrame(columns=[
            "escopo", "vacina", "fonte", "n_casos", "n_campo_preenchido",
            "pct_completude", "n_vacinados_sim", "n_vacinados_nao",
            "pct_vacinados_entre_preenchidos", "pct_vacinados_entre_casos", "nota",
        ])
    if kdf.empty:
        kdf = pd.DataFrame(columns=[
            "escopo", "indicador", "n_casos", "n_doses_cipv",
            "pct_completude_sinan", "pct_vacinados_sinan", "fonte_cipv",
        ])

    doses_agg.to_csv(OUT / "cipv_doses_agregadas_v34.csv", index=False, encoding="utf-8-sig")
    doses_reg.to_csv(OUT / "cipv_doses_regional_ano_v34.csv", index=False, encoding="utf-8-sig")
    status.to_csv(OUT / "cipv_sinan_status_vacinal_v34.csv", index=False, encoding="utf-8-sig")
    kdf.to_csv(OUT / "cipv_kpis_cobertura_v34.csv", index=False, encoding="utf-8-sig")

    if cipv_disponivel and not prep.empty:
        modo, n_tot = _sipni_meta_extrato()
        n_doses_prep = float(pd.to_numeric(prep.get("n_doses"), errors="coerce").fillna(1).sum()) if "n_doses" in prep.columns else float(len(prep))
        modo_txt = f" · modo=`{modo}`" if modo else ""
        msg = (
            f"SI-PNI/CIPV com {len(raw)} linhas brutas → {len(prep)} agregados filtrados "
            f"({int(n_doses_prep)} doses){modo_txt}; "
            f"SINAN={'ok' if sinan_ok else 'ausente'} ({len(base)} casos)."
        )
    elif cipv_disponivel:
        modo, n_tot = _sipni_meta_extrato()
        msg = (
            f"Extrato CIPV presente ({len(raw)} linhas) mas sem imunobiológicos "
            f"MenACWY/MenC/Hib reconhecíveis após filtro."
        )
    else:
        modo, n_tot = None, None
        msg = (
            f"{CIPV_PATH.name} ausente — KPIs SINAN gerados"
            f"{' (' + str(len(base)) + ' casos)' if sinan_ok else ''}. "
            "Para doses PNI: módulo 19 + SIPNI_MSSQL_* / CIPV_DW_TABLE."
        )

    if modo is None:
        modo, n_tot = _sipni_meta_extrato()
    n_doses_meta = None
    if not doses_agg.empty and "n_doses" in doses_agg.columns:
        n_doses_meta = float(pd.to_numeric(doses_agg["n_doses"], errors="coerce").fillna(0).sum())
    elif n_tot is not None:
        n_doses_meta = float(n_tot)

    write_meta(
        len(raw), len(prep), len(base) if sinan_ok else 0, kdf,
        cipv_disponivel=bool(cipv_disponivel and not prep.empty),
        sinan_disponivel=sinan_ok,
        msg=msg,
        sipni_modo=modo,
        n_doses_total=n_doses_meta,
    )
    write_report(
        status, doses_agg, kdf,
        cipv_disponivel=bool(cipv_disponivel and not prep.empty),
        msg=msg,
    )

    print(f"[OK] CIPV/SINAN V34: {msg}")
    if not kdf.empty:
        show = kdf.head(8)
        print(show.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
