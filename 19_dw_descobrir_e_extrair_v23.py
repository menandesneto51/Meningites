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
    "sinan_srag": "dbo.VW_SINAN_SINDROMERESPIRATORIAAGUDAGRAVE",
    "sinan_dengue": "dbo.VW_SINAN_DENGUE",
    "sinan_chik": "dbo.VW_SINAN_CHIKUNGUNYA",
}

# CIDs típicos de meningite / doença meningocócica no SIM
SIM_CID_LIKE = (
    "A39%",  # doença meningocócica
    "G00%",  # meningite bacteriana
    "G01%",  # meningite em doenças bacterianas classificadas em outra parte
    "G02%",  # meningite em outras doenças infecciosas
    "G03%",  # meningite por outras causas e não especificadas
    "A87%",  # meningite viral
)


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
        if k.startswith("DW_") or k in {"USE_SQLSERVER", "USE_DW"}:
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
    ORDER BY TABLE_TYPE, TABLE_NAME
    """
    return pd.read_sql(sql, conn)


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

        # candidatos meningite SINAN / SINASC
        names = objs["TABLE_NAME"].astype(str).tolist() if not objs.empty else []
        mening_views = [n for n in names if re.search(r"MENING", n, re.I)]
        sinasc_views = [n for n in names if re.search(r"SINASC", n, re.I)]
        gal_ok = any(n.upper() == "VW_GAL" for n in names) or True
        sim_ok = any(n.upper() == "SIM" for n in names) or True

        resumo = {
            "conectado_em": datetime.now().isoformat(timespec="seconds"),
            "host": host,
            "database": db,
            "n_objetos_filtrados": len(objs),
            "views_meningite_candidatas": mening_views,
            "views_sinasc_candidatas": sinasc_views,
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

        # SINAN meningite: prioriza view com MENING no nome
        sinan_view = mening_views[0] if mening_views else None
        if sinan_view:
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
