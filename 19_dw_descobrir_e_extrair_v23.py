# -*- coding: utf-8 -*-
"""
19_dw_descobrir_e_extrair_v23.py
Descobre e extrai views do Data Warehouse SES/MT relevantes para Meningites.

Reutiliza o padrão de conexão do ROBÔ SIVEP / Clima-Saúde:
  USE_SQLSERVER=true
  DW_HOST / DW_SERVER, DW_DATABASE, DW_USER, DW_PASSWORD, DW_DRIVER

Por padrão tenta carregar .env de:
  1) Meningites/.env
  2) DW_ENV_FILE
  3) ../Monitoramento ondas de calor/.env
  4) ../SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO/.env
  5) ../ROBÔ SIVEP/.env

Nunca imprime senha.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from meningites_v17_common import OUT, ROOT, REL

ENTRADAS = ROOT / "entradas_linkage"
ENTRADAS.mkdir(exist_ok=True)

# Objetos conhecidos nos outros projetos CIEVS
KNOWN = {
    "gal": "dbo.VW_GAL",
    "sim": "dbo.SIM",
    "cnes_estab": "dbo.CNES_ESTABELECIMENTOS",
    "cnes_leitos": "dbo.CNES_LEITOS",
    "sih_internacao": "dbo.VW_INTERNACAO",
    # CIPV / SI-PNI: nome real varia no DW — override via CIPV_DW_SCHEMA / CIPV_DW_TABLE
    "cipv": "dbo.VW_CIPV",
    "sipni": "dbo.VW_SIPNI",
    "sinan_srag": "dbo.VW_SINAN_SINDROMERESPIRATORIAAGUDAGRAVE",
    "sinan_dengue": "dbo.VW_SINAN_DENGUE",
    "sinan_chik": "dbo.VW_SINAN_CHIKUNGUNYA",
    "sinan_meningite": "dbo.VW_SINAN_MENINGITE",
}

# Preferência de nomes para descoberta CIPV/SI-PNI (sem inventar linhas).
CANONICAL_CIPV = (
    "VW_Vacinas_PNI",
    "VW_VACINAS_PNI",
    "VW_CIPV",
    "CIPV",
    "VW_SIPNI",
    "SIPNI",
    "VW_SI_PNI",
    "SI_PNI",
    "VW_PNI",
    "PNI_DOSES",
    "VW_IMUNIZACAO",
    "IMUNIZACAO",
    "IMUNIZACAOCOBERTURA",
)

# Códigos DATASUS/SI-PNI de imunobiológicos ligados a meningite (sem zeros à esquerda).
# Não inclui 108 (VSR gestante — projeto VSR).
SIPNI_MENINGITE_CODES = frozenset({
    "9",    # Hib
    "17",   # pentavalente (Hib)
    "29",   # meningocócica C conjugada
    "42",   # meningocócica B
    "46",   # hexavalente (Hib)
    "73",   # meningocócica C (outras apresentações)
    "93",   # hexavalente
    "102",  # meningocócica C
    "103",  # MenACWY
    "114",  # MenACWY conjugada
})

# Colunas operacionais da VW_Vacinas_PNI (padrão VIGIA-VSR; sem CPF/CNS/nome).
SIPNI_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "CO_VACINA": (
        "CO_VACINA", "CO_IMUNOBIOLOGICO", "SG_VACINA", "VACINA_CODIGO",
        "CD_VACINA", "COD_VACINA",
    ),
    "DT_VACINA": (
        "DT_VACINA", "DT_APLICACAO", "DT_IMUNIZACAO", "DATA_VACINA", "DATA_APLICACAO",
    ),
    "CO_MUNICIPIO_RESIDENCIA": (
        "CO_MUNICIPIO_RESIDENCIA", "CO_MUNICIPIO_PACIENTE", "CO_MUN_RES",
        "CODMUNRES", "CD_MUNICIPIO_RESIDENCIA",
    ),
    "CO_DOSE": ("CO_DOSE", "CO_DOSE_VACINA", "DS_DOSE", "SG_DOSE", "DOSE"),
    "CO_CNES": ("CO_CNES", "CO_CNES_ESTABELECIMENTO", "CO_ESTABELECIMENTO", "CNES"),
}

# Imunobiológicos relevantes à vigilância de meningites (filtro textual no extrato).
CIPV_VACINA_LIKE = (
    "%MENING%",
    "%MENACWY%",
    "%MENAC%",
    "%MEN C%",
    "%MENC%",
    "%ACWY%",
    "%HAEMOPH%",
    "%HEMOFIL%",
    "%HIB%",
    "%PENTA%",
    "%HEXA%",
)

# Nomes canônicos da view SINAN meningite (ordem = preferência).
# Aceita com ou sem schema dbo.; comparação sem acento/case.
CANONICAL_SINAN_MENINGITE = (
    "VW_SINAN_MENINGITE",
    "DW_VW_SINAN_MENINGITE",
    "SINAN_MENINGITE",
    "VW_SINAN_MENINGITES",
)


def _norm_view_name(name: str) -> str:
    raw = str(name or "").strip()
    if "." in raw:
        raw = raw.split(".")[-1]
    return re.sub(r"[^A-Z0-9_]", "", raw.upper())


def pick_sinan_meningite_view(candidatas: list[str]) -> dict:
    """
    Escolhe a view SINAN meningite com preferência canônica.

    Retorna dict com: view, metodo (canonico|heuristica|nenhuma),
    warning, candidatas, canonicas_encontradas.
    """
    candidatas = [str(c).strip() for c in candidatas if str(c).strip()]
    by_norm = {_norm_view_name(c): c for c in candidatas}
    canon_hits = []
    for pref in CANONICAL_SINAN_MENINGITE:
        hit = by_norm.get(_norm_view_name(pref))
        if hit and hit not in canon_hits:
            canon_hits.append(hit)
    if canon_hits:
        return {
            "view": canon_hits[0],
            "metodo": "canonico",
            "warning": None,
            "candidatas": candidatas,
            "canonicas_encontradas": canon_hits,
        }
    if candidatas:
        warning = (
            f"Nenhuma view canônica SINAN meningite "
            f"({', '.join(CANONICAL_SINAN_MENINGITE)}). "
            f"Fallback heurístico (*MENING*): usando '{candidatas[0]}' "
            f"entre {len(candidatas)} candidata(s)."
        )
        return {
            "view": candidatas[0],
            "metodo": "heuristica",
            "warning": warning,
            "candidatas": candidatas,
            "canonicas_encontradas": [],
        }
    return {
        "view": None,
        "metodo": "nenhuma",
        "warning": "Nenhuma view *MENING* encontrada no INFORMATION_SCHEMA.",
        "candidatas": [],
        "canonicas_encontradas": [],
    }

# CIDs típicos de meningite / doença meningocócica no SIM e SIH
SIM_CID_LIKE = (
    "A39%",  # doença meningocócica
    "G00%",  # meningite bacteriana
    "G01%",  # meningite em doenças bacterianas classificadas em outra parte
    "G02%",  # meningite em outras doenças infecciosas
    "G03%",  # meningite por outras causas e não especificadas
    "A87%",  # meningite viral
)
SIH_CID_LIKE = SIM_CID_LIKE


def log(msg: str) -> None:
    print(msg, flush=True)


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def resolve_env() -> dict[str, str]:
    merged: dict[str, str] = {}
    env_file = (os.getenv("DW_ENV_FILE") or "").strip()
    parent = ROOT.parent
    candidates = [
        ROOT / ".env",
        Path(env_file) if env_file else None,
        parent / "Monitoramento ondas de calor" / ".env",
        parent / "SIS-Monitoramento-Clima-Saude-GITHUB-LIMPO" / ".env",
        parent / "ROBÔ SIVEP" / ".env",
    ]
    for p in candidates:
        if p is None:
            continue
        try:
            if p.exists() and p.is_file():
                merged.update(load_dotenv(p))
                log(f"[ENV] Carregado: {p}")
        except OSError:
            continue
    for k, v in os.environ.items():
        if (
            k.startswith("DW_")
            or k.startswith("SIH_DW_")
            or k.startswith("CIPV_DW_")
            or k.startswith("SIPNI_MSSQL_")
            or k in {"USE_SQLSERVER", "USE_DW"}
        ):
            merged[k] = v
    return merged


def env_get(cfg: dict[str, str], *keys: str, default: str | None = None) -> str | None:
    for k in keys:
        v = cfg.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default


def pick_driver(preferred: str | None) -> str:
    try:
        import pyodbc
        available = [str(d) for d in pyodbc.drivers()]
    except Exception:
        available = []
    if preferred and preferred in available:
        return preferred
    for cand in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"]:
        if cand in available:
            return cand
    return preferred or "ODBC Driver 17 for SQL Server"


def build_conn_str(cfg: dict[str, str]) -> str:
    server = env_get(cfg, "DW_SERVER", "DW_HOST")
    database = env_get(cfg, "DW_DATABASE")
    user = env_get(cfg, "DW_USER")
    password = env_get(cfg, "DW_PASSWORD")
    port = env_get(cfg, "DW_PORT", default="1433")
    driver = pick_driver(env_get(cfg, "DW_DRIVER", default="ODBC Driver 18 for SQL Server"))
    encrypt = env_get(cfg, "DW_ENCRYPT", default="no") or "no"
    trust = env_get(cfg, "DW_TRUST_SERVER_CERTIFICATE", default="yes") or "yes"
    if not server or not database:
        raise RuntimeError("DW_SERVER/DW_HOST e DW_DATABASE são obrigatórios.")
    if not user or not password:
        raise RuntimeError("DW_USER e DW_PASSWORD são obrigatórios.")
    target = f"{server},{port}" if port else server
    return (
        f"DRIVER={{{driver}}};SERVER={target};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt={encrypt};TrustServerCertificate={trust};"
    )


def sipni_host_configured(cfg: dict[str, str] | None = None) -> bool:
    cfg = cfg or {}
    return bool(env_get(cfg, "SIPNI_MSSQL_HOST"))


def build_sipni_conn_str(cfg: dict[str, str]) -> str:
    """Conexão ao SQL Server Vacinas — distinto do DW Datawarehouse.

    Senha: SIPNI_MSSQL_PASSWORD; se vazia, reutiliza DW_PASSWORD (mesmo usuário SES).
    """
    server = env_get(cfg, "SIPNI_MSSQL_HOST")
    database = env_get(cfg, "SIPNI_MSSQL_DATABASE", default="Vacinas") or "Vacinas"
    user = env_get(cfg, "SIPNI_MSSQL_USER", "DW_USER")
    password = env_get(cfg, "SIPNI_MSSQL_PASSWORD", "DW_PASSWORD")
    port = env_get(cfg, "SIPNI_MSSQL_PORT", default="1433") or "1433"
    driver = pick_driver(
        env_get(cfg, "SIPNI_MSSQL_DRIVER", "DW_DRIVER", default="ODBC Driver 18 for SQL Server")
    )
    encrypt = env_get(cfg, "SIPNI_MSSQL_ENCRYPT", "DW_ENCRYPT", default="no") or "no"
    trust = (
        env_get(
            cfg,
            "SIPNI_MSSQL_TRUST_SERVER_CERTIFICATE",
            "DW_TRUST_SERVER_CERTIFICATE",
            default="yes",
        )
        or "yes"
    )
    if not server or not database:
        raise RuntimeError("SIPNI_MSSQL_HOST e SIPNI_MSSQL_DATABASE são obrigatórios.")
    if not user or not password:
        raise RuntimeError("SIPNI_MSSQL_USER e senha (ou DW_PASSWORD) são obrigatórios.")
    target = f"{server},{port}"
    return (
        f"DRIVER={{{driver}}};SERVER={target};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt={encrypt};TrustServerCertificate={trust};"
    )


def discover_objects(conn) -> pd.DataFrame:
    sql = """
    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%MENING%'
       OR TABLE_NAME LIKE '%GAL%'
       OR TABLE_NAME LIKE '%LACEN%'
       OR TABLE_NAME = 'SIM'
       OR TABLE_NAME LIKE 'SIM_%'
       OR TABLE_NAME LIKE '%SINASC%'
       OR TABLE_NAME LIKE '%CNES%'
       OR TABLE_NAME LIKE 'VW_SINAN%'
       OR TABLE_NAME LIKE '%INTERNAC%'
       OR TABLE_NAME LIKE '%SIH%'
       OR TABLE_NAME LIKE '%AIH%'
       OR TABLE_NAME LIKE '%CIPV%'
       OR TABLE_NAME LIKE '%SIPNI%'
       OR TABLE_NAME LIKE '%SI_PNI%'
       OR TABLE_NAME LIKE '%PNI%'
       OR TABLE_NAME LIKE '%IMUNIZ%'
       OR TABLE_NAME LIKE '%VACIN%'
    ORDER BY TABLE_TYPE, TABLE_NAME
    """
    return pd.read_sql(sql, conn)


def resolve_sih_view(cfg: dict[str, str] | None = None) -> tuple[str, str]:
    """Retorna (schema, table) para SIH; env SIH_DW_* sobrepõe o padrão VW_INTERNACAO."""
    cfg = cfg or {}
    schema = env_get(cfg, "SIH_DW_SCHEMA", default="dbo") or "dbo"
    table = env_get(cfg, "SIH_DW_TABLE", default="VW_INTERNACAO") or "VW_INTERNACAO"
    return schema, table


def resolve_cipv_view(
    cfg: dict[str, str] | None = None,
    candidatas: list[str] | None = None,
) -> tuple[str, str, str]:
    """
    Retorna (schema, table, metodo) para CIPV/SI-PNI.
    Env CIPV_DW_SCHEMA / CIPV_DW_TABLE sobrepõe; senão tenta canônicos nas candidatas.
    """
    cfg = cfg or {}
    schema = env_get(cfg, "CIPV_DW_SCHEMA", "SIPNI_MSSQL_SCHEMA", default="dbo") or "dbo"
    forced = env_get(cfg, "CIPV_DW_TABLE", "SIPNI_MSSQL_VIEW", default="") or ""
    if forced.strip():
        return schema, forced.strip().split(".")[-1], "env"
    by_norm = {_norm_view_name(c): c for c in (candidatas or []) if str(c).strip()}
    for pref in CANONICAL_CIPV:
        hit = by_norm.get(_norm_view_name(pref))
        if hit:
            raw = str(hit)
            if "." in raw:
                parts = raw.split(".", 1)
                return parts[0], parts[1], "canonico"
            return schema, raw, "canonico"
    # heurística: nome com CIPV / SIPNI / PNI+VACIN
    for c in candidatas or []:
        n = _norm_view_name(c)
        if "CIPV" in n or "SIPNI" in n or re.search(r"SI.?PNI", n):
            return schema, str(c).split(".")[-1], "heuristica"
    return schema, "", "nenhuma"


def _scrub_pii_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove colunas nominais/documento do extrato CIPV antes de gravar (LGPD)."""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    drop = []
    for c in df.columns:
        cl = str(c).lower()
        if re.search(r"vacina|imuno|produto|imunobiolog", cl):
            continue  # preserva NomeVacina / imunobiológico
        if re.search(
            r"nomepaciente|nome_paciente|nomemae|nome_mae|nomepai|nome_pai|"
            r"nomeobito|nome_obito|^nome$|cpf|cns|cartaosus|cartao_sus|"
            r"endereco|logradouro|bairro|cep|telefone|email|doc_|rg\b",
            cl,
            re.I,
        ):
            drop.append(c)
    return df.drop(columns=drop, errors="ignore")


def _norm_vacina_code(value) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    return digits.lstrip("0") or "0"


def _sipni_map_columns(cols: list[str]) -> dict[str, str]:
    upper = {c.upper(): c for c in cols}
    mapping: dict[str, str] = {}
    for dest, cands in SIPNI_COLUMN_CANDIDATES.items():
        for cand in cands:
            if cand.upper() in upper:
                mapping[dest] = upper[cand.upper()]
                break
    return mapping


def extract_cipv_meningite(
    conn,
    years_back: int = 5,
    cfg: dict[str, str] | None = None,
    candidatas: list[str] | None = None,
) -> pd.DataFrame:
    """
    Doses SI-PNI de imunobiológicos ligados a meningites (MenACWY/MenC/Hib/penta).
    Preferência: VW_Vacinas_PNI no servidor Vacinas, filtro por CO_VACINA.
    Nunca persiste CPF/CNS/nome (scrub + SELECT só colunas operacionais).
    """
    schema, table, metodo = resolve_cipv_view(cfg, candidatas)
    if not table:
        log("[INFO] CIPV/SI-PNI: nenhuma tabela resolvida (defina SIPNI_MSSQL_VIEW).")
        return pd.DataFrame()
    fqn = f"[{schema}].[{table}]"
    log(f"[SQL] Extraindo SI-PNI: {fqn} (método={metodo})")

    cols: list[str] = []
    try:
        cols = pd.read_sql(
            f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA=N'{schema}' AND TABLE_NAME=N'{table}'
            """,
            conn,
        )["COLUMN_NAME"].astype(str).tolist()
    except Exception as e:
        log(f"[AVISO] SI-PNI INFORMATION_SCHEMA: {e}")
    if not cols:
        try:
            cols = list(pd.read_sql(f"SELECT TOP (0) * FROM {fqn}", conn).columns.astype(str))
        except Exception as e:
            log(f"[AVISO] SI-PNI TOP 0: {e}")
            return pd.DataFrame()

    mapping = _sipni_map_columns(cols)
    vac_col = mapping.get("CO_VACINA") or next(
        (c for c in cols if re.search(r"vacina|imuno|produto|imunobiolog", c, re.I)),
        None,
    )
    date_col = mapping.get("DT_VACINA") or next(
        (c for c in cols if re.search(r"data_aplic|dt_aplic|dt_vacin|data_vacin", c, re.I)),
        None,
    )
    year_pred = ""
    if date_col:
        year_pred = f"AND TRY_CONVERT(date, [{date_col}]) >= DATEADD(year, -{int(years_back)}, GETDATE())"

    mun_col = mapping.get("CO_MUNICIPIO_RESIDENCIA")
    codes = sorted(SIPNI_MENINGITE_CODES)
    literals = ", ".join(f"'{c}'" for c in codes)
    literals_pad = ", ".join(f"'{c.zfill(4)}'" for c in codes)
    code_pred = (
        f"LTRIM(RTRIM(CAST([{vac_col}] AS varchar(20)))) IN ({literals}, {literals_pad})"
        if vac_col else "1=0"
    )

    # Preferência: agregado município×ano×código (sem TOP) — cobre milhões de doses.
    # Recorte MT: município de residência começa com 51 (IBGE).
    mt_pred = ""
    if mun_col:
        mt_pred = (
            f"AND LEFT(LTRIM(RTRIM(CAST([{mun_col}] AS varchar(20)))), 2) = '51'"
        )

    df = pd.DataFrame()
    modo = "vazio"
    if vac_col and date_col and mun_col:
        sql = f"""
        SELECT
            [{vac_col}] AS co_vacina,
            [{mun_col}] AS co_municipio_paciente,
            YEAR(TRY_CONVERT(date, [{date_col}])) AS ano_aplic,
            COUNT_BIG(*) AS n_doses
        FROM {fqn}
        WHERE ({code_pred}) {year_pred} {mt_pred}
        GROUP BY [{vac_col}], [{mun_col}], YEAR(TRY_CONVERT(date, [{date_col}]))
        """
        try:
            df = pd.read_sql(sql, conn)
            modo = "agregado_mun_ano"
            n_doses = int(pd.to_numeric(df["n_doses"], errors="coerce").fillna(0).sum()) if not df.empty else 0
            log(
                f"[SI-PNI] agregado município×ano×código: "
                f"{0 if df is None else len(df)} linhas · {n_doses} doses (MT)"
            )
        except Exception as e1:
            log(f"[AVISO] SI-PNI agregado falhou ({e1}); tentando amostra TOP (degradado)")
            df = pd.DataFrame()
    if (df is None or df.empty) and vac_col:
        select_cols = []
        seen = set()
        for src in mapping.values():
            if src not in seen:
                select_cols.append(f"[{src}]")
                seen.add(src)
        select_sql = ", ".join(select_cols) if select_cols else "*"
        sql = (
            f"SELECT TOP (400000) {select_sql} FROM {fqn} "
            f"WHERE ({code_pred}) {year_pred} {mt_pred}"
        )
        try:
            df = pd.read_sql(sql, conn)
            modo = "amostra_top400k"
            log("[AVISO] SI-PNI em modo amostra TOP 400000 — KPIs de doses são parciais.")
        except Exception as e1:
            log(f"[AVISO] SI-PNI filtro por código falhou ({e1}); tentando LIKE nome")
            likes = " OR ".join([f"CAST([{vac_col}] AS varchar(80)) LIKE '{p}'" for p in CIPV_VACINA_LIKE])
            try:
                df = pd.read_sql(
                    f"SELECT TOP (200000) {select_sql} FROM {fqn} WHERE ({likes}) {year_pred} {mt_pred}",
                    conn,
                )
                modo = "amostra_like"
            except Exception as e2:
                log(f"[AVISO] SI-PNI indisponível: {e2}")
                return pd.DataFrame()
    elif not vac_col:
        log("[AVISO] SI-PNI sem coluna de vacina mapeada.")
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    code_col = "co_vacina" if "co_vacina" in df.columns else vac_col
    if code_col and code_col in df.columns:
        codes_ok = df[code_col].map(_norm_vacina_code).isin(SIPNI_MENINGITE_CODES)
        if codes_ok.any():
            df = df.loc[codes_ok].copy()
        elif code_col != "co_vacina":
            vac_re = re.compile(
                r"mening|menacwy|menac|menc\b|acwy|haemoph|hemofil|hib\b|penta|hexa",
                re.I,
            )
            text_cols = [
                c for c in df.columns
                if df[c].dtype == object or str(df[c].dtype).startswith("string")
            ]
            mask = pd.Series(False, index=df.index)
            for c in text_cols[:12]:
                mask = mask | df[c].astype(str).str.contains(vac_re, na=False)
            if mask.any():
                df = df.loc[mask].copy()

    out = _scrub_pii_columns(df)
    if not out.empty:
        out.attrs["sipni_modo_extracao"] = modo
    return out


def _sih_cid_predicate(diag_col: str, codigo_col: str | None = None) -> str:
    parts = []
    for pat in SIH_CID_LIKE:
        parts.append(f"{diag_col} LIKE '{pat}'")
        if codigo_col:
            parts.append(f"{codigo_col} LIKE '{pat}'")
    return " OR ".join(parts)


def extract_sih_meningite(conn, years_back: int = 5, cfg: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Internações SIH com CID de meningite (DiagnosticoPrincipal / CodigoDiagnosticoPrincipal).
    View padrão: dbo.VW_INTERNACAO (override via SIH_DW_SCHEMA / SIH_DW_TABLE).
    """
    schema, table = resolve_sih_view(cfg)
    fqn = f"[{schema}].[{table}]"
    cid_where = _sih_cid_predicate("DiagnosticoPrincipal", "CodigoDiagnosticoPrincipal")
    sql = f"""
    SELECT *
    FROM {fqn}
    WHERE TRY_CONVERT(int, AnoInternacao) >= YEAR(GETDATE()) - {int(years_back)}
      AND ({cid_where})
    """
    try:
        log(f"[SQL] Extraindo SIH meningite: {fqn} (últimos {years_back} anos)")
        return pd.read_sql(sql, conn)
    except Exception as e1:
        log(f"[AVISO] SIH filtro completo falhou ({e1}); tentando só DiagnosticoPrincipal")
        cid_simple = _sih_cid_predicate("DiagnosticoPrincipal")
        sql2 = f"""
        SELECT TOP (200000) *
        FROM {fqn}
        WHERE ({cid_simple})
        """
        try:
            return pd.read_sql(sql2, conn)
        except Exception as e2:
            log(f"[AVISO] SIH indisponível: {e2}")
            return pd.DataFrame()


def extract_gal(conn, years_back: int = 5) -> pd.DataFrame:
    sql = f"""
    SELECT *
    FROM dbo.VW_GAL
    WHERE (
        Agravo_Requisicao LIKE '%Mening%'
        OR Agravo_Gal LIKE '%Mening%'
        OR CID_Agravo_Gal LIKE 'A39%'
        OR CID_Agravo_Gal LIKE 'G00%'
        OR CID_Agravo_Gal LIKE 'G01%'
        OR CID_Agravo_Gal LIKE 'G02%'
        OR CID_Agravo_Gal LIKE 'G03%'
        OR CID_Agravo_Gal LIKE 'A87%'
        OR Exame LIKE '%Mening%'
        OR Exame LIKE '%líquor%'
        OR Exame LIKE '%liquor%'
        OR Exame LIKE '%LCR%'
        OR Material_Biologico LIKE '%líquor%'
        OR Material_Biologico LIKE '%liquor%'
        OR Material_Biologico LIKE '%LCR%'
    )
    AND COALESCE(Data_Liberacao_dt, Data_Processamento_dt, Data_Coleta_dt, Data_Solicitacao_dt)
        >= DATEADD(year, -{int(years_back)}, GETDATE())
    """
    try:
        return pd.read_sql(sql, conn)
    except Exception as e:
        log(f"[AVISO] Filtro GAL meningite falhou ({e}); tentando amostra ampla.")
        return pd.read_sql("SELECT TOP (50000) * FROM dbo.VW_GAL ORDER BY DT_Atualizacao DESC", conn)


def extract_sim(conn, years_back: int = 5) -> pd.DataFrame:
    likes = " OR ".join([f"CausaBasica LIKE '{c}'" for c in SIM_CID_LIKE])
    # também busca nas linhas da DO se existirem
    extra = " OR ".join([
        f"LinhaA LIKE '{c}' OR LinhaB LIKE '{c}' OR LinhaC LIKE '{c}' OR LinhaD LIKE '{c}'"
        for c in SIM_CID_LIKE
    ])
    sql = f"""
    SELECT *
    FROM dbo.SIM
    WHERE TRY_CONVERT(int, AnoObito) >= YEAR(GETDATE()) - {int(years_back)}
      AND (({likes}) OR ({extra}))
    """
    return pd.read_sql(sql, conn)


def extract_cnes(conn) -> pd.DataFrame:
    sql = """
    WITH ultima_competencia AS (
        SELECT MAX(CONCAT(Ano, RIGHT('00' + Mes, 2))) AS comp
        FROM dbo.CNES_ESTABELECIMENTOS
    )
    SELECT *
    FROM dbo.CNES_ESTABELECIMENTOS
    WHERE CONCAT(Ano, RIGHT('00' + Mes, 2)) = (SELECT comp FROM ultima_competencia)
    """
    return pd.read_sql(sql, conn)


def extract_cnes_leitos(conn) -> pd.DataFrame:
    """Leitos CNES (UTI e demais) — última competência disponível."""
    sql = """
    WITH ultima_competencia AS (
        SELECT MAX(CONCAT(Ano, RIGHT('00' + CAST(Mes AS varchar(2)), 2))) AS comp
        FROM dbo.CNES_LEITOS
    )
    SELECT *
    FROM dbo.CNES_LEITOS
    WHERE CONCAT(Ano, RIGHT('00' + CAST(Mes AS varchar(2)), 2)) = (SELECT comp FROM ultima_competencia)
    """
    try:
        return pd.read_sql(sql, conn)
    except Exception as e1:
        log(f"[AVISO] CNES_LEITOS (filtro competência): {e1} — tentando TOP sem filtro")
        try:
            return pd.read_sql("SELECT TOP (200000) * FROM dbo.CNES_LEITOS", conn)
        except Exception as e2:
            log(f"[AVISO] CNES_LEITOS indisponível: {e2}")
            return pd.DataFrame()


def extract_sinan_meningite(conn, view_name: str | None) -> pd.DataFrame:
    if not view_name:
        return pd.DataFrame()
    fqn = view_name if "." in view_name else f"dbo.{view_name}"
    log(f"[SQL] Extraindo SINAN meningite: {fqn}")
    return pd.read_sql(f"SELECT * FROM {fqn}", conn)


def extract_sinasc(conn, view_name: str | None, years_back: int = 3) -> pd.DataFrame:
    if not view_name:
        return pd.DataFrame()
    fqn = view_name if "." in view_name else f"dbo.{view_name}"
    # tenta filtro por ano se coluna existir
    try:
        cols = pd.read_sql(
            f"""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='{fqn.split('.')[-1]}'
            """,
            conn,
        )["COLUMN_NAME"].tolist()
    except Exception:
        cols = []
    year_col = next((c for c in cols if re.search(r"ano", c, re.I)), None)
    if year_col:
        sql = f"SELECT * FROM {fqn} WHERE TRY_CONVERT(int, [{year_col}]) >= YEAR(GETDATE()) - {int(years_back)}"
    else:
        sql = f"SELECT TOP (100000) * FROM {fqn}"
    return pd.read_sql(sql, conn)


def save_extract(df: pd.DataFrame, stem: str) -> Path | None:
    if df is None or df.empty:
        log(f"[INFO] Sem dados para {stem}")
        return None
    path = ENTRADAS / f"{stem}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    # espelho em saida
    df.head(0).to_csv(OUT / f"dw_schema_{stem}.csv", index=False, encoding="utf-8-sig")
    meta = {
        "arquivo": path.name,
        "n_linhas": int(len(df)),
        "n_colunas": int(df.shape[1]),
        "colunas": list(map(str, df.columns[:80])),
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
    }
    attrs = getattr(df, "attrs", None) or {}
    modo = attrs.get("sipni_modo_extracao")
    if modo:
        meta["sipni_modo_extracao"] = modo
        if "n_doses" in df.columns:
            meta["n_doses_total"] = int(
                pd.to_numeric(df["n_doses"], errors="coerce").fillna(0).sum()
            )
    (OUT / f"dw_meta_{stem}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[OK] {stem}: {len(df)} linhas → {path}")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover-only", action="store_true")
    ap.add_argument("--years", type=int, default=5)
    args = ap.parse_args()

    cfg = resolve_env()
    use = (env_get(cfg, "USE_SQLSERVER", "USE_DW", default="true") or "true").lower() in {"1", "true", "yes", "sim"}
    if not use:
        raise SystemExit("USE_SQLSERVER/USE_DW desabilitado no .env")

    import pyodbc

    conn_str = build_conn_str(cfg)
    host = env_get(cfg, "DW_SERVER", "DW_HOST")
    db = env_get(cfg, "DW_DATABASE")
    log(f"[DW] Conectando {host} / {db} ...")

    with pyodbc.connect(conn_str, timeout=45) as conn:
        objs = discover_objects(conn)
        objs.to_csv(OUT / "dw_objetos_descobertos_v23.csv", index=False, encoding="utf-8-sig")
        log(f"[DW] Objetos descobertos: {len(objs)}")
        if not objs.empty:
            print(objs.to_string(index=False))

        # candidatos meningite SINAN / SINASC / CIPV
        names = objs["TABLE_NAME"].astype(str).tolist() if not objs.empty else []
        mening_views = [n for n in names if re.search(r"MENING", n, re.I)]
        sinasc_views = [n for n in names if re.search(r"SINASC", n, re.I)]
        cipv_cands = [
            n for n in names
            if re.search(r"CIPV|SIPNI|SI_?PNI|IMUNIZ|VACIN|\bPNI", n, re.I)
        ]
        gal_ok = any(n.upper() == "VW_GAL" for n in names) or True
        sim_ok = any(n.upper() == "SIM" for n in names) or True

        escolha = pick_sinan_meningite_view(mening_views)
        if escolha.get("warning"):
            log(f"[AVISO] {escolha['warning']}")
        cipv_res = resolve_cipv_view(cfg, cipv_cands or names)

        resumo = {
            "conectado_em": datetime.now().isoformat(timespec="seconds"),
            "host": host,
            "database": db,
            "n_objetos_filtrados": len(objs),
            "views_meningite_candidatas": mening_views,
            "views_sinasc_candidatas": sinasc_views,
            "views_cipv_candidatas": cipv_cands,
            "cipv_escolha": {
                "schema": cipv_res[0],
                "table": cipv_res[1] or None,
                "metodo": cipv_res[2],
            },
            "sinan_meningite_escolha": escolha,
            "known_map": KNOWN,
        }

        if args.discover_only:
            (OUT / "dw_descoberta_resumo_v23.json").write_text(
                json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log("[OK] Discovery concluída (--discover-only).")
            return

        # Extrações
        extracts = {}
        if gal_ok:
            extracts["gal_lacen_meningites"] = extract_gal(conn, years_back=args.years)
        if sim_ok:
            extracts["sim_obitos_meningites"] = extract_sim(conn, years_back=args.years)
        try:
            extracts["cnes_estabelecimentos"] = extract_cnes(conn)
        except Exception as e:
            log(f"[AVISO] CNES: {e}")
        try:
            leitos = extract_cnes_leitos(conn)
            if leitos is not None and not leitos.empty:
                extracts["cnes_leitos"] = leitos
            else:
                log("[INFO] CNES_LEITOS sem linhas (objeto ausente ou vazio).")
        except Exception as e:
            log(f"[AVISO] CNES_LEITOS: {e}")

        try:
            sih = extract_sih_meningite(conn, years_back=args.years, cfg=cfg)
            if sih is not None and not sih.empty:
                extracts["sih_internacoes_meningite"] = sih
            else:
                log("[INFO] SIH VW_INTERNACAO sem linhas de meningite (ou objeto ausente).")
        except Exception as e:
            log(f"[AVISO] SIH: {e}")

        # CIPV / SI-PNI — servidor Vacinas (SIPNI_MSSQL_*) se configurado; senão tenta no DW
        try:
            sipni_conn = None
            if sipni_host_configured(cfg):
                log(
                    f"[SI-PNI] Conectando {env_get(cfg, 'SIPNI_MSSQL_HOST')} / "
                    f"{env_get(cfg, 'SIPNI_MSSQL_DATABASE', default='Vacinas')} ..."
                )
                sipni_conn = pyodbc.connect(build_sipni_conn_str(cfg), timeout=45)
            try:
                cipv = extract_cipv_meningite(
                    sipni_conn or conn,
                    years_back=args.years,
                    cfg=cfg,
                    candidatas=cipv_cands or names,
                )
            finally:
                if sipni_conn is not None:
                    sipni_conn.close()
            if cipv is not None and not cipv.empty:
                extracts["cipv_doses_meningite"] = cipv
            else:
                log("[INFO] SI-PNI sem linhas de MenACWY/MenC/Hib (códigos DATASUS ou view vazia).")
        except Exception as e:
            log(f"[AVISO] CIPV/SI-PNI: {e}")

        # SINAN meningite: canônico primeiro; heurística *MENING* só como fallback
        sinan_view = escolha.get("view")
        if sinan_view:
            log(
                f"[SINAN] View selecionada: {sinan_view} "
                f"(método={escolha.get('metodo')})"
            )
            extracts["sinan_meningites_dw"] = extract_sinan_meningite(conn, sinan_view)
        else:
            log("[AVISO] Nenhuma view *MENING* encontrada no INFORMATION_SCHEMA.")
            log("        Mantendo base local SINAN; confirme com equipe do DW o nome da view.")

        if sinasc_views:
            extracts["sinasc_dw"] = extract_sinasc(conn, sinasc_views[0], years_back=min(3, args.years))

        saved = {}
        for stem, df in extracts.items():
            p = save_extract(df, stem)
            saved[stem] = {
                "arquivo": p.name if p else None,
                "n": int(len(df)) if df is not None else 0,
            }

        resumo["extracoes"] = saved
        (OUT / "dw_descoberta_resumo_v23.json").write_text(
            json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Relatório curto
        lines = [
            "# Extração DW — Meningites V23",
            "",
            f"**Quando:** {resumo['conectado_em']}",
            f"**Host:** {host} · **DB:** {db}",
            "",
            "## Views/tabelas candidatas (*MENING*)",
            "",
        ]
        if mening_views:
            lines += [f"- `{v}`" for v in mening_views]
        else:
            lines.append("- (nenhuma encontrada pelo filtro INFORMATION_SCHEMA)")
        lines += [
            "",
            f"**View SINAN escolhida:** `{sinan_view or '—'}` "
            f"(método=`{escolha.get('metodo')}`)",
        ]
        if escolha.get("warning"):
            lines.append(f"**Aviso:** {escolha['warning']}")
        lines += ["", "## Extratos gerados em `entradas_linkage/`", ""]
        for k, v in saved.items():
            lines.append(f"- **{k}**: {v['n']} linhas → `{v['arquivo']}`")
        lines += [
            "",
            "## Próximo passo",
            "",
            "```bat",
            "py -3.13 17_linkage_gal_lacen_sim_v23.py",
            "```",
            "",
            "Fontes reutilizadas dos projetos: ROBÔ SIVEP, Monitoramento ondas de calor, SIS Clima-Saúde.",
            "",
        ]
        (REL / "DW_EXTRACAO_MENINGITES_V23.md").write_text("\n".join(lines), encoding="utf-8")
        log(f"[OK] Relatório: {REL / 'DW_EXTRACAO_MENINGITES_V23.md'}")


if __name__ == "__main__":
    main()
