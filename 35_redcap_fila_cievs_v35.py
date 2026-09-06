# -*- coding: utf-8 -*-
"""
35_redcap_fila_cievs_v35.py
Fila CIEVS / RedCap — notificação quase em tempo real de meningites.

Contexto
--------
Busca em Meningites e pastas CIEVS-MT irmãs **não encontrou** schema/API/export
de RedCap de meningites (apenas referências operacionais genéricas à fila CIEVS
baseada em SINAN/GAL/SIM no módulo 20). Este módulo é um **stub offline-safe**:
contratos, loader e painel prontos para quando o export existir.

Entrada (ausência NÃO derruba o pipeline):
  entradas_linkage/redcap_fila_meningite_cievs.csv
  ou caminho em REDCAP_FILA_CSV / REDCAP_MENINGITE_CSV

Colunas esperadas no export (aliases flexíveis — ver COLUNAS_ESPERADAS):
  record_id, data_notificacao, data_sintomas, codigo_municipio, municipio,
  regional, tipo_evento, etiologia, sorogrupo, faixa_etaria, sexo,
  status_fila, prioridade, acao_pendente, obito, surto_cluster,
  nu_notificacao_sinan (opcional — só flag de vínculo, nunca exportado cru)

Saídas (saida_meningites_v17/):
  - redcap_fila_prep_v35.csv       (só se export existir; sem PII)
  - redcap_kpis_fila_v35.csv
  - redcap_gap_sinan_v35.csv       (RedCap aberto sem vínculo SINAN; se houver dados)
  - redcap_schema_esperado_v35.csv (cabeçalho canônico documentado)
  - redcap_fonte_meta_v35.json
  - relatorios/REDCAP_FILA_CIEVS_V35.md

LGPD: descarta CPF/CNS/nome/endereço/telefone; record_id vira hash curto;
nu_notificacao_sinan vira apenas flag booleana. Não inventa registros de produção.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, ROOT, norm_code6, text_key

ENTRADAS = ROOT / "entradas_linkage"
DEFAULT_PATH = ENTRADAS / "redcap_fila_meningite_cievs.csv"

# Contrato canônico documentado (export RedCap CIEVS meningites — quando existir)
COLUNAS_ESPERADAS: list[str] = [
    "record_id",
    "data_notificacao",
    "data_sintomas",
    "codigo_municipio",
    "municipio",
    "regional",
    "tipo_evento",
    "etiologia",
    "sorogrupo",
    "faixa_etaria",
    "sexo",
    "status_fila",
    "prioridade",
    "acao_pendente",
    "obito",
    "surto_cluster",
    "nu_notificacao_sinan",
]

PREP_COLS = [
    "id_registro_v35",
    "data_evento_v35",
    "data_sintomas_v35",
    "codigo_municipio_v35",
    "municipio_v35",
    "regional_v35",
    "tipo_evento_v35",
    "etiologia_v35",
    "sorogrupo_v35",
    "faixa_etaria_v35",
    "sexo_v35",
    "status_fila_v35",
    "prioridade_v35",
    "acao_pendente_v35",
    "obito_v35",
    "surto_cluster_v35",
    "tem_vinculo_sinan_v35",
    "horas_desde_evento_v35",
    "fonte_v35",
]


def resolve_redcap_path() -> Path:
    for key in ("REDCAP_FILA_CSV", "REDCAP_MENINGITE_CSV", "REDCAP_CIEVS_CSV"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return Path(raw)
    return DEFAULT_PATH


def _read_redcap(path: Path | None = None) -> pd.DataFrame:
    p = path or resolve_redcap_path()
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    except Exception:
        try:
            return pd.read_csv(p, encoding="latin1", low_memory=False)
        except Exception:
            return pd.DataFrame()


def _drop_pii(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    drop = []
    for c in df.columns:
        cl = str(c).lower()
        if re.search(
            r"nomepaciente|nome_paciente|nomemae|nome_mae|nomepai|nome_pai|"
            r"nomeobito|nome_obito|^nome$|cpf|cns|cartaosus|cartao_sus|"
            r"endereco|logradouro|bairro|cep|telefone|celular|email|"
            r"doc_|rg\b|prontuario|prontuário",
            cl,
            re.I,
        ):
            drop.append(c)
    return df.drop(columns=drop, errors="ignore")


def _hash_id(valor) -> str:
    s = str(valor).strip()
    if not s or s.lower() in {"nan", "none", "<na>"}:
        return ""
    digest = hashlib.sha256(f"redcap_v35|{s}".encode("utf-8")).hexdigest()[:10].upper()
    return f"RC-{digest}"


def _pick_col(df: pd.DataFrame, patterns: list[str]) -> str | None:
    for pat in patterns:
        for c in df.columns:
            if re.search(pat, str(c), re.I):
                return str(c)
    return None


def _parse_dt(serie: pd.Series) -> pd.Series:
    """ISO primeiro; se falhar em massa, tenta dayfirst (export BR)."""
    iso = pd.to_datetime(serie, errors="coerce")
    if iso.notna().sum() >= max(1, int(0.5 * len(serie))):
        return iso
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def _sim_nao(x) -> int | float:
    if pd.isna(x):
        return np.nan
    t = text_key(x)
    if not t:
        return np.nan
    if t in {"1", "S", "SIM", "YES", "Y", "TRUE", "VERDADEIRO", "OBITO", "ÓBITO"}:
        return 1
    if t in {"0", "N", "NAO", "NÃO", "NO", "FALSE", "FALSO"}:
        return 0
    if "OBITO" in t or "ÓBITO" in t or "SURTO" in t or "CLUSTER" in t:
        return 1
    return np.nan


def _norm_sexo(x) -> str:
    t = text_key(x)
    if not t:
        return ""
    if t.startswith("M") or t in {"1", "MASCULINO"}:
        return "M"
    if t.startswith("F") or t in {"2", "FEMININO"}:
        return "F"
    return ""


def _norm_prioridade(row: pd.Series) -> str:
    p = text_key(row.get("prioridade_raw", ""))
    if p in {"CRITICA", "CRÍTICA", "CRITICO", "CRÍTICO", "1", "P1"}:
        return "critica"
    if p in {"ALTA", "2", "P2"}:
        return "alta"
    if p in {"MEDIA", "MÉDIA", "3", "P3"}:
        return "media"
    if p in {"BAIXA", "4", "P4"}:
        return "baixa"
    # heurística operacional CIEVS (notificação imediata)
    if int(row.get("obito_v35") or 0) == 1:
        return "critica"
    if int(row.get("surto_cluster_v35") or 0) == 1:
        return "critica"
    tipo = text_key(row.get("tipo_evento_v35", ""))
    if "OBITO" in tipo or "SURTO" in tipo or "CLUSTER" in tipo:
        return "critica"
    etio = text_key(row.get("etiologia_v35", ""))
    if "MENINGOCOC" in etio or etio in {"DM", "DOENCA MENINGOCOCICA"}:
        return "alta"
    status = text_key(row.get("status_fila_v35", ""))
    if status in {"ABERTO", "PENDENTE", "EM INVESTIGACAO", "EM INVESTIGAÇÃO"}:
        return "alta"
    return "media"


def _norm_status(x) -> str:
    t = text_key(x)
    if not t:
        return "ignorado"
    if "ENCERR" in t or t in {"FECHADO", "CONCLUIDO", "CONCLUÍDO"}:
        return "encerrado"
    if "INVESTIG" in t:
        return "em_investigacao"
    if t in {"ABERTO", "PENDENTE", "NOVO", "FILA"}:
        return "aberto"
    return t.lower()[:40]


def preparar_redcap(raw: pd.DataFrame, agora: datetime | None = None) -> pd.DataFrame:
    """Normaliza export RedCap flexível → colunas canônicas sem PII."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=PREP_COLS)
    df = _drop_pii(raw).copy()
    agora = agora or datetime.now()

    id_c = _pick_col(df, [r"^record_?id$", r"^id_registro$", r"^id$", r"redcap.?id"])
    dt_c = _pick_col(df, [r"data_notif", r"dt_notif", r"timestamp", r"data_registro", r"data_evento"])
    sint_c = _pick_col(df, [r"data_sintom", r"dt_sintom", r"inicio_sintom"])
    mun_c = _pick_col(df, [r"codigo.?municipio|ibge|cod_mun|municipio_ibge|cd_mun"])
    mun_nome = _pick_col(df, [r"^municipio$|nome_municipio|municipio_resid"])
    reg_c = _pick_col(df, [r"regional|rs_|crs"])
    tipo_c = _pick_col(df, [r"tipo_evento|tipo_caso|classificacao_evento|evento"])
    etio_c = _pick_col(df, [r"etiolog|classificacao|agravo|diagnost"])
    soro_c = _pick_col(df, [r"sorogrupo|serogrupo"])
    faixa_c = _pick_col(df, [r"faixa.?etar|grupo.?idad"])
    sexo_c = _pick_col(df, [r"^sexo$|sexo_paciente"])
    status_c = _pick_col(df, [r"status_fila|status_caso|situacao|status"])
    prio_c = _pick_col(df, [r"prioridade|urgencia|criticidade"])
    acao_c = _pick_col(df, [r"acao_pendente|ação_pendente|pendencia|acao"])
    obito_c = _pick_col(df, [r"^obito$|óbito|evolucao.?obito|desfecho.?obito"])
    surto_c = _pick_col(df, [r"surto|cluster|aglomerado"])
    sinan_c = _pick_col(df, [r"nu_?notif|numero.?notif|sinan"])

    out = pd.DataFrame(index=df.index)
    if id_c:
        out["id_registro_v35"] = df[id_c].map(_hash_id)
    else:
        out["id_registro_v35"] = [f"RC-ROW{i:04d}" for i in range(len(df))]

    if dt_c:
        out["data_evento_v35"] = _parse_dt(df[dt_c])
    else:
        out["data_evento_v35"] = pd.NaT
    if sint_c:
        out["data_sintomas_v35"] = _parse_dt(df[sint_c])
    else:
        out["data_sintomas_v35"] = pd.NaT

    if mun_c:
        out["codigo_municipio_v35"] = df[mun_c].map(norm_code6)
    else:
        out["codigo_municipio_v35"] = np.nan
    out["municipio_v35"] = df[mun_nome].astype(str) if mun_nome else ""
    out["regional_v35"] = df[reg_c].astype(str) if reg_c else ""
    out["tipo_evento_v35"] = df[tipo_c].astype(str) if tipo_c else ""
    out["etiologia_v35"] = df[etio_c].astype(str) if etio_c else ""
    out["sorogrupo_v35"] = df[soro_c].astype(str) if soro_c else ""
    out["faixa_etaria_v35"] = df[faixa_c].astype(str) if faixa_c else ""
    out["sexo_v35"] = df[sexo_c].map(_norm_sexo) if sexo_c else ""
    out["status_fila_v35"] = df[status_c].map(_norm_status) if status_c else "ignorado"
    out["acao_pendente_v35"] = df[acao_c].astype(str) if acao_c else ""
    out["obito_v35"] = df[obito_c].map(_sim_nao) if obito_c else np.nan
    out["surto_cluster_v35"] = df[surto_c].map(_sim_nao) if surto_c else np.nan
    if sinan_c:
        out["tem_vinculo_sinan_v35"] = df[sinan_c].notna() & df[sinan_c].astype(str).str.strip().ne("")
    else:
        out["tem_vinculo_sinan_v35"] = False

    out["prioridade_raw"] = df[prio_c].astype(str) if prio_c else ""
    out["prioridade_v35"] = out.apply(_norm_prioridade, axis=1)
    out = out.drop(columns=["prioridade_raw"], errors="ignore")

    delta = (pd.Timestamp(agora) - out["data_evento_v35"]).dt.total_seconds() / 3600.0
    out["horas_desde_evento_v35"] = delta
    out["fonte_v35"] = "redcap_cievs"

    # serializa datas
    out["data_evento_v35"] = out["data_evento_v35"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out["data_sintomas_v35"] = out["data_sintomas_v35"].dt.strftime("%Y-%m-%d")
    return out[PREP_COLS].reset_index(drop=True)


def kpis_fila(prep: pd.DataFrame, *, disponivel: bool) -> pd.DataFrame:
    rows = []
    if not disponivel or prep is None or prep.empty:
        rows.append({
            "escopo": "STUB",
            "indicador": "export_redcap",
            "n": 0,
            "pct": np.nan,
            "nota": "Export ausente — stub offline-safe; sem dados inventados",
        })
        return pd.DataFrame(rows)

    n = len(prep)
    abertos = prep["status_fila_v35"].isin(["aberto", "em_investigacao", "pendente"])
    crit = prep["prioridade_v35"].eq("critica")
    sem_sinan = ~prep["tem_vinculo_sinan_v35"].fillna(False)
    obitos = prep["obito_v35"].fillna(0).astype(float).eq(1)
    surtos = prep["surto_cluster_v35"].fillna(0).astype(float).eq(1)

    def _pct(num, den):
        if den == 0:
            return float("nan")
        return float(num) / float(den) * 100.0

    rows.extend([
        {"escopo": "ESTADUAL", "indicador": "registros_total", "n": n, "pct": 100.0,
         "nota": "Linhas no export RedCap após scrub"},
        {"escopo": "ESTADUAL", "indicador": "abertos_ou_investigacao", "n": int(abertos.sum()),
         "pct": _pct(abertos.sum(), n), "nota": "Fila ativa CIEVS"},
        {"escopo": "ESTADUAL", "indicador": "prioridade_critica", "n": int(crit.sum()),
         "pct": _pct(crit.sum(), n), "nota": "Óbito/surto/cluster ou prioridade explícita"},
        {"escopo": "ESTADUAL", "indicador": "sem_vinculo_sinan", "n": int(sem_sinan.sum()),
         "pct": _pct(sem_sinan.sum(), n), "nota": "Sinal de atraso SINAN ou notificação só RedCap"},
        {"escopo": "ESTADUAL", "indicador": "obitos", "n": int(obitos.sum()),
         "pct": _pct(obitos.sum(), n), "nota": "Notificação imediata (óbito)"},
        {"escopo": "ESTADUAL", "indicador": "surto_cluster", "n": int(surtos.sum()),
         "pct": _pct(surtos.sum(), n), "nota": "Notificação imediata (surto/cluster)"},
    ])

    for prio, g in prep.groupby("prioridade_v35", dropna=False):
        rows.append({
            "escopo": "PRIORIDADE",
            "indicador": str(prio),
            "n": int(len(g)),
            "pct": _pct(len(g), n),
            "nota": "Distribuição de prioridade",
        })
    for reg, g in prep.groupby("regional_v35", dropna=False):
        if not str(reg).strip() or str(reg).lower() in {"nan", "none"}:
            continue
        rows.append({
            "escopo": "REGIONAL",
            "indicador": str(reg)[:80],
            "n": int(len(g)),
            "pct": _pct(len(g), n),
            "nota": "Volume por regional",
        })
    return pd.DataFrame(rows)


def gap_sinan(prep: pd.DataFrame) -> pd.DataFrame:
    """Itens ativos RedCap sem vínculo SINAN — sem PII."""
    if prep is None or prep.empty:
        return pd.DataFrame(columns=PREP_COLS)
    mask = (
        ~prep["tem_vinculo_sinan_v35"].fillna(False)
        & prep["status_fila_v35"].isin(["aberto", "em_investigacao", "pendente", "ignorado"])
    )
    cols = [
        "id_registro_v35", "data_evento_v35", "codigo_municipio_v35", "municipio_v35",
        "regional_v35", "tipo_evento_v35", "etiologia_v35", "prioridade_v35",
        "status_fila_v35", "acao_pendente_v35", "horas_desde_evento_v35",
    ]
    return prep.loc[mask, [c for c in cols if c in prep.columns]].copy()


def write_schema_esperado() -> Path:
    path = OUT / "redcap_schema_esperado_v35.csv"
    pd.DataFrame(columns=COLUNAS_ESPERADAS).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_meta(
    *,
    path_entrada: Path,
    n_raw: int,
    n_prep: int,
    disponivel: bool,
    kdf: pd.DataFrame,
    msg: str,
) -> Path:
    meta = {
        "modulo": "35_redcap_fila_cievs_v35",
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "redcap_disponivel": bool(disponivel),
        "entrada": str(path_entrada),
        "entrada_default": str(DEFAULT_PATH.name),
        "env_override": ["REDCAP_FILA_CSV", "REDCAP_MENINGITE_CSV", "REDCAP_CIEVS_CSV"],
        "n_linhas_raw": int(n_raw),
        "n_linhas_prep": int(n_prep),
        "colunas_esperadas": COLUNAS_ESPERADAS,
        "lgpd": {
            "cpf_cns_nome_exportados": False,
            "record_id_hasheado": True,
            "nu_notificacao_sinan_exportado": False,
            "politica": "scrub nominal/documento; id hasheado; SINAN só como flag",
        },
        "nota": (
            "Stub offline-safe: não há schema RedCap meningites no repositório CIEVS-MT. "
            "Deposite export CSV (sem PII desnecessário) em entradas_linkage/ "
            "ou defina REDCAP_FILA_CSV. Não inventa fila de produção."
        ),
        "mensagem": msg,
        "kpis_resumo": (
            kdf.head(12).fillna("").astype(str).to_dict(orient="records")
            if kdf is not None and not kdf.empty else []
        ),
    }
    path = OUT / "redcap_fonte_meta_v35.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_report(*, disponivel: bool, prep: pd.DataFrame, kdf: pd.DataFrame, msg: str) -> Path:
    lines = [
        "# Fila CIEVS / RedCap — Meningites V35",
        "",
        f"**Gerado em:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Status:** {msg}",
        "",
        "## Escopo",
        "",
        "- Canal quase em tempo real da CIEVS-MT para meningites / DM (quando o export existir).",
        "- Complementa a fila SINAN/GAL/SIM do módulo 20 — **não a substitui**.",
        "- Stub offline-safe: ausência do CSV não falha o pipeline.",
        "- LGPD: sem CPF/CNS/nome; `record_id` hasheado; NU_NOTIFICACAO só como flag.",
        "",
        f"**Export disponível:** {'sim' if disponivel else 'não'}",
        "",
        "## Colunas esperadas no CSV",
        "",
    ]
    for c in COLUNAS_ESPERADAS:
        lines.append(f"- `{c}`")
    lines += [
        "",
        "## Como ativar",
        "",
        "1. Exportar do RedCap CIEVS (projeto meningites) as colunas acima (ou aliases).",
        "2. Remover PII desnecessária no export de origem.",
        f"3. Salvar em `{DEFAULT_PATH.as_posix()}` **ou** definir `REDCAP_FILA_CSV`.",
        "4. Rodar `py -3.13 35_redcap_fila_cievs_v35.py`.",
        "",
        "## IndicaSUS (fora de escopo por enquanto)",
        "",
        "IndicaSUS **não** está integrado neste projeto. Só será considerado se houver "
        "objeto/API útil que SINAN/SIH/CNES não cubram; até lá permanece adiado "
        "(ver `.env.example`).",
        "",
    ]
    if disponivel and prep is not None and not prep.empty:
        lines += ["## KPIs", ""]
        for _, r in kdf[kdf["escopo"].eq("ESTADUAL")].iterrows():
            lines.append(
                f"- **{r['indicador']}**: n={int(r['n'])}"
                + (f" ({float(r['pct']):.1f}%)" if pd.notna(r.get("pct")) else "")
            )
        lines.append("")
    else:
        lines += [
            "## Stub ativo",
            "",
            "Nenhum registro RedCap de meningites foi carregado. "
            "O painel mostra o bloco 'Fila CIEVS / RedCap' com esta mensagem. "
            "A fila unificada V23 (SINAN) continua válida na aba operacional.",
            "",
        ]
    path = REL / "REDCAP_FILA_CIEVS_V35.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(exist_ok=True)
    REL.mkdir(exist_ok=True)

    path_in = resolve_redcap_path()
    raw = _read_redcap(path_in)
    disponivel = not raw.empty
    prep = preparar_redcap(raw) if disponivel else pd.DataFrame(columns=PREP_COLS)
    kdf = kpis_fila(prep, disponivel=disponivel and not prep.empty)
    gaps = gap_sinan(prep) if disponivel and not prep.empty else pd.DataFrame(columns=PREP_COLS)

    prep.to_csv(OUT / "redcap_fila_prep_v35.csv", index=False, encoding="utf-8-sig")
    kdf.to_csv(OUT / "redcap_kpis_fila_v35.csv", index=False, encoding="utf-8-sig")
    gaps.to_csv(OUT / "redcap_gap_sinan_v35.csv", index=False, encoding="utf-8-sig")
    write_schema_esperado()

    if disponivel and not prep.empty:
        msg = (
            f"RedCap com {len(raw)} linhas brutas → {len(prep)} registros scrubados; "
            f"gap SINAN ativos={len(gaps)}."
        )
    elif disponivel:
        msg = f"Export presente em {path_in.name} mas ficou vazio após normalização."
    else:
        msg = (
            f"{path_in.name if path_in else DEFAULT_PATH.name} ausente — stub V35 ativo "
            "(sem inventar fila). Deposite CSV ou defina REDCAP_FILA_CSV."
        )

    write_meta(
        path_entrada=path_in,
        n_raw=len(raw),
        n_prep=len(prep),
        disponivel=bool(disponivel and not prep.empty),
        kdf=kdf,
        msg=msg,
    )
    write_report(disponivel=bool(disponivel and not prep.empty), prep=prep, kdf=kdf, msg=msg)

    print(f"[OK] RedCap / Fila CIEVS V35: {msg}")
    if not kdf.empty:
        print(kdf.head(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
