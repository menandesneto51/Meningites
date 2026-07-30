# -*- coding: utf-8 -*-
"""
30_cnes_sinasc_enriquecimento_v30.py
Enriquecimento operacional com CNES (unidade notificante) e SINASC (nascidos vivos).

Entradas (opcionais — se ausentes, sai limpo sem crash):
  - saida_meningites_v17/base_unica_meningites_v17.csv
  - entradas_linkage/cnes_estabelecimentos.csv
  - entradas_linkage/sinasc_dw.csv

Saídas:
  - cnes_perfil_unidade_notificante_v30.csv
  - cnes_acesso_complexidade_regional_v30.csv
  - cnes_tipo_unidade_casos_v30.csv
  - sinasc_nascidos_vivos_municipio_ano_v30.csv  (se SINASC existir)
  - incidencia_menor1ano_sinasc_v30.csv          (se houver casos <1 ano + NV)
  - relatorios/CNES_SINASC_ENRIQUECIMENTO_V30.md

SINASC: usado como denominador de nascidos vivos para proxy de incidência em
menores de 1 ano. Linkage nominal mãe–caso não é feito (LGPD / utilidade fraca).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from meningites_v17_common import OUT, REL, ROOT, load_base_v17, norm_code6, text_key

ENTRADAS = ROOT / "entradas_linkage"
CNES_PATH = ENTRADAS / "cnes_estabelecimentos.csv"
SINASC_PATH = ENTRADAS / "sinasc_dw.csv"

# Classificação operacional do TipoUnidade CNES para proxy de acesso
ATENCAO_BASICA = {
    "CENTRO DE SAUDE/UNIDADE BASICA",
    "POSTO DE SAUDE",
    "UNIDADE DE ATENCAO A SAUDE INDIGENA",
    "POLICLINICA",
    "CENTRO DE APOIO A SAUDE DA FAMILIA",
    "UNIDADE MOVEL FLUVIAL",
    "UNIDADE MOVEL TERRESTRE",
}
ALTA_COMPLEXIDADE = {
    "HOSPITAL GERAL",
    "HOSPITAL ESPECIALIZADO",
    "HOSPITAL/DIA - ISOLADO",
    "PRONTO SOCORRO GERAL",
    "PRONTO SOCORRO ESPECIALIZADO",
    "PRONTO ATENDIMENTO",
    "TIPO 15",  # eventual código residual
    "CLINICA/CENTRO DE ESPECIALIDADE",
    "UNIDADE MISTA",
}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        try:
            return pd.read_csv(path, encoding="latin1", low_memory=False)
        except Exception:
            return pd.DataFrame()


def _norm_cnes(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(r"\D", "", regex=True)
    s = s.str.lstrip("0")
    return s.replace({"": np.nan, "nan": np.nan, "None": np.nan})


def classificar_complexidade(tipo: object) -> str:
    t = text_key(tipo) if pd.notna(tipo) else ""
    if not t:
        return "Sem informação"
    # text_key remove acentos e upper
    basica_keys = {text_key(x) for x in ATENCAO_BASICA}
    alta_keys = {text_key(x) for x in ALTA_COMPLEXIDADE}
    if t in basica_keys or "UNIDADE BASICA" in t or "POSTO DE SAUDE" in t:
        return "Atenção básica"
    if t in alta_keys or "HOSPITAL" in t or "PRONTO" in t or "ESPECIALIDADE" in t:
        return "Alta complexidade / hospitalar"
    return "Outros / intermediário"


def enriquecer_cnes(df: pd.DataFrame, cnes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "CodigoUnidadeNotificacao" not in df.columns:
        print("[AVISO] Base sem CodigoUnidadeNotificacao — CNES não cruzado.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    keep = [
        c for c in [
            "CodigoCnes", "EstabelecimentoNome", "TipoUnidade", "EsferaAdministrativa",
            "NivelHierarquia", "EstabelecimentoMunicipioCodigo", "EstabelecimentoMunicipioNome",
            "EstabelecimentoRegional", "VinculoSUS", "Natureza",
        ]
        if c in cnes.columns
    ]
    c = cnes[keep].copy()
    c["cnes_key"] = _norm_cnes(c["CodigoCnes"])
    c = c.dropna(subset=["cnes_key"]).drop_duplicates("cnes_key", keep="first")
    c["complexidade_acesso_v30"] = c["TipoUnidade"].map(classificar_complexidade) if "TipoUnidade" in c.columns else "Sem informação"

    base = df.copy()
    base["cnes_key"] = _norm_cnes(base["CodigoUnidadeNotificacao"])
    m = base.merge(c, on="cnes_key", how="left", suffixes=("", "_cnes"))
    m["match_cnes_v30"] = m["CodigoCnes"].notna().astype(int) if "CodigoCnes" in m.columns else 0
    if "complexidade_acesso_v30" not in m.columns:
        m["complexidade_acesso_v30"] = "Sem informação"
    m["complexidade_acesso_v30"] = m["complexidade_acesso_v30"].fillna("Sem match CNES")
    m.loc[m["match_cnes_v30"] == 0, "complexidade_acesso_v30"] = "Sem match CNES"

    # Perfil da unidade notificante (estadual + por tipo)
    perfil_rows = [{
        "escopo": "ESTADUAL",
        "recorte": "MT",
        "casos": int(len(m)),
        "com_match_cnes": int(m["match_cnes_v30"].sum()),
        "pct_match_cnes": float(m["match_cnes_v30"].mean() * 100) if len(m) else np.nan,
        "pct_alta_complexidade": float(
            (m["complexidade_acesso_v30"] == "Alta complexidade / hospitalar").mean() * 100
        ) if len(m) else np.nan,
        "pct_atencao_basica": float(
            (m["complexidade_acesso_v30"] == "Atenção básica").mean() * 100
        ) if len(m) else np.nan,
        "unidades_distintas": int(m.loc[m["match_cnes_v30"] == 1, "cnes_key"].nunique()),
    }]
    if "regional_v17" in m.columns:
        for reg, g in m.groupby(m["regional_v17"].fillna("Sem regional").astype(str)):
            perfil_rows.append({
                "escopo": "REGIONAL",
                "recorte": reg,
                "casos": int(len(g)),
                "com_match_cnes": int(g["match_cnes_v30"].sum()),
                "pct_match_cnes": float(g["match_cnes_v30"].mean() * 100) if len(g) else np.nan,
                "pct_alta_complexidade": float(
                    (g["complexidade_acesso_v30"] == "Alta complexidade / hospitalar").mean() * 100
                ) if len(g) else np.nan,
                "pct_atencao_basica": float(
                    (g["complexidade_acesso_v30"] == "Atenção básica").mean() * 100
                ) if len(g) else np.nan,
                "unidades_distintas": int(g.loc[g["match_cnes_v30"] == 1, "cnes_key"].nunique()),
            })
    perfil = pd.DataFrame(perfil_rows)

    # Proxy de acesso por regional
    acesso = perfil[perfil["escopo"].isin(["ESTADUAL", "REGIONAL"])].copy()
    acesso = acesso.rename(columns={
        "pct_alta_complexidade": "pct_casos_alta_complexidade",
        "pct_atencao_basica": "pct_casos_atencao_basica",
    })
    acesso["nota"] = (
        "Proxy de acesso: % de casos notificados em unidades de alta complexidade "
        "vs atenção básica (CNES TipoUnidade × CodigoUnidadeNotificacao)."
    )

    # Contagem por tipo de unidade
    tipo_col = "TipoUnidade" if "TipoUnidade" in m.columns else None
    if tipo_col:
        tipo = (
            m.assign(TipoUnidade=m[tipo_col].fillna("Sem match/sem tipo").astype(str))
            .groupby(["TipoUnidade", "complexidade_acesso_v30"], dropna=False)
            .agg(casos=("cnes_key", "size"), unidades=("cnes_key", "nunique"))
            .reset_index()
            .sort_values("casos", ascending=False)
        )
    else:
        tipo = pd.DataFrame()

    return perfil, acesso, tipo


def processar_sinasc(df: pd.DataFrame, sinasc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Nascidos vivos por município/ano como denominador para casos <1 ano."""
    if sinasc.empty:
        return pd.DataFrame(), pd.DataFrame()

    s = sinasc.copy()
    if "UfResidencia" in s.columns:
        s = s[s["UfResidencia"].astype(str).str.upper().str.strip().eq("MT")].copy()

    mun_col = next(
        (c for c in ["CodigoMunicipioResidencia", "CodigoMunicipioOcorrencia"] if c in s.columns),
        None,
    )
    ano_col = next((c for c in ["AnoNascimento", "Ano"] if c in s.columns), None)
    if mun_col is None or ano_col is None:
        print("[AVISO] SINASC sem colunas de município/ano — denominador <1 ano não gerado.")
        return pd.DataFrame(), pd.DataFrame()

    s["codigo_municipio"] = s[mun_col].map(norm_code6)
    s["ano"] = pd.to_numeric(s[ano_col], errors="coerce").astype("Int64")
    nv = (
        s.dropna(subset=["codigo_municipio", "ano"])
        .groupby(["codigo_municipio", "ano"], as_index=False)
        .size()
        .rename(columns={"size": "nascidos_vivos"})
    )
    # Casos <1 ano — preferir FaixaEtaria; IdadePaciente vem como "010m"/"002a"
    if "FaixaEtaria" in df.columns:
        fx = df["FaixaEtaria"].astype(str).map(text_key)
        menor1 = fx.str.contains("MENOR 01|MENOR DE 1|MENOR 1 ANO|0 A 1", regex=True, na=False)
        casos_m1 = df.loc[menor1].copy()
    elif "IdadePaciente" in df.columns:
        idade_txt = df["IdadePaciente"].astype(str).str.lower()
        # meses (m) ou valor 000a
        casos_m1 = df.loc[idade_txt.str.contains(r"\d+m$|^000a$", regex=True, na=False)].copy()
    else:
        casos_m1 = pd.DataFrame()

    if casos_m1.empty:
        print("[INFO] Sem casos <1 ano identificáveis para incidência SINASC.")
        return nv, pd.DataFrame()

    casos_m1 = casos_m1.copy()
    casos_m1["codigo_municipio"] = casos_m1.get("codigo_municipio_v17")
    casos_m1["ano"] = pd.to_numeric(casos_m1.get("ano_evento_v17"), errors="coerce").astype("Int64")
    group_cols = [c for c in ["codigo_municipio", "ano", "municipio_v17", "regional_v17"] if c in casos_m1.columns]
    if "caso_v17" in casos_m1.columns:
        agg = casos_m1.groupby(group_cols, dropna=False).agg(casos_menor1ano=("caso_v17", "sum")).reset_index()
    else:
        agg = casos_m1.groupby(group_cols, dropna=False).size().reset_index(name="casos_menor1ano")

    out = agg.merge(nv, on=["codigo_municipio", "ano"], how="left")
    out["incidencia_por_1000_nv"] = (
        out["casos_menor1ano"] / out["nascidos_vivos"].replace(0, np.nan) * 1000
    )
    out["tem_denominador_sinasc"] = out["nascidos_vivos"].notna()
    return nv, out


def write_report(
    perfil: pd.DataFrame,
    acesso: pd.DataFrame,
    tipo: pd.DataFrame,
    nv: pd.DataFrame,
    inc_m1: pd.DataFrame,
    cnes_ok: bool,
    sinasc_ok: bool,
) -> Path:
    REL.mkdir(exist_ok=True)
    lines = [
        "# CNES / SINASC — enriquecimento V30",
        "",
        f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Escopo",
        "",
        "- **CNES:** perfil da unidade notificante (tipo, esfera, regional) cruzado com SINAN.",
        "- **Proxy de acesso:** % de casos notificados em alta complexidade vs atenção básica, por regional "
        "(complementa a distância a Cuiabá).",
        "- **SINASC:** nascidos vivos como denominador para proxy de incidência em <1 ano. "
        "Linkage nominal mãe–caso **não** é feito (utilidade epidemiológica fraca / LGPD).",
        "",
        f"- CNES disponível: **{'sim' if cnes_ok else 'não'}**",
        f"- SINASC disponível: **{'sim' if sinasc_ok else 'não'}**",
        "",
    ]
    if not perfil.empty:
        est = perfil[perfil["escopo"].eq("ESTADUAL")]
        if not est.empty:
            r = est.iloc[0]
            lines += [
                "## Resumo estadual (CNES)",
                "",
                f"- Match CNES: **{float(r.get('pct_match_cnes') or 0):.1f}%** ({int(r.get('com_match_cnes', 0) or 0)}/{int(r.get('casos', 0) or 0)})",
                f"- Alta complexidade / hospitalar: **{float(r.get('pct_alta_complexidade') or 0):.1f}%**",
                f"- Atenção básica: **{float(r.get('pct_atencao_basica') or 0):.1f}%**",
                f"- Unidades distintas: **{int(r.get('unidades_distintas', 0) or 0)}**",
                "",
            ]
    if not acesso.empty:
        lines += [
            "## Proxy de acesso por regional",
            "",
            "Ver `cnes_acesso_complexidade_regional_v30.csv`.",
            "",
        ]
    if not tipo.empty:
        lines += [
            "## Top tipos de unidade notificante",
            "",
        ]
        for _, r in tipo.head(8).iterrows():
            lines.append(
                f"- {r.get('TipoUnidade')}: {int(r.get('casos', 0))} casos "
                f"({r.get('complexidade_acesso_v30')})"
            )
        lines.append("")
    if not nv.empty:
        lines += [
            "## SINASC",
            "",
            f"- Nascidos vivos agregados: **{int(nv['nascidos_vivos'].sum())}** "
            f"em {nv['ano'].nunique()} ano(s) / {nv['codigo_municipio'].nunique()} municípios.",
            "",
        ]
    if not inc_m1.empty:
        com = int(inc_m1["tem_denominador_sinasc"].sum()) if "tem_denominador_sinasc" in inc_m1.columns else 0
        lines += [
            f"- Linhas município-ano com casos <1 ano: **{len(inc_m1)}** (com NV: {com})",
            "- Arquivo: `incidencia_menor1ano_sinasc_v30.csv`",
            "",
        ]
    if not cnes_ok and not sinasc_ok:
        lines += [
            "## Status",
            "",
            "Nenhum extrato CNES/SINASC em `entradas_linkage/`. "
            "Rode o módulo 19 (`--from-dw`) quando houver rede ao DW.",
            "",
        ]
    path = REL / "CNES_SINASC_ENRIQUECIMENTO_V30.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(exist_ok=True)
    cnes = _read_csv(CNES_PATH)
    sinasc = _read_csv(SINASC_PATH)
    cnes_ok = not cnes.empty
    sinasc_ok = not sinasc.empty

    if not cnes_ok and not sinasc_ok:
        print(
            "[INFO] CNES e SINASC ausentes em entradas_linkage/ — módulo 30 encerra sem erro. "
            "Extraia com 19_dw_descobrir_e_extrair_v23.py quando houver DW."
        )
        write_report(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            pd.DataFrame(), pd.DataFrame(), False, False,
        )
        # artefatos vazios com cabeçalho mínimo para o painel
        pd.DataFrame(columns=[
            "escopo", "recorte", "casos", "com_match_cnes", "pct_match_cnes",
            "pct_alta_complexidade", "pct_atencao_basica", "unidades_distintas",
        ]).to_csv(OUT / "cnes_perfil_unidade_notificante_v30.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(columns=[
            "escopo", "recorte", "casos", "pct_casos_alta_complexidade",
            "pct_casos_atencao_basica", "nota",
        ]).to_csv(OUT / "cnes_acesso_complexidade_regional_v30.csv", index=False, encoding="utf-8-sig")
        return 0

    try:
        df = load_base_v17()
    except Exception as e:
        print(f"[AVISO] Base única indisponível ({e}) — módulo 30 encerra sem erro.")
        write_report(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            pd.DataFrame(), pd.DataFrame(), cnes_ok, sinasc_ok,
        )
        return 0

    if df is None or df.empty:
        print("[AVISO] Base única vazia — módulo 30 encerra sem erro.")
        write_report(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            pd.DataFrame(), pd.DataFrame(), cnes_ok, sinasc_ok,
        )
        return 0

    perfil = acesso = tipo = pd.DataFrame()
    if cnes_ok:
        perfil, acesso, tipo = enriquecer_cnes(df, cnes)
        perfil.to_csv(OUT / "cnes_perfil_unidade_notificante_v30.csv", index=False, encoding="utf-8-sig")
        acesso.to_csv(OUT / "cnes_acesso_complexidade_regional_v30.csv", index=False, encoding="utf-8-sig")
        tipo.to_csv(OUT / "cnes_tipo_unidade_casos_v30.csv", index=False, encoding="utf-8-sig")
        print(f"[OK] CNES: match em perfil ({len(perfil)} escopos) · tipos={len(tipo)}")
    else:
        print("[INFO] CNES ausente — pulando cruzamento de unidade notificante.")

    nv = inc_m1 = pd.DataFrame()
    if sinasc_ok:
        nv, inc_m1 = processar_sinasc(df, sinasc)
        if not nv.empty:
            nv.to_csv(OUT / "sinasc_nascidos_vivos_municipio_ano_v30.csv", index=False, encoding="utf-8-sig")
            print(f"[OK] SINASC: {len(nv)} município-ano de nascidos vivos")
        if not inc_m1.empty:
            inc_m1.to_csv(OUT / "incidencia_menor1ano_sinasc_v30.csv", index=False, encoding="utf-8-sig")
            print(f"[OK] Incidência <1 ano (NV): {len(inc_m1)} linhas")
    else:
        print("[INFO] SINASC ausente — sem denominador de nascidos vivos.")

    rel = write_report(perfil, acesso, tipo, nv, inc_m1, cnes_ok, sinasc_ok)
    print(f"[OK] Relatório: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
